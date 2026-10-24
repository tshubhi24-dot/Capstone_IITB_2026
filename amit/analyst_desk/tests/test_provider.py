"""Money and authority boundaries with mocked HTTP only; no paid model calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
import json
import threading

from fastapi.testclient import TestClient
import httpx
import pytest

from desk.model_gateway import build_app
from desk.provider import BudgetLedger, GATEWAY_URL, ModelGatewayClient, PROVIDER_URL, ProviderError, ReasoningGateway

KEY = "invented-provider-credential-" * 3
TOKEN = "invented-private-gateway-token-" * 3
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"], "additionalProperties": False}


@pytest.fixture
def config():
    return {"enabled": True, "authorization_id": "test-authorization", "version": "test-v1", "cap_usd": "1.00", "per_run_usd": ".50",
            "max_calls_per_run": 12, "max_tokens_per_run": 150000, "prompt_token_ceiling": 32768, "max_message_bytes": 28000, "max_output_tokens": 4096,
            "models": {"producer": {"id": "openai/gpt-4.1-mini", "prompt_usd_per_token": "0.0000004", "completion_usd_per_token": "0.0000016"},
                       "critic": {"id": "openai/gpt-4.1", "prompt_usd_per_token": "0.000002", "completion_usd_per_token": "0.000008"}}}


def arguments(**edits):
    return {"run_id": "run-one", "call_id": "run-one:planner:input-v1", "role": "planner", "messages": [{"role": "user", "content": "Use the supplied test-only evidence."}],
            "response_schema": SCHEMA, "max_output_tokens": 256, **edits}


def response(model="openai/gpt-4.1-mini", content=None, usage=None):
    return {"model": model, "choices": [{"message": {"content": json.dumps(content if content is not None else {"answer": "Test-only source-backed result."})}, "finish_reason": "stop"}],
            "usage": usage if usage is not None else {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": .0001}}


def gateway(tmp_path, config, handler=None):
    calls = []
    def capture(request):
        calls.append(request)
        return handler(request) if handler else httpx.Response(200, json=response(json.loads(request.content)["model"]))
    engine = ReasoningGateway(config, tmp_path / "ledger.sqlite", KEY, httpx.MockTransport(capture))
    return engine, calls


def test_exact_provider_and_price_policy_critic_and_persistent_idempotency(tmp_path, config):
    engine, calls = gateway(tmp_path, config)
    result = engine.complete(**arguments())
    assert result["content"]["answer"] and result["usage"]["cost_usd"] == "0.0001"
    request = calls[0]
    assert str(request.url) == PROVIDER_URL and request.headers["Authorization"] == "Bearer " + KEY
    payload = json.loads(request.content)
    assert payload["provider"] == {"only": ["openai"], "allow_fallbacks": False, "require_parameters": True, "data_collection": "deny", "max_price": {"prompt": .4, "completion": 1.6}}
    assert payload["response_format"]["json_schema"]["strict"] is True and "usage" not in payload
    restarted = ReasoningGateway(config, tmp_path / "ledger.sqlite", KEY, httpx.MockTransport(lambda _: pytest.fail("Cached result must not call provider")))
    assert restarted.complete(**arguments())["cached"] is True
    assert restarted.budget()["model_calls"] == 1
    with pytest.raises(ProviderError, match="different content"):
        restarted.complete(**arguments(messages=[{"role": "user", "content": "Changed input"}]))
    critic = engine.complete(**arguments(role="critic", call_id="run-one:critic:v1"))
    assert critic["usage"]["model"] == "openai/gpt-4.1"
    assert json.loads(calls[1].content)["provider"]["max_price"] == {"prompt": 2.0, "completion": 8.0}
    assert engine.budget()["committed_usd"] == "0.0002"


def test_unauthorized_and_missing_key_cannot_spend(tmp_path, config):
    disabled = {**config, "enabled": False}
    engine, calls = gateway(tmp_path, disabled)
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "live_not_authorized" and calls == [] and engine.budget()["model_calls"] == 0
    missing = ReasoningGateway(config, tmp_path / "ledger.sqlite", "")
    with pytest.raises(ProviderError) as error:
        missing.complete(**arguments())
    assert error.value.code == "provider_key_missing" and missing.budget()["model_calls"] == 0


def test_authorization_cannot_reset_existing_limits_or_spend(tmp_path, config):
    engine, _ = gateway(tmp_path, config)
    engine.complete(**arguments())
    disabled = ReasoningGateway({**config, "enabled": False}, tmp_path / "ledger.sqlite", KEY)
    assert disabled.budget()["committed_usd"] == "0.0001"
    enabled = ReasoningGateway(config, tmp_path / "ledger.sqlite", KEY)
    assert enabled.budget()["model_calls"] == 1
    with pytest.raises(ProviderError) as error:
        ReasoningGateway({**config, "cap_usd": "2.00"}, tmp_path / "ledger.sqlite", KEY)
    assert error.value.code == "authorization_changed"


def test_parallel_reservations_cannot_overspend_shared_authorization(tmp_path, config):
    config = {**config, "cap_usd": ".02", "per_run_usd": ".02"}
    ledger_one = BudgetLedger(tmp_path / "shared.sqlite", config)
    ledger_two = BudgetLedger(tmp_path / "shared.sqlite", config)
    barrier = threading.Barrier(2)
    def reserve(index, ledger):
        barrier.wait(timeout=3)
        try:
            ledger.reserve(f"run-{index}", f"call-{index}", f"hash-{index}", Decimal(".015"), 10000)
            return "reserved"
        except ProviderError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda pair: reserve(*pair), [(1, ledger_one), (2, ledger_two)]))
    assert sorted(results) == ["budget_exhausted", "reserved"]
    assert Decimal(ledger_one.summary()["committed_usd"]) == Decimal(".015")


@pytest.mark.parametrize("failure", ["timeout", "missing_usage", "missing_cost", "bad_token_total", "redirect", "http_error"])
def test_uncertain_provider_outcomes_hold_budget_and_never_retry(tmp_path, config, failure):
    def fail(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("secret provider diagnostics must not escape", request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://untrusted.invalid/steal"})
        if failure == "http_error":
            return httpx.Response(500, text=KEY)
        data = response()
        if failure == "missing_usage":
            del data["usage"]
        elif failure == "missing_cost":
            del data["usage"]["cost"]
        else:
            data["usage"]["total_tokens"] = 999
        return httpx.Response(200, json=data)
    engine, calls = gateway(tmp_path, config, fail)
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert KEY not in str(error.value)
    assert error.value.__cause__ is None and error.value.__context__ is None
    summary = engine.budget()
    assert summary["reported_spend_usd"] == "0" and Decimal(summary["held_usd"]) > 0 and summary["uncertain_calls"] == 1
    with pytest.raises(ProviderError) as repeated:
        engine.complete(**arguments())
    assert repeated.value.code == "call_not_retriable" and len(calls) == 1


def test_invalid_model_output_is_charged_but_never_returned_or_retried(tmp_path, config):
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=response(content={"unsupported": "extra"})))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "model_output_invalid"
    assert engine.budget()["reported_spend_usd"] == "0.0001" and engine.budget()["held_usd"] == "0"
    with pytest.raises(ProviderError):
        engine.complete(**arguments())
    assert len(calls) == 1


def test_provider_credential_echo_never_enters_results_or_private_cache(tmp_path, config):
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=response(content={"answer": KEY})))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "model_output_invalid" and KEY not in str(error.value)
    with engine.ledger.connection() as db:
        row = db.execute("SELECT result,error_code,charged_usd FROM model_calls").fetchone()
    assert row["result"] is None and row["charged_usd"] == "0.0001"
    assert KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    assert len(calls) == 1


def test_above_reservation_accounting_blocks_all_further_calls(tmp_path, config):
    large = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": .75}
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=response(usage=large)))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "accounting_anomaly"
    assert engine.budget()["blocked"] and engine.budget()["reported_spend_usd"] == "0.75"
    with pytest.raises(ProviderError) as blocked:
        engine.complete(**arguments(call_id="another-call"))
    assert blocked.value.code == "accounting_blocked" and len(calls) == 1


@pytest.mark.parametrize("change", [{"max_calls_per_run": 1}, {"max_tokens_per_run": 32768}])
def test_original_call_and_token_limits_are_enforced(tmp_path, config, change):
    engine, calls = gateway(tmp_path, {**config, **change})
    if "max_calls_per_run" in change:
        engine.complete(**arguments())
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments(call_id="a-new-call"))
    assert error.value.code == "run_limit_exhausted"
    assert len(calls) == int("max_calls_per_run" in change)


@pytest.mark.parametrize("edits", [{"role": "publisher"}, {"max_output_tokens": 4097},
                                    {"messages": [{"role": "user", "content": "x" * 28001}]},
                                    {"messages": [{"role": "user", "content": KEY}]},
                                    {"response_schema": {"$ref": "https://untrusted.invalid/schema"}}])
def test_unapproved_context_roles_and_schema_never_reach_provider(tmp_path, config, edits):
    engine, calls = gateway(tmp_path, config)
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments(**edits))
    assert error.value.code == "invalid_request" and calls == [] and engine.budget()["model_calls"] == 0


def test_gateway_http_auth_disabled_mode_and_validation_do_not_expose_content(tmp_path, config):
    engine, calls = gateway(tmp_path, {**config, "enabled": False})
    with TestClient(build_app(engine, TOKEN)) as client:
        assert client.get("/health").json()["enabled"] is False
        assert client.get("/v1/budget").status_code == 401
        assert client.post("/v1/reason", json=arguments()).status_code == 401
        client.headers["X-Model-Token"] = TOKEN
        assert client.get("/v1/budget").json()["model_calls"] == 0
        denied = client.post("/v1/reason", json=arguments())
        assert denied.status_code == 403 and denied.json()["error"]["code"] == "live_not_authorized"
        malformed = client.post("/v1/reason", json={**arguments(), "extra": KEY})
        assert malformed.status_code == 422 and KEY not in malformed.text
        assert client.get("/openapi.json").status_code == 404
    assert calls == []


def test_client_address_proxy_redirect_and_error_boundaries(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://untrusted.invalid:9999")
    seen = []
    def redirect(request):
        seen.append(request)
        return httpx.Response(302, headers={"Location": "https://untrusted.invalid/steal"})
    client = ModelGatewayClient(TOKEN, transport=httpx.MockTransport(redirect))
    with pytest.raises(ProviderError):
        client.complete(**arguments())
    assert len(seen) == 1 and str(seen[0].url) == GATEWAY_URL + "/v1/reason"
    assert seen[0].headers["X-Model-Token"] == TOKEN and "Authorization" not in seen[0].headers
    with pytest.raises(ProviderError):
        ModelGatewayClient(TOKEN, base_url="https://untrusted.invalid")
