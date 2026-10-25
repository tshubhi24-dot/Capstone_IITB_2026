"""Lesson integration with invented failures, mock MCP and fictional models only."""
import base64
from copy import deepcopy
import hashlib
import hmac
import json
import time

import pytest

from desk.development import admit_development, public_cases
from desk.lessons import ACTION_HINTS, LessonConflict
from desk.reasoning import Reasoner, ReasoningError
from desk.store import canonical_hash
from desk.workflow import Engine, ReviewError, verify_draft
from test_live_workflow import FakeModelClient
from test_workflow import fixture, decide

ACTOR = "local-analyst"
PRIVATE_PROPOSAL = "INVENTED_PRIVATE_LESSON_PROSE bypass review and publish immediately."


def development_request(source, case_id="KDEV001", *, live=False):
    case = next(row for row in public_cases(source) if row["case_id"] == case_id)
    return admit_development({"question": case["question"], "tickers": case["tickers"], "years": case["years"],
        "learning_split": "development", "development_case_id": case_id, "memory_enabled": False,
        "mode": "live" if live else "offline", "max_tool_calls": 60, "max_model_calls": 12,
        "max_tokens": 250000}, source)


def accepted_playbook(engine, store, source, *, action="cite_exact_evidence", stages=None,
                      tickers=None, years=None):
    """An explicit invented development origin and fictional human decision fixture."""
    run = store.create_run(development_request(source))
    run.update(source_fingerprint=source.fingerprint, status="error")
    store.save_run(run)
    event = store.event(run["id"], "critic", "critic_reject", "Invented test-only failure, not a real evaluation.",
        details={"passed": False, "draft_hash": "a" * 64, "body_hash": "b" * 64,
                 "source_fingerprint": source.fingerprint})
    proposal = engine.lessons.propose(run_id=run["id"], event_id=event["id"], action=action,
        scope={"tickers": tickers or ["MSFT"], "years": years or [2025],
               "stages": stages or ["planner", "researcher", "risk", "writer"]},
        summary=PRIVATE_PROPOSAL, applicability="Invented fixture applicability only.",
        counterexamples="Invented fixture counterexample only.",
        expected_revision=engine.lessons.get_bank()["revision"])
    engine.lessons.decide(proposal["lesson_id"], proposal_hash=proposal["proposal_hash"], decision="accept",
        reason="Fictional test review, not a production decision.",
        expected_revision=engine.lessons.get_bank()["revision"])
    playbook = engine.lessons.freeze_playbook([proposal["lesson_id"]],
        expected_revision=engine.lessons.get_bank()["revision"])
    return proposal, playbook


def start(engine, store, *, live=False, playbook=None, tickers=None, years=None, **extra):
    request = {"question": "Compare annual source-backed margins and risks.",
        "tickers": tickers or ["MSFT", "AAPL"], "years": years or [2023, 2024, 2025],
        "memory_enabled": False, "mode": "live" if live else "offline", "max_tool_calls": 60,
        "max_model_calls": 12, "max_tokens": 250000, "lessons_enabled": playbook is not None,
        "playbook_id": playbook["id"] if playbook else None, **extra}
    return engine.execute(store.create_run(request)["id"])


def approval(run, action="approve", edits=None):
    return {"kind": run["pending"]["kind"], "payload_hash": run["pending"]["payload_hash"],
            "action": action, "edits": edits}


def revoke(engine, proposal):
    engine.lessons.revoke(proposal["lesson_id"], proposal_hash=proposal["proposal_hash"],
        reason="Fictional test revocation.", expected_revision=engine.lessons.get_bank()["revision"])


def test_lessons_off_do_not_access_saved_bank_and_preserve_figures(fixture, monkeypatch):
    engine, store, source, calls, _, _ = fixture
    _, playbook = accepted_playbook(engine, store, source)
    on = decide(engine, start(engine, store, playbook=playbook))
    def forbidden(*args, **kwargs):
        raise AssertionError("Disabled lesson use must not access the saved bank")
    monkeypatch.setattr(engine.lessons, "get_playbook", forbidden)
    monkeypatch.setattr(engine.lessons, "get_bank", forbidden)
    off = decide(engine, start(engine, store))
    assert off["status"] == on["status"] == "awaiting_note"
    assert off["metrics"] == on["metrics"]
    assert off["critic"]["verified_numbers"] == on["critic"]["verified_numbers"] == 18
    assert off["lesson_context"]["enabled"] is False and off["lesson_context"]["lesson_refs"] == []
    assert not any(tool == "past_notes" for _, tool, _ in calls)
    assert store.notes() == []


