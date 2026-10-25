"""Synthetic full-graph writer contract checks; no live research evidence.

The fixture uses deliberately fictional MSFT/AAPL facts and the fake transport
from test_live_workflow. These tests exercise orchestration, provenance and
accounting, not actual model quality or ABT/AMGN source interpretation.
"""
from copy import deepcopy
import json

import pytest

from desk.provider import ProviderError
from desk.workflow import ReviewError, verify_draft
from test_live_workflow import FakeModelClient
from test_workflow import fixture, decide


QUESTION = (
    "Compare the selected annual sources and verified operating margins. "
    "Raw-question sentinel: explain whether revenue grew by ninety percent."
)
INVALID_QUANTITY = "The issuer incurred one billion dollars in operational losses."


def begin_scoped(engine, store, *, max_model_calls=12):
    request = {
        "question": QUESTION,
        "tickers": ["MSFT", "AAPL"],
        "years": [2024, 2025],
        "mode": "live",
        "max_tool_calls": 60,
        "max_tokens": 250000,
        "max_model_calls": max_model_calls,
        "memory_enabled": False,
        "lessons_enabled": False,
    }
    return engine.execute(store.create_run(request)["id"])


def contexts(client, role):
    return [json.loads(call["messages"][-1]["content"])
            for call in client.calls if call["role"] == role]


class QuantityFailureClient(FakeModelClient):
    """Return an unchanged invalid fixture, then optionally a valid response."""

    def __init__(self, *, repeat=False, invalid_revision=False):
        super().__init__()
        self.repeat = repeat
        self.invalid_revision = invalid_revision
        self.invalid_outputs = []

    def complete(self, **request):
        already_cached = request["call_id"] in self.cache
        result = super().complete(**request)
        if request["role"] != "writer" or already_cached:
            return result
        context = json.loads(request["messages"][-1]["content"])
        if self.repeat or not context.get("validation_feedback"):
            if self.invalid_revision:
                next(iter(result["content"]["risk_revisions"].values()))["text"] = INVALID_QUANTITY
            else:
                result["content"]["claims"][0]["text"] = INVALID_QUANTITY
            self.invalid_outputs.append(deepcopy(result["content"]))
            self.cache[request["call_id"]] = deepcopy(result)
        return result


def assert_writer_contract(client, source):
    for context in contexts(client, "writer"):
        assert not {"question", "plan", "metrics", "verified_metrics"} & context.keys()
        assert QUESTION not in json.dumps(context)
        assert "ninety percent" not in json.dumps(context)
        menu = context["quote_menu"]
        assert menu
        assert not {row["source_id"] for row in menu} & source._facts.keys()
        assert all("item1A" in row["source_id"] for row in menu)
        assert context["risk_observations"]


def test_full_synthetic_graph_keeps_financial_data_out_of_writer_but_in_critic(fixture):
    engine, store, source, _, _, _ = fixture
    client = engine.model_client = FakeModelClient()
    plan = begin_scoped(engine, store)
    original_request = deepcopy(store.get_run(plan["id"])["request"])
    note = decide(engine, plan)

    assert note["status"] == "awaiting_note", note.get("error")
    assert_writer_contract(client, source)
    assert len(note["metrics"]) == 4 and note["critic"]["verified_numbers"] == 12
    assert verify_draft(note["draft"], source)["passed"]
    critic = contexts(client, "critic")
    assert len(critic) == 1 and critic[0]["body"] == note["draft"]["body"]
    financial_ids = {identifier for row in note["metrics"] for identifier in row["fact_ids"]}
    assert financial_ids <= {row["id"] for row in critic[0]["evidence"]}
    assert note["request"] == original_request
    assert note["plan"] == plan["plan"]
    assert len(client.calls) == note["usage"]["model_calls"] == 7
    assert store.notes() == []
    assert note["pending"]["kind"] == "note"


