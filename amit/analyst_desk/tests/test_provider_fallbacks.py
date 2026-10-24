"""Fixed fallback routing and conservative accounting; mocked HTTP only."""
from copy import deepcopy
from decimal import Decimal
import json

import httpx
import pytest

from desk.model_profiles import model_profile, model_route
from desk.provider import ProviderError, ReasoningGateway, validate_config

PROFILE = "live-step16-fallbacks-v1"
PRIMARY = "openai/gpt-4.1-mini"
BACKUP = "mistralai/mistral-medium-3.1"
CRITIC = "google/gemini-2.5-flash"
KEY = "synthetic-fallback-provider-credential-" * 3
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"], "additionalProperties": False}


def configuration(version=PROFILE, **edits):
    profile = model_profile(version)
    return {"enabled": True, "authorization_id": "synthetic-fallback-authorization", "version": version,
            "cap_usd": "1.00", "per_run_usd": ".50", "max_calls_per_run": 12, "max_tokens_per_run": 250000,
            "prompt_token_ceiling": 49152, "max_message_bytes": 45056, "max_output_tokens": 2000,
            "models": profile["models"], **edits}


def arguments(**edits):
    return {"run_id": "synthetic-run", "call_id": "synthetic-run:planner:v1", "role": "planner",
            "messages": [{"role": "user", "content": "Use supplied public evidence."}],
            "response_schema": SCHEMA, "max_output_tokens": 256, **edits}


def completion(model=PRIMARY, *, cost="0.00001", prompt=10, output=5, content=None):
    return {"model": model, "id": "gen-synthetic-fallback", "usage": {
        "prompt_tokens": prompt, "completion_tokens": output, "total_tokens": prompt + output, "cost": cost},
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(content or {"answer": "Supplied evidence supports this synthetic result."})}}]}


def engine(tmp_path, config=None, reply=None):
    calls = []
    def capture(request):
        calls.append(request)
        return reply(request) if reply else httpx.Response(200, json=completion())
    return ReasoningGateway(config or configuration(), tmp_path / "ledger.sqlite", KEY, httpx.MockTransport(capture)), calls


def test_routes_are_fixed_independent_copies_and_explicitly_enabled():
    route = model_route(PROFILE, "producer")
    assert route == {"models": [PRIMARY, BACKUP], "providers": ["openai", "azure", "mistral/zdr"],
                     "allow_fallbacks": True, "prompt_usd_per_token": "4E-7", "completion_usd_per_token": "0.000002"}
    route["models"].append("unapproved")
    assert model_route(PROFILE, "producer")["models"] == [PRIMARY, BACKUP]
    assert model_route(PROFILE, "critic") == {"models": [CRITIC], "providers": ["google-ai-studio"],
        "allow_fallbacks": False, "prompt_usd_per_token": "3E-7", "completion_usd_per_token": "0.0000025"}
    with pytest.raises(ValueError):
        model_route(PROFILE, "planner")
    with pytest.raises(ValueError):
        model_profile({**configuration(), "version": "unreviewed-custom-version"})


@pytest.mark.parametrize("version", ["live-step6-openrouter-v1", "live-step10-mistral-v1", "live-step10-mistral-large2407-v1", "live-step10-google-critic-v1"])
def test_legacy_custom_policy_versions_still_bind_single_route(version):
    config = configuration(version)
    config["version"] = "existing-custom-policy"
    assert model_profile(config)["version"] == version
    assert model_route(config, "producer")["allow_fallbacks"] is False
    assert "routes" not in model_profile(config)