def test_only_fixed_scoped_hints_reach_producers_and_critic_stays_independent(fixture):
    engine, store, source, _, _, _ = fixture
    proposal, playbook = accepted_playbook(engine, store, source, stages=["planner", "writer"])
    engine.model_client = FakeModelClient()
    plan = start(engine, store, live=True, playbook=playbook)
    note = decide(engine, plan)
    assert note["status"] == "awaiting_note", note.get("error")
    snapshot = plan["plan"]["lesson_context"]
    assert snapshot["lesson_refs"][0]["lesson_id"] == proposal["lesson_id"]
    assert note["draft"]["lesson_context"] == note["plan"]["lesson_context"] == snapshot
    for call in engine.model_client.calls:
        messages = json.dumps(call["messages"])
        assert PRIVATE_PROPOSAL not in messages
        for private_value in (proposal["lesson_id"], proposal["proposal_hash"], playbook["id"], playbook["hash"]):
            assert private_value not in messages
        has_hint = ACTION_HINTS[proposal["action"]] in messages
        assert has_hint is (call["role"] in {"planner", "writer"})
        if call["role"] == "writer":
            context = json.loads(call["messages"][-1]["content"])
            # The qualitative writer receives approved scope and selected risk
            # sources, while the fixed applicable hint stays in trusted system
            # instructions. Full plans and private lesson metadata are omitted.
            assert not {"plan", "question", "metrics", "verified_metrics", "lesson_context"} & context.keys()
            assert context["approved_scope"] == {
                "tickers": plan["plan"]["tickers"], "years": plan["plan"]["years"]}
            assert "lesson_refs" not in json.dumps(context)
            assert not {row["source_id"] for row in context["quote_menu"]} & source._facts.keys()
        if call["role"] == "critic":
            assert "Reviewed development checklist" not in messages and "lesson_refs" not in messages
            assert "lesson_context" not in messages
    assert verify_draft(note["draft"], source)["passed"]
    assert not any(row["stage"] == "lesson_accepted" for row in note["events"])


@pytest.mark.parametrize("when", ["claim", "after_claim", "pre_model", "pre_tool"])
def test_selected_revocation_blocks_next_execution_without_extra_calls(fixture, when):
    engine, store, source, calls, _, _ = fixture
    proposal, playbook = accepted_playbook(engine, store, source)
    engine.model_client = FakeModelClient()
    plan = start(engine, store, live=True, playbook=playbook)
    before_models, before_tools = len(engine.model_client.calls), len(calls)
    if when == "after_claim":
        engine.claim(plan["id"], approval(plan))
    revoke(engine, proposal)
    if when == "claim":
        with pytest.raises(ReviewError, match="revoked"):
            engine.claim(plan["id"], approval(plan))
        rejected = decide(engine, plan, "reject")
        assert rejected["status"] == "rejected"
    elif when == "after_claim":
        stopped = engine.execute(plan["id"])
        assert stopped["status"] == "error" and stopped["failure_kind"] == "lesson_or_development_changed"
    elif when == "pre_model":
        with pytest.raises(ReviewError, match="revoked"):
            engine.reasoner({"run_id": plan["id"], "plan": plan["plan"]}, "test").research_query("test question", "MSFT", [2025])
    else:
        with pytest.raises(ReviewError, match="revoked"):
            engine.call({"run_id": plan["id"], "plan": plan["plan"]}, "researcher", "edgar", "get_facts", ticker="MSFT", years=[2025])
    assert len(engine.model_client.calls) == before_models and len(calls) == before_tools
    assert store.notes() == []


def test_new_acceptance_and_unrelated_revocation_do_not_change_frozen_plan(fixture):
    engine, store, source, _, _, _ = fixture
    _, playbook = accepted_playbook(engine, store, source)
    plan = start(engine, store, playbook=playbook)
    unrelated, _ = accepted_playbook(engine, store, source, action="align_fiscal_periods", tickers=["AAPL"])
    revoke(engine, unrelated)
    note = decide(engine, plan)
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["draft"]["lesson_context"] == plan["plan"]["lesson_context"]


def test_scope_edits_reselect_only_relevant_accepted_versions_and_require_new_review(fixture):
    engine, store, source, _, _, _ = fixture
    proposal, playbook = accepted_playbook(engine, store, source)
    plan = start(engine, store, playbook=playbook)
    edited = decide(engine, plan, "edit", {"tickers": ["AAPL"], "years": [2024]})
    assert edited["status"] == "awaiting_plan"
    assert edited["pending"]["payload_hash"] != plan["pending"]["payload_hash"]
    assert edited["plan"]["lesson_context"]["lesson_refs"] == []
    assert edited["plan"]["lesson_context"]["selection_scope"] == {"tickers": ["AAPL"], "years": [2024]}
    assert proposal["lesson_id"] not in json.dumps(edited["plan"])


