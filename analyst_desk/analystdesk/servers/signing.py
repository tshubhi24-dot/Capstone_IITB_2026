"""Fix 2 — the approver's own signature, made with a key nothing here holds.

What the HMAC token cannot say. `approval.py` binds a sign-off to one exact
note with an HMAC over `note_hash(title, body, tickers)`. That is a real
control and Fix 2 does not replace it: an edit after approval still
invalidates the token. But HMAC is symmetric, and the consequences are
structural rather than accidental:

  * the key that *verifies* also *mints*. research-portal must hold
    APPROVAL_SECRET to check a token, so the verifier can forge one;
  * the app holds it too, because the note gate is where `approval.sign` is
    called — so the process running the model can mint an approval for any
    text, with any name on it;
  * `approver: "jayshree"` is therefore a string, not a claim. Nothing binds
    it to that person. One secret writes any name.

`tests/security/test_forced_approval_injection.py` already pins the five links
an injected "publish this" has to break, and the fifth is that HMAC. Fix 2
changes what the fifth link is made of.

The guardrail. The approver signs the note digest with an **Ed25519 private
key**, and this project holds only the **public** half:

    approver's device          data/approval/approvers/
    <name>.key  (private)  ->  <name>.pub  (public, this is all we keep)
    signs note_sha256          verifies it; cannot produce it

So the portal can check a sign-off and cannot manufacture one; the agent
process holds no signing key at all; and the name on the approval now selects
which public key must verify, which is what turns it from a label into a
claim. That is the lecture's point in docs_notfor_submission/notes/approver-signature.png —
"a signature proves who approved and exactly what, with a key the agent cannot
reach" — and AP2's signed mandates are the same shape.

**The limit, stated first because it is the question that will be asked.**
This is enforced **only once a public key is registered**. `data/approval/
approvers/` is empty in the repo, and with no key registered the desk behaves
exactly as before: an HMAC token alone publishes. Register one key and the
rule becomes fail-closed for *every* publish — an unknown approver is refused,
so there is no "name someone unregistered" way around it. The registry is
therefore a deployment switch, not a per-call option.

Second limit, since the first invites it: today the registry sits inside the
`approval` volume that the app and the portal share, so a deployment wanting
"the portal can verify and nothing else can edit the registry" mounts
APPROVER_KEYS_DIR read-only into research-portal alone. That is one line in
compose.yaml, outside this branch's scope, and it is recorded as a hand-off
rather than done here. What already holds without it is the part that matters:
no private key exists anywhere in this project, so no process here can produce
a signature, whatever it can read.

What is signed is the digest, not the note: a 64-character hex string the
approver can be shown in full next to the text it stands for. Replay of a
signature publishes the same note twice, which `note_sha256 TEXT NOT NULL
UNIQUE` already refuses.

Approver side, on a machine this project does not run on:

    python -m analystdesk.servers.signing keygen jayshree --out ~/keys
    # copy ~/keys/jayshree.pub to the deployment; the .key never moves
    python -m analystdesk.servers.signing sign --key ~/keys/jayshree.key \
        --note note.json          # or --digest <sha256 hex>

Layering: imports `..approval` for `note_hash` only — that module is stdlib
and imports nothing from here, so there is no cycle. This is the one place in
the project that uses `cryptography`; stdlib has no asymmetric signatures, and
hand-rolling Ed25519 to preserve a style rule would be the wrong trade.
"""

# Fix for Module 4 - Security — this whole module is new in Module 4 (Fix 2).

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path

from analystdesk.governance import approval as approval

DEFAULT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "approval" / "approvers"

# One file per approver. The name is part of the filename, so it is constrained.
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
PUBLIC_SUFFIX = ".pub"
PRIVATE_SUFFIX = ".key"

CODE = "APPROVAL_UNSIGNED"


class SignatureError(ValueError):
    """The approver's signature is missing, unknown, malformed or does not verify."""


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text.strip() + "=" * (-len(text.strip()) % 4))


def keys_dir() -> Path:
    """Where registered public keys live. APPROVER_KEYS_DIR overrides."""
    return Path(os.getenv("APPROVER_KEYS_DIR", str(DEFAULT_DIR)))


def normalise(approver: str) -> str:
    return (approver or "").strip().lower()


