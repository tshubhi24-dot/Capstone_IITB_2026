"""C2 — the team: a research lead, parallel specialists and a compliance critic (L11).

    START → input_guard → plan → review_plan ─fan-out (Send, in parallel)─┐
        researcher[T]   one per company: MD&A drivers from filings-kb      │
        quant           all companies: XBRL facts, ratios in the sandbox   │
        risk_diff[T]    one per company: Item 1A, latest year vs prior     │
      ◄─────────────────── typed HandoffMessage from each ────────────────┘
    → gather ─(a specialist hit NOT_IN_COVERAGE)→ replan → plan
             → write → critic ─(issues, max 2)→ write
             → review_note → publish (publisher holds the only write tool)

* Each specialist is its own small ReAct loop over only its own tools
  (servers.AGENT_TOOLS), with its own tool budget. Every call goes through
  the hooks: permission, budget and EDGAR rate limit before; trace after.
* Specialists return a typed HandoffMessage. Its passage_ids and fact_ids
  are extracted by code from the tool results, not claimed by the model.
* The compliance critic = the code checks (numbers vs XBRL facts, quotes vs
  passages, advice wording) + a judge from a different model family that
  checks every cited claim against its passage. A claim the judge could not
  review leaves the review incomplete, which blocks approval.
* Same model, same tools and the same total tool budget as C1
  (graph.tool_budget, split across the specialists by specialist_budgets),
  so E1 compares the orchestration only.
"""

from __future__ import annotations

import json
import os
import re
import time
from itertools import combinations
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from ..servers import quarantine   # Fix for Module 4 - Security (Fix 3)
from .checks import PASSAGE_ID
from .guards import screen
from .graph import (MAX_REPLANS, TOKEN_BUDGET, AgentState, _event, add_common_tail,
                    common_nodes, tool_budget, trim_context, usage)
from .hooks import Hooks
from ..llm_config import LLM_CONFIG, max_output_tokens

