"""Prepare an inactive live-model proposal, or record an explicit exact-version decision.

No operation in this helper contacts a model provider. Confirmation text is
operator-supplied evidence, not independent verification of a human identity.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from desk.model_profiles import UNLIMITED_CALL_PROFILE, model_profile

PRIVATE = ROOT / ".runtime/live"
CONFIG_FILE = PRIVATE / "model_config.json"
KEY_FILE = PRIVATE / "provider.key"
APPROVAL_FILE = PRIVATE / "authorization.json"
DEFAULTS = {
    "enabled": False,
    "version": "live-step6-openrouter-v1",
    "cap_usd": "1.00",
    "per_run_usd": "0.50",
    "max_calls_per_run": 12,
    "max_tokens_per_run": 250000,
    "prompt_token_ceiling": 65536,
    "max_message_bytes": 60000,
    "max_output_tokens": 4096,
    "models": model_profile("live-step6-openrouter-v1")["models"],
}
SWITCH_PROFILES = {"mistral": "live-step10-mistral-v1", "mistral-large2407": "live-step10-mistral-large2407-v1",
                   "google-critic": "live-step10-google-critic-v1",
                   "fallbacks": "live-step16-fallbacks-v1",
                   "program-office": "live-program-models-v1"}


def now():
    return datetime.now(timezone.utc).isoformat()


def proposal_hash(config):
    """The decision covers this exact proposal; activation alone is excluded."""
    value = deepcopy(config)
    value["enabled"] = False
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def ensure_private_directory():
    if PRIVATE.is_symlink():
        raise ValueError("The private live directory must not be a symlink.")
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    PRIVATE.chmod(0o700)


def write_private(path, value, mode):
    if path.is_symlink():
        raise ValueError("Private live files must not be symlinks.")
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(value)
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_config(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULTS) | {"authorization_id"}:
        raise ValueError("Unexpected live proposal fields.")
    if type(value["enabled"]) is not bool or not isinstance(value["authorization_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", value["authorization_id"]):
        raise ValueError("Invalid activation or authorization identifier.")
    profile = model_profile(value["version"])
    if value["models"] != profile["models"]:
        raise ValueError("The model and pricing proposal differs from this reviewed implementation.")
    try:
        caps = [Decimal(value[key]) for key in ("cap_usd", "per_run_usd")]
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("Invalid live spending caps.") from error
    if not all(cap.is_finite() and cap > 0 for cap in caps) or caps[1] > caps[0]:
        raise ValueError("Live caps must be finite, positive and consistent.")
    for key in ("max_calls_per_run", "max_tokens_per_run", "prompt_token_ceiling", "max_message_bytes", "max_output_tokens"):
        if key == "max_calls_per_run" and value[key] is None and profile["version"] == UNLIMITED_CALL_PROFILE:
            continue
        if type(value[key]) is not int or value[key] <= 0:
            raise ValueError("Live call and token limits must be positive integers.")
    if any(value[key] > ceiling for key, ceiling in profile.get("limits", {}).items()):
        raise ValueError("The model context exceeds its reviewed profile limit.")
    if value["max_message_bytes"] + 4096 > value["prompt_token_ceiling"]:
        raise ValueError("The prompt reservation must cover message bytes and format overhead.")
    if value["prompt_token_ceiling"] + value["max_output_tokens"] > value["max_tokens_per_run"]:
        raise ValueError("The token budget cannot cover even one reserved request.")
    return value


def load_config():
    if CONFIG_FILE.is_symlink() or not CONFIG_FILE.is_file():
        raise ValueError("Prepare the live model proposal first.")
    return validate_config(json.loads(CONFIG_FILE.read_text()))


def read_provider_key(path):
    """Extract only this requested setting; never evaluate or copy an env file."""
    matches = []
    for line in Path(path).read_text().splitlines():
        match = re.fullmatch(r"\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*?)\s*", line)
        if match:
            value = match[1]
            if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            matches.append(value)
    if len(matches) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{24,}", matches[0]):
        raise ValueError("The supplied file must contain one valid OpenRouter key.")
    return matches[0]


def prepared_key():
    if KEY_FILE.is_symlink() or not KEY_FILE.is_file():
        raise ValueError("The private provider key has not been prepared.")
    value = KEY_FILE.read_text().strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{24,}", value):
        raise ValueError("The private provider key is invalid.")
    return value


def prepare(provider_env=None):
    ensure_private_directory()
    if provider_env is not None:
        key = read_provider_key(provider_env)
        if KEY_FILE.exists() and prepared_key() != key:
            raise ValueError("A different provider credential is already prepared; it was not replaced.")
        if not KEY_FILE.exists():
            # The parent is 0700. A readable bind mount lets nonroot UID10001
            # read this one file without sharing the host's other credentials.
            write_private(KEY_FILE, key + "\n", 0o444)
    prepared_key()
    KEY_FILE.chmod(0o444)
    if CONFIG_FILE.exists():
        config = load_config()
    else:
        config = {**deepcopy(DEFAULTS), "authorization_id": uuid.uuid4().hex}
        write_private(CONFIG_FILE, json.dumps(config, indent=2) + "\n", 0o444)
    return {"proposal_hash": proposal_hash(config), "config": config,
            "provider_key_prepared": True, "paid_calls_performed": 0,
            "next_action": "Review the exact proposal and explicitly authorize its spending cap before activation." if not config["enabled"] else "This exact authorization is already enabled; prepare did not change its limits."}


def authorize(expected_hash, human_confirmation):
    ensure_private_directory()
    config = load_config()
    prepared_key()
    if not re.fullmatch(r"[a-f0-9]{64}", expected_hash or "") or proposal_hash(config) != expected_hash:
        raise ValueError("The reviewed live proposal is stale or has a different hash.")
    if not isinstance(human_confirmation, str) or not human_confirmation.strip():
        raise ValueError("Explicit human confirmation of this exact spending proposal is required.")
    if config["enabled"]:
        if not APPROVAL_FILE.is_file() or json.loads(APPROVAL_FILE.read_text()).get("proposal_hash") != expected_hash:
            raise ValueError("An enabled proposal has no matching private authorization record.")
        return {"enabled": True, "proposal_hash": expected_hash, "changed": False, "paid_calls_performed": 0}
    record = {"time_utc": now(), "authorization_id": config["authorization_id"], "proposal_hash": expected_hash,
              "human_confirmation": human_confirmation.strip(), "confirmation_sha256": hashlib.sha256(human_confirmation.strip().encode()).hexdigest(),
              "scope": "Operator-supplied explicit human decision; not independent identity verification.",
              "cap_usd": config["cap_usd"], "per_run_usd": config["per_run_usd"]}
    write_private(APPROVAL_FILE, json.dumps(record, indent=2) + "\n", 0o600)
    config["enabled"] = True
    write_private(CONFIG_FILE, json.dumps(config, indent=2) + "\n", 0o444)
    return {"enabled": True, "proposal_hash": expected_hash, "changed": True,
            "authorization_id": config["authorization_id"], "paid_calls_performed": 0}


def disable():
    ensure_private_directory()
    config = load_config()
    config["enabled"] = False
    write_private(CONFIG_FILE, json.dumps(config, indent=2) + "\n", 0o444)
    return {"enabled": False, "proposal_hash": proposal_hash(config), "paid_calls_performed": 0}


def switch_profile(name, expected_hash):
    """Stage a reviewed replacement without changing credentials or ledger files.

    The old policy ID is immutable in the ledger. A replacement therefore gets
    a new ID; the gateway's lifetime spending cap still counts every old hold
    and charge. Activation requires a separate decision for the new hash.
    """
    if name not in SWITCH_PROFILES:
        raise ValueError("Unknown reviewed model profile switch.")
    ensure_private_directory()
    previous = load_config()
    if not re.fullmatch(r"[a-f0-9]{64}", expected_hash or "") or proposal_hash(previous) != expected_hash:
        raise ValueError("The model profile switch refers to a stale proposal hash.")
    profile = model_profile(SWITCH_PROFILES[name])
    call_limit = None if profile["version"] == UNLIMITED_CALL_PROFILE else (previous["max_calls_per_run"] or DEFAULTS["max_calls_per_run"])
    if (previous["version"] == profile["version"] and previous["models"] == profile["models"]
            and previous["max_calls_per_run"] == call_limit):
        raise ValueError("This model profile is already prepared; its authorization was not changed.")
    replacement = {**deepcopy(previous), "enabled": False, "authorization_id": uuid.uuid4().hex,
                   "version": profile["version"], "models": profile["models"], "max_calls_per_run": call_limit}
    for key, ceiling in profile.get("limits", {}).items():
        replacement[key] = min(previous[key], ceiling)
    validate_config(replacement)
    approval = None
    if APPROVAL_FILE.is_symlink() or APPROVAL_FILE.exists() and not APPROVAL_FILE.is_file():
        raise ValueError("The previous authorization must be a regular private file.")
    if APPROVAL_FILE.is_file():
        approval = APPROVAL_FILE.read_text()
    history = PRIVATE / "policy_history"
    if history.is_symlink() or history.exists() and not history.is_dir():
        raise ValueError("The private policy archive must be a regular directory.")
    history.mkdir(mode=0o700, exist_ok=True)
    history.chmod(0o700)
    archive = history / (previous["authorization_id"] + "-" + replacement["authorization_id"])
    archive.mkdir(mode=0o700)
    write_private(archive / "model_config.json", json.dumps(previous, indent=2) + "\n", 0o600)
    if approval is not None:
        write_private(archive / "authorization.json", approval, 0o600)
    # Archive first; a failed write never discards the previous policy. After
    # replacement even a leftover old receipt cannot authorize the new hash.
    write_private(CONFIG_FILE, json.dumps(replacement, indent=2) + "\n", 0o444)
    APPROVAL_FILE.unlink(missing_ok=True)
    return {"changed": True, "enabled": False, "proposal_hash": proposal_hash(replacement),
            "config": replacement, "previous_policy_archived": True, "credentials_changed": False,
            "ledger_changed": False, "paid_calls_performed": 0,
            "next_action": "Review this replacement proposal and separately record its spending authorization before activation."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--authorize", action="store_true")
    action.add_argument("--disable", action="store_true")
    action.add_argument("--switch-profile", choices=sorted(SWITCH_PROFILES))
    parser.add_argument("--provider-env", type=Path)
    parser.add_argument("--expected-hash")
    parser.add_argument("--human-confirmation")
    args = parser.parse_args()
    try:
        if args.prepare:
            if args.expected_hash or args.human_confirmation:
                raise ValueError("Preparation cannot include an authorization decision.")
            result = prepare(args.provider_env)
        elif args.authorize:
            if args.provider_env is not None:
                raise ValueError("Prepare credentials before reviewing the spending proposal.")
            result = authorize(args.expected_hash, args.human_confirmation)
        elif args.switch_profile:
            if args.provider_env is not None or args.human_confirmation:
                raise ValueError("A model profile switch cannot include credentials or an authorization decision.")
            result = switch_profile(args.switch_profile, args.expected_hash)
        else:
            if args.provider_env is not None or args.expected_hash or args.human_confirmation:
                raise ValueError("Disable accepts no credential or approval inputs.")
            result = disable()
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Errors never interpolate provider key content or source env-file text.
        print("Live preparation: " + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
