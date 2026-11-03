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
  checks each cited claim against its passage.
* Same model, same tools and the same budgets as C1, so E1 compares the
  orchestration only.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from .checks import PASSAGE_ID
from .graph import (MAX_REPLANS, TOKEN_BUDGET, AgentState, _event, add_common_tail,
                    common_nodes, trim_context, usage)
from .hooks import Hooks
from ..llm_config import LLM_CONFIG

CALLS_PER_SPECIALIST = {"researcher": 6, "quant": 14, "risk_diff": 6}
_FACT_ID = re.compile(r"[A-Za-z]+/\d{4}/\d{10}-\d{2}-\d{6}")


class HandoffMessage(BaseModel):
    """What every specialist hands back to the research lead."""
    agent: str
    company: str | None = None
    findings: str = Field(description="The specialist's summary, citing ids")
    passage_ids: list[str] = Field(default_factory=list, description="Passages it read (from tool results)")
    fact_ids: list[str] = Field(default_factory=list, description="XBRL facts it used (from tool results)")
    confidence: Literal["high", "medium", "low"] = "medium"
    tool_calls: int = 0
    errors: list[str] = Field(default_factory=list)
    round: int = 0


# ── specialist runner ─────────────────────────────────────────────────────────

async def run_specialist(agent: str, company: str | None, llm, tools_by_name: dict, system: str,
                         hooks: Hooks, budget: int, emit=None) -> tuple[HandoffMessage, int]:
    """A small ReAct loop for one specialist; every tool call goes through the hooks."""
    allowed = [tools_by_name[n] for n in sorted(hooks.allowed[agent]) if n in tools_by_name]
    bound = llm.bind_tools(allowed)
    who = f"{agent}/{company}" if company else agent
    msgs = [SystemMessage(system), HumanMessage("Begin.")]
    tokens = calls = 0
    passages, facts, errors = [], [], []
    for _ in range(budget + 2):
        reply = await bound.ainvoke(trim_context(msgs))
        tokens += usage(reply)
        msgs.append(reply)
        if not reply.tool_calls:
            break
        for call in reply.tool_calls:
            start = time.perf_counter()
            denial = await hooks.pre(agent, call["name"], who)
            if denial:
                content = json.dumps(denial)
            else:
                calls += 1
                raw = await tools_by_name[call["name"]].ainvoke(call["args"])
                content = raw if isinstance(raw, str) else json.dumps(raw)
            event = hooks.post(who, call["name"], call["args"], content,
                               (time.perf_counter() - start) * 1000, bool(denial))
            if emit:
                emit(event)
            if not event["ok"] and event["error"]:
                errors.append(event["error"])
            passages += PASSAGE_ID.findall(content)
            facts += _FACT_ID.findall(content)
            msgs.append(ToolMessage(content, tool_call_id=call["id"], name=call["name"]))
    findings = msgs[-1].content if isinstance(msgs[-1], AIMessage) else ""
    confidence = "high" if not errors and (passages or facts) else ("low" if not (passages or facts) else "medium")
    handoff = HandoffMessage(agent=agent, company=company, findings=str(findings)[:6000],
                             passage_ids=sorted(set(passages)), fact_ids=sorted(set(facts)),
                             confidence=confidence, tool_calls=calls, errors=sorted(set(errors)))
    return handoff, tokens


# ── compliance critic: the judge part ─────────────────────────────────────────

