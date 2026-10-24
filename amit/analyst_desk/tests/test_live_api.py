"""Live API policy and reporting tests; no paid models or real gateway calls."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from desk.api import app
from desk.store import Store
from desk.model_profiles import model_profile


def budget_snapshot(profile_name="live-step6-openrouter-v1"):
    profile = model_profile(profile_name)
    return {"enabled": True, "blocked": False, "provider_key_configured": True,
            "cap_usd": "2.00", "per_run_usd": "1.00", "reported_spend_usd": "0.04",
            "held_usd": "0.10", "committed_usd": "0.14", "authorization_committed_usd": "0.14",
            "remaining_authorization_usd": "1.86", "model_calls": 2, "tokens": 200,
            "uncertain_calls": 1, "config_version": "synthetic-live-policy-v1",
            "models": {role: policy["id"] for role, policy in profile["models"].items()},
            "model_profile": profile["version"], "provider": profile["provider"],
            "provider_api_key": "secret-must-never-be-returned", "untrusted_extra": "not-public"}


class FakeGateway:
    def __init__(self, value):
        self.value, self.reads = value, 0

    def budget(self):
        self.reads += 1
        if isinstance(self.value, Exception):
            raise self.value
        return deepcopy(self.value)

    def complete(self, **kwargs):
        raise AssertionError("API budget/configuration checks must not make model calls")


@pytest.fixture
def api_fixture(tmp_path, monkeypatch):
    store = Store(tmp_path / "api.sqlite", secret="synthetic-local-signing-key-" * 3)
    class Source:
        fingerprint = "synthetic-source"
        def companies(self):
            return [{"ticker": "MSFT"}, {"ticker": "AAPL"}]
        def years(self, ticker):
            return [2023, 2024, 2025]
    class Engine:
        model_client = None
        def view(self, identifier):
            return store.get_run(identifier)
        def execute(self, identifier):
            run = store.get_run(identifier)
            run.update(status="awaiting_plan", mode=run["request"]["mode"])
            store.save_run(run)
    engine = Engine()
    monkeypatch.setattr(app.router, "lifespan_context", FastAPI().router.lifespan_context)
    monkeypatch.setattr(app.state, "source", Source(), raising=False)
    monkeypatch.setattr(app.state, "store", store, raising=False)
    monkeypatch.setattr(app.state, "engine", engine, raising=False)
    monkeypatch.setenv("ANALYST_API_TOKEN", "synthetic-analyst-token")
    with TestClient(app, headers={"X-Analyst-Token": "synthetic-analyst-token"}) as client:
        yield client, engine, store


def test_unconfigured_api_remains_explicitly_offline_and_blocks_live(api_fixture):
    client, engine, store = api_fixture
    config = client.get("/api/config").json()
    assert config["mode"] == "offline" and config["available_modes"] == ["offline"] and not config["live_enabled"]
    assert config["models"] == {} and config["model_profile"] is None
    assert client.get("/api/budget").json() == {"cap_usd": 0, "spent_usd": 0, "model_calls": 0,
                                              "mode": "offline", "provider_key_configured": False}
    response = client.post("/api/runs", json={"question": "Compare source-backed annual margins", "mode": "live"})
    assert response.status_code == 409 and store.list_runs() == []
    response = client.post("/api/runs", json={"question": "Compare source-backed annual margins"})
    assert response.status_code == 202
    assert store.get_run(response.json()["id"])["request"]["mode"] == "offline"


@pytest.mark.parametrize("profile_name", ["live-step6-openrouter-v1", "live-step10-mistral-v1"])
def test_budget_and_configuration_are_safe_reads_and_live_request_stays_live(api_fixture, profile_name):
    client, engine, store = api_fixture
    snapshot = budget_snapshot(profile_name)
    engine.model_client = FakeGateway(snapshot)
    config = client.get("/api/config").json()
    result = client.get("/api/budget").json()
    assert config["live_enabled"] and config["available_modes"] == ["offline", "live"]
    assert config["models"] == snapshot["models"]
    assert config["model_profile"] == result["model_profile"] == snapshot["model_profile"]
    assert config["model_provider"] == result["provider"] == snapshot["provider"]
    assert result["spent_usd"] == .04 and result["held_usd"] == "0.10"
    assert "secret-must-never-be-returned" not in str(config) + str(result)
    assert "provider_api_key" not in result and "untrusted_extra" not in result
    response = client.post("/api/runs", json={"question": "Compare source-backed annual margins", "mode": "live", "max_tokens": 250000, "max_model_calls": 12})
    assert response.status_code == 202
    saved = store.get_run(response.json()["id"])
    assert saved["mode"] == "live" and saved["request"]["max_tokens"] == 250000
    assert engine.model_client.reads == 3


@pytest.mark.parametrize("changes", [{"enabled": False}, {"blocked": True}, {"provider_key_configured": False},
                                     {"remaining_authorization_usd": "0"}, {"remaining_authorization_usd": "NaN"},
                                     {"enabled": "true"}])
def test_disabled_unfunded_or_invalid_gateway_blocks_before_run_creation(api_fixture, changes):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway({**budget_snapshot(), **changes})
    response = client.post("/api/runs", json={"question": "Compare source-backed annual margins", "mode": "live"})
    assert response.status_code == 409 and store.list_runs() == []
    assert client.get("/api/config").json()["live_enabled"] is False


def test_gateway_outage_is_explicit_and_does_not_report_zero_unknown_spend(api_fixture):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway(RuntimeError("secret-in-private-error"))
    response = client.post("/api/runs", json={"question": "Compare source-backed annual margins", "mode": "live"})
    result = client.get("/api/budget").json()
    assert response.status_code == 409 and store.list_runs() == []
    assert result["gateway_status"] == "unavailable" and result["spent_usd"] is None
    assert "secret-in-private-error" not in str(result) + response.text


@pytest.mark.parametrize("changes", [
    {"models": {"producer": "unreviewed-model-private-value", "critic": "openai/gpt-4.1"}},
    {"models": {"producer": "mistralai/mistral-medium-3.1", "critic": "openai/gpt-4.1"}},
    {"model_profile": "unreviewed-model-private-value"},
    {"model_profile": "live-step10-mistral-v1"},
    {"provider": "unreviewed-model-private-value"},
    {"provider": "mistral/zdr"}, {"models": None}, {"model_profile": None},
    {"config_version": ""},
])
def test_untrusted_model_metadata_fails_closed_without_disclosing_values(api_fixture, changes):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway({**budget_snapshot(), **changes})
    config = client.get("/api/config").json()
    result = client.get("/api/budget").json()
    assert config["available_modes"] == ["offline"] and config["models"] == {}
    assert config["live_enabled"] is False and result["gateway_status"] == "unavailable"
    response = client.post("/api/runs", json={"question": "Compare source-backed annual margins", "mode": "live"})
    assert response.status_code == 409 and store.list_runs() == []
    assert "unreviewed-model-private-value" not in str(config) + str(result) + response.text


@pytest.mark.parametrize("profile_name", ["live-step6-openrouter-v1", "live-step10-mistral-v1"])
def test_runtime_evidence_budget_uses_actual_allowlisted_profile_metadata(profile_name):
    from ops.verify_live_runtime import safe_budget
    snapshot = budget_snapshot(profile_name)
    safe = safe_budget(snapshot)
    assert safe["models"] == snapshot["models"]
    assert safe["model_profile"] == snapshot["model_profile"]
    assert safe["provider"] == snapshot["provider"]
    assert "provider_api_key" not in safe
    snapshot["provider"] = "arbitrary-route"
    with pytest.raises(ValueError, match="inconsistent"):
        safe_budget(snapshot)


@pytest.mark.parametrize("changes", [{"mode": "automatic"}, {"max_model_calls": 13}, {"max_model_calls": 0}, {"max_tokens": 500001}, {"model": "arbitrary-model"}])
def test_unreviewed_run_modes_models_or_limits_are_rejected(api_fixture, changes):
    client, engine, store = api_fixture
    response = client.post("/api/runs", json={"question": "Compare source-backed annual margins", **changes})
    assert response.status_code == 422 and store.list_runs() == []


def test_model_metrics_use_actual_accounting_and_unknown_cost_is_nan(api_fixture):
    client, engine, store = api_fixture
    run = store.create_run({"mode": "live"})
    run["usage"] = {"model_calls": 3, "tool_calls": 4, "tokens": 1234, "cost_usd": "0.031"}
    store.save_run(run)
    text = client.get("/metrics").text
    assert "analyst_model_calls_total 3\n" in text
    assert "analyst_model_tokens_total 1234\n" in text
    assert "analyst_model_spend_usd_total 0.031\n" in text
    run["usage"]["cost_usd"] = None
    store.save_run(run)
    assert "analyst_model_spend_usd_total NaN\n" in client.get("/metrics").text
