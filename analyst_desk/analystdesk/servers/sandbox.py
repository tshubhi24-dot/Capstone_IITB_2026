"""python-sandbox MCP server — run calculation code in isolation.

Tool:
    run_python   execute pandas/numpy code on given data; return result + stdout

The quant agent does every calculation here (rule 1: no arithmetic inside
the LLM). The code is written by a model, so it is untrusted.

Isolation (SANDBOX_MODE):
    docker  a fresh container per call: no network, read-only filesystem,
            non-root user, all capabilities dropped, memory/CPU/process limits.
            This is the security boundary.
    local   a separate Python process with no environment secrets and the
            runner's import guard + audit hooks. A guard, not a boundary —
            for machines without Docker and for tests.
    auto    (default) docker when available, otherwise local.
Every result reports which mode actually ran, so traces show it.

Both modes run the same runner (sandbox_runner.py) and enforce a time limit.

Run standalone (stdio):  python -m analystdesk.servers.sandbox
Build the image:        docker build -t analystdesk-sandbox -f docker/sandbox/Dockerfile .
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from .common import READ_ONLY, ToolError, ToolResult, fail, serve, structured_errors

RUNNER = Path(__file__).with_name("sandbox_runner.py")
IMAGE = os.getenv("SANDBOX_IMAGE", "analystdesk-sandbox:latest")
MAX_CODE_CHARS = 20_000
DOCKER_STARTUP_S = int(os.getenv("SANDBOX_DOCKER_STARTUP_S", "30"))

mcp = FastMCP(
    "python-sandbox",
    instructions=(
        "Run Python to calculate: pandas as pd and numpy as np are available, the "
        "input is in `data`, and the answer must be assigned to `result`. No network, "
        "no files, no other imports. Use it for every calculation."
    ),
)


class RunResult(ToolResult):
    result: Any = None
    stdout: str = ""
    blocked: list[str] = []
    sandbox_mode: Literal["docker", "local"] | None = None


@lru_cache(maxsize=1)
def docker_available() -> bool:
    """Docker CLI present and the sandbox image built (checked once per process)."""
    if not shutil.which("docker"):
        return False
    try:
        probe = subprocess.run(["docker", "image", "inspect", IMAGE],
                               capture_output=True, timeout=30)   # Docker Desktop may be waking from Resource Saver
        return probe.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _mode() -> str:
    mode = os.getenv("SANDBOX_MODE", "auto").lower()
    if mode == "auto":
        return "docker" if docker_available() else "local"
    return mode


def _docker_cmd(name: str) -> list[str]:
    return [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network", "none",                 # no network at all
        "--read-only", "--tmpfs", "/tmp:size=16m",
        "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--user", "65534:65534",             # nobody
        IMAGE,
    ]


def _local_cmd() -> list[str]:
    # -I: ignore PYTHON* env vars and user site; -B: never write .pyc files
    return [sys.executable, "-I", "-B", str(RUNNER)]


def _local_env() -> dict[str, str]:
    """No inherited environment: API keys and secrets never reach the code."""
    keep = ("SYSTEMROOT", "WINDIR", "TEMP", "TMP")   # needed for Python on Windows
    return {k: os.environ[k] for k in keep if k in os.environ}


@mcp.tool(annotations=READ_ONLY)
@structured_errors(RunResult)
def run_python(
    code: Annotated[str, Field(description="Python using `data`, pd and np; assign the answer "
                                "to `result`. Example: result = data['op'] / data['rev'] * 100")],
    data: Annotated[Any, Field(description="JSON input available to the code as `data`")] = None,
    timeout_s: Annotated[int, Field(ge=1, le=30, description="Time limit in seconds")] = 10,
) -> RunResult:
    """Run calculation code in an isolated sandbox and return `result`."""
    if not code.strip():
        return fail(RunResult, "BAD_INPUT", "code is empty")
    if len(code) > MAX_CODE_CHARS:
        return fail(RunResult, "BAD_INPUT", f"code longer than {MAX_CODE_CHARS} characters")

    mode = _mode()
    request = json.dumps({"code": code, "data": data, "timeout_s": timeout_s})
    name = f"sbx-{uuid.uuid4().hex[:12]}"
    if mode == "docker":
        cmd, env, cwd = _docker_cmd(name), None, None
    elif mode == "local":
        cmd, env, cwd = _local_cmd(), _local_env(), tempfile.gettempdir()
    else:
        return fail(RunResult, "BAD_INPUT", f"SANDBOX_MODE must be docker, local or auto; got {mode}")

    try:
        proc = subprocess.run(cmd, input=request, capture_output=True, text=True,
                              # container start-up, plus waking Docker Desktop's VM after idle
                              timeout=timeout_s + (DOCKER_STARTUP_S if mode == "docker" else 0),
                              env=env, cwd=cwd)
    except subprocess.TimeoutExpired:
        if mode == "docker":
            # Backstop: the runner also stops itself at the limit
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)
        result = fail(RunResult, "TIMEOUT", f"code ran longer than {timeout_s}s and was stopped")
        result.sandbox_mode = mode
        return result

    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = fail(RunResult, "EXEC_ERROR",
                      f"sandbox exited without a result (exit {proc.returncode}): "
                      f"{proc.stderr.strip()[-500:]}")
        result.sandbox_mode = mode
        return result

    result = RunResult(ok=out["ok"], result=out.get("result"), stdout=out.get("stdout", ""),
                       blocked=out.get("blocked", []), sandbox_mode=mode)
    if not out["ok"]:
        result.error = ToolError(**out["error"])
    return result


if __name__ == "__main__":
    serve(mcp)
