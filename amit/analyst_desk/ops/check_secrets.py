"""Check staged Git content for known private credentials without printing them."""
import argparse
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def read_env_key(path):
    values = []
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*?)\s*", line)
        if match:
            value = match[1]
            if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values.append(value)
    if len(values) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{24,}", values[0]):
        raise ValueError("A valid private provider credential is required.")
    return values[0]


def _archived_provider_keys(root, archive):
    """Read a private known-key archive without following file symlinks."""
    directory = root / ".runtime/live" / archive
    if directory.is_symlink():
        raise ValueError("A private credential directory must not be a symlink.")
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise ValueError("A private credential archive is invalid.")
    values = []
    for path in sorted(directory.glob("*.key")):
        if path.is_symlink() or not path.is_file():
            continue
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "r") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                continue
            value = stream.read(4097).strip()
        if len(value) > 4096 or not re.fullmatch(r"[A-Za-z0-9_-]{24,}", value):
            raise ValueError("An archived credential could not be checked safely.")
        values.append(value)
    return values


def retired_provider_keys(root):
    """Read previously active known keys; retained for existing callers."""
    return _archived_provider_keys(root, "retired")


def vault_provider_keys(root):
    """Read separately stored known keys even when they have never been active."""
    return _archived_provider_keys(root, "key_vault")


def staged_matches(repo, credentials):
    if not credentials or any(not value or b"\n" in value for value in credentials):
        raise ValueError("Known credentials must be supplied privately for this check.")
    result = subprocess.run(["git", "grep", "--cached", "-a", "-l", "-F", "-f", "-"], cwd=repo,
                            input=b"\n".join(credentials) + b"\n", capture_output=True)
    if result.returncode not in {0, 1}:
        raise ValueError("Git could not check the staged content.")
    return result.stdout.decode().splitlines()


def history_contains(repo, credentials):
    """Scan reachable blob contents; never put a credential in a process argument."""
    result = subprocess.run(["git", "rev-list", "--objects", "HEAD"], cwd=repo, capture_output=True)
    if result.returncode:
        raise ValueError("Git history could not be inspected.")
    for line in result.stdout.splitlines():
        identifier = line.split(b" ", 1)[0].decode("ascii")
        kind = subprocess.run(["git", "cat-file", "-t", identifier], cwd=repo, capture_output=True, check=True).stdout.strip()
        if kind == b"blob":
            content = subprocess.run(["git", "cat-file", "blob", identifier], cwd=repo, capture_output=True, check=True).stdout
            if any(value in content for value in credentials):
                return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-env", type=Path)
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    try:
        path = ROOT / ".runtime/live/provider.key"
        if args.provider_env:
            provider = read_env_key(args.provider_env)
        elif path.is_file():
            provider = path.read_text().strip()
        else:
            raise ValueError("Prepare the private key or supply its local env file for the credential check.")
        credentials = [provider.encode()]
        credentials.extend(value.encode() for value in retired_provider_keys(ROOT))
        credentials.extend(value.encode() for value in vault_provider_keys(ROOT))
        analyst = ROOT / ".runtime/journey/credentials.env"
        if analyst.is_file():
            credentials += [line.split("=", 1)[1].strip().encode() for line in analyst.read_text().splitlines() if line.startswith("ANALYST_API_TOKEN=")]
        credentials = list(dict.fromkeys(credentials))
        names = staged_matches(ROOT, credentials)
        if names:
            print("STOP: a known private credential appears in staged files. Commit blocked.", file=sys.stderr)
            return 1
        if args.history and history_contains(ROOT, credentials):
            print("STOP: a known private credential appears in reachable Git history. Push blocked.", file=sys.stderr)
            return 1
        print("Known current, retired, vaulted provider and analyst credentials are absent from staged content" + (" and reachable Git history." if args.history else "."))
        return 0
    except Exception:
        print("Credential check could not finish safely; no secret content was printed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
