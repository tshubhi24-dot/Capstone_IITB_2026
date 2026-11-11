"""Sandbox runner: executes one piece of untrusted Python and reports back.

Standalone on purpose (standard library + pandas/numpy only, no package
imports), so the very same file runs as a local subprocess or inside the
sandbox container.

Protocol: one JSON object on stdin  {"code": str, "data": any}
          one JSON object on stdout {"ok", "stdout", "result", "error", "blocked"}
The code sees `data` and `pd`/`np`, and sets `result` to return a value.

Two layers of protection in this process:
  1. Import guard — the code may import only ALLOWED_IMPORTS.
  2. Audit hooks — network, processes, native libraries, file writes and
     deletes are refused at the moment they happen, however they are
     reached (e.g. through a module pandas already loaded).
In local mode this is a guard, not a security boundary: Python code can
find ways around in-process checks. The real boundary is the container
(no network, read-only filesystem, non-root, CPU/memory/process limits).
"""

import builtins
import contextlib
import io
import json
import signal
import sys
import traceback

MAX_STDOUT = 20_000

ALLOWED_IMPORTS = {
    "pandas", "numpy", "math", "statistics", "decimal", "fractions", "datetime",
    "json", "re", "collections", "itertools", "functools", "operator", "typing",
    "dataclasses",
}

BLOCKED_EVENTS = {
    "socket.__new__", "socket.connect", "socket.bind", "socket.getaddrinfo",
    "socket.gethostbyname", "socket.sendto",
    "subprocess.Popen", "os.system", "os.exec", "os.spawn", "os.posix_spawn",
    "os.startfile", "os.fork",
    "ctypes.dlopen", "ctypes.dlsym", "ctypes.call_function",
    "os.remove", "os.rmdir", "os.rename", "os.mkdir", "os.chmod", "shutil.rmtree",
    "shutil.copyfile", "shutil.move", "winreg.OpenKey",
}
WRITE_FLAGS = 0x1 | 0x2 | 0x40 | 0x200 | 0x400   # O_WRONLY|O_RDWR|O_CREAT|O_TRUNC|O_APPEND

blocked: list[str] = []


class SandboxBlocked(PermissionError):
    pass


class SandboxTimeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise SandboxTimeout()


def _audit(event, args):
    if event in BLOCKED_EVENTS:
        blocked.append(event)
        raise SandboxBlocked(f"sandbox blocked: {event}")
    if event == "open":
        mode, flags = (args[1] if len(args) > 1 else None), (args[2] if len(args) > 2 else 0)
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                  (isinstance(flags, int) and flags & WRITE_FLAGS)
        if writing:
            blocked.append("open(write)")
            raise SandboxBlocked(f"sandbox blocked: writing {args[0]!r}")


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if level != 0 or root not in ALLOWED_IMPORTS:
        blocked.append(f"import {name}")
        raise SandboxBlocked(f"sandbox blocked: import {name} (allowed: {sorted(ALLOWED_IMPORTS)})")
    return _real_import(name, globals, locals, fromlist, level)


def _jsonable(value):
    """Best-effort conversion of pandas/numpy results to JSON."""
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    return str(value)


def main() -> None:
    request = json.loads(sys.stdin.read().lstrip("\ufeff"))   # tolerate a UTF-8 BOM
    real_stdout = sys.stdout

    # Load libraries before the hooks so their own start-up is not affected
    import numpy as np
    import pandas as pd

    sys.addaudithook(_audit)   # cannot be removed for the rest of the process

    safe_builtins = dict(vars(builtins))
    safe_builtins["__import__"] = _guarded_import
    for name in ("open", "input", "breakpoint", "exit", "quit", "help"):
        safe_builtins.pop(name, None)
    namespace = {"__builtins__": safe_builtins, "data": request.get("data"),
                 "pd": pd, "np": np, "result": None}

    # The code stops itself at the time limit (Linux, i.e. in the container),
    # so a runaway loop ends even if the host fails to kill the container
    timeout_s = int(request.get("timeout_s") or 0)
    if timeout_s and hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _on_alarm)
        signal.alarm(timeout_s)

    captured = io.StringIO()
    out = {"ok": True, "stdout": "", "result": None, "error": None, "blocked": []}
    try:
        with contextlib.redirect_stdout(captured):
            exec(compile(request["code"], "<sandbox>", "exec"), namespace)
        out["result"] = json.loads(json.dumps(namespace.get("result"), default=_jsonable))
    except SandboxTimeout:
        out.update(ok=False, error={"code": "TIMEOUT",
                                    "message": f"code ran longer than {timeout_s}s and was stopped"})
    except SandboxBlocked as exc:
        out.update(ok=False, error={"code": "BLOCKED", "message": str(exc)})
    except BaseException as exc:   # noqa: BLE001 — report every failure to the caller
        tb = traceback.extract_tb(exc.__traceback__)
        where = next((f"line {f.lineno}" for f in reversed(tb) if f.filename == "<sandbox>"), "")
        out.update(ok=False, error={"code": "EXEC_ERROR",
                                    "message": f"{type(exc).__name__}: {exc} {where}".strip()})
    # Any refused action is reported as BLOCKED — also when a library wrapped
    # the refusal in its own exception (pandas -> urllib -> URLError), or the
    # code caught it and carried on
    out["blocked"] = list(dict.fromkeys(blocked))
    if blocked:
        out.update(ok=False, error={"code": "BLOCKED",
                                    "message": "sandbox blocked: " + ", ".join(out["blocked"])})
    out["stdout"] = captured.getvalue()[:MAX_STDOUT]
    real_stdout.write(json.dumps(out))
    real_stdout.flush()


_real_import = builtins.__import__

if __name__ == "__main__":
    main()
