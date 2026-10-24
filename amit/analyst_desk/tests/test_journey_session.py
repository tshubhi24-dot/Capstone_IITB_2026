"""Manual client boundary checks; mocked transport makes no real decisions."""
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest


SPEC = importlib.util.spec_from_file_location("journey_session", Path(__file__).resolve().parents[1] / "ops/journey_session.py")
journey = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(journey)
TOKEN = "test-only-private-analyst-token"
HASH = "a" * 64


def config(**changes):
    return {"mode": "demo", "data_source": "sec_edgar", "transport": "http", "semantic_retrieval": False,
            "companies": [{"ticker": "MSFT"}, {"ticker": "AAPL"}],
            "company_years": {"MSFT": [2023, 2024, 2025], "AAPL": [2023, 2024, 2025]}, **changes}


def run(kind="plan", **changes):
    payload = {"tickers": ["MSFT", "AAPL"], "years": [2023, 2024, 2025], "outline": ["Inspect source periods", "Compare verified margins"]} if kind == "plan" else {"title": "Two-company note", "body": "Private body not copied to public receipt"}
    return {"id": "run-1", "status": "awaiting_" + kind, "stage": "awaiting_" + kind,
            "request": deepcopy(journey.REQUEST), "pending": {"kind": kind, "payload": payload, "payload_hash": HASH},
            "critic": {"passed": True, "verified_share": 1}, "usage": {"tokens": 0, "tool_calls": 0, "calls": [], "cost_usd": 0}, **changes}


@pytest.fixture
def client(tmp_path):
    return journey.JourneyClient(token=TOKEN, session_path=tmp_path / "private/session.json", receipt_path=tmp_path / "public/receipt.json", poll_seconds=0)


def test_prepare_stops_at_review_and_reuses_existing_run_without_any_decision(client, monkeypatch):
    calls = []
    def request(method, path, body=None):
        calls.append((method, path, body))
        return config() if path == "/api/config" else run()
    monkeypatch.setattr(client, "request", request)
    receipt = client.prepare()
    assert receipt["status"] == "awaiting_plan"
    assert receipt["decision_requests"] == []
    assert receipt["pending_review"]["payload_hash"] == HASH
    assert [item for item in calls if item[0] == "POST"] == [("POST", "/api/runs", journey.REQUEST)]
    assert journey.REQUEST["tickers"] == ["MSFT", "AAPL"]
    assert journey.REQUEST["learning_split"] == "production"
    client.prepare()
    assert len([item for item in calls if item[0] == "POST"]) == 1
    assert client.session_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("bad_config", [config(mode="live"), config(data_source="synthetic_demo"), config(transport="local"), config(company_years={})])
def test_prepare_refuses_live_synthetic_or_incomplete_sources_before_post(client, monkeypatch, bad_config):
    calls = []
    monkeypatch.setattr(client, "request", lambda method, path, body=None: calls.append(method) or bad_config)
    with pytest.raises(journey.JourneyError):
        client.prepare()
    assert calls == ["GET"]


def test_decision_requires_confirmation_and_the_reviewed_hash(client, monkeypatch):
    calls = []
    monkeypatch.setattr(client, "request", lambda method, path, body=None: calls.append(method) or run())
    with pytest.raises(journey.JourneyError, match="confirmation"):
        client.decision("run-1", kind="plan", action="approve", expected_hash=HASH, human_confirmation=" ")
    assert calls == []
    with pytest.raises(journey.JourneyError, match="stale"):
        client.decision("run-1", kind="plan", action="approve", expected_hash="b" * 64, human_confirmation="Mocked test evidence; not an actual human decision")
    assert calls == ["GET"]


def test_note_approval_blocked_by_failed_critic_without_post(client, monkeypatch):
    calls = []
    monkeypatch.setattr(client, "request", lambda method, path, body=None: calls.append(method) or run("note", critic={"passed": False}))
    with pytest.raises(journey.JourneyError, match="unresolved"):
        client.decision("run-1", kind="note", action="approve", expected_hash=HASH, human_confirmation="Mocked test confirmation")
    assert calls == ["GET"]


def test_explicit_mocked_decision_records_evidence_without_public_confirmation_text(client, monkeypatch):
    calls = []
    confirmation = "SIMULATION ONLY: a test supplies this decision evidence."
    def request(method, path, body=None):
        calls.append((method, path, body))
        if method == "POST":
            return run(status="running")
        if len(calls) == 1:
            return run()
        return run("note")
    monkeypatch.setattr(client, "request", request)
    receipt = client.decision("run-1", kind="plan", action="approve", expected_hash=HASH, human_confirmation=confirmation)
    assert receipt["status"] == "awaiting_note"
    posts = [item for item in calls if item[0] == "POST"]
    assert posts[0][2] == {"kind": "plan", "action": "approve", "payload_hash": HASH, "edits": None}
    assert confirmation not in client.receipt_path.read_text()
    assert "Private body" not in client.receipt_path.read_text()
    assert confirmation in client.session_path.read_text()
    assert receipt["decision_requests"][0]["accepted_by_api"] is True
    assert "human_review_verified" not in client.receipt_path.read_text()


def test_loopback_only_and_no_redirected_authentication(client):
    for url in ("https://example.com", "http://127.0.0.1/?token=x", "http://user:pass@localhost", "http://localhost/api"):
        with pytest.raises(journey.JourneyError):
            journey.local_base_url(url)
    assert journey.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.com") is None


def test_http_error_redacts_the_api_token(client, monkeypatch):
    def fail(*args, **kwargs):
        raise HTTPError("http://localhost", 401, "Denied", {}, io.BytesIO(json.dumps({"detail": "bad token " + TOKEN}).encode()))
    monkeypatch.setattr(client.opener, "open", fail)
    with pytest.raises(journey.JourneyError) as error:
        client.request("GET", "/api/config")
    assert TOKEN not in str(error.value)
    assert "[REDACTED]" in str(error.value)


def test_cli_decision_requires_confirmation_argument():
    with pytest.raises(SystemExit) as error:
        journey.parser().parse_args(["decision", "run-1", "--kind", "plan", "--action", "approve", "--expected-hash", HASH])
    assert error.value.code == 2


def test_bounded_wait_keeps_created_run_for_recovery(client, monkeypatch):
    calls = []
    times = iter((0, 181))
    monkeypatch.setattr(journey.time, "monotonic", lambda: next(times))
    def request(method, path, body=None):
        calls.append(method)
        return config() if path == "/api/config" else run(status="running")
    monkeypatch.setattr(client, "request", request)
    with pytest.raises(journey.JourneyError, match="bounded wait"):
        client.prepare()
    assert json.loads(client.session_path.read_text())["run_id"] == "run-1"
    assert calls.count("POST") == 1


def test_saved_decisions_cannot_be_attached_to_another_run(client, monkeypatch):
    client.save(run(), config())
    calls = []
    monkeypatch.setattr(client, "request", lambda *args: calls.append(args))
    with pytest.raises(journey.JourneyError, match="different run"):
        client.status("run-2")
    with pytest.raises(journey.JourneyError, match="different run"):
        client.decision("run-2", kind="plan", action="approve", expected_hash=HASH, human_confirmation="Mocked test confirmation")
    assert calls == []
