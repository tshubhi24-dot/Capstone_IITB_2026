"""C1 — one agent with all the tools, as a LangGraph graph (L8, L10).

    START → input_guard → plan → review_plan ⟲(edit) → research ⇄ tools
          → write → check ─(issues, max 2)→ write
          → review_note ─(edit)→ check │ (reject)→ END
          → publish → END
    tools ─(a tool contradicts the plan: NOT_IN_COVERAGE)→ replan → review_plan

* Typed state (AgentState) and conditional edges.
* Two human gates with interrupt(): the analyst approves or edits the plan,
  and approves, edits or rejects the exact note (L14).
* Self-correction loop: code checks every number and citation (checks.py)
  and sends the issues back to the writer, at most twice.
* Replanning: a tool result that contradicts the plan sends it back to the
  planner, and the analyst sees the revised plan.
* ReAct inside research: think → call a tool → observe → repeat, within a
  tool-call and token budget. Every tool call passes through the hooks.
* A persistent checkpointer (SQLite) saves state after every step, so a run
  can be stopped at any gate and resumed later from a new process.

The nodes shared with the C2 team (guard, plan, gates, writer, checks,
publish) are built by common_nodes() and reused by team.py.

The model proposes; code decides numbers and checks; a person approves.
"""

from __future__ import annotations

import json
import operator
import os
import re
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from .. import approval
from ..llm_config import LLM_CONFIG
from ..query import find_companies, find_years
from ..scope import COMPANIES
from ..servers.common import COVERED_YEARS
from .checks import ADVICE, check_note
from .figures import build_figures, comparability_notes, figures_table, render
from .guards import INJECTION, defences_on, private_names
from .hooks import Hooks, wrap_for_toolnode

# Tool-call budget for one run, the SAME for C1 and C2 (brief: the single agent and the team get
# "the same tools and budget"; L11: only the division of work changes). It grows with the number
# of companies in the plan: 12 + 12 per company = 24 for one company, 36 for two, 48 for three.
# C2 splits this same total across its specialists (team.specialist_budgets).
CALLS_BASE = int(os.getenv("AGENT_CALLS_BASE", "12"))
CALLS_PER_COMPANY = int(os.getenv("AGENT_CALLS_PER_COMPANY", "12"))


def critic_loop_on() -> bool:
    """The critic loop: revisions after failed checks and, in C2, the judge. Off for E4."""
    return os.getenv("AGENT_CRITIC", "1") != "0"


def tool_budget(n_companies: int) -> int:
    """Tool calls one run may make, C1 and C2 alike. AGENT_MAX_TOOL_CALLS fixes it (experiments)."""
    fixed = os.getenv("AGENT_MAX_TOOL_CALLS")
    if fixed:
        return int(fixed)
    return CALLS_BASE + CALLS_PER_COMPANY * max(1, n_companies)

TOKEN_BUDGET = int(os.getenv("AGENT_TOKEN_BUDGET", "120000"))
MAX_CONTEXT_CHARS = int(os.getenv("AGENT_MAX_CONTEXT_CHARS", "60000"))
MAX_REVISIONS = 2
MAX_REPLANS = 1
_TICKERS = {c.ticker for c in COMPANIES}
_BANKS = {c.ticker for c in COMPANIES if c.margin_basis == "pretax"}
_ASKS_FOR_CHANGES = re.compile(r"last note|previous note|since our|what changed", re.I)


# ── state ─────────────────────────────────────────────────────────────────────

class Plan(BaseModel):
    companies: list[str] = Field(description="Tickers to cover, e.g. ['MSFT', 'GOOGL']")
    fiscal_years: list[int] = Field(description="Fiscal years, e.g. [2022, 2023, 2024]")
    sub_questions: list[str] = Field(description="3-6 concrete research questions")
    outline: list[str] = Field(description="Section headings of the note")


class Draft(BaseModel):
    title: str
    body: str = Field(description="The note in Markdown, every number with its source tag")
    tickers: list[str]


