"""Explicit development lessons, exact human decisions and frozen scoped reuse.

Only fixed checklist strings can reach producing models. Proposal and review
prose stays local; no method automatically accepts a lesson or publishes a note.
"""
from copy import deepcopy
import json
import re
import sqlite3
import uuid

from .memory import MemoryConflict, _actor, _namespace, _revision
from .store import canonical_hash


ACTION_HINTS = {
    "align_fiscal_periods": "Check actual fiscal start and end dates before comparing companies or years; state calendar differences explicitly.",
    "verify_current_facts": "Use the current canonical SEC fact identifiers and independently verified arithmetic; historical notes are context only.",
    "preserve_risk_qualifiers": "Preserve the source's uncertainty, conditions and negation; selected excerpts cannot establish a new, absent or removed risk.",
    "cite_exact_evidence": "Attach the exact approved-scope evidence identifiers to each claim and verify that the cited text supports its wording.",
}
STAGES = {"planner", "researcher", "risk", "writer"}
MAX_PROPOSALS, MAX_PLAYBOOKS, MAX_PLAYBOOK_LESSONS, MAX_SELECTED = 256, 64, 16, 3
HEX32, HEX64 = re.compile(r"[0-9a-f]{32}\Z"), re.compile(r"[0-9a-f]{64}\Z")
SECRET = re.compile(r"(?i)(?:sk-[A-Za-z0-9_-]{12,}|bearer\s+\S+|-----BEGIN [A-Z ]*PRIVATE KEY|(?:api[_ -]?key|password|secret)\s*[:=]\s*\S+)")
REF_FIELDS = {"lesson_id", "proposal_hash", "decision_hash", "action", "scope"}
SNAPSHOT_FIELDS = {"enabled", "actor", "source_fingerprint", "selection_scope", "playbook_id", "playbook_hash",
                   "bank_revision", "revocation_revision", "lesson_refs", "fingerprint"}


class LessonConflict(MemoryConflict):
    pass


def _text(value):
    if (not isinstance(value, str) or not 1 <= len(value.strip()) <= 600 or SECRET.search(value)
            or any(ord(char) < 32 and char not in "\n\t" for char in value)):
        raise ValueError("Lesson explanations require bounded local text without credentials or control characters.")
    return value.strip()


def _hex(value, pattern=HEX64):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError("A canonical lesson identifier or fingerprint is required.")
    return value


def _scope(value, *, stages=True):
    expected = {"tickers", "years", "stages"} if stages else {"tickers", "years"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("Lesson applicability requires an explicit company/year scope.")
    tickers, years = value["tickers"], value["years"]
    if (not isinstance(tickers, list) or not 1 <= len(tickers) <= 12
            or any(not isinstance(ticker, str) or not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker) for ticker in tickers)
            or len(set(tickers)) != len(tickers)
            or not isinstance(years, list) or not 1 <= len(years) <= 3
            or any(type(year) is not int or not 1900 <= year <= 2100 for year in years)
            or len(set(years)) != len(years)):
        raise ValueError("Lesson applicability exceeds its company/year bounds.")
    result = {"tickers": sorted(tickers), "years": sorted(years)}
    if stages:
        values = value["stages"]
        if (not isinstance(values, list) or not values or any(not isinstance(stage, str) or stage not in STAGES for stage in values)
                or len(set(values)) != len(values)):
            raise ValueError("Lesson applicability supports only declared producing stages.")
        result["stages"] = sorted(values)
    return result


def _bank(value):
    if value is None:
        return {"revision": 0, "revocation_revision": 0, "proposal_ids": [], "playbook_ids": []}
    try:
        if set(value) != {"revision", "revocation_revision", "proposal_ids", "playbook_ids"}:
            raise ValueError
        _revision(value["revision"]); _revision(value["revocation_revision"])
        for key, maximum, pattern in (("proposal_ids", MAX_PROPOSALS, HEX32), ("playbook_ids", MAX_PLAYBOOKS, HEX64)):
            rows = value[key]
            if (not isinstance(rows, list) or len(rows) > maximum
                    or any(not isinstance(item, str) or not pattern.fullmatch(item) for item in rows)
                    or len(set(rows)) != len(rows)):
                raise ValueError
        return deepcopy(value)
    except (KeyError, TypeError, ValueError) as error:
        raise LessonConflict("The persisted lesson bank is invalid.") from error


