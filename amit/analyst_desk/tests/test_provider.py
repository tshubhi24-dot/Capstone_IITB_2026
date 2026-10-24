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
from desk.provider import BudgetLedger, FORBIDDEN_BODY_LIMIT, GATEWAY_URL, MODEL_PROFILES, ModelGatewayClient, PROVIDER_URL, ProviderError, ReasoningGateway, SAFE_ERROR_CODES, model_profile, safe_error_code

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


def test_reviewed_mistral_pair_has_fixed_private_route_and_price_ceilings(tmp_path, config):
    profile = model_profile("live-step10-mistral-v1")
    revised = {**config, "version": profile["version"], "models": profile["models"]}
    engine, calls = gateway(tmp_path, revised)
    engine.complete(**arguments())
    engine.complete(**arguments(role="critic", call_id="critic-call"))
    producer, critic = (json.loads(call.content) for call in calls)
    assert producer["model"] == "mistralai/mistral-medium-3.1" and critic["model"] == "mistralai/mistral-large-2512"
    assert producer["provider"] == {"only": ["mistral/zdr"], "allow_fallbacks": False, "require_parameters": True,
                                   "data_collection": "deny", "max_price": {"prompt": .4, "completion": 2.0}}
    assert critic["provider"] == {**producer["provider"], "max_price": {"prompt": .5, "completion": 1.5}}
    summary = engine.budget()
    assert summary["models"] == {role: policy["id"] for role, policy in profile["models"].items()}
    assert summary["model_profile"] == profile["version"] and summary["provider"] == "mistral/zdr"
    assert KEY not in json.dumps(summary)


def test_model_profiles_return_independent_copies_and_preserve_legacy_versions(config):
    profile = model_profile(config)
    assert profile["version"] == "live-step6-openrouter-v1" and profile["provider"] == "openai"
    profile["models"]["producer"]["id"] = "unapproved"
    assert model_profile(config)["models"]["producer"]["id"] == "openai/gpt-4.1-mini"
    assert set(MODEL_PROFILES) == {"live-step6-openrouter-v1", "live-step10-mistral-v1", "live-step10-mistral-large2407-v1", "live-step10-google-critic-v1"}
    with pytest.raises(ValueError):
        model_profile("unapproved")


def test_large2407_profile_preserves_producer_route_and_exposes_frozen_budget_policy(tmp_path, config):
    profile = model_profile("live-step10-mistral-large2407-v1")
    revised = {**config, "version": profile["version"], "models": profile["models"], **profile["limits"]}
    engine, calls = gateway(tmp_path, revised)
    engine.complete(**arguments(role="critic", call_id="large2407-critic"))
    payload = json.loads(calls[0].content)
    assert profile["models"]["producer"] == model_profile("live-step10-mistral-v1")["models"]["producer"]
    assert payload["model"] == "mistralai/mistral-large-2407"
    assert payload["provider"] == {"only": ["mistral/zdr"], "allow_fallbacks": False, "require_parameters": True,
                                   "data_collection": "deny", "max_price": {"prompt": 2.0, "completion": 6.0}}
    summary = engine.budget("run-one")
    assert summary["policy_hash"] == engine.ledger.policy_hash
    assert summary["model_profile"] == profile["version"]
    for key in ("prompt_token_ceiling", "max_message_bytes", "max_output_tokens", "max_calls_per_run", "max_tokens_per_run"):
        assert summary[key] == revised[key]
    disabled = ReasoningGateway({**revised, "enabled": False}, tmp_path / "ledger.sqlite", KEY)
    assert disabled.budget("run-one")["policy_hash"] == summary["policy_hash"]
    assert KEY not in json.dumps(summary)


@pytest.mark.parametrize("field,excess", [("prompt_token_ceiling", 49153), ("max_message_bytes", 45057)])
def test_large2407_gateway_refuses_context_above_reviewed_limit(tmp_path, config, field, excess):
    profile = model_profile("live-step10-mistral-large2407-v1")
    revised = {**config, "version": profile["version"], "models": profile["models"], **profile["limits"], field: excess}
    if field == "max_message_bytes":
        # Keep generic formatting overhead valid so the reviewed bound is tested.
        revised["max_message_bytes"] = 45057
        revised["prompt_token_ceiling"] = 49153
    with pytest.raises(ProviderError) as error:
        gateway(tmp_path, revised)
    assert error.value.code == "invalid_configuration"


