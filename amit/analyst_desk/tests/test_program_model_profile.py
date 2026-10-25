"""Restricted model routes and policy migration; synthetic credentials and HTTP."""
from copy import deepcopy
from decimal import Decimal
import json

import httpx
import pytest

from desk.model_profiles import model_profile, model_route
from desk.provider import ProviderError, ReasoningGateway, validate_config
from ops import prepare_live as prep


PROFILE = "live-program-models-v1"
PRIMARY = "openai/gpt-4.1-mini"
BACKUP = "openai/gpt-4.1-nano"
CRITIC = "google/gemini-3.1-flash-lite"
# This profile deliberately uses only these three approved catalogue entries.
APPROVED_MODELS = frozenset({PRIMARY, BACKUP, CRITIC})
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}},
          "required": ["answer"], "additionalProperties": False}


def configuration():
    return {"enabled": True, "authorization_id": "synthetic-restricted-authorization", "version": PROFILE,
            "cap_usd": "1.00", "per_run_usd": "0.50", "max_calls_per_run": 12,
            "max_tokens_per_run": 250000, "prompt_token_ceiling": 49152, "max_message_bytes": 45056,
            "max_output_tokens": 2000, "models": model_profile(PROFILE)["models"]}


def test_every_route_uses_only_approved_models_and_conservative_prices():
    assert validate_config(configuration()) == configuration()
    producer = model_route(PROFILE, "producer")
    critic = model_route(PROFILE, "critic")
    assert producer == {"models": [PRIMARY, BACKUP], "providers": ["openai", "azure"],
                        "allow_fallbacks": True, "prompt_usd_per_token": "4E-7", "completion_usd_per_token": "0.0000016"}
    assert critic == {"models": [CRITIC], "providers": ["google-ai-studio"], "allow_fallbacks": False,
                      "prompt_usd_per_token": "2.5E-7", "completion_usd_per_token": "0.0000015"}
    for route in (producer, critic):
        assert set(route["models"]) <= APPROVED_MODELS
        assert not any("mistral" in model or "gemini-2.5" in model for model in route["models"])
    assert set(producer["models"]).isdisjoint(critic["models"])
    producer["models"].append("unapproved")
    assert model_route(PROFILE, "producer")["models"] == [PRIMARY, BACKUP]


@pytest.mark.parametrize("role,returned_model", [("planner", PRIMARY), ("writer", BACKUP), ("critic", CRITIC)])
def test_fixed_route_payload_schema_and_minimal_critic_reasoning(tmp_path, role, returned_model):
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"model": returned_model, "id": "gen-synthetic-restricted",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
                      "completion_tokens_details": {"reasoning_tokens": 2 if role == "critic" else 0}, "cost": "0.00001"},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"answer": "Synthetic supported answer."})}}]})
    gateway = ReasoningGateway(configuration(), tmp_path / "ledger.sqlite", "synthetic-provider-key-" * 3,
                               httpx.MockTransport(respond))
    result = gateway.complete(run_id="synthetic-run", call_id="synthetic-" + role, role=role,
                              messages=[{"role": "user", "content": "Use the supplied evidence."}],
                              response_schema=SCHEMA, max_output_tokens=256)
    assert len(requests) == 1 and result["usage"]["returned_model"] == returned_model
    payload = requests[0]
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert payload["provider"]["require_parameters"] is True
    assert payload["provider"]["data_collection"] == "deny"
    if role == "critic":
        assert payload["model"] == CRITIC and "models" not in payload
        assert payload["reasoning"] == {"effort": "minimal", "exclude": True}
        assert payload["provider"]["only"] == ["google-ai-studio"]
        assert payload["provider"]["allow_fallbacks"] is False
        assert payload["provider"]["max_price"] == {"prompt": 0.25, "completion": 1.5}
    else:
        assert payload["models"] == [PRIMARY, BACKUP] and "model" not in payload
        assert payload["provider"]["only"] == ["openai", "azure"]
        assert payload["provider"]["allow_fallbacks"] is True
        assert payload["provider"]["max_price"] == {"prompt": 0.4, "completion": 1.6}
        assert "reasoning" not in payload
    budget = gateway.budget("synthetic-run")
    assert budget["model_calls"] == 1 and budget["tokens"] == 15
    assert budget["reported_spend_usd"] == "0.00001" and budget["held_usd"] == "0"
    with gateway.ledger.connection() as db:
        reserved = db.execute("SELECT reserved_usd FROM model_calls").fetchone()[0]
    route = model_route(PROFILE, "critic" if role == "critic" else "producer")
    assert Decimal(reserved) == Decimal(route["prompt_usd_per_token"]) * 49152 + Decimal(route["completion_usd_per_token"]) * 256


@pytest.mark.parametrize("role,returned_model", [("writer", "mistralai/mistral-medium-3.1"),
    ("critic", "google/gemini-2.5-flash"), ("critic", PRIMARY), ("writer", CRITIC)])
