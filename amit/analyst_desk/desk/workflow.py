"""Fresh step-four teaching graph: real MCP tools, persistent human pauses.

This first journey is deterministic offline research. It performs no LLM calls
and does not claim learned retrieval or semantic risk judgments.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
import json
import operator
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from typing import Annotated, TypedDict

from fastmcp import Client
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, Send, interrupt

from .store import canonical_hash


class ReviewError(ValueError):
    pass


class State(TypedDict, total=False):
    run_id: str
    actor: str
    request: dict
    plan: dict
    plan_action: str
    ticker: str
    findings: Annotated[list[dict], operator.add]
    metrics: list[dict]
    risks: list[dict]
    draft: dict
    critic: dict
    repairs: int
    human_edited: bool
    status: str
    note_id: str
    capability: str


def numeric_table(rows):
    lines = ["| Company | FY | Actual period | Revenue (USD) | Operating income (USD) | Margin | Sources |",
             "|---|---|---|---:|---:|---:|---|"]
    for row in rows:
        refs = " ".join(f"[{ref}]" for ref in row["fact_ids"])
        lines.append(f"| {row['ticker']} | {row['year']} | {row['period_start']} to {row['period_end']} | {row['revenue']} | {row['operating_income']} | {row['margin_pct']}% | {refs} |")
    return "\n".join(lines)


def verify_draft(draft, source):
    rows = draft.get("metrics", [])
    table = numeric_table(rows)
    issues = []
    if not rows or not all(source.verify_row(row) for row in rows):
        issues.append("A financial row failed independent source and arithmetic verification.")
    table_matches = draft.get("numeric_table") == table and table in draft.get("body", "")
    if not table_matches:
        issues.append("The displayed numeric table differs from the verified table.")
    rest = draft.get("body", "").replace(table, "")
    refs = {ref for row in rows for ref in row["fact_ids"]}
    refs.update(ref for risk in draft.get("risks", []) for ref in risk["source_ids"])
    for ref in refs:
        rest = rest.replace(f"[{ref}]", "")
    # Exempt only generated risk labels. A year used elsewhere can still be an
    # unsupported financial number (for example, "Revenue is 2025 USD").
    for risk in draft.get("risks", []):
        label = f"- {risk['ticker']}, fiscal {risk['before_year']} to {risk['after_year']}:"
        rest = re.sub(r"^" + re.escape(label), "", rest, flags=re.MULTILINE)
    extra_numbers = len(re.findall(r"\d+(?:[.,]\d+)*(?:%)?", rest))
    if extra_numbers:
        issues.append("An extra number outside the canonical financial table needs source verification.")
    if re.search(r"\b(buy|sell|guaranteed returns?|recommend buying)\b", rest, re.I):
        issues.append("Investment recommendation or promised-return language is outside this journey.")
    total = len(rows) * 3 + extra_numbers
    valid = sum(3 for row in rows if source.verify_row(row)) if table_matches else 0
    return {"passed": not issues, "issues": issues, "verified_numbers": valid, "total_numbers": total,
            "verified_share": valid / total if total else 0, "semantic_review": "not_run_offline"}


class Engine:
    def __init__(self, store, source, runtime, caller=None):
        self.store, self.source = store, source
        self.runtime = Path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.runtime / "checkpoints.sqlite", check_same_thread=False)
        self.saver = SqliteSaver(self.connection)
        self.locks, self.master, self.usage_lock = {}, threading.RLock(), threading.RLock()
        self.caller = caller or self._wire_call
        graph = StateGraph(State)
        for name in ("plan", "review_plan", "research_company", "quant", "risk", "draft", "critic", "repair", "review_note", "publish"):
            graph.add_node(name, getattr(self, "_" + name))
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "review_plan")
        graph.add_conditional_edges("review_plan", self._dispatch)
        graph.add_edge("research_company", "quant")
        for before, after in (("quant", "risk"), ("risk", "draft"), ("draft", "critic"), ("repair", "draft")):
            graph.add_edge(before, after)
        graph.add_conditional_edges("critic", lambda s: "repair" if not s["critic"]["passed"] and not s.get("human_edited") and s.get("repairs", 0) < 2 else "review_note")
        graph.add_edge("publish", END)
        self.graph = graph.compile(checkpointer=self.saver)

    def close(self):
        self.connection.close()

    def lock(self, run_id):
        with self.master:
            return self.locks.setdefault(run_id, threading.RLock())

    def event(self, run_id, agent, stage, message, **details):
        self.store.event(run_id, agent, stage, message, details or None)

    async def _wire_call(self, role, server, tool, arguments):
        config = json.loads(Path(os.environ["SCOPED_CONFIG"]).read_text())
        endpoint = os.environ["MCP_" + server.replace("-", "_").upper() + "_URL"]
        async with Client(endpoint, auth=config["roles"][role], timeout=30) as client:
            result = await client.call_tool(tool, arguments)
        envelope = getattr(result, "structured_content", None)
        if envelope is None:
            envelope = json.loads(next(item.text for item in result.content if getattr(item, "type", "") == "text"))
        if not isinstance(envelope, dict) or not envelope.get("ok"):
            raise ReviewError(f"{server}/{tool} refused the operation.")
        return envelope["data"]

    def call(self, state, role, server, tool, **arguments):
        run_id = state["run_id"]
        with self.usage_lock:
            run = self.store.get_run(run_id)
            usage = run.setdefault("usage", {"tokens": 0, "model_calls": 0, "tool_calls": 0, "cost_usd": 0})
            usage.setdefault("tool_calls", 0)
            usage.setdefault("tokens", 0)
            if usage["tool_calls"] >= run["request"].get("max_tool_calls", 60):
                raise ReviewError("The original run tool budget is exhausted.")
            usage["tool_calls"] += 1
            self.store.save_run(run)
        self.event(run_id, role, "tool_start", f"Calling {server}/{tool}")
        started = time.monotonic()
        try:
            result = self.caller(role, server, tool, arguments)
            if hasattr(result, "__await__"):
                result = asyncio.run(result)
        except Exception:
            self.event(run_id, role, "tool_error", f"{server}/{tool} failed; no fallback was substituted.")
            raise
        self.event(run_id, role, "tool_result", f"{server}/{tool} returned", seconds=round(time.monotonic() - started, 3))
        return result

    def execute(self, run_id, decision=None):
        with self.lock(run_id):
            run = self.store.get_run(run_id)
            if run["status"] in {"published", "rejected"}:
                return self.view(run_id)
            run["status"], run["stage"] = "running", "working"
            run.update(mode="offline", data_source="sec_edgar", transport="http", source_fingerprint=self.source.fingerprint)
            self.store.save_run(run)
            config = {"configurable": {"thread_id": run_id}, "recursion_limit": 40}
            try:
                queued = decision or run.get("queued_decision")
                initial = {"run_id": run_id, "actor": run.get("actor", "local-analyst"), "request": run["request"], "findings": [], "repairs": 0}
                inputs = Command(resume=queued) if queued else (None if self.graph.get_state(config).values else initial)
                result = self.graph.invoke(inputs, config, durability="sync")
                run = self.store.get_run(run_id)
                for key in ("plan", "metrics", "risks", "draft", "critic", "repairs", "status", "note_id"):
                    if key in result:
                        run[key] = result[key]
                pauses = result.get("__interrupt__", [])
                if pauses:
                    run["pending"] = pauses[0].value
                    run["status"] = "awaiting_" + run["pending"]["kind"]
                else:
                    run.pop("pending", None)
                run["stage"] = run["status"]
                run.pop("queued_decision", None)
                self.store.save_run(run)
            except Exception as exc:
                # MCP credentials and exception bodies never enter public traces.
                run = self.store.get_run(run_id)
                detail = str(exc) if isinstance(exc, ReviewError) else "research stopped; inspect service diagnostics"
                run.update(status="error", stage="error", error=f"{type(exc).__name__}: {detail}")
                self.store.save_run(run)
                self.event(run_id, "system", "error", run["error"])
            return self.view(run_id)

    def view(self, run_id):
        run = deepcopy(self.store.get_run(run_id))
        if not run:
            return None
        run.pop("queued_decision", None)
        run["events"] = self.store.events(run_id)
        return run

    def claim(self, run_id, decision):
        with self.lock(run_id):
            run = self.store.get_run(run_id)
            pending = run.get("pending", {})
            if run["status"] != "awaiting_" + decision["kind"] or pending.get("payload_hash") != decision["payload_hash"] or pending.get("kind") != decision["kind"]:
                raise ReviewError("Stale review or another decision is already running.")
            if decision["action"] == "approve" and decision["kind"] == "note" and not run.get("critic", {}).get("passed"):
                raise ReviewError("Unresolved checks prevent publication.")
            run.update(status="running", stage="resuming", queued_decision=decision)
            self.store.save_run(run)

    def _plan(self, state):
        request = state["request"]
        plan = {"tickers": request["tickers"], "years": request["years"],
                "outline": ["Inspect original annual facts and actual fiscal periods", "Calculate and independently verify operating margins", "Compare cached adjacent-year risk sections; original boundaries require human domain review", "Draft a cited note and identify limits"],
                "caveats": ["Offline deterministic teaching workflow; no language model or semantic judgment.", "Fiscal-year labels do not align different company calendars."]}
        self.event(state["run_id"], "planner", "plan", "Research plan prepared; waiting for the analyst.")
        return {"plan": plan}

    def _review_plan(self, state):
        plan = state["plan"]
        decision = interrupt({"kind": "plan", "payload": plan, "payload_hash": canonical_hash(plan)})
        if decision["payload_hash"] != canonical_hash(plan):
            raise ReviewError("Plan version changed.")
        action = decision["action"]
        if action == "reject":
            self.event(state["run_id"], "human", "plan_rejected", "The analyst rejected the plan; nothing was published.")
            return {"status": "rejected", "plan_action": "reject"}
        if action == "edit":
            edits = decision.get("edits") or {}
            if set(edits) - {"tickers", "years", "outline"}:
                raise ReviewError("Unsupported plan edit fields.")
            updated = {**plan, **edits}
            validate_scope(updated, self.source)
            self.event(state["run_id"], "human", "plan_edit", "Plan edited; review the new version before continuing.")
            return {"plan": updated, "plan_action": "edit"}
        self.event(state["run_id"], "human", "plan_approved", "The analyst approved this exact plan.")
        return {"plan_action": "approve"}

    def _dispatch(self, state):
        if state.get("status") == "rejected":
            return END
        if state.get("plan_action") == "edit":
            return "review_plan"
        return [Send("research_company", {"run_id": state["run_id"], "plan": state["plan"], "ticker": ticker}) for ticker in state["plan"]["tickers"]]

    def _research_company(self, state):
        ticker, years = state["ticker"], state["plan"]["years"]
        self.event(state["run_id"], "researcher", "research", f"Researching {ticker} in a parallel company branch.")
        facts = self.call(state, "researcher", "edgar", "get_facts", ticker=ticker, years=years)
        passages = self.call(state, "researcher", "filings-kb", "search_filings", query="operating income revenue annual results and risks", ticker=ticker, years=years, k=5)
        return {"findings": [{"ticker": ticker, "facts": facts, "passage_ids": [p["id"] for p in passages]}]}

    def _quant(self, state):
        rows = []
        for company in sorted(state["findings"], key=lambda item: item["ticker"]):
            for year in state["plan"]["years"]:
                facts = {f["concept"]: f for f in company["facts"] if f["fiscal_year"] == year}
                row = self.call(state, "quant", "python-sandbox", "calculate_margin", revenue_fact_id=facts["revenue"]["id"], operating_income_fact_id=facts["operating_income"]["id"])
                if not self.source.verify_row(row):
                    raise ReviewError("Calculation does not match the canonical source facts.")
                rows.append(row)
        return {"metrics": rows}

    def _risk(self, state):
        risks = []
        for ticker in state["plan"]["tickers"]:
            sections = {}
            for year in state["plan"]["years"]:
                section = self.call(state, "risk", "edgar", "get_section", ticker=ticker, year=year, item="1A")
                if not section.get("snapshot_complete"):
                    raise ReviewError("Risk comparison requires all cached section chunks.")
                sections[year] = section
            for before, after in zip(state["plan"]["years"], state["plan"]["years"][1:]):
                texts = ["\n".join(chunk["text"] for chunk in sections[year]["chunks"]) for year in (before, after)]
                digests = [hashlib.sha256(text.encode()).hexdigest() for text in texts]
                risks.append({"ticker": ticker, "before_year": before, "after_year": after, "text_changed": digests[0] != digests[1],
                    "source_ids": sections[before]["source_ids"] + sections[after]["source_ids"], "source_digests": digests,
                    "snapshot_complete": True, "original_section_boundaries_verified": False,
                    "interpretation": "Cached text comparison only. Original Item boundaries, economic materiality and added or removed risks require human domain review."})
        return {"risks": risks}

    def _draft(self, state):
        table = numeric_table(state["metrics"])
        risk_lines = []
        for risk in state["risks"]:
            refs = " ".join(f"[{ref}]" for ref in risk["source_ids"])
            description = "source wording differs" if risk["text_changed"] else "source text is unchanged"
            risk_lines.append(f"- {risk['ticker']}, fiscal {risk['before_year']} to {risk['after_year']}: {description}; no economic-materiality conclusion is made. {refs}")
        notes = self.call(state, "planner", "research-portal", "past_notes", actor=state["actor"])
        history = "Relevant approved notes are available in the library for follow-up comparison." if notes else "There is no previously approved note in this local library."
        body = "Offline research rehearsal using actual SEC sources. Financial arithmetic is independently checked; narrative semantic review has not been run.\n\n## Verified operating margins\n" + table + "\n\n## Cached risk-section text comparison\n" + ("\n".join(risk_lines) or "No adjacent-year comparison is available.") + "\n\n## Limits and history\nFiscal periods differ across companies. Original Item boundaries require human domain review. Cached text differences do not establish changes in economic risk. This draft provides no investment recommendation.\n" + history
        draft = {"run_id": state["run_id"], "actor": state["actor"], "title": " / ".join(state["plan"]["tickers"]) + " annual research note", "body": body,
                 "numeric_table": table, "metrics": state["metrics"], "risks": state["risks"], "plan": state["plan"],
                 "source_kind": "sec_edgar", "model_mode": "offline", "source_fingerprint": self.source.fingerprint}
        self.event(state["run_id"], "writer", "draft", "A cited draft was assembled; semantic judgments remain for human review.")
        return {"draft": draft, "human_edited": False}

    def _critic(self, state):
        critic = verify_draft(state["draft"], self.source)
        self.event(state["run_id"], "critic", "critic_pass" if critic["passed"] else "critic_reject", "Independent code checks completed.", **critic)
        return {"critic": critic}

    def _repair(self, state):
        return {"repairs": state.get("repairs", 0) + 1}

    def _review_note(self, state):
        draft = state["draft"]
        decision = interrupt({"kind": "note", "payload": draft, "payload_hash": canonical_hash(draft), "critic": state["critic"]})
        if decision["payload_hash"] != canonical_hash(draft):
            raise ReviewError("Note version changed.")
        if decision["action"] == "reject":
            self.store.invalidate_approval(state["run_id"])
            self.event(state["run_id"], "human", "note_rejected", "The analyst rejected the note; nothing was published.")
            return Command(update={"status": "rejected"}, goto=END)
        if decision["action"] == "edit":
            edits = decision.get("edits") or {}
            if set(edits) != {"body"} or not isinstance(edits["body"], str) or len(edits["body"]) > 100000:
                raise ReviewError("A note edit must contain only a body string within the size limit.")
            self.store.invalidate_approval(state["run_id"])
            self.event(state["run_id"], "human", "note_edit", "Note edited; the previous version cannot be approved and checks will repeat.")
            return Command(update={"draft": {**draft, **edits}, "human_edited": True}, goto="critic")
        if not state["critic"]["passed"] or not verify_draft(draft, self.source)["passed"]:
            raise ReviewError("Unresolved checks prevent publication.")
        fingerprint = canonical_hash(draft)
        self.store.record_approval(state["run_id"], state["actor"], fingerprint)
        capability = self.store.make_capability(state["run_id"], state["actor"], fingerprint)
        self.event(state["run_id"], "human", "note_approved", "The analyst signed the exact checked note.", payload_hash=fingerprint)
        return Command(update={"capability": capability}, goto="publish")

    def _publish(self, state):
        if not verify_draft(state["draft"], self.source)["passed"]:
            raise ReviewError("Final code verification failed.")
        receipt = self.call(state, "publisher", "research-portal", "publish_note", payload=state["draft"], capability=state["capability"])
        self.event(state["run_id"], "publisher", "published", "Approved note saved to the library.", note_id=receipt["note_id"])
        return {"status": "published", "note_id": receipt["note_id"], "capability": ""}


def validate_scope(value, source):
    tickers, years = value.get("tickers", []), value.get("years", [])
    known = {company["ticker"] for company in source.companies()}
    if not isinstance(tickers, list) or not 1 <= len(tickers) <= 4 or len(set(tickers)) != len(tickers) or not set(tickers) <= known:
        raise ReviewError("Choose up to four covered companies.")
    if not isinstance(years, list) or not 1 <= len(years) <= 3 or not all(isinstance(year, int) and not isinstance(year, bool) for year in years) or years != sorted(set(years)) or any(not set(years) <= set(source.years(ticker)) for ticker in tickers):
        raise ReviewError("Choose up to three available fiscal years in ascending order.")
    if "outline" in value and (not isinstance(value["outline"], list) or not value["outline"] or not all(isinstance(item, str) and item.strip() for item in value["outline"])):
        raise ReviewError("The plan needs a nonempty research outline.")