def test_tightened_final_critic_reservation_preserves_original_twelve_call_token_limit_and_holds(tmp_path, config):
    old_profile = model_profile("live-step10-mistral-v1")
    original = {**config, "version": old_profile["version"], "models": old_profile["models"],
                "max_calls_per_run": 12, "max_tokens_per_run": 250000, "prompt_token_ceiling": 65536,
                "max_message_bytes": 60000, "max_output_tokens": 2000}
    path = tmp_path / "same-run.sqlite"
    ledger = BudgetLedger(path, original)
    for index, total_tokens in enumerate([6000] * 8 + [12185]):
        ledger.reserve("same-run", f"settled-{index}", f"hash-{index}", Decimal(".04"), 67536)
        ledger.settle(f"settled-{index}", {"cost_usd": ".001", "total_tokens": total_tokens}, {"content": "Synthetic result"})
    for index in range(2):
        ledger.reserve("same-run", f"uncertain-{index}", f"uncertain-hash-{index}", Decimal(".035768"), 67536)
        ledger.uncertain(f"uncertain-{index}", "provider_http_429")
    previous = ledger.summary("same-run")
    assert previous["tokens"] == 195257 and previous["model_calls"] == 11 and previous["uncertain_calls"] == 2

    profile = model_profile("live-step10-mistral-large2407-v1")
    revised = {**original, "authorization_id": "final-critic-policy", "version": profile["version"],
               "models": profile["models"], **profile["limits"]}
    engine = ReasoningGateway(revised, path, KEY)
    with pytest.raises(ProviderError) as oversized:
        engine.ledger.reserve("same-run", "oversized-final", "oversized-hash", Decimal(".110304"), 67536)
    assert oversized.value.code == "run_limit_exhausted"
    engine.ledger.reserve("same-run", "final-critic", "final-hash", Decimal(".110304"),
                          revised["prompt_token_ceiling"] + revised["max_output_tokens"])
    current = engine.budget("same-run")
    assert current["tokens"] == 246409 and current["model_calls"] == 12 and current["uncertain_calls"] == 2
    assert current["max_tokens_per_run"] == 250000 and current["max_calls_per_run"] == 12
    assert current["cap_usd"] == "1.00" and Decimal(current["per_run_usd"]) == Decimal(".50")
    with pytest.raises(ProviderError) as thirteenth:
        engine.ledger.reserve("same-run", "thirteenth-call", "thirteenth-hash", Decimal(".000001"), 1)
    assert thirteenth.value.code == "run_limit_exhausted"
    with engine.ledger.connection() as db:
        holds = db.execute("SELECT authorization_id,status,reserved_tokens,reserved_usd,error_code FROM model_calls WHERE call_id LIKE 'uncertain-%' ORDER BY call_id").fetchall()
        original_policy = db.execute("SELECT policy_hash FROM authorization WHERE id=?", (original["authorization_id"],)).fetchone()[0]
    assert [tuple(row) for row in holds] == [(original["authorization_id"], "uncertain", 67536, "0.035768", "provider_http_429")] * 2
    assert original_policy == ledger.policy_hash and current["policy_hash"] != original_policy


@pytest.mark.parametrize("failure", ["mixed_pair", "unreviewed_model", "price_increase", "mismatched_version"])
def test_unreviewed_model_pair_or_price_cannot_reach_provider(tmp_path, config, failure):
    revised = deepcopy(config)
    if failure == "mixed_pair":
        revised["models"]["critic"] = model_profile("live-step10-mistral-v1")["models"]["critic"]
    elif failure == "unreviewed_model":
        revised["models"]["producer"]["id"] = "unreviewed/free-model"
    elif failure == "price_increase":
        revised["models"] = model_profile("live-step10-mistral-v1")["models"]
        revised["models"]["producer"]["completion_usd_per_token"] = "0.0000021"
    else:
        revised["version"] = "live-step10-mistral-v1"
    with pytest.raises(ProviderError) as error:
        gateway(tmp_path, revised)
    assert error.value.code == "invalid_configuration"