def _checked_hash(value, field="hash"):
    if not isinstance(value, dict) or not isinstance(value.get(field), str) or canonical_hash({key: item for key, item in value.items() if key != field}) != value[field]:
        raise LessonConflict("An immutable lesson record changed.")
    return value


def _proposal(value, actor):
    _checked_hash(value, "proposal_hash")
    required = {"lesson_id", "actor", "origin", "action", "scope", "summary", "applicability", "counterexamples",
                "supersedes", "created_at", "created_bank_revision", "proposal_hash"}
    if (set(value) != required or value["actor"] != actor or value["action"] not in ACTION_HINTS
            or _scope(value["scope"]) != value["scope"]):
        raise LessonConflict("The lesson proposal schema or namespace is invalid.")
    _hex(value["lesson_id"], HEX32)
    for field in ("summary", "applicability", "counterexamples"):
        _text(value[field])
    return value


def _decision(value, proposal):
    _checked_hash(value)
    if (value.get("lesson_id") != proposal["lesson_id"] or value.get("proposal_hash") != proposal["proposal_hash"]
            or value.get("actor") != proposal["actor"] or value.get("decision") not in {"accept", "reject"}):
        raise LessonConflict("The human decision does not match the exact proposal.")
    _text(value.get("reason"))
    return value


def _ref(proposal, decision):
    return {"lesson_id": proposal["lesson_id"], "proposal_hash": proposal["proposal_hash"], "decision_hash": decision["hash"],
            "action": proposal["action"], "scope": deepcopy(proposal["scope"])}


def _playbook(value, actor):
    _checked_hash(value)
    if (set(value) != {"id", "hash", "actor", "source_fingerprint", "bank_revision", "revocation_revision", "lesson_refs", "created_at"}
            or value["actor"] != actor or value["id"] != canonical_hash({key: item for key, item in value.items() if key not in {"id", "hash"}})
            or not isinstance(value["lesson_refs"], list) or not 1 <= len(value["lesson_refs"]) <= MAX_PLAYBOOK_LESSONS):
        raise LessonConflict("The frozen playbook is invalid.")
    _hex(value["source_fingerprint"])
    _revision(value["bank_revision"]); _revision(value["revocation_revision"])
    return value


def _relevant(ref, scope):
    return bool(set(ref["scope"]["tickers"]) & set(scope["tickers"]) and set(ref["scope"]["years"]) & set(scope["years"]))


def _selected(refs, scope, revoked):
    chosen, actions = [], set()
    for ref in sorted(refs, key=lambda value: (len(value["scope"]["tickers"]), value["action"], value["lesson_id"])):
        if ref["lesson_id"] not in revoked and ref["action"] not in actions and _relevant(ref, scope):
            chosen.append(deepcopy(ref)); actions.add(ref["action"])
            if len(chosen) == MAX_SELECTED:
                break
    return chosen


