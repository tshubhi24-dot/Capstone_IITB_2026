"""Synthetic risk-stage corrections with fake models; no live case quality claim."""
from copy import deepcopy
from decimal import Decimal
import json

import pytest

from desk.provider import ProviderError
from desk.workflow import verify_draft
from test_live_workflow import FakeModelClient
from test_workflow import fixture, decide


INVALID_QUANTITY = "The issuer incurred one billion dollars in operational losses."
INVALID_DIGIT = "Selected disclosures identify 12 operational incidents."


def start(engine, store, *, max_model_calls=12):
    request = {"question": "Compare selected annual margins and disclosed risks.",
        "tickers": ["MSFT", "AAPL"], "years": [2024, 2025], "mode": "live",
        "max_tool_calls": 60, "max_model_calls": max_model_calls, "max_tokens": 250000,
        "memory_enabled": False, "lessons_enabled": False}
    return engine.execute(store.create_run(request)["id"])


def contexts(client, role):
    return [json.loads(call["messages"][-1]["content"]) for call in client.calls if call["role"] == role]


class InvalidRiskClient(FakeModelClient):
    def __init__(self, *, ticker="MSFT", text=INVALID_QUANTITY, repeat=False, mutation=None):
        super().__init__()
        self.ticker, self.text, self.repeat, self.mutation = ticker, text, repeat, mutation
        self.risk_requests = []
        self.invalid_outputs = []

    def complete(self, **request):
        cached = request["call_id"] in self.cache
        if request["role"] == "risk":
            self.risk_requests.append(deepcopy(request))
        result = super().complete(**request)
        if request["role"] != "risk" or cached:
            return result
        context = json.loads(request["messages"][-1]["content"])
        if context["ticker"] == self.ticker and (self.repeat or not context.get("validation_feedback")):
            comparisons = result["content"]["comparisons"]
            finding = next(iter(comparisons.values()))["findings"][0]
            if self.mutation == "unknown_quote":
                finding["before_quote_id"] = "quote-not-in-canonical-menu"
            elif self.mutation == "same_period":
                finding["after_quote_id"] = finding["before_quote_id"]
            elif self.mutation == "wrong_comparison":
                comparisons["comparison-2023-2025"] = comparisons.pop(next(iter(comparisons)))
            else:
                finding["text"] = self.text
            self.invalid_outputs.append(deepcopy(result["content"]))
            self.cache[request["call_id"]] = deepcopy(result)
        return result


@pytest.mark.parametrize("text,code", [(INVALID_QUANTITY, "narrative_quantity"), (INVALID_DIGIT, "output_schema")])
@pytest.mark.parametrize("ticker", ["MSFT", "AAPL"])
def test_newly_settled_risk_format_failure_gets_one_bounded_correction_and_full_checks(fixture, text, code, ticker):
    engine, store, source, _, _, _ = fixture
    client = engine.model_client = InvalidRiskClient(ticker=ticker, text=text)
    plan = start(engine, store)
    original_request = deepcopy(store.get_run(plan["id"])["request"])
    note = decide(engine, plan)

    assert note["status"] == "awaiting_note", note.get("error")
    risk_contexts = contexts(client, "risk")
    repaired = [context for context in risk_contexts if context["ticker"] == ticker]
    assert len(repaired) == 2 and not repaired[0].get("validation_feedback")
    assert repaired[1]["validation_feedback"] == [code]
    assert text not in json.dumps(repaired[1])  # Only fixed codes, not raw rejected prose.
    assert repaired[0]["quote_menu"] == repaired[1]["quote_menu"]
    assert repaired[0]["years"] == repaired[1]["years"] == [2024, 2025]
    assert len([context for context in risk_contexts if context["ticker"] != ticker]) == 1
    assert len(client.invalid_outputs) == 1 and text in json.dumps(client.invalid_outputs[0])
    assert len(contexts(client, "planner")) == 1 and len(contexts(client, "researcher")) == 2
    assert len(contexts(client, "writer")) == len(contexts(client, "critic")) == 1
    assert len(client.calls) == note["usage"]["model_calls"] == 8
    assert note["usage"]["cost_usd"] == .008 and note["usage"]["model_reservations"] == {}
    assert note["request"] == original_request and note["plan"] == plan["plan"]
    assert note["request"]["max_tokens"] == 250000 and note["request"]["max_model_calls"] == 12
    assert store.get_run(note["id"])["plan_approval"]["payload_hash"] == plan["pending"]["payload_hash"]
    assert verify_draft(note["draft"], source)["passed"]
    assert note["critic"]["verified_numbers"] == 12 and len(note["metrics"]) == 4
    assert text not in note["draft"]["body"]
    assert store.notes() == [] and note["pending"]["kind"] == "note"


