"""Live graph integration with real schemas/ledger boundaries and fake paid transport."""
from copy import deepcopy
from decimal import Decimal
import json

import pytest

from desk.provider import ProviderError
from desk.workflow import ReviewError, verify_draft
from desk.store import canonical_hash
from test_workflow import fixture, decide


class FakeModelClient:
    """Fictional model outputs; never a substitute for live-run evidence."""
    def __init__(self):
        self.calls = []
        self.cache = {}

    def complete(self, **request):
        identifier = request["call_id"]
        if identifier in self.cache:
            return {**deepcopy(self.cache[identifier]), "cached": True}
        self.calls.append(request)
        stage = request["role"]
        context = json.loads(request["messages"][-1]["content"])
        if stage == "planner":
            content = {"outline": ["Inspect scoped annual evidence", "Check margins and cited disclosures"], "caveats": ["Selected evidence is incomplete."]}
        elif stage == "researcher":
            content = {"query": "annual revenue operating income and disclosed risks", "focus": "Source-backed annual evidence"}
        elif stage == "risk":
            def quote_id(year):
                return next(row["quote_id"] for row in context["quote_menu"] if row["year"] == year)
            content = {"comparisons": {key: {"status": "evidence_available",
                "findings": [{"text": "Selected disclosures discuss operational uncertainty.", "confidence": "low",
                              "before_quote_id": quote_id(pair["before_year"]), "after_quote_id": quote_id(pair["after_year"])}]}
                                      for key, pair in context["comparison_keys"].items()}}
        elif stage == "writer":
            row = next(row for row in context["quote_menu"] if "item1A" in row["source_id"])
            revisions = {claim["claim_id"]: {"text": claim["text"], "confidence": claim["confidence"],
                "before_quote_id": next(option["quote_id"] for option in context["quote_menu"]
                                        if option["ticker"] == claim["ticker"] and option["year"] == claim["before_year"]
                                        and option["source_id"] in {citation["source_id"] for citation in claim["citations"]}),
                "after_quote_id": next(option["quote_id"] for option in context["quote_menu"]
                                       if option["ticker"] == claim["ticker"] and option["year"] == claim["after_year"]
                                       and option["source_id"] in {citation["source_id"] for citation in claim["citations"]})}
                         for claim in context["risk_observations"]}
            content = {"risk_revisions": revisions, "claims": [{"text": "Selected source excerpts provide limited disclosure context.", "confidence": "low", "category": "limitation",
                "quote_ids": [row["quote_id"]]}]}
        elif stage == "critic":
            bad = "certain disaster" in context["body"]
            content = {"issues": ["The edited claim overstates the evidence."] if bad else [],
                "verdicts": [{"claim_id": claim["claim_id"], "supported": not bad, "reason": "Test-only model support judgment."} for claim in context["claims"]]}
        else:
            raise AssertionError(stage)
        result = {"content": content, "cached": False, "config_version": "test-only-v1", "usage": {"call_id": identifier,
            "model": "fictional-test-model", "model_calls": 1, "prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20, "cost_usd": "0.001"}}
        self.cache[identifier] = deepcopy(result)
        return result


def begin_live(engine, store, max_tokens=250000, max_model_calls=12):
    request = {"question": "Compare annual source-backed margins and risks.", "tickers": ["MSFT", "AAPL"], "years": [2023, 2024, 2025],
        "mode": "live", "max_tool_calls": 60, "max_tokens": max_tokens, "max_model_calls": max_model_calls}
    return engine.execute(store.create_run(request)["id"])


class ContentFailureClient(FakeModelClient):
    def __init__(self):
        super().__init__()
        self.invalid_risk = True

    def complete(self, **request):
        result = super().complete(**request)
        if request["role"] == "risk" and self.invalid_risk:
            next(iter(result["content"]["comparisons"].values()))["findings"][0]["after_quote_id"] = "quote-not-in-supplied-menu"
            self.cache[request["call_id"]] = deepcopy(result)
        return result


def content_failure(engine, store, *, max_model_calls=12):
    engine.model_client = ContentFailureClient()
    plan = begin_live(engine, store, max_model_calls=max_model_calls)
    failed = decide(engine, plan)
    assert failed["status"] == "error" and failed["failure_kind"] == "content_validation"
    assert failed["usage"]["model_calls"] == 4
    return plan, failed


def test_writer_refines_provisional_risk_and_critic_checks_exact_revision(fixture):
    engine, store, source, _, _, _ = fixture
    provisional = "Selected disclosures establish consistent scope and framing."
    revised = "Selected excerpts describe conditional operational uncertainty."
    class RefiningClient(FakeModelClient):
        def complete(self, **request):
            result = super().complete(**request)
            if request["role"] == "risk":
                next(iter(result["content"]["comparisons"].values()))["findings"][0]["text"] = provisional
            if request["role"] == "writer":
                for revision in result["content"]["risk_revisions"].values():
                    if revision["text"] == provisional:
                        revision["text"] = revised
            self.cache[request["call_id"]] = deepcopy(result)
            return result
    engine.model_client = RefiningClient()
    note = decide(engine, begin_live(engine, store))
    assert note["status"] == "awaiting_note", note.get("error")
    draft = note["draft"]
    assert any(item["text"] == provisional for item in draft["provisional_risk_claims"])
    assert provisional not in draft["body"] and revised in draft["body"]
    assert draft["risk_revision_method"] == "writer_refined_against_same_sources"
    original = {item["claim_id"]: item for item in draft["provisional_risk_claims"]}
    for item in draft["narrative_claims"]:
        if item["claim_id"] in original:
            for field in ("ticker", "before_year", "after_year", "category"):
                assert item[field] == original[item["claim_id"]][field]
    critic_call = next(call for call in engine.model_client.calls if call["role"] == "critic")
    critic_context = json.loads(critic_call["messages"][-1]["content"])
    assert critic_context["body"] == draft["body"]
    assert all(item["text"] != provisional for item in critic_context["claims"])
    assert verify_draft(draft, source)["passed"] and store.notes() == []


@pytest.mark.parametrize("legacy", [False, True])
def test_explicit_content_continuation_keeps_existing_approval_request_and_usage(fixture, monkeypatch, legacy):
    from desk import reasoning
    engine, store, source, _, _, _ = fixture
    plan, failed = content_failure(engine, store)
    plan_hash = plan["pending"]["payload_hash"]
    original_request, original_calls = deepcopy(failed["request"]), deepcopy(failed["usage"]["calls"])
    if legacy:
        # The deployed failure predates these explicit metadata fields. Its
        # accepted queued decision and completed approval checkpoint remain.
        stored = store.get_run(failed["id"])
        for field in ("plan_approval", "source_fingerprint", "failure_kind"):
            stored.pop(field, None)
        store.save_run(stored)
    assert engine.view(failed["id"])["continuation"] == {
        "available": True, "plan_hash": plan_hash, "failure_kind": "content_validation"}
    assert engine.execute(failed["id"])["status"] == "error"
    assert len(engine.model_client.calls) == 4  # No implicit retry.
    engine.claim_continuation(failed["id"], plan_hash)
    with pytest.raises(ReviewError, match="once"):
        engine.claim_continuation(failed["id"], plan_hash)
    assert store.get_run(failed["id"])["request"] == original_request
    assert store.get_run(failed["id"])["usage"]["calls"] == original_calls
    if legacy:
        assert store.get_run(failed["id"])["plan_approval"]["evidence_origin"] == "retained_accepted_plan_decision_and_checkpoint"
    # Revised trusted instructions produce a new content-addressed call ID;
    # earlier completed graph nodes and their billed results stay in place.
    engine.model_client.invalid_risk = False
    monkeypatch.setattr(reasoning, "COMMON_INSTRUCTIONS", reasoning.COMMON_INSTRUCTIONS + " Use only the supplied quotation identifiers.")
    note = engine.execute(failed["id"])
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["request"] == original_request and note["plan"] == plan["plan"]
    assert note["usage"]["model_calls"] == len(engine.model_client.calls) == 8
    assert note["usage"]["calls"][:4] == original_calls and note["usage"]["cost_usd"] == .008
    assert [call["role"] for call in engine.model_client.calls].count("planner") == 1
    assert [call["role"] for call in engine.model_client.calls].count("researcher") == 2
    assert sum(event["stage"] == "plan_approved" for event in note["events"]) == 1
    assert sum(event["stage"] == "continuation_requested" for event in note["events"]) == 1
    assert "error" not in note and "queued_continuation" not in note and store.notes() == []
    assert verify_draft(note["draft"], source)["passed"]
    with pytest.raises(ReviewError):
        engine.claim_continuation(note["id"], plan_hash)


@pytest.mark.parametrize("change", ["stale_hash", "request", "plan", "source", "approval", "uncertain", "provider_error", "failure_kind"])
def test_continuation_rejects_changed_scope_missing_approval_or_uncertainty(fixture, change):
    engine, store, _, _, _, _ = fixture
    plan, failed = content_failure(engine, store)
    stored = store.get_run(failed["id"])
    expected_hash = plan["pending"]["payload_hash"]
    if change == "stale_hash":
        expected_hash = "f" * 64
    elif change == "request":
        stored["request"]["max_tokens"] += 1000
    elif change == "plan":
        stored["plan"]["outline"].append("Unreviewed extra work")
    elif change == "source":
        stored["source_fingerprint"] = "changed-source"
    elif change == "approval":
        stored.pop("plan_approval", None)
        stored.pop("queued_decision", None)
    elif change == "uncertain":
        stored["usage"]["model_reservations"] = {"unresolved-provider-call": 100}
    elif change == "provider_error":
        stored["error"] = "ReviewError: provider_usage_uncertain"
    else:
        stored["failure_kind"] = "not_continuable"
    store.save_run(stored)
    before = deepcopy(store.get_run(failed["id"]))
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], expected_hash)
    assert store.get_run(failed["id"]) == before and len(engine.model_client.calls) == 4
    assert store.notes() == []