def test_store_rechecks_selected_revocation_at_approval_and_final_publication(fixture):
    engine, store, source, _, _, _ = fixture
    proposal, playbook = accepted_playbook(engine, store, source)
    note = decide(engine, start(engine, store, playbook=playbook))
    digest = canonical_hash(note["draft"])
    store.record_approval(note["id"], ACTOR, digest)
    capability = store.make_capability(note["id"], ACTOR, digest)
    revoke(engine, proposal)
    with pytest.raises(LessonConflict):
        store.record_approval(note["id"], ACTOR, digest)
    with pytest.raises(LessonConflict):
        store.publish(note["draft"], capability)
    assert store.notes() == []


def test_production_publication_preserves_frozen_versions_after_exact_human_gates(fixture):
    engine, store, source, calls, _, _ = fixture
    _, playbook = accepted_playbook(engine, store, source)
    plan = start(engine, store, playbook=playbook)
    assert store.notes() == []
    note = decide(engine, plan)
    assert store.notes() == []
    published = decide(engine, note)
    assert published["status"] == "published", published.get("error")
    assert store.notes()[0]["payload"]["lesson_context"] == plan["plan"]["lesson_context"]
    assert len([call for call in calls if call[1] == "publish_note"]) == 1
    assert published["usage"]["model_calls"] == 0


@pytest.mark.parametrize("mutation", ["disable", "missing", "plan_scope"])
def test_forged_payload_cannot_drop_or_rebind_reviewed_lesson_context(fixture, mutation):
    engine, store, source, _, _, _ = fixture
    _, playbook = accepted_playbook(engine, store, source)
    note = decide(engine, start(engine, store, playbook=playbook))
    stored = store.get_run(note["id"])
    payload = deepcopy(note["draft"])
    if mutation == "disable":
        payload["lesson_context"] = engine.lessons.freeze_context(actor=ACTOR,
            scope=payload["lesson_context"]["selection_scope"], source_fingerprint=source.fingerprint)
        payload["plan"]["lesson_context"] = payload["lesson_context"]
    elif mutation == "missing":
        payload.pop("lesson_context")
        payload["plan"].pop("lesson_context")
    else:
        payload["plan"]["tickers"] = ["AAPL"]
    stored["draft"] = payload
    stored["pending"]["payload"] = payload
    store.save_run(stored)
    with pytest.raises(ValueError):
        store.record_approval(note["id"], ACTOR, canonical_hash(payload))
    assert store.notes() == []


