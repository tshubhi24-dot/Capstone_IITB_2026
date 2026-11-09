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

Storage: SQLite at data/portal/portal.db (gitignored), or PORTAL_DB.
Run standalone (stdio):  python -m analystdesk.servers.portal
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .. import approval
from ..scope import COMPANIES
from . import signing
from .common import READ_ONLY, WRITE, ToolResult, fail, serve, structured_errors

DEFAULT_DB = Path(__file__).resolve().parent.parent.parent / "data" / "portal" / "portal.db"

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
            "SELECT * FROM notes WHERE EXISTS (SELECT 1 FROM json_each(notes.tickers) "
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
            cur = con.execute(
                "INSERT INTO notes (title, body, tickers, note_sha256, approver, approved_at, "
                "published_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, body, json.dumps(canonical_tickers), claims["note_sha256"],
                 claims["approver"], claims["approved_at"], published_at),
            )
            note_id = cur.lastrowid
    except sqlite3.IntegrityError:
        return fail(PublishResult, "ALREADY_EXISTS", "this exact note is already published")
    return PublishResult(note_id=note_id, note_sha256=claims["note_sha256"], published_at=published_at)


if __name__ == "__main__":
    serve(mcp)
