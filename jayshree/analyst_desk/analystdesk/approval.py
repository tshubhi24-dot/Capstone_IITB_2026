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

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

# Separate from the portal DB: in Docker this folder is a volume shared by
# the app (signs) and the portal (verifies); the app gets no access to the DB
KEY_FILE = Path(__file__).parent.parent / "data" / "approval" / "approval.key"


class ApprovalError(ValueError):
    """The token is missing, malformed, forged, or for a different note."""


# Analyst override, for judgement findings only: lines without a passage
# citation (headings, table rows, code-verified figures the judge cannot check),
# claims the judge did not accept, and claims the judge gave no verdict on.
# The analyst reads the highlighted lines, takes responsibility and gives a
# reason. Failures that code proves (a number that does not match the filing or
# has no source, advice wording, a private-watchlist name, an unfinished
# template, evidence that changed during review) still block.
_REVIEW_INCOMPLETE = "Review incomplete: "
UNCITED_ISSUE_MARK = " substantive line(s) lack a passage citation."
JUDGE_REJECTED_PREFIX = "Claim not supported by its cited passage (judge): "
JUDGE_NO_VERDICT_PREFIX = "Review incomplete: the judge gave no valid verdict for "


def _is_uncited_issue(issue) -> bool:
    if not isinstance(issue, str) or not issue.startswith(_REVIEW_INCOMPLETE):
        return False
    count, sep, _ = issue[len(_REVIEW_INCOMPLETE):].partition(UNCITED_ISSUE_MARK)
    return bool(sep) and count.isdigit()


def is_judgement_issue(issue) -> bool:
    """An issue the analyst may take responsibility for (see above)."""
    return isinstance(issue, str) and (_is_uncited_issue(issue) or issue.startswith(JUDGE_REJECTED_PREFIX)
                                       or issue.startswith(JUDGE_NO_VERDICT_PREFIX))


def overridable(check) -> bool:
    """True when the check failed only on judgement findings."""
    if not isinstance(check, dict) or check.get("ok") is True:
        return False
    issues = check.get("issues")
    return isinstance(issues, list) and bool(issues) and all(is_judgement_issue(i) for i in issues)


def valid_override(override) -> bool:
    return (isinstance(override, dict) and override.get("uncited") is True
            and isinstance(override.get("reason"), str) and bool(override["reason"].strip()))


def review_passed(check, override=None) -> bool:
    """The note may be approved: every check passed, or the analyst overrode uncited lines only."""
    if isinstance(check, dict) and check.get("ok") is True:
        return True
    return overridable(check) and valid_override(override)


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