def specialist_budgets(n_companies: int) -> dict[str, int]:
    """Split the run's tool budget (the same total C1 gets) across the team.

    The quant needs 3 get_financials calls per company plus room for run_python, including a
    retry when the sandbox fails (live run 0c8cbf5f: two TIMEOUTs, no call left), so it is
    reserved 3 per company + 3. The rest is shared evenly by the researcher and the risk-diff of
    each company; any remainder goes to the quant. The shares always add up to
    tool_budget(n_companies): 1 company -> 9 + 9, quant 6; 2 companies -> 6 + 6 per company, quant 12.
    """
    n = max(1, n_companies)
    total = tool_budget(n)
    each = max(1, (total - (3 * n + 3)) // (2 * n))
    return {"researcher": each, "risk_diff": each, "quant": max(1, total - 2 * n * each)}

_FACT_ID = re.compile(r"[A-Za-z]+/\d{4}/\d{10}-\d{2}-\d{6}")


def risk_years(years: list[int]) -> tuple[int, int] | None:
    """(latest, prior) for the risk-diff: the plan's latest year and the plan's previous one
    (FY2022 vs FY2024 when those two were asked for), else latest - 1 if that year is covered.
    None when there is no covered earlier year (a FY2022-only plan)."""
    from ..servers.common import COVERED_YEARS
    latest = max(years)
    prior = max((y for y in years if y < latest), default=latest - 1)
    return (latest, prior) if prior in COVERED_YEARS else None


class RiskPairCoverage(BaseModel):
    company: str
    earlier_year: int
    later_year: int
    earlier_passages: list[str]
    later_passages: list[str]
    status: Literal["missing_evidence", "excerpt_only"]


def risk_pair_coverage(company: str, years: list[int], claims: list[dict]) -> list[RiskPairCoverage]:
    ids = {c["passage_id"] for c in claims}
    ordered = sorted(set(years))
    result = []
    for earlier, later in combinations(ordered, 2):
        before = sorted(p for p in ids if p.startswith(f"{company}_{earlier}_item1a_"))
        after = sorted(p for p in ids if p.startswith(f"{company}_{later}_item1a_"))
        result.append(RiskPairCoverage(company=company, earlier_year=earlier, later_year=later,
                                       earlier_passages=before, later_passages=after,
                                       status="excerpt_only" if before and after else "missing_evidence"))
    return result


class HandoffMessage(BaseModel):
    """What every specialist hands back to the research lead.

    Fix for Module 4 - Security (Fix 3 - use cases 3 and 4): there is no
    free-text field. `claims` are spans copied out of the passage each cites
    and checked against it by code; `facts` carry values code read from XBRL,
    never numbers the model typed. Nothing a specialist wrote in its own words
    reaches the writer.
    """
    agent: str
    company: str | None = None
    claims: list[dict] = Field(default_factory=list,
                               description="Verified filing spans (quarantine.PassageClaim)")
    facts: list[dict] = Field(default_factory=list,
                              description="fact_id plus the value code looked up")
    dropped: list[str] = Field(default_factory=list,
                               description="Claims code refused, counted at the gate")
    passage_ids: list[str] = Field(default_factory=list, description="Passages it read (from tool results)")
    fact_ids: list[str] = Field(default_factory=list, description="XBRL facts it used (from tool results)")
    risk_coverage: list[RiskPairCoverage] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    tool_calls: int = 0
    errors: list[str] = Field(default_factory=list)
    round: int = 0
    # Cost of this specialist (L11 metering): what it read and spent, per agent
    tokens: int = 0
    model_calls: int = 0
    largest_prompt: int = Field(0, description="Largest single prompt it read, in tokens")


# ── specialist runner ─────────────────────────────────────────────────────────

# Fix for Module 4 - Security (Fix 3 - use cases 3 and 4): passage_text is injected
# the way check_note takes it, so verifying a quote needs no Chroma index.
async def run_specialist(agent: str, company: str | None, llm, tools_by_name: dict, system: str,
                         hooks: Hooks, budget: int, emit=None,
                         context: dict | None = None,
                         passage_text=None) -> tuple[HandoffMessage, int]:
    """A small ReAct loop for one specialist; every tool call goes through the hooks.

    context: {"plan", "watchlist"} of the run, for the hooks' watchlist check.
    """
    allowed = [tools_by_name[n] for n in sorted(hooks.allowed[agent]) if n in tools_by_name]
    bound = llm.bind_tools(allowed)
    who = f"{agent}/{company}" if company else agent
    msgs = [SystemMessage(system), HumanMessage("Begin.")]
    tokens = calls = model_calls = largest_prompt = 0
    passages, facts, errors = [], [], []
    for _ in range(budget + 2):
        reply = await bound.ainvoke(trim_context(msgs))
        tokens += usage(reply)
        model_calls += 1
        prompt = int((getattr(reply, "usage_metadata", None) or {}).get("input_tokens", 0))
        largest_prompt = max(largest_prompt, prompt)
        msgs.append(reply)
        if not reply.tool_calls:
            break
        for call in reply.tool_calls:
            start = time.perf_counter()
            denial = await hooks.pre(agent, call["name"], who, args=call["args"], context=context)
            if not denial and call["name"] not in tools_by_name:   # e.g. get_past_notes in a memory-off run
                denial = {"ok": False, "error": {"code": "NOT_AVAILABLE",
                                                 "message": f"{call['name']} is not available in this run"}}
            withheld = 0
            if denial:
                content = json.dumps(denial)
            else:
                calls += 1
                raw = await tools_by_name[call["name"]].ainvoke(call["args"])
                content, withheld = screen(raw if isinstance(raw, str) else json.dumps(raw))
            event = hooks.post(who, call["name"], call["args"], content,
                               (time.perf_counter() - start) * 1000, bool(denial), withheld)
            if emit:
                emit(event)
            if not event["ok"] and event["error"]:
                errors.append(event["error"])
            passages += PASSAGE_ID.findall(content)
            facts += _FACT_ID.findall(content)
            msgs.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))
    # Fix for Module 4 - Security (Fix 3 - use cases 3 and 4): one more turn, for
    # fields instead of prose. Whatever the model says here is checked before any
    # of it crosses, and a failure to produce the typed shape hands back nothing —
    # the safe direction, because an empty hand-off starves the writer rather than
    # feeding it unchecked text.
    claims, verified_facts, dropped = [], [], []
    ask = quarantine.ask_for(agent)
    if ask:
        try:
            out = await llm.with_structured_output(quarantine.Handoff).ainvoke(
                trim_context(msgs) + [HumanMessage(ask)])
            kept, dropped = quarantine.verify_passages(out.claims, passage_text)
            claims = [c.model_dump() for c in kept]
            pairs, fact_drops = quarantine.verify_facts(out.facts)
            verified_facts = [{"fact_id": f, "value_usd": v} for f, v in pairs]
            dropped += fact_drops
        except Exception as exc:   # noqa: BLE001 — recorded, and nothing crosses
            dropped.append(f"hand-off could not be typed: {type(exc).__name__}")

    survived = len(claims) + len(verified_facts)
    confidence = "high" if not errors and survived else ("low" if not survived else "medium")
    coverage = []
    if agent == "risk_diff" and company and context:
        coverage = risk_pair_coverage(company, (context.get("plan") or {}).get("fiscal_years") or [], claims)
        if any(pair.status == "missing_evidence" for pair in coverage):
            confidence = "low"
        elif coverage and confidence == "high":
            confidence = "medium"
    handoff = HandoffMessage(agent=agent, company=company, claims=claims, facts=verified_facts,
                             dropped=dropped, passage_ids=sorted(set(passages)),
                             risk_coverage=coverage,
                             fact_ids=sorted(set(facts)), confidence=confidence,
                             tool_calls=calls, errors=sorted(set(errors)),
                             tokens=tokens, model_calls=model_calls, largest_prompt=largest_prompt)
    return handoff, tokens