def test_continuation_does_not_reset_exhausted_original_call_budget(fixture):
    engine, store, _, _, _, _ = fixture
    plan, failed = content_failure(engine, store, max_model_calls=4)
    assert failed["continuation"]["available"] is False
    with pytest.raises(ReviewError, match="budget"):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"])
    assert len(engine.model_client.calls) == 4 and store.get_run(failed["id"])["request"]["max_model_calls"] == 4


def test_checkpoint_failure_between_claim_and_execution_stops_without_model_requests(fixture, monkeypatch):
    engine, store, _, _, _, _ = fixture
    plan, failed = content_failure(engine, store)
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"])
    def unavailable(*args, **kwargs):
        raise RuntimeError("private-checkpoint-error")
    monkeypatch.setattr(engine.graph, "get_state", unavailable)
    stopped = engine.execute(failed["id"])
    assert stopped["status"] == "error" and len(engine.model_client.calls) == 4
    assert stopped["usage"] == failed["usage"]
    assert "private-checkpoint-error" not in json.dumps(stopped)
    assert "queued_continuation" not in store.get_run(failed["id"])


def test_live_graph_uses_seven_structured_model_calls_and_separate_human_gates(fixture):
    engine, store, source, tool_calls, _, _ = fixture
    client = engine.model_client = FakeModelClient()
    plan = begin_live(engine, store)
    assert plan["status"] == "awaiting_plan" and plan["mode"] == "live"
    assert len(client.calls) == 1 and tool_calls == []
    note = decide(engine, plan)
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["critic"]["passed"] and note["critic"]["semantic_review"] == "model_assisted_not_gold"
    assert note["critic"]["verified_numbers"] == 18
    assert note["usage"]["model_calls"] == 7 and len(client.calls) == 7
    assert len(note["draft"]["narrative_claims"]) == 5
    assert verify_draft(note["draft"], source)["passed"]
    assert store.notes() == []
    published = decide(engine, note)
    assert published["status"] == "published", published.get("error")
    assert published["usage"]["model_calls"] == 7 and len(store.notes()) == 1
    assert published["usage"]["tool_calls"] == 17  # Local frozen history replaces the old unbounded portal read.


def test_live_planner_uses_vetted_annual_coverage_for_every_requested_period(fixture):
    engine, store, source, tool_calls, _, _ = fixture
    engine.model_client = FakeModelClient()
    plan = begin_live(engine, store)
    assert plan["status"] == "awaiting_plan" and tool_calls == []
    context = json.loads(engine.model_client.calls[0]["messages"][-1]["content"])
    coverage = context["source_coverage"]
    assert coverage == plan["plan"]["source_coverage"]
    assert coverage["annual_financial_inputs_complete"] is True
    assert coverage["risk_original_sections_complete"] is False
    assert coverage["source_fingerprint"] == source.fingerprint
    assert {(row["ticker"], row["fiscal_year"]) for row in coverage["annual_periods"]} == {
        (ticker, year) for ticker in ("MSFT", "AAPL") for year in (2023, 2024, 2025)}
    for row in coverage["annual_periods"]:
        revenue, income = source.canonical_pair(row["revenue_fact_id"], row["operating_income_fact_id"])
        assert row["period_start"] == revenue["start"] and row["period_end"] == income["end"]