def test_new_model_policy_retains_every_old_charge_and_uncertain_hold(tmp_path, config):
    ledger = BudgetLedger(tmp_path / "shared.sqlite", config)
    ledger.reserve("old-paid-run", "old-paid", "old-paid-hash", Decimal(".4"), 100)
    ledger.settle("old-paid", {"cost_usd": ".2", "total_tokens": 30}, {"content": "test-only"})
    ledger.reserve("old-uncertain-run", "old-uncertain", "old-uncertain-hash", Decimal(".45"), 100)
    ledger.uncertain("old-uncertain", "provider_http_403")
    profile = model_profile("live-step10-mistral-v1")
    revised = {**config, "authorization_id": "replacement-policy", "version": profile["version"], "models": profile["models"]}
    replacement = BudgetLedger(tmp_path / "shared.sqlite", revised)
    summary = replacement.summary()
    assert summary["reported_spend_usd"] == "0.2" and summary["held_usd"] == "0.45"
    assert summary["committed_usd"] == "0.65" and summary["remaining_authorization_usd"] == "0.35"
    assert summary["uncertain_calls"] == 1 and summary["model_calls"] == 2 and summary["ledger_scope"] == "desk_lifetime"
    with pytest.raises(ProviderError) as error:
        replacement.reserve("new-run", "over-budget", "new-hash", Decimal(".4"), 100)
    assert error.value.code == "budget_exhausted"
    replacement.reserve("new-run", "within-budget", "new-hash", Decimal(".3"), 100)
    assert replacement.summary("new-run")["authorization_committed_usd"] == "0.95"
    assert replacement.summary("old-uncertain-run")["held_usd"] == "0.45"
    assert ledger.summary()["remaining_authorization_usd"] == "0.05"


def test_fresh_authorization_cannot_raise_original_desk_ceiling(tmp_path, config):
    ledger = BudgetLedger(tmp_path / "shared.sqlite", config)
    with pytest.raises(ProviderError) as error:
        BudgetLedger(tmp_path / "shared.sqlite", {**config, "authorization_id": "new-policy", "cap_usd": "2.00"})
    assert error.value.code == "desk_budget_increase_forbidden"
    assert ledger.summary()["desk_cap_usd"] == "1.00" and ledger.summary()["model_calls"] == 0


def test_parallel_reservations_across_policies_cannot_reset_cumulative_cap(tmp_path, config):
    original = {**config, "cap_usd": ".02", "per_run_usd": ".02"}
    ledger_one = BudgetLedger(tmp_path / "shared.sqlite", original)
    ledger_two = BudgetLedger(tmp_path / "shared.sqlite", {**original, "authorization_id": "new-policy", "version": "test-v2"})
    barrier = threading.Barrier(2)
    def reserve(pair):
        index, ledger = pair
        barrier.wait(timeout=3)
        try:
            ledger.reserve(f"run-{index}", f"call-{index}", f"hash-{index}", Decimal(".015"), 100)
            return "reserved"
        except ProviderError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, [(1, ledger_one), (2, ledger_two)]))
    assert sorted(outcomes) == ["budget_exhausted", "reserved"]
    assert ledger_one.summary()["committed_usd"] == ledger_two.summary()["committed_usd"] == "0.015"


@pytest.mark.parametrize("boundary", ["spend", "calls", "tokens"])
def test_same_run_original_limits_survive_policy_change(tmp_path, config, boundary):
    original = {**config, "per_run_usd": ".1", "max_calls_per_run": 1 if boundary == "calls" else 12,
                "max_tokens_per_run": 100 if boundary == "tokens" else 150000}
    ledger = BudgetLedger(tmp_path / "shared.sqlite", original)
    ledger.reserve("same-run", "old-call", "old-hash", Decimal(".06"), 60)
    revised = {**config, "authorization_id": "new-policy", "per_run_usd": ".8", "max_calls_per_run": 20, "max_tokens_per_run": 500000}
    replacement = BudgetLedger(tmp_path / "shared.sqlite", revised)
    with pytest.raises(ProviderError) as error:
        replacement.reserve("same-run", "new-call", "new-hash", Decimal(".06") if boundary == "spend" else Decimal(".001"), 60)
    assert error.value.code == ("budget_exhausted" if boundary == "spend" else "run_limit_exhausted")
    assert replacement.summary("same-run")["per_run_usd"] == "0.1"
    assert replacement.summary()["model_calls"] == 1


