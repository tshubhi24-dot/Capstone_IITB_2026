"""Validate and serially start the optional live-model Docker overlay.

This launcher never enables spending and never creates a research request.
"""
import argparse
import json
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ops import prepare_live
from ops import start_journey as base

LIVE_ORDER = ("pandas-worker", "filings-kb", "edgar", "python-sandbox", "research-portal", "chroma",
              "model-gateway", "app", "prometheus", "grafana", "ingress")


def compose(docker):
    return base.compose(docker) + ["-f", str(ROOT / "compose.live.yaml")]


def environment(docker):
    env = base.clean_environment(docker)
    prefixes = ("OPENAI_", "ANTHROPIC_", "GEMINI_", "GOOGLE_", "AZURE_OPENAI_", "MODEL_")
    return {key: value for key, value in env.items() if not key.startswith(prefixes)}


def validate(model):
    """Apply the existing boundaries and the gateway's narrow additional grant."""
    base.validate(model)
    services = model["services"]
    gateway = services["model-gateway"]
    if services["app"]["environment"].get("MODEL_GATEWAY_URL") != "http://model-gateway:8020":
        raise ValueError("The app must use the internal fixed model gateway.")
    if set(gateway.get("networks", {})) != {"backend", "provider-egress"}:
        raise ValueError("Only the model gateway receives the provider egress network.")
    if model["networks"]["provider-egress"].get("internal", False):
        raise ValueError("The provider egress network is not usable.")
    for name, service in services.items():
        if name != "model-gateway" and "provider-egress" in service.get("networks", {}):
            raise ValueError("Other services must not join provider egress.")
        if any(key in service.get("environment", {}) for key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY")):
            raise ValueError("Provider key values do not belong in container environments.")
    if gateway.get("ports") or gateway.get("privileged") or not gateway.get("read_only") or gateway.get("cap_drop") != ["ALL"]:
        raise ValueError("The model gateway must retain its process and network restrictions.")
    if str(gateway.get("user")) != "10001:10001":
        raise ValueError("The model gateway must run as the unprivileged analyst user.")
    expected_environment = {
        "SCOPED_CONFIG": "/run/credentials/config.json",
        "MODEL_CONFIG_FILE": "/run/provider/model_config.json",
        "OPENROUTER_KEY_FILE": "/run/provider/key",
        "MODEL_LEDGER_PATH": "/runtime/model-ledger.sqlite",
    }
    if gateway.get("environment") != expected_environment:
        raise ValueError("Unexpected model gateway environment.")
    mounts = {mount["target"]: mount for mount in gateway.get("volumes", [])}
    if len(mounts) != 4 or set(mounts) != {"/runtime", "/run/credentials", "/run/provider/model_config.json", "/run/provider/key"}:
        raise ValueError("The gateway must not mount app history, tools or extra host files.")
    for target, source in (("/runtime", "model-ledger"), ("/run/credentials", "gateway-auth")):
        mount = mounts[target]
        if mount.get("type") != "volume" or mount.get("source") != source or bool(mount.get("read_only")) != (target != "/runtime"):
            raise ValueError("The gateway needs its own ledger and a read-only scoped credential.")
    for target, source in (("/run/provider/model_config.json", prepare_live.CONFIG_FILE), ("/run/provider/key", prepare_live.KEY_FILE)):
        mount = mounts[target]
        if mount.get("type") != "bind" or not mount.get("read_only") or Path(mount["source"]).resolve() != source.resolve():
            raise ValueError("The gateway may read only the prepared private provider files.")
    initialized = services["init-secrets"]
    if initialized.get("entrypoint") != ["python", "ops/bootstrap.py", "init", "--model-gateway"]:
        raise ValueError("Live credentials require the explicit scoped initializer.")
    auth_mount = [mount for mount in initialized.get("volumes", []) if mount["target"] == "/secrets/model-gateway"]
    if len(auth_mount) != 1 or auth_mount[0].get("source") != "gateway-auth":
        raise ValueError("The initializer must populate the gateway-only credential volume.")


def prepared_configuration():
    config = prepare_live.load_config()
    prepare_live.prepared_key()
    if stat.S_IMODE(prepare_live.PRIVATE.stat().st_mode) != 0o700:
        raise ValueError("The live credential parent directory must remain private.")
    if config["enabled"]:
        receipt = prepare_live.APPROVAL_FILE
        if receipt.is_symlink() or not receipt.is_file() or stat.S_IMODE(receipt.stat().st_mode) != 0o600:
            raise ValueError("Enabled spending requires its matching private authorization record.")
        approved = json.loads(receipt.read_text())
        if approved.get("proposal_hash") != prepare_live.proposal_hash(config) or approved.get("authorization_id") != config["authorization_id"]:
            raise ValueError("The live spending proposal differs from the recorded authorization.")
    return config


def start_stack(command, env, token):
    print("Building the reviewed application image.", flush=True)
    base.capture(command + ["--parallel", "1", "build", "app"], env, token, timeout=900)
    print("Initializing scoped credentials; existing credentials are preserved.", flush=True)
    base.capture(command + ["up", "--no-deps", "--no-build", "--detach", "init-secrets"], env, token, timeout=120)
    base.capture(command + ["wait", "init-secrets"], env, token, timeout=120)
    initializer = base.capture(command + ["ps", "--all", "--quiet", "init-secrets"], env, token).strip()
    if not initializer or "\n" in initializer:
        raise RuntimeError("The live credential initializer is missing or ambiguous.")
    state = base.capture([command[0], "--context", base.CONTEXT, "inspect", "--format", "{{.State.Status}} {{.State.ExitCode}}", initializer], env, token).strip()
    if state != "exited 0":
        raise RuntimeError("Live credential initialization failed.")
    for service in LIVE_ORDER:
        print(f"Starting {service}.", flush=True)
        options = ["up", "--no-deps", "--no-build", "--detach", "--wait", "--wait-timeout", "120"]
        if service == "model-gateway":
            # Private settings are loaded at startup and atomically replaced on
            # approval. Recreate just this service to remount the reviewed file.
            options.append("--force-recreate")
        if service == "ingress":
            # Refresh Nginx's startup-resolved upstream addresses after the
            # rebuilt app and dashboard are running.
            options.append("--force-recreate")
        base.capture(command + options + [service], env, token, timeout=150)
    running = set(base.capture(command + ["ps", "--status", "running", "--services"], env, token).splitlines())
    if not set(LIVE_ORDER).issubset(running):
        raise RuntimeError("One or more live-overlay services stopped during startup.")
    base.local_readiness()


def prepare():
    config = prepared_configuration()
    _, _, token = base.prepare()
    docker = base.docker_binary()
    env = environment(docker)
    command = compose(docker)
    model = json.loads(base.capture(command + ["config", "--format", "json"], env, token))
    validate(model)
    return command, env, token, config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Validate prepared files and render Compose without contacting the daemon.")
    action.add_argument("--start", action="store_true", help="Build and serially start; never enables a spending proposal.")
    args = parser.parse_args()
    try:
        command, env, token, config = prepare()
        print("Live spending proposal: " + ("explicitly authorized" if config["enabled"] else "disabled; no paid requests permitted") + ".")
        if args.start:
            base.capture([command[0], "--context", base.CONTEXT, "info", "--format", "{{.ServerVersion}}"], env, token)
            start_stack(command, env, token)
            print("Research: http://127.0.0.1:18080 · Dashboard: http://127.0.0.1:13080")
        print("No research requests or paid model calls were made by this launcher.")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError) as error:
        print("Live startup: " + (str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