def test_second_invalid_risk_output_stops_without_writer_or_critic_and_keeps_both_charges(fixture):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = InvalidRiskClient(repeat=True)
    plan = start(engine, store)
    failed = decide(engine, plan)
    assert failed["status"] == "error" and failed["failure_kind"] == "content_validation"
    assert len(contexts(client, "risk")) == 2 and len(client.invalid_outputs) == 2
    assert contexts(client, "writer") == contexts(client, "critic") == []
    assert len(client.calls) == failed["usage"]["model_calls"] == 5
    assert failed["usage"]["cost_usd"] == .005
    assert len([call for call in failed["usage"]["calls"] if call["stage"] == "risk"]) == 2
    engine.execute(failed["id"])
    assert len(client.calls) == 5 and store.notes() == []


@pytest.mark.parametrize("code", ["provider_http_429", "provider_http_403", "model_output_invalid"])
def test_provider_errors_are_not_risk_content_corrections(fixture, code):
    engine, store, _, _, _, _ = fixture

    class UnavailableRisk(FakeModelClient):
        def complete(self, **request):
            if request["role"] == "risk":
                self.calls.append(deepcopy(request))
                raise ProviderError(code, "Synthetic unavailable provider.")
            return super().complete(**request)

    client = engine.model_client = UnavailableRisk()
    failed = decide(engine, start(engine, store))
    assert failed["status"] == "error" and failed["failure_kind"] == "not_continuable"
    assert len(contexts(client, "risk")) == 1
    assert contexts(client, "writer") == contexts(client, "critic") == []
    assert failed["usage"]["model_reservations"] and store.notes() == []


@pytest.mark.parametrize("mutation", ["unknown_quote", "same_period", "wrong_comparison"])
def test_provenance_or_period_failure_is_not_silently_repaired_as_formatting(fixture, mutation):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = InvalidRiskClient(mutation=mutation)
    failed = decide(engine, start(engine, store))
    assert failed["status"] == "error" and failed["failure_kind"] == "content_validation"
    assert len(contexts(client, "risk")) == 1
    assert contexts(client, "writer") == contexts(client, "critic") == []
    assert failed["usage"]["model_calls"] == 4 and failed["usage"]["cost_usd"] == .004
    assert store.notes() == []


def test_cached_invalid_risk_response_cannot_trigger_another_paid_correction_on_resume(fixture):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = InvalidRiskClient()
    plan = start(engine, store, max_model_calls=7)
    failed = decide(engine, plan)
    assert failed["status"] == "error" and failed["usage"]["model_calls"] == 4
    original_calls = deepcopy(failed["usage"]["calls"])
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"])
    stopped = engine.execute(failed["id"])
    assert stopped["status"] == "error" and stopped["failure_kind"] == "content_validation"
    assert len(contexts(client, "risk")) == 1 and len(client.risk_requests) == 2
    assert client.risk_requests[0] == client.risk_requests[1]
    assert stopped["usage"]["calls"] == original_calls and stopped["usage"]["model_calls"] == 4
    assert stopped["request"] == failed["request"] and stopped["plan"] == plan["plan"]
    assert store.notes() == []


@pytest.mark.parametrize("ticker", ["MSFT", "AAPL"])
@pytest.mark.parametrize("limit,expected_status,expected_risk_calls", [(7, "error", None), (8, "awaiting_note", 3)])
def test_finite_limit_leaves_capacity_for_correction_remaining_risk_writer_and_critic(
        fixture, ticker, limit, expected_status, expected_risk_calls):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = InvalidRiskClient(ticker=ticker)
    plan = start(engine, store, max_model_calls=limit)
    result = decide(engine, plan)
    assert result["status"] == expected_status, result.get("error")
    if expected_risk_calls is None:
        expected_risk_calls = 1 if ticker == "MSFT" else 2
    assert len(contexts(client, "risk")) == expected_risk_calls
    assert result["request"]["max_model_calls"] == limit
    assert result["usage"]["model_calls"] <= limit
    assert len(contexts(client, "critic")) == (1 if expected_status == "awaiting_note" else 0)
    assert store.notes() == []