def test_old_accounting_anomaly_blocks_new_policy_and_all_summaries(tmp_path, config):
    ledger = BudgetLedger(tmp_path / "shared.sqlite", config)
    ledger.reserve("old-run", "old-call", "old-hash", Decimal(".01"), 100)
    with pytest.raises(ProviderError) as anomaly:
        ledger.settle("old-call", {"cost_usd": ".02", "total_tokens": 20}, {"content": "test-only"})
    assert anomaly.value.code == "accounting_anomaly"
    revised = BudgetLedger(tmp_path / "shared.sqlite", {**config, "authorization_id": "new-policy"})
    with pytest.raises(ProviderError) as blocked:
        revised.reserve("new-run", "new-call", "new-hash", Decimal(".01"), 100)
    assert blocked.value.code == "accounting_blocked" and revised.summary()["blocked"]
    assert revised.summary()["reported_spend_usd"] == "0.02"


def test_new_policy_cannot_return_old_policy_cached_result(tmp_path, config):
    engine, _ = gateway(tmp_path, config)
    engine.complete(**arguments())
    revised, calls = gateway(tmp_path, {**config, "authorization_id": "new-policy"})
    with pytest.raises(ProviderError) as error:
        revised.complete(**arguments())
    assert error.value.code == "call_id_conflict" and calls == [] and revised.budget()["model_calls"] == 1


def test_legacy_ledger_requires_original_unchanged_policy_for_migration(tmp_path, config):
    path = tmp_path / "legacy.sqlite"
    original = BudgetLedger(path, config)
    original.reserve("old-run", "old-call", "old-hash", Decimal(".1"), 100)
    with original.connection() as db:
        db.execute("DROP TABLE desk_budget")
        db.execute("DROP TABLE run_limits")
    with pytest.raises(ProviderError) as error:
        BudgetLedger(path, {**config, "authorization_id": "new-policy", "cap_usd": "2.00"})
    assert error.value.code == "authorization_changed"
    migrated = BudgetLedger(path, config)
    assert migrated.summary()["desk_cap_usd"] == "1.00" and migrated.summary()["held_usd"] == "0.1"
    revised = BudgetLedger(path, {**config, "authorization_id": "new-policy"})
    assert revised.summary()["model_calls"] == 1 and revised.summary("old-run")["per_run_usd"] == "0.50"


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
    expected = {"timeout": "provider_read_timeout", "missing_usage": "provider_usage_missing", "missing_cost": "provider_usage_cost_missing",
                "bad_token_total": "provider_usage_inconsistent", "redirect": "provider_http_302", "http_error": "provider_http_500"}[failure]
    assert error.value.code == expected
    with engine.ledger.connection() as db:
        assert db.execute("SELECT error_code FROM model_calls").fetchone()[0] == expected
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


@pytest.mark.parametrize("returned_model", ["openai/gpt-4.1", None, KEY])
def test_wrong_model_is_charged_and_terminal_with_safe_model_metadata(tmp_path, config, returned_model):
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=response(model=returned_model)))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "model_output_invalid"
    summary = engine.budget()
    assert summary["reported_spend_usd"] == "0.0001" and summary["held_usd"] == "0" and summary["uncertain_calls"] == 0
    with engine.ledger.connection() as db:
        row = db.execute("SELECT status,result,usage FROM model_calls").fetchone()
    usage = json.loads(row["usage"])
    assert row["status"] == "invalid_output" and row["result"] is None
    assert usage["requested_model"] == "openai/gpt-4.1-mini"
    assert usage["returned_model"] == ("openai/gpt-4.1" if returned_model == "openai/gpt-4.1" else "unapproved")
    assert KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    with pytest.raises(ProviderError) as repeat:
        engine.complete(**arguments())
    assert repeat.value.code == "call_not_retriable" and len(calls) == 1


