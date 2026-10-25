"""Program-profile count policy; fictional accounting and mocked HTTP only."""
from copy import deepcopy
from decimal import Decimal
import json

import httpx
import pytest

from desk.model_profiles import MODEL_PROFILES, UNLIMITED_CALL_PROFILE, model_profile
from desk.provider import BudgetLedger, ProviderError, ReasoningGateway, validate_config
from ops import prepare_live as prep
from test_program_model_profile import configuration, PRIMARY, SCHEMA


def unlimited_config(**edits):
    return {**configuration(), "max_calls_per_run": None, **edits}


@pytest.mark.parametrize("version", list(MODEL_PROFILES))
def test_null_call_limit_is_exclusive_to_program_profile(version):
    config = {**unlimited_config(), "version": version, "models": model_profile(version)["models"]}
    if version == UNLIMITED_CALL_PROFILE:
        assert validate_config(config)["max_calls_per_run"] is None
    else:
        with pytest.raises(ProviderError) as error:
            validate_config(config)
        assert error.value.code == "invalid_configuration"


@pytest.mark.parametrize("invalid", [0, -1, False, "unlimited", "null"])
def test_no_call_limit_uses_explicit_null_not_an_ambiguous_sentinel(invalid):
    with pytest.raises(ProviderError) as error:
        validate_config(unlimited_config(max_calls_per_run=invalid))
    assert error.value.code == "invalid_configuration"


def test_more_than_twenty_mocked_completions_remain_counted_and_idempotent(tmp_path):
    requests = []
    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"model": PRIMARY, "id": "gen-synthetic-unlimited",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": "0.00001"},
            "choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"Synthetic result."}'}}]})
    path = tmp_path / "ledger.sqlite"
    config = unlimited_config()
    gateway = ReasoningGateway(config, path, "synthetic-provider-credential-" * 3, httpx.MockTransport(respond))
    request = {"run_id": "synthetic-run", "role": "writer", "messages": [{"role": "user", "content": "Synthetic source."}],
               "response_schema": SCHEMA, "max_output_tokens": 256}
    for index in range(25):
        gateway.complete(**request, call_id=f"synthetic-{index}")
    summary = gateway.budget("synthetic-run")
    assert len(requests) == summary["model_calls"] == 25
    assert summary["max_calls_per_run"] is None and summary["original_max_calls_per_run"] is None
    assert summary["tokens"] == 375 and summary["reported_spend_usd"] == "0.00025"
    assert summary["uncertain_calls"] == 0 and summary["held_usd"] == "0"
    assert summary["max_tokens_per_run"] == 250000 and Decimal(summary["per_run_usd"]) == Decimal(".50")
    assert requests[0]["models"] == ["openai/gpt-4.1-mini", "openai/gpt-4.1-nano"]
    assert requests[0]["provider"]["only"] == ["openai", "azure"]
    restarted = ReasoningGateway(config, path, "synthetic-provider-credential-" * 3,
        httpx.MockTransport(lambda _: pytest.fail("Cached calls must not contact the provider")))
    assert restarted.complete(**request, call_id="synthetic-0")["cached"] is True
    assert restarted.budget("synthetic-run")["model_calls"] == 25