class AgentState(TypedDict, total=False):
    request: str
    mode: str                         # "c1" single agent | "c2" team
    guard: dict
    plan: dict
    plan_feedback: str
    year_confirmation: dict
    replans: int
    messages: Annotated[list, add_messages]          # C1 research conversation
    handoffs: Annotated[list, operator.add]          # C2 specialists' typed hand-offs
    tool_calls: Annotated[int, operator.add]         # increments, so parallel agents add up
    tokens: Annotated[int, operator.add]
    draft: dict
    render_issues: list
    check: dict
    revisions: int
    outcome: str                      # approved | published | rejected | publish_failed
    published: dict
    analyst: str
    memory_on: bool
    memory: dict                      # what memory contributed to this run
    watchlist: list                   # the analyst's private watchlist (never leaves the system)
    lessons: list                     # approved playbook lessons used in this run
    trace: Annotated[list, operator.add]


def _event(node: str, **info) -> list[dict]:
    return [{"node": node, **info}]


def usage(msg) -> int:
    meta = getattr(msg, "usage_metadata", None) or {}
    return int(meta.get("total_tokens", 0))


def tool_json(raw) -> dict:
    """The structured result of an MCP tool call as a dict.

    The adapter returns content blocks: [{"type": "text", "text": "<json>"}]
    (or that list as a JSON string); the tool's own result is the inner JSON.
    """
    data = raw
    for _ in range(3):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                return {}
        elif isinstance(data, list) and data and isinstance(data[0], dict) and "text" in data[0]:
            data = data[0]["text"]
        elif isinstance(data, dict):
            return data
        else:
            return {}
    return data if isinstance(data, dict) else {}


def insert_changes(body: str, changed: str) -> str:
    """Put the code-computed 'what changed' lines into the note, always under a heading.

    The writer may leave {WHAT_CHANGED} with or without its own heading above it; without
    one, the lines read as the end of the note and the analyst does not notice them.
    """
    section = "## What changed since our last note\n" + changed
    if "{WHAT_CHANGED}" not in body:
        return body + "\n\n" + section
    before = body.split("{WHAT_CHANGED}")[0].rstrip().splitlines()
    has_heading = bool(before) and before[-1].lstrip().startswith("#")
    return body.replace("{WHAT_CHANGED}", changed if has_heading else section)


_RELATIVE_YEARS = re.compile(
    r"\b(most\s+recent|last|past|previous|recent|latest)\s+(two|three|2|3)\s+(fiscal\s+)?years\b",
    re.I,
)
_YEAR_COUNTS = {"two": 2, "three": 3}


def _relative_year_count(request: str) -> int | None:
    match = _RELATIVE_YEARS.search(request)
    if not match:
        return None
    count = match.group(2)
    return int(count) if count.isdigit() else _YEAR_COUNTS[count.lower()]


def year_confirmation_required(request: str) -> bool:
    """Relative and unspecified periods need an explicit choice at the plan gate."""
    return _relative_year_count(request) is not None or not find_years(request)


def _format_years(years: list[int]) -> str:
    ordered = sorted(set(years))
    if not ordered:
        return "no covered fiscal years"
    if ordered == list(range(ordered[0], ordered[-1] + 1)):
        return f"FY{ordered[0]}–FY{ordered[-1]}" if len(ordered) > 1 else f"FY{ordered[0]}"
    return ", ".join(f"FY{year}" for year in ordered)


def plan_assumptions(request: str, plan: dict) -> list[str]:
    """How code read the request, shown at the plan gate so the analyst can correct it."""
    years = _format_years(plan["fiscal_years"])
    out = []
    if m := _RELATIVE_YEARS.search(request):
        count = _relative_year_count(request)
        covered = sorted(COVERED_YEARS)[-count:]
        years = _format_years(covered)
        out.append(f"“{m.group(0)}” proposes {years}, the latest covered fiscal years, "
                   "using each company's own fiscal year (not calendar years).")
        if len(covered) < count:
            out.append(f"The data covers only {len(covered)} of the requested {count} fiscal years; "
                       "edit the plan or cancel if that range is insufficient.")
    elif not find_years(request):
        out.append(f"No year was named, so the proposed default covers {years}.")
    banks = [t for t in plan["companies"] if t in _BANKS]
    if banks:
        out.append(f"{', '.join(banks)} {'is a bank' if len(banks) == 1 else 'are banks'}: "
                   "margins are pre-tax margin, not operating margin.")
    return out


