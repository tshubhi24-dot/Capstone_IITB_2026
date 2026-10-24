"""Fictional development failures and fixture reviews, never human-review evidence."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import sqlite3
import threading

import pytest

from desk.development import admit_development, public_cases
from desk.lessons import (ACTION_HINTS, MAX_PLAYBOOKS, MAX_PROPOSALS, LessonConflict, LessonStore,
                          model_lesson_hints, validate_lesson_snapshot, validate_lesson_structure)
from desk.memory import MemoryStore
from desk.store import Store, canonical_hash


class PublicSourceFixture:
    fingerprint = "a" * 64
    def years(self, ticker):
        return [2023, 2024, 2025]


@pytest.fixture
def fixture(tmp_path):
    portal = Store(tmp_path / "portal.sqlite", secret="fictional-publication-secret-" * 3)
    memory = MemoryStore(portal.path, clock=lambda: 1000)
    lessons = LessonStore(memory, portal)
    case = public_cases()[0]
    request = admit_development({"question": case["question"], "tickers": case["tickers"], "years": case["years"],
                                 "learning_split": "development", "development_case_id": case["case_id"],
                                 "memory_enabled": False}, PublicSourceFixture())
    run = portal.create_run(request)
    run.update(source_fingerprint=PublicSourceFixture.fingerprint, status="error")
    portal.save_run(run)
    event = portal.event(run["id"], "critic", "critic_reject", "Invented fixture failure; no live model ran.",
                         {"passed": False, "draft_hash": "b" * 64, "body_hash": "c" * 64,
                          "source_fingerprint": PublicSourceFixture.fingerprint})
    scope = {"tickers": case["tickers"], "years": case["years"], "stages": ["planner", "researcher", "risk", "writer"]}
    yield lessons, memory, portal, run, event, scope
    memory.close()


def propose(fixture, **changes):
    lessons, _, _, run, event, scope = fixture
    values = {"run_id": run["id"], "event_id": event["id"], "action": "cite_exact_evidence", "scope": scope,
              "summary": "Invented test-only proposal summary.", "applicability": "Fictional fixture applicability.",
              "counterexamples": "Fictional fixture counterexample; no real review is claimed.",
              "expected_revision": lessons.get_bank()["revision"]}
    values.update(changes)
    return lessons.propose(**values)


def accept(fixture, proposal):
    lessons = fixture[0]
    return lessons.decide(proposal["lesson_id"], proposal_hash=proposal["proposal_hash"], decision="accept",
                           reason="Fictional fixture acceptance, not a human decision.",
                           expected_revision=lessons.get_bank()["revision"])


def playbook(fixture, proposals=None):
    lessons = fixture[0]
    proposals = [propose(fixture)] if proposals is None else proposals
    for proposal in proposals:
        accept(fixture, proposal)
    return lessons.freeze_playbook([proposal["lesson_id"] for proposal in proposals], expected_revision=lessons.get_bank()["revision"])


def context(fixture, book):
    lessons, _, _, _, _, scope = fixture
    return lessons.freeze_context(scope={key: scope[key] for key in ("tickers", "years")},
                                   source_fingerprint=PublicSourceFixture.fingerprint, enabled=True, playbook_id=book["id"])


def checked(fixture, snapshot):
    with fixture[2].connection() as db:
        return validate_lesson_snapshot(db, "local-analyst", snapshot, PublicSourceFixture.fingerprint,
                                        snapshot["selection_scope"])


def rehash(snapshot):
    snapshot["fingerprint"] = canonical_hash({key: value for key, value in snapshot.items() if key != "fingerprint"})
    return snapshot


def test_pending_proposals_cannot_be_reused_without_an_exact_human_decision(fixture):
    lessons, memory, _, run, event, _ = fixture
    before = lessons.get_bank()
    assert before == {"revision": 0, "revocation_revision": 0, "proposal_ids": [], "playbook_ids": []}
    proposal = propose(fixture)
    assert proposal["status"] == "pending" and proposal["decision"] is None
    assert proposal["origin"]["event_hash"] == canonical_hash(event)
    assert proposal["origin"]["run_id"] == run["id"]
    assert run["request"]["question"] not in json.dumps(proposal)
    with pytest.raises(LessonConflict, match="accepted"):
        lessons.freeze_playbook([proposal["lesson_id"]], expected_revision=1)
    assert lessons.get_bank()["revision"] == 1
    assert memory.langgraph_store.get(("analyst", "local-analyst", "lessons"), proposal["lesson_id"]).value["proposal_hash"] == proposal["proposal_hash"]


def test_exact_review_freezes_real_store_versions_and_only_fixed_model_hints(fixture):
    lessons = fixture[0]
    proposal = propose(fixture)
    with pytest.raises(LessonConflict):
        lessons.decide(proposal["lesson_id"], proposal_hash="f" * 64, decision="accept", reason="Fictional review", expected_revision=1)
    accepted = accept(fixture, proposal)
    assert accepted["status"] == "accepted" and accepted["decision"]["proposal_hash"] == proposal["proposal_hash"]
    book = lessons.freeze_playbook([proposal["lesson_id"]], expected_revision=2)
    assert len(book["id"]) == len(book["hash"]) == 64 and lessons.get_playbook(book["id"]) == book
    frozen = context(fixture, book)
    assert checked(fixture, frozen)
    assert model_lesson_hints(frozen, "writer") == [ACTION_HINTS["cite_exact_evidence"]]
    assert model_lesson_hints(frozen, "critic") == []
    hints = json.dumps(model_lesson_hints(frozen, "writer"))
    assert proposal["summary"] not in hints and proposal["proposal_hash"] not in hints and proposal["lesson_id"] not in hints


def test_rejected_proposals_retain_reasons_and_cannot_enter_playbooks(fixture):
    lessons = fixture[0]
    proposal = propose(fixture)
    rejected = lessons.decide(proposal["lesson_id"], proposal_hash=proposal["proposal_hash"], decision="reject",
                               reason="Fictional fixture rejection: counterexample defeats the proposed applicability.", expected_revision=1)
    assert rejected["status"] == "rejected" and "counterexample" in rejected["decision"]["reason"]
    with pytest.raises(LessonConflict):
        lessons.freeze_playbook([proposal["lesson_id"]], expected_revision=2)
    with pytest.raises(LessonConflict):
        lessons.decide(proposal["lesson_id"], proposal_hash=proposal["proposal_hash"], decision="accept",
                       reason="A different fictional review", expected_revision=2)
    with pytest.raises(LessonConflict):
        propose(fixture, supersedes=proposal["lesson_id"], summary="A rejected proposal cannot be silently revised.")
    replacement = propose(fixture, summary="A separate new invented hypothesis after rejection.")
    assert replacement["lesson_id"] != proposal["lesson_id"] and replacement["supersedes"] is None
    assert lessons.get_lesson(proposal["lesson_id"]) == rejected and replacement["status"] == "pending"


def test_pending_revision_supersedes_old_exact_review_and_prevents_forks(fixture):
    lessons = fixture[0]
    original = propose(fixture)
    revised = propose(fixture, supersedes=original["lesson_id"], summary="Revised fictional fixture applicability.")
    old = lessons.get_lesson(original["lesson_id"])
    assert old["status"] == "superseded" and old["supersession"]["superseded_by"] == revised["lesson_id"]
    assert revised["origin"] == original["origin"] and revised["status"] == "pending"
    with pytest.raises(LessonConflict): accept(fixture, original)
    with pytest.raises(LessonConflict): propose(fixture, supersedes=original["lesson_id"])
    assert accept(fixture, revised)["status"] == "accepted"
    with pytest.raises(LessonConflict): propose(fixture, supersedes=revised["lesson_id"])


def test_revision_cannot_relabel_a_different_persisted_development_event(fixture):
    _, _, portal, run, _, _ = fixture
    original = propose(fixture)
    different = portal.event(run["id"], "critic", "critic_reject", "Different fictional fixture failure", {
        "passed": False, "draft_hash": "d" * 64, "body_hash": "e" * 64, "source_fingerprint": PublicSourceFixture.fingerprint})
    with pytest.raises(LessonConflict, match="same development evidence"):
        propose(fixture, supersedes=original["lesson_id"], event_id=different["id"])


@pytest.mark.parametrize("mutation", ["production", "unknown_case", "question", "source", "admission", "foreign_actor"])
def test_only_persisted_registered_development_origins_can_propose(fixture, mutation):
    lessons, _, portal, run, _, _ = fixture
    changed = deepcopy(run)
    if mutation == "production": changed["request"]["learning_split"] = "production"
    elif mutation == "unknown_case": changed["request"]["development_case_id"] = "FINAL001"
    elif mutation == "question": changed["request"]["question"] = "An invented question outside the public registry."
    elif mutation == "source": changed["source_fingerprint"] = "d" * 64
    elif mutation == "admission": changed["request"]["development_admission"]["admission_hash"] = "e" * 64
    else: changed["actor"] = "other-analyst"
    portal.save_run(changed)
    with pytest.raises(ValueError): propose(fixture)
    assert lessons.get_bank()["revision"] == 0 and lessons.list_lessons() == []


@pytest.mark.parametrize("agent,stage,details", [
    ("critic", "critic_pass", {"passed": True}), ("planner", "plan", {}),
    ("human", "plan_edit", {}), ("critic", "critic_reject", {"passed": True}),
    ("critic", "critic_reject", {"passed": False}),
])
def test_ineligible_or_unproven_events_cannot_be_promoted(fixture, agent, stage, details):
    _, _, portal, run, _, _ = fixture
    event = portal.event(run["id"], agent, stage, "Invented ineligible fixture event", details)
    with pytest.raises(ValueError): propose(fixture, event_id=event["id"])


def test_actual_recorded_note_edit_hashes_are_eligible_but_noop_edit_is_not(fixture):
    lessons, _, portal, run, _, _ = fixture
    details = {"source_fingerprint": PublicSourceFixture.fingerprint, "before_draft_hash": "b" * 64,
               "before_body_hash": "c" * 64, "after_body_hash": "d" * 64}
    event = portal.event(run["id"], "human", "note_edit", "Invented fixture human edit", details)
    proposal = propose(fixture, event_id=event["id"])
    assert proposal["origin"]["event_kind"] == "note_edit"
    same = portal.event(run["id"], "human", "note_edit", "Invented unchanged edit", {**details, "after_body_hash": details["before_body_hash"]})
    with pytest.raises(ValueError, match="did not change"):
        propose(fixture, event_id=same["id"])
    assert lessons.validate_origin(run["id"], event["id"])["event_hash"] == canonical_hash(event)


def test_decision_revalidates_original_event_instead_of_trusting_proposal_prose(fixture):
    lessons, _, portal, _, event, _ = fixture
    proposal = propose(fixture)
    with portal.connection() as db:
        row = db.execute("SELECT data FROM events WHERE id=?", (event["id"],)).fetchone()
        changed = json.loads(row[0]); changed["message"] = "Invented event was changed after proposal"
        db.execute("UPDATE events SET data=? WHERE id=?", (json.dumps(changed), event["id"]))
    with pytest.raises(LessonConflict, match="evidence changed"):
        accept(fixture, proposal)
    assert lessons.get_lesson(proposal["lesson_id"])["status"] == "pending"


@pytest.mark.parametrize("field,value", [("summary", "x" * 601), ("counterexamples", ""), ("action", "ignore_checks"),
                                         ("scope", {"tickers": ["MSFT"], "years": [2025], "stages": ["critic"]})])
def test_bounded_typed_actions_and_local_explanations(fixture, field, value):
    with pytest.raises(ValueError): propose(fixture, **{field: value})


def test_obvious_credentials_are_rejected_without_saving_them(fixture):
    with pytest.raises(ValueError, match="credentials"):
        propose(fixture, summary="sk-" + "x" * 40)
    assert fixture[0].get_bank()["proposal_ids"] == []


def test_disabled_learning_reads_and_writes_no_lesson_bank(fixture, monkeypatch):
    lessons, _, portal, _, _, scope = fixture
    monkeypatch.setattr(lessons, "_get", lambda *args: pytest.fail("Disabled lessons must not read the bank"))
    monkeypatch.setattr(portal, "connection", lambda *args: pytest.fail("Disabled lessons need no database connection"))
    frozen = lessons.freeze_context(scope={key: scope[key] for key in ("tickers", "years")},
                                    source_fingerprint=PublicSourceFixture.fingerprint, enabled=False)
    assert frozen["lesson_refs"] == [] and model_lesson_hints(frozen, "writer") == []
    db = sqlite3.connect(":memory:")
    try: assert validate_lesson_snapshot(db, "local-analyst", frozen)
    finally: db.close()


def test_actor_source_and_scope_binding_cannot_be_forged(fixture):
    lessons = fixture[0]
    book = playbook(fixture)
    frozen = context(fixture, book)
    assert lessons.get_playbook(book["id"], "other-analyst") is None
    assert lessons.get_lesson(frozen["lesson_refs"][0]["lesson_id"], "other-analyst") is None
    with fixture[2].connection() as db:
        for changes in ({"actor": "other-analyst"}, {"source_fingerprint": "d" * 64},
                        {"selection_scope": {"tickers": ["UNH"], "years": [2025]}}):
            with pytest.raises(ValueError):
                validate_lesson_snapshot(db, "local-analyst", rehash({**frozen, **changes}), PublicSourceFixture.fingerprint)


def test_rehashed_action_or_acceptance_reference_cannot_override_persisted_review(fixture):
    book = playbook(fixture)
    frozen = context(fixture, book)
    for field, value in (("action", "verify_current_facts"), ("decision_hash", "f" * 64), ("proposal_hash", "e" * 64)):
        forged = deepcopy(frozen); forged["lesson_refs"][0][field] = value
        with pytest.raises(LessonConflict): checked(fixture, rehash(forged))
    forged = deepcopy(frozen); forged["lesson_refs"][0]["arbitrary_instruction"] = "Invented unsafe extra field"
    with pytest.raises(LessonConflict): validate_lesson_structure(rehash(forged))


def test_unrelated_pending_rejected_and_accepted_lessons_do_not_change_frozen_context(fixture):
    lessons = fixture[0]
    frozen = context(fixture, playbook(fixture))
    pending = propose(fixture, action="align_fiscal_periods")
    assert checked(fixture, frozen)
    lessons.decide(pending["lesson_id"], proposal_hash=pending["proposal_hash"], decision="reject",
                   reason="Fictional fixture rejection", expected_revision=lessons.get_bank()["revision"])
    assert checked(fixture, frozen)
    accept(fixture, propose(fixture, action="verify_current_facts"))
    assert checked(fixture, frozen)


def test_selected_revocation_invalidates_old_context_but_preserves_immutable_playbook(fixture):
    lessons = fixture[0]
    book = playbook(fixture)
    frozen = context(fixture, book)
    ref = frozen["lesson_refs"][0]
    revoked = lessons.revoke(ref["lesson_id"], proposal_hash=ref["proposal_hash"], reason="Fictional fixture revocation",
                             expected_revision=lessons.get_bank()["revision"])
    assert revoked["status"] == "revoked" and lessons.get_playbook(book["id"]) == book
    with pytest.raises(LessonConflict, match="revoked"):
        checked(fixture, frozen)
    fresh = context(fixture, book)
    assert fresh["lesson_refs"] == [] and checked(fixture, fresh)


def test_three_deterministic_relevant_actions_and_stage_selection(fixture):
    proposals = [propose(fixture, action=action) for action in ACTION_HINTS]
    book = playbook(fixture, proposals)
    frozen = context(fixture, book)
    assert len(frozen["lesson_refs"]) == 3
    assert len(model_lesson_hints(frozen, "writer")) == 3
    unused = next(row for row in proposals if row["lesson_id"] not in {ref["lesson_id"] for ref in frozen["lesson_refs"]})
    lessons = fixture[0]
    lessons.revoke(unused["lesson_id"], proposal_hash=unused["proposal_hash"], reason="Fictional unrelated revocation",
                   expected_revision=lessons.get_bank()["revision"])
    assert checked(fixture, frozen)


def test_nonapplicable_scope_and_stage_produce_no_hint(fixture):
    scope = deepcopy(fixture[-1]); scope["stages"] = ["risk"]
    book = playbook(fixture, [propose(fixture, scope=scope, action="preserve_risk_qualifiers")])
    frozen = context(fixture, book)
    assert model_lesson_hints(frozen, "writer") == []
    assert model_lesson_hints(frozen, "risk") == [ACTION_HINTS["preserve_risk_qualifiers"]]
    other = fixture[0].freeze_context(scope={"tickers": ["UNH"], "years": [2025]},
                                     source_fingerprint=PublicSourceFixture.fingerprint, enabled=True, playbook_id=book["id"])
    assert other["lesson_refs"] == []


def test_restart_persists_proposals_review_playbook_and_revocation(fixture):
    lessons, memory, portal, _, _, _ = fixture
    book = playbook(fixture); frozen = context(fixture, book)
    reopened = MemoryStore(memory.path)
    try:
        restarted = LessonStore(reopened, portal)
        assert restarted.get_playbook(book["id"]) == book
        assert restarted.get_lesson(frozen["lesson_refs"][0]["lesson_id"])["status"] == "accepted"
        ref = frozen["lesson_refs"][0]
        restarted.revoke(ref["lesson_id"], proposal_hash=ref["proposal_hash"], reason="Fictional restart revocation",
                          expected_revision=restarted.get_bank()["revision"])
        with pytest.raises(LessonConflict): checked(fixture, frozen)
    finally: reopened.close()


def test_same_bank_revision_allows_only_one_concurrent_proposal(fixture):
    lessons, memory, portal, _, _, _ = fixture
    other_memory = MemoryStore(memory.path)
    other = LessonStore(other_memory, portal)
    barrier = threading.Barrier(2)
    def write(instance):
        barrier.wait(timeout=5)
        values = list(fixture); values[0] = instance
        try: return propose(values, expected_revision=0)["lesson_id"]
        except LessonConflict: return "stale"
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(write, instance) for instance in (lessons, other)]
            results = [future.result(timeout=10) for future in futures]
        assert results.count("stale") == 1 and len(lessons.list_lessons()) == 1
    finally: other_memory.close()


def test_publisher_validation_does_not_commit_or_write_and_serializes_revocation(fixture):
    lessons, _, portal, _, _, _ = fixture
    book = playbook(fixture); frozen = context(fixture, book); ref = frozen["lesson_refs"][0]
    started = threading.Event()
    def revoke():
        started.set()
        return lessons.revoke(ref["lesson_id"], proposal_hash=ref["proposal_hash"], reason="Fictional concurrent revocation",
                              expected_revision=lessons.get_bank()["revision"])
    with portal.connection() as db:
        db.execute("BEGIN IMMEDIATE"); before = db.total_changes
        assert validate_lesson_snapshot(db, "local-analyst", frozen)
        assert db.in_transaction and db.total_changes == before
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(revoke)
            assert started.wait(timeout=5) and not future.done()
            db.commit()
            assert future.result(timeout=5)["status"] == "revoked"
    with pytest.raises(LessonConflict): checked(fixture, frozen)


def test_proposal_and_playbook_counts_have_finite_limits(fixture):
    lessons, memory, _, _, _, _ = fixture
    bank = lessons.get_bank(); bank["proposal_ids"] = [f"{index:032x}" for index in range(MAX_PROPOSALS)]
    memory.langgraph_store.put(("analyst", "local-analyst", "lesson-bank"), "bank", bank)
    with pytest.raises(ValueError, match="proposal limit"): propose(fixture)
    bank["proposal_ids"] = []; memory.langgraph_store.put(("analyst", "local-analyst", "lesson-bank"), "bank", bank)
    proposal = propose(fixture); accept(fixture, proposal)
    bank = lessons.get_bank(); bank["playbook_ids"] = [f"{index:064x}" for index in range(MAX_PLAYBOOKS)]
    memory.langgraph_store.put(("analyst", "local-analyst", "lesson-bank"), "bank", bank)
    with pytest.raises(ValueError, match="playbook limit"):
        lessons.freeze_playbook([proposal["lesson_id"]], expected_revision=bank["revision"])
