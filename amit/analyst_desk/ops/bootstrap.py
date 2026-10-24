"""Initialize service-scoped credentials or load one scoped file before exec."""
import json
import os
from pathlib import Path
import secrets
import sys

ROLES = ("planner", "researcher", "quant", "risk", "critic", "publisher")
SERVICE_ROLES = {
    "filings-kb": ("planner", "researcher", "risk", "critic"),
    "edgar": ("researcher", "quant", "risk", "critic"),
    "python-sandbox": ("quant",),
    "research-portal": ("planner", "publisher"),
}


def atomic_write(path, text, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".new")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(text)
    temporary.chmod(mode)
    temporary.replace(path)


def initialize(root=Path("/secrets")):
    app_file = root / "app/config.json"
    if app_file.exists():
        app = json.loads(app_file.read_text())
        if set(app.get("roles", {})) != set(ROLES) or any(len(v) < 32 for v in app["roles"].values()):
            raise ValueError("Existing role credentials are invalid; refusing silent rotation.")
        if any(len(app.get(key, "")) < 32 for key in ("publication_secret", "metrics_token")):
            raise ValueError("Existing signing/metrics credentials are invalid.")
    else:
        app = {"roles": {role: secrets.token_urlsafe(36) for role in ROLES},
               "publication_secret": secrets.token_urlsafe(48), "metrics_token": secrets.token_urlsafe(36)}
    atomic_write(app_file, json.dumps(app) + "\n")
    for service, roles in SERVICE_ROLES.items():
        scoped = {"roles": {role: app["roles"][role] for role in roles}}
        if service == "research-portal":
            scoped["publication_secret"] = app["publication_secret"]
        atomic_write(root / service / "config.json", json.dumps(scoped) + "\n")
    atomic_write(root / "metrics/token", app["metrics_token"], 0o444)
    password = root / "grafana/admin_password"
    if not password.exists():
        atomic_write(password, secrets.token_urlsafe(36), 0o444)
    print("Scoped service credentials are ready; existing credentials were preserved.")


def execute(arguments):
    if not arguments:
        raise ValueError("An executable command is required.")
    location = os.environ.get("SCOPED_CONFIG")
    if location:
        config = json.loads(Path(location).read_text())
        if set(config) - {"roles", "publication_secret", "metrics_token"}:
            raise ValueError("Unexpected scoped credential fields.")
        if config.get("publication_secret"):
            os.environ["PUBLICATION_SECRET"] = config["publication_secret"]
        if config.get("metrics_token"):
            os.environ["ANALYST_METRICS_TOKEN"] = config["metrics_token"]
    os.execvp(arguments[0], arguments)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "init":
        initialize()
    elif len(sys.argv) >= 2 and sys.argv[1] == "exec":
        execute(sys.argv[2:])
    else:
        raise SystemExit("Use bootstrap.py init or bootstrap.py exec COMMAND.")