class LessonStore:
    def __init__(self, memory, store):
        if memory.path.resolve() != store.path.resolve():
            raise ValueError("Lessons and publication must share the same SQLite database.")
        self.memory, self.store = memory, store

    def _get(self, actor, kind, key):
        return self.memory._get(actor, kind, key)

    def _put(self, actor, kind, key, value):
        self.memory.langgraph_store.put(_namespace(actor, kind), key, value, index=False)

    def get_bank(self, actor="local-analyst"):
        return _bank(self._get(actor, "lesson-bank", "bank"))

    def _current(self, actor, expected_revision):
        bank = self.get_bank(actor)
        if bank["revision"] != _revision(expected_revision):
            raise LessonConflict("The lesson bank changed; reload before reviewing or freezing.")
        return bank

    def _origin(self, actor, run_id, event_id):
        from .development import validate_development_run
        _hex(run_id, HEX32)
        if type(event_id) is not int or event_id < 1:
            raise ValueError("A persisted development event is required.")
        run = self.store.get_run(run_id)
        if not run or run.get("actor") != actor:
            raise ValueError("The development origin is unavailable for this analyst.")
        admission = validate_development_run(run)
        event = next((row for row in self.store.events(run_id) if row["id"] == event_id), None)
        if not event:
            raise ValueError("The recorded development event is unavailable.")
        details = event.get("details", {})
        if details.get("source_fingerprint") != run.get("source_fingerprint"):
            raise ValueError("The development event source identity is unverified.")
        if event.get("agent") == "critic" and event.get("stage") == "critic_reject" and details.get("passed") is False:
            hashes = {key: _hex(details.get(key)) for key in ("draft_hash", "body_hash")}
        elif event.get("agent") == "human" and event.get("stage") == "note_edit":
            hashes = {key: _hex(details.get(key)) for key in ("before_draft_hash", "before_body_hash", "after_body_hash")}
            if hashes["before_body_hash"] == hashes["after_body_hash"]:
                raise ValueError("The development note edit did not change the body.")
        else:
            raise ValueError("Lessons require a failed development critic or a recorded human note edit.")
        return {"run_id": run_id, "event_id": event_id, "event_hash": canonical_hash(event), "event_kind": event["stage"],
                "learning_split": "development", "development_case_id": admission["case_id"],
                "admission_hash": admission["admission_hash"], "source_fingerprint": run["source_fingerprint"], **hashes}

    def validate_origin(self, run_id, event_id, actor="local-analyst"):
        """Read persisted evidence before an optional, separately budgeted reflection."""
        return deepcopy(self._origin(actor, run_id, event_id))

    def propose(self, *, run_id, event_id, action, scope, summary, applicability, counterexamples,
                expected_revision, supersedes=None, actor="local-analyst"):
        _actor(actor)
        if not isinstance(action, str) or action not in ACTION_HINTS:
            raise ValueError("Choose a declared lesson checklist action.")
        scope = _scope(scope)
        texts = {"summary": _text(summary), "applicability": _text(applicability), "counterexamples": _text(counterexamples)}
        with self.memory._transaction():
            bank = self._current(actor, expected_revision)
            if len(bank["proposal_ids"]) >= MAX_PROPOSALS:
                raise ValueError("The bounded lesson-proposal limit has been reached.")
            origin = self._origin(actor, run_id, event_id)
            parent = None
            if supersedes is not None:
                _hex(supersedes, HEX32)
                if supersedes not in bank["proposal_ids"]:
                    raise ValueError("The preceding lesson proposal is unavailable.")
                parent = self.get_lesson(supersedes, actor)
                if parent["status"] != "pending" or parent["origin"] != origin:
                    raise LessonConflict("Only an unsuperseded pending proposal with the same development evidence can be revised.")
            lesson_id = uuid.uuid4().hex
            value = {"lesson_id": lesson_id, "actor": actor, "origin": origin, "action": action, "scope": scope,
                     **texts, "supersedes": supersedes, "created_at": self.memory.clock(), "created_bank_revision": bank["revision"] + 1}
            value["proposal_hash"] = canonical_hash(value)
            self._put(actor, "lessons", lesson_id, value)
            if parent is not None:
                supersession = {"lesson_id": supersedes, "superseded_by": lesson_id, "actor": actor,
                                "parent_proposal_hash": parent["proposal_hash"], "replacement_proposal_hash": value["proposal_hash"],
                                "superseded_at": self.memory.clock(), "bank_revision": bank["revision"] + 1}
                supersession["hash"] = canonical_hash(supersession)
                self._put(actor, "lesson-supersessions", supersedes, supersession)
            bank["proposal_ids"].append(lesson_id); bank["revision"] += 1
            self._put(actor, "lesson-bank", "bank", bank)
        return self.get_lesson(lesson_id, actor)

    def get_lesson(self, lesson_id, actor="local-analyst"):
        _hex(lesson_id, HEX32)
        raw = self._get(actor, "lessons", lesson_id)
        if raw is None:
            return None
        proposal = _proposal(raw, actor)
        decision = self._get(actor, "lesson-decisions", lesson_id)
        revocation = self._get(actor, "lesson-revocations", lesson_id)
        supersession = self._get(actor, "lesson-supersessions", lesson_id)
        if decision is not None:
            _decision(decision, proposal)
        if revocation is not None:
            _checked_hash(revocation)
        if supersession is not None:
            _checked_hash(supersession)
            if (decision is not None or supersession.get("lesson_id") != lesson_id or supersession.get("actor") != actor
                    or supersession.get("parent_proposal_hash") != proposal["proposal_hash"]):
                raise LessonConflict("The immutable proposal supersession is invalid.")
        status = "pending" if decision is None else "accepted" if decision["decision"] == "accept" else "rejected"
        if revocation is not None:
            status = "revoked"
        if supersession is not None:
            status = "superseded"
        return {**deepcopy(proposal), "status": status, "decision": deepcopy(decision), "revocation": deepcopy(revocation),
                "supersession": deepcopy(supersession)}

    def list_lessons(self, actor="local-analyst"):
        return [self.get_lesson(identifier, actor) for identifier in self.get_bank(actor)["proposal_ids"]]

    def decide(self, lesson_id, *, proposal_hash, decision, reason, expected_revision, actor="local-analyst"):
        _hex(lesson_id, HEX32); _hex(proposal_hash)
        if not isinstance(decision, str) or decision not in {"accept", "reject"}:
            raise ValueError("A human must explicitly accept or reject the exact lesson.")
        reason = _text(reason)
        with self.memory._transaction():
            bank = self._current(actor, expected_revision)
            if lesson_id not in bank["proposal_ids"]:
                raise ValueError("The lesson proposal is unavailable.")
            proposal = _proposal(self._get(actor, "lessons", lesson_id), actor)
            if (proposal["proposal_hash"] != proposal_hash or self._get(actor, "lesson-decisions", lesson_id) is not None
                    or self._get(actor, "lesson-supersessions", lesson_id) is not None):
                raise LessonConflict("The proposal changed or already has an immutable human decision.")
            # Recheck the original persisted development proof at decision time.
            if self._origin(actor, proposal["origin"]["run_id"], proposal["origin"]["event_id"]) != proposal["origin"]:
                raise LessonConflict("The lesson's development evidence changed.")
            value = {"lesson_id": lesson_id, "proposal_hash": proposal_hash, "actor": actor, "decision": decision,
                     "reason": reason, "decided_at": self.memory.clock(), "bank_revision": bank["revision"] + 1}
            value["hash"] = canonical_hash(value)
            self._put(actor, "lesson-decisions", lesson_id, value)
            bank["revision"] += 1; self._put(actor, "lesson-bank", "bank", bank)
        return self.get_lesson(lesson_id, actor)

    def revoke(self, lesson_id, *, proposal_hash, reason, expected_revision, actor="local-analyst"):
        reason = _text(reason); _hex(lesson_id, HEX32); _hex(proposal_hash)
        with self.memory._transaction():
            bank = self._current(actor, expected_revision)
            value = self.get_lesson(lesson_id, actor)
            if not value or value["status"] != "accepted" or value["proposal_hash"] != proposal_hash:
                raise LessonConflict("Only the exact accepted, unrevoked lesson can be revoked.")
            revocation = {"lesson_id": lesson_id, "proposal_hash": proposal_hash, "actor": actor, "reason": reason,
                          "revoked_at": self.memory.clock(), "bank_revision": bank["revision"] + 1,
                          "revocation_revision": bank["revocation_revision"] + 1}
            revocation["hash"] = canonical_hash(revocation)
            self._put(actor, "lesson-revocations", lesson_id, revocation)
            bank["revision"] += 1; bank["revocation_revision"] += 1
            self._put(actor, "lesson-bank", "bank", bank)
        return self.get_lesson(lesson_id, actor)

    def freeze_playbook(self, lesson_ids, *, expected_revision, actor="local-analyst"):
        if (not isinstance(lesson_ids, list) or not 1 <= len(lesson_ids) <= MAX_PLAYBOOK_LESSONS
                or any(not isinstance(identifier, str) or not HEX32.fullmatch(identifier) for identifier in lesson_ids)
                or len(set(lesson_ids)) != len(lesson_ids)):
            raise ValueError("Freeze one through sixteen distinct accepted lesson versions.")
        with self.memory._transaction():
            bank = self._current(actor, expected_revision)
            if len(bank["playbook_ids"]) >= MAX_PLAYBOOKS:
                raise ValueError("The bounded frozen-playbook limit has been reached.")
            rows = [self.get_lesson(identifier, actor) for identifier in sorted(lesson_ids)]
            if any(not row or row["status"] != "accepted" for row in rows):
                raise LessonConflict("A playbook may contain only explicitly accepted, unrevoked lessons.")
            sources = {row["origin"]["source_fingerprint"] for row in rows}
            if len(sources) != 1:
                raise ValueError("A frozen playbook requires one source snapshot.")
            value = {"actor": actor, "source_fingerprint": next(iter(sources)), "bank_revision": bank["revision"] + 1,
                     "revocation_revision": bank["revocation_revision"], "lesson_refs": [_ref(row, row["decision"]) for row in rows],
                     "created_at": self.memory.clock()}
            value["id"] = canonical_hash(value); value["hash"] = canonical_hash(value)
            self._put(actor, "lesson-playbooks", value["id"], value)
            bank["playbook_ids"].append(value["id"]); bank["revision"] += 1
            self._put(actor, "lesson-bank", "bank", bank)
        return deepcopy(value)

    def get_playbook(self, identifier, actor="local-analyst"):
        _hex(identifier)
        value = self._get(actor, "lesson-playbooks", identifier)
        return deepcopy(_playbook(value, actor)) if value is not None else None

    def list_playbooks(self, actor="local-analyst"):
        return [self.get_playbook(identifier, actor) for identifier in self.get_bank(actor)["playbook_ids"]]

    def freeze_context(self, *, actor="local-analyst", scope, source_fingerprint, enabled=False, playbook_id=None):
        _actor(actor); _hex(source_fingerprint)
        if type(enabled) is not bool:
            raise ValueError("Lesson enablement must be explicit.")
        scope = _scope(scope, stages=False)
        snapshot = {"enabled": enabled, "actor": actor, "source_fingerprint": source_fingerprint, "selection_scope": scope,
                    "playbook_id": None, "playbook_hash": None, "bank_revision": None, "revocation_revision": None, "lesson_refs": []}
        if enabled:
            playbook = self.get_playbook(playbook_id, actor)
            if not playbook or playbook["source_fingerprint"] != source_fingerprint:
                raise LessonConflict("Choose a frozen playbook matching the active source snapshot.")
            revoked = {ref["lesson_id"] for ref in playbook["lesson_refs"] if self._get(actor, "lesson-revocations", ref["lesson_id"]) is not None}
            snapshot.update(playbook_id=playbook["id"], playbook_hash=playbook["hash"], bank_revision=playbook["bank_revision"],
                            revocation_revision=playbook["revocation_revision"], lesson_refs=_selected(playbook["lesson_refs"], scope, revoked))
        elif playbook_id is not None:
            raise ValueError("Disabled lessons cannot name a playbook.")
        snapshot["fingerprint"] = canonical_hash(snapshot)
        if enabled:
            with self.store.connection() as db:
                validate_lesson_snapshot(db, actor, snapshot, source_fingerprint=source_fingerprint, scope=scope)
        else:
            validate_lesson_structure(snapshot, actor, source_fingerprint, scope)
        return snapshot


