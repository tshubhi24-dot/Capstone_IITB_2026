"""research-portal MCP server — past notes (read) and publishing (write).

Tools:
    get_past_notes   published notes that cover a ticker, newest first
    publish_note     WRITE: publish a note — only with a valid approval token
                     for that exact note (see analystdesk/approval.py)

publish_note is the only tool in the system that changes the outside world.
Only the publisher agent is given it, and even then the server itself
refuses without an analyst-issued token: approval is enforced here, not
only in the graph, so a skipped gate or an injected instruction cannot
publish.

Storage: SQLite at .runtime/portal/portal.db (gitignored), or PORTAL_DB.
Run standalone (stdio):  python -m analystdesk.servers.portal
"""

from __future__ import annotations

import json
import os
import sqlite3
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from analystdesk.paths import RUNTIME_ROOT

from analystdesk.governance import approval as approval
from analystdesk.research.scope import COMPANIES
from . import signing
from .common import READ_ONLY, WRITE, ToolResult, fail, serve, structured_errors

DEFAULT_DB = RUNTIME_ROOT / "portal" / "portal.db"

mcp = FastMCP(
    "research-portal",
    instructions=(
        "Past research notes (read) and publishing (write). publish_note needs an "
        "approval_token issued when the analyst approves that exact note; it is "
        "refused for any other text."
    ),
)