def approvers() -> dict[str, bytes]:
    """Registered approver -> raw 32-byte Ed25519 public key."""
    directory = keys_dir()
    if not directory.is_dir():
        return {}
    out = {}
    for path in sorted(directory.glob("*" + PUBLIC_SUFFIX)):
        name = normalise(path.name[: -len(PUBLIC_SUFFIX)])
        if not NAME.match(name):
            continue
        try:
            raw = _unb64(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if len(raw) == 32:       # an Ed25519 public key is exactly 32 bytes
            out[name] = raw
    return out


def enabled() -> bool:
    """True once any approver key is registered — the deployment switch."""
    return bool(approvers())


def verify(approver: str, signature: str, digest: str) -> None:
    """Raise SignatureError unless `signature` is `approver`'s over `digest`."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    name = normalise(approver)
    registered = approvers()
    if not registered:
        raise SignatureError("no approver public key is registered")
    if name not in registered:
        raise SignatureError(f"approver {approver!r} has no registered public key "
                             f"(registered: {', '.join(sorted(registered)) or 'none'})")
    if not signature:
        raise SignatureError(f"approver {name!r} must sign this note; no signature was supplied")
    try:
        raw = _unb64(signature)
    except (ValueError, TypeError):
        raise SignatureError("the approver signature is not valid base64") from None
    try:
        Ed25519PublicKey.from_public_bytes(registered[name]).verify(raw, digest.encode("ascii"))
    except InvalidSignature:
        raise SignatureError(f"the signature does not verify as {name}'s over this note; "
                             "the note was changed after signing, or the key is not theirs") from None
    except ValueError as exc:
        raise SignatureError(f"the approver signature is malformed: {exc}") from None


# ── what the guardrail and the portal both call ──────────────────────────────

def claimed_approver(approval_token: str) -> str:
    """The approver named in a token's payload, read *without* verifying it.

    Safe to trust for key selection only: the name chooses which public key
    must verify, so a forged name selects a key whose holder did not sign.
    """
    try:
        payload = (approval_token or "").strip().split(".")[0]
        return normalise(json.loads(_unb64(payload)).get("approver", ""))
    except Exception:   # noqa: BLE001 — a malformed token is refused downstream
        return ""


def check(args: dict) -> str | None:
    """None if this publish may proceed; otherwise why it may not.

    Fail-closed once any key is registered: an unknown or unnamed approver is
    refused, so there is no unregistered name to hide behind.
    """
    if not enabled():
        return None
    digest = approval.note_hash(args.get("title", ""), args.get("body", ""),
                                args.get("tickers") or [])
    try:
        verify(claimed_approver(args.get("approval_token", "")),
               args.get("approver_signature") or "", digest)
    except SignatureError as exc:
        return str(exc)
    return None


def denial(reason: str) -> dict:
    """The refusal, in the envelope every tool returns (common.py)."""
    return {"ok": False, "error": {
        "code": CODE,
        "message": (f"refused: {reason}. A note is published only with the approver's own "
                    f"Ed25519 signature over its digest; this deployment holds public keys "
                    f"only and cannot produce one.")}}


# ── approver side: run on the device that holds the private key ──────────────

def sign(private_key: Path | str, digest: str) -> str:
    """Sign a note digest. Never called by this project at run time."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    raw = _unb64(Path(private_key).read_text(encoding="utf-8"))
    return _b64(Ed25519PrivateKey.from_private_bytes(raw).sign(digest.encode("ascii")))


def keygen(name: str, out_dir: Path | str) -> tuple[Path, Path]:
    """Write <name>.key (private, 0600) and <name>.pub. Refuses to overwrite."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    name = normalise(name)
    if not NAME.match(name):
        raise ValueError(f"approver name {name!r} must match {NAME.pattern}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    private_path, public_path = out / (name + PRIVATE_SUFFIX), out / (name + PUBLIC_SUFFIX)
    for path in (private_path, public_path):
        if path.exists():
            raise FileExistsError(f"{path} already exists; refusing to overwrite a key")

    key = Ed25519PrivateKey.generate()
    from cryptography.hazmat.primitives import serialization as _ser
    raw_private = key.private_bytes(_ser.Encoding.Raw, _ser.PrivateFormat.Raw, _ser.NoEncryption())
    raw_public = key.public_key().public_bytes(_ser.Encoding.Raw, _ser.PublicFormat.Raw)

    # 0600 before any bytes are written, not after: a key must never exist
    # readable, however briefly.
    fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(_b64(raw_private) + "\n")
    public_path.write_text(_b64(raw_public) + "\n", encoding="utf-8")
    return private_path, public_path


def _main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="python -m analystdesk.servers.signing",
                                description="Approver-side key handling for Fix 2.")
    sub = p.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("keygen", help="create an approver keypair")
    k.add_argument("name")
    k.add_argument("--out", default=".", help="directory for <name>.key and <name>.pub")

    s = sub.add_parser("sign", help="sign one note digest")
    s.add_argument("--key", required=True, help="path to <name>.key")
    group = s.add_mutually_exclusive_group(required=True)
    group.add_argument("--digest", help="the note's sha256, as printed at the gate")
    group.add_argument("--note", help="a JSON file with title, body and tickers")

    sub.add_parser("list", help="show the approvers registered here")

    args = p.parse_args(argv)
    if args.cmd == "keygen":
        private_path, public_path = keygen(args.name, args.out)
        print(f"private key  {private_path}   keep this on your own device, never copy it")
        print(f"public key   {public_path}   copy this into the deployment's approvers directory")
        return 0
    if args.cmd == "sign":
        digest = args.digest
        if args.note:
            note = json.loads(Path(args.note).read_text(encoding="utf-8"))
            digest = approval.note_hash(note["title"], note["body"], note["tickers"])
        print(sign(args.key, digest))
        return 0
    registered = approvers()
    print(f"approver keys in {keys_dir()}:")
    for name in sorted(registered) or ["(none registered - Fix 2 is not enforced)"]:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