@pytest.mark.parametrize("prompt,completion", [(32769, 0), (10, 257)])
def test_prompt_and_completion_tokens_obey_separate_limits(tmp_path, config, prompt, completion):
    usage = {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion, "cost": .0001}
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(200, json=response(usage=usage)))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "model_output_invalid"
    assert engine.budget()["reported_spend_usd"] == "0.0001" and engine.budget()["held_usd"] == "0"
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


@pytest.mark.parametrize("status,expected", [(400, "provider_http_400"), (401, "provider_http_401"), (402, "provider_http_402"),
                                           (403, "provider_http_403"), (404, "provider_http_404"), (422, "provider_http_422"),
                                           (429, "provider_http_429"), (502, "provider_http_502"), (503, "provider_http_503"),
                                           (399, "provider_http_3xx"), (499, "provider_http_4xx"), (599, "provider_http_5xx"),
                                           (201, "provider_http_unexpected_status")])
def test_http_diagnostics_retain_only_allowed_status_codes(tmp_path, config, status, expected):
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(status, headers={"X-Private-Detail": KEY}, json={"error": {"message": KEY}}))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == expected and expected in SAFE_ERROR_CODES and KEY not in str(error.value)
    with engine.ledger.connection() as db:
        row = db.execute("SELECT status,error_code,result,reserved_usd,charged_usd FROM model_calls").fetchone()
    assert row["status"] == "uncertain" and row["error_code"] == expected and row["result"] is None
    assert row["charged_usd"] is None and Decimal(row["reserved_usd"]) > 0
    assert KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    with pytest.raises(ProviderError):
        engine.complete(**arguments())
    assert len(calls) == 1


@pytest.mark.parametrize("kind,expected", [(httpx.ConnectTimeout, "provider_connect_timeout"), (httpx.ReadTimeout, "provider_read_timeout"),
                                         (httpx.WriteTimeout, "provider_write_timeout"), (httpx.PoolTimeout, "provider_pool_timeout"),
                                         (httpx.ConnectError, "provider_connect_error"), (httpx.ReadError, "provider_network_error"),
                                         (httpx.RemoteProtocolError, "provider_protocol_error")])
def test_network_diagnostics_never_retain_exception_details(tmp_path, config, kind, expected):
    def fail(request):
        raise kind(KEY, request=request)
    engine, calls = gateway(tmp_path, config, fail)
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == expected and KEY not in str(error.value)
    assert error.value.__context__ is None and error.value.__cause__ is None
    with engine.ledger.connection() as db:
        row = db.execute("SELECT error_code FROM model_calls").fetchone()
    assert row[0] == expected and KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    assert len(calls) == 1 and Decimal(engine.budget()["held_usd"]) > 0


@pytest.mark.parametrize("failure,expected", [("bad_json", "provider_response_json_invalid"), ("shape", "provider_response_shape_invalid"),
                                             ("error_envelope", "provider_error_envelope"), ("usage_shape", "provider_usage_invalid"),
                                             ("tokens_missing", "provider_usage_tokens_missing"), ("tokens_invalid", "provider_usage_tokens_invalid"),
                                             ("cost_missing", "provider_usage_cost_missing"), ("cost_invalid", "provider_usage_cost_invalid"),
                                             ("cost_null", "provider_usage_cost_invalid"), ("cost_nan", "provider_usage_cost_invalid")])
def test_json_usage_diagnostics_are_specific_safe_and_conservative(tmp_path, config, failure, expected):
    def malformed(request):
        if failure == "bad_json":
            return httpx.Response(200, content=KEY)
        if failure == "shape":
            return httpx.Response(200, json=[KEY])
        if failure == "error_envelope":
            return httpx.Response(200, json={"error": {"message": KEY, "code": KEY}})
        data = response()
        if failure == "usage_shape":
            data["usage"] = KEY
        elif failure == "tokens_missing":
            del data["usage"]["completion_tokens"]
        elif failure == "tokens_invalid":
            data["usage"]["completion_tokens"] = True
        elif failure == "cost_missing":
            del data["usage"]["cost"]
        else:
            data["usage"]["cost"] = {"cost_invalid": KEY, "cost_null": None, "cost_nan": "NaN"}[failure]
        return httpx.Response(200, json=data)
    engine, calls = gateway(tmp_path, config, malformed)
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == expected and KEY not in str(error.value)
    assert error.value.__context__ is None and error.value.__cause__ is None
    with engine.ledger.connection() as db:
        row = db.execute("SELECT error_code,status,charged_usd FROM model_calls").fetchone()
    assert tuple(row) == (expected, "uncertain", None)
    assert KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    assert Decimal(engine.budget()["held_usd"]) > 0 and len(calls) == 1


