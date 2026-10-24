"""Catalogue breadth must not admit live requests beyond writer capacity."""
from copy import deepcopy

import pytest

from desk.workflow import ReviewError, validate_scope


class CoveredCompanies:
    def companies(self):
        return [{"ticker": ticker} for ticker in ("MSFT", "AAPL", "GOOGL", "ORCL", "ADBE", "CRM", "ABBV", "AMGN", "GILD", "ABT", "UNH", "TMO")]

    def years(self, ticker):
        return [2023, 2024, 2025]


@pytest.mark.parametrize("tickers,years,mode,accepted", [
    (["ABBV", "AMGN"], [2023, 2024, 2025], "live", True),
    (["MSFT", "GOOGL", "UNH"], [2023, 2024, 2025], "live", False),
    (["AAPL", "ORCL", "CRM", "GILD"], [2024, 2025], "live", True),
    (["MSFT", "AAPL", "GOOGL", "ORCL"], [2023, 2024, 2025], "offline", True),
    (["MSFT", "AAPL", "GOOGL", "ORCL", "ADBE"], [2025], "offline", False),
])
def test_request_scope_respects_mode_and_existing_bounds(tickers, years, mode, accepted):
    value = {"tickers": tickers, "years": years, "mode": mode}
    before = deepcopy(value)
    if accepted:
        validate_scope(value, CoveredCompanies())
    else:
        with pytest.raises(ReviewError):
            validate_scope(value, CoveredCompanies())
    assert value == before


from test_live_api import api_fixture, FakeGateway, budget_snapshot
from desk.api import app


def test_oversized_live_scope_is_rejected_before_gateway_or_run_creation(api_fixture, monkeypatch):
    client, engine, store = api_fixture
    monkeypatch.setattr(app.state, "source", CoveredCompanies())
    engine.model_client = FakeGateway(budget_snapshot())
    response = client.post("/api/runs", json={"question": "Compare the selected companies and annual risks.",
        "tickers": ["MSFT", "GOOGL", "UNH"], "years": [2023, 2024, 2025], "mode": "live"})
    assert response.status_code == 400
    assert engine.model_client.reads == 0
    assert store.list_runs() == []


def test_live_plan_edit_cannot_bypass_capacity_with_missing_payload_mode(api_fixture, monkeypatch):
    client, engine, store = api_fixture
    monkeypatch.setattr(app.state, "source", CoveredCompanies())
    run = store.create_run({"question": "Compare annual risks.", "tickers": ["MSFT", "AAPL"],
                            "years": [2023, 2024, 2025], "mode": "live"})
    run.update(status="awaiting_plan", pending={"kind": "plan", "payload": {
        "tickers": ["MSFT", "AAPL"], "years": [2023, 2024, 2025], "outline": ["Read evidence"]}})
    store.save_run(run)
    response = client.post(f"/api/runs/{run['id']}/decision", json={"kind": "plan", "action": "edit",
        "payload_hash": "a" * 64, "edits": {"tickers": ["MSFT", "GOOGL", "UNH"]}})
    assert response.status_code == 400
    assert store.get_run(run["id"])["status"] == "awaiting_plan"


from test_workflow import fixture, begin, decide


def test_snapshot_change_blocks_old_plan_approval_and_direct_resume(fixture):
    engine, store, source, calls, _, _ = fixture
    plan = begin(engine, store)
    original_fingerprint = source.fingerprint
    source.fingerprint = "b" * 64
    decision = {"kind": "plan", "action": "approve", "payload_hash": plan["pending"]["payload_hash"]}
    with pytest.raises(ReviewError, match="source snapshot changed"):
        engine.claim(plan["id"], decision)
    assert store.get_run(plan["id"])["status"] == "awaiting_plan"
    result = engine.execute(plan["id"], decision)
    assert result["failure_kind"] == "source_changed"
    assert result["source_fingerprint"] == original_fingerprint
    assert calls == [] and store.notes() == []


def test_snapshot_change_rechecked_after_approval_is_queued(fixture):
    engine, store, source, calls, _, _ = fixture
    plan = begin(engine, store)
    engine.claim(plan["id"], {"kind": "plan", "action": "approve", "payload_hash": plan["pending"]["payload_hash"]})
    source.fingerprint = "c" * 64
    result = engine.execute(plan["id"])
    assert result["failure_kind"] == "source_changed" and calls == []
    assert "queued_decision" not in store.get_run(plan["id"])


def test_old_plan_can_still_be_rejected_after_source_expansion(fixture):
    engine, store, source, calls, _, _ = fixture
    plan = begin(engine, store)
    original_fingerprint = source.fingerprint
    source.fingerprint = "d" * 64
    decision = {"kind": "plan", "action": "reject", "payload_hash": plan["pending"]["payload_hash"]}
    engine.claim(plan["id"], decision)
    result = engine.execute(plan["id"])
    assert result["status"] == "rejected" and calls == []
    assert result["source_fingerprint"] == original_fingerprint