def trim_context(msgs: list, max_chars: int = MAX_CONTEXT_CHARS) -> list:
    """Short-term memory (L9): keep the system prompt, the request and the most
    recent tool rounds within a size budget. The cut always lands on an AI
    message, so no tool result is left without the call that asked for it."""
    def size(m):
        return len(m.content if isinstance(m.content, str) else json.dumps(m.content))
    if sum(size(m) for m in msgs) <= max_chars or len(msgs) <= 3:
        return msgs
    head, rest = msgs[:2], msgs[2:]
    budget = max_chars - sum(size(m) for m in head)
    keep_from = len(rest)
    for i in range(len(rest) - 1, -1, -1):
        budget -= size(rest[i])
        if budget < 0:
            break
        if isinstance(rest[i], AIMessage):
            keep_from = i
    note = HumanMessage(f"[{keep_from} earlier messages trimmed to fit the context budget; "
                        "rely on your notes of their results so far.]")
    return head + [note] + rest[keep_from:]


# ── nodes shared by C1 and C2 ─────────────────────────────────────────────────

def common_nodes(llm, publish_tool, passage_text=None, critic=None) -> dict:
    """Guard, plan, plan gate, writer, check (+ optional critic), note gate, publish.

    critic: async fn(draft_body) -> {"issues": [...], ...} run after the code
    checks (the C2 compliance critic's judge); None for C1.
    """

    # 1. scope check in code: covered companies, no advice requests
    def input_guard(state: AgentState):
        req = state["request"]
        companies = find_companies(req)
        years = [y for y in find_years(req)]
        reason = None
        if not companies:
            reason = f"No covered company named. Covered: {', '.join(sorted(_TICKERS))}."
        elif [y for y in years if y not in COVERED_YEARS]:
            reason = f"Only fiscal years {COVERED_YEARS} are covered."
        elif ADVICE.search(req):
            reason = "Requests for investment advice (buy/sell/price targets) are out of scope."
        elif INJECTION.search(req):
            reason = "The request contains instructions aimed at the system rather than a research question."
        if not defences_on():   # E2, defences off: every request goes through
            reason = None
        guard = {"ok": reason is None, "reason": reason, "companies": companies, "years": years}
        # evaluation runs never use memory, so results stay reproducible
        memory_on = state.get("memory_on", True) and os.getenv("AGENT_EVAL") != "1"
        return {"guard": guard, "replans": 0, "revisions": 0, "memory_on": memory_on,
                "trace": _event("input_guard", **guard)}

    def after_guard(state) -> Literal["plan", "__end__"]:
        return "plan" if state["guard"]["ok"] else END

    # 2. plan (also used for replanning, with feedback)
    async def plan(state: AgentState):
        mem = dict(state.get("memory") or {})
        if state.get("memory_on", True) and not mem:
            from .. import memory as ltm
            prefs = [p["text"] for p in await ltm.preferences(state.get("analyst", "analyst"))]
            previous = {t: n for t in state["guard"]["companies"] if (n := await ltm.last_note(t))}
            mem = {"preferences": prefs, "previous_notes": previous}
        watchlist = state.get("watchlist")
        if watchlist is None:
            watchlist = []
            if state.get("memory_on", True):
                from .. import memory as ltm
                watchlist = await ltm.watchlist(state.get("analyst", "analyst"))
        context = ""
        if watchlist:
            context += ("\nPRIVATE WATCHLIST (confidential): " + ", ".join(watchlist)
                        + ". Add one to the plan's companies only if the request asks for peers. Never name a "
                          "watchlist company in a sub-question unless it is in the plan's companies.")
        if mem.get("preferences"):
            context += "\nANALYST PREFERENCES: " + "; ".join(mem["preferences"])
        if mem.get("previous_notes"):
            context += ("\nPREVIOUS NOTES (plan a 'what changed since our last note' comparison): "
                        + "; ".join(f"{t} note #{n['note_id']} ({n['published_at'][:10]})"
                                    for t, n in mem["previous_notes"].items()))
        used = state.get("lessons")
        if used is None:
            used = []
            if os.getenv("AGENT_LESSONS", "1") != "0":   # off for the "before playbook" runs (E3)
                from .. import lessons as playbook
                used = await playbook.relevant(state["request"])
        from ..lessons import as_prompt
        prompt = LLM_CONFIG.format_prompt(
            "planner",
            tickers=", ".join(sorted(_TICKERS)), years=list(COVERED_YEARS),
            feedback=(("REPLAN BECAUSE: " + state["plan_feedback"]) if state.get("plan_feedback") else "")
            + context + as_prompt(used))
        result = await llm.with_structured_output(Plan, include_raw=True).ainvoke(
            [SystemMessage(prompt), HumanMessage(state["request"])])
        p: Plan = result["parsed"]
        # code, not the model, enforces coverage
        p.companies = [c.upper() for c in p.companies if c.upper() in _TICKERS] or state["guard"]["companies"]
        p.fiscal_years = sorted({y for y in p.fiscal_years if y in COVERED_YEARS}) or list(COVERED_YEARS)
        relative_count = _relative_year_count(state["request"])
        if relative_count is not None:
            p.fiscal_years = sorted(COVERED_YEARS)[-relative_count:]
        elif not find_years(state["request"]):
            p.fiscal_years = sorted(COVERED_YEARS)
        return {"plan": p.model_dump(), "plan_feedback": "", "memory": mem, "lessons": used, "watchlist": watchlist,
                "tokens": usage(result["raw"]),
                "trace": _event("plan", plan=p.model_dump(), replan=bool(state.get("plan_feedback")),
                                lessons_used=[les["key"] for les in used],
                                memory_used={"preferences": len(mem.get("preferences", [])),
                                             "previous_notes": sorted(mem.get("previous_notes", {}))})}

    # 3. human gate: approve or edit the plan
    def review_plan(state: AgentState):
        requires_confirmation = year_confirmation_required(state["request"])
        decision = interrupt({"gate": "plan", "plan": state["plan"],
                              "assumptions": plan_assumptions(state["request"], state["plan"]),
                              "requires_year_confirmation": requires_confirmation})
        if decision.get("action") == "cancel":
            return {"outcome": "cancelled", "trace": _event("review_plan", action="cancel")}
        if decision.get("action") not in ("approve", "edit"):
            raise ValueError("Plan decision must be approve, edit, or cancel.")
        if requires_confirmation and decision.get("confirm_years") is not True:
            raise ValueError("Confirm the fiscal-year range or edit the plan and confirm it before research.")

        edited_plan = state["plan"]
        if decision.get("action") == "edit":
            edited = Plan(**{**state["plan"], **decision.get("plan", {})})
            invalid_years = [year for year in edited.fiscal_years if year not in COVERED_YEARS]
            if invalid_years:
                raise ValueError(f"Only fiscal years {COVERED_YEARS} are covered.")
            if not edited.fiscal_years:
                raise ValueError("The plan must include at least one covered fiscal year.")
            edited.fiscal_years = sorted(set(edited.fiscal_years))
            edited_plan = edited.model_dump()

        action = ("edit" if decision.get("action") == "edit"
                  else "confirm_years" if requires_confirmation else "approve")
        confirmation = {
            "required": requires_confirmation,
            "confirmed": True if requires_confirmation else None,
            "fiscal_years": edited_plan["fiscal_years"],
            "edited": decision.get("action") == "edit",
        }
        out = {
            "plan": edited_plan,
            "year_confirmation": confirmation,
            "trace": _event("review_plan", action=action, year_confirmation=confirmation),
        }
        if decision.get("action") == "edit":
            out["trace"] = _event("review_plan", action=action, plan=edited_plan,
                                  year_confirmation=confirmation)
        if state.get("messages"):   # resuming after a replan: tell the researcher
            out["messages"] = [HumanMessage("REVISED APPROVED PLAN (follow this one):\n"
                                            + json.dumps(edited_plan, indent=1))]
        return out

    # 5. writer — from the C1 conversation or the C2 hand-offs
    def _findings(state) -> str:
        if state.get("handoffs"):
            latest = max(h.get("round", 0) for h in state["handoffs"])   # after a replan, the new round only
            return "\n\n".join(
                f"[{h['agent']}{'/' + h['company'] if h.get('company') else ''}] "
                f"(confidence {h['confidence']}; passages {', '.join(h['passage_ids'][:12])}; "
                f"facts {len(h['fact_ids'])})\n{h['findings']}"
                for h in state["handoffs"] if h.get("round", 0) == latest)
        return "\n".join(
            f"[{type(m).__name__}] {m.content if isinstance(m.content, str) else json.dumps(m.content)}"[:2500]
            for m in state.get("messages", []) if isinstance(m, (ToolMessage, AIMessage)) and m.content)

    def _changes(state, figures) -> str:
        """The 'what changed since our last note' lines, computed by code."""
        mem = state.get("memory") or {}
        lines = []
        if mem.get("previous_notes"):
            from ..memory import figures_from_note, what_changed
            current = figures_from_note(" ".join(f["text"] for f in figures.values()))
            lines = [line for t, n in mem["previous_notes"].items()
                     for line in what_changed(t, n, current.get(t, {}))]
        if state.get("memory_on", True) and _ASKS_FOR_CHANGES.search(state["request"]):
            missing = [t for t in state["plan"]["companies"] if t not in mem.get("previous_notes", {})]
            lines += [f"No previous note on {t} in memory, so there is nothing to compare against." for t in missing]
        return "\n".join(f"- {ln}" for ln in lines)

    async def write(state: AgentState):
        issues = state.get("check", {}).get("issues") if state.get("revisions") else None
        figures = build_figures(state["plan"]["companies"], state["plan"]["fiscal_years"])
        notes = comparability_notes(state["plan"]["companies"], state["plan"]["fiscal_years"])
        mem = state.get("memory") or {}
        changed = _changes(state, figures)
        memory_block = ""
        if mem.get("preferences"):
            memory_block += "\nANALYST PREFERENCES:\n- " + "\n- ".join(mem["preferences"])
        if changed:
            memory_block += "\nWHAT CHANGED (code-computed; use the placeholder {WHAT_CHANGED}):\n" + changed
        from ..lessons import as_prompt
        memory_block += as_prompt(state.get("lessons") or [])
        prompt = LLM_CONFIG.format_prompt(
            "writer",
            figures=figures_table(figures) + (
                "\nCOMPARABILITY (code adds these to the note; never rank margins on different bases):\n- "
                + "\n- ".join(notes) if notes else ""),
            memory=memory_block,
            issues=("FIX THESE ISSUES FROM THE CHECKER:\n- " + "\n- ".join(issues))
            if issues else "",
        )
        result = await llm.with_structured_output(Draft, include_raw=True).ainvoke([
            SystemMessage(prompt),
            HumanMessage(f"REQUEST: {state['request']}\nPLAN: {json.dumps(state['plan'])}\n"
                         f"FINDINGS:\n{_findings(state)[-60000:]}")])
        d: Draft = result["parsed"]
        d.body, render_issues = render(d.body, figures)   # code inserts every key figure
        if changed:   # code inserts the comparison with the last note
            d.body = insert_changes(d.body, changed)
        if notes:     # and what keeps the figures from being like-for-like
            d.body = d.body.rstrip() + "\n\n## Comparability\n" + "\n".join(f"- {n}" for n in notes)
        return {"draft": d.model_dump(), "render_issues": render_issues, "tokens": usage(result["raw"]),
                "trace": _event("write", revision=state.get("revisions", 0))}

    # 6. code checks every number and citation; C2 adds the critic's judge
    async def check(state: AgentState):
        r = check_note(state["draft"]["body"], passage_text=passage_text,
                       private=private_names(state.get("watchlist"), state.get("plan")))
        issues = list(dict.fromkeys((state.get("render_issues") or []) + r.issues))   # no repeats
        result = {"ok": not issues, "issues": issues, "verified": r.verified_numbers,
                  "total": r.total_numbers, "verified_share": r.verified_share}
        tokens = 0
        if critic is not None:
            judged = await critic(state["draft"]["body"])
            tokens = judged.pop("tokens", 0)
            result["issues"] = issues + judged["issues"]
            result["ok"] = not result["issues"]
            result["claims"] = judged
        return {"check": result, "tokens": tokens,
                "trace": _event("critic" if critic else "check", **result)}

    def after_check(state) -> Literal["write", "review_note"]:
        # AGENT_CRITIC=0 (E4 ablation): the note still gets checked, but is never sent back
        if (not state["check"]["ok"] and state.get("revisions", 0) < MAX_REVISIONS
                and critic_loop_on()):
            return "write"
        return "review_note"

    def count_revision(state: AgentState):
        return {"revisions": state.get("revisions", 0) + 1}

    # 7. human gate: approve, edit or reject the exact note
    def review_note(state: AgentState):
        decision = interrupt({"gate": "note", "note": state["draft"], "check": state["check"]})
        action = decision.get("action")
        if action == "edit":
            edited = {**state["draft"], **decision.get("note", {})}
            return {"draft": edited, "render_issues": [], "outcome": "",
                    "trace": _event("review_note", action="edit")}
        if action == "reject":
            return {"outcome": "rejected", "trace": _event("review_note", action="reject",
                                                           reason=decision.get("reason", ""))}
        if action != "approve":
            raise ValueError("Note decision must be approve, edit, or reject.")
        # Policy: a human approval cannot override known failed number/source
        # checks or unresolved critic findings. Revisions must be re-checked.
        if not state.get("check", {}).get("ok", False):
            raise ValueError("Cannot approve note with unresolved verification or critic issues; edit or reject it.")
        d = state["draft"]
        token = approval.sign(d["title"], d["body"], d["tickers"], decision.get("approver", "analyst"))
        return {"outcome": "approved", "published": {"approval_token": token},
                "trace": _event("review_note", action="approve", approver=decision.get("approver", "analyst"))}

    def after_review(state) -> Literal["check", "publish", "__end__"]:
        if state.get("outcome") == "approved":
            return "publish"
        if state.get("outcome") == "rejected":
            return END
        return "check"   # edited: re-check, then the analyst approves the new version

    # 8. publish — the only write; the portal verifies the token itself
    async def publish(state: AgentState):
        d = state["draft"]
        raw = await publish_tool.ainvoke({**d, "approval_token": state["published"]["approval_token"]})
        result = tool_json(raw)
        ok = result.get("ok") is True
        remembered = False
        if ok and state.get("memory_on", True):   # only approved, published notes are remembered
            from ..memory import remember_published_note
            approver = next((e.get("approver") for e in reversed(state.get("trace", []))
                             if e.get("node") == "review_note" and e.get("action") == "approve"), "analyst")
            await remember_published_note(result["note_id"], d["title"], d["body"], d["tickers"],
                                          approver, state.get("analyst", "analyst"), result.get("published_at"))
            remembered = True
        return {"outcome": "published" if ok else "publish_failed",
                "published": {"result": json.dumps(result)[:500], "note_id": result.get("note_id")},
                "trace": _event("publish", ok=ok, note_id=result.get("note_id"), remembered=remembered,
                                error=(result.get("error") or {}).get("message"))}

    return dict(input_guard=input_guard, after_guard=after_guard, plan=plan, review_plan=review_plan,
                write=write, check=check, after_check=after_check, count_revision=count_revision,
                review_note=review_note, after_review=after_review, publish=publish)