_TICKERS = {c.ticker for c in COMPANIES}

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    body          TEXT NOT NULL,
    tickers       TEXT NOT NULL,          -- JSON list, e.g. ["MSFT","GOOGL"]
    note_sha256   TEXT NOT NULL UNIQUE,   -- hash of the exact approved note
    approver      TEXT NOT NULL,
    approved_at   TEXT NOT NULL,
    published_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approval_context (
    note_id INTEGER PRIMARY KEY REFERENCES notes(id),
    context_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS note_lifecycle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id INTEGER NOT NULL UNIQUE REFERENCES notes(id),
    action TEXT NOT NULL CHECK(action IN ('withdraw', 'supersede')),
    replacement_id INTEGER REFERENCES notes(id),
    reason TEXT NOT NULL,
    actor TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    signature TEXT
);
"""


def _db_path() -> Path:
    return Path(os.getenv("PORTAL_DB", str(DEFAULT_DB)))


@contextmanager
def _connect():
    """Open the portal DB; commit on success, always close (Windows locks open files)."""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA)
        with con:
            yield con
    finally:
        con.close()


class Note(BaseModel):
    note_id: int
    title: str
    body: str
    tickers: list[str]
    approver: str
    approved_at: str
    published_at: str


class PastNotesResult(ToolResult):
    notes: list[Note] = []


class PublishResult(ToolResult):
    note_id: int | None = None
    note_sha256: str | None = None
    published_at: str | None = None


class LifecycleError(ValueError):
    """A lifecycle action is invalid or not authorised."""


def lifecycle_digest(note_id: int, action: str, replacement_id: int | None, reason: str, actor: str) -> str:
    data = {"action": action, "note_id": note_id, "replacement_id": replacement_id,
            "reason": reason.strip(), "actor": actor.strip()}
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def change_lifecycle(note_id: int, action: str, reason: str, actor: str,
                     replacement_id: int | None = None, signature: str | None = None) -> dict:
    """Record a terminal lifecycle action; this is never exposed as an agent tool."""
    reason, actor = reason.strip(), actor.strip()
    if type(note_id) is not int or note_id < 1 or action not in {"withdraw", "supersede"}:
        raise LifecycleError("Invalid note or lifecycle action")
    if not reason or not actor:
        raise LifecycleError("A reason and actor are required")
    if action == "withdraw" and replacement_id is not None:
        raise LifecycleError("A withdrawal cannot have a replacement")
    if action == "supersede" and (type(replacement_id) is not int or replacement_id < 1
                                   or replacement_id == note_id):
        raise LifecycleError("Supersession requires a different replacement note")
    if signing.enabled():
        try:
            signing.verify(actor, signature or "", lifecycle_digest(note_id, action, replacement_id, reason, actor))
        except signing.SignatureError as exc:
            raise LifecycleError(str(exc)) from exc
    with _connect() as con:
        con.execute("BEGIN IMMEDIATE")
        old = con.execute("SELECT id, tickers FROM notes WHERE id = ?", (note_id,)).fetchone()
        if old is None:
            raise LifecycleError("Note not found")
        if con.execute("SELECT 1 FROM note_lifecycle WHERE note_id = ?", (note_id,)).fetchone():
            raise LifecycleError("Note is already withdrawn or superseded")
        if action == "supersede":
            replacement = con.execute(
                "SELECT n.id, n.tickers, c.context_json FROM notes n "
                "LEFT JOIN approval_context c ON c.note_id = n.id "
                "WHERE n.id = ? AND NOT EXISTS (SELECT 1 FROM note_lifecycle l WHERE l.note_id = n.id)",
                (replacement_id,)).fetchone()
            if replacement is None:
                raise LifecycleError("Replacement note does not exist or is inactive")
            if replacement["id"] <= old["id"]:
                raise LifecycleError("Replacement must be published after the original note")
            if set(json.loads(replacement["tickers"])) != set(json.loads(old["tickers"])):
                raise LifecycleError("Replacement must cover the same tickers")
            if not replacement["context_json"]:
                raise LifecycleError("Replacement requires a fresh graph approval and review context")
            context = json.loads(replacement["context_json"])
            if (not isinstance(context, dict) or not isinstance(context.get("check"), dict)
                    or context["check"].get("ok") is not True):
                raise LifecycleError("Replacement has no successful review")
        occurred_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        con.execute("INSERT INTO note_lifecycle (note_id, action, replacement_id, reason, actor, occurred_at, signature) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (note_id, action, replacement_id, reason, actor, occurred_at, signature))
    return {"note_id": note_id, "action": action, "replacement_id": replacement_id,
            "reason": reason, "actor": actor, "occurred_at": occurred_at}


def inactive_note_ids() -> set[int]:
    """Read the lifecycle ledger without creating a portal when none exists."""
    if not _db_path().exists():
        return set()
    with _connect() as con:
        return {row["note_id"] for row in con.execute("SELECT note_id FROM note_lifecycle")}


def _note(row: sqlite3.Row) -> Note:
    return Note(
        note_id=row["id"], title=row["title"], body=row["body"],
        tickers=json.loads(row["tickers"]), approver=row["approver"],
        approved_at=row["approved_at"], published_at=row["published_at"],
    )


@mcp.tool(annotations=READ_ONLY)
@structured_errors(PastNotesResult)
def get_past_notes(
    ticker: Annotated[str, Field(description="Ticker, e.g. MSFT")],
    limit: Annotated[int, Field(ge=1, le=20, description="Maximum notes to return")] = 5,
) -> PastNotesResult:
    """Published notes covering this ticker, newest first (for "what changed since our last note?")."""
    t = ticker.strip().upper()
    if t not in _TICKERS:
        return fail(PastNotesResult, "NOT_IN_COVERAGE", f"{ticker} is not covered")
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM notes WHERE NOT EXISTS (SELECT 1 FROM note_lifecycle l WHERE l.note_id = notes.id) "
            "AND EXISTS (SELECT 1 FROM json_each(notes.tickers) "
            "WHERE value = ?) ORDER BY published_at DESC, id DESC LIMIT ?",
            (t, limit),
        ).fetchall()
    return PastNotesResult(notes=[_note(r) for r in rows])


@mcp.tool(annotations=WRITE)
@structured_errors(PublishResult)
def publish_note(
    title: Annotated[str, Field(description="Note title, exactly as approved")],
    body: Annotated[str, Field(description="Note body, exactly as approved")],
    tickers: Annotated[list[str], Field(description="Tickers the note covers, as approved")],
    approval_token: Annotated[str, Field(description="Token issued when the analyst approved "
                                         "this exact note")],
    approver_signature: Annotated[str | None, Field(
        description="The approver's own Ed25519 signature over the note's sha256 digest, "
                    "base64url. Required once an approver public key is registered "
                    "(see servers/signing.py)")] = None,
) -> PublishResult:
    """WRITE — publish a research note to the portal.

    Refused unless approval_token was issued for exactly this title, body and
    ticker list. Any edit after approval requires a new approval. Once an
    approver public key is registered, also refused without that approver's
    own signature over the note digest.
    """
    unknown = [t for t in tickers if t.strip().upper() not in _TICKERS]
    if not tickers or unknown:
        return fail(PublishResult, "BAD_INPUT", f"tickers must be covered companies; got {tickers}")
    if not title.strip() or not body.strip():
        return fail(PublishResult, "BAD_INPUT", "title and body must not be empty")
    try:
        claims = approval.verify(approval_token, title, body, tickers)
    except approval.ApprovalError as exc:
        return fail(PublishResult, "APPROVAL_INVALID", str(exc))

    # Fix for Module 4 - Security (Fix 2 - use case 2): enforced in the server,
    # not only in the graph, for the same reason the HMAC is. Checked against
    # the *verified* claims rather than the raw token, so the approver name and
    # the digest are both authenticated by the time the signature is held
    # against them.
    if signing.enabled():
        try:
            signing.verify(claims["approver"], approver_signature or "", claims["note_sha256"])
        except signing.SignatureError as exc:
            return fail(PublishResult, signing.CODE, str(exc))

    published_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    canonical_tickers = sorted({t.strip().upper() for t in tickers})
    try:
        with _connect() as con:
            con.execute("BEGIN IMMEDIATE")
            context = claims.get("review_context")
            if context is not None and not isinstance(context, dict):
                raise approval.ApprovalError("approval review context is malformed")
            if isinstance(context, dict) and context.get("version") == 2:
                check = context.get("check")
                snapshot = context.get("evidence_snapshot")
                if not isinstance(check, dict) or check.get("ok") is not True:
                    raise approval.ApprovalError("approval review did not pass")
                if (not isinstance(snapshot, dict) or snapshot.get("version") != 1
                        or snapshot.get("note_sha256") != claims["note_sha256"]
                        or not isinstance(snapshot.get("facts"), dict)
                        or not isinstance(snapshot.get("passages"), dict)
                        or not isinstance(snapshot.get("policy_sha256"), str)
                        or len(snapshot["policy_sha256"]) != 64):
                    raise approval.ApprovalError("approval evidence snapshot is missing or malformed")
            if isinstance(context, dict) and context.get("memory_on") is True:
                epoch = context.get("lifecycle_epoch")
                current = con.execute("SELECT COUNT(*) FROM note_lifecycle").fetchone()[0]
                if type(epoch) is not int or epoch != current:
                    raise approval.ApprovalError("Published-note status changed; start a fresh run and approve again")
            cur = con.execute(
                "INSERT INTO notes (title, body, tickers, note_sha256, approver, approved_at, "
                "published_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, body, json.dumps(canonical_tickers), claims["note_sha256"],
                 claims["approver"], claims["approved_at"], published_at),
            )
            note_id = cur.lastrowid
            if "review_context" in claims:
                con.execute("INSERT INTO approval_context (note_id, context_json) VALUES (?, ?)",
                            (note_id, json.dumps(context, ensure_ascii=False, sort_keys=True)))
    except approval.ApprovalError as exc:
        return fail(PublishResult, "APPROVAL_INVALID", str(exc))
    except sqlite3.IntegrityError:
        # name the existing record, so a retry after a lost response can be reconciled
        with _connect() as con:
            row = con.execute("SELECT id, published_at FROM notes WHERE note_sha256 = ?",
                              (claims["note_sha256"],)).fetchone()
        where = f" as note #{row[0]} at {row[1]}" if row else ""
        return fail(PublishResult, "ALREADY_EXISTS", f"this exact note is already published{where}")
    return PublishResult(note_id=note_id, note_sha256=claims["note_sha256"], published_at=published_at)


if __name__ == "__main__":
    serve(mcp)
