"""Only a known paired-risk prose format failure gets the fixed diagnosis."""
from copy import deepcopy
import json

from fastapi.testclient import TestClient
import httpx
import pytest

from desk.model_gateway import build_app
from desk.provider import ProviderError, safe_error_code
from desk.reasoning import QUALITATIVE_TEXT_PATTERN, Reasoner
from test_provider import KEY, TOKEN, config, gateway, response


@pytest.fixture
def risk_request():
    captured = {}
    def capture(role, **request):
        captured.update(request)
        menu = request["context"]["quote_menu"]
        result = {"comparisons": {identifier: {"status": "evidence_available", "findings": [{
            "text": "The compared filings describe conditional supplier disruption.", "confidence": "low",
            "before_quote_id": next(row["quote_id"] for row in menu if row["year"] == pair["before_year"]),
            "after_quote_id": next(row["quote_id"] for row in menu if row["year"] == pair["after_year"])}]}
            for identifier, pair in request["context"]["comparison_keys"].items()}}
        captured["candidate"] = deepcopy(result)
        return result
    sections = {year: {"ticker": "AMGN", "year": year, "snapshot_complete": True,
                       "chunks": [{"id": f"risk-AMGN-{year}", "ticker": "AMGN", "year": year,
                                   "text": "Supplier disruption may interrupt product supply and affect business operations."}]}
                for year in (2023, 2024, 2025)}
    Reasoner(capture).compare_risks("AMGN", [2023, 2024, 2025], sections)
    request = {"run_id": "run-risk", "call_id": "run-risk:format-v1", "role": "risk",
               "messages": [{"role": "system", "content": captured["system"]},
                            {"role": "user", "content": json.dumps(captured["context"])}],
               "response_schema": captured["schema"], "max_output_tokens": 256}
    return request, captured["candidate"]


def dated(candidate):
    for comparison in candidate["comparisons"].values():
        comparison["findings"][0]["text"] = "The issuer describes supplier risk in 2023, and in 2024."
    return candidate


def test_known_risk_pattern_failure_is_charged_audited_and_never_retried(tmp_path, config, risk_request):
    request, candidate = risk_request
    dated(candidate)
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=response(content=candidate)))
    with pytest.raises(ProviderError) as error:
        engine.complete(**request)
    assert error.value.code == safe_error_code("risk_narrative_format") == "risk_narrative_format"
    assert len(calls) == 1 and candidate["comparisons"]["comparison-2023-2024"]["findings"][0]["text"] not in str(error.value)
    budget = engine.budget("run-risk")
    assert budget["reported_spend_usd"] == "0.0001" and budget["held_usd"] == "0"
    assert budget["model_calls"] == 1 and budget["settled_calls"][0]["status"] == "invalid_output"
    with engine.ledger.connection() as db:
        call = dict(db.execute("SELECT * FROM model_calls").fetchone())
        audit = dict(db.execute("SELECT * FROM model_output_audit").fetchone())
    assert call["error_code"] == "risk_narrative_format" and call["result"] is None
    assert audit["validation_stage"] == "schema_validation" and audit["schema_keyword"] == "pattern"
    assert json.loads(audit["schema_path"]) == ["properties", "comparisons", "properties", "comparison-2023-2024",
                                               "properties", "findings", "items", "properties", "text", "pattern"]
    assert "candidate" not in json.dumps(budget)
    with pytest.raises(ProviderError) as repeated:
        engine.complete(**request)
    assert repeated.value.code == "call_not_retriable" and len(calls) == 1
    assert engine.budget("run-risk")["reported_spend_usd"] == "0.0001"


@pytest.mark.parametrize("case", ["wrong_role", "wrong_path", "unrelated_schema", "different_pattern", "unknown_quote",
                                  "date_and_unknown_quote", "credential_echo", "other_credential", "unknown_model", "json_parse", "truncated"])
def test_other_paid_output_failures_never_receive_risk_format_diagnosis(tmp_path, config, risk_request, case):
    request, candidate = risk_request
    finding = candidate["comparisons"]["comparison-2023-2024"]["findings"][0]
    schema = request["response_schema"]["properties"]["comparisons"]["properties"]["comparison-2023-2024"]
    if case == "wrong_role":
        request["role"] = "writer"
        dated(candidate)
    elif case == "wrong_path":
        schema["properties"]["findings"]["items"]["properties"]["before_quote_id"] = {
            "type": "string", "pattern": QUALITATIVE_TEXT_PATTERN}
        finding["before_quote_id"] = "2023"
    elif case == "unrelated_schema":
        request["response_schema"] = {"type": "object", "properties": {"answer": {"type": "string", "pattern": QUALITATIVE_TEXT_PATTERN}},
                                      "required": ["answer"], "additionalProperties": False}
        candidate = {"answer": "The issuer discloses supplier risk in 2023."}
    elif case == "different_pattern":
        dated(candidate)
        for comparison in request["response_schema"]["properties"]["comparisons"]["properties"].values():
            comparison["properties"]["findings"]["items"]["properties"]["text"]["pattern"] = r"^[A-Za-z .]+$"
    elif case in {"unknown_quote", "date_and_unknown_quote"}:
        if case == "date_and_unknown_quote":
            dated(candidate)
        finding["before_quote_id"] = "an-invented-quotation"
    elif case == "credential_echo":
        finding["text"] = KEY
    elif case == "other_credential":
        finding["text"] = "sk-or-v1-" + "a" * 64
    body = response(content=candidate)
    if case == "unknown_model":
        dated(candidate)
        body = response(model="unapproved-model", content=candidate)
    elif case == "json_parse":
        body["choices"][0]["message"]["content"] = "{not valid JSON"
    elif case == "truncated":
        dated(candidate)
        body = response(content=candidate)
        body["choices"][0]["finish_reason"] = "length"
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=body))
    with pytest.raises(ProviderError) as error:
        engine.complete(**request)
    assert error.value.code == "model_output_invalid" and len(calls) == 1
    assert KEY not in str(error.value)
    with engine.ledger.connection() as db:
        call = dict(db.execute("SELECT * FROM model_calls").fetchone())
        audit = dict(db.execute("SELECT * FROM model_output_audit").fetchone())
    assert call["status"] == "invalid_output" and call["error_code"] == "model_output_invalid"
    assert call["result"] is None and engine.budget("run-risk")["held_usd"] == "0"
    if case == "credential_echo":
        assert audit["validation_stage"] == "credential_echo" and audit["candidate"] is None


def test_authenticated_gateway_reports_fixed_code_without_failed_prose(tmp_path, config, risk_request):
    request, candidate = risk_request
    dated(candidate)
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=response(content=candidate)))
    with TestClient(build_app(engine, TOKEN)) as client:
        result = client.post("/v1/reason", json=request, headers={"X-Model-Token": TOKEN})
        assert result.status_code == 502 and result.json()["error"]["code"] == "risk_narrative_format"
        assert "in 2023" not in result.text and KEY not in result.text
        budget = client.get("/v1/budget", params={"run_id": "run-risk"}, headers={"X-Model-Token": TOKEN}).json()
        assert budget["settled_calls"][0]["status"] == "invalid_output" and budget["held_usd"] == "0"
        repeated = client.post("/v1/reason", json=request, headers={"X-Model-Token": TOKEN})
        assert repeated.status_code == 409 and repeated.json()["error"]["code"] == "call_not_retriable"
    assert len(calls) == 1