def test_explicit_program_policy_removes_old_count_ceiling_without_rewriting_history(tmp_path):
    path = tmp_path / "ledger.sqlite"
    previous = configuration()
    ledger = BudgetLedger(path, previous)
    for index in range(12):
        ledger.reserve("same-run", f"old-{index}", f"hash-{index}", Decimal(".001"), 100)
        if index == 11:
            ledger.uncertain(f"old-{index}", "provider_http_429")
        else:
            ledger.settle(f"old-{index}", {"cost_usd": ".0001", "total_tokens": 10}, {"synthetic": True})
    with ledger.connection() as db:
        old_rows = [dict(row) for row in db.execute("SELECT * FROM model_calls ORDER BY call_id")]
        old_limits = tuple(db.execute("SELECT cap_usd,max_calls,max_tokens FROM run_limits").fetchone())
    with pytest.raises(ProviderError) as limited:
        ledger.reserve("same-run", "thirteenth", "new-hash", Decimal(".001"), 100)
    assert limited.value.code == "run_limit_exhausted"
    changed = unlimited_config(authorization_id="synthetic-new-count-policy")
    active = BudgetLedger(path, changed)
    active.reserve("same-run", "thirteenth", "new-hash", Decimal(".001"), 100)
    summary = active.summary("same-run")
    assert summary["model_calls"] == 13 and summary["uncertain_calls"] == 1
    assert summary["held_usd"] == "0.002" and summary["reported_spend_usd"] == "0.0011"
    assert summary["original_max_calls_per_run"] == 12
    with active.connection() as db:
        assert [dict(row) for row in db.execute("SELECT * FROM model_calls WHERE call_id LIKE 'old-%' ORDER BY call_id")] == old_rows
        assert tuple(db.execute("SELECT cap_usd,max_calls,max_tokens FROM run_limits").fetchone()) == old_limits
    with pytest.raises(ProviderError) as same_attempt:
        active.reserve("same-run", "old-11", "hash-11", Decimal(".001"), 100)
    assert same_attempt.value.code == "call_id_conflict"  # Prior policy remains authoritative for its own row.


@pytest.mark.parametrize("boundary", ["tokens", "per_run_spend", "desk_spend"])
def test_no_count_ceiling_does_not_relax_token_or_monetary_limits(tmp_path, boundary):
    ledger = BudgetLedger(tmp_path / "ledger.sqlite", unlimited_config())
    if boundary == "tokens":
        ledger.reserve("same-run", "existing", "old", Decimal(".001"), 249999)
        attempt = ("same-run", "next", "new", Decimal(".001"), 2)
        expected = "run_limit_exhausted"
    elif boundary == "per_run_spend":
        ledger.reserve("same-run", "existing", "old", Decimal(".49"), 1)
        attempt = ("same-run", "next", "new", Decimal(".02"), 1)
        expected = "budget_exhausted"
    else:
        ledger.reserve("other-one", "existing-one", "old-one", Decimal(".4"), 1)
        ledger.reserve("other-two", "existing-two", "old-two", Decimal(".4"), 1)
        attempt = ("other-three", "next", "new", Decimal(".21"), 1)
        expected = "budget_exhausted"
    before = deepcopy(ledger.summary())
    with pytest.raises(ProviderError) as blocked:
        ledger.reserve(*attempt)
    assert blocked.value.code == expected
    assert ledger.summary() == before