@pytest.mark.parametrize("invalid_revision", [False, True])
def test_one_content_correction_retains_first_charge_and_gets_fresh_exact_critic(fixture, invalid_revision):
    engine, store, source, tool_calls, _, _ = fixture
    client = engine.model_client = QuantityFailureClient(invalid_revision=invalid_revision)
    plan = begin_scoped(engine, store)
    original_request = deepcopy(store.get_run(plan["id"])["request"])
    plan_hash = plan["pending"]["payload_hash"]
    note = decide(engine, plan)

    assert note["status"] == "awaiting_note", note.get("error")
    assert_writer_contract(client, source)
    writer_contexts = contexts(client, "writer")
    assert len(writer_contexts) == 2
    assert not writer_contexts[0].get("validation_feedback")
    assert writer_contexts[1]["validation_feedback"] == ["narrative_quantity"]
    # Failed model prose is not pasted into the next prompt or silently edited.
    assert INVALID_QUANTITY not in json.dumps(writer_contexts[1])
    assert len(client.invalid_outputs) == 1
    assert INVALID_QUANTITY in json.dumps(client.invalid_outputs[0])
    assert INVALID_QUANTITY not in note["draft"]["body"]
    assert contexts(client, "critic")[0]["body"] == note["draft"]["body"]
    assert len(contexts(client, "critic")) == 1
    assert len(client.calls) == note["usage"]["model_calls"] == 8
    assert len(note["usage"]["calls"]) == 8 and note["usage"]["cost_usd"] == .008
    assert note["request"] == original_request and note["plan"] == plan["plan"]
    assert store.get_run(note["id"])["plan_approval"]["payload_hash"] == plan_hash
    assert sum(event["stage"] == "plan_approved" for event in note["events"]) == 1
    assert len(contexts(client, "planner")) == 1 and len(contexts(client, "researcher")) == 2
    assert len(contexts(client, "risk")) == 2
    assert len([call for call in tool_calls if call[1] == "get_facts"]) == 2
    assert verify_draft(note["draft"], source)["passed"]
    assert note["pending"]["kind"] == "note" and store.notes() == []


def test_repeated_writer_content_failure_stops_after_one_correction(fixture):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = QuantityFailureClient(repeat=True)
    plan = begin_scoped(engine, store)
    failed = decide(engine, plan)

    assert failed["status"] == "error" and failed["failure_kind"] == "content_validation"
    assert len(contexts(client, "writer")) == 2
    assert contexts(client, "critic") == []
    assert len(client.calls) == failed["usage"]["model_calls"] == 7
    assert failed["usage"]["cost_usd"] == .007 and len(client.invalid_outputs) == 2
    assert store.notes() == []
    engine.execute(failed["id"])
    assert len(client.calls) == 7  # A page refresh does not start another repair.


def test_corrected_writer_output_does_not_bypass_an_independent_critic_rejection(fixture):
    engine, store, _, _, _, _ = fixture

    class RejectingCriticClient(QuantityFailureClient):
        def complete(self, **request):
            # Inject the quantity failure only into the first writer request;
            # later ordinary critic-driven repair drafts use valid fixtures.
            if request["role"] == "writer" and self.invalid_outputs:
                result = FakeModelClient.complete(self, **request)
            else:
                result = super().complete(**request)
            if request["role"] == "critic":
                result["content"]["verdicts"][0]["supported"] = False
                result["content"]["verdicts"][0]["reason"] = "Fictional reviewer rejects unsupported source interpretation."
                self.cache[request["call_id"]] = deepcopy(result)
            return result

    client = engine.model_client = RejectingCriticClient()
    note = decide(engine, begin_scoped(engine, store))
    assert note["status"] == "awaiting_note", note.get("error")
    assert not note["critic"]["passed"]
    # Identical repaired bodies may legitimately reuse the exact cached critic
    # verdict. Reuse must retain the rejection rather than imply new approval.
    assert 1 <= len(contexts(client, "critic")) <= 3
    assert sum(event["stage"] == "critic_reject" for event in note["events"]) == 3
    assert contexts(client, "critic")[-1]["body"] == note["draft"]["body"]
    assert len(client.calls) == note["usage"]["model_calls"] <= 12
    assert len(client.invalid_outputs) == 1
    with pytest.raises(ReviewError, match="Unresolved"):
        engine.claim(note["id"], {"kind": "note", "action": "approve",
                                "payload_hash": note["pending"]["payload_hash"]})
    assert store.notes() == []


