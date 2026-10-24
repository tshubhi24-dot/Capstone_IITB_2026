"""Verify synthetic lessons in a separate operator database, never analyst memory.

Synthetic decisions exercise software behavior and do not satisfy genuine
human-review or independent E3 evidence. No model or provider is contacted.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desk.data import Corpus
from desk.development import admit_development, public_cases
from desk.lessons import ACTION_HINTS, LessonConflict, LessonStore, model_lesson_hints, validate_lesson_snapshot
from desk.memory import MemoryStore
from desk.store import Store, canonical_hash

ACTOR = "lesson-operator-fixture"
FIXTURE_KIND = "synthetic_operator_fixture_not_human_learning_evidence"


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".lessons-receipt-", delete=False) as handle:
            stage = Path(handle.name)
            handle.write((json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
            handle.flush(); os.fsync(handle.fileno())
        stage.replace(path)
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)


def _rejected(operation):
    try:
        operation()
    except (ValueError, LessonConflict):
        return True
    return False


def verify(phase, *, runtime_dir=None, corpus_path=None):
    if phase not in {"prepare", "inspect", "cleanup"}:
        raise ValueError("Choose a declared lesson-verification phase.")
    runtime = Path(runtime_dir or os.getenv("RUNTIME_DIR", "/runtime")).resolve()
    directory = runtime / "lesson-operator"
    if directory.is_symlink():
        raise ValueError("The isolated lesson operator directory must not be a symlink.")
    database, state_file = directory / "portal.sqlite", directory / "fixture.json"
    real_database = runtime / "portal.sqlite"
    same_file = database.is_file() and real_database.is_file() and database.samefile(real_database)
    if database.is_symlink() or state_file.is_symlink() or database.resolve() == real_database.resolve() or same_file:
        raise ValueError("The verifier must not use the real analyst database.")
    if phase != "prepare" and (not database.is_file() or not state_file.is_file()):
        raise ValueError("Prepare the separate synthetic lesson fixture before inspection or cleanup.")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    corpus = Corpus(corpus_path or os.getenv("CORPUS_PATH", "/sources/corpus.json"))
    portal = Store(database, secret="synthetic-operator-signing-only-" * 3)
    memory = MemoryStore(database)
    lessons = LessonStore(memory, portal)
    checks, synthetic_decisions = [], 0
    def record(name, passed):
        checks.append({"name": name, "passed": bool(passed)})
    def validate(snapshot):
        with portal.connection() as db:
            return validate_lesson_snapshot(db, ACTOR, snapshot, corpus.fingerprint, snapshot["selection_scope"])
    try:
        state = json.loads(state_file.read_text()) if state_file.is_file() else None
        if state is not None and (state.get("fixture_kind") != FIXTURE_KIND or state.get("actor") != ACTOR):
            raise ValueError("The operator fixture identity is invalid.")
        if phase == "prepare" and (state is None or state.get("cleaned") is True):
            case = next(row for row in public_cases(corpus) if row["case_id"] == "KDEV001")
            if not case["available"]:
                raise ValueError("The registered public fixture case is unavailable in this source snapshot.")
            request = admit_development({"question": case["question"], "tickers": case["tickers"], "years": case["years"],
                                         "learning_split": "development", "development_case_id": case["case_id"],
                                         "memory_enabled": False, "mode": "offline"}, corpus)
            run = portal.create_run(request, actor=ACTOR)
            draft = {"run_id": run["id"], "actor": ACTOR, "body": "Declared synthetic operator draft; no research quality claim.",
                     "source_fingerprint": corpus.fingerprint}
            run.update(source_fingerprint=corpus.fingerprint, status="error", draft=draft, fixture_kind=FIXTURE_KIND)
            portal.save_run(run)
            event = portal.event(run["id"], "critic", "critic_reject", "Declared synthetic operator critic failure; no model ran.",
                                 {"passed": False, "draft_hash": canonical_hash(draft), "body_hash": hashlib.sha256(draft["body"].encode()).hexdigest(),
                                  "source_fingerprint": corpus.fingerprint})
            scope = {"tickers": case["tickers"], "years": case["years"], "stages": ["planner", "researcher", "risk", "writer"]}
            values = {"actor": ACTOR, "run_id": run["id"], "event_id": event["id"], "scope": scope,
                      "summary": "Synthetic operator proposal, not a real analyst lesson.",
                      "applicability": "Only a declared synthetic software verification fixture.",
                      "counterexamples": "No independent research-quality benefit is established by this fixture."}
            accepted = lessons.propose(**values, action="cite_exact_evidence", expected_revision=lessons.get_bank(ACTOR)["revision"])
            record("pending_lesson_cannot_be_frozen", _rejected(lambda: lessons.freeze_playbook([accepted["lesson_id"]], actor=ACTOR,
                                                                                              expected_revision=lessons.get_bank(ACTOR)["revision"])))
            accepted = lessons.decide(accepted["lesson_id"], actor=ACTOR, proposal_hash=accepted["proposal_hash"], decision="accept",
                                       reason="Synthetic fixture acceptance; no genuine human review is claimed.",
                                       expected_revision=lessons.get_bank(ACTOR)["revision"])
            rejected = lessons.propose(**values, action="verify_current_facts", expected_revision=lessons.get_bank(ACTOR)["revision"])
            rejected = lessons.decide(rejected["lesson_id"], actor=ACTOR, proposal_hash=rejected["proposal_hash"], decision="reject",
                                       reason="Synthetic fixture rejection; it does not satisfy genuine rejected-lesson evidence.",
                                       expected_revision=lessons.get_bank(ACTOR)["revision"])
            synthetic_decisions = 2
            book = lessons.freeze_playbook([accepted["lesson_id"]], actor=ACTOR, expected_revision=lessons.get_bank(ACTOR)["revision"])
            snapshot = lessons.freeze_context(actor=ACTOR, scope={key: scope[key] for key in ("tickers", "years")},
                                               source_fingerprint=corpus.fingerprint, enabled=True, playbook_id=book["id"])
            state = {"fixture_kind": FIXTURE_KIND, "actor": ACTOR, "source_fingerprint": corpus.fingerprint,
                     "run_id": run["id"], "event_id": event["id"], "accepted_id": accepted["lesson_id"],
                     "rejected_id": rejected["lesson_id"], "playbook_id": book["id"], "snapshot": snapshot, "cleaned": False}
            atomic_json(state_file, state)
        if state is None or state["source_fingerprint"] != corpus.fingerprint:
            raise ValueError("The isolated fixture source changed; preserve and inspect its recorded state.")
        accepted = lessons.get_lesson(state["accepted_id"], ACTOR)
        rejected = lessons.get_lesson(state["rejected_id"], ACTOR)
        book = lessons.get_playbook(state["playbook_id"], ACTOR)
        snapshot = state["snapshot"]
        record("operator_database_is_separate", database.resolve() != (runtime / "portal.sqlite").resolve())
        record("registered_development_proof_persisted", lessons.validate_origin(state["run_id"], state["event_id"], ACTOR)["source_fingerprint"] == corpus.fingerprint)
        record("rejection_is_explicit_and_retained", rejected["status"] == "rejected" and rejected["decision"]["decision"] == "reject")
        record("playbook_contains_only_fixture_accepted_version", [ref["lesson_id"] for ref in book["lesson_refs"]] == [state["accepted_id"]])
        record("rejected_proposal_cannot_enter_playbook", _rejected(lambda: lessons.freeze_playbook([state["rejected_id"]], actor=ACTOR,
                                                                                                 expected_revision=lessons.get_bank(ACTOR)["revision"])))
        if phase == "cleanup":
            if accepted["status"] == "accepted":
                lessons.revoke(accepted["lesson_id"], actor=ACTOR, proposal_hash=accepted["proposal_hash"],
                                reason="Synthetic operator fixture cleanup; no real lesson or human decision is changed.",
                                expected_revision=lessons.get_bank(ACTOR)["revision"])
                synthetic_decisions = 1
            record("only_fixture_acceptance_revoked", lessons.get_lesson(state["accepted_id"], ACTOR)["status"] == "revoked")
            record("old_fixture_context_blocked_after_revocation", _rejected(lambda: validate(snapshot)))
            record("immutable_fixture_audit_retained", lessons.get_playbook(state["playbook_id"], ACTOR) == book and rejected["status"] == "rejected")
            state["cleaned"] = True; atomic_json(state_file, state)
        else:
            if state.get("cleaned"):
                raise ValueError("The isolated fixture was already cleaned; prepare a new synthetic batch.")
            record("accepted_context_survives_reload", accepted["status"] == "accepted" and validate(snapshot))
            record("only_fixed_public_checklist_reaches_producer", model_lesson_hints(snapshot, "writer") == [ACTION_HINTS["cite_exact_evidence"]])
            record("critic_receives_no_learning_hints", model_lesson_hints(snapshot, "critic") == [])
            wrong = deepcopy(snapshot); wrong["source_fingerprint"] = "0" * 64
            wrong["fingerprint"] = canonical_hash({key: value for key, value in wrong.items() if key != "fingerprint"})
            record("changed_source_context_is_blocked", _rejected(lambda: validate(wrong)))
            wrong = deepcopy(snapshot); wrong["selection_scope"]["years"] = [1900]
            wrong["fingerprint"] = canonical_hash({key: value for key, value in wrong.items() if key != "fingerprint"})
            record("changed_scope_context_is_blocked", _rejected(lambda: validate(wrong)))
            queries = []
            memory.conn.set_trace_callback(queries.append)
            try:
                off = lessons.freeze_context(actor=ACTOR, scope=snapshot["selection_scope"], source_fingerprint=corpus.fingerprint, enabled=False)
            finally:
                memory.conn.set_trace_callback(None)
            record("lessons_off_reads_no_lesson_bank", off["lesson_refs"] == [] and not queries)
        record("real_analyst_namespace_absent_from_isolated_database", portal.list_runs("local-analyst") == [] and lessons.get_bank("local-analyst")["revision"] == 0)
        record("no_notes_published_by_fixture", portal.notes(ACTOR) == [] and portal.notes("local-analyst") == [])
        return {"verification_kind": "isolated_lessons_runtime", "fixture_kind": FIXTURE_KIND, "phase": phase,
                "status": "passed" if all(row["passed"] for row in checks) else "failed", "checks": checks,
                "checks_passed": sum(row["passed"] for row in checks), "checks_total": len(checks),
                "source_fingerprint": corpus.fingerprint, "company_count": len(corpus.companies()),
                "synthetic_decisions": synthetic_decisions, "human_decisions_submitted": 0,
                "generative_model_calls": 0, "external_provider_requests": 0, "real_research_runs_created": 0,
                "real_notes_published": 0, "real_analyst_namespace_touched": False,
                "limitations": ["Synthetic operator decisions demonstrate software behavior only.",
                                "No genuine accepted or rejected lesson, independent E3 comparison or research-quality improvement is established.",
                                "The separate synthetic operator database retains its proposals, decisions and revocation audit."]}
    finally:
        memory.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "inspect", "cleanup"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output:
            isolated = (Path(os.getenv("RUNTIME_DIR", "/runtime")) / "lesson-operator").resolve()
            output = args.output.resolve()
            if (args.output.is_symlink() or not output.is_relative_to(isolated) or output.suffix != ".json"
                    or output.name == "fixture.json"):
                raise ValueError("Receipts must be JSON files inside the isolated lesson-operator directory.")
        receipt = verify(args.phase)
        if args.output:
            atomic_json(args.output, receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        raise SystemExit(0 if receipt["status"] == "passed" else 1)
    except (ValueError, OSError, sqlite3.Error) as error:
        print("Isolated lesson verification stopped: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