def test_unlimited_calls_preserve_uncertain_attempts_and_never_retry_same_request(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.sqlite", unlimited_config())
    ledger.reserve("same-run", "held", "held-hash", Decimal(".01"), 100)
    ledger.uncertain("held", "provider_http_429")
    before = deepcopy(ledger.summary("same-run"))
    with pytest.raises(ProviderError) as error:
        ledger.reserve("same-run", "held", "held-hash", Decimal(".01"), 100)
    assert error.value.code == "call_not_retriable" and ledger.summary("same-run") == before
    ledger.reserve("same-run", "new-explicit-request", "new-hash", Decimal(".01"), 100)
    after = ledger.summary("same-run")
    assert after["model_calls"] == 2 and after["uncertain_calls"] == 1
    assert after["held_usd"] == "0.02" and after["tokens"] == 200


def test_existing_authorization_cannot_silently_change_its_call_policy(tmp_path):
    path = tmp_path / "ledger.sqlite"
    BudgetLedger(path, configuration())
    with pytest.raises(ProviderError) as error:
        BudgetLedger(path, unlimited_config())
    assert error.value.code == "authorization_changed"


def test_legacy_policy_restores_a_count_ceiling_after_unlimited_run(tmp_path):
    path = tmp_path / "ledger.sqlite"
    unlimited = BudgetLedger(path, unlimited_config())
    unlimited.reserve("same-run", "first", "first-hash", Decimal(".001"), 10)
    legacy = model_profile("live-step16-fallbacks-v1")
    config = {**configuration(), "authorization_id": "synthetic-restored-limit", "version": legacy["version"],
              "models": legacy["models"], "max_calls_per_run": 1}
    restored = BudgetLedger(path, config)
    with pytest.raises(ProviderError) as error:
        restored.reserve("same-run", "second", "second-hash", Decimal(".001"), 10)
    assert error.value.code == "run_limit_exhausted" and restored.summary("same-run")["model_calls"] == 1


@pytest.mark.parametrize("version", list(MODEL_PROFILES))
def test_host_proposal_allows_null_only_for_program_profile(version):
    config = {**unlimited_config(authorization_id="a" * 32), "version": version,
              "models": model_profile(version)["models"]}
    if version == UNLIMITED_CALL_PROFILE:
        assert prep.validate_config(config)["max_calls_per_run"] is None
    else:
        with pytest.raises(ValueError, match="positive integers"):
            prep.validate_config(config)


def test_explicit_same_profile_count_policy_change_archives_authority_and_changes_only_count(tmp_path, monkeypatch):
    directory = tmp_path / "private"
    for name, value in {"PRIVATE": directory, "CONFIG_FILE": directory / "model_config.json",
                        "KEY_FILE": directory / "provider.key", "APPROVAL_FILE": directory / "authorization.json"}.items():
        monkeypatch.setattr(prep, name, value)
    source = tmp_path / "synthetic.env"
    source.write_text("OPENROUTER_API_KEY=" + "synthetic-provider-credential-" * 3 + "\n")
    prep.prepare(source)
    initial = {**configuration(), "enabled": False, "authorization_id": "a" * 32}
    prep.write_private(prep.CONFIG_FILE, json.dumps(initial), 0o444)
    before_hash = prep.proposal_hash(initial)
    prep.authorize(before_hash, "Synthetic old twelve-call decision")
    previous = prep.load_config()
    key_bytes = prep.KEY_FILE.read_bytes()
    approval_bytes = prep.APPROVAL_FILE.read_bytes()
    ledger = directory / "ledger-sentinel"
    ledger.write_bytes(b"all prior charges and holds remain unchanged")

    result = prep.switch_profile("program-office", before_hash)
    current = prep.load_config()
    assert current["version"] == previous["version"] == UNLIMITED_CALL_PROFILE
    assert current["max_calls_per_run"] is None and previous["max_calls_per_run"] == 12
    assert current["authorization_id"] != previous["authorization_id"]
    for key in set(previous) - {"max_calls_per_run", "enabled", "authorization_id"}:
        assert current[key] == previous[key]
    assert result["paid_calls_performed"] == 0 and result["ledger_changed"] is False
    assert not current["enabled"] and not prep.APPROVAL_FILE.exists()
    assert prep.KEY_FILE.read_bytes() == key_bytes
    assert ledger.read_bytes() == b"all prior charges and holds remain unchanged"
    archive = next((directory / "policy_history").iterdir())
    assert json.loads((archive / "model_config.json").read_text()) == previous
    assert (archive / "authorization.json").read_bytes() == approval_bytes
    assert result["proposal_hash"] != before_hash
    with pytest.raises(ValueError, match="stale"):
        prep.authorize(before_hash, "An old decision cannot enable the new policy")
    prep.authorize(result["proposal_hash"], "Synthetic explicit no-call-ceiling decision")
    assert prep.load_config()["enabled"]
    with pytest.raises(ValueError, match="already prepared"):
        prep.switch_profile("program-office", result["proposal_hash"])
    legacy = prep.switch_profile("fallbacks", result["proposal_hash"])
    assert legacy["config"]["max_calls_per_run"] == 12
    assert legacy["config"]["max_tokens_per_run"] == 250000
    assert legacy["config"]["cap_usd"] == "1.00" and legacy["config"]["per_run_usd"] == "0.50"
    assert not legacy["config"]["enabled"]
