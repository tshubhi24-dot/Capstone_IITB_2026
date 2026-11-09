"""Run the C1 agent to its next human gate — shared by the CLI and the app.

Tools are always reached over MCP, through one of three transports:
    inprocess  in-memory MCP clients for the four servers (the app: no
               subprocesses, and filings-kb reuses the app's loaded index)
    stdio      one subprocess per server (CLI default during development)
    http       Docker Compose services (when MCP_URL_<SERVER> is set)
The protocol, tool schemas and results are identical in all three.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from ..llm_config import LLM_CONFIG

ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINTS = Path(os.getenv("AGENT_CHECKPOINTS", ROOT / "data" / "runs" / "checkpoints.sqlite"))
RESEARCH_TOOLS = {"search_filings", "get_passage", "list_filings", "get_financials",
                  "get_fact", "run_python", "get_past_notes"}
# Tools that read earlier notes: memory, so a memory-off run does not get them at all
MEMORY_TOOLS = {"get_past_notes"}

Event = dict[str, Any]


def make_llm(model_role: str = "agent"):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=LLM_CONFIG.model(model_role),
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
        temperature=0,
        timeout=120,
    )


@contextlib.asynccontextmanager
async def open_tools(transport: str = "auto"):
    """All MCP tools, over the chosen transport, for the length of one run."""
    from langchain_mcp_adapters.tools import load_mcp_tools
    async with contextlib.AsyncExitStack() as stack:
        tools = []
        if transport == "inprocess":
            from fastmcp import Client
            from ..servers import edgar_server, filings_kb, portal, sandbox
            for module in (filings_kb, edgar_server, sandbox, portal):
                client = await stack.enter_async_context(Client(module.mcp))
                tools += await load_mcp_tools(client.session)
        else:
            from ..servers.client import make_client
            client = make_client()
            for name in client.connections:
                session = await stack.enter_async_context(client.session(name))
                tools += await load_mcp_tools(session)
        yield tools


_passages: dict[str, str] | None = None


def passage_text(pid: str) -> str | None:
    global _passages
    if _passages is None:
        from ..ingest import load_passages
        _passages = {p["passage_id"]: p["text"] for p in load_passages()}
    return _passages.get(pid)


def _tool_events(value: dict) -> list[Event]:
    """Tool results from a ToolNode update, as display events."""
    events = []
    for m in (value or {}).get("messages", []):
        content = m.content if isinstance(m.content, str) else json.dumps(m.content)
        text = content
        try:   # adapter returns [{"type": "text", "text": "<json>"}]
            blocks = json.loads(content)
            if isinstance(blocks, list) and blocks and isinstance(blocks[0], dict):
                text = blocks[0].get("text", content)
        except (ValueError, TypeError):
            pass
        ok = '"ok":true' in text.replace(" ", "")
        events.append({"node": "tool_result", "tool": getattr(m, "name", "?"), "ok": ok,
                       "preview": text[:400]})
    return events


async def run_until_gate(run_id: str, payload, on_event: Callable[[Event], Awaitable[None]] | None = None,
                         transport: str = "auto") -> dict:
    """Run from a request or Command(resume=...) to the next gate or the end.

    A new run's payload may set "mode": "c1" (single agent, default) or "c2"
    (team). A resumed run keeps the mode it was started with.
    """
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    CHECKPOINTS.parent.mkdir(parents=True, exist_ok=True)
    async with open_tools(transport) as tools, AsyncSqliteSaver.from_conn_string(str(CHECKPOINTS)) as saver:
        if isinstance(payload, dict):
            payload = {**payload, "mode": payload.get("mode", "c1")}
            mode = payload["mode"]
            memory_on = payload.get("memory_on", True)
        else:
            mode = await _mode_of(saver, run_id)
            memory_on = await _memory_on(saver, run_id)
        research = research_tools(tools, memory_on)
        publish = next(t for t in tools if t.name == "publish_note")
        graph = _build(mode, make_llm(), research, publish, passage_text, live=True).compile(checkpointer=saver)
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 150}
        from .. import observability as obs
        tokens_before = int((await graph.aget_state(config)).values.get("tokens", 0) or 0)
        started = time.perf_counter()
        with obs.run_span(run_id, mode) as span:
            result = await _stream(graph, payload, config, on_event)
            values = result["values"]
            obs.record_tokens(mode, int(values.get("tokens", 0) or 0) - tokens_before)
            obs.record_run(mode, values, result["interrupts"], time.perf_counter() - started, span)
        return result


async def _stream(graph, payload, config, on_event) -> dict:
    """Stream the graph to the next gate, passing each event on; return the snapshot."""
    async for kind, chunk in graph.astream(payload, config, stream_mode=["updates", "custom"]):
        if kind == "custom":      # live tool events from the C2 specialists
            events = [chunk]
        else:
            events = []
            for node, value in chunk.items():
                if node == "__interrupt__":
                    continue
                events += _tool_events(value) if node == "tools" else (value or {}).get("trace", [])
        for ev in events:
            if on_event:
                await on_event(ev)
    return await _snapshot(graph, config)


def _build(mode: str, llm, research, publish, passage_text_fn, live: bool = False):
    if mode == "c2":
        from .team import build_team_graph, make_judge_llm
        return build_team_graph(llm, research, publish, passage_text_fn,
                                judge_llm=make_judge_llm() if live else None)
    from .graph import build_graph
    return build_graph(llm, research, publish, passage_text_fn)


def research_tools(tools: list, memory_on: bool) -> list:
    """The research tools for one run; without memory, no tool that reads earlier notes.

    Evaluation runs (AGENT_EVAL=1) are always memory-off, as in graph.input_guard.
    """
    memory_on = memory_on and os.getenv("AGENT_EVAL") != "1"
    return [t for t in tools if t.name in RESEARCH_TOOLS and (memory_on or t.name not in MEMORY_TOOLS)]


async def _mode_of(saver, run_id: str) -> str:
    """The mode a saved run was started with (c1 for runs from before C2 existed)."""
    tup = await saver.aget_tuple({"configurable": {"thread_id": run_id}})
    if tup is None:
        return "c1"
    return (tup.checkpoint.get("channel_values") or {}).get("mode") or "c1"


async def _memory_on(saver, run_id: str) -> bool:
    """Whether a saved run uses memory (set by its input guard; on for old runs)."""
    tup = await saver.aget_tuple({"configurable": {"thread_id": run_id}})
    if tup is None:
        return True
    return (tup.checkpoint.get("channel_values") or {}).get("memory_on", True) is not False


async def get_run(run_id: str) -> dict:
    """Current state of a saved run, without calling any model or tool."""
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    if not CHECKPOINTS.exists():
        return {"values": {}, "interrupts": [], "next": []}
    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINTS)) as saver:
        graph = _build(await _mode_of(saver, run_id), _NoModel(), [], None, None).compile(checkpointer=saver)
        return await _snapshot(graph, {"configurable": {"thread_id": run_id}})


def _status(snapshot: dict) -> str:
    v = snapshot["values"]
    if snapshot["interrupts"]:
        return "⏸ waiting: plan approval" if snapshot["interrupts"][0]["gate"] == "plan" \
            else "⏸ waiting: note approval"
    if v.get("guard") and not v["guard"].get("ok"):
        return "⛔ out of scope"
    return {"published": "✅ published", "rejected": "🛑 rejected", "cancelled": "🚫 plan cancelled",
            "publish_failed": "❌ publish refused"}.get(v.get("outcome"), "⏳ in progress / stopped")


async def list_runs(limit: int = 50) -> list[dict]:
    """Every saved run, newest first: id, when, request, status, tools, check."""
    import sqlite3
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    if not CHECKPOINTS.exists():
        return []
    con = sqlite3.connect(f"file:{CHECKPOINTS}?mode=ro", uri=True)
    try:
        ids = [r[0] for r in con.execute(
            "SELECT thread_id FROM checkpoints GROUP BY thread_id "
            "ORDER BY MAX(checkpoint_id) DESC LIMIT ?", (limit,))]
    finally:
        con.close()
    runs = []
    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINTS)) as saver:
        for rid in ids:
            mode = await _mode_of(saver, rid)
            graph = _build(mode, _NoModel(), [], None, None).compile(checkpointer=saver)
            config = {"configurable": {"thread_id": rid}}
            snap = await graph.aget_state(config)
            s = {"values": snap.values, "interrupts": [i.value for t in snap.tasks for i in t.interrupts]}
            check = snap.values.get("check") or {}
            runs.append({
                "run_id": rid,
                "mode": "C2 team" if mode == "c2" else "C1 single",
                "updated": (snap.created_at or "")[:16].replace("T", " "),
                "request": snap.values.get("request", ""),
                "status": _status(s),
                "tool_calls": snap.values.get("tool_calls", 0),
                "check": f"{check['verified']}/{check['total']}" if check else "",
            })
    return runs


async def _snapshot(graph, config) -> dict:
    snap = await graph.aget_state(config)
    return {"values": snap.values, "interrupts": [i.value for t in snap.tasks for i in t.interrupts],
            "next": list(snap.next)}


class _NoModel:
    """Stand-in model for building the graph without calling an API."""
    def bind_tools(self, tools):
        return self