@pytest.mark.parametrize("model", [PRIMARY, BACKUP])
def test_primary_or_backup_success_is_one_private_bounded_request_and_one_reservation(tmp_path, model):
    gateway, calls = engine(tmp_path, reply=lambda _: httpx.Response(200, json=completion(model)))
    result = gateway.complete(**arguments())
    assert len(calls) == 1 and result["content"]["answer"]
    payload = json.loads(calls[0].content)
    assert "model" not in payload and payload["models"] == [PRIMARY, BACKUP]
    assert payload["provider"] == {"only": ["openai", "azure", "mistral/zdr"], "allow_fallbacks": True,
        "require_parameters": True, "data_collection": "deny", "max_price": {"prompt": .4, "completion": 2.0}}
    assert payload["messages"] == arguments()["messages"] and payload["max_tokens"] == 256
    assert payload["response_format"]["json_schema"]["strict"] is True and "reasoning" not in payload
    assert result["usage"]["requested_model"] == PRIMARY and result["usage"]["returned_model"] == model
    summary = gateway.budget("synthetic-run")
    assert summary["model_calls"] == 1 and summary["reported_spend_usd"] == "0.00001" and summary["held_usd"] == "0"
    assert summary["model_routes"] == {role: model_route(PROFILE, role) for role in ("producer", "critic")}
    with gateway.ledger.connection() as db:
        row = db.execute("SELECT reserved_usd,reserved_tokens FROM model_calls").fetchone()
    assert Decimal(row["reserved_usd"]) == Decimal(".0000004") * 49152 + Decimal(".000002") * 256
    assert row["reserved_tokens"] == 49152 + 256
    assert gateway.complete(**arguments())["cached"] is True and len(calls) == 1
    restarted = ReasoningGateway(configuration(), tmp_path / "ledger.sqlite", KEY,
        httpx.MockTransport(lambda _: pytest.fail("Cached fallback must not request another paid HTTP call")))
    assert restarted.complete(**arguments())["usage"]["returned_model"] == model
    assert restarted.budget()["model_calls"] == 1


def test_critic_cannot_fallback_into_any_producer_model_or_provider(tmp_path):
    gateway, calls = engine(tmp_path, reply=lambda _: httpx.Response(200, json=completion(CRITIC)))
    result = gateway.complete(**arguments(role="critic", call_id="synthetic:critic:v1"))
    payload = json.loads(calls[0].content)
    assert payload["model"] == CRITIC and "models" not in payload and payload["reasoning"] == {"enabled": False}
    assert payload["provider"] == {"only": ["google-ai-studio"], "allow_fallbacks": False,
        "require_parameters": True, "data_collection": "deny", "max_price": {"prompt": .3, "completion": 2.5}}
    assert result["usage"]["returned_model"] == CRITIC


@pytest.mark.parametrize("role,model", [("planner", CRITIC), ("critic", PRIMARY), ("critic", BACKUP),
                                         ("writer", "unknown-model"), ("writer", None), ("writer", KEY)])
def test_unapproved_or_wrong_role_response_is_terminal_and_retains_full_hold(tmp_path, role, model):
    gateway, calls = engine(tmp_path, reply=lambda _: httpx.Response(200, json=completion(model)))
    args = arguments(role=role)
    with pytest.raises(ProviderError) as error:
        gateway.complete(**args)
    assert error.value.code == "provider_response_invalid"
    summary = gateway.budget("synthetic-run")
    assert summary["uncertain_calls"] == 1 and summary["reported_spend_usd"] == "0"
    assert Decimal(summary["held_usd"]) > 0 and summary["tokens"] == 49152 + 256
    assert summary["settled_calls"] == []
    with gateway.ledger.connection() as db:
        row = db.execute("SELECT status,usage,result FROM model_calls").fetchone()
        audit = db.execute("SELECT validation_stage,candidate FROM model_output_audit").fetchone()
    assert row["status"] == "uncertain" and row["result"] is None
    assert json.loads(row["usage"])["requested_model"] == (CRITIC if role == "critic" else PRIMARY)
    assert tuple(audit) == ("returned_model", None)
    with pytest.raises(ProviderError) as repeat:
        gateway.complete(**args)
    assert repeat.value.code == "call_not_retriable" and len(calls) == 1
    assert KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()


@pytest.mark.parametrize("cost,prompt,output,stage", [(".001", 10, 5, "price_ceiling"),
    (".00001", 49153, 5, "token_ceiling"), (".00001", 10, 257, "token_ceiling")])