# ── compliance critic: the judge part ─────────────────────────────────────────

JUDGE_BATCH = 10
_TAGS = re.compile(r"\[(fact|calc|growth|diff):[^\]]*\]")
# A figure code rendered and verified against XBRL ($245,122.0M [fact: ...], 44.64% [calc: ...]).
# The judge sees a marker instead: it judges the wording against the passage, not a number
# the passage was never meant to state.
_VERIFIED_FIGURE = re.compile(r"-?\$?\s?[\d,]+(?:\.\d+)?\s?(?:[MB]|%|pp)?\s*\[(?:fact|calc|growth|diff):[^\]]*\]")
VERIFIED_MARK = "[code-verified figure]"
_STRUCTURAL_HEADINGS = {
    "summary", "overview", "comparability", "limitations", "risks", "risk factors",
    "financials", "financial performance", "margins", "drivers", "conclusion", "sources",
    "what changed", "what changed since our last note",
}
_TABLE_SEPARATOR = re.compile(r"^\|?[\s:|-]+\|?$")


def claim_lines(body: str) -> tuple[list[tuple[str, list[str]]], int]:
    """Conservatively inventory text, including titles, headings and table rows.

    Only exact structural headings and Markdown separators are exempt. A section
    name cannot establish that its contents were generated or verified by code.
    """
    cited, uncited = _inventory(body)
    return cited, len(uncited)


def uncited_lines(body: str) -> list[str]:
    """The lines that count as uncited, as the analyst sees them (for the note gate)."""
    return _inventory(body)[1]


def _inventory(body: str) -> tuple[list[tuple[str, list[str]]], list[str]]:
    cited, uncited = [], []
    for line in body.splitlines():
        s = line.strip()
        if not s or _TABLE_SEPARATOR.fullmatch(s):
            continue
        heading = re.sub(r"^#{1,6}\s*", "", s).strip().lower()
        if s.startswith("#") and heading in _STRUCTURAL_HEADINGS:
            continue
        pids = PASSAGE_ID.findall(s)
        text = _TAGS.sub("", _VERIFIED_FIGURE.sub(
            lambda match: VERIFIED_MARK + " [XBRL sources: " + ", ".join(_FACT_ID.findall(match.group())) + "]",
            s)).strip(" -*")
        if pids:
            cited.append((text, pids))
        elif any(ch.isalnum() for ch in text.replace(VERIFIED_MARK, "")):
            uncited.append(s)
    return cited, uncited


