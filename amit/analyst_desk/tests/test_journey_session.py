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


def test_live_client_requires_enabled_configuration_before_any_research_post(tmp_path, monkeypatch):
    client = journey.JourneyClient(token=TOKEN, mode="live", session_path=tmp_path / "live.json", receipt_path=tmp_path / "receipt.json")
    calls = []
    monkeypatch.setattr(client, "request", lambda method, path, body=None: calls.append(method) or config(mode="offline", live_enabled=False))
    with pytest.raises(journey.JourneyError, match="explicitly authorized"):
        client.prepare()
    assert calls == ["GET"]


def test_live_client_sends_explicit_live_limits_and_keeps_human_gate(tmp_path, monkeypatch):
    client = journey.JourneyClient(token=TOKEN, mode="live", session_path=tmp_path / "live.json", receipt_path=tmp_path / "receipt.json")
    calls = []
    def request(method, path, body=None):
        calls.append((method, path, body))
        return config(mode="offline", live_enabled=True, live_model_config_version="test-live-v1") if path == "/api/config" else run(mode="live", request=client.research_request)
    monkeypatch.setattr(client, "request", request)
    receipt = client.prepare()
    body = next(body for method, _, body in calls if method == "POST")
    assert body["mode"] == "live" and body["max_tokens"] == 250000 and body["max_model_calls"] == 12
    assert receipt["configuration"]["mode"] == "live" and receipt["configuration"]["model_config_version"] == "test-live-v1"
    assert receipt["status"] == "awaiting_plan" and receipt["decision_requests"] == []
    assert journey.REQUEST.get("mode") is None


def test_explicit_continuation_keeps_run_budget_and_does_not_record_another_approval(client, monkeypatch):
    client.mode = "live"
    failed = run(status="error", request={**journey.REQUEST, "mode": "live", "max_tokens": 250000, "max_model_calls": 12},
                 continuation={"available": True, "plan_hash": HASH, "failure_kind": "content_validation"})
    calls = []
    def request(method, path, body=None):
        calls.append((method, path, body))
        if path == "/api/config":
            return config(mode="offline", live_enabled=True)
        if method == "POST":
            return {**failed, "status": "running", "pending": None}
        if len(calls) == 2:
            return failed
        return run("note", request=failed["request"])
    monkeypatch.setattr(client, "request", request)
    receipt = client.continue_run("run-1", expected_plan_hash=HASH)
    assert receipt["status"] == "awaiting_note" and receipt["decision_requests"] == []
    assert receipt["request"]["max_tokens"] == 250000 and receipt["request"]["max_model_calls"] == 12
    assert [item for item in calls if item[0] == "POST"] == [("POST", "/api/runs/run-1/continue", {"plan_hash": HASH})]
    assert receipt["continuation_requests"][0]["plan_hash"] == HASH
    assert receipt["continuation_requests"][0]["accepted_by_api"] is True
    assert "human_confirmation" not in client.session_path.read_text()
    assert "human_review_verified" not in client.receipt_path.read_text()
    assert journey.parser().parse_args(["continue", "run-1", "--expected-plan-hash", HASH]).command == "continue"


@pytest.mark.parametrize("case", ["offline_mode", "disabled_budget", "not_failed", "ineligible", "wrong_hash", "wrong_run_mode"])
def test_continuation_client_never_posts_for_invalid_or_unready_run(client, monkeypatch, case):
    client.mode = "offline" if case == "offline_mode" else "live"
    failed = run(status="error", request={**journey.REQUEST, "mode": "live"},
                 continuation={"available": True, "plan_hash": HASH})
    if case == "not_failed":
        failed["status"] = "awaiting_plan"
    elif case == "ineligible":
        failed["continuation"]["available"] = False
    elif case == "wrong_hash":
        failed["continuation"]["plan_hash"] = "b" * 64
    elif case == "wrong_run_mode":
        failed["request"]["mode"] = "offline"
    calls = []
    def request(method, path, body=None):
        calls.append((method, path, body))
        return config(mode="offline", live_enabled=case != "disabled_budget") if path == "/api/config" else failed
    monkeypatch.setattr(client, "request", request)
    with pytest.raises(journey.JourneyError):
        client.continue_run("run-1", expected_plan_hash=HASH)
    assert all(method == "GET" for method, _, _ in calls)
    assert not client.session_path.exists()


def test_continuation_cli_requires_existing_plan_hash():
    with pytest.raises(SystemExit) as error:
        journey.parser().parse_args(["continue", "run-1"])
    assert error.value.code == 2