@pytest.mark.parametrize("code", [KEY, "invented-private-response-value", "provider_http_499", None, ["provider_http_400"]])
def test_unrecognized_error_codes_never_cross_gateway_client_boundary(code):
    assert safe_error_code(code) == "gateway_request_failed"
    transport = httpx.MockTransport(lambda _: httpx.Response(502, json={"error": {"code": code, "message": KEY}}))
    with pytest.raises(ProviderError) as error:
        ModelGatewayClient(TOKEN, transport=transport).complete(**arguments())
    assert error.value.code == "gateway_request_failed" and KEY not in str(error.value)


@pytest.mark.parametrize("message,error_type,expected", [
    ("Your privacy settings prevent access.", None, "provider_http_403_privacy_policy_hint"),
    ("This model is not available in your country.", None, "provider_http_403_region_hint"),
    ("Your account is suspended.", None, "provider_http_403_account_access_hint"),
    ("This model is not authorized for this key.", None, "provider_http_403_model_access_hint"),
    ("The request was flagged by moderation.", None, "provider_http_403_content_policy_hint"),
    ("Forbidden.", "unsupported_region", "provider_http_403_region_hint"),
    ("Forbidden.", "DATA_POLICY_VIOLATION", "provider_http_403_privacy_policy_hint"),
    ("Forbidden.", "invented-private-response-value", "provider_http_403"),
    ("The region field was supplied.", None, "provider_http_403"),
    ("Your account is suspended and your country is blocked.", None, "provider_http_403"),
    ("Forbidden. Contact support.", None, "provider_http_403"),
])
def test_forbidden_hints_are_fixed_provider_reported_categories_without_key_echo(tmp_path, config, message, error_type, expected):
    body = {"error": {"message": message + " " + KEY, "type": error_type, "metadata": {"raw": KEY}}}
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(403, headers={"X-Private": KEY}, json=body))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == expected and expected in SAFE_ERROR_CODES
    assert KEY not in str(error.value) and error.value.__context__ is None and error.value.__cause__ is None
    with engine.ledger.connection() as db:
        row = db.execute("SELECT error_code,status,result,charged_usd FROM model_calls").fetchone()
    assert tuple(row) == (expected, "uncertain", None, None)
    assert KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    assert Decimal(engine.budget()["held_usd"]) > 0
    with pytest.raises(ProviderError) as again:
        engine.complete(**arguments())
    assert again.value.code == "call_not_retriable" and len(calls) == 1


@pytest.mark.parametrize("body", [
    KEY.encode(), b"{invalid-json", b"<html>Forbidden</html>", b"\xff\xfe", b"[]", b'{"error":"unreadable"}',
    json.dumps({"error": {"message": "Your privacy settings prevent access.", "padding": "x" * FORBIDDEN_BODY_LIMIT}}).encode(),
])
def test_unreadable_and_oversized_forbidden_bodies_stay_generic(tmp_path, config, body):
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(403, content=body))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "provider_http_403" and KEY not in str(error.value)
    assert error.value.__context__ is None and error.value.__cause__ is None
    assert engine.budget()["uncertain_calls"] == 1 and Decimal(engine.budget()["held_usd"]) > 0 and len(calls) == 1