def test_route_accounting_violations_keep_full_holds_and_block_further_spending(tmp_path, cost, prompt, output, stage):
    gateway, calls = engine(tmp_path, reply=lambda _: httpx.Response(200, json=completion(cost=cost, prompt=prompt, output=output)))
    with pytest.raises(ProviderError) as error:
        gateway.complete(**arguments())
    assert error.value.code == "provider_response_invalid"
    before = gateway.budget()
    assert before["blocked"] and before["uncertain_calls"] == 1 and Decimal(before["held_usd"]) > 0
    assert before["tokens"] == 49152 + 256
    with gateway.ledger.connection() as db:
        assert db.execute("SELECT validation_stage FROM model_output_audit").fetchone()[0] == stage
    with pytest.raises(ProviderError) as blocked:
        gateway.complete(**arguments(call_id="next-call"))
    assert blocked.value.code == "accounting_blocked" and len(calls) == 1
    legacy = ReasoningGateway(configuration("live-step10-google-critic-v1", authorization_id="another-policy"),
        tmp_path / "ledger.sqlite", KEY, httpx.MockTransport(lambda _: pytest.fail("Anomaly must block every policy")))
    with pytest.raises(ProviderError) as new_policy:
        legacy.complete(**arguments(call_id="legacy-next-call"))
    assert new_policy.value.code == "accounting_blocked" and legacy.budget()["held_usd"] == before["held_usd"]


@pytest.mark.parametrize("model", [CRITIC, "unknown-model", None])
def test_wrong_model_does_not_mask_an_independent_accounting_breach(tmp_path, model):
    gateway, calls = engine(tmp_path, reply=lambda _: httpx.Response(200, json=completion(model, cost=".9")))
    with pytest.raises(ProviderError) as error:
        gateway.complete(**arguments())
    assert error.value.code == "provider_response_invalid"
    assert gateway.budget()["blocked"] and gateway.budget()["uncertain_calls"] == 1
    with pytest.raises(ProviderError) as blocked:
        gateway.complete(**arguments(call_id="must-stay-blocked"))
    assert blocked.value.code == "accounting_blocked" and len(calls) == 1


def test_exhausted_router_429_keeps_hold_and_cannot_create_a_retry_or_reset_by_profile(tmp_path):
    gateway, calls = engine(tmp_path, reply=lambda _: httpx.Response(429, json={"error": {"message": "Synthetic limit"}}))
    with pytest.raises(ProviderError) as error:
        gateway.complete(**arguments())
    assert error.value.code == "provider_http_429" and len(calls) == 1
    before = gateway.budget("synthetic-run")
    assert before["uncertain_calls"] == 1 and Decimal(before["held_usd"]) > 0
    with pytest.raises(ProviderError) as same:
        gateway.complete(**arguments())
    assert same.value.code == "call_not_retriable" and len(calls) == 1
    changed = ReasoningGateway(configuration("live-step10-google-critic-v1", authorization_id="legacy-after-fallback"),
        tmp_path / "ledger.sqlite", KEY, httpx.MockTransport(lambda _: pytest.fail("Limit must fail before HTTP")))
    assert changed.budget()["held_usd"] == before["held_usd"]
    assert changed.budget()["desk_cap_usd"] == "1.00" and Decimal(changed.budget()["per_run_usd"]) == Decimal(".50")
    assert changed.budget("synthetic-run")["tokens"] == before["tokens"]
    too_big = {**configuration(), "authorization_id": "cannot-reset-budget", "cap_usd": "2.00"}
    with pytest.raises(ProviderError) as cap:
        ReasoningGateway(too_big, tmp_path / "ledger.sqlite", KEY)
    assert cap.value.code == "desk_budget_increase_forbidden"


@pytest.mark.parametrize("change", [{"routes": {"producer": {"models": ["unknown"]}}},
    {"providers": {"producer": "unapproved"}}, {"models": {"producer": {"id": BACKUP}}}])
def test_runtime_arbitrary_routing_cannot_enter_configuration(change):
    with pytest.raises(ProviderError) as error:
        validate_config({**configuration(), **deepcopy(change)})
    assert error.value.code == "invalid_configuration"


def test_invalid_json_schema_output_with_valid_accounting_is_charged_but_never_retried(tmp_path):
    gateway, calls = engine(tmp_path, reply=lambda _: httpx.Response(200, json=completion(BACKUP, content={"wrong": "shape"})))
    with pytest.raises(ProviderError) as error:
        gateway.complete(**arguments())
    assert error.value.code == "model_output_invalid"
    assert gateway.budget()["held_usd"] == "0" and gateway.budget()["reported_spend_usd"] == "0.00001"
    assert gateway.budget()["settled_calls"][0]["usage"]["returned_model"] == BACKUP
    with pytest.raises(ProviderError):
        gateway.complete(**arguments())
    assert len(calls) == 1
