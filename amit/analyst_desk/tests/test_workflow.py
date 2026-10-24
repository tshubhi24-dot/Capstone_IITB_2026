"""Fresh deterministic workflow checks; synthetic fixtures and mocked MCP only."""
from decimal import Decimal, ROUND_HALF_UP
import json
import threading

import pytest

from desk.data import Corpus
from desk.store import Store
from desk.workflow import Engine, ReviewError


@pytest.fixture
def fixture(tmp_path):
    document = {"metadata": {"test_only": True}, "companies": [{"ticker": t, "company": t, "sector": "Test"} for t in ("MSFT", "AAPL")], "facts": [], "passages": []}
    for ticker in ("MSFT", "AAPL"):
        for year in (2023, 2024, 2025):
            for concept, value in (("revenue", 1000), ("operating_income", 200)):
                document["facts"].append({"id": f"test:{ticker}:{year}:{concept}", "ticker": ticker, "concept": concept, "fiscal_year": year,
                    "value": value, "unit": "USD", "start": f"{year}-01-01", "end": f"{year}-12-31", "accession": f"test-{ticker}-{year}"})
            for item in ("1A", "7"):
                document["passages"].append({"id": f"test:{ticker}:{year}:item{item}", "ticker": ticker, "year": year, "item": item, "text": f"Test-only source evidence {ticker} {year} Item {item}."})
    path = tmp_path / "source.json"
    path.write_text(json.dumps(document))
    source = Corpus(path)
    store = Store(tmp_path / "runtime", secret="test-signing-key-" * 4)
    calls = []
    def caller(role, server, tool, arguments):
        calls.append((role, tool, arguments))
        if tool == "get_facts":
            return source.facts(arguments["ticker"], arguments["years"])
        if tool == "search_filings":
            return source.search(arguments["query"], arguments["ticker"], arguments["years"], arguments["k"])
        if tool == "get_section":
            return source.section(arguments["ticker"], arguments["year"], arguments["item"])
        if tool == "calculate_margin":
            revenue, income = source.canonical_pair(arguments["revenue_fact_id"], arguments["operating_income_fact_id"])
            return {"ticker": revenue["ticker"], "year": revenue["fiscal_year"], "revenue": str(revenue["value"]), "operating_income": str(income["value"]),
                "margin_pct": str((Decimal(income["value"]) / Decimal(revenue["value"]) * 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)),
                "fact_ids": [revenue["id"], income["id"]], "period_start": revenue["start"], "period_end": revenue["end"], "unit": "USD"}
        if tool == "past_notes":
            return store.notes(arguments["actor"])
        if tool == "publish_note":
            return store.publish(arguments["payload"], arguments["capability"])
        raise AssertionError(tool)
    engine = Engine(store, source, tmp_path / "runtime", caller=caller)
    yield engine, store, source, calls, caller, tmp_path
    engine.close()


def begin(engine, store):
    request = {"question": "Compare annual source-backed margins and risks.", "tickers": ["MSFT", "AAPL"], "years": [2023, 2024, 2025], "max_tool_calls": 60}
    return engine.execute(store.create_run(request)["id"])


def decide(engine, run, action="approve", edits=None):
    decision = {"kind": run["pending"]["kind"], "payload_hash": run["pending"]["payload_hash"], "action": action, "edits": edits}
    engine.claim(run["id"], decision)
    return engine.execute(run["id"])


def test_real_graph_pauses_then_checks_and_publishes_only_after_separate_decisions(fixture):
    engine, store, source, calls, _, _ = fixture
    plan = begin(engine, store)
    assert plan["status"] == "awaiting_plan" and calls == [] and store.notes() == []
    note = decide(engine, plan)
    assert note["status"] == "awaiting_note", note.get("error")
    assert len(note["metrics"]) == 6 and len(note["risks"]) == 4
    assert note["critic"]["passed"] and note["critic"]["verified_numbers"] == 18
    assert note["critic"]["semantic_review"] == "not_run_offline"
    assert len([call for call in calls if call[1] == "get_facts"]) == 2
    assert store.notes() == [] and not any(call[1] == "publish_note" for call in calls)
    published = decide(engine, note)
    assert published["status"] == "published", published.get("error")
    assert len(store.notes()) == 1
    assert published["usage"]["model_calls"] == 0 and published["usage"]["cost_usd"] == 0
    assert engine.execute(published["id"])["note_id"] == published["note_id"]
    assert len(store.notes()) == 1


def test_plan_edit_needs_a_new_review_and_reject_does_not_research(fixture):
    engine, store, _, calls, _, _ = fixture
    original = begin(engine, store)
    edited = decide(engine, original, "edit", {"outline": ["Check exact fiscal source periods"]})
    assert edited["status"] == "awaiting_plan" and calls == []
    assert edited["pending"]["payload_hash"] != original["pending"]["payload_hash"]
    with pytest.raises(ReviewError, match="Stale"):
        engine.claim(edited["id"], {"kind": "plan", "action": "approve", "payload_hash": original["pending"]["payload_hash"]})
    rejected = decide(engine, edited, "reject")
    assert rejected["status"] == "rejected" and calls == []


