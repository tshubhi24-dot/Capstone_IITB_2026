"""Shared pieces for the MCP servers (L7).

Every tool returns a typed result with `ok`. On failure, `ok` is False and
`error` says why with a stable code, instead of raising: an agent can read
"NOT_IN_COVERAGE" and adjust its plan, while an exception would end the run.

Codes:
    BAD_INPUT         arguments are well-typed but not valid (e.g. unknown ticker)
    NOT_IN_COVERAGE   valid request outside the 15 companies x FY2022-2024 data
    NOT_FOUND         the requested id does not exist
    APPROVAL_INVALID  publish without a valid approval for this exact note
    ALREADY_EXISTS    the same note was already published
    BLOCKED           the sandbox refused an operation (network, files, imports)
    UNSOURCED_ADVICE  a write was refused because the text takes a position on
                      the security and cites nothing (guardrails.py, Fix 1).
                      Under ADVICE_GUARD_MODE=warn the same finding arrives as
                      an entry in `warnings` on a successful result instead
    APPROVAL_UNSIGNED the named approver has not signed this note with their
                      own private key (signing.py, Fix 2)
    TIMEOUT           the sandbox ran past its time limit
    EXEC_ERROR        sandbox code raised an exception
    INTERNAL          unexpected failure inside the tool (bug), reported not raised

Tool annotations: every tool is marked read or write with MCP's standard
hints, so the marking is part of each tool's published schema.
"""

from __future__ import annotations

import functools
import logging
import os
import traceback
from typing import Any, Literal

from pydantic import BaseModel

log = logging.getLogger("analystdesk.servers")

ErrorCode = Literal[
    "BAD_INPUT", "NOT_IN_COVERAGE", "NOT_FOUND", "APPROVAL_INVALID",
    "ALREADY_EXISTS", "BLOCKED", "TIMEOUT", "EXEC_ERROR", "INTERNAL",
    # Fix for Module 4 - Security (Fix 1 and Fix 2): the two codes Module 4 adds
    "UNSOURCED_ADVICE", "APPROVAL_UNSIGNED",
]

# Data the tools cover; requests outside it get NOT_IN_COVERAGE
COVERED_YEARS = (2022, 2023, 2024)

READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
# Adds a row; never edits or deletes existing notes
WRITE = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True,
         "openWorldHint": False}


class ToolError(BaseModel):
    code: ErrorCode
    message: str


class ToolResult(BaseModel):
    """Base for every tool's result model."""
    ok: bool = True
    error: ToolError | None = None


def fail(result_cls: type[ToolResult], code: ErrorCode, message: str) -> Any:
    return result_cls(ok=False, error=ToolError(code=code, message=message))


def structured_errors(result_cls: type[ToolResult]):
    """Turn an unexpected exception into an INTERNAL error result.

    Expected failures are returned explicitly with fail(); this is the
    safety net so a bug in a tool never crashes the agent run.
    """
    def wrap(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 — reported, not swallowed
                log.error("tool %s failed:\n%s", fn.__name__, traceback.format_exc())
                return fail(result_cls, "INTERNAL", f"{type(exc).__name__}: {exc}")
        return inner
    return wrap


def serve(mcp) -> None:
    """Run a server over the transport chosen by MCP_TRANSPORT.

    stdio (default)  development: the client starts the server as a subprocess
    http             Docker Compose: each server is its own container, reached
                     at http://<service>:<MCP_PORT>/mcp on the internal network
    """
    if os.getenv("MCP_TRANSPORT", "stdio") == "http":
        hosts = [h for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h]
        mcp.run(transport="http", host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8000")),
                show_banner=False, **({"allowed_hosts": hosts} if hosts else {}))
    else:
        mcp.run()