def make_judge(judge_llm, passage_text):
    """async critic(body) -> {"issues", "checked", "supported", "model", "tokens"}."""
    async def critic(body: str) -> dict:
        items = []
        for line in body.splitlines():
            pids = PASSAGE_ID.findall(line)
            text = re.sub(r"\[(fact|calc):[^\]]*\]", "", line).strip(" -*#")
            if pids and len(text) > 30:
                src = "\n".join(f"[{p}] {(passage_text(p) or '(missing)')[:900]}" for p in pids[:2])
                items.append((text[:500], src))
        items = items[:10]
        if not items:
            return {"issues": [], "checked": 0, "supported": 0,
                    "model": LLM_CONFIG.model("judge"), "tokens": 0}
        prompt = "\n\n".join(f"ITEM {i}\nCLAIM: {c}\nPASSAGES:\n{s}" for i, (c, s) in enumerate(items, 1))
        try:
            reply = await judge_llm.ainvoke([
                SystemMessage(LLM_CONFIG.prompt("judge")), HumanMessage(prompt)
            ])
            raw = reply.content if isinstance(reply.content, str) else json.dumps(reply.content)
            verdicts = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])["verdicts"]
        except Exception as exc:   # noqa: BLE001 — a judge failure must not block the note
            return {"issues": [], "checked": len(items), "supported": None,
                    "model": LLM_CONFIG.model("judge"),
                    "error": f"judge unavailable: {type(exc).__name__}", "tokens": 0}
        unsupported = [v for v in verdicts if not v.get("supported")]
        issues = [f"Claim not supported by its cited passage (judge): \"{items[v['i'] - 1][0][:160]}\" — "
                  f"{v.get('reason', '')}" for v in unsupported if 1 <= v.get("i", 0) <= len(items)]
        return {"issues": issues, "checked": len(items), "supported": len(items) - len(unsupported),
                "model": LLM_CONFIG.model("judge"), "tokens": usage(reply)}
    return critic


def make_judge_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=LLM_CONFIG.model("judge"), base_url="https://openrouter.ai/api/v1",
                      api_key=os.environ["OPENROUTER_API_KEY"], temperature=0, timeout=120)


# ── graph ─────────────────────────────────────────────────────────────────────

def build_team_graph(llm, tools: list, publish_tool, passage_text=None, judge_llm=None,
                     hooks: Hooks | None = None):
    hooks = hooks or Hooks(max_calls_per_agent=max(CALLS_PER_SPECIALIST.values()))
    tools_by_name = {t.name: t for t in tools}
    critic = make_judge(judge_llm, passage_text or (lambda pid: None)) if judge_llm else None
    n = common_nodes(llm, publish_tool, passage_text, critic=critic)

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
        base = {"plan": plan, "round": state.get("replans", 0), "lessons": state.get("lessons") or []}
        sends = [Send("researcher", {**base, "company": t}) for t in plan["companies"]]
        sends.append(Send("quant", base))
        sends += [Send("risk_diff", {**base, "company": t}) for t in plan["companies"]]
        return sends

    def _specialist(agent: str):
        async def node(task: dict):
            plan, company = task["plan"], task.get("company")
            years = plan["fiscal_years"]
            prompt_name = {
                "researcher": "specialist_researcher",
                "quant": "specialist_quant",
                "risk_diff": "specialist_risk_diff",
            }[agent]
            system = LLM_CONFIG.format_prompt(
                prompt_name,
                company=company, companies=", ".join(plan["companies"]), years=years,
                latest=max(years), prior=max(years) - 1, budget=CALLS_PER_SPECIALIST[agent],
                plan=json.dumps(plan))
            from ..lessons import as_prompt
            system += as_prompt(task.get("lessons") or [])
            budgeted = Hooks(max_calls_per_agent=CALLS_PER_SPECIALIST[agent], allowed=hooks.allowed,
                             calls=hooks.calls, events=hooks.events)
            handoff, tokens = await run_specialist(agent, company, llm, tools_by_name, system,
                                                   budgeted, CALLS_PER_SPECIALIST[agent], _emit())
            handoff.round = task.get("round", 0)
            h = handoff.model_dump()
            who = f"{agent}/{company}" if company else agent
            # this agent's hook events, kept in the run's history (live ones only stream)
            tools_log = [{k: e[k] for k in ("tool", "args", "ok", "error", "ms", "denied")}
                         for e in hooks.events if e["agent"] == who]
            return {"handoffs": [h], "tool_calls": handoff.tool_calls, "tokens": tokens,
                    "trace": _event("handoff", agent=agent, company=company, confidence=h["confidence"],
                                    passages=len(h["passage_ids"]), facts=len(h["fact_ids"]),
                                    tool_calls=h["tool_calls"], errors=h["errors"], tools=tools_log)}
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
