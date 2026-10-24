"""Live graph integration with real schemas/ledger boundaries and fake paid transport."""
from copy import deepcopy
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
            content = {"comparisons": [{"before_year": before, "after_year": after, "status": "evidence_available",
                "findings": [{"text": "Selected disclosures discuss operational uncertainty.", "confidence": "low", "quote_ids": [quote_id(before), quote_id(after)]}]} for before, after in context["comparison_pairs"]]}
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
            result["content"]["comparisons"][0]["findings"][0]["quote_ids"] = ["quote-not-in-supplied-menu"]
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
                result["content"]["comparisons"][0]["findings"][0]["text"] = provisional
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
    assert published["usage"]["tool_calls"] == 18


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
