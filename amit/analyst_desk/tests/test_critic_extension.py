"""Exact operator grants with fictional accounting and mocked provider only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
import json
import sqlite3

import httpx
import pytest

from desk.model_profiles import model_profile
from desk.provider import BudgetLedger, ProviderError, ReasoningGateway
from desk.store import canonical_hash
from ops import critic_extension as extension
from ops import prepare_live as prep


@pytest.fixture
def context(tmp_path):
    old_profile = model_profile("live-step10-mistral-v1")
    original = {**deepcopy(prep.DEFAULTS), "enabled": True, "authorization_id": "a" * 32,
                "version": old_profile["version"], "models": old_profile["models"], "max_output_tokens": 2000}
    path = tmp_path / "ledger.sqlite"
    old = BudgetLedger(path, original)
    for index, total in enumerate([6000] * 8 + [12185]):
        old.reserve("same-run", f"settled-{index}", f"hash-{index}", Decimal(".04"), 67536)
        old.settle(f"settled-{index}", {"cost_usd": ".001", "total_tokens": total}, {"synthetic": True})
    for index in range(2):
        old.reserve("same-run", f"old-hold-{index}", f"hold-hash-{index}", Decimal(".035768"), 67536)
        old.uncertain(f"old-hold-{index}", "provider_http_429")
    profile = model_profile("live-step10-mistral-large2407-v1")
    intermediate = {**original, "authorization_id": "b" * 32, "version": profile["version"], "models": profile["models"], **profile["limits"]}
    middle = BudgetLedger(path, intermediate)
    middle.reserve("same-run", "third-hold", "third-hash", Decimal(".110304"), 51152)
    middle.uncertain("third-hold", "provider_http_429")
    profile = model_profile(extension.PROFILE)
    config = {**intermediate, "authorization_id": "c" * 32, "version": profile["version"], "models": profile["models"]}
    gateway = ReasoningGateway(config, path, "invented-credential-for-mocked-calls")
    evidence = [{"id": "earlier", "ticker": "MSFT", "year": 2023, "text": "Cyber attacks may interrupt services and compromise customer trust."},
                {"id": "later", "ticker": "MSFT", "year": 2024, "text": "Cybersecurity threats may disrupt operations and customer trust."}]
    claim = {"claim_id": "risk-MSFT-2023-2024-1", "ticker": "MSFT", "before_year": 2023, "after_year": 2024,
             "category": "risk_observation", "confidence": "medium", "text": "Selected disclosures discuss cybersecurity exposure.",
             "citations": [{"source_id": "earlier", "quote": "Cyber attacks may interrupt services"},
                           {"source_id": "later", "quote": "Cybersecurity threats may disrupt operations"}]}
    draft = {"body": "Selected disclosures discuss cybersecurity exposure. Evidence selection is partial.",
             "narrative_claims": [claim], "ai_evidence": evidence, "metrics": [], "source_fingerprint": "synthetic"}
    run = {"id": "same-run", "status": "error", "error": "ReviewError: provider_http_429: Synthetic provider capacity error",
           "request": {"mode": "live", "max_model_calls": 12, "max_tokens": 250000},
           "draft": draft, "plan": {"tickers": ["MSFT", "AAPL"], "years": [2023, 2024, 2025]}}
    package = extension.build_proposal(run, gateway.budget("same-run"), config, "d" * 32)
    return {"gateway": gateway, "config": config, "path": path, "run": run, **package}


def register(context):
    return context["gateway"].ledger.grant_run_extension(context["proposal"], context["proposal_hash"], "Synthetic test approval only")


def reserve(context, **edits):
    grant = context["proposal"]
    arguments = {"run_id": grant["run_id"], "call_id": grant["call_id"], "request_hash": grant["request_hash"],
                 "usd": Decimal(grant["reservation_usd"]), "tokens": grant["reserved_tokens"], "role": "critic", **edits}
    return context["gateway"].ledger.reserve(**arguments)


def test_approved_exact_call_preserves_original_limits_and_all_three_holds(context):
    engine = context["gateway"]
    before = engine.budget("same-run")
    assert before["model_calls"] == 12 and before["tokens"] == 246409 and before["uncertain_calls"] == 3
    with pytest.raises(ProviderError) as blocked:
        reserve(context)
    assert blocked.value.code == "run_limit_exhausted"
    assert register(context)["approved"]
    grant = engine.budget("same-run")["run_budget_grant"]
    assert grant["approved"] and not grant["consumed"] and grant["request_hash"] == canonical_hash(context["request"])
    reserve(context)
    after = engine.budget("same-run")
    assert after["model_calls"] == 13 and after["tokens"] == 297561 and after["uncertain_calls"] == 3
    assert after["run_budget_grant"]["consumed"] and after["original_max_calls_per_run"] == 12
    assert after["original_max_tokens_per_run"] == 250000 and after["max_tokens_per_run"] == 250000
    assert Decimal(after["held_usd"]) == Decimal(before["held_usd"]) + Decimal(".0197456")
    with engine.ledger.connection() as db:
        limits = db.execute("SELECT max_calls,max_tokens FROM run_limits WHERE run_id='same-run'").fetchone()
        holds = db.execute("SELECT reserved_tokens,status FROM model_calls WHERE status='uncertain'").fetchall()
    assert tuple(limits) == (12, 250000)
    assert sorted(tuple(row) for row in holds) == [(51152, "uncertain"), (67536, "uncertain"), (67536, "uncertain")]
    with pytest.raises(ProviderError):
        reserve(context, call_id="fourteenth", request_hash="other", tokens=1, usd=Decimal(".000001"))


@pytest.mark.parametrize("mutation", ["role", "call_id", "request_hash", "tokens", "usd", "run_id"])
def test_grant_cannot_fund_any_other_role_payload_or_run(context, mutation):
    register(context)
    wrong = {"role": "writer", "call_id": "different-call", "request_hash": "0" * 64,
             "tokens": 51151, "usd": Decimal(".0197455"), "run_id": "different-run"}
    if mutation == "run_id":
        # An unrelated run has its ordinary original limits and no extension.
        ledger = context["gateway"].ledger
        for index in range(12):
            ledger.reserve("different-run", f"other-{index}", f"other-hash-{index}", Decimal(".001"), 1)
    with pytest.raises(ProviderError) as error:
        reserve(context, **{mutation: wrong[mutation]})
    assert error.value.code == "run_limit_exhausted"
    assert context["gateway"].budget("same-run")["run_budget_grant"]["consumed"] is False


def test_grant_consumption_is_atomic_and_survives_uncertainty_and_restart(context):
    register(context)
    def attempt(_):
        try:
            reserve(context)
            return "reserved"
        except ProviderError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == ["call_not_retriable", "reserved"]
    context["gateway"].ledger.uncertain(context["proposal"]["call_id"], "provider_http_429")
    restarted = ReasoningGateway(context["config"], context["path"])
    summary = restarted.budget("same-run")
    assert summary["tokens"] == 297561 and summary["uncertain_calls"] == 4 and summary["run_budget_grant"]["consumed"]
    with pytest.raises(ProviderError):
        reserve(context)


def test_google_critic_route_reasoning_and_cache_obey_grant(context):
    register(context)
    calls = []
    def reply(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert context["gateway"].budget("same-run")["tokens"] == 297561
        return httpx.Response(200, json={"model": "google/gemini-2.5-flash", "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"verdicts": [{"claim_id": "risk-MSFT-2023-2024-1", "supported": True, "reason": "Synthetic support verdict"}], "issues": []})}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120, "cost": .00008}})
    engine = ReasoningGateway(context["config"], context["path"], "invented-credential-for-mocked-calls", httpx.MockTransport(reply))
    request = {key: value for key, value in context["request"].items() if key not in {"model", "config_version"}}
    result = engine.complete(**request)
    assert not result["cached"] and calls[0]["reasoning"] == {"enabled": False}
    assert calls[0]["provider"]["only"] == ["google-ai-studio"] and calls[0]["provider"]["allow_fallbacks"] is False
    assert calls[0]["provider"]["max_price"] == {"prompt": .3, "completion": 2.5}
    assert engine.complete(**request)["cached"] and len(calls) == 1
    assert engine.budget("same-run")["providers"] == {"producer": "mistral/zdr", "critic": "google-ai-studio"}
    with pytest.raises(ProviderError):
        reserve(context, call_id="fourteenth", request_hash="other", tokens=1, usd=Decimal(".000001"))


def test_duplicate_or_changed_checkpoint_cannot_mint_another_grant(context):
    ledger = context["gateway"].ledger
    assert register(context)["changed"] and not register(context)["changed"]
    different = {**context["proposal"], "grant_id": "e" * 32}
    with pytest.raises(ProviderError) as error:
        ledger.grant_run_extension(different, canonical_hash(different), "Synthetic duplicate approval")
    assert error.value.code == "authorization_changed"
    with ledger.connection() as db:
        with pytest.raises(sqlite3.IntegrityError, match="append only"):
            db.execute("DELETE FROM run_budget_grants")


def test_grant_cannot_raise_desk_dollar_ceiling(context):
    register(context)
    ledger = context["gateway"].ledger
    ledger.reserve("other-run-one", "other-charge-one", "other-hash-one", Decimal(".4"), 1)
    ledger.reserve("other-run-two", "other-charge-two", "other-hash-two", Decimal(".4"), 1)
    with pytest.raises(ProviderError) as blocked:
        reserve(context)
    assert blocked.value.code == "budget_exhausted"
    assert context["gateway"].budget("same-run")["run_budget_grant"]["consumed"] is False


def test_grant_cannot_be_used_under_a_different_authorization(context):
    register(context)
    changed = ReasoningGateway({**context["config"], "authorization_id": "f" * 32}, context["path"])
    assert changed.budget("same-run")["policy_hash"] != context["proposal"]["policy_hash"]
    with pytest.raises(ProviderError) as blocked:
        reserve({**context, "gateway": changed})
    assert blocked.value.code == "run_limit_exhausted"
    assert context["gateway"].budget("same-run")["run_budget_grant"]["consumed"] is False


def test_full_old_row_checkpoint_changes_block_even_when_totals_are_identical(context):
    register(context)
    engine = context["gateway"]
    before = engine.budget("same-run")
    with engine.ledger.connection() as db:
        db.execute("UPDATE model_calls SET error_code='provider_http_500' WHERE call_id='old-hold-0'")
    after = engine.budget("same-run")
    assert all(after[key] == before[key] for key in ("model_calls", "tokens", "uncertain_calls", "held_usd", "reported_spend_usd"))
    assert after["ledger_checkpoint_hash"] != before["ledger_checkpoint_hash"]
    with pytest.raises(ProviderError) as blocked:
        reserve(context)
    assert blocked.value.code == "run_limit_exhausted" and after["run_budget_grant"]["consumed"] is False


def test_google_profile_producer_keeps_its_reviewed_route_without_reasoning_override(context):
    payloads = []
    def reply(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"model": "mistralai/mistral-medium-3.1", "choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"Synthetic"}'}}],
                                        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": .0001}})
    engine = ReasoningGateway(context["config"], context["path"], "invented-credential-for-mocked-calls", httpx.MockTransport(reply))
    engine.complete(run_id="ordinary-new-run", call_id="ordinary-producer", role="writer", messages=[{"role": "user", "content": "Synthetic"}],
                    response_schema={"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"], "additionalProperties": False}, max_output_tokens=100)
    assert payloads[0]["provider"]["only"] == ["mistral/zdr"] and "reasoning" not in payloads[0]
    assert payloads[0]["provider"]["max_price"] == {"prompt": .4, "completion": 2.0}
    assert engine.budget("ordinary-new-run")["run_budget_grant"] is None


@pytest.mark.parametrize("field", ["checkpoint_hash", "request_hash", "max_calls", "policy_hash", "checkpoint_tokens"])
def test_stale_or_wider_grant_proposals_are_rejected(context, field):
    changed = deepcopy(context["proposal"])
    changed[field] = changed[field] + 1 if isinstance(changed[field], int) else "0" * 64
    # A request hash alone can be approved, but the gateway will only spend its exact preimage.
    if field == "request_hash":
        context["gateway"].ledger.grant_run_extension(changed, canonical_hash(changed), "Synthetic exact different hash")
        with pytest.raises(ProviderError):
            reserve(context)
    else:
        with pytest.raises(ProviderError):
            context["gateway"].ledger.grant_run_extension(changed, canonical_hash(changed), "Synthetic changed proposal")


def test_host_preparation_and_authorization_are_separate_exact_hash_operations(context, tmp_path, monkeypatch):
    directory = tmp_path / "private"
    directory.mkdir(mode=0o700)
    monkeypatch.setattr(prep, "PRIVATE", directory)
    monkeypatch.setattr(extension, "PROPOSAL_FILE", directory / "proposal.json")
    monkeypatch.setattr(extension, "APPROVAL_FILE", directory / "approval.json")
    monkeypatch.setattr(prep, "load_config", lambda: deepcopy(context["config"]))
    class Client:
        def request(self, method, path):
            assert method == "GET" and path == "/api/runs/same-run"
            return deepcopy(context["run"])
    client = Client()
    reader = lambda _: context["gateway"].budget("same-run")
    prepared = extension.prepare("same-run", client=client, budget_reader=reader, grant_id="d" * 32)
    assert prepared["proposal_hash"] == context["proposal_hash"] and prepared["approved"] is False
    assert "request" not in prepared and not extension.APPROVAL_FILE.exists()
    assert extension.PROPOSAL_FILE.stat().st_mode & 0o777 == 0o600
    for expected_hash, confirmation in [("0" * 64, "Synthetic approval"), (prepared["proposal_hash"], " ")]:
        with pytest.raises(ValueError):
            extension.authorize(expected_hash, confirmation, client=client, budget_reader=reader)
    result = extension.authorize(prepared["proposal_hash"], "Synthetic explicit one-call approval", client=client,
                                 budget_reader=reader, registrar=context["gateway"].ledger.grant_run_extension)
    assert result["approved"] and result["paid_calls_performed"] == 0
    assert "Synthetic explicit" not in json.dumps(result)
    assert "Synthetic explicit" in extension.APPROVAL_FILE.read_text()
    assert context["gateway"].budget("same-run")["model_calls"] == 12


def stopped_after_invalid_thirteenth(context):
    register(context)
    reserve(context)
    usage = {"call_id": context["proposal"]["call_id"], "prompt_tokens": 6934,
             "completion_tokens": 903, "total_tokens": 7837, "cost_usd": "0.0043377",
             "model": "google/gemini-2.5-flash", "model_calls": 1}
    context["gateway"].ledger.settle(context["proposal"]["call_id"], usage, None, "model_output_invalid")
    run = deepcopy(context["run"])
    run["error"] = "ReviewError: model_output_invalid: Synthetic rejected formatting"
    return run


def test_amendment_is_exactly_one_more_critic_after_known_invalid_output(context):
    run = stopped_after_invalid_thirteenth(context)
    budget = context["gateway"].budget("same-run")
    package = extension.build_proposal(run, budget, context["config"], "e" * 32)
    grant = package["proposal"]
    assert grant["parent_grant_id"] == context["proposal"]["grant_id"]
    assert (grant["max_calls"], grant["max_tokens"], package["next_reserved_token_total"]) == (14, 350000, 305398)
    assert grant["call_id"] != context["proposal"]["call_id"]
    assert grant["request_hash"] == canonical_hash(package["request"])
    amended = {**context, **package}
    register(amended)
    reserve(amended)
    after = context["gateway"].budget("same-run")
    assert after["model_calls"] == 14 and after["tokens"] == 305398 and after["uncertain_calls"] == 3
    assert after["parent_run_budget_grant"]["grant_id"] == context["proposal"]["grant_id"]
    assert after["parent_run_budget_grant"]["consumed"] and after["run_budget_grant"]["consumed"]
    assert after["original_max_calls_per_run"] == 12 and after["original_max_tokens_per_run"] == 250000
    with pytest.raises(ProviderError):
        reserve(amended, call_id="fifteenth", request_hash="other", tokens=1, usd=Decimal(".000001"))


@pytest.mark.parametrize("change", ["parent", "settlement", "draft", "error", "tokens"])
def test_amendment_preparation_rejects_a_changed_parent_or_checkpoint(context, change):
    run = stopped_after_invalid_thirteenth(context)
    budget = context["gateway"].budget("same-run")
    if change == "parent":
        budget["run_budget_grant"]["consumed"] = False
    elif change == "settlement":
        budget["settled_calls"] = []
    elif change == "draft":
        run["draft"]["body"] += " Changed."
    elif change == "error":
        run["error"] = "ReviewError: provider_http_403: Synthetic refusal"
    else:
        budget["tokens"] += 1
    with pytest.raises(ValueError):
        extension.build_proposal(run, budget, context["config"], "e" * 32)


def test_host_amendment_archives_consumed_parent_and_is_idempotent(context, tmp_path, monkeypatch):
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    monkeypatch.setattr(prep, "PRIVATE", private)
    monkeypatch.setattr(extension, "PROPOSAL_FILE", private / "proposal.json")
    monkeypatch.setattr(extension, "APPROVAL_FILE", private / "approval.json")
    monkeypatch.setattr(prep, "load_config", lambda: deepcopy(context["config"]))
    prep.write_private(extension.PROPOSAL_FILE, json.dumps({key: context[key] for key in
                       ("proposal_hash", "proposal", "request", "paid_calls_performed", "approved", "next_reserved_token_total")}), 0o600)
    prep.write_private(extension.APPROVAL_FILE, "Synthetic parent approval", 0o600)
    run = stopped_after_invalid_thirteenth(context)
    class Client:
        def request(self, method, path):
            assert method == "GET"
            return deepcopy(run)
    reader = lambda _: context["gateway"].budget("same-run")
    first = extension.prepare("same-run", client=Client(), budget_reader=reader, grant_id="e" * 32)
    assert first["proposal"]["parent_grant_id"] == context["proposal"]["grant_id"]
    assert not extension.APPROVAL_FILE.exists()
    history = private / "critic_extension_history"
    assert len(list(history.iterdir())) == 2
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in history.iterdir())
    assert extension.prepare("same-run", client=Client(), budget_reader=reader) == first