def validate_lesson_structure(snapshot, actor=None, source_fingerprint=None, scope=None):
    if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_FIELDS:
        raise LessonConflict("The frozen lesson context has unsupported fields.")
    _checked_hash(snapshot, "fingerprint")
    _actor(snapshot["actor"]); _hex(snapshot["source_fingerprint"])
    if type(snapshot["enabled"]) is not bool or actor is not None and snapshot["actor"] != actor:
        raise LessonConflict("The frozen lesson context belongs to another analyst.")
    if source_fingerprint is not None and snapshot["source_fingerprint"] != source_fingerprint:
        raise LessonConflict("The frozen lesson source snapshot changed.")
    if _scope(snapshot["selection_scope"], stages=False) != snapshot["selection_scope"] or scope is not None and _scope(scope, stages=False) != snapshot["selection_scope"]:
        raise LessonConflict("The frozen lesson research scope changed.")
    refs = snapshot["lesson_refs"]
    if not isinstance(refs, list) or len(refs) > MAX_SELECTED or len(json.dumps(snapshot).encode()) > 16000:
        raise LessonConflict("The frozen lesson context exceeds its bounds.")
    if not snapshot["enabled"]:
        if refs or any(snapshot[key] is not None for key in ("playbook_id", "playbook_hash", "bank_revision", "revocation_revision")):
            raise LessonConflict("Disabled lessons cannot contain saved learning.")
    else:
        _hex(snapshot["playbook_id"]); _hex(snapshot["playbook_hash"])
        _revision(snapshot["bank_revision"]); _revision(snapshot["revocation_revision"])
    seen = set()
    for ref in refs:
        if (not isinstance(ref, dict) or set(ref) != REF_FIELDS or not isinstance(ref["action"], str) or ref["action"] not in ACTION_HINTS
                or _scope(ref["scope"]) != ref["scope"] or not _relevant(ref, snapshot["selection_scope"])):
            raise LessonConflict("The frozen lesson action or applicability changed.")
        _hex(ref["lesson_id"], HEX32); _hex(ref["proposal_hash"]); _hex(ref["decision_hash"])
        if ref["lesson_id"] in seen:
            raise LessonConflict("Frozen lesson references must be unique.")
        seen.add(ref["lesson_id"])
    return True