def test_live_planning_missing_annual_pair_stops_before_any_model_call(fixture):
    engine, store, source, tool_calls, _, _ = fixture
    engine.model_client = FakeModelClient()
    del source._facts["test:MSFT:2025:operating_income"]
    run = begin_live(engine, store)
    assert run["status"] == "error" and engine.model_client.calls == [] and tool_calls == []
    assert store.notes() == []


def test_live_scope_edit_refreshes_annual_coverage_without_another_model_call(fixture):
    engine, store, _, tool_calls, _, _ = fixture
    engine.model_client = FakeModelClient()
    original = begin_live(engine, store)
    edited = decide(engine, original, "edit", {"years": [2024, 2025]})
    assert edited["status"] == "awaiting_plan", edited.get("error")
    assert {(row["ticker"], row["fiscal_year"]) for row in edited["plan"]["source_coverage"]["annual_periods"]} == {
        (ticker, year) for ticker in ("MSFT", "AAPL") for year in (2024, 2025)}
    assert len(engine.model_client.calls) == 1 and tool_calls == []
    assert edited["pending"]["payload_hash"] != original["pending"]["payload_hash"]


def test_live_note_edit_invalidates_previous_verdict_and_gets_exact_body_review(fixture):
    engine, store, _, _, _, _ = fixture
    engine.model_client = FakeModelClient()
    note = decide(engine, begin_live(engine, store))
    body = note["draft"]["body"].replace("Selected disclosures discuss operational uncertainty.", "Selected disclosures establish a certain disaster.", 1)
    edited = decide(engine, note, "edit", {"body": body})
    assert edited["status"] == "awaiting_note", edited.get("error")
    assert not edited["critic"]["passed"] and edited["usage"]["model_calls"] == 8
    assert edited["draft"]["semantic_verdict"]["body_hash"] != note["draft"]["semantic_verdict"]["body_hash"]
    with pytest.raises(ReviewError):
        engine.claim(edited["id"], {"kind": "note", "action": "approve", "payload_hash": note["pending"]["payload_hash"]})
    with pytest.raises(ReviewError, match="Unresolved"):
        engine.claim(edited["id"], {"kind": "note", "action": "approve", "payload_hash": edited["pending"]["payload_hash"]})
    assert store.notes() == []


def test_changed_table_or_unstructured_prose_blocks_before_another_paid_critic(fixture):
    engine, store, _, _, _, _ = fixture
    engine.model_client = FakeModelClient()
    note = decide(engine, begin_live(engine, store))
    edited = decide(engine, note, "edit", {"body": note["draft"]["body"] + "\nUnlisted source-free conclusion."})
    assert edited["status"] == "awaiting_note" and not edited["critic"]["passed"]
    assert edited["usage"]["model_calls"] == 7
    assert "semantic_verdict" not in edited["draft"] and store.notes() == []


def test_changed_evidence_cannot_reuse_a_passing_semantic_verdict(fixture):
    engine, store, source, _, _, _ = fixture
    engine.model_client = FakeModelClient()
    note = decide(engine, begin_live(engine, store))
    changed = deepcopy(note["draft"])
    changed["ai_evidence"][0]["text"] = "Invented replacement source evidence."
    assert not verify_draft(changed, source)["passed"]
    changed = deepcopy(note["draft"])
    changed["semantic_verdict"]["checked_input_hash"] = "0" * 64
    assert not verify_draft(changed, source)["passed"]


def test_live_request_tiny_budget_or_missing_gateway_never_silently_uses_offline(fixture):
    engine, store, _, tool_calls, _, _ = fixture
    missing = begin_live(engine, store)
    assert missing["status"] == "error" and store.notes() == [] and tool_calls == []
    engine.model_client = FakeModelClient()
    tiny = begin_live(engine, store, max_tokens=100)
    assert tiny["status"] == "error" and engine.model_client.calls == []
    assert tiny["usage"]["model_calls"] == 0


def test_provider_failure_holds_request_reservation_and_never_publishes(fixture):
    engine, store, _, _, _, _ = fixture
    class FailingClient:
        def complete(self, **request):
            raise ProviderError("provider_request_failed", "The provider refused the bounded request.")
    engine.model_client = FailingClient()
    failed = begin_live(engine, store)
    assert failed["status"] == "error" and failed["usage"]["model_reservations"]
    assert "provider_request_failed" in failed["error"]
    event = next(item for item in failed["events"] if item["stage"] == "model_error")
    assert event["details"]["error_code"] == "provider_request_failed"
    assert failed["usage"]["cost_usd"] is None and failed["usage"]["accounting_status"] == "unknown_after_failure"
    assert store.notes() == []


def test_billed_failure_reports_authoritative_gateway_cost_instead_of_zero(fixture):
    engine, store, _, _, _, _ = fixture
    class BilledFailure:
        def complete(self, **request):
            raise ProviderError("model_output_invalid", "The billed model output was invalid.")
        def budget(self, run_id):
            return {"model_calls": 1, "reported_spend_usd": "0.002", "held_usd": "0", "committed_usd": "0.002"}
    engine.model_client = BilledFailure()
    run = begin_live(engine, store)
    assert run["status"] == "error" and run["usage"]["model_calls"] == 1
    assert run["usage"]["cost_usd"] == .002 and run["usage"]["committed_usd"] == .002
    assert store.notes() == []


def test_unrecognized_gateway_code_is_not_copied_into_run_trace(fixture):
    engine, store, _, _, _, _ = fixture
    private_code = "invented-private-response-value"
    class FailingClient:
        def complete(self, **request):
            raise ProviderError(private_code, "The model gateway blocked or failed the operation.")
    engine.model_client = FailingClient()
    run = begin_live(engine, store)
    assert run["status"] == "error" and private_code not in json.dumps(run)
    event = next(item for item in run["events"] if item["stage"] == "model_error")
    assert event["details"]["error_code"] == "gateway_request_failed"


