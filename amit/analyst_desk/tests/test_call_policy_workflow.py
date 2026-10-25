"""Unlimited program call accounting and exact-note critic rechecks, simulated."""
from copy import deepcopy
import json

import pytest

from desk.store import canonical_hash
from desk.workflow import ReviewError, verify_draft
from test_workflow import fixture, decide
from test_live_workflow import FakeModelClient


class ProgramClient(FakeModelClient):
    def __init__(self, *, unlimited=True, body_issue=True):
        super().__init__()
        self.unlimited, self.body_issue = unlimited, body_issue

    def budget(self, run_id=None):
        return {"model_profile": "live-program-models-v1", "enabled": True, "blocked": False,
                "max_calls_per_run": None if self.unlimited else 12}

    def complete(self, **request):
        result = super().complete(**request)
        if request["role"] == "critic" and self.body_issue:
            result["content"]["issues"] = ["Test-only body review needs reporting context."]
        self.cache[request["call_id"]] = deepcopy(result)
        return result


def start(engine, store, *, max_model_calls=12, max_tokens=250000):
    return engine.execute(store.create_run({"question": "Compare source-backed margins and selected risk disclosures.",
        "tickers": ["MSFT", "AAPL"], "years": [2024, 2025], "mode": "live", "max_tool_calls": 60,
        "max_model_calls": max_model_calls, "max_tokens": max_tokens})["id"])


def reach_twelve_settled_calls(store, run_id):
    run = store.get_run(run_id)
    while len(run["usage"]["calls"]) < 12:
        index = len(run["usage"]["calls"])
        run["usage"]["calls"].append({"call_id": f"synthetic-previous-call-{index}", "stage": "writer",
            "model_calls": 1, "prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20,
            "cost_usd": "0.001", "config_version": "test-only-v1"})
    run["usage"].update(model_calls=12, tokens=240, cost_usd=.012)
    store.save_run(run)
    return deepcopy(run["usage"]["calls"])


def test_body_only_critic_objection_stops_at_review_without_rewriting_supported_claims(fixture):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = ProgramClient()
    note = decide(engine, start(engine, store))
    assert note["status"] == "awaiting_note" and not note["critic"]["passed"]
    assert all(value["supported"] for value in note["draft"]["semantic_verdict"]["verdicts"])
    assert note["repairs"] == 0
    assert sum(call["role"] == "writer" for call in client.calls) == 1
    assert sum(call["role"] == "critic" for call in client.calls) == 1
    assert store.notes() == []


def test_exact_blocked_note_can_recheck_after_twelve_calls_without_resetting_history(fixture):
    engine, store, source, _, _, _ = fixture
    client = engine.model_client = ProgramClient()
    plan = start(engine, store)
    note = decide(engine, plan)
    original_request, original_plan = deepcopy(note["request"]), deepcopy(note["plan"])
    old_body, old_hash = note["draft"]["body"], note["pending"]["payload_hash"]
    previous_calls = reach_twelve_settled_calls(store, note["id"])
    client.body_issue = False
    checked = decide(engine, note, "recheck")
    assert checked["status"] == "awaiting_note" and checked["critic"]["passed"], checked.get("error")
    assert checked["usage"]["model_calls"] == 13 and checked["usage"]["cost_usd"] == .013
    assert checked["usage"]["calls"][:-1] == previous_calls
    assert checked["draft"]["body"] == old_body
    assert checked["request"] == original_request and checked["request"]["max_model_calls"] == 12
    assert checked["plan"] == original_plan == plan["plan"]
    assert checked["pending"]["payload_hash"] != old_hash  # fresh verdict is an exact new review version
    assert verify_draft(checked["draft"], source)["passed"]
    assert sum(call["role"] == "writer" for call in client.calls) == 1
    critics = [call for call in client.calls if call["role"] == "critic"]
    assert len(critics) == 2 and critics[0]["call_id"] != critics[1]["call_id"]
    assert len([event for event in checked["events"] if event["stage"] == "note_recheck"]) == 1
    assert not any(event["stage"] in {"note_edit", "note_approved", "published"} for event in checked["events"])
    assert store.notes() == []


def test_legacy_call_ceiling_still_blocks_an_extra_critic(fixture):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = ProgramClient(unlimited=False)
    note = decide(engine, start(engine, store))
    previous = reach_twelve_settled_calls(store, note["id"])
    before = len(client.calls)
    failed = decide(engine, note, "recheck")
    assert failed["status"] == "error" and "model-call budget is exhausted" in failed["error"]
    assert len(client.calls) == before and failed["usage"]["calls"] == previous
    assert store.notes() == []


@pytest.mark.parametrize("budget", [None, {}, {"model_profile": "live-program-models-v1", "enabled": True, "blocked": False},
    {"model_profile": "live-step6-openrouter-v1", "enabled": True, "blocked": False, "max_calls_per_run": None},
    {"model_profile": "live-program-models-v1", "enabled": True, "blocked": True, "max_calls_per_run": None}])
def test_null_request_cannot_bypass_missing_disabled_or_legacy_call_policy(fixture, budget):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = ProgramClient()
    client.budget = lambda run_id=None: deepcopy(budget)
    failed = start(engine, store, max_model_calls=None)
    assert failed["status"] == "error" and "active program model policy" in failed["error"]
    assert client.calls == [] and store.notes() == []


def test_unlimited_call_policy_retains_token_limit(fixture):
    engine, store, _, _, _, _ = fixture
    client = engine.model_client = ProgramClient()
    failed = start(engine, store, max_model_calls=None, max_tokens=100)
    assert failed["status"] == "error" and "token budget" in failed["error"]
    assert client.calls == [] and failed["usage"]["model_calls"] == 0


@pytest.mark.parametrize("kind,action", [("plan", "recheck"), ("note", "recheck")])
def test_recheck_refuses_plan_or_passing_note_without_recording_approval(fixture, kind, action):
    engine, store, _, _, _, _ = fixture
    engine.model_client = ProgramClient(body_issue=False)
    plan = start(engine, store)
    run = plan if kind == "plan" else decide(engine, plan)
    with pytest.raises(ReviewError, match="blocked live note"):
        engine.claim(run["id"], {"kind": kind, "action": action, "payload_hash": run["pending"]["payload_hash"], "edits": None})
    assert store.get_run(run["id"])["status"] == run["status"]
    assert store.notes() == []


def test_workflow_reconstructs_canonical_filing_dates_and_run_date_for_critic(fixture):
    engine, store, source, _, _, _ = fixture
    for fact in source._facts.values():
        fact["filed"] = f"{fact['fiscal_year'] + 1}-02-01"
    client = engine.model_client = ProgramClient(body_issue=False)
    note = decide(engine, start(engine, store))
    assert note["status"] == "awaiting_note" and note["critic"]["passed"], note.get("error")
    request = next(call for call in client.calls if call["role"] == "critic")
    context = json.loads(request["messages"][-1]["content"])["review_context"]
    assert context["financial_checks"] == {"passed": True, "verified_numbers": 12, "total_numbers": 12}
    assert context["source_fingerprint"] == source.fingerprint and len(context["source_periods"]) == 4
    assert all(period["filed"] == source.fact(period["source_ids"][0])["filed"] for period in context["source_periods"])
    assert context["as_of"] >= "2026-02-01"  # runtime date supplied by the trusted run record
    assert canonical_hash(note["plan"]) == note["plan_approval"]["payload_hash"]
