"""SQLite run history and exact-version, expiring, idempotent publication."""
from contextlib import contextmanager
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
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
        pending = run.get("pending") or {}
        payload = pending.get("payload") if pending.get("kind") == "note" else run.get("draft")
        if not payload or canonical_hash(payload) != payload_hash:
            raise ValueError("Approval must match the persisted exact note")
        critic = run.get("critic") or {}
        if not critic.get("passed"):
            raise ValueError("A failed note cannot be approved")
        with self.connection() as db:
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
            previous = db.execute("SELECT * FROM notes WHERE run_id=?", (payload["run_id"],)).fetchone()
            if previous:
                if previous["payload_hash"] != digest:
                    raise ValueError("Idempotency key already has different content")
                return {"note_id": previous["id"], "run_id": payload["run_id"], "payload_hash": digest, "idempotent": True}
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
