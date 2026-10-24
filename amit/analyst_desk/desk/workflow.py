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
    memory_context: dict


LIVE_NOTICE = "Model-assisted research using actual SEC sources. Financial arithmetic is independently checked; AI interpretations need human source review."
LIVE_LIMITS = "Issuer fiscal calendars differ. Risk and writer context uses code-selected verbatim quote windows. Selected risk excerpts are partial and original section boundaries are unverified. Selected excerpts cannot establish absent or removed risks or economic materiality. This note provides no investment recommendation."


def semantic_input_hash(draft):
    return canonical_hash({key: value for key, value in draft.items() if key != "semantic_verdict"})



def critic_extension_request(draft, run_id, grant_id, budget):
    """Rebuild the exact critic request without contacting a provider."""
    from .reasoning import Reasoner
    captured = {}
    class Captured(Exception):
        pass
    def capture(role, *, system, context, schema, max_output_tokens):
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
        purpose = "critic:" + semantic_input_hash(draft) + ":explicit-approved-extension:" + grant_id
        call_id = canonical_hash({"run": run_id, "purpose": purpose, "role": role, "messages": messages, "schema": schema})
        captured.update(run_id=run_id, call_id=call_id, role=role, messages=messages,
                        response_schema=schema, max_output_tokens=max_output_tokens,
                        model=budget["models"]["critic"], config_version=budget["config_version"])
        raise Captured
    try:
        Reasoner(capture).critique(draft, draft["ai_evidence"])
    except Captured:
        return captured
    raise ReviewError("The exact frozen critic request could not be reconstructed.")



def reconcile_settled_model_call(usage, accounting, *, run_id, call_id, role):
    """Record one authoritative billed failure without releasing other holds.

    This can also reconcile an already stopped call using a fresh read-only
    gateway budget; it never sends, retries or accepts model content.
    """
    try:
        if (not isinstance(accounting, dict) or accounting.get("run_id") != run_id
                or not isinstance(accounting.get("config_version"), str)
                or not 1 <= len(accounting["config_version"]) <= 200
                or not isinstance(accounting.get("settled_calls"), list)):
            return False
        matches = [item for item in accounting["settled_calls"]
                   if isinstance(item, dict) and item.get("call_id") == call_id]
        if len(matches) != 1:
            return False
        settled = matches[0]
        observed = settled.get("usage")
        if (set(settled) != {"call_id", "status", "usage"} or settled["status"] not in {"invalid_output", "succeeded"}
                or not isinstance(observed, dict) or observed.get("call_id") != call_id
                or type(observed.get("model_calls")) is not int or observed["model_calls"] != 1):
            return False
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if type(observed.get(key)) is not int or observed[key] < 0:
                return False
        if observed["total_tokens"] <= 0 or observed["total_tokens"] != observed["prompt_tokens"] + observed["completion_tokens"]:
            return False
        cost = Decimal(str(observed["cost_usd"]))
        amounts = [Decimal(str(accounting[key])) for key in ("reported_spend_usd", "held_usd", "committed_usd")]
        if (not cost.is_finite() or cost < 0 or not all(value.is_finite() and value >= 0 for value in amounts)
                or amounts[2] != amounts[0] + amounts[1]):
            return False
        calls = deepcopy(usage.get("calls", []))
        if not isinstance(calls, list) or len({item["call_id"] for item in calls}) != len(calls):
            return False
        recorded = [item for item in calls if item["call_id"] == call_id]
        entry = {key: observed[key] for key in ("call_id", "model_calls", "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd")}
        from .provider import MODEL_RATES
        for key in ("model", "requested_model", "returned_model"):
            if observed.get(key) in MODEL_RATES:
                entry[key] = observed[key]
        entry.update(stage=role, config_version=accounting["config_version"], accepted_output=settled["status"] == "succeeded")
        if recorded:
            if any(recorded[0].get(key) != entry[key] for key in ("call_id", "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd")):
                return False
        else:
            if call_id not in (usage.get("model_reservations") or {}):
                return False
            calls.append(entry)
        reservations = dict(usage.get("model_reservations") or {})
        reservations.pop(call_id, None)
        total_tokens = sum(item["total_tokens"] for item in calls)
        total_cost = sum((Decimal(str(item["cost_usd"])) for item in calls), Decimal(0))
        if (any(type(item.get("total_tokens")) is not int or item["total_tokens"] <= 0 for item in calls)
                or not total_cost.is_finite() or total_cost < 0 or total_cost != amounts[0]
                or type(accounting.get("observed_tokens")) is not int or accounting["observed_tokens"] != total_tokens
                or type(accounting.get("model_calls")) is not int or accounting["model_calls"] != len(calls) + len(reservations)
                or type(accounting.get("uncertain_calls")) is not int or accounting["uncertain_calls"] != len(reservations)
                or type(accounting.get("tokens")) is not int or accounting["tokens"] < total_tokens
                or reservations and (amounts[1] <= 0 or accounting["tokens"] <= total_tokens)):
            return False
    except (KeyError, ValueError, TypeError, ArithmeticError):
        return False
    usage.update(calls=calls, model_reservations=reservations, tokens=total_tokens,
                 model_calls=accounting["model_calls"], cost_usd=float(amounts[0]), held_usd=float(amounts[1]),
                 committed_usd=float(amounts[2]), accounting_status="provider_reported_with_holds", gateway_budget=deepcopy(accounting))
    return True