def test_note_edit_rechecks_hash_and_blocks_unverified_claims(fixture):
    engine, store, _, _, _, _ = fixture
    note = decide(engine, begin(engine, store))
    edited = decide(engine, note, "edit", {"body": note["draft"]["body"] + "\nUnsupported forecast: margin reaches 99%."})
    assert edited["status"] == "awaiting_note" and not edited["critic"]["passed"]
    assert edited["critic"]["verified_share"] < .98
    assert edited["pending"]["payload_hash"] != note["pending"]["payload_hash"]
    with pytest.raises(ReviewError, match="Unresolved"):
        engine.claim(edited["id"], {"kind": "note", "action": "approve", "payload_hash": edited["pending"]["payload_hash"]})
    assert store.notes() == []


def test_fiscal_year_digits_cannot_bypass_numeric_claim_verification(fixture):
    engine, store, _, _, _, _ = fixture
    note = decide(engine, begin(engine, store))
    assert note["critic"]["passed"]  # Generated fiscal-year labels remain valid.
    edited = decide(engine, note, "edit", {"body": note["draft"]["body"] + "\nRevenue is 2025 USD."})
    assert edited["status"] == "awaiting_note" and not edited["critic"]["passed"]
    assert edited["critic"]["total_numbers"] == 19
    assert edited["critic"]["verified_numbers"] == 18
    with pytest.raises(ReviewError, match="Unresolved"):
        engine.claim(edited["id"], {"kind": "note", "action": "approve", "payload_hash": edited["pending"]["payload_hash"]})
    assert store.notes() == []


def test_checkpoint_survives_restart_without_inventing_a_decision(fixture):
    engine, store, source, calls, caller, tmp_path = fixture
    pending = begin(engine, store)
    second = Engine(store, source, tmp_path / "runtime", caller=caller)
    try:
        resumed = second.execute(pending["id"])
        assert resumed["status"] == "awaiting_plan"
        assert resumed["pending"]["payload_hash"] == pending["pending"]["payload_hash"]
        assert calls == []
    finally:
        second.close()


def test_company_mcp_reads_use_actual_parallel_graph_branches(fixture):
    engine, store, _, _, caller, _ = fixture
    barrier = threading.Barrier(2)
    def parallel_caller(role, server, tool, arguments):
        if tool == "get_facts":
            barrier.wait(timeout=4)
        return caller(role, server, tool, arguments)
    engine.caller = parallel_caller
    note = decide(engine, begin(engine, store))
    assert note["status"] == "awaiting_note", note.get("error")


def test_local_api_auth_stale_decisions_and_evidence(fixture, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from desk.api import app
    engine, store, source, _, _, _ = fixture
    # Skip production lifespan only; install the isolated real workflow/store.
    app.state.source, app.state.store, app.state.engine = source, store, engine
    app.router.lifespan_context = FastAPI().router.lifespan_context
    monkeypatch.setenv("ANALYST_API_TOKEN", "test-api-token-local-only")
    monkeypatch.setenv("ANALYST_METRICS_TOKEN", "test-metrics-token-local-only")
    with TestClient(app) as client:
        assert client.get("/api/config").status_code == 401
        client.headers["X-Analyst-Token"] = "test-api-token-local-only"
        config = client.get("/api/config").json()
        assert config["mode"] == "offline" and config["transport"] == "http"
        assert client.post("/api/runs", headers={"Origin": "https://untrusted.example"}, json={}).status_code == 403
        created = client.post("/api/runs", json={"question": "Compare annual source margins and risks."})
        assert created.status_code == 202
        run_id = created.json()["id"]
        pending = client.get(f"/api/runs/{run_id}").json()
        assert pending["status"] == "awaiting_plan"
        assert client.post(f"/api/runs/{run_id}/decision", json={"kind": "plan", "action": "approve", "payload_hash": "0" * 64}).status_code == 409
        assert client.post(f"/api/runs/{run_id}/decision", json={"kind": "plan", "action": "edit", "payload_hash": pending["pending"]["payload_hash"], "edits": {"outline": []}}).status_code == 400
        assert client.get(f"/api/runs/{run_id}").json()["status"] == "awaiting_plan"
        fact_id = source.facts("MSFT", [2023])[0]["id"]
        assert client.get("/api/evidence/" + fact_id).json()["id"] == fact_id
        assert client.get("/api/evidence/test:MSFT:2023:item1A").status_code == 200
        assert client.get("/api/evidence/missing").status_code == 404
        assert client.get("/api/notes").json() == []
        assert client.get("/api/budget").json()["spent_usd"] == 0
        assert "analyst_verified_number_share NaN" in client.get("/metrics").text
    # Avoid leaking the temporary no-op lifespan into other test imports.
    from desk.api import lifespan
    app.router.lifespan_context = lifespan