@pytest.mark.parametrize("original_call_limit", [None, 7])
def test_program_no_count_ceiling_allows_bounded_risk_correction_and_retains_token_scope(fixture, original_call_limit):
    engine, store, source, _, _, _ = fixture

    class ProgramRiskClient(InvalidRiskClient):
        def budget(self, run_id=None):
            return {"model_profile": "live-program-models-v1", "enabled": True,
                    "blocked": False, "max_calls_per_run": None}

    client = engine.model_client = ProgramRiskClient()
    plan = start(engine, store, max_model_calls=original_call_limit)
    original_request = deepcopy(store.get_run(plan["id"])["request"])
    note = decide(engine, plan)
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["request"] == original_request and note["request"]["max_model_calls"] == original_call_limit
    assert note["request"]["max_tokens"] == 250000
    assert len(client.calls) == note["usage"]["model_calls"] == 8
    assert note["usage"]["cost_usd"] == .008 and note["usage"]["model_reservations"] == {}
    assert verify_draft(note["draft"], source)["passed"] and store.notes() == []


class SettledGatewayFormatClient(FakeModelClient):
    """Model the gateway's fixed format error and separate billing metadata."""
    def __init__(self, *, accounting="settled"):
        super().__init__()
        self.failed_id = None
        self.accounting = accounting

    def complete(self, **request):
        result = super().complete(**request)
        if request["role"] == "risk" and self.failed_id is None:
            self.failed_id = request["call_id"]
            raise ProviderError("risk_narrative_format", "Synthetic audited risk prose pattern failure.")
        return result

    def budget(self, run_id=None):
        if self.failed_id and self.accounting == "missing":
            raise RuntimeError("Synthetic unavailable accounting")
        uncertain = self.failed_id is not None and self.accounting == "uncertain"
        settled = [{"call_id": identifier,
                    "status": "invalid_output" if identifier == self.failed_id else "succeeded",
                    "usage": deepcopy(result["usage"])}
                   for identifier, result in self.cache.items()
                   if not (uncertain and identifier == self.failed_id)]
        spend = Decimal(len(settled)) * Decimal(".001")
        held = Decimal(".01") if uncertain else Decimal(0)
        observed = len(settled) * 20
        return {"run_id": run_id, "config_version": "test-only-v1",
                "model_calls": len(self.calls), "reported_spend_usd": str(spend),
                "held_usd": str(held), "committed_usd": str(spend + held),
                "observed_tokens": observed, "tokens": observed + (100000 if uncertain else 0),
                "uncertain_calls": int(uncertain), "settled_calls": settled}


def test_gateway_audited_risk_format_failure_reconciles_charge_before_bounded_correction(fixture):
    engine, store, source, _, _, _ = fixture
    client = engine.model_client = SettledGatewayFormatClient()
    plan = start(engine, store)
    request = deepcopy(store.get_run(plan["id"])["request"])
    note = decide(engine, plan)
    assert note["status"] == "awaiting_note", note.get("error")
    risk = contexts(client, "risk")
    assert len(risk) == 3 and risk[1]["validation_feedback"] == ["output_schema"]
    assert risk[0]["quote_menu"] == risk[1]["quote_menu"]
    rejected = [call for call in note["usage"]["calls"] if call["call_id"] == client.failed_id]
    assert len(rejected) == 1 and rejected[0]["accepted_output"] is False
    assert rejected[0]["stage"] == "risk" and rejected[0]["cost_usd"] == "0.001"
    assert note["usage"]["model_calls"] == len(client.calls) == 8
    assert note["usage"]["cost_usd"] == .008 and note["usage"]["tokens"] == 160
    assert note["usage"]["model_reservations"] == {}
    assert note["request"] == request and note["plan"] == plan["plan"]
    assert verify_draft(note["draft"], source)["passed"] and store.notes() == []


@pytest.mark.parametrize("accounting", ["missing", "uncertain"])
def test_risk_format_error_without_authoritative_settlement_cannot_trigger_correction(fixture, accounting):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = SettledGatewayFormatClient(accounting=accounting)
    failed = decide(engine, start(engine, store))
    assert failed["status"] == "error" and failed["failure_kind"] == "not_continuable"
    assert len(contexts(client, "risk")) == 1
    assert contexts(client, "writer") == contexts(client, "critic") == []
    assert client.failed_id in failed["usage"]["model_reservations"]
    assert not any(call.get("accepted_output") is False for call in failed["usage"]["calls"])
    assert store.notes() == []