class RateLimitedCritic(FakeModelClient):
    """Fictional held critic attempt, not a real provider response."""
    def __init__(self, *, code="provider_http_429", fail_accounting_after_retry=False, reject=False, repeat_failure=False):
        super().__init__()
        self.failed_id = None
        self.code = code
        self.fail_accounting_after_retry = fail_accounting_after_retry
        self.reject = reject
        self.repeat_failure = repeat_failure

    def complete(self, **request):
        if request["role"] == "critic" and (self.failed_id is None or self.repeat_failure):
            self.failed_id = self.failed_id or request["call_id"]
            self.calls.append(deepcopy(request))
            raise ProviderError(self.code, "Test-only temporary provider failure.")
        result = super().complete(**request)
        if request["role"] == "critic" and self.reject:
            result["content"]["issues"] = ["Test-only source support concern."]
            result["content"]["verdicts"][0]["supported"] = False
            self.cache[request["call_id"]] = deepcopy(result)
        return result

    def budget(self, run_id):
        if self.fail_accounting_after_retry and len(self.cache) >= 7:
            raise RuntimeError("test-only unavailable accounting")
        cost = Decimal(len(self.cache)) * Decimal("0.001")
        held = Decimal("0.035768")
        return {"run_id": run_id, "blocked": False, "uncertain_calls": 1,
                "model_calls": len(self.calls), "reported_spend_usd": str(cost),
                "held_usd": str(held), "committed_usd": str(cost + held),
                "tokens": len(self.cache) * 20 + 67536}


def critic_rate_failure(engine, store, *, max_model_calls=12, **options):
    engine.model_client = RateLimitedCritic(**options)
    plan = begin_live(engine, store, max_model_calls=max_model_calls)
    failed = decide(engine, plan)
    assert failed["status"] == "error" and len(engine.model_client.calls) == 7
    return plan, failed


@pytest.mark.parametrize("legacy", [False, True])
def test_one_explicit_critic_429_retry_preserves_frozen_draft_holds_and_approval(fixture, legacy):
    engine, store, source, _, _, _ = fixture
    plan, failed = critic_rate_failure(engine, store)
    original_request = deepcopy(failed["request"])
    original_calls = deepcopy(failed["usage"]["calls"])
    original_reservations = deepcopy(failed["usage"]["model_reservations"])
    if legacy:
        stored = store.get_run(failed["id"])
        for field in ("draft", "source_fingerprint", "plan_approval", "failure_kind"):
            stored.pop(field, None)
        store.save_run(stored)
    view = engine.view(failed["id"])
    assert view["continuation"]["available"] is False
    assert view["continuation"]["retry_transient_available"] is True
    assert engine.execute(failed["id"])["status"] == "error" and len(engine.model_client.calls) == 7
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"])
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)
    claimed = store.get_run(failed["id"])
    assert claimed["usage"]["model_reservations"] == original_reservations
    assert claimed["transient_critic_retry"]["draft_hash"] == canonical_hash(claimed["draft"])
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)
    note = engine.execute(failed["id"])
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["request"] == original_request and note["plan"] == plan["plan"]
    assert note["usage"]["calls"][:6] == original_calls
    assert note["usage"]["model_reservations"] == original_reservations
    assert note["usage"]["model_calls"] == len(engine.model_client.calls) == 8
    assert len(note["usage"]["calls"]) == 7 and note["usage"]["tokens"] == 140
    assert note["usage"]["held_usd"] == .035768 and note["usage"]["cost_usd"] == .007
    assert note["usage"]["gateway_budget"]["tokens"] > note["usage"]["tokens"]
    critic_calls = [request for request in engine.model_client.calls if request["role"] == "critic"]
    assert critic_calls[0]["call_id"] != critic_calls[1]["call_id"]
    assert critic_calls[0]["messages"] == critic_calls[1]["messages"]
    assert sum(event["stage"] == "plan_approved" for event in note["events"]) == 1
    assert verify_draft(note["draft"], source)["passed"] and store.notes() == []


@pytest.mark.parametrize("change", ["403", "timeout", "other_reservation", "draft", "plan", "accounting", "exhausted"])
def test_explicit_429_retry_rejects_other_failures_or_changed_original_bounds(fixture, change):
    engine, store, _, _, _, _ = fixture
    code = {"403": "provider_http_403", "timeout": "provider_read_timeout"}.get(change, "provider_http_429")
    plan, failed = critic_rate_failure(engine, store, code=code)
    stored = store.get_run(failed["id"])
    if change == "other_reservation":
        stored["usage"]["model_reservations"]["another-ambiguous-call"] = 100
    elif change == "draft":
        snapshot = engine.graph.get_state({"configurable": {"thread_id": failed["id"]}})
        stored["draft"] = {**snapshot.values["draft"], "body": "Unreviewed changed body"}
    elif change == "plan":
        stored["plan"]["outline"].append("Unapproved scope")
    elif change == "accounting":
        stored["usage"]["gateway_budget"]["uncertain_calls"] = 0
    elif change == "exhausted":
        stored["usage"]["model_calls"] = stored["request"]["max_model_calls"]
    store.save_run(stored)
    before = deepcopy(stored)
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)
    assert store.get_run(failed["id"]) == before and len(engine.model_client.calls) == 7


def test_frozen_critic_checkpoint_rechecked_before_explicit_retry(fixture):
    engine, store, _, _, _, _ = fixture
    plan, failed = critic_rate_failure(engine, store)
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)
    stored = store.get_run(failed["id"])
    stored["draft"]["body"] += "Unreviewed change"
    store.save_run(stored)
    stopped = engine.execute(failed["id"])
    assert stopped["status"] == "error" and len(engine.model_client.calls) == 7
    assert stopped["usage"]["held_usd"] == .035768 and store.notes() == []


def test_second_rate_limit_cannot_get_another_explicit_retry(fixture):
    engine, store, _, _, _, _ = fixture
    plan, failed = critic_rate_failure(engine, store, repeat_failure=True)
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)
    stopped = engine.execute(failed["id"])
    assert stopped["status"] == "error" and len(engine.model_client.calls) == 8
    assert stopped["continuation"] == {"available": False}
    assert len(stopped["usage"]["model_reservations"]) == 2
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)


def test_retry_success_with_unavailable_accounting_never_refunds_old_hold(fixture):
    engine, store, _, _, _, _ = fixture
    plan, failed = critic_rate_failure(engine, store, fail_accounting_after_retry=True)
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)
    note = engine.execute(failed["id"])
    assert note["status"] == "awaiting_note"
    assert note["usage"]["model_calls"] == 8 and note["usage"]["tokens"] == 140
    assert note["usage"]["held_usd"] == .035768
    assert note["usage"]["cost_usd"] is None and note["usage"]["accounting_status"] == "unknown_after_retry"


def test_failed_retry_critic_does_not_buy_unreviewable_repair_with_one_slot(fixture):
    engine, store, _, _, _, _ = fixture
    plan, failed = critic_rate_failure(engine, store, max_model_calls=9, reject=True)
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], retry_transient=True)
    note = engine.execute(failed["id"])
    assert note["status"] == "awaiting_note" and note["critic"]["passed"] is False
    assert note["usage"]["model_calls"] == 8 and len(engine.model_client.calls) == 8
    assert sum(request["role"] == "writer" for request in engine.model_client.calls) == 1
    with pytest.raises(ReviewError):
        engine.claim(note["id"], {"kind": "note", "action": "approve", "payload_hash": note["pending"]["payload_hash"]})
    assert store.notes() == []