def test_critic_rate_limit_retry_requires_explicit_client_flag_and_retains_receipt(client, monkeypatch):
    client.mode = "live"
    failed = run(status="error", request={**journey.REQUEST, "mode": "live", "max_model_calls": 12},
                 continuation={"available": False, "retry_transient_available": True,
                               "plan_hash": HASH, "failure_kind": "critic_rate_limit"},
                 usage={"model_calls": 10, "held_usd": .035768})
    calls = []
    posted = False
    def request(method, path, body=None):
        nonlocal posted
        calls.append((method, path, body))
        if path == "/api/config":
            return config(mode="offline", live_enabled=True)
        if method == "POST":
            posted = True
            return {**failed, "status": "running", "pending": None}
        if posted:
            return run("note", request=failed["request"], usage={"model_calls": 11, "held_usd": .035768})
        return failed
    monkeypatch.setattr(client, "request", request)
    with pytest.raises(journey.JourneyError):
        client.continue_run("run-1", expected_plan_hash=HASH)
    assert all(item[0] == "GET" for item in calls)
    receipt = client.continue_run("run-1", expected_plan_hash=HASH, retry_transient=True)
    assert [item for item in calls if item[0] == "POST"] == [
        ("POST", "/api/runs/run-1/continue", {"plan_hash": HASH, "retry_transient": True})]
    assert receipt["usage"]["held_usd"] == .035768
    assert receipt["continuation_requests"][-1]["retry_transient"] is True
    assert receipt["decision_requests"] == []
    args = journey.parser().parse_args(["continue", "run-1", "--expected-plan-hash", HASH, "--retry-transient"])
    assert args.retry_transient is True


@pytest.mark.parametrize("case", ["content_only", "provider_refusal", "exhausted", "invalid_flag"])
def test_explicit_transient_retry_does_not_post_when_hint_is_ineligible(client, monkeypatch, case):
    client.mode = "live"
    hint = {"available": case == "content_only", "retry_transient_available": False,
            "plan_hash": HASH, "failure_kind": "provider_http_403" if case == "provider_refusal" else "not_eligible"}
    failed = run(status="error", request={**journey.REQUEST, "mode": "live"}, continuation=hint)
    calls = []
    def request(method, path, body=None):
        calls.append((method, path, body))
        return config(mode="offline", live_enabled=True) if path == "/api/config" else failed
    monkeypatch.setattr(client, "request", request)
    with pytest.raises(journey.JourneyError):
        client.continue_run("run-1", expected_plan_hash=HASH, retry_transient="true" if case == "invalid_flag" else True)
    assert all(item[0] == "GET" for item in calls)
    assert not client.session_path.exists()


def test_replacement_critic_policy_client_requires_explicit_matching_policy_hash(client, monkeypatch):
    client.mode = "live"
    policy_hash = "c" * 64
    failed = run(status="error", request={**journey.REQUEST, "mode": "live", "max_model_calls": 12},
                 continuation={"available": False, "replace_critic_policy_available": True,
                               "plan_hash": HASH, "policy_hash": policy_hash, "failure_kind": "critic_rate_limit"})
    calls = []
    posted = False
    def request(method, path, body=None):
        nonlocal posted
        calls.append((method, path, body))
        if path == "/api/config":
            return config(mode="offline", live_enabled=True)
        if method == "POST":
            posted = True
            return {**failed, "status": "running", "pending": None}
        return run("note", request=failed["request"]) if posted else failed
    monkeypatch.setattr(client, "request", request)
    with pytest.raises(journey.JourneyError):
        client.continue_run("run-1", expected_plan_hash=HASH)
    with pytest.raises(journey.JourneyError):
        client.continue_run("run-1", expected_plan_hash=HASH, replace_critic_policy="d" * 64)
    assert all(item[0] == "GET" for item in calls)
    receipt = client.continue_run("run-1", expected_plan_hash=HASH, replace_critic_policy=policy_hash)
    assert [item for item in calls if item[0] == "POST"] == [
        ("POST", "/api/runs/run-1/continue", {"plan_hash": HASH, "replace_critic_policy": policy_hash})]
    assert receipt["decision_requests"] == []
    assert receipt["continuation_requests"][-1]["replace_critic_policy"] == policy_hash
    assert "retry_transient" not in receipt["continuation_requests"][-1]
    args = journey.parser().parse_args(["continue", "run-1", "--expected-plan-hash", HASH,
                                       "--replace-critic-policy", policy_hash])
    assert args.replace_critic_policy == policy_hash and not args.retry_transient


@pytest.mark.parametrize("replacement,retry", [("bad", False), (True, False), ("c" * 64, True)])
def test_replacement_critic_policy_client_rejects_invalid_hash_or_combo_before_request(client, monkeypatch, replacement, retry):
    client.mode = "live"
    calls = []
    monkeypatch.setattr(client, "request", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(journey.JourneyError):
        client.continue_run("run-1", expected_plan_hash=HASH, replace_critic_policy=replacement, retry_transient=retry)
    assert calls == []


def test_replacement_critic_policy_cli_cannot_combine_with_transient_retry():
    with pytest.raises(SystemExit) as error:
        journey.parser().parse_args(["continue", "run-1", "--expected-plan-hash", HASH,
                                    "--replace-critic-policy", "c" * 64, "--retry-transient"])
    assert error.value.code == 2