def test_critic_rejection_reaches_repair_as_exact_failed_claim_without_raw_reason(fixture):
    engine, store, source, _, _, _ = fixture
    original_text = "Selected source excerpts provide limited disclosure context."
    narrowed_text = "Selected excerpts supply only limited context for the cited disclosure wording."
    private_reason = "Fictional critic reason sentinel: revenue rose by ninety percent."

    class FeedbackAwareClient(FakeModelClient):
        def complete(self, **request):
            result = super().complete(**request)
            context = json.loads(request["messages"][-1]["content"])
            if request["role"] == "writer" and context.get("critic_feedback"):
                feedback = context["critic_feedback"]
                assert len(feedback) == 1
                assert feedback[0]["claim_id"] == "writer-1" and feedback[0]["text"] == original_text
                result["content"]["claims"][0]["text"] = narrowed_text
            if request["role"] == "critic":
                target = next(claim for claim in context["claims"] if claim["claim_id"] == "writer-1")
                verdict = next(value for value in result["content"]["verdicts"] if value["claim_id"] == "writer-1")
                verdict["supported"] = target["text"] == narrowed_text
                verdict["reason"] = "Fictional support check of the narrower wording." if verdict["supported"] else private_reason
            self.cache[request["call_id"]] = deepcopy(result)
            return result

    client = engine.model_client = FeedbackAwareClient()
    plan = begin_scoped(engine, store)
    original_request = deepcopy(store.get_run(plan["id"])["request"])
    note = decide(engine, plan)
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["critic"]["passed"] and note["repairs"] == 1
    writer_contexts = contexts(client, "writer")
    assert len(writer_contexts) == 2
    assert writer_contexts[0].get("critic_feedback") == []
    assert writer_contexts[1]["critic_feedback_instruction"]
    feedback = writer_contexts[1]["critic_feedback"]
    first_critic_claim = next(claim for claim in contexts(client, "critic")[0]["claims"] if claim["claim_id"] == "writer-1")
    assert feedback == [first_critic_claim]
    assert "reason" not in feedback[0] and "body" not in feedback[0]
    assert private_reason not in json.dumps(writer_contexts[1])
    assert_writer_contract(client, source)
    assert len(contexts(client, "critic")) == 2
    assert contexts(client, "critic")[0]["body"] != contexts(client, "critic")[1]["body"]
    assert contexts(client, "critic")[1]["body"] == note["draft"]["body"]
    assert narrowed_text in note["draft"]["body"] and original_text not in note["draft"]["body"]
    assert len(client.calls) == note["usage"]["model_calls"] == 9
    assert note["usage"]["cost_usd"] == .009
    assert note["request"] == original_request and note["plan"] == plan["plan"]
    assert verify_draft(note["draft"], source)["passed"]
    assert store.notes() == [] and note["pending"]["kind"] == "note"


@pytest.mark.parametrize("code", ["provider_http_429", "provider_http_403", "model_output_invalid"])
def test_writer_provider_failures_never_trigger_a_content_correction(fixture, code):
    engine, store, _, _, _, _ = fixture

    class ProviderFailureClient(FakeModelClient):
        def complete(self, **request):
            if request["role"] == "writer":
                self.calls.append(deepcopy(request))
                raise ProviderError(code, "Test-only provider failure.")
            return super().complete(**request)

    client = engine.model_client = ProviderFailureClient()
    failed = decide(engine, begin_scoped(engine, store))
    assert failed["status"] == "error"
    assert failed["failure_kind"] == "not_continuable"
    assert len(contexts(client, "writer")) == 1
    assert contexts(client, "critic") == [] and store.notes() == []
    assert failed["usage"]["model_reservations"]  # Uncertain charge is retained.


@pytest.mark.parametrize("call_limit, expected_writers, expected_status", [
    (7, 1, "error"),
    (8, 2, "awaiting_note"),
])
def test_content_correction_reserves_room_for_critic_inside_original_call_limit(
        fixture, call_limit, expected_writers, expected_status):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = QuantityFailureClient()
    plan = begin_scoped(engine, store, max_model_calls=call_limit)
    result = decide(engine, plan)
    assert result["status"] == expected_status, result.get("error")
    assert len(contexts(client, "writer")) == expected_writers
    assert result["request"]["max_model_calls"] == call_limit
    assert result["usage"]["model_calls"] <= call_limit
    assert len(contexts(client, "critic")) == (1 if expected_status == "awaiting_note" else 0)
    assert store.notes() == []
