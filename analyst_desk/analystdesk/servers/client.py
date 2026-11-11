"""Load MCP tools into LangChain/LangGraph, filtered per agent.

Each server runs as its own process over stdio (development); inside Docker
the same servers will be reached over HTTP. langchain-mcp-adapters turns each
MCP tool schema into a LangChain tool an agent can call.

load_agent_tools("quant") returns only the quant agent's tools (see
AGENT_TOOLS), so an agent cannot even see a tool it is not allowed to use.
Hooks (Phase 6) attach in the graph, not here: agent/hooks.py is called
explicitly inside C2's specialist loop and wraps C1's ToolNode.

What does attach here is the Fix 1 guardrail (guardrails.py): every tool is
built with the UNSOURCED_ADVICE interceptor, so a write whose text recommends
without citing anything is refused before the tool runs. Build tools with
load_guarded_tools() rather than langchain-mcp-adapters' load_mcp_tools()
directly, or that guardrail is simply not installed.

Note: by default the adapter starts a fresh server process for every tool
call. filings-kb takes ~30 s to load its index, so agent runs (Phase 4)
should hold persistent sessions (client.session(name) + load_mcp_tools) for
the length of a run.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

from . import AGENT_TOOLS, SERVERS, guardrails

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

# Least privilege applied to secrets, not just tools (L7): each secret names the
# only servers that need it, and is withheld from every other one. compose.yaml
# does the same for the HTTP deployment — APPROVAL_SECRET appears in the
# research-portal service's environment and in no other.
_SECRET_ENV = {
    "OPENROUTER_API_KEY": frozenset(),                   # no server calls a model
    "APPROVAL_SECRET": frozenset({"research-portal"}),   # only the portal verifies tokens
}


def _env_for(server: str) -> dict[str, str]:
    """The environment one server is started with: everything except the
    secrets it has no use for."""
    return {k: v for k, v in os.environ.items()
            if k not in _SECRET_ENV or server in _SECRET_ENV[k]}


def _url_var(name: str) -> str:
    """Env var holding a server's HTTP URL, e.g. MCP_URL_FILINGS_KB."""
    return "MCP_URL_" + name.upper().replace("-", "_")


def connections(servers: list[str] | None = None) -> dict:
    """stdio subprocesses, or HTTP when MCP_URL_<SERVER> is set (Docker Compose)."""
    out = {}
    for name, module in SERVERS.items():
        if servers is not None and name not in servers:
            continue
        url = os.getenv(_url_var(name))
        if url:
            out[name] = {"transport": "streamable_http", "url": url}
        else:
            out[name] = {"transport": "stdio", "command": sys.executable, "args": ["-m", module],
                         "cwd": str(PROJECT_DIR), "env": _env_for(name)}
    return out


# Fix for Module 4 - Security (Fix 1 - use case 3, injected recommendation).
# Default, not opt-in: a guardrail you have to remember to pass is a guardrail
# that is missing from the run where it mattered.
def make_client(servers: list[str] | None = None, interceptors: list | None = None) -> MultiServerMCPClient:
    """The MCP client, with the Fix 1 guardrail installed unless replaced.

    interceptors=[] switches the guardrail off — only tests do that, to show
    what the unguarded call returns.
    """
    chain = guardrails.interceptors() if interceptors is None else list(interceptors)
    return MultiServerMCPClient(connections(servers), tool_interceptors=chain)


# Fix for Module 4 - Security (Fix 1 - use case 3). The adapter's
# load_mcp_tools() takes its interceptors per call, so a tool loaded straight
# from a session carries no guardrail at all.
async def load_guarded_tools(session, interceptors: list | None = None, **kwargs) -> list:
    """Every tool on one MCP session, each wrapped in the Fix 1 guardrail."""
    from langchain_mcp_adapters.tools import load_mcp_tools
    chain = guardrails.interceptors() if interceptors is None else list(interceptors)
    return await load_mcp_tools(session, tool_interceptors=chain, **kwargs)


async def load_agent_tools(agent: str, client: MultiServerMCPClient | None = None) -> list:
    """The LangChain tools this agent is allowed to use, and no others."""
    if agent not in AGENT_TOOLS:
        raise KeyError(f"Unknown agent {agent!r}; known: {sorted(AGENT_TOOLS)}")
    allowed = AGENT_TOOLS[agent]
    client = client or make_client()
    return [t for t in await client.get_tools() if t.name in allowed]
