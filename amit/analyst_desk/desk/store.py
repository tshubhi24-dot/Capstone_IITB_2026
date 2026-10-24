"""SQLite run history and exact-version, expiring, idempotent publication."""
from contextlib import contextmanager
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


class Store:
    def __init__(self, path=None, secret=None, runtime_dir=None):
        root = Path(runtime_dir or os.environ.get("RUNTIME_DIR", ".runtime/journey"))
        candidate = Path(path) if path else root / "portal.sqlite"
        if candidate.suffix not in {".sqlite", ".db"}:
            candidate = candidate / "portal.sqlite"
        self.path = candidate
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.secret = secret or os.environ.get("PUBLICATION_SECRET", "")
        config = os.environ.get("SCOPED_CONFIG")
        if not self.secret and config:
            self.secret = json.loads(Path(config).read_text()).get("publication_secret", "")
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, actor TEXT NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS approvals(run_id TEXT PRIMARY KEY,actor TEXT NOT NULL,payload_hash TEXT NOT NULL,expires REAL NOT NULL,consumed INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY,run_id TEXT NOT NULL UNIQUE,actor TEXT NOT NULL,payload_hash TEXT NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_run(self, request, actor="local-analyst"):
        if hasattr(request, "model_dump"):
            request = request.model_dump()
        run = {"id": uuid.uuid4().hex, "actor": actor, "request": request, "status": "queued", "pending": None,
               "created_at": time.time(), "metrics": [], "risks": [], "critic": None, "usage": {"model_calls": 0, "cost_usd": 0}}
        self.save_run(run)
        return run

    def save_run(self, run):
        with self.connection() as db:
            db.execute("INSERT INTO runs(id,actor,data) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (run["id"], run.get("actor", "local-analyst"), json.dumps(run)))
        return run

    def get_run(self, identifier):
        with self.connection() as db:
            row = db.execute("SELECT data FROM runs WHERE id=?", (identifier,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_runs(self, actor="local-analyst"):
        with self.connection() as db:
            rows = db.execute("SELECT data FROM runs WHERE actor=? ORDER BY rowid DESC", (actor,)).fetchall()
        return [json.loads(v[0]) for v in rows]

    def event(self, identifier, agent, stage, message, details=None):
        value = {"agent": agent, "stage": stage, "message": message, "details": details or {}, "time": time.time()}
        with self.connection() as db:
            cursor = db.execute("INSERT INTO events(run_id,data) VALUES(?,?)", (identifier, json.dumps(value)))
            value["id"] = cursor.lastrowid
        return value

    def events(self, identifier):
        with self.connection() as db:
            rows = db.execute("SELECT id,data FROM events WHERE run_id=? ORDER BY id", (identifier,)).fetchall()
        return [{**json.loads(v["data"]), "id": v["id"]} for v in rows]

    def invalidate_approval(self, identifier):
        with self.connection() as db:
            db.execute("DELETE FROM approvals WHERE run_id=? AND consumed=0", (identifier,))

    def record_approval(self, run_id, actor, payload_hash, ttl=900):
        run = self.get_run(run_id)
        if not run or run["actor"] != actor:
            raise ValueError("Unknown run or actor")
        self._assert_publishable_run(run)
        pending = run.get("pending") or {}
        payload = pending.get("payload") if pending.get("kind") == "note" else run.get("draft")
        if not payload or canonical_hash(payload) != payload_hash:
            raise ValueError("Approval must match the persisted exact note")
        critic = run.get("critic") or {}
        if not critic.get("passed"):
            raise ValueError("A failed note cannot be approved")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT data FROM runs WHERE id=?", (run_id,)).fetchone()
            run = json.loads(current["data"]) if current else None
            if not run or run.get("actor") != actor:
                raise ValueError("Unknown run or actor")
            self._assert_publishable_run(run)
            pending = run.get("pending") or {}
            payload = pending.get("payload") if pending.get("kind") == "note" else run.get("draft")
            if not payload or canonical_hash(payload) != payload_hash or not (run.get("critic") or {}).get("passed"):
                raise ValueError("Approval must match the persisted exact checked note")
            if run["request"].get("lessons_enabled", False) and "lesson_context" not in payload:
                raise ValueError("The reviewed note is missing its frozen lesson context")
            if "memory_context" in payload:
                self._validate_payload_memory(payload, actor, db)
            if "lesson_context" in payload:
                self._validate_payload_lessons(payload, actor, db)
            db.execute("INSERT INTO approvals VALUES(?,?,?,?,0) ON CONFLICT(run_id) DO UPDATE SET actor=excluded.actor,payload_hash=excluded.payload_hash,expires=excluded.expires,consumed=0", (run_id, actor, payload_hash, time.time() + ttl))

    def make_capability(self, run_id, actor, payload_hash):
        if len(self.secret) < 32:
            raise ValueError("Publication signing secret is not configured")
        with self.connection() as db:
            row = db.execute("SELECT * FROM approvals WHERE run_id=?", (run_id,)).fetchone()
        if not row or row["actor"] != actor or row["payload_hash"] != payload_hash or row["expires"] < time.time() or row["consumed"]:
            raise ValueError("No current exact-version human approval")
        raw = json.dumps({"run_id": run_id, "actor": actor, "payload_hash": payload_hash, "expires": row["expires"]}, sort_keys=True).encode()
        token = base64.urlsafe_b64encode(raw).decode()
        signature = hmac.new(self.secret.encode(), token.encode(), hashlib.sha256).hexdigest()
        return token + "." + signature

    def publish(self, payload, capability):
        try:
            token, signature = capability.rsplit(".", 1)
            expected = hmac.new(self.secret.encode(), token.encode(), hashlib.sha256).hexdigest()
            if len(self.secret) < 32 or not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid publication capability")
            grant = json.loads(base64.urlsafe_b64decode(token))
            digest = canonical_hash(payload)
            if grant["payload_hash"] != digest or grant["run_id"] != payload["run_id"] or grant["actor"] != payload["actor"]:
                raise ValueError("Capability does not match payload")
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Invalid or mismatched publication capability") from exc
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            persisted = db.execute("SELECT data FROM runs WHERE id=?", (payload["run_id"],)).fetchone()
            if persisted is None:
                raise ValueError("The approved research run is unavailable")
            persisted_run = json.loads(persisted["data"])
            self._assert_publishable_run(persisted_run)
            if persisted_run["request"].get("lessons_enabled", False) and "lesson_context" not in payload:
                raise ValueError("The reviewed note is missing its frozen lesson context")
            previous = db.execute("SELECT * FROM notes WHERE run_id=?", (payload["run_id"],)).fetchone()
            if previous:
                if previous["payload_hash"] != digest:
                    raise ValueError("Idempotency key already has different content")
                return {"note_id": previous["id"], "run_id": payload["run_id"], "payload_hash": digest, "idempotent": True}
            if "memory_context" in payload:
                self._validate_payload_memory(payload, payload["actor"], db)
            if "lesson_context" in payload:
                self._validate_payload_lessons(payload, payload["actor"], db)
            row = db.execute("SELECT * FROM approvals WHERE run_id=?", (payload["run_id"],)).fetchone()
            if not row or row["actor"] != payload["actor"] or row["payload_hash"] != digest or row["consumed"] or row["expires"] < time.time() or grant["expires"] < time.time():
                raise ValueError("Stored human approval is missing, stale or consumed")
            identifier = uuid.uuid4().hex
            db.execute("INSERT INTO notes VALUES(?,?,?,?,?,?)", (identifier, payload["run_id"], payload["actor"], digest, json.dumps(payload), time.time()))
            db.execute("UPDATE approvals SET consumed=1 WHERE run_id=?", (payload["run_id"],))
        return {"note_id": identifier, "run_id": payload["run_id"], "payload_hash": digest, "idempotent": False}

    def notes(self, actor="local-analyst"):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM notes WHERE actor=? ORDER BY created DESC", (actor,)).fetchall()
        return [{"id": v["id"], "run_id": v["run_id"], "payload_hash": v["payload_hash"], "created_at": v["created"], "payload": json.loads(v["payload"])} for v in rows]

    def approved_note_candidates(self, actor, tickers, years, limit=50, *, excluded_note_ids=None):
        """Scope and approval are filtered in SQL before the bounded recent window."""
        from .history import validate_scope
        validate_scope(actor, tickers, years, limit, maximum=50)
        excluded = excluded_note_ids or []
        if (not isinstance(excluded, list) or len(excluded) > 256
                or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value) for value in excluded)):
            raise ValueError("Approved-history exclusions are invalid")
        parameters = [actor, *tickers, *years]
        sql = """SELECT n.* FROM notes n JOIN approvals a ON a.run_id=n.run_id
                 AND a.actor=n.actor AND a.payload_hash=n.payload_hash AND a.consumed=1
                 WHERE n.actor=? AND EXISTS (
                   SELECT 1 FROM json_each(CASE WHEN json_valid(n.payload) THEN n.payload ELSE '{}' END,'$.metrics') m
                   WHERE json_extract(CASE WHEN m.type='object' THEN m.value ELSE '{}' END,'$.ticker') IN (""" + ",".join("?" for _ in tickers) + ") AND json_extract(CASE WHEN m.type='object' THEN m.value ELSE '{}' END,'$.year') IN (" + ",".join("?" for _ in years) + "))"
        if excluded:
            sql += " AND n.id NOT IN (" + ",".join("?" for _ in excluded) + ")"
            parameters.extend(excluded)
        sql += " ORDER BY n.created DESC,n.id ASC LIMIT ?"
        parameters.append(limit)
        with self.connection() as db:
            rows = db.execute(sql, parameters).fetchall()
        candidates = []
        for row in rows:
            try:
                candidates.append(self._approved_note_row(row))
            except (ValueError, KeyError, TypeError):
                continue
        return candidates

    def approved_note(self, note_id, actor, db=None):
        """Read one actor-owned immutable approved payload, without applying reuse policy."""
        if (not isinstance(note_id, str) or not re.fullmatch(r"[0-9a-f]{32}", note_id)
                or not isinstance(actor, str) or not 1 <= len(actor) <= 80):
            return None
        if db is None:
            with self.connection() as connection:
                return self.approved_note(note_id, actor, connection)
        row = db.execute("""SELECT n.* FROM notes n JOIN approvals a ON a.run_id=n.run_id
                          AND a.actor=n.actor AND a.payload_hash=n.payload_hash AND a.consumed=1
                          WHERE n.id=? AND n.actor=?""", (note_id, actor)).fetchone()
        if row is None:
            return None
        try:
            return self._approved_note_row(row)
        except (ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _approved_note_row(row):
        import math
        from .history import note_scope
        payload = json.loads(row["payload"])
        if (not isinstance(payload, dict) or canonical_hash(payload) != row["payload_hash"]
                or payload.get("actor") != row["actor"] or payload.get("run_id") != row["run_id"]
                or not isinstance(row["created"], (int, float)) or not math.isfinite(row["created"])):
            raise ValueError("Approved note payload differs from its publication receipt")
        note_scope(payload)
        return {"id": row["id"], "run_id": row["run_id"], "payload_hash": row["payload_hash"],
                "created_at": row["created"], "payload": payload}

    def validate_memory_snapshot(self, snapshot, source_fingerprint=None, db=None, *, actor=None):
        """Recheck current same-database memory eligibility, including at publication."""
        from .history import note_reference, validate_snapshot_structure
        from .memory import validate_memory_versions
        validate_snapshot_structure(snapshot, actor=actor, source_fingerprint=source_fingerprint)
        if db is None:
            with self.connection() as connection:
                # Acquire a coherent view of revision records and selected notes.
                connection.execute("BEGIN")
                return self.validate_memory_snapshot(snapshot, source_fingerprint, connection, actor=actor)
        validate_memory_versions(db, snapshot["actor"], snapshot)
        for reference in snapshot["note_refs"]:
            note = self.approved_note(reference["note_id"], snapshot["actor"], db)
            if note is None:
                raise ValueError("A selected approved note is no longer available to this analyst")
            scope = snapshot["selection_scope"]
            if not any(row["ticker"] in scope["tickers"] and row["year"] in scope["years"] for row in note["payload"]["metrics"]):
                raise ValueError("A selected historical note is outside the frozen research scope")
            expected = note_reference(note, snapshot["source_fingerprint"])
            if expected != reference:
                raise ValueError("A selected approved note version or provenance changed")
        return True

    def _validate_payload_memory(self, payload, actor, db):
        context = payload["memory_context"]
        if "plan" in payload:
            plan = payload["plan"]
            if (not isinstance(plan, dict) or not isinstance(plan.get("tickers"), list)
                    or not isinstance(plan.get("years"), list)
                    or context.get("selection_scope") != {"tickers": sorted(plan["tickers"]),
                                                          "years": sorted(plan["years"])}):
                raise ValueError("The frozen memory scope differs from the approved research plan")
        return self.validate_memory_snapshot(context, payload.get("source_fingerprint"), db, actor=actor)

    @staticmethod
    def _assert_publishable_run(run):
        request = run.get("request") or {}
        if (request.get("learning_split", "production") != "production"
                or request.get("development_case_id") is not None or request.get("development_admission") is not None):
            raise ValueError("Development and evaluation research cannot receive publication approval or enter the note library")

    def validate_lesson_context(self, snapshot, source_fingerprint=None, db=None, *, actor=None, scope=None):
        from .lessons import validate_lesson_snapshot
        selected_actor = actor if actor is not None else snapshot.get("actor")
        if db is None:
            with self.connection() as connection:
                connection.execute("BEGIN")
                return self.validate_lesson_context(snapshot, source_fingerprint, connection,
                                                    actor=selected_actor, scope=scope)
        return validate_lesson_snapshot(db, selected_actor, snapshot,
                                        source_fingerprint=source_fingerprint, scope=scope)

    def _validate_payload_lessons(self, payload, actor, db):
        plan = payload.get("plan")
        if not isinstance(plan, dict):
            raise ValueError("A reviewed research plan is required for lesson reuse")
        context = payload["lesson_context"]
        if plan.get("lesson_context") != context:
            raise ValueError("The note's lesson context differs from the reviewed plan")
        current = db.execute("SELECT data FROM runs WHERE id=?", (payload.get("run_id"),)).fetchone()
        run = json.loads(current["data"]) if current else None
        if (not run or run.get("actor") != actor or run.get("lesson_context") != context
                or context.get("enabled") is not run["request"].get("lessons_enabled", False)
                or context.get("enabled") and context.get("playbook_id") != run["request"].get("playbook_id")
                or context.get("source_fingerprint") != payload.get("source_fingerprint")
                or context.get("source_fingerprint") != run.get("source_fingerprint")):
            raise ValueError("The approved lesson context differs from the original research run")
        return self.validate_lesson_context(context, payload.get("source_fingerprint"), db, actor=actor,
            scope={"tickers": sorted(plan["tickers"]), "years": sorted(plan["years"])})