def _read(db, actor, kind, key):
    row = db.execute("SELECT value FROM store WHERE prefix=? AND key=?", (".".join(_namespace(actor, kind)), key)).fetchone()
    return json.loads(row[0]) if row else None


def validate_lesson_snapshot(db, actor, snapshot, source_fingerprint=None, scope=None):
    """Revalidate accepted versions and revocation inside the publisher's transaction."""
    validate_lesson_structure(snapshot, actor, source_fingerprint, scope)
    if not snapshot["enabled"]:
        return True
    try:
        playbook = _playbook(_read(db, actor, "lesson-playbooks", snapshot["playbook_id"]), actor)
        if (playbook["hash"] != snapshot["playbook_hash"] or playbook["source_fingerprint"] != snapshot["source_fingerprint"]
                or playbook["bank_revision"] != snapshot["bank_revision"] or playbook["revocation_revision"] != snapshot["revocation_revision"]):
            raise LessonConflict("The selected frozen playbook changed.")
        revoked = {ref["lesson_id"] for ref in playbook["lesson_refs"] if _read(db, actor, "lesson-revocations", ref["lesson_id"]) is not None}
        if _selected(playbook["lesson_refs"], snapshot["selection_scope"], revoked) != snapshot["lesson_refs"]:
            raise LessonConflict("Selected lessons changed or were revoked; create a fresh plan.")
        for ref in snapshot["lesson_refs"]:
            proposal = _proposal(_read(db, actor, "lessons", ref["lesson_id"]), actor)
            decision = _decision(_read(db, actor, "lesson-decisions", ref["lesson_id"]), proposal)
            if (decision["decision"] != "accept" or _ref(proposal, decision) != ref
                    or proposal["origin"]["source_fingerprint"] != snapshot["source_fingerprint"] or ref["lesson_id"] in revoked):
                raise LessonConflict("A frozen lesson lacks its exact current human acceptance.")
    except LessonConflict:
        raise
    except (sqlite3.Error, KeyError, TypeError, ValueError) as error:
        raise LessonConflict("The accepted lesson context could not be validated.") from error
    return True


def model_lesson_hints(snapshot, stage):
    validate_lesson_structure(snapshot)
    if stage == "critic":
        return []
    if stage not in STAGES:
        raise ValueError("Lesson hints support only declared producing stages.")
    if not snapshot["enabled"]:
        return []
    return list(dict.fromkeys(ACTION_HINTS[ref["action"]] for ref in snapshot["lesson_refs"] if stage in ref["scope"]["stages"]))