class ReplacementCriticClient(RateLimitedCritic):
    def __init__(self):
        super().__init__(repeat_failure=True)
        self.replacement_enabled = False
        self.policy_hash = "f" * 64
        self.budget_changes = {}

    def complete(self, **request):
        if self.replacement_enabled:
            self.repeat_failure = False
        return super().complete(**request)

    def budget(self, run_id):
        failures = len(self.calls) - len(self.cache)
        cost = Decimal(len(self.cache)) * Decimal("0.001")
        held = Decimal(failures) * Decimal("0.035768")
        value = {"run_id": run_id, "enabled": True, "blocked": False,
                 "authorization_id": "new-policy" if self.replacement_enabled else "old-policy",
                 "uncertain_calls": failures, "model_calls": len(self.calls),
                 "reported_spend_usd": str(cost), "held_usd": str(held), "committed_usd": str(cost + held),
                 "tokens": 195257 if failures == 2 else len(self.cache) * 20 + 67536 * failures,
                 "models": {"producer": "mistralai/mistral-medium-3.1", "critic": "mistralai/mistral-large-2407" if self.replacement_enabled else "mistralai/mistral-large-2512"},
                 "model_profile": "live-step10-mistral-large2407-v1" if self.replacement_enabled else "live-step10-mistral-v1",
                 "provider": "mistral/zdr", "cap_usd": "1.00", "per_run_usd": "0.50",
                 "remaining_authorization_usd": str(Decimal(1) - cost - held),
                 "policy_hash": self.policy_hash if self.replacement_enabled else "e" * 64,
                 "prompt_token_ceiling": 49152 if self.replacement_enabled else 65536,
                 "max_message_bytes": 45056 if self.replacement_enabled else 60000,
                 "max_output_tokens": 4096, "max_calls_per_run": 12, "max_tokens_per_run": 250000}
        if self.replacement_enabled:
            value.update(self.budget_changes)
        return value


def two_rate_limits(engine, store):
    client = engine.model_client = ReplacementCriticClient()
    plan = begin_live(engine, store)
    first = decide(engine, plan)
    engine.claim_continuation(first["id"], plan["pending"]["payload_hash"], retry_transient=True)
    second = engine.execute(first["id"])
    assert second["status"] == "error" and len(second["usage"]["model_reservations"]) == 2
    client.replacement_enabled = True
    return plan, second, client


def test_final_replacement_policy_retains_both_holds_and_exact_approved_draft(fixture):
    engine, store, source, _, _, _ = fixture
    plan, stopped, client = two_rate_limits(engine, store)
    original = deepcopy(store.get_run(stopped["id"]))
    view = engine.view(stopped["id"])
    assert view["continuation"] == {"available": False, "replace_critic_policy_available": True,
                                    "plan_hash": plan["pending"]["payload_hash"], "policy_hash": client.policy_hash,
                                    "failure_kind": "critic_policy_replacement"}
    engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], replace_critic_policy=client.policy_hash)
    with pytest.raises(ReviewError):
        engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], replace_critic_policy=client.policy_hash)
    claimed = store.get_run(stopped["id"])
    assert claimed["critic_policy_replacement"]["draft_hash"] == canonical_hash(claimed["draft"])
    note = engine.execute(stopped["id"])
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["request"] == original["request"] and note["plan"] == plan["plan"]
    assert note["usage"]["model_reservations"] == original["usage"]["model_reservations"]
    assert note["usage"]["model_calls"] == len(client.calls) == 9
    assert len(note["usage"]["calls"]) == 7 and note["usage"]["tokens"] == 140
    assert note["usage"]["held_usd"] == .071536 and note["usage"]["cost_usd"] == .007
    critic_calls = [call for call in client.calls if call["role"] == "critic"]
    assert len({call["call_id"] for call in critic_calls}) == 3
    assert critic_calls[0]["messages"] == critic_calls[-1]["messages"]
    assert verify_draft(note["draft"], source)["passed"] and store.notes() == []
    assert sum(event["stage"] == "plan_approved" for event in note["events"]) == 1


@pytest.mark.parametrize("change", ["wrong_hash", "producer", "critic", "provider", "same_policy", "cap", "run_cap", "call_cap", "token_cap", "message_bound", "tokens_exhausted", "refund", "403", "draft", "other_hold", "mixed_flags"])
def test_final_replacement_rejects_unreviewed_policy_or_mutated_original_limits(fixture, change):
    engine, store, _, _, _, _ = fixture
    plan, stopped, client = two_rate_limits(engine, store)
    expected = client.policy_hash
    if change == "wrong_hash": expected = "a" * 64
    elif change == "producer": client.budget_changes["models"] = {"producer": "other", "critic": "mistralai/mistral-large-2407"}
    elif change == "critic": client.budget_changes["models"] = {"producer": "mistralai/mistral-medium-3.1", "critic": "other"}
    elif change == "provider": client.budget_changes["provider"] = "mistral/eu"
    elif change == "same_policy": client.budget_changes["authorization_id"] = "old-policy"
    elif change == "cap": client.budget_changes["cap_usd"] = "2"
    elif change == "run_cap": client.budget_changes["per_run_usd"] = "1"
    elif change == "call_cap": client.budget_changes["max_calls_per_run"] = 13
    elif change == "token_cap": client.budget_changes["max_tokens_per_run"] = 300000
    elif change == "message_bound": client.budget_changes["max_message_bytes"] = 60000
    elif change == "tokens_exhausted": client.budget_changes["max_tokens_per_run"] = 246408
    elif change == "refund": client.budget_changes["held_usd"] = "0"
    elif change in {"403", "draft", "other_hold"}:
        stored = store.get_run(stopped["id"])
        if change == "403": stored["error"] = "ReviewError: provider_http_403: refused"
        elif change == "draft": stored["draft"]["body"] += "Unreviewed change"
        else: stored["usage"]["model_reservations"]["unrelated-call"] = 100
        store.save_run(stored)
    before = deepcopy(store.get_run(stopped["id"]))
    with pytest.raises(ReviewError):
        engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"],
                                  replace_critic_policy=expected, retry_transient=change == "mixed_flags")
    assert store.get_run(stopped["id"]) == before and len(client.calls) == 8


