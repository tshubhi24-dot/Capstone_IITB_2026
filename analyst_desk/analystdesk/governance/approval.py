"""Approval tokens tie an analyst's sign-off to one exact note (rule 3, L14).

When the analyst approves a note, the approval gate calls sign(): it hashes
the exact note (title, body, tickers) and signs that hash together with the
approver and time, using a secret key. publish_note calls verify(): it
re-hashes the note it was given and checks the signature.

So:
  * an edit after approval changes the hash, and the old token no longer
    verifies — the note must be approved again;
  * an agent cannot approve on its own: making a token needs the secret key,
    which lives only on the approval-gate side and never enters a prompt.
A plain hash would not do: anyone (including an injected agent) could
compute it. The HMAC key is what makes the token a signature.

The key comes from the APPROVAL_SECRET environment variable; for local
development a random key is created once in data/approval/approval.key
(gitignored).
"""

from __future__ import annotations

from analystdesk.paths import APP_ROOT

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone

# Separate from the portal DB: in Docker this folder is a volume shared by
# the app (signs) and the portal (verifies); the app gets no access to the DB
KEY_FILE = APP_ROOT / "data" / "approval" / "approval.key"


class ApprovalError(ValueError):
    """The token is missing, malformed, forged, or for a different note."""


def _key() -> bytes:
    env = os.getenv("APPROVAL_SECRET")
    if env:
        return env.encode()
    if not KEY_FILE.exists():
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            # "x" = create only if absent: when the app and the portal start
            # together, exactly one key is written and both then read it
            with open(KEY_FILE, "x", encoding="utf-8") as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    return KEY_FILE.read_text(encoding="utf-8").strip().encode()


def note_hash(title: str, body: str, tickers: list[str]) -> str:
    """SHA-256 of the canonical note. Any change to any field changes it."""
    canonical = json.dumps(
        {"title": title, "body": body, "tickers": sorted(t.upper() for t in tickers)},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(title: str, body: str, tickers: list[str], approver: str, *, context: dict | None = None) -> str:
    """Issue an approval token for this exact note. Approval-gate side only."""
    claims = {
        "note_sha256": note_hash(title, body, tickers),
        "approver": approver,
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if context is not None:
        claims["review_context"] = context
    payload = _b64(json.dumps(claims, sort_keys=True).encode())
    sig = _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify(token: str, title: str, body: str, tickers: list[str]) -> dict:
    """Return the approval claims if the token approves exactly this note.

    Raises ApprovalError otherwise, with the reason.
    """
    try:
        payload, sig = token.strip().split(".")
        claims = json.loads(_unb64(payload))
    except Exception:
        raise ApprovalError("approval token is malformed") from None
    expected = _b64(hmac.new(_key(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise ApprovalError("approval token signature is invalid (not issued by the approval gate)")
    if claims.get("note_sha256") != note_hash(title, body, tickers):
        raise ApprovalError("note differs from the approved version; it must be approved again")
    return claims