def make_judge(judge_llm, passage_text):
    """async critic(body) -> {"issues", "checked", "reviewed", "supported", "uncited", "model", "tokens"}.

    Every cited claim is judged, in batches of JUDGE_BATCH. Each claim needs exactly one
    true/false verdict; a claim left without one (judge down, malformed or missing
    verdict) makes the review incomplete, which is an issue: approval stays unavailable
    until a re-check completes it. A missing verdict is never counted as supported.
    """
    async def critic(body: str, trusted_suffix: str = "", fact_evidence: dict | None = None) -> dict:
        if trusted_suffix and body.endswith(trusted_suffix):
            body = body[:-len(trusted_suffix)]
        lines, uncited_list = _inventory(body)
        uncited = len(uncited_list)
        items = []
        invalid: dict[int, str] = {}
        for index, (text, pids) in enumerate(lines):
            passages = [(pid, passage_text(pid)) for pid in dict.fromkeys(pids)]
            missing = [pid for pid, passage in passages if not passage]
            source = "\n".join(f"[{pid}] {passage}" for pid, passage in passages)
            for fid in dict.fromkeys(_FACT_ID.findall(text)):
                if fact_evidence and fid in fact_evidence:
                    source += f"\n[XBRL {fid}] {json.dumps(fact_evidence[fid], sort_keys=True)}"
                else:
                    invalid[index] = "cited XBRL fact not found in evidence snapshot"
            items.append((text, source))
            if missing:
                invalid[index] = "cited passage not found"
            elif len(text) > 4000 or len(source) > 16000:
                invalid[index] = "claim or cited evidence exceeds the review limit"
        verdict: dict[int, dict] = {}
        tokens, errors = 0, []
        for start in range(0, len(items), JUDGE_BATCH):
            batch = [(i, *items[i]) for i in range(start, min(start + JUDGE_BATCH, len(items)))
                     if i not in invalid]
            if not batch:
                continue
            prompt = "\n\n".join(f"ITEM {i}\nCLAIM: {c}\nPASSAGES:\n{s}"
                                  for i, (_, c, s) in enumerate(batch, 1))
            try:
                reply = await judge_llm.ainvoke([SystemMessage(LLM_CONFIG.prompt("judge")), HumanMessage(prompt)])
                tokens += usage(reply)
                raw = reply.content if isinstance(reply.content, str) else json.dumps(reply.content)
                got = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["verdicts"]
                if not isinstance(got, list):
                    raise ValueError("verdicts must be a list")
            except Exception as exc:   # noqa: BLE001 — recorded below as an incomplete review
                errors.append(f"judge unavailable: {type(exc).__name__}")
                continue
            duplicate = set()
            for v in got:
                i = v.get("i") if isinstance(v, dict) else None
                if type(i) is int and 1 <= i <= len(batch):
                    key = batch[i - 1][0]
                    if key in verdict or key in duplicate:
                        verdict.pop(key, None)
                        duplicate.add(key)
                    elif isinstance(v.get("supported"), bool):
                        verdict[key] = v
        issues = [f"Claim not supported by its cited passage (judge): \"{items[k][0][:160]}\" — "
                  f"{v.get('reason', '')}" for k, v in sorted(verdict.items()) if not v["supported"]]
        missing = len(items) - len(verdict)
        if missing:
            if invalid:
                errors.append(next(iter(invalid.values())))
            issues.append(f"Review incomplete: the judge gave no valid verdict for {missing} of {len(items)} "
                          f"cited claims{' (' + errors[0] + ')' if errors else ''}. Re-check before approval.")
        if uncited:
            issues.append(f"Review incomplete: {uncited} substantive line(s) lack a passage citation. "
                          "Add supporting evidence or remove the unsupported claims before approval.")
        out = {"issues": issues, "checked": len(items), "reviewed": len(verdict),
               "supported": sum(v["supported"] for v in verdict.values()), "uncited": uncited,
               "uncited_lines": [line[:300] for line in uncited_list[:40]],
               "model": LLM_CONFIG.model("judge"), "tokens": tokens}
        if errors:
            out["error"] = errors[0]
        return out
    return critic


def make_judge_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=LLM_CONFIG.model("judge"), base_url="https://openrouter.ai/api/v1",
                      api_key=os.environ["OPENROUTER_API_KEY"], temperature=0, timeout=120,
                      max_tokens=max_output_tokens() or LLM_CONFIG.max_output_tokens)


# ── graph ─────────────────────────────────────────────────────────────────────