def live_body(draft):
    from .reasoning import render_claims
    claims = {claim["claim_id"]: claim for claim in draft["narrative_claims"]}
    sections = draft["live_sections"]
    if len(claims) != len(draft["narrative_claims"]) or set(sections["risk_ids"] + sections["writer_ids"]) != set(claims):
        raise ValueError("Narrative sections do not cover the exact claims")
    risks = render_claims([claims[identifier] for identifier in sections["risk_ids"]]) or "Selected evidence did not support a disclosure comparison."
    summary = render_claims([claims[identifier] for identifier in sections["writer_ids"]])
    figures = "\n\n## Verified operating margins\n" + draft["numeric_table"]
    narrative = "\n\n## AI disclosure observations\n" + risks + "\n\n## AI research summary\n" + summary
    sections = narrative + figures if draft.get("report_style") == "summary_first" else figures + narrative
    return (LIVE_NOTICE + sections
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
        comparison_periods = (claim.get("before_year"), claim.get("after_year")) if "ticker" in claim else None
        claim["text"] = validate_prose(line[2:-len(suffix)], comparison_periods=comparison_periods)
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
    if "memory_context" in draft:
        try:
            from .history import validate_snapshot_structure
            validate_snapshot_structure(draft["memory_context"], actor=draft.get("actor"), source_fingerprint=source.fingerprint)
            if (draft.get("plan", {}).get("memory_context") != draft["memory_context"]
                    or draft.get("report_style") != draft["memory_context"]["report_style"]
                    or draft["memory_context"]["selection_scope"] != {
                        "tickers": sorted(draft["plan"]["tickers"]), "years": sorted(draft["plan"]["years"])}):
                raise ValueError("The note memory differs from the reviewed plan")
        except (ValueError, TypeError, KeyError):
            issues.append("The note's local memory references differ from its reviewed plan.")
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
        from .memory import MemoryStore
        self.store, self.source = store, source
        self.memory = MemoryStore(store.path)
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
        graph.add_conditional_edges("critic", self._after_critic)
        graph.add_edge("publish", END)
        self.graph = graph.compile(checkpointer=self.saver, store=self.memory.langgraph_store)

    def close(self):
        self.connection.close()
        self.memory.close()

    def _validate_memory(self, state):
        snapshot = state.get("memory_context")
        if snapshot is None and state.get("run_id"):
            snapshot = (self.store.get_run(state["run_id"]) or {}).get("memory_context")
        if snapshot is not None:
            try:
                self.store.validate_memory_snapshot(snapshot, source_fingerprint=self.source.fingerprint,
                    actor=state.get("actor") or (self.store.get_run(state["run_id"]) or {}).get("actor"))
                plan = state.get("plan") or (self.store.get_run(state["run_id"]) or {}).get("plan")
                if plan and snapshot["selection_scope"] != {"tickers": sorted(plan["tickers"]), "years": sorted(plan["years"])}:
                    raise ValueError("Memory scope differs from the reviewed research scope")
            except ValueError as error:
                raise ReviewError("Analyst memory changed or expired. Create a fresh plan before continuing.") from error
        return snapshot

    def _freeze_memory(self, state, tickers, years):
        from .history import freeze_memory_context
        run = self.store.get_run(state["run_id"])
        enabled = run["request"].get("memory_enabled", True)
        if enabled:
            self.memory.remember_coverage(self.source, run["actor"])
        snapshot = freeze_memory_context(self.store, self.memory, run["request"]["question"], tickers, years,
            actor=run["actor"], current_source_fingerprint=self.source.fingerprint, enabled=enabled)
        run["memory_context"] = snapshot
        self.store.save_run(run)
        return snapshot

    @staticmethod
    def _history_sentence(snapshot):
        if not snapshot or not snapshot.get("enabled"):
            return "Analyst memory is off for this research."
        if snapshot["note_refs"]:
            return "Relevant approved notes are attached as local history references. Historical content stays separate from current SEC evidence."
        return "No relevant approved history was selected from local analyst memory."

    def lock(self, run_id):
        with self.master:
            return self.locks.setdefault(run_id, threading.RLock())

    def event(self, run_id, agent, stage, message, **details):
        self.store.event(run_id, agent, stage, message, details or None)

    def is_live(self, state):
        return self.store.get_run(state["run_id"])["request"].get("mode", "offline") == "live"

    def _after_critic(self, state):
        if state["critic"]["passed"] or state.get("human_edited") or state.get("repairs", 0) >= 2:
            return "review_note"
        if self.is_live(state):
            run = self.store.get_run(state["run_id"])
            # A draft repair requires both another writer and another critic.
            # Do not spend the last allowance on a draft that cannot be checked.
            if run["usage"].get("model_calls", 0) + 2 > run["request"].get("max_model_calls", 12):
                return "review_note"
        return "repair"

    def reasoner(self, state, purpose):
        from .reasoning import Reasoner
        if not self.model_client:
            raise ReviewError("Live model reasoning is unavailable; no offline result was substituted.")
        def model_call(role, *, system, context, schema, max_output_tokens):
            self._validate_memory(state)
            messages = [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
            identifier = canonical_hash({"run": state["run_id"], "purpose": purpose, "role": role, "messages": messages, "schema": schema})
            reserved_tokens = len(json.dumps({"messages": messages, "schema": schema}, ensure_ascii=False).encode()) + 4096 + max_output_tokens
            with self.usage_lock:
                run = self.store.get_run(state["run_id"])
                usage = run["usage"]
                reservations = usage.setdefault("model_reservations", {})
                recorded = {item["call_id"] for item in usage.get("calls", [])}
                if identifier not in recorded and identifier not in reservations:
                    token_limit = run["request"].get("max_tokens", 100000)
                    call_limit = run["request"].get("max_model_calls", 12)
                    extension = run.get("approved_critic_extension")
                    if extension:
                        actual_request = {"run_id": state["run_id"], "call_id": identifier, "role": role,
                            "messages": messages, "response_schema": schema, "max_output_tokens": max_output_tokens,
                            "model": extension["critic_model"], "config_version": extension["config_version"]}
                        budget = self.model_client.budget(state["run_id"])
                        grant = budget.get("run_budget_grant") or {}
                        if (role != "critic" or extension.get("approved") is not True or identifier != extension.get("call_id")
                                or canonical_hash(actual_request) != extension.get("request_hash")
                                or budget.get("policy_hash") != extension.get("policy_hash")
                                or budget.get("authorization_id") != extension.get("authorization_id")
                                or budget.get("config_version") != extension.get("config_version")
                                or grant.get("approved") is not True or grant.get("consumed") is not False
                                or {key: value for key, value in extension.items() if key not in {"authorization_id", "config_version"}}
                                   != {key: value for key, value in grant.items() if key != "consumed"}
                                or budget.get("ledger_checkpoint_hash") != extension.get("checkpoint_hash")
                                or budget.get("model_calls") != extension.get("checkpoint_calls")
                                or budget.get("tokens") != extension.get("checkpoint_tokens")
                                or canonical_hash(state.get("draft")) != extension.get("draft_hash")
                                or call_limit != extension.get("original_calls") or token_limit != extension.get("original_tokens")):
                            raise ReviewError("Only the separately approved exact critic request may use its one-call extension.")
                        call_limit, token_limit = extension["max_calls"], extension["max_tokens"]
                    if usage.get("tokens", 0) + sum(reservations.values()) + reserved_tokens > token_limit:
                        raise ReviewError("The original request token budget cannot cover this model call.")
                    if len(recorded) + len(reservations) >= call_limit:
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
                        try:
                            amounts = [Decimal(str(accounting[key])) for key in ("reported_spend_usd", "held_usd", "committed_usd")]
                            if (type(accounting["model_calls"]) is not int or accounting["model_calls"] < 0
                                    or not all(value.is_finite() and value >= 0 for value in amounts)
                                    or amounts[2] != amounts[0] + amounts[1]):
                                accounting = None
                        except (KeyError, ValueError, TypeError, ArithmeticError):
                            accounting = None
                    if accounting is not None:
                        reconciled = reconcile_settled_model_call(usage, accounting, run_id=state["run_id"], call_id=identifier, role=role)
                        if ("settled_calls" in accounting and not reconciled
                                and (accounting.get("uncertain_calls") != len(usage.get("model_reservations", {}))
                                     or usage.get("model_reservations") and Decimal(str(accounting["held_usd"])) <= 0)):
                            accounting = None
                    if accounting is not None:
                        usage.update(model_calls=accounting["model_calls"], cost_usd=float(accounting["reported_spend_usd"]),
                            held_usd=float(accounting["held_usd"]), committed_usd=float(accounting["committed_usd"]),
                            accounting_status="provider_reported_with_holds", gateway_budget=accounting)
                    else:
                        # Unknown accounting cannot erase a previously known
                        # held allowance or release any local reservation.
                        usage.update(cost_usd=None, committed_usd=None, accounting_status="unknown_after_failure")
                    self.store.save_run(run)
                from .provider import ProviderError, safe_error_code
                code = safe_error_code(exc.code) if isinstance(exc, ProviderError) else "gateway_request_failed"
                self.event(state["run_id"], role, "model_error", "Model reasoning stopped; no automatic paid retry or offline substitute.", call_id=identifier, error_code=code)
                message = str(exc) if isinstance(exc, ProviderError) else "The live model operation failed."
                raise ReviewError(f"{code}: {message}") from None
            with self.usage_lock:
                run = self.store.get_run(state["run_id"])
                usage = run["usage"]
                calls = usage.setdefault("calls", [])
                if identifier not in {item["call_id"] for item in calls}:
                    calls.append({**result["usage"], "stage": role, "config_version": result["config_version"]})
                usage.setdefault("model_reservations", {}).pop(identifier, None)
                usage.update(model_calls=len(calls) + len(usage["model_reservations"]), tokens=sum(item["total_tokens"] for item in calls),
                             cost_usd=float(sum((Decimal(str(item["cost_usd"])) for item in calls), Decimal(0))))
                self.store.save_run(run)
            # A deliberate transient retry never refunds the earlier ambiguous
            # call. Keep observed tokens distinct from its held token allowance.
            if usage["model_reservations"]:
                accounting = None
                try:
                    accounting = self.model_client.budget(state["run_id"])
                    amounts = [Decimal(str(accounting[key])) for key in ("reported_spend_usd", "held_usd", "committed_usd")]
                    if (type(accounting["model_calls"]) is not int or accounting["model_calls"] < len(calls) + len(usage["model_reservations"])
                            or not all(value.is_finite() and value >= 0 for value in amounts)
                            or amounts[0] < Decimal(str(usage["cost_usd"])) or amounts[2] != amounts[0] + amounts[1]):
                        accounting = None
                except Exception:
                    accounting = None
                with self.usage_lock:
                    run = self.store.get_run(state["run_id"])
                    if accounting is not None:
                        run["usage"].update(model_calls=accounting["model_calls"], cost_usd=float(accounting["reported_spend_usd"]),
                            held_usd=float(accounting["held_usd"]), committed_usd=float(accounting["committed_usd"]),
                            accounting_status="provider_reported_with_holds", gateway_budget=accounting)
                    else:
                        # Preserve the last known hold; unavailable accounting
                        # cannot be represented as a release or a zero charge.
                        run["usage"].update(cost_usd=None, committed_usd=None, accounting_status="unknown_after_retry")
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
        self._validate_memory(state)
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
            if run["status"] in {"published", "rejected", "error"}:
                return self.view(run_id)
            queued_decision = decision or run.get("queued_decision") or {}
            if (run.get("source_fingerprint") not in (None, self.source.fingerprint)
                    and queued_decision.get("action") != "reject"):
                run.update(status="error", stage="error", failure_kind="source_changed",
                           error="ReviewError: The source snapshot changed. Create a new research plan; this checkpoint was preserved without further calls.")
                run.pop("queued_decision", None)
                run.pop("queued_continuation", None)
                self.store.save_run(run)
                return self.view(run_id)
            if queued_decision.get("action") != "reject":
                try:
                    self._validate_memory(run)
                except ReviewError as error:
                    run.update(status="error", stage="error", failure_kind="memory_changed", error="ReviewError: " + str(error))
                    run.pop("queued_decision", None)
                    run.pop("queued_continuation", None)
                    self.store.save_run(run)
                    return self.view(run_id)
            continuation = run.get("queued_continuation")
            if continuation:
                try:
                    snapshot, _ = self._continuation_checkpoint(run, continuation["plan_hash"],
                        retry_transient=continuation.get("retry_transient", False),
                        replace_critic_policy=continuation.get("replace_critic_policy"),
                        critic_extension=continuation.get("critic_extension"), allow_queued=True)
                    if (snapshot.config["configurable"]["checkpoint_id"] != continuation["checkpoint_id"]
                            or self.source.fingerprint != continuation["source_fingerprint"]
                            or (continuation.get("retry_transient") or continuation.get("replace_critic_policy") or continuation.get("critic_extension"))
                            and canonical_hash(snapshot.values.get("draft")) != continuation["draft_hash"]):
                        raise ReviewError("The failed checkpoint changed before continuation.")
                except Exception:
                    run.update(status="error", stage="error", error="ReviewError: The approved continuation checkpoint changed; no model request was sent.")
                    run.pop("queued_continuation", None)
                    self.store.save_run(run)
                    return self.view(run_id)
            run["status"], run["stage"] = "running", "working"
            run.update(mode=run["request"].get("mode", "offline"), data_source="sec_edgar", transport="http",
                       source_fingerprint=run.get("source_fingerprint") or self.source.fingerprint)
            self.store.save_run(run)
            config = {"configurable": {"thread_id": run_id}, "recursion_limit": 40}
            try:
                queued = None if continuation else decision or run.get("queued_decision")
                initial = {"run_id": run_id, "actor": run.get("actor", "local-analyst"), "request": run["request"], "findings": [], "repairs": 0}
                inputs = Command(resume=queued) if queued else (None if self.graph.get_state(config).values else initial)
                result = self.graph.invoke(inputs, config, durability="sync")
                run = self.store.get_run(run_id)
                for key in ("plan", "metrics", "risks", "risk_ai", "draft", "critic", "repairs", "status", "note_id", "memory_context"):
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
                run.pop("queued_continuation", None)
                run.pop("error", None)
                run.pop("failure_kind", None)
                self.store.save_run(run)
            except Exception as exc:
                # MCP credentials and exception bodies never enter public traces.
                run = self.store.get_run(run_id)
                detail = str(exc) if isinstance(exc, ReviewError) else "research stopped; inspect service diagnostics"
                run.update(status="error", stage="error", error=f"{type(exc).__name__}: {detail}")
                from .reasoning import ReasoningError
                run["failure_kind"] = "content_validation" if isinstance(exc, ReasoningError) else "not_continuable"
                run.pop("queued_continuation", None)
                self.store.save_run(run)
                self.event(run_id, "system", "error", run["error"])
            return self.view(run_id)

    def view(self, run_id):
        run = deepcopy(self.store.get_run(run_id))
        if not run:
            return None
        run.pop("queued_decision", None)
        run.pop("queued_continuation", None)
        run["events"] = self.store.events(run_id)
        run["continuation"] = {"available": False}
        if run.get("status") == "error":
            try:
                _, proof = self._continuation_checkpoint(self.store.get_run(run_id), canonical_hash(run.get("plan")))
                run["continuation"] = {"available": True, "plan_hash": proof["payload_hash"], "failure_kind": "content_validation"}
            except Exception:
                try:
                    _, proof = self._continuation_checkpoint(self.store.get_run(run_id), canonical_hash(run.get("plan")), retry_transient=True)
                    run["continuation"] = {"available": False, "retry_transient_available": True,
                                           "plan_hash": proof["payload_hash"], "failure_kind": "critic_rate_limit"}
                except Exception:
                    try:
                        budget = self.model_client.budget(run_id)
                        policy_hash = budget.get("policy_hash")
                        _, proof = self._continuation_checkpoint(self.store.get_run(run_id), canonical_hash(run.get("plan")),
                                                                replace_critic_policy=policy_hash)
                        run["continuation"] = {"available": False, "replace_critic_policy_available": True,
                                               "plan_hash": proof["payload_hash"], "policy_hash": policy_hash,
                                               "failure_kind": "critic_policy_replacement"}
                    except Exception:
                        try:
                            grant = (self.model_client.budget(run_id).get("run_budget_grant") or {})
                            grant_id = grant.get("grant_id")
                            _, proof = self._continuation_checkpoint(self.store.get_run(run_id), canonical_hash(run.get("plan")),
                                                                    critic_extension=grant_id)
                            if grant_id is not None:
                                run["continuation"] = {"available": False, "critic_extension_available": True,
                                    "grant_id": grant_id, "plan_hash": proof["payload_hash"], "failure_kind": "approved_critic_extension"}
                        except Exception:
                            pass
        return run

    def _continuation_checkpoint(self, run, expected_plan_hash, *, retry_transient=False, replace_critic_policy=None, critic_extension=None, allow_queued=False):
        """Verify durable approval and a failed content check, without requests."""
        if (not run or run.get("actor") != "local-analyst" or run.get("request", {}).get("mode") != "live" or run.get("note_id")):
            raise ReviewError("Only a failed live content check can be continued explicitly.")
        self._validate_memory(run)
        if sum((bool(retry_transient), replace_critic_policy is not None, critic_extension is not None)) > 1:
            raise ReviewError("Choose one explicit continuation mode.")
        if not retry_transient and replace_critic_policy is None and critic_extension is None and (not str(run.get("error", "")).startswith("ReasoningError:")
                or run.get("failure_kind") not in {None, "content_validation"} or run.get("usage", {}).get("model_reservations")):
            raise ReviewError("Only a failed live content check can be continued explicitly.")
        snapshot = self.graph.get_state({"configurable": {"thread_id": run["id"]}})
        state = snapshot.values
        permitted = {"research_company", "quant", "risk", "draft", "critic", "repair"}
        failures = [task.error for task in snapshot.tasks if task.error]
        if (not snapshot.next or not set(snapshot.next) <= permitted or not failures
                or not retry_transient and replace_critic_policy is None and critic_extension is None and any(not str(error).startswith("ReasoningError(") for error in failures)
                or state.get("run_id") != run["id"] or state.get("actor") != run["actor"]
                or state.get("plan_action") != "approve" or state.get("capability")):
            raise ReviewError("A failed approved research checkpoint is required.")
        plan = state.get("plan")
        if (not isinstance(expected_plan_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_plan_hash)
                or canonical_hash(plan) != expected_plan_hash or canonical_hash(run.get("plan")) != expected_plan_hash
                or canonical_hash(state.get("request")) != canonical_hash(run["request"])
                or "source_fingerprint" in run and run["source_fingerprint"] != self.source.fingerprint
                or (plan or {}).get("source_coverage", {}).get("source_fingerprint") != self.source.fingerprint):
            raise ReviewError("The approved plan, original request or source snapshot changed.")
        events = self.store.events(run["id"])
        if retry_transient:
            self._critic_retry_proof(run, snapshot, events, allow_queued=allow_queued)
        if replace_critic_policy is not None:
            self._critic_policy_replacement_proof(run, snapshot, events, replace_critic_policy, allow_queued=allow_queued)
        if critic_extension is not None:
            self._critic_extension_proof(run, snapshot, events, critic_extension, allow_queued=allow_queued)
        proof = run.get("plan_approval")
        if proof:
            accepted = any(item["id"] == proof.get("event_id") and item["agent"] == "human"
                           and item["stage"] == "plan_approved" for item in events)
            if (not accepted or proof.get("payload_hash") != expected_plan_hash
                    or proof.get("request_hash") != canonical_hash(run["request"])
                    or proof.get("source_fingerprint") != self.source.fingerprint):
                raise ReviewError("The prior human plan approval cannot be verified.")
        else:
            # Older checkpoints retained the exact accepted decision when a
            # later node failed. Preserve that evidence; never invent a vote.
            queued = run.get("queued_decision") or {}
            approvals = [item for item in events if item["agent"] == "human" and item["stage"] == "plan_approved"]
            if (queued.get("kind") != "plan" or queued.get("action") != "approve"
                    or queued.get("payload_hash") != expected_plan_hash or queued.get("edits") is not None or not approvals):
                raise ReviewError("The prior human plan approval cannot be verified.")
            proof = {"payload_hash": expected_plan_hash, "request_hash": canonical_hash(run["request"]),
                     "source_fingerprint": self.source.fingerprint, "event_id": approvals[-1]["id"],
                     "evidence_origin": "retained_accepted_plan_decision_and_checkpoint"}
        usage, request = run.get("usage", {}), run["request"]
        if ((critic_extension is None and (usage.get("model_calls", 0) >= request.get("max_model_calls", 12)
                or usage.get("tokens", 0) >= request.get("max_tokens", 100000)))
                or usage.get("tool_calls", 0) >= request.get("max_tool_calls", 60)):
            raise ReviewError("The original run budget is exhausted.")
        return snapshot, proof

    def _critic_retry_proof(self, run, snapshot, events, *, allow_queued=False):
        """One explicit 429 retry of the same frozen critic input, never 403."""
        queued = run.get("queued_continuation") or {}
        attempt = run.get("transient_critic_retry")
        if attempt and not (allow_queued and queued.get("retry_transient") is True
                            and queued.get("draft_hash") == attempt.get("draft_hash")):
            raise ReviewError("The one explicit transient critic retry has already been used.")
        errors = [task.error for task in snapshot.tasks if task.error]
        draft = snapshot.values.get("draft")
        reservations = run.get("usage", {}).get("model_reservations") or {}
        model_events = [item for item in events if item["stage"] in {"model_start", "model_result", "model_error"}]
        last = model_events[-1] if model_events else {}
        call_id = last.get("details", {}).get("call_id")
        if (not str(run.get("error", "")).startswith("ReviewError: provider_http_429:")
                or set(snapshot.next) != {"critic"} or not errors
                or any(not re.match(r"^ReviewError\(['\"]provider_http_429:", str(error)) for error in errors)
                or last.get("agent") != "critic" or last.get("stage") != "model_error"
                or last.get("details", {}).get("error_code") != "provider_http_429"
                or set(reservations) != {call_id} or not isinstance(draft, dict)
                or call_id in {item.get("call_id") for item in run.get("usage", {}).get("calls", [])}
                or any(type(value) is not int or value <= 0 for value in reservations.values())
                or snapshot.values.get("human_edited") or (run.get("pending") or {}).get("kind") == "note"
                or not verify_draft(draft, self.source, require_semantic=False)["passed"]
                or "draft" in run and canonical_hash(run["draft"]) != canonical_hash(draft)):
            raise ReviewError("Only a rate-limited critic with an unchanged checked draft can be retried explicitly.")
        if attempt and (attempt.get("failed_call_id") != call_id or attempt.get("draft_hash") != canonical_hash(draft)):
            raise ReviewError("The frozen critic retry input changed.")
        accounting = run.get("usage", {}).get("gateway_budget") or {}
        if (accounting.get("run_id") != run["id"] or accounting.get("blocked") is not False
                or accounting.get("uncertain_calls") != 1
                or accounting.get("model_calls") != len(run["usage"].get("calls", [])) + 1):
            raise ReviewError("The held critic request needs authoritative unchanged accounting.")
        return {"draft_hash": canonical_hash(draft), "failed_call_id": call_id, "attempt": 1}

    def _critic_policy_replacement_proof(self, run, snapshot, events, expected_hash, *, allow_queued=False):
        """One explicit reviewed critic-policy replacement; no fresh budget."""
        from .model_profiles import model_profile
        profile = model_profile("live-step10-mistral-large2407-v1")
        previous = run.get("usage", {}).get("gateway_budget") or {}
        try:
            budget = self.model_client.budget(run["id"])
            if not isinstance(budget, dict):
                raise ValueError
        except Exception:
            raise ReviewError("The reviewed replacement gateway metadata is unavailable.") from None
        draft = snapshot.values.get("draft")
        transient = run.get("transient_critic_retry") or {}
        replacement = run.get("critic_policy_replacement")
        queued = run.get("queued_continuation") or {}
        if replacement and not (allow_queued and queued.get("replace_critic_policy") == expected_hash
                                and replacement.get("policy_hash") == expected_hash):
            raise ReviewError("The one explicit critic-policy replacement has already been used.")
        reservations = run.get("usage", {}).get("model_reservations") or {}
        model_events = [event for event in events if event["stage"] in {"model_start", "model_result", "model_error"}]
        last = model_events[-1] if model_events else {}
        failed_ids = {event.get("details", {}).get("call_id") for event in events
                      if event["agent"] == "critic" and event["stage"] == "model_error"
                      and event.get("details", {}).get("error_code") == "provider_http_429"}
        errors = [task.error for task in snapshot.tasks if task.error]
        if (not isinstance(expected_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_hash)
                or not str(run.get("error", "")).startswith("ReviewError: provider_http_429:")
                or set(snapshot.next) != {"critic"} or not errors
                or any(not re.match(r"^ReviewError\(['\"]provider_http_429:", str(error)) for error in errors)
                or last.get("agent") != "critic" or last.get("stage") != "model_error"
                or last.get("details", {}).get("error_code") != "provider_http_429"
                or len(reservations) != 2 or set(reservations) != failed_ids
                or transient.get("failed_call_id") not in reservations
                or last.get("details", {}).get("call_id") == transient.get("failed_call_id")
                or any(type(value) is not int or value <= 0 for value in reservations.values())
                or set(reservations) & {item.get("call_id") for item in run["usage"].get("calls", [])}
                or not isinstance(draft, dict) or transient.get("draft_hash") != canonical_hash(draft)
                or snapshot.values.get("human_edited") or (run.get("pending") or {}).get("kind") == "note"
                or not verify_draft(draft, self.source, require_semantic=False)["passed"]
                or "draft" in run and canonical_hash(run["draft"]) != canonical_hash(draft)):
            raise ReviewError("A checked frozen critic checkpoint with both retained rate-limit reservations is required.")
        expected_models = {role: policy["id"] for role, policy in profile["models"].items()}
        if (budget.get("policy_hash") != expected_hash or budget.get("model_profile") != profile["version"]
                or budget.get("models") != expected_models or budget.get("provider") != profile["provider"]
                or (previous.get("models") or {}).get("producer") != expected_models["producer"]
                or (previous.get("models") or {}).get("critic") != "mistralai/mistral-large-2512"
                or budget.get("authorization_id") == previous.get("authorization_id")
                or budget.get("run_id") != run["id"] or budget.get("enabled") is not True or budget.get("blocked") is not False
                or budget.get("uncertain_calls") != 2
                or budget.get("model_calls") != len(run["usage"].get("calls", [])) + 2):
            raise ReviewError("The replacement must be the exact reviewed different critic policy with the same producer and holds.")
        try:
            for key in ("reported_spend_usd", "held_usd", "committed_usd"):
                if Decimal(str(budget[key])) != Decimal(str(previous[key])):
                    raise ValueError
            for key, ceiling in (("cap_usd", "1"), ("per_run_usd", ".50")):
                value = Decimal(str(budget[key]))
                if not value.is_finite() or not 0 < value <= min(Decimal(ceiling), Decimal(str(previous[key]))):
                    raise ValueError
            if Decimal(str(budget["remaining_authorization_usd"])) > Decimal(str(previous["remaining_authorization_usd"])):
                raise ValueError
            limits = {"max_calls_per_run": 12, "max_tokens_per_run": 250000,
                      "prompt_token_ceiling": 49152, "max_message_bytes": 45056, "max_output_tokens": 4096}
            if any(type(budget[key]) is not int or not 0 < budget[key] <= ceiling for key, ceiling in limits.items()):
                raise ValueError
            if (budget["max_calls_per_run"] > run["request"].get("max_model_calls", 12)
                    or budget["max_tokens_per_run"] > run["request"].get("max_tokens", 250000)):
                raise ValueError
            if budget["max_output_tokens"] < 2000:
                raise ValueError
            # Use the gateway's true reservations, not the client's smaller
            # message-size allowance, when deciding if this final call fits.
            reserved_tokens = budget["prompt_token_ceiling"] + 2000
            if (type(budget["tokens"]) is not int or budget["tokens"] != previous["tokens"]
                    or budget["model_calls"] + 1 > min(run["request"].get("max_model_calls", 12), budget["max_calls_per_run"])
                    or budget["tokens"] + reserved_tokens > min(run["request"].get("max_tokens", 250000), budget["max_tokens_per_run"])):
                raise ValueError
            price = profile["models"]["critic"]
            reservation = Decimal(price["prompt_usd_per_token"]) * budget["prompt_token_ceiling"] + Decimal(price["completion_usd_per_token"]) * 2000
            if (Decimal(str(budget["committed_usd"])) + reservation > Decimal(str(budget["per_run_usd"]))
                    or reservation > Decimal(str(budget["remaining_authorization_usd"]))):
                raise ValueError
        except (KeyError, ValueError, TypeError, ArithmeticError):
            raise ReviewError("The replacement must retain all accounting and fit the original dollar, call and token limits.") from None
        proof = {"policy_hash": expected_hash, "draft_hash": canonical_hash(draft),
                 "failed_call_ids": sorted(reservations), "authorization_id": budget["authorization_id"],
                 "model_profile": profile["version"], "critic_model": expected_models["critic"]}
        if replacement and replacement != proof:
            raise ReviewError("The frozen replacement policy or critic input changed.")
        return proof

    def _critic_extension_proof(self, run, snapshot, events, grant_id, *, allow_queued=False):
        """Consume one separately approved exact critic call; original caps stay frozen."""
        from .model_profiles import model_profile
        profile = model_profile("live-step10-google-critic-v1")
        previous = run.get("usage", {}).get("gateway_budget") or {}
        try:
            budget = self.model_client.budget(run["id"])
            grant = budget.get("run_budget_grant") or {}
        except Exception:
            raise ReviewError("The approved critic extension metadata is unavailable.") from None
        queued = run.get("queued_continuation") or {}
        extension = run.get("approved_critic_extension")
        amendment = grant.get("parent_grant_id") is not None
        parent = budget.get("parent_run_budget_grant") or {}
        if amendment:
            history = run.get("critic_extension_history", [])
            prior = history[0] if history else extension
            queued_amendment = (allow_queued and queued.get("critic_extension") == grant_id
                                and (extension or {}).get("grant_id") == grant_id)
            if (not isinstance(prior, dict) or prior.get("max_calls") != 13
                    or prior.get("grant_id") != grant.get("parent_grant_id")
                    or parent.get("grant_id") != prior.get("grant_id")
                    or parent.get("approved") is not True or parent.get("consumed") is not True
                    or {key: value for key, value in prior.items() if key not in {"authorization_id", "config_version"}}
                       != {key: value for key, value in parent.items() if key != "consumed"}
                    or len(history) > 1 or history and not queued_amendment
                    or extension and extension.get("max_calls") == 14 and not queued_amendment):
                raise ReviewError("The amendment requires its unchanged consumed first grant and can be requested only once.")
        elif extension and not (allow_queued and queued.get("critic_extension") == grant_id
                                and extension.get("grant_id") == grant_id):
            raise ReviewError("The one approved critic extension has already been requested.")
        draft = snapshot.values.get("draft")
        reservations = run.get("usage", {}).get("model_reservations") or {}
        transient = run.get("transient_critic_retry") or {}
        replacement = run.get("critic_policy_replacement") or {}
        errors = [task.error for task in snapshot.tasks if task.error]
        model_events = [item for item in events if item["stage"] in {"model_start", "model_result", "model_error"}]
        last = model_events[-1] if model_events else {}
        failed_ids = {item.get("details", {}).get("call_id") for item in events
                      if item["agent"] == "critic" and item["stage"] == "model_error"
                      and item.get("details", {}).get("error_code") == "provider_http_429"}
        expected_error = "model_output_invalid" if amendment else "provider_http_429"
        if (not isinstance(grant_id, str) or not re.fullmatch(r"[a-f0-9]{32}", grant_id)
                or not str(run.get("error", "")).startswith("ReviewError: " + expected_error + ":")
                or set(snapshot.next) != {"critic"} or not errors
                or any(not re.match(r"^ReviewError\(['\"]" + expected_error + ":", str(error)) for error in errors)
                or last.get("agent") != "critic" or last.get("stage") != "model_error"
                or last.get("details", {}).get("error_code") != expected_error
                or len(reservations) != 3 or set(reservations) != failed_ids
                or any(type(value) is not int or value <= 0 for value in reservations.values())
                or set(reservations) & {item.get("call_id") for item in run["usage"].get("calls", [])}
                or transient.get("failed_call_id") not in reservations
                or not set(replacement.get("failed_call_ids", [])) < set(reservations)
                or len(replacement.get("failed_call_ids", [])) != 2
                or last.get("details", {}).get("call_id") in replacement.get("failed_call_ids", [])
                or amendment and (last.get("details", {}).get("call_id") != parent.get("call_id")
                    or parent.get("call_id") in reservations
                    or not any(item.get("call_id") == parent.get("call_id") and item.get("accepted_output") is False
                               for item in run["usage"].get("calls", [])))
                or not isinstance(draft, dict) or transient.get("draft_hash") != canonical_hash(draft)
                or replacement.get("draft_hash") != canonical_hash(draft)
                or snapshot.values.get("human_edited") or (run.get("pending") or {}).get("kind") == "note"
                or not verify_draft(draft, self.source, require_semantic=False)["passed"]
                or canonical_hash(run.get("draft")) != canonical_hash(draft)):
            raise ReviewError("The approved extension requires the same frozen critic checkpoint and all three held rate-limit calls.")
        models = {role: policy["id"] for role, policy in profile["models"].items()}
        if (budget.get("model_profile") != profile["version"] or budget.get("models") != models
                or budget.get("provider") != profile["provider"] or budget.get("providers") != profile["providers"]
                or (previous.get("models") or {}).get("producer") != models["producer"]
                or (previous.get("models") or {}).get("critic") != (models["critic"] if amendment else "mistralai/mistral-large-2407")
                or (budget.get("authorization_id") != previous.get("authorization_id") if amendment
                    else budget.get("authorization_id") == previous.get("authorization_id"))
                or budget.get("run_id") != run["id"] or budget.get("enabled") is not True or budget.get("blocked") is not False
                or grant.get("approved") is not True or grant.get("consumed") is not False
                or grant.get("grant_id") != grant_id or grant.get("run_id") != run["id"]
                or grant.get("policy_hash") != budget.get("policy_hash")
                or not isinstance(grant.get("policy_hash"), str) or not re.fullmatch(r"[a-f0-9]{64}", grant["policy_hash"])
                or grant.get("plan_hash") != canonical_hash(run["plan"])
                or grant.get("draft_hash") != canonical_hash(draft)
                or grant.get("model_profile") != profile["version"] or grant.get("critic_model") != models["critic"]
                or grant.get("role") != "critic" or grant.get("checkpoint_hash") != budget.get("ledger_checkpoint_hash")
                or not isinstance(grant.get("checkpoint_hash"), str) or not re.fullmatch(r"[a-f0-9]{64}", grant["checkpoint_hash"])):
            raise ReviewError("A fresh separately approved grant for this exact Google critic policy and checkpoint is required.")
        try:
            exact = {"original_calls": 12, "original_tokens": 250000, "max_calls": 14 if amendment else 13, "max_tokens": 350000 if amendment else 300000,
                     "checkpoint_calls": 13 if amendment else 12, "checkpoint_tokens": 254246 if amendment else 246409, "checkpoint_uncertain": 3, "reserved_tokens": 51152}
            if any(type(grant[key]) is not int or grant[key] != value for key, value in exact.items()):
                raise ValueError
            if (run["request"].get("max_model_calls") != 12 or run["request"].get("max_tokens") != 250000
                    or budget["original_max_calls_per_run"] != 12 or budget["original_max_tokens_per_run"] != 250000
                    or budget["max_calls_per_run"] != 12 or budget["max_tokens_per_run"] != 250000
                    or budget["prompt_token_ceiling"] != 49152 or budget["max_message_bytes"] != 45056
                    or type(budget["max_output_tokens"]) is not int or not 2000 <= budget["max_output_tokens"] <= 4096
                    or budget["model_calls"] != exact["checkpoint_calls"] or budget["tokens"] != exact["checkpoint_tokens"] or budget["uncertain_calls"] != 3
                    or budget["model_calls"] != len(run["usage"].get("calls", [])) + len(reservations)
                    or budget["model_calls"] != previous["model_calls"] or budget["tokens"] != previous["tokens"]
                    or budget["tokens"] + grant["reserved_tokens"] > grant["max_tokens"]):
                raise ValueError
            for key in ("reported_spend_usd", "held_usd", "committed_usd"):
                if Decimal(str(budget[key])) != Decimal(str(previous[key])):
                    raise ValueError
            for key, limit in (("cap_usd", "1"), ("per_run_usd", ".50")):
                value = Decimal(str(budget[key]))
                if (not value.is_finite() or not 0 < value <= min(Decimal(limit), Decimal(str(previous[key])))
                        or Decimal(str(grant[key])) != value):
                    raise ValueError
            if (Decimal(str(grant["checkpoint_reported_spend_usd"])) != Decimal(str(budget["reported_spend_usd"]))
                    or Decimal(str(grant["checkpoint_held_usd"])) != Decimal(str(budget["held_usd"]))
                    or Decimal(str(budget["remaining_authorization_usd"])) > Decimal(str(previous["remaining_authorization_usd"]))):
                raise ValueError
            price = profile["models"]["critic"]
            reservation = Decimal(price["prompt_usd_per_token"]) * 49152 + Decimal(price["completion_usd_per_token"]) * 2000
            if (Decimal(str(grant["reservation_usd"])) != reservation
                    or Decimal(str(budget["committed_usd"])) + reservation > Decimal(str(budget["per_run_usd"]))
                    or reservation > Decimal(str(budget["remaining_authorization_usd"]))):
                raise ValueError
            request = critic_extension_request(draft, run["id"], grant_id, budget)
            if (grant["call_id"] != request["call_id"] or grant["request_hash"] != canonical_hash(request)
                    or len(json.dumps({key: request[key] for key in ("messages", "response_schema")}, sort_keys=True,
                                      separators=(",", ":"), ensure_ascii=False).encode()) > budget["max_message_bytes"]):
                raise ValueError
        except (KeyError, ValueError, TypeError, ArithmeticError):
            raise ReviewError("The exact approved critic request must fit its one-call extension with every original hold and dollar cap retained.") from None
        proof = {key: deepcopy(value) for key, value in grant.items() if key != "consumed"}
        proof["authorization_id"] = budget["authorization_id"]
        proof["config_version"] = budget["config_version"]
        if extension and (not amendment or extension.get("grant_id") == grant_id) and extension != proof:
            raise ReviewError("The approved critic extension or frozen request changed.")
        return proof

    def claim_continuation(self, run_id, expected_plan_hash, *, retry_transient=False, replace_critic_policy=None, critic_extension=None):
        with self.lock(run_id):
            run = self.store.get_run(run_id)
            if not run or run.get("status") != "error":
                raise ReviewError("Only a stopped content-check failure can be continued once.")
            snapshot, proof = self._continuation_checkpoint(run, expected_plan_hash, retry_transient=retry_transient,
                                                          replace_critic_policy=replace_critic_policy, critic_extension=critic_extension)
            run.update(status="running", stage="continuing", plan_approval=proof,
                       queued_continuation={"plan_hash": expected_plan_hash,
                                            "checkpoint_id": snapshot.config["configurable"]["checkpoint_id"],
                                            "source_fingerprint": self.source.fingerprint})
            if retry_transient:
                retry = self._critic_retry_proof(run, snapshot, self.store.events(run_id))
                run["transient_critic_retry"] = retry
                run["draft"] = deepcopy(snapshot.values["draft"])
                run["queued_continuation"].update(retry_transient=True, draft_hash=retry["draft_hash"])
            if replace_critic_policy is not None:
                replacement = self._critic_policy_replacement_proof(run, snapshot, self.store.events(run_id), replace_critic_policy)
                run["critic_policy_replacement"] = replacement
                run["draft"] = deepcopy(snapshot.values["draft"])
                run["queued_continuation"].update(replace_critic_policy=replace_critic_policy, draft_hash=replacement["draft_hash"])
            if critic_extension is not None:
                extension = self._critic_extension_proof(run, snapshot, self.store.events(run_id), critic_extension)
                prior = run.get("approved_critic_extension")
                if prior and prior.get("grant_id") != extension["grant_id"]:
                    run.setdefault("critic_extension_history", []).append(deepcopy(prior))
                run["approved_critic_extension"] = extension
                run["draft"] = deepcopy(snapshot.values["draft"])
                run["queued_continuation"].update(critic_extension=critic_extension, draft_hash=extension["draft_hash"])
            run.pop("queued_decision", None)
            run.pop("pending", None)
            self.store.save_run(run)
            self.event(run_id, "system", "continuation_requested",
                       ("The operator explicitly requested a separately approved one-call critic extension under the existing approved plan and original dollar ceilings."
                        if critic_extension is not None else "The operator explicitly continued the stopped research under the existing approved plan and original budgets."), payload_hash=expected_plan_hash,
                       retry_transient=retry_transient, replace_critic_policy=replace_critic_policy, critic_extension=critic_extension)

    def claim(self, run_id, decision):
        with self.lock(run_id):
            run = self.store.get_run(run_id)
            pending = run.get("pending", {})
            if run["status"] != "awaiting_" + decision["kind"] or pending.get("payload_hash") != decision["payload_hash"] or pending.get("kind") != decision["kind"]:
                raise ReviewError("Stale review or another decision is already running.")
            if decision["action"] != "reject" and run.get("source_fingerprint") not in (None, self.source.fingerprint):
                raise ReviewError("The source snapshot changed. Create a new research plan before approving or editing.")
            if decision["action"] != "reject":
                self._validate_memory(run)
            if decision["action"] == "approve" and decision["kind"] == "note" and not run.get("critic", {}).get("passed"):
                raise ReviewError("Unresolved checks prevent publication.")
            run.update(status="running", stage="resuming", queued_decision=decision)
            self.store.save_run(run)

    def _annual_source_coverage(self, tickers, years):
        """Describe code-vetted annual inputs without claiming full risk coverage."""
        periods = []
        for ticker in tickers:
            facts = self.source.facts(ticker, years)
            for year in years:
                pair = {}
                for concept in ("revenue", "operating_income"):
                    matches = [fact for fact in facts if fact["fiscal_year"] == year and fact["concept"] == concept]
                    if len(matches) != 1:
                        raise ReviewError("Planning requires one canonical annual input for each concept, issuer and fiscal year.")
                    pair[concept] = matches[0]
                revenue, income = self.source.canonical_pair(pair["revenue"]["id"], pair["operating_income"]["id"])
                periods.append({"ticker": ticker, "fiscal_year": year,
                    "period_start": revenue["start"], "period_end": revenue["end"],
                    "revenue_fact_id": revenue["id"], "operating_income_fact_id": income["id"]})
        return {"source_fingerprint": self.source.fingerprint, "financial_scope": "reported_annual",
                "annual_financial_inputs_complete": True, "annual_periods": periods,
                "risk_original_sections_complete": False}

    def _plan(self, state):
        request = state["request"]
        validate_scope(request, self.source)
        memory_context = self._freeze_memory(state, request["tickers"], request["years"])
        if self.is_live(state):
            coverage = self._annual_source_coverage(request["tickers"], request["years"])
            plan = self.reasoner(state, "plan").plan(request["question"], request["tickers"], request["years"], source_coverage=coverage)
            plan["mode"] = "live"
            plan["memory_context"] = memory_context
            self.event(state["run_id"], "planner", "plan", "AI research plan prepared; waiting for the analyst.")
            return {"plan": plan, "memory_context": memory_context}
        plan = {"tickers": request["tickers"], "years": request["years"],
                "outline": ["Inspect original annual facts and actual fiscal periods", "Calculate and independently verify operating margins", "Compare cached adjacent-year risk sections; original boundaries require human domain review", "Draft a cited note and identify limits"],
                "caveats": ["Offline deterministic teaching workflow; no language model or semantic judgment.", "Fiscal-year labels do not align different company calendars."], "memory_context": memory_context}
        self.event(state["run_id"], "planner", "plan", "Research plan prepared; waiting for the analyst.")
        return {"plan": plan, "memory_context": memory_context}

    def _review_plan(self, state):
        plan = state["plan"]
        decision = interrupt({"kind": "plan", "payload": plan, "payload_hash": canonical_hash(plan)})
        if decision["payload_hash"] != canonical_hash(plan):
            raise ReviewError("Plan version changed.")
        action = decision["action"]
        if action == "reject":
            self.event(state["run_id"], "human", "plan_rejected", "The analyst rejected the plan; nothing was published.")
            return {"status": "rejected", "plan_action": "reject"}
        self._validate_memory(state)
        if action == "edit":
            edits = decision.get("edits") or {}
            if set(edits) - {"tickers", "years", "outline"}:
                raise ReviewError("Unsupported plan edit fields.")
            updated = {**plan, **edits}
            validate_scope({**updated, "mode": "live" if self.is_live(state) else "offline"}, self.source)
            if self.is_live(state):
                updated["source_coverage"] = self._annual_source_coverage(updated["tickers"], updated["years"])
            memory_context = self._freeze_memory(state, updated["tickers"], updated["years"])
            updated["memory_context"] = memory_context
            self.event(state["run_id"], "human", "plan_edit", "Plan edited; review the new version before continuing.")
            return {"plan": updated, "plan_action": "edit", "memory_context": memory_context}
        approval = self.store.event(state["run_id"], "human", "plan_approved", "The analyst approved this exact plan.", {"payload_hash": canonical_hash(plan)})
        run = self.store.get_run(state["run_id"])
        run["plan_approval"] = {"payload_hash": canonical_hash(plan), "request_hash": canonical_hash(run["request"]),
                                "source_fingerprint": self.source.fingerprint, "event_id": approval["id"]}
        self.store.save_run(run)
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
        memory_context = self._validate_memory(state)
        history = self._history_sentence(memory_context)
        body = "Offline research rehearsal using actual SEC sources. Financial arithmetic is independently checked; narrative semantic review has not been run.\n\n## Verified operating margins\n" + table + "\n\n## Cached risk-section text comparison\n" + ("\n".join(risk_lines) or "No adjacent-year comparison is available.") + "\n\n## Limits and history\nFiscal periods differ across companies. Original Item boundaries require human domain review. Cached text differences do not establish changes in economic risk. This draft provides no investment recommendation.\n" + history
        if memory_context and memory_context["report_style"] == "summary_first":
            body = body.replace("\n\n## Verified operating margins\n" + table, "").replace("\n\n## Limits and history", "\n\n## Verified operating margins\n" + table + "\n\n## Limits and history", 1)
        draft = {"run_id": state["run_id"], "actor": state["actor"], "title": " / ".join(state["plan"]["tickers"]) + " annual research note", "body": body,
                 "numeric_table": table, "metrics": state["metrics"], "risks": state["risks"], "plan": state["plan"],
                 "source_kind": "sec_edgar", "model_mode": "offline", "source_fingerprint": self.source.fingerprint}
        if memory_context is not None:
            draft.update(memory_context=memory_context, report_style=memory_context["report_style"])
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
        model_plan = {key: value for key, value in state["plan"].items() if key != "memory_context"}
        written = self.reasoner(state, "writer:" + str(state.get("repairs", 0))).write(question, model_plan, state["metrics"], state.get("risk_ai", []), known)
        provisional_risk_claims = [claim for analysis in state.get("risk_ai", []) for comparison in analysis["comparisons"] for claim in comparison["claims"]]
        risk_claims = written["risk_claims"]
        memory_context = self._validate_memory(state)
        history = self._history_sentence(memory_context)
        draft = {"run_id": state["run_id"], "actor": state["actor"], "title": " / ".join(state["plan"]["tickers"]) + " AI-assisted annual research note",
            "numeric_table": table, "metrics": state["metrics"], "risks": state["risks"], "plan": state["plan"], "source_kind": "sec_edgar", "model_mode": "live", "source_fingerprint": self.source.fingerprint,
            "narrative_claims": risk_claims + written["claims"], "ai_evidence": known, "evidence_selection": [analysis["selection"] for analysis in state.get("risk_ai", [])],
            "provisional_risk_claims": provisional_risk_claims, "risk_revision_method": "writer_refined_against_same_sources",
            "live_sections": {"risk_ids": [claim["claim_id"] for claim in risk_claims], "writer_ids": [claim["claim_id"] for claim in written["claims"]]}, "history_sentence": history}
        if memory_context is not None:
            draft.update(memory_context=memory_context, report_style=memory_context["report_style"])
        draft["body"] = live_body(draft)
        self.event(state["run_id"], "writer", "draft", "Cited AI narrative and code-verified table prepared for source-support checks.")
        return {"draft": draft, "human_edited": False}

    def _critic(self, state):
        draft = deepcopy(state["draft"])
        draft.pop("semantic_verdict", None)
        critic = verify_draft(draft, self.source, require_semantic=False)
        if self.is_live(state) and critic["passed"]:
            purpose = "critic:" + semantic_input_hash(draft)
            current_run = self.store.get_run(state["run_id"])
            extension = current_run.get("approved_critic_extension")
            replacement = current_run.get("critic_policy_replacement")
            retry = current_run.get("transient_critic_retry")
            if extension:
                purpose += ":explicit-approved-extension:" + extension["grant_id"]
            elif replacement:
                purpose += ":explicit-policy-replacement:" + replacement["policy_hash"]
            elif retry:
                purpose += ":explicit-429-retry:" + str(retry["attempt"])
            verdict = self.reasoner(state, purpose).critique(draft, draft["ai_evidence"])
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
        self._validate_memory(state)
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
        self._validate_memory(state)
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
    if value.get("mode") == "live" and len(tickers) * max(0, len(years) - 1) > 4:
        raise ReviewError("Live research supports at most four company/year risk comparisons. Choose fewer companies or fiscal years.")
    if "outline" in value and (not isinstance(value["outline"], list) or not value["outline"] or not all(isinstance(item, str) and item.strip() for item in value["outline"])):
        raise ReviewError("The plan needs a nonempty research outline.")