def test_replacement_rechecks_live_policy_and_cannot_repeat_after_failure(fixture):
    engine, store, _, _, _, _ = fixture
    plan, stopped, client = two_rate_limits(engine, store)
    engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], replace_critic_policy=client.policy_hash)
    client.budget_changes["policy_hash"] = "c" * 64
    failed = engine.execute(stopped["id"])
    assert failed["status"] == "error" and len(client.calls) == 8
    assert failed["usage"]["model_reservations"] == stopped["usage"]["model_reservations"]
    with pytest.raises(ReviewError):
        engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], replace_critic_policy=client.policy_hash)


class ExtensionCriticClient(ReplacementCriticClient):
    def __init__(self):
        super().__init__()
        self.google_enabled = False
        self.grant = None
        self.extension_changes = {}
        self.extension_failure = False

    def complete(self, **request):
        if self.google_enabled:
            assert self.grant["call_id"] == request["call_id"] and request["role"] == "critic"
            assert not self.grant["consumed"]
            self.grant["consumed"] = True
            if self.extension_failure:
                self.calls.append(deepcopy(request))
                raise ProviderError("provider_http_429", "Test-only final rate limit.")
            return FakeModelClient.complete(self, **request)
        if self.replacement_enabled and request["role"] == "critic":
            self.calls.append(deepcopy(request))
            raise ProviderError("provider_http_429", "Test-only replacement rate limit.")
        return super().complete(**request)

    def budget(self, run_id):
        value = super().budget(run_id)
        failures = len(self.calls) - len(self.cache)
        if failures >= 3:
            value["tokens"] = 246409 + (20 if self.grant and self.grant["consumed"] else 0)
        if self.google_enabled:
            value.update(authorization_id="approved-google-policy", config_version="test-google-v1", policy_hash="a" * 64,
                model_profile="live-step10-google-critic-v1", provider="role-specific",
                providers={"producer": "mistral/zdr", "critic": "google-ai-studio"},
                models={"producer": "mistralai/mistral-medium-3.1", "critic": "google/gemini-2.5-flash"},
                original_max_calls_per_run=12, original_max_tokens_per_run=250000,
                ledger_checkpoint_hash="b" * 64, run_budget_grant=deepcopy(self.grant))
            value.update(self.extension_changes)
        return value


def approved_extension_failure(engine, store):
    from desk.workflow import critic_extension_request
    client = engine.model_client = ExtensionCriticClient()
    plan = begin_live(engine, store)
    first = decide(engine, plan)
    engine.claim_continuation(first["id"], plan["pending"]["payload_hash"], retry_transient=True)
    engine.execute(first["id"])
    client.replacement_enabled = True
    engine.claim_continuation(first["id"], plan["pending"]["payload_hash"], replace_critic_policy=client.policy_hash)
    stopped = engine.execute(first["id"])
    assert stopped["status"] == "error" and len(stopped["usage"]["model_reservations"]) == 3
    # Three fictional earlier successful writer repairs reproduce the actual
    # exhausted 12-call ledger without extra graph work or any paid transport.
    stored = store.get_run(first["id"])
    for index in range(3):
        identifier = "prior-fictional-success-" + str(index)
        result = deepcopy(next(iter(client.cache.values())))
        result["usage"]["call_id"] = identifier
        client.cache[identifier] = result
        client.calls.append({"call_id": identifier, "role": "writer"})
        stored["usage"]["calls"].append({**result["usage"], "stage": "writer", "config_version": "test-only-v1"})
    stored["usage"].update(model_calls=12, tokens=180, gateway_budget=client.budget(first["id"]))
    store.save_run(stored)
    client.google_enabled = True
    grant_id = "c" * 32
    budget = client.budget(first["id"])
    draft = stored["draft"]
    request = critic_extension_request(draft, first["id"], grant_id, budget)
    client.grant = {"grant_id": grant_id, "run_id": first["id"], "policy_hash": budget["policy_hash"],
        "plan_hash": plan["pending"]["payload_hash"], "draft_hash": canonical_hash(draft),
        "call_id": request["call_id"], "request_hash": canonical_hash(request), "checkpoint_hash": budget["ledger_checkpoint_hash"],
        "approved": True, "consumed": False, "original_calls": 12, "original_tokens": 250000,
        "max_calls": 13, "max_tokens": 300000, "checkpoint_calls": 12, "checkpoint_tokens": 246409,
        "checkpoint_uncertain": 3, "reserved_tokens": 51152, "reservation_usd": "0.0197456",
        "checkpoint_reported_spend_usd": budget["reported_spend_usd"], "checkpoint_held_usd": budget["held_usd"],
        "cap_usd": "1.00", "per_run_usd": "0.50", "model_profile": budget["model_profile"],
        "critic_model": "google/gemini-2.5-flash", "role": "critic"}
    return plan, store.get_run(first["id"]), client


def test_human_approved_exact_extra_critic_preserves_original_caps_three_holds_and_note_review(fixture):
    engine, store, source, _, _, _ = fixture
    plan, stopped, client = approved_extension_failure(engine, store)
    original = deepcopy(stopped)
    view = engine.view(stopped["id"])
    assert view["continuation"]["critic_extension_available"] is True
    with pytest.raises(ReviewError):
        engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"])
    engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    note = engine.execute(stopped["id"])
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["request"] == original["request"] and note["request"]["max_model_calls"] == 12
    assert note["request"]["max_tokens"] == 250000 and note["usage"]["model_calls"] == 13
    assert note["usage"]["model_reservations"] == original["usage"]["model_reservations"]
    assert note["usage"]["tokens"] == 200 and len(note["usage"]["calls"]) == 10
    assert note["usage"]["held_usd"] == float(client.budget(note["id"])["held_usd"])
    assert client.grant["consumed"] and client.calls[-1]["call_id"] == client.grant["call_id"]
    assert verify_draft(note["draft"], source)["passed"] and store.notes() == []
    assert sum(event["stage"] == "plan_approved" for event in note["events"]) == 1
    assert not any(event["stage"] == "note_approved" for event in note["events"])