def test_old_or_wrong_role_models_cannot_be_accepted(tmp_path, role, returned_model):
    reply = {"model": returned_model, "id": "gen-synthetic-wrong-model", "usage": {
        "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": "0.00001"},
        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"answer": "Synthetic answer."})}}]}
    gateway = ReasoningGateway(configuration(), tmp_path / "ledger.sqlite", "synthetic-provider-key-" * 3,
                               httpx.MockTransport(lambda _: httpx.Response(200, json=reply)))
    with pytest.raises(ProviderError) as error:
        gateway.complete(run_id="synthetic-run", call_id="synthetic-call", role=role,
            messages=[{"role": "user", "content": "Use supplied evidence."}], response_schema=SCHEMA, max_output_tokens=256)
    assert error.value.code == "provider_response_invalid"
    assert gateway.budget()["uncertain_calls"] == 1
    assert Decimal(gateway.budget()["held_usd"]) > 0


def test_switch_keeps_old_history_credentials_and_limits_but_requires_exact_activation(tmp_path, monkeypatch):
    private = tmp_path / "private"
    for name, value in {"PRIVATE": private, "CONFIG_FILE": private / "model_config.json",
                        "KEY_FILE": private / "provider.key", "APPROVAL_FILE": private / "authorization.json"}.items():
        monkeypatch.setattr(prep, name, value)
    source = tmp_path / "source.env"
    source.write_text("OPENROUTER_API_KEY=" + "synthetic-provider-credential-" * 3 + "\n")
    prepared = prep.prepare(source)
    prep.authorize(prepared["proposal_hash"], "Synthetic prior decision")
    previous = deepcopy(prep.load_config())
    key_bytes = prep.KEY_FILE.read_bytes()
    approval_bytes = prep.APPROVAL_FILE.read_bytes()
    sentinel = private / "ledger-sentinel"
    sentinel.write_bytes(b"all previous charges and uncertain holds")
    result = prep.switch_profile("program-office", prepared["proposal_hash"])
    current = prep.load_config()
    assert current["version"] == PROFILE and current["models"] == model_profile(PROFILE)["models"]
    assert current["authorization_id"] != previous["authorization_id"]
    assert not current["enabled"] and not prep.APPROVAL_FILE.exists()
    for field in ("cap_usd", "per_run_usd", "max_tokens_per_run", "max_output_tokens"):
        assert current[field] == previous[field]
    assert current["max_calls_per_run"] is None
    assert prep.KEY_FILE.read_bytes() == key_bytes
    assert sentinel.read_bytes() == b"all previous charges and uncertain holds"
    assert result["paid_calls_performed"] == 0 and result["ledger_changed"] is False
    archive = next((private / "policy_history").iterdir())
    assert json.loads((archive / "model_config.json").read_text()) == previous
    assert (archive / "authorization.json").read_bytes() == approval_bytes
    with pytest.raises(ValueError, match="stale"):
        prep.authorize(prepared["proposal_hash"], "A previous decision is insufficient")
    prep.authorize(result["proposal_hash"], "Synthetic exact replacement decision")
    assert prep.load_config()["enabled"]


def test_new_profile_uses_same_actual_ledger_and_cannot_reset_spend_or_uncertain_holds(tmp_path):
    old_config = configuration()
    old_profile = model_profile("live-step16-fallbacks-v1")
    old_config.update(version=old_profile["version"], models=old_profile["models"],
                      authorization_id="synthetic-original-authorization")
    ledger = tmp_path / "ledger.sqlite"
    request_count = 0
    def respond(request):
        nonlocal request_count
        request_count += 1
        if request_count == 2:
            return httpx.Response(429, json={"error": {"message": "Synthetic rate limit"}})
        return httpx.Response(200, json={"model": PRIMARY, "id": "gen-synthetic-original",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": "0.00001"},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"answer": "Synthetic answer."})}}]})
    old = ReasoningGateway(old_config, ledger, "synthetic-provider-key-" * 3, httpx.MockTransport(respond))
    arguments = {"run_id": "synthetic-run", "role": "planner", "messages": [{"role": "user", "content": "Supplied public evidence."}],
                 "response_schema": SCHEMA, "max_output_tokens": 256}
    old.complete(call_id="synthetic-first", **arguments)
    with pytest.raises(ProviderError) as error:
        old.complete(call_id="synthetic-second", **arguments)
    assert error.value.code == "provider_http_429" and request_count == 2
    before = old.budget("synthetic-run")
    replacement = ReasoningGateway(configuration(), ledger, "synthetic-provider-key-" * 3,
        httpx.MockTransport(lambda _: pytest.fail("A policy migration must not request a completion")))
    after = replacement.budget("synthetic-run")
    for field in ("reported_spend_usd", "held_usd", "committed_usd", "remaining_authorization_usd",
                  "model_calls", "tokens", "uncertain_calls", "desk_cap_usd", "per_run_usd"):
        assert after[field] == before[field]
    assert after["reported_spend_usd"] == "0.00001" and Decimal(after["held_usd"]) > 0
    assert after["model_calls"] == 2 and after["uncertain_calls"] == 1
    assert after["model_profile"] == PROFILE and after["models"]["critic"] == CRITIC
    with pytest.raises(ProviderError) as reused:
        replacement.complete(call_id="synthetic-first", **arguments)
    assert reused.value.code == "call_id_conflict"
    assert replacement.budget()["held_usd"] == before["held_usd"]
    larger = {**configuration(), "authorization_id": "synthetic-forbidden-increase", "cap_usd": "2.00"}
    with pytest.raises(ProviderError) as increase:
        ReasoningGateway(larger, ledger, "synthetic-provider-key-" * 3)
    assert increase.value.code == "desk_budget_increase_forbidden"
