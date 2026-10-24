"""Fresh step-four teaching graph: real MCP tools, persistent human pauses.

This first journey is deterministic offline research. It performs no LLM calls
and does not claim learned retrieval or semantic risk judgments.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from decimal import Decimal
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
    risk_ai: list[dict]


LIVE_NOTICE = "Model-assisted research using actual SEC sources. Financial arithmetic is independently checked; AI interpretations need human source review."
LIVE_LIMITS = "Issuer fiscal calendars differ. Evidence selection is partial and original section boundaries are unverified. Selected excerpts cannot establish absent or removed risks or economic materiality. This note provides no investment recommendation."


def semantic_input_hash(draft):
    return canonical_hash({key: value for key, value in draft.items() if key != "semantic_verdict"})


def live_body(draft):
    from .reasoning import render_claims
    claims = {claim["claim_id"]: claim for claim in draft["narrative_claims"]}
    sections = draft["live_sections"]
    if len(claims) != len(draft["narrative_claims"]) or set(sections["risk_ids"] + sections["writer_ids"]) != set(claims):
        raise ValueError("Narrative sections do not cover the exact claims")
    risks = render_claims([claims[identifier] for identifier in sections["risk_ids"]]) or "Selected evidence did not support a disclosure comparison."
    summary = render_claims([claims[identifier] for identifier in sections["writer_ids"]])
    return (LIVE_NOTICE + "\n\n## Verified operating margins\n" + draft["numeric_table"]
            + "\n\n## AI disclosure observations\n" + risks
            + "\n\n## AI research summary\n" + summary
            + "\n\n## Limits and history\n" + LIVE_LIMITS + "\n" + draft["history_sentence"])


def edited_live_claims(draft, body):
    """Allow edits to claim sentences while retaining their code-owned evidence."""
    from .reasoning import validate_prose
    lines = [line for line in body.splitlines() if line.startswith("- ")]
    ordered = draft["live_sections"]["risk_ids"] + draft["live_sections"]["writer_ids"]
    if len(lines) != len(ordered):
        raise ValueError("Keep the existing claim bullets and evidence references")
    claims = {claim["claim_id"]: deepcopy(claim) for claim in draft["narrative_claims"]}
    for identifier, line in zip(ordered, lines):
        claim = claims[identifier]
        suffix = " " + " ".join(f"[{citation['source_id']}]" for citation in claim["citations"])
        if not line.endswith(suffix):
            raise ValueError("Evidence references must stay attached to their claim")
        claim["text"] = validate_prose(line[2:-len(suffix)])
    updated = [claims[identifier] for identifier in ordered]
    if live_body({**draft, "narrative_claims": updated}) != body:
        raise ValueError("Keep the verified table, headings, evidence and mandatory limitations")
    return updated


def numeric_table(rows):
    lines = ["| Company | FY | Actual period | Revenue (USD) | Operating income (USD) | Margin | Sources |",
             "|---|---|---|---:|---:|---:|---|"]
    for row in rows:
        refs = " ".join(f"[{ref}]" for ref in row["fact_ids"])
        lines.append(f"| {row['ticker']} | {row['year']} | {row['period_start']} to {row['period_end']} | {row['revenue']} | {row['operating_income']} | {row['margin_pct']}% | {refs} |")
    return "\n".join(lines)


def verify_draft(draft, source, require_semantic=True):
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
    refs.update(citation["source_id"] for claim in draft.get("narrative_claims", []) for citation in claim.get("citations", []))
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
    semantic_review = "not_run_offline"
    if draft.get("model_mode") == "live":
        from .reasoning import normalize_evidence, validate_claims
        try:
            if draft.get("source_fingerprint") != source.fingerprint:
                raise ValueError("The source snapshot changed")
            for evidence in draft["ai_evidence"]:
                try:
                    original = source.fact(evidence["id"])
                except ValueError:
                    original = source.passage(evidence["id"])
                normalized = normalize_evidence([original])[0]
                if (evidence["ticker"], evidence["year"]) != (normalized["ticker"], normalized["year"]) or evidence["text"] not in normalized["text"]:
                    raise ValueError("Narrative evidence differs from the frozen source")
                if evidence["ticker"] not in draft["plan"]["tickers"] or evidence["year"] not in draft["plan"]["years"]:
                    raise ValueError("Narrative evidence is outside approved scope")
            validate_claims(draft["narrative_claims"], draft["ai_evidence"])
            if draft["body"] != live_body(draft):
                raise ValueError("Displayed narrative differs from its checked claims or limitations")
            if require_semantic:
                verdict = draft.get("semantic_verdict") or {}
                expected = {claim["claim_id"] for claim in draft["narrative_claims"]}
                actual = [item["claim_id"] for item in verdict.get("verdicts", [])]
                if (not verdict.get("passed") or verdict.get("issues") or set(actual) != expected or len(actual) != len(expected)
                        or not all(item["supported"] is True for item in verdict.get("verdicts", []))
                        or verdict.get("body_hash") != hashlib.sha256(draft["body"].encode()).hexdigest()
                        or verdict.get("source_fingerprint") != source.fingerprint
                        or verdict.get("checked_input_hash") != semantic_input_hash(draft)):
                    raise ValueError("The exact note needs a passing, current AI source-support review")
                semantic_review = "model_assisted_not_gold"
            else:
                semantic_review = "pending_model_review"
        except (ValueError, KeyError, TypeError) as exc:
            issues.append(str(exc))
            semantic_review = "blocked"
    total = len(rows) * 3 + extra_numbers
    valid = sum(3 for row in rows if source.verify_row(row)) if table_matches else 0
    return {"passed": not issues, "issues": issues, "verified_numbers": valid, "total_numbers": total,
            "verified_share": valid / total if total else 0, "semantic_review": semantic_review}


class Engine:
    def __init__(self, store, source, runtime, caller=None, model_client=None):
        self.store, self.source = store, source
        self.runtime = Path(runtime)
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.runtime / "checkpoints.sqlite", check_same_thread=False)
        self.saver = SqliteSaver(self.connection)
        self.locks, self.master, self.usage_lock = {}, threading.RLock(), threading.RLock()
        self.caller = caller or self._wire_call
        self.model_client = model_client
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

    def is_live(self, state):
        return self.store.get_run(state["run_id"])["request"].get("mode", "offline") == "live"

    def reasoner(self, state, purpose):
        from .reasoning import Reasoner
        if not self.model_client:
            raise ReviewError("Live model reasoning is unavailable; no offline result was substituted.")
        def model_call(role, *, system, context, schema, max_output_tokens):
            messages = [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
            identifier = canonical_hash({"run": state["run_id"], "purpose": purpose, "role": role, "messages": messages, "schema": schema})
            reserved_tokens = len(json.dumps({"messages": messages, "schema": schema}, ensure_ascii=False).encode()) + 4096 + max_output_tokens
            with self.usage_lock:
                run = self.store.get_run(state["run_id"])
                usage = run["usage"]
                reservations = usage.setdefault("model_reservations", {})
                recorded = {item["call_id"] for item in usage.get("calls", [])}
                if identifier not in recorded and identifier not in reservations:
                    if usage.get("tokens", 0) + sum(reservations.values()) + reserved_tokens > run["request"].get("max_tokens", 100000):
                        raise ReviewError("The original request token budget cannot cover this model call.")
                    if len(recorded) + len(reservations) >= run["request"].get("max_model_calls", 12):
                        raise ReviewError("The original request model-call budget is exhausted.")
                    reservations[identifier] = reserved_tokens
                    self.store.save_run(run)
            self.event(state["run_id"], role, "model_start", "Requesting bounded live model reasoning.", call_id=identifier)
            try:
                result = self.model_client.complete(run_id=state["run_id"], call_id=identifier, role=role,
                    messages=messages, response_schema=schema, max_output_tokens=max_output_tokens)
            except Exception as exc:
                accounting = None
                try:
                    accounting = self.model_client.budget(state["run_id"])
                except Exception:
                    pass
                with self.usage_lock:
                    run = self.store.get_run(state["run_id"])
                    usage = run["usage"]
                    if accounting is not None:
                        usage.update(model_calls=accounting["model_calls"], cost_usd=float(accounting["reported_spend_usd"]),
                            held_usd=float(accounting["held_usd"]), committed_usd=float(accounting["committed_usd"]),
                            accounting_status="provider_reported_with_holds", gateway_budget=accounting)
                    else:
                        usage.update(cost_usd=None, held_usd=None, committed_usd=None, accounting_status="unknown_after_failure")
                    self.store.save_run(run)
                self.event(state["run_id"], role, "model_error", "Model reasoning stopped; no automatic paid retry or offline substitute.", call_id=identifier)
                from .provider import ProviderError
                message = str(exc) if isinstance(exc, ProviderError) else "The live model operation failed."
                raise ReviewError(message) from None
            with self.usage_lock:
                run = self.store.get_run(state["run_id"])
                usage = run["usage"]
                calls = usage.setdefault("calls", [])
                if identifier not in {item["call_id"] for item in calls}:
                    calls.append({**result["usage"], "stage": role, "config_version": result["config_version"]})
                usage.setdefault("model_reservations", {}).pop(identifier, None)
                usage.update(model_calls=len(calls), tokens=sum(item["total_tokens"] for item in calls),
                             cost_usd=float(sum((Decimal(str(item["cost_usd"])) for item in calls), Decimal(0))))
                self.store.save_run(run)
            self.event(state["run_id"], role, "model_result", "Structured live model response received.", call_id=identifier, cached=result.get("cached", False))
            return result["content"]
        return Reasoner(model_call)

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
            run.update(mode=run["request"].get("mode", "offline"), data_source="sec_edgar", transport="http", source_fingerprint=self.source.fingerprint)
            self.store.save_run(run)
            config = {"configurable": {"thread_id": run_id}, "recursion_limit": 40}
            try:
                queued = decision or run.get("queued_decision")
                initial = {"run_id": run_id, "actor": run.get("actor", "local-analyst"), "request": run["request"], "findings": [], "repairs": 0}
                inputs = Command(resume=queued) if queued else (None if self.graph.get_state(config).values else initial)
                result = self.graph.invoke(inputs, config, durability="sync")
                run = self.store.get_run(run_id)
                for key in ("plan", "metrics", "risks", "risk_ai", "draft", "critic", "repairs", "status", "note_id"):
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
        if self.is_live(state):
            plan = self.reasoner(state, "plan").plan(request["question"], request["tickers"], request["years"])
            plan["mode"] = "live"
            self.event(state["run_id"], "planner", "plan", "AI research plan prepared; waiting for the analyst.")
            return {"plan": plan}
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
        selection = self.reasoner(state, "query:" + ticker).research_query(self.store.get_run(state["run_id"])["request"]["question"], ticker, years) if self.is_live(state) else {"query": "operating income revenue annual results and risks", "focus": "Offline fixed query"}
        passages = self.call(state, "researcher", "filings-kb", "search_filings", query=selection["query"], ticker=ticker, years=years, k=5)
        return {"findings": [{"ticker": ticker, "facts": facts, "passage_ids": [p["id"] for p in passages], "query_selection": selection}]}

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
        analyses = []
        for ticker in state["plan"]["tickers"]:
            sections = {}
            for year in state["plan"]["years"]:
                section = self.call(state, "risk", "edgar", "get_section", ticker=ticker, year=year, item="1A")
                if not section.get("snapshot_complete"):
                    raise ReviewError("Risk comparison requires all cached section chunks.")
                sections[year] = section
            if self.is_live(state):
                analyses.append(self.reasoner(state, "risk:" + ticker).compare_risks(ticker, state["plan"]["years"], sections))
            for before, after in zip(state["plan"]["years"], state["plan"]["years"][1:]):
                texts = ["\n".join(chunk["text"] for chunk in sections[year]["chunks"]) for year in (before, after)]
                digests = [hashlib.sha256(text.encode()).hexdigest() for text in texts]
                risks.append({"ticker": ticker, "before_year": before, "after_year": after, "text_changed": digests[0] != digests[1],
                    "source_ids": sections[before]["source_ids"] + sections[after]["source_ids"], "source_digests": digests,
                    "snapshot_complete": True, "original_section_boundaries_verified": False,
                    "interpretation": "Cached text comparison only. Original Item boundaries, economic materiality and added or removed risks require human domain review."})
        return {"risks": risks, "risk_ai": analyses}

    def _draft(self, state):
        table = numeric_table(state["metrics"])
        if self.is_live(state):
            return self._live_draft(state, table)
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

    def _live_draft(self, state, table):
        from .reasoning import normalize_evidence
        evidence = [item for analysis in state.get("risk_ai", []) for item in analysis["selected_evidence"]]
        facts = [fact for company in state["findings"] for fact in company["facts"]]
        known = normalize_evidence(evidence + facts)
        question = self.store.get_run(state["run_id"])["request"]["question"]
        if state.get("repairs"):
            question += "\nRevision feedback from the previous checks: " + json.dumps(state.get("critic", {}).get("issues", []))
        written = self.reasoner(state, "writer:" + str(state.get("repairs", 0))).write(question, state["plan"], state["metrics"], state.get("risk_ai", []), known)
        risk_claims = [claim for analysis in state.get("risk_ai", []) for comparison in analysis["comparisons"] for claim in comparison["claims"]]
        notes = self.call(state, "planner", "research-portal", "past_notes", actor=state["actor"])
        history = "Approved earlier research is available in the local library; it was not sent to the model in this run." if notes else "There is no previously approved note in this local library."
        draft = {"run_id": state["run_id"], "actor": state["actor"], "title": " / ".join(state["plan"]["tickers"]) + " AI-assisted annual research note",
            "numeric_table": table, "metrics": state["metrics"], "risks": state["risks"], "plan": state["plan"], "source_kind": "sec_edgar", "model_mode": "live", "source_fingerprint": self.source.fingerprint,
            "narrative_claims": risk_claims + written["claims"], "ai_evidence": known, "evidence_selection": [analysis["selection"] for analysis in state.get("risk_ai", [])],
            "live_sections": {"risk_ids": [claim["claim_id"] for claim in risk_claims], "writer_ids": [claim["claim_id"] for claim in written["claims"]]}, "history_sentence": history}
        draft["body"] = live_body(draft)
        self.event(state["run_id"], "writer", "draft", "Cited AI narrative and code-verified table prepared for source-support checks.")
        return {"draft": draft, "human_edited": False}

    def _critic(self, state):
        draft = deepcopy(state["draft"])
        draft.pop("semantic_verdict", None)
        critic = verify_draft(draft, self.source, require_semantic=False)
        if self.is_live(state) and critic["passed"]:
            verdict = self.reasoner(state, "critic:" + semantic_input_hash(draft)).critique(draft, draft["ai_evidence"])
            verdict["checked_input_hash"] = semantic_input_hash(draft)
            draft["semantic_verdict"] = verdict
            critic = verify_draft(draft, self.source)
            if not verdict["passed"]:
                critic["issues"].extend(verdict["issues"] + [item["reason"] for item in verdict["verdicts"] if not item["supported"]])
        self.event(state["run_id"], "critic", "critic_pass" if critic["passed"] else "critic_reject", "Independent code checks completed.", **critic)
        return {"critic": critic, "draft": draft}

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
            updated = {**draft, **edits}
            updated.pop("semantic_verdict", None)
            if self.is_live(state):
                try:
                    updated["narrative_claims"] = edited_live_claims(draft, edits["body"])
                except ValueError:
                    pass  # The critic will expose the invalid edit at the new review gate.
            return Command(update={"draft": updated, "human_edited": True}, goto="critic")
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