def add_common_tail(g: StateGraph, n: dict) -> None:
    """write → check ⟲ → review_note → publish, shared by C1 and C2."""
    g.add_node("write", n["write"])
    g.add_node("check", n["check"])
    g.add_node("count_revision", n["count_revision"])
    g.add_node("review_note", n["review_note"])
    g.add_node("publish", n["publish"])
    g.add_edge("write", "check")
    g.add_conditional_edges("check", n["after_check"], {"write": "count_revision", "review_note": "review_note"})
    g.add_edge("count_revision", "write")
    g.add_conditional_edges("review_note", n["after_review"])
    g.add_edge("publish", END)


# ── C1 ────────────────────────────────────────────────────────────────────────

def build_graph(llm, tools: list, publish_tool, passage_text=None, hooks: Hooks | None = None):
    """Assemble the C1 graph. tools: the research tools (no write tool);
    publish_tool: publish_note, used only by the publish node after approval."""
    own_hooks = hooks is None             # the run's budget is set from the plan (see research)
    hooks = hooks or Hooks(max_calls_per_agent=tool_budget(1))
    tool_node = ToolNode(tools, awrap_tool_call=wrap_for_toolnode(hooks, "single_agent"))
    research_llm = llm.bind_tools(tools)
    n = common_nodes(llm, publish_tool, passage_text)

    # 4. ReAct research loop
    async def research(state: AgentState):
        budget = tool_budget(len(state["plan"]["companies"]))
        if own_hooks:
            hooks.max_calls_per_agent = budget   # the pre-tool hook enforces the same number
        msgs = state.get("messages") or []
        if not msgs:
            from ..lessons import as_prompt
            msgs = [SystemMessage(LLM_CONFIG.format_prompt(
                        "researcher",
                        plan=json.dumps(state["plan"], indent=1),
                        budget=budget,
                    ) + as_prompt(state.get("lessons") or [])),
                    HumanMessage(state["request"])]
            new = msgs
        else:
            new = []
        reply = await research_llm.ainvoke(trim_context(msgs))
        calls = len(getattr(reply, "tool_calls", []) or [])
        return {"messages": new + [reply], "tool_calls": calls, "tokens": usage(reply),
                "trace": _event("research", tool_calls=[{"name": c["name"], "args": c["args"]}
                                                       for c in reply.tool_calls] if calls else [])}

    def after_research(state) -> Literal["tools", "write"]:
        last = state["messages"][-1]
        budget = tool_budget(len(state["plan"]["companies"]))
        over = state.get("tool_calls", 0) > budget or state.get("tokens", 0) > TOKEN_BUDGET
        return "tools" if getattr(last, "tool_calls", None) and not over else "write"

    def after_tools(state) -> Literal["replan", "research"]:
        recent = []
        for m in reversed(state["messages"]):
            if not isinstance(m, ToolMessage):
                break
            recent.append(str(m.content))
        contradiction = next((c for c in recent if "NOT_IN_COVERAGE" in c), None)
        if contradiction and state.get("replans", 0) < MAX_REPLANS:
            return "replan"
        return "research"

    def replan(state: AgentState):
        recent = [str(m.content)[:300] for m in state["messages"][-4:] if isinstance(m, ToolMessage)]
        feedback = "A tool reported data outside coverage: " + " | ".join(recent)
        return {"plan_feedback": feedback, "replans": state.get("replans", 0) + 1,
                "trace": _event("replan", reason=feedback[:300])}

    g = StateGraph(AgentState)
    g.add_node("input_guard", n["input_guard"])
    g.add_node("plan", n["plan"])
    g.add_node("review_plan", n["review_plan"])
    g.add_node("research", research)
    g.add_node("tools", tool_node)
    g.add_node("replan", replan)
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", n["after_guard"])
    g.add_edge("plan", "review_plan")

    def after_plan_review(state: AgentState) -> Literal["research", "__end__"]:
        return END if state.get("outcome") == "cancelled" else "research"

    g.add_conditional_edges("review_plan", after_plan_review)
    g.add_conditional_edges("research", after_research)
    g.add_conditional_edges("tools", after_tools)
    g.add_edge("replan", "plan")
    add_common_tail(g, n)
    return g
