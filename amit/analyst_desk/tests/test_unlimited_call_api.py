"""No-count-ceiling API boundaries with synthetic accounting; no model calls."""
import pytest

from test_live_api import FakeGateway, api_fixture, budget_snapshot


def program_budget(**edits):
    return {**budget_snapshot("live-program-models-v1"),
            "max_calls_per_run": None, "cap_usd": "1.00", "per_run_usd": "0.50",
            "remaining_authorization_usd": "0.86", **edits}


def test_program_configuration_exposes_null_ceiling_without_private_fields_or_completions(api_fixture):
    client, engine, store = api_fixture
    snapshot = program_budget(model_calls=37)
    engine.model_client = FakeGateway(snapshot)
    config = client.get("/api/config").json()
    budget = client.get("/api/budget").json()

    assert config["live_enabled"] and config["available_modes"] == ["offline", "live"]
    assert config["live_budget"]["max_calls_per_run"] is None
    assert budget["max_calls_per_run"] is None
    assert config["live_budget"]["model_calls"] == budget["model_calls"] == 37
    assert config["models"] == snapshot["models"] and config["model_routes"] == snapshot["model_routes"]
    assert budget["cap_usd"] == "1.00" and budget["per_run_usd"] == "0.50"
    assert budget["reported_spend_usd"] == "0.04" and budget["held_usd"] == "0.10"
    assert budget["tokens"] == 200 and budget["uncertain_calls"] == 1
    assert "provider_api_key" not in budget and "untrusted_extra" not in budget
    assert "secret-must-never-be-returned" not in str(config) + str(budget)
    assert engine.model_client.reads == 2 and store.list_runs() == []


@pytest.mark.parametrize("profile", ["live-step6-openrouter-v1", "live-step10-mistral-v1",
    "live-step10-google-critic-v1", "live-step16-fallbacks-v1"])
def test_legacy_null_gateway_ceiling_fails_readiness_before_run_creation(api_fixture, profile):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway({**budget_snapshot(profile), "max_calls_per_run": None})
    config = client.get("/api/config").json()
    assert not config["live_enabled"] and config["available_modes"] == ["offline"]
    assert config["live_budget"] == {"gateway_status": "unavailable"}
    response = client.post("/api/runs", json={"mode": "live", "question": "Compare selected annual evidence."})
    assert response.status_code == 409 and store.list_runs() == []


@pytest.mark.parametrize("invalid", [0, -1, False, "unlimited", 13])
def test_ambiguous_or_unreviewed_gateway_count_policy_is_not_ready(api_fixture, invalid):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway(program_budget(max_calls_per_run=invalid))
    config = client.get("/api/config").json()
    assert not config["live_enabled"] and config["live_budget"] == {"gateway_status": "unavailable"}
    assert store.list_runs() == []


@pytest.mark.parametrize("profile", ["live-step6-openrouter-v1", "live-step16-fallbacks-v1"])
def test_legacy_request_cannot_remove_a_required_count_ceiling(api_fixture, profile):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway(budget_snapshot(profile))
    response = client.post("/api/runs", json={"mode": "live", "question": "Compare selected annual evidence.",
                                             "max_model_calls": None, "max_tokens": 250000})
    assert response.status_code == 400
    assert "requires a call-count limit" in response.text and store.list_runs() == []
    assert engine.model_client.reads == 1


@pytest.mark.parametrize("submitted_count", ["omitted", None, 12, 1])
def test_program_authority_stores_no_count_ceiling_even_for_an_old_form(api_fixture, submitted_count):
    client, engine, store = api_fixture
    snapshot = program_budget(model_calls=37)
    engine.model_client = FakeGateway(snapshot)
    body = {"mode": "live", "question": "Compare selected annual evidence.",
            "tickers": ["MSFT", "AAPL"], "years": [2024, 2025], "max_tokens": 250000}
    if submitted_count != "omitted":
        body["max_model_calls"] = submitted_count
    response = client.post("/api/runs", json=body)
    assert response.status_code == 202, response.text
    run = store.get_run(response.json()["id"])
    assert run["status"] == "awaiting_plan" and run["request"]["mode"] == "live"
    assert run["request"]["max_model_calls"] is None
    assert run["request"]["max_tokens"] == 250000
    assert run["request"]["tickers"] == body["tickers"] and run["request"]["years"] == body["years"]
    assert run["request"]["question"] == body["question"]
    assert engine.model_client.value == snapshot and engine.model_client.reads == 1


def test_missing_legacy_gateway_count_metadata_retains_its_twelve_call_default(api_fixture):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway(budget_snapshot())
    response = client.post("/api/runs", json={"mode": "live", "question": "Compare selected annual evidence.",
                                             "max_tokens": 250000})
    assert response.status_code == 202
    saved = store.get_run(response.json()["id"])
    assert saved["request"]["max_model_calls"] == 12
    assert client.get("/api/budget").json()["max_calls_per_run"] == 12
    assert engine.model_client.reads == 2


@pytest.mark.parametrize("actual_count", [13, 37, 1000])
def test_call_counts_above_old_limit_are_reported_without_clamping(api_fixture, actual_count):
    client, engine, store = api_fixture
    engine.model_client = FakeGateway(program_budget(model_calls=actual_count))
    report = client.get("/api/budget").json()
    assert report["model_calls"] == actual_count and report["max_calls_per_run"] is None
    run = store.create_run({"mode": "live", "max_model_calls": None, "max_tokens": 250000})
    run["usage"] = {"model_calls": actual_count, "tool_calls": 4, "tokens": 1234, "cost_usd": ".031"}
    store.save_run(run)
    saved = client.get("/api/runs/" + run["id"]).json()
    assert saved["usage"]["model_calls"] == actual_count
    assert saved["request"]["max_model_calls"] is None
    assert f"analyst_model_calls_total {actual_count}\n" in client.get("/metrics").text