@pytest.mark.parametrize("change", ["unapproved", "consumed", "wrong_grant", "policy", "call", "request", "plan", "draft", "checkpoint", "role", "stale", "calls", "tokens", "cap", "original", "403", "missing_hold", "producer", "provider", "mixed"])
def test_critic_extension_rejects_unapproved_mismatched_stale_or_expanded_grant(fixture, change):
    engine, store, _, _, _, _ = fixture
    plan, stopped, client = approved_extension_failure(engine, store)
    grant_id = client.grant["grant_id"]
    if change == "unapproved": client.grant["approved"] = False
    elif change == "consumed": client.grant["consumed"] = True
    elif change == "wrong_grant": grant_id = "d" * 32
    elif change in {"policy", "call", "request", "plan", "draft", "checkpoint"}:
        key = {"policy": "policy_hash", "call": "call_id", "request": "request_hash", "plan": "plan_hash", "draft": "draft_hash", "checkpoint": "checkpoint_hash"}[change]
        client.grant[key] = "d" * 64
    elif change == "role": client.grant["role"] = "writer"
    elif change == "stale": client.extension_changes["ledger_checkpoint_hash"] = "e" * 64
    elif change == "calls": client.grant["max_calls"] = 14
    elif change == "tokens": client.grant["max_tokens"] = 400000
    elif change == "cap": client.extension_changes["per_run_usd"] = "1"
    elif change == "original": client.extension_changes["original_max_calls_per_run"] = 13
    elif change == "producer": client.extension_changes["models"] = {"producer": "other", "critic": "google/gemini-2.5-flash"}
    elif change == "provider": client.extension_changes["providers"] = {"producer": "mistral/zdr", "critic": "other"}
    elif change in {"403", "missing_hold"}:
        stored = store.get_run(stopped["id"])
        if change == "403": stored["error"] = "ReviewError: provider_http_403: refused"
        else: stored["usage"]["model_reservations"].pop(next(iter(stored["usage"]["model_reservations"])))
        store.save_run(stored)
    before = deepcopy(store.get_run(stopped["id"]))
    with pytest.raises(ReviewError):
        engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], critic_extension=grant_id,
                                  retry_transient=change == "mixed")
    assert store.get_run(stopped["id"]) == before and len(client.calls) == 12


@pytest.mark.parametrize("change", ["request_hash", "draft", "policy", "role_request", "second_failure"])
def test_exact_critic_extension_rechecked_and_never_repeated(fixture, change):
    engine, store, _, _, _, _ = fixture
    plan, stopped, client = approved_extension_failure(engine, store)
    engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    with pytest.raises(ReviewError):
        engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    if change == "request_hash": client.grant["request_hash"] = "d" * 64
    elif change == "policy": client.extension_changes["policy_hash"] = "d" * 64
    elif change == "draft":
        stored = store.get_run(stopped["id"])
        stored["draft"]["body"] += "Changed"
        store.save_run(stored)
    elif change == "role_request":
        snapshot = engine.graph.get_state({"configurable": {"thread_id": stopped["id"]}})
        with pytest.raises(ReviewError):
            engine.reasoner(snapshot.values, "unapproved-producer").plan("Unapproved question", ["MSFT", "AAPL"], [2023, 2024, 2025])
        assert len(client.calls) == 12
        return
    else: client.extension_failure = True
    result = engine.execute(stopped["id"])
    assert result["status"] == "error" and len(client.calls) == (13 if change == "second_failure" else 12)
    assert len(result["usage"]["model_reservations"]) == (4 if change == "second_failure" else 3)
    with pytest.raises(ReviewError):
        engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    assert store.notes() == []


