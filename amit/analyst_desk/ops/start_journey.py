"""Prepare or start this step's standalone, zero-spend Docker Compose stack."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".runtime/journey"
ENV_FILE = PRIVATE / "credentials.env"
PROJECT = "analyst-desk-journey"
CONTEXT = "desktop-linux"
START_ORDER = ("chroma", "pandas-worker", "filings-kb", "edgar", "python-sandbox", "research-portal",
               "app", "prometheus", "grafana", "ingress")


def docker_binary():
    for candidate in (shutil.which("docker"), str(Path.home() / ".docker/bin/docker"),
                      "/Applications/Docker.app/Contents/Resources/bin/docker"):
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError("Docker Desktop's command-line client is unavailable.")


def clean_environment(docker):
    prefixes = ("COMPOSE_", "DOCKER_", "OPENROUTER_", "ANALYST_", "PAID_", "MCP_", "LANGSMITH_", "LANGCHAIN_", "OTEL_")
    extra = {"HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "SEC_USER_AGENT", "CORPUS_PATH"}
    env = {key: value for key, value in os.environ.items() if key not in extra and not key.startswith(prefixes)}
    env["PATH"] = os.pathsep.join([str(Path(docker).parent), "/Applications/Docker.app/Contents/Resources/bin", env.get("PATH", "")])
    return env


def private_token():
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    PRIVATE.chmod(0o700)
    if ENV_FILE.is_symlink():
        raise RuntimeError("The private environment must be a regular file.")
    if not ENV_FILE.exists():
        descriptor = os.open(ENV_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write("ANALYST_API_TOKEN=" + secrets.token_urlsafe(36) + "\n")
    lines = ENV_FILE.read_text().splitlines()
    if len(lines) != 1 or not lines[0].startswith("ANALYST_API_TOKEN="):
        raise RuntimeError("Unexpected private environment format.")
    token = lines[0].split("=", 1)[1]
    if len(token) < 32 or not all(c.isalnum() or c in "_-" for c in token):
        raise RuntimeError("Invalid analyst credential; refusing silent rotation.")
    ENV_FILE.chmod(0o600)
    return token


def compose(docker):
    return [docker, "--context", CONTEXT, "compose", "--project-name", PROJECT,
            "--project-directory", str(ROOT), "--env-file", str(ENV_FILE), "-f", str(ROOT / "compose.yaml")]


def capture(command, env, token, timeout=30):
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:].replace(token, "[redacted]") or "Docker command failed.")
    return result.stdout


def local_readiness():
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + 30
    for url, field, value in (("http://127.0.0.1:18080/health", "status", "ok"),
                              ("http://127.0.0.1:13080/api/health", "database", "ok")):
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("The research or dashboard was not ready within 30 seconds.")
            try:
                with opener.open(url, timeout=min(8, remaining)) as response:
                    if response.status != 200 or json.load(response).get(field) != value:
                        raise RuntimeError("The research or dashboard readiness check failed.")
                break
            except HTTPError as error:
                if error.code != 502:
                    raise
            except URLError as error:
                if not isinstance(error.reason, (ConnectionRefusedError, TimeoutError)):
                    raise
            except (ConnectionRefusedError, TimeoutError):
                pass
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("The research or dashboard was not ready within 30 seconds.")
            time.sleep(min(2, remaining))


def start_stack(command, env, token):
    """Issue exactly one container start at a time, including dependencies."""
    print("Building this journey's shared application image.", flush=True)
    capture(command + ["--parallel", "1", "build", "app"], env, token, timeout=900)
    print("Initializing private service credentials.", flush=True)
    capture(command + ["up", "--no-deps", "--no-build", "--detach", "init-secrets"], env, token, timeout=120)
    capture(command + ["wait", "init-secrets"], env, token, timeout=120)
    initializer = capture(command + ["ps", "--all", "--quiet", "init-secrets"], env, token).strip()
    if not initializer or "\n" in initializer:
        raise RuntimeError("The credential initializer container is ambiguous or missing.")
    state = capture([command[0], "--context", CONTEXT, "inspect", "--format", "{{.State.Status}} {{.State.ExitCode}}", initializer], env, token).strip()
    if state != "exited 0":
        raise RuntimeError("Private credential initialization did not complete successfully.")
    for service in START_ORDER:
        print(f"Starting {service}.", flush=True)
        options = ["up", "--no-deps", "--no-build", "--detach", "--wait", "--wait-timeout", "120"]
        if service == "ingress":
            # Nginx resolves upstream addresses at startup. Refresh it after
            # rebuilt services have started so it does not retain an old IP.
            options.append("--force-recreate")
        capture(command + options + [service], env, token, timeout=150)
        if service == "chroma":
            prepare_vector_store(command, env, token)
    running = set(capture(command + ["ps", "--status", "running", "--services"], env, token).splitlines())
    if not set(START_ORDER).issubset(running):
        raise RuntimeError("One or more journey services stopped during startup.")
    local_readiness()


def prepare_vector_store(command, env, token):
    """Populate/reuse the frozen vector collection before starting its reader."""
    print("Verifying and preparing the local public-evidence vector store.", flush=True)
    capture(command + ["run", "--rm", "--no-deps", "--pull", "never",
                       "--entrypoint", "python", "filings-kb", "ops/prepare_vector_store.py",
                       "--corpus", "/sources/corpus.json", "--artifacts", "/retrieval",
                       "--chroma-url", "http://chroma:8000", "--wait-seconds", "30"],
            env, token, timeout=120)


def validate(config):
    services = config["services"]
    ports = services["ingress"]["ports"]
    actual = {(p["host_ip"], str(p["published"]), p["target"]) for p in ports}
    if config["name"] != PROJECT or actual != {("127.0.0.1", "18080", 8000), ("127.0.0.1", "13080", 3000)}:
        raise ValueError("Only the dedicated journey project and loopback ports are allowed.")
    if not config["networks"]["backend"].get("internal"):
        raise ValueError("The backend must remain internal.")
    app = services["app"]["environment"]
    if app["ANALYST_MODE"] != "offline" or app["PAID_SPEND_LIMIT_USD"] != "0" or not app.get("ANALYST_API_TOKEN"):
        raise ValueError("The first journey requires authenticated offline zero-spend mode.")
    for name, service in services.items():
        if name != "ingress" and service.get("ports"):
            raise ValueError("Only ingress may publish host ports.")
        if service.get("environment", {}).get("OPENROUTER_API_KEY"):
            raise ValueError("Provider credentials do not belong in this offline stack.")
        if any("docker.sock" in str(m) for m in service.get("volumes", [])):
            raise ValueError("Container access to the Docker socket is prohibited.")
    worker = services["pandas-worker"]
    if worker.get("network_mode") != "none" or {m["target"] for m in worker["volumes"]} != {"/queue"}:
        raise ValueError("The worker may access only its networkless queue.")
    if not worker.get("read_only") or worker.get("cap_drop") != ["ALL"]:
        raise ValueError("The worker must retain its process restrictions.")
    if int(worker.get("mem_limit", 0)) != 268435456 or int(worker.get("pids_limit", 0)) != 32 or float(worker.get("cpus", 0)) != .5:
        raise ValueError("The worker's resource limits must be retained.")
    for name in ("app", "filings-kb", "edgar", "python-sandbox"):
        service = services[name]
        mounts = [m for m in service["volumes"] if m["target"] == "/sources"]
        if len(mounts) != 1 or not mounts[0].get("read_only") or Path(mounts[0]["source"]).resolve() != (PRIVATE / "sources").resolve():
            raise ValueError("Source readers must share the prepared read-only snapshot.")
        if service["environment"]["CORPUS_PATH"] != "/sources/corpus.json" or service["networks"] != {"backend": None}:
            raise ValueError("Source identity and private network must match.")
    retrieval = services["filings-kb"]
    mount = [item for item in retrieval["volumes"] if item["target"] == "/retrieval"]
    expected_env = {"RETRIEVAL_MODE": "hybrid_rerank", "RETRIEVAL_ARTIFACTS": "/retrieval",
                    "CHROMA_URL": "http://chroma:8000", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    if (len(mount) != 1 or not mount[0].get("read_only")
            or Path(mount[0]["source"]).resolve() != (PRIVATE / "retrieval").resolve()
            or any(retrieval["environment"].get(key) != value for key, value in expected_env.items())
            or app.get("RETRIEVAL_MODE") != "hybrid_rerank"):
        raise ValueError("Retrieval requires the prepared read-only bundle and local offline models.")


def prepare(source_corpus=None):
    if source_corpus:
        subprocess.run([sys.executable, str(ROOT / "ops/prepare_sources.py"), "--source-corpus", str(source_corpus)], cwd=ROOT, check=True)
    source = PRIVATE / "sources/corpus.json"
    if not source.is_file():
        raise RuntimeError("Prepare the real-source snapshot first, or pass --source-corpus PATH.")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    token = private_token()
    docker = docker_binary()
    env = clean_environment(docker)
    command = compose(docker)
    config = json.loads(capture(command + ["config", "--format", "json"], env, token))
    validate(config)
    receipt = {"project": PROJECT, "context": CONTEXT, "source_sha256": source_hash,
               "mode": "offline", "retrieval": "BM25 only; no learned vector/reranker claim", "paid_cap_usd": 0,
               "prepared": True, "services_started_by_prepare": False}
    (PRIVATE / "prepared.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Prepared the real-source snapshot and authenticated zero-spend Compose configuration.")
    return command, env, token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--start", action="store_true")
    parser.add_argument("--source-corpus", type=Path)
    args = parser.parse_args()
    try:
        command, env, token = prepare(args.source_corpus)
        if args.start:
            capture([command[0], "--context", CONTEXT, "info", "--format", "{{.ServerVersion}}"], env, token)
            running = capture(command + ["ps", "--status", "running", "--services"], env, token).splitlines()
            if "ingress" not in running:
                for port in (18080, 13080):
                    with socket.socket() as check:
                        try:
                            check.bind(("127.0.0.1", port))
                        except OSError as exc:
                            raise RuntimeError(f"Port {port} is busy; no existing service was stopped.") from exc
            print("Building and starting this journey's services. Human decisions remain pending.", flush=True)
            start_stack(command, env, token)
            print("Research: http://127.0.0.1:18080 · Dashboard: http://127.0.0.1:13080")
        print("The analyst credential is saved privately in .runtime/journey/credentials.env; it was not printed.")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("Journey setup: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