def build_team_graph(llm, tools: list, publish_tool, passage_text=None, judge_llm=None,
                     hooks: Hooks | None = None, require_critic=False):
    hooks = hooks or Hooks()      # shares permissions and logs; each specialist gets its own budget
    tools_by_name = {t.name: t for t in tools}
    critic = make_judge(judge_llm, passage_text or (lambda pid: None)) if judge_llm else None
    n = common_nodes(llm, publish_tool, passage_text, critic=critic, require_critic=require_critic)

    def _emit():
        try:
            from langgraph.config import get_stream_writer
            writer = get_stream_writer()
            return lambda ev: writer(ev)
        except Exception:   # noqa: BLE001 — outside a streaming run
            return None

    def fan_out(state: AgentState) -> list[Send] | str:
        """Parallel fan-out: one researcher and one risk-diff per company, one quant."""
        if state.get("outcome") == "cancelled":
            return END
        plan = state["plan"]
        base = {"plan": plan, "round": state.get("replans", 0), "lessons": state.get("lessons") or [],
                "watchlist": state.get("watchlist") or []}
        sends = [Send("researcher", {**base, "company": t}) for t in plan["companies"]]
        sends.append(Send("quant", base))
        # risk-diff needs a covered earlier year to compare with: a FY2022-only plan has none
        # (FY2021 is not covered), and searching it would trip NOT_IN_COVERAGE and a needless replan
        if risk_years(plan["fiscal_years"]):
            sends += [Send("risk_diff", {**base, "company": t}) for t in plan["companies"]]
        return sends

    def _specialist(agent: str):
        async def node(task: dict):
            plan, company = task["plan"], task.get("company")
            years = plan["fiscal_years"]
            latest, prior = risk_years(years) or (max(years), max(years))
            budget = specialist_budgets(len(plan["companies"]))[agent]
            prompt_name = {
                "researcher": "specialist_researcher",
                "quant": "specialist_quant",
                "risk_diff": "specialist_risk_diff",
            }[agent]
            system = LLM_CONFIG.format_prompt(
                prompt_name,
                company=company, companies=", ".join(plan["companies"]), years=years,
                latest=latest, prior=prior, budget=budget,
                plan=json.dumps(plan))
            if agent == "risk_diff":
                system += ("\nCover every requested fiscal-year pair, not only the latest pair. "
                           "Retrieve and quote Item 1A passages for every requested year. Excerpts do not "
                           "establish section-wide absence, additions, removals or unchanged risks.")
                if len(set(years)) < 2:
                    system += " Only one year was requested: do not infer a comparison with another year."
            from ..lessons import as_prompt
            system += as_prompt(task.get("lessons") or [])
            budgeted = Hooks(max_calls_per_agent=budget, allowed=hooks.allowed,
                             calls=hooks.calls, events=hooks.events)
            # Fix for Module 4 - Security (Fix 3 - use cases 3 and 4): passage_text
            handoff, tokens = await run_specialist(agent, company, llm, tools_by_name, system,
                                                   budgeted, budget, _emit(),
                                                   context={"plan": plan,
                                                            "watchlist": task.get("watchlist")},
                                                   passage_text=passage_text)
            handoff.round = task.get("round", 0)
            h = handoff.model_dump()
            who = f"{agent}/{company}" if company else agent
            # this agent's hook events, kept in the run's history (live ones only stream)
            tools_log = [{k: e.get(k) for k in ("tool", "args", "ok", "error", "ms", "denied", "withheld",
                                                "result")}
                         for e in hooks.events if e["agent"] == who]
            return {"handoffs": [h], "tool_calls": handoff.tool_calls, "tokens": tokens,
                    "trace": _event("handoff", agent=agent, company=company, confidence=h["confidence"],
                                    passages=len(h["passage_ids"]), facts=len(h["fact_ids"]),
                                    # Fix for Module 4 - Security (Fix 3): what crossed
                                    quotes=len(h["claims"]), dropped=h["dropped"],
                                    tool_calls=h["tool_calls"], errors=h["errors"], tools=tools_log,
                                    tokens=h["tokens"], model_calls=h["model_calls"],
                                    largest_prompt=h["largest_prompt"], budget=budget)}
        return node

    def gather(state: AgentState):
        current = [h for h in state.get("handoffs", []) if h.get("round", 0) == state.get("replans", 0)]
        return {"trace": _event("gather", handoffs=len(current),
                                over_budget=state.get("tokens", 0) > TOKEN_BUDGET)}

    def after_gather(state) -> Literal["replan", "write"]:
        current = [h for h in state.get("handoffs", []) if h.get("round", 0) == state.get("replans", 0)]
        if any("NOT_IN_COVERAGE" in h["errors"] for h in current) and state.get("replans", 0) < MAX_REPLANS:
            return "replan"
        return "write"

    def replan(state: AgentState):
        current = [h for h in state.get("handoffs", []) if h.get("round", 0) == state.get("replans", 0)]
        bad = [f"{h['agent']}/{h.get('company') or 'all'}" for h in current if "NOT_IN_COVERAGE" in h["errors"]]
        feedback = f"Specialists reported data outside coverage: {', '.join(bad)}. Keep to covered companies and years."
        return {"plan_feedback": feedback, "replans": state.get("replans", 0) + 1,
                "trace": _event("replan", reason=feedback)}

    g = StateGraph(AgentState)
    g.add_node("input_guard", n["input_guard"])
    g.add_node("plan", n["plan"])
    g.add_node("review_plan", n["review_plan"])
    for agent in ("researcher", "quant", "risk_diff"):
        g.add_node(agent, _specialist(agent))
    g.add_node("gather", gather)
    g.add_node("replan", replan)
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", n["after_guard"])
    g.add_edge("plan", "review_plan")
    g.add_conditional_edges("review_plan", fan_out, ["researcher", "quant", "risk_diff", END])
    for agent in ("researcher", "quant", "risk_diff"):
        g.add_edge(agent, "gather")
    g.add_conditional_edges("gather", after_gather)
    g.add_edge("replan", "plan")
    add_common_tail(g, n)
    return g