def billed_invalid_critic_extension(engine, store):
    """Fictional settled invalid output at call13, retaining three older holds."""
    plan, stopped, client = approved_extension_failure(engine, store)
    stored = store.get_run(stopped["id"])
    extra = 60185 - stored["usage"]["tokens"]
    first = stored["usage"]["calls"][0]
    first["prompt_tokens"] += extra
    first["total_tokens"] += extra
    client.cache[first["call_id"]]["usage"]["prompt_tokens"] += extra
    client.cache[first["call_id"]]["usage"]["total_tokens"] += extra
    stored["usage"]["tokens"] = 60185
    store.save_run(stored)
    original_budget = client.budget
    invalid = None
    parent = None
    held = original_budget(stopped["id"])["held_usd"]
    def complete(**request):
        nonlocal invalid, parent
        if client.grant["max_calls"] == 13:
            assert request["call_id"] == client.grant["call_id"]
            client.calls.append(deepcopy(request))
            client.grant["consumed"] = True
            parent = deepcopy(client.grant)
            invalid = {"call_id": request["call_id"], "status": "invalid_output", "usage": {
                "call_id": request["call_id"], "model_calls": 1, "prompt_tokens": 6934, "completion_tokens": 903,
                "total_tokens": 7837, "cost_usd": "0.0043377", "model": "google/gemini-2.5-flash"}}
            raise ProviderError("model_output_invalid", "Test-only billed invalid schema output.")
        client.grant["consumed"] = True
        return FakeModelClient.complete(client, **request)
    def budget(run_id):
        value = original_budget(run_id)
        if invalid is not None:
            observed = sum(item["usage"]["total_tokens"] for item in client.cache.values()) + 7837
            cost = sum((Decimal(item["usage"]["cost_usd"]) for item in client.cache.values()), Decimal(".0043377"))
            value.update(tokens=254246 + max(0, len(client.cache) - 9) * 20,
                model_calls=len(client.calls), uncertain_calls=3, observed_tokens=observed,
                reported_spend_usd=str(cost), held_usd=held, committed_usd=str(cost + Decimal(held)),
                remaining_authorization_usd=str(Decimal(1) - cost - Decimal(held)),
                settled_calls=[{"call_id": item["usage"]["call_id"], "status": "succeeded", "usage": deepcopy(item["usage"])} for item in client.cache.values()] + [deepcopy(invalid)])
            if client.grant.get("parent_grant_id"):
                value["parent_run_budget_grant"] = deepcopy(parent)
                value["ledger_checkpoint_hash"] = "e" * 64
        return value
    client.complete, client.budget = complete, budget
    engine.claim_continuation(stopped["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    failed = engine.execute(stopped["id"])
    return plan, failed, client


def test_billed_invalid_critic_records_observed_usage_and_releases_only_its_settled_reservation(fixture):
    engine, store, _, _, _, _ = fixture
    _, failed, client = billed_invalid_critic_extension(engine, store)
    assert failed["status"] == "error" and "model_output_invalid" in failed["error"]
    assert failed["usage"]["tokens"] == 68022 and failed["usage"]["model_calls"] == 13
    assert len(failed["usage"]["calls"]) == 10 and len(failed["usage"]["model_reservations"]) == 3
    assert client.grant["call_id"] not in failed["usage"]["model_reservations"]
    recorded = failed["usage"]["calls"][-1]
    assert recorded["call_id"] == client.grant["call_id"] and recorded["accepted_output"] is False
    assert recorded["total_tokens"] == 7837 and recorded["cost_usd"] == "0.0043377"
    assert failed["usage"]["cost_usd"] == .0133377 and failed["usage"]["held_usd"] > 0
    assert failed["usage"]["gateway_budget"]["tokens"] - failed["usage"]["tokens"] == 186224
    assert client.grant["consumed"] is True and store.notes() == []


@pytest.mark.parametrize("change", ["call_id", "status", "negative", "nan", "inconsistent", "observed", "uncertain", "count", "held", "duplicate", "config"])
def test_malformed_settled_accounting_never_releases_current_or_older_reservations(fixture, change):
    from desk.workflow import reconcile_settled_model_call
    engine, store, _, _, _, _ = fixture
    _, failed, client = billed_invalid_critic_extension(engine, store)
    usage = deepcopy(failed["usage"])
    last = usage["calls"].pop()
    usage["tokens"] -= last["total_tokens"]
    usage["model_reservations"][last["call_id"]] = 29447
    budget = client.budget(failed["id"])
    item = budget["settled_calls"][-1]
    if change == "call_id": item["usage"]["call_id"] = "other"
    elif change == "status": item["status"] = "uncertain"
    elif change == "negative": item["usage"]["completion_tokens"] = -1
    elif change == "nan": item["usage"]["cost_usd"] = "NaN"
    elif change == "inconsistent": item["usage"]["total_tokens"] += 1
    elif change == "observed": budget["observed_tokens"] += 1
    elif change == "uncertain": budget["uncertain_calls"] = 0
    elif change == "count": budget["model_calls"] = 12
    elif change == "held": budget["held_usd"] = "0"
    elif change == "duplicate": budget["settled_calls"].append(deepcopy(item))
    elif change == "config": budget.pop("config_version")
    before = deepcopy(usage)
    assert not reconcile_settled_model_call(usage, budget, run_id=failed["id"], call_id=last["call_id"], role="critic")
    assert usage == before


def approved_critic_amendment(engine, store):
    from desk.workflow import critic_extension_request
    plan, failed, client = billed_invalid_critic_extension(engine, store)
    parent = deepcopy(client.grant)
    budget = client.budget(failed["id"])
    grant_id = "d" * 32
    request = critic_extension_request(failed["draft"], failed["id"], grant_id, budget)
    client.grant = {**parent, "grant_id": grant_id, "parent_grant_id": parent["grant_id"], "consumed": False,
        "call_id": request["call_id"], "request_hash": canonical_hash(request), "checkpoint_hash": "e" * 64,
        "max_calls": 14, "max_tokens": 350000, "checkpoint_calls": 13, "checkpoint_tokens": 254246,
        "checkpoint_reported_spend_usd": budget["reported_spend_usd"], "checkpoint_held_usd": budget["held_usd"]}
    return plan, failed, client


def test_second_human_approved_critic_amendment_retains_first_grant_and_every_old_hold(fixture):
    engine, store, source, _, _, _ = fixture
    plan, failed, client = approved_critic_amendment(engine, store)
    first = deepcopy(failed["approved_critic_extension"])
    view = engine.view(failed["id"])
    assert view["continuation"]["grant_id"] == client.grant["grant_id"]
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    claimed = store.get_run(failed["id"])
    assert claimed["critic_extension_history"] == [first]
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    note = engine.execute(failed["id"])
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["usage"]["model_calls"] == 14 and note["usage"]["tokens"] == 68042
    assert note["usage"]["model_reservations"] == failed["usage"]["model_reservations"]
    assert note["request"] == failed["request"] and note["request"]["max_model_calls"] == 12
    assert note["critic_extension_history"] == [first] and note["approved_critic_extension"]["max_calls"] == 14
    assert note["usage"]["calls"][-2]["accepted_output"] is False
    assert note["usage"]["calls"][-1]["call_id"] != first["call_id"]
    assert verify_draft(note["draft"], source)["passed"] and store.notes() == []


@pytest.mark.parametrize("change", ["parent", "parent_consumed", "parent_draft", "fifteenth", "tokens", "stale", "unknown_output", "403", "same_id"])
def test_critic_amendment_rejects_wrong_parent_stale_or_unbounded_retry(fixture, change):
    engine, store, _, _, _, _ = fixture
    plan, failed, client = approved_critic_amendment(engine, store)
    if change == "parent": client.grant["parent_grant_id"] = "e" * 32
    elif change == "parent_consumed":
        original = client.budget
        def budget(run_id):
            value = original(run_id)
            value["parent_run_budget_grant"]["consumed"] = False
            return value
        client.budget = budget
    elif change == "parent_draft":
        stored = store.get_run(failed["id"])
        stored["approved_critic_extension"]["draft_hash"] = "f" * 64
        store.save_run(stored)
    elif change == "fifteenth": client.grant["max_calls"] = 15
    elif change == "tokens": client.grant["max_tokens"] = 400000
    elif change == "stale": client.grant["checkpoint_hash"] = "f" * 64
    elif change in {"unknown_output", "403"}:
        stored = store.get_run(failed["id"])
        if change == "unknown_output": stored["usage"]["calls"][-1].pop("accepted_output")
        else: stored["error"] = "ReviewError: provider_http_403: refused"
        store.save_run(stored)
    else: client.grant["call_id"] = failed["approved_critic_extension"]["call_id"]
    before = deepcopy(store.get_run(failed["id"]))
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    assert store.get_run(failed["id"]) == before and len(client.calls) == 13


def test_settled_invalid_accounting_reconciliation_is_read_only_and_idempotent(fixture):
    from desk.workflow import reconcile_settled_model_call
    engine, store, _, _, _, _ = fixture
    _, failed, client = billed_invalid_critic_extension(engine, store)
    usage = deepcopy(failed["usage"])
    before_calls = len(client.calls)
    assert reconcile_settled_model_call(usage, client.budget(failed["id"]),
        run_id=failed["id"], call_id=client.grant["call_id"], role="critic")
    assert usage["calls"] == failed["usage"]["calls"] and usage["tokens"] == 68022
    assert len(client.calls) == before_calls and len(usage["model_reservations"]) == 3


def test_amendment_cannot_resume_after_failed_final_call(fixture):
    engine, store, _, _, _, _ = fixture
    plan, failed, client = approved_critic_amendment(engine, store)
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    def final_failure(**request):
        client.calls.append(deepcopy(request))
        client.grant["consumed"] = True
        raise ProviderError("model_output_invalid", "Test-only terminal final invalid output.")
    client.complete = final_failure
    stopped = engine.execute(failed["id"])
    assert stopped["status"] == "error" and len(client.calls) == 14
    assert len(stopped["critic_extension_history"]) == 1
    with pytest.raises(ReviewError):
        engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"], critic_extension=client.grant["grant_id"])
    assert len(client.calls) == 14 and store.notes() == []