def test_forbidden_body_read_failure_keeps_known_http_status_without_details(tmp_path, config):
    class BrokenBody(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"error":{"message":"Your privacy settings prevent access.'
            raise httpx.ReadError(KEY)
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(403, stream=BrokenBody()))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "provider_http_403" and KEY not in str(error.value)
    assert error.value.__cause__ is None and error.value.__context__ is None
    with engine.ledger.connection() as db:
        assert db.execute("SELECT error_code FROM model_calls").fetchone()[0] == "provider_http_403"
    assert len(calls) == 1 and Decimal(engine.budget()["held_usd"]) > 0


def test_forbidden_hint_read_is_bounded_to_the_decoded_limit(tmp_path, config):
    reads = []
    class LargeBody(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(100):
                chunk = b"x" * 4096
                reads.append(len(chunk))
                yield chunk
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(403, stream=LargeBody()))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == "provider_http_403"
    assert sum(reads) == FORBIDDEN_BODY_LIMIT and len(reads) == 4
    assert len(calls) == 1 and Decimal(engine.budget()["held_usd"]) > 0


@pytest.mark.parametrize("outer_type,raw,expected", [
    (None, json.dumps({"error": {"code": "unsupported_country_region_territory", "message": "Country, region, or territory not supported. " + KEY}}), "provider_http_403_region_hint"),
    (None, {"error": {"code": "unsupported_country_region_territory", "message": KEY}}, "provider_http_403_region_hint"),
    (None, {"code": "unsupported_region", "message": KEY}, "provider_http_403_region_hint"),
    (None, KEY, "provider_http_403"),
    (None, {"error": {"code": KEY, "message": "Forbidden. " + KEY}}, "provider_http_403"),
    ("data_policy_violation", {"error": {"code": "unsupported_country_region_territory", "message": KEY}}, "provider_http_403"),
    ("unsupported_region", json.dumps({"error": {"code": "account_disabled", "message": KEY}}), "provider_http_403"),
    (None, json.dumps(json.dumps({"error": {"code": "unsupported_country_region_territory"}})), "provider_http_403"),
    (None, {"error": {"metadata": {"raw": json.dumps({"error": {"code": "unsupported_country_region_territory"}})}}}, "provider_http_403"),
    (None, {"error": {"type": "unsupported_country_region_territory", "message": "Your account is disabled. " + KEY}}, "provider_http_403"),
    (None, [KEY], "provider_http_403"),
    (None, {"error": KEY}, "provider_http_403"),
])
def test_single_level_nested_provider_error_hints_are_bounded_safe_and_unambiguous(tmp_path, config, outer_type, raw, expected):
    body = {"error": {"message": "Provider returned error. " + KEY, "type": outer_type, "metadata": {"raw": raw}}}
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(403, json=body))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == expected and expected in SAFE_ERROR_CODES and KEY not in str(error.value)
    assert error.value.__context__ is None and error.value.__cause__ is None
    with engine.ledger.connection() as db:
        row = db.execute("SELECT error_code,status,result,charged_usd FROM model_calls").fetchone()
    assert tuple(row) == (expected, "uncertain", None, None)
    assert KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    assert Decimal(engine.budget()["held_usd"]) > 0 and len(calls) == 1
    with pytest.raises(ProviderError) as repeated:
        engine.complete(**arguments())
    assert repeated.value.code == "call_not_retriable" and len(calls) == 1


@pytest.mark.parametrize("metadata,expected", [
    ({"provider_code": "unsupported_country_region_territory"}, "provider_http_403_region_hint"),
    ({"error_type": "content_policy_violation"}, "provider_http_403_content_policy_hint"),
    ({"provider_code": KEY, "error_type": KEY}, "provider_http_403"),
    ({"provider_code": "model_not_allowed", "raw": {"error": {"code": "unsupported_region"}}}, "provider_http_403"),
])
def test_router_metadata_codes_are_allowlisted_and_do_not_override_conflicting_hints(tmp_path, config, metadata, expected):
    body = {"error": {"message": "Provider returned error.", "metadata": metadata}}
    engine, calls = gateway(tmp_path, config, lambda _: httpx.Response(403, json=body))
    with pytest.raises(ProviderError) as error:
        engine.complete(**arguments())
    assert error.value.code == expected and len(calls) == 1
    assert KEY not in str(error.value) and KEY.encode() not in (tmp_path / "ledger.sqlite").read_bytes()
    assert Decimal(engine.budget()["held_usd"]) > 0