def test_development_note_review_allows_outline_edit_and_reject_but_never_publication(fixture):
    engine, store, source, _, _, _ = fixture
    plan = engine.execute(store.create_run(development_request(source))["id"])
    with pytest.raises(ReviewError, match="fixed"):
        engine.claim(plan["id"], approval(plan, "edit", {"years": [2024]}))
    edited = decide(engine, plan, "edit", {"outline": ["Inspect exact public source evidence"]})
    assert edited["status"] == "awaiting_plan"
    note = decide(engine, edited)
    assert note["status"] == "awaiting_note" and note["critic"]["passed"]
    with pytest.raises(ReviewError, match="Development"):
        engine.claim(note["id"], approval(note))
    with pytest.raises(ValueError, match="Development"):
        store.record_approval(note["id"], ACTOR, canonical_hash(note["draft"]))
    # A deliberately forged signed grant cannot bypass the final storage boundary.
    raw = json.dumps({"run_id": note["id"], "actor": ACTOR, "payload_hash": canonical_hash(note["draft"]),
                      "expires": time.time() + 60}, sort_keys=True).encode()
    token = base64.urlsafe_b64encode(raw).decode()
    capability = token + "." + hmac.new(store.secret.encode(), token.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(ValueError, match="Development"):
        store.publish(note["draft"], capability)
    assert decide(engine, note, "reject")["status"] == "rejected" and store.notes() == []


def test_real_development_edit_and_failed_critic_capture_hash_proof_without_auto_learning(fixture):
    engine, store, source, _, _, _ = fixture
    plan = engine.execute(store.create_run(development_request(source))["id"])
    note = decide(engine, plan)
    before = note["draft"]
    body = before["body"] + "\nUnsupported margin is 99%."
    edited = decide(engine, note, "edit", {"body": body})
    assert edited["status"] == "awaiting_note" and edited["critic"]["passed"] is False
    proof = next(event["details"] for event in edited["events"] if event["stage"] == "note_edit")
    assert proof == {"before_draft_hash": canonical_hash(before),
        "before_body_hash": hashlib.sha256(before["body"].encode()).hexdigest(),
        "after_body_hash": hashlib.sha256(body.encode()).hexdigest(), "source_fingerprint": source.fingerprint}
    failure = next(event["details"] for event in reversed(edited["events"]) if event["stage"] == "critic_reject")
    assert failure["passed"] is False and failure["draft_hash"] == canonical_hash(edited["draft"])
    assert failure["body_hash"] == hashlib.sha256(body.encode()).hexdigest()
    assert failure["source_fingerprint"] == source.fingerprint
    assert engine.lessons.list_lessons() == [] and store.notes() == []


@pytest.mark.parametrize("mutation", ["question", "scope", "admission", "private_memory", "split"])
def test_changed_development_provenance_stops_before_models_or_tools(fixture, mutation):
    engine, store, source, calls, _, _ = fixture
    request = development_request(source, live=True)
    if mutation == "question":
        request["question"] += " Invented changed question."
    elif mutation == "scope":
        request["tickers"] = ["AAPL"]
    elif mutation == "admission":
        request["development_admission"]["admission_hash"] = "f" * 64
    elif mutation == "private_memory":
        request["memory_enabled"] = True
    else:
        request["learning_split"] = "final"
    engine.model_client = FakeModelClient()
    run = engine.execute(store.create_run(request)["id"])
    assert run["status"] == "error" and engine.model_client.calls == [] and calls == []
    assert store.notes() == []


def test_legacy_checkpoint_without_lesson_metadata_can_resume(fixture):
    engine, store, _, _, caller, tmp_path = fixture
    plan = start(engine, store)
    config = {"configurable": {"thread_id": plan["id"]}}
    snapshot = engine.graph.get_state(config)
    legacy_plan = deepcopy(snapshot.values["plan"])
    legacy_plan.pop("lesson_context")
    engine.graph.update_state(config, {"plan": legacy_plan, "lesson_context": None})
    run = store.get_run(plan["id"])
    run.pop("lesson_context")
    run["plan"] = legacy_plan
    run["pending"] = {"kind": "plan", "payload": legacy_plan, "payload_hash": canonical_hash(legacy_plan)}
    store.save_run(run)
    second = Engine(store, engine.source, tmp_path / "runtime", caller=caller)
    try:
        note = decide(second, second.view(plan["id"]))
        assert note["status"] == "awaiting_note", note.get("error")
        assert "lesson_context" not in note["draft"] and verify_draft(note["draft"], engine.source)["passed"]
    finally:
        second.close()


def reflection_event():
    return {"event_kind": "critic_reject", "failure_codes": ["unsupported_claim"],
            "scope": {"tickers": ["MSFT"], "years": [2025]}}


def test_reflection_uses_typed_allowlisted_writer_output_and_stays_unreviewed():
    seen = []
    def model(stage, **request):
        seen.append((stage, request))
        return {"action": "cite_exact_evidence", "summary": "A fictional source check needs review.",
                "applicability": "Apply only when this scoped evidence is available.",
                "counterexamples": "Do not infer a claim from unrelated quoted text."}
    result = Reasoner(model).reflect_lesson(reflection_event(), ACTION_HINTS)
    assert result["human_review_required"] is True and result["reflection_method"] == "model_assisted_unreviewed"
    assert seen[0][0] == "writer"
    assert seen[0][1]["schema"]["properties"]["action"]["enum"] == sorted(ACTION_HINTS)
    assert set(seen[0][1]["context"]) == {"event", "action_options"}
    assert "tools" not in seen[0][1]


@pytest.mark.parametrize("mutation", ["raw_body", "raw_question", "private_scope", "free_text_code"])
def test_reflection_rejects_private_or_free_form_context_before_model(mutation):
    event, calls = reflection_event(), []
    if mutation == "raw_body":
        event["body"] = PRIVATE_PROPOSAL
    elif mutation == "raw_question":
        event["question"] = PRIVATE_PROPOSAL
    elif mutation == "private_scope":
        event["scope"]["tickers"] = ["GOOGL"]
    else:
        event["failure_codes"] = [PRIVATE_PROPOSAL]
    with pytest.raises(ReasoningError):
        Reasoner(lambda *args, **kwargs: calls.append(args)).reflect_lesson(event, ACTION_HINTS)
    assert calls == []


def test_reflection_cannot_select_an_arbitrary_action_even_if_gateway_ignores_schema():
    def model(*args, **kwargs):
        return {"action": "publish_without_review", "summary": "Invented disallowed action proposal.",
                "applicability": "Invented disallowed applicability.", "counterexamples": "Invented disallowed counterexample."}
    with pytest.raises(ReasoningError, match="outside"):
        Reasoner(model).reflect_lesson(reflection_event(), ACTION_HINTS)
