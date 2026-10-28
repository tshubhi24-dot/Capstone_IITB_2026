"""FastAPI service and the mounted research UI."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]
ResearchRunner = Callable[[str, dict[str, Any], EventCallback], Awaitable[dict[str, Any]]]


class ResearchRequest(BaseModel):
    request: str = Field(min_length=1, max_length=4000)
    mode: Literal["c1", "c2"] = "c1"
    analyst: str = Field(default="analyst", min_length=1, max_length=80)
    memory_on: bool = True


class ResearchDecision(BaseModel):
    action: Literal["approve", "edit", "reject"]
    plan: dict[str, Any] | None = None
    note: dict[str, Any] | None = None
    approver: str = Field(default="analyst", min_length=1, max_length=80)
    reason: str = Field(default="", max_length=1000)


async def _run_until_gate(
    run_id: str, payload: dict[str, Any], on_event: EventCallback
) -> dict[str, Any]:
    from .agent.runtime import run_until_gate

    if "resume" in payload:
        from langgraph.types import Command

        payload = Command(resume=payload["resume"])
    return await run_until_gate(run_id, payload, on_event, transport="inprocess")


async def _load_run(run_id: str) -> dict[str, Any]:
    from .agent.runtime import get_run

    return await get_run(run_id)


def _event(name: str, data: dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(data)}\n\n"


def _run_summary(run_id: str, result: dict[str, Any]) -> dict[str, Any]:
    values = result.get("values", {})
    interrupts = result.get("interrupts", [])
    gate = interrupts[0] if interrupts else {}
    gate_name = gate.get("gate")

    if gate_name == "plan":
        status = "waiting_for_plan_approval"
    elif gate_name == "note":
        status = "waiting_for_note_approval"
    else:
        status = values.get("outcome") or "completed"

    return {
        "run_id": run_id,
        "status": status,
        "plan": gate.get("plan") or values.get("plan"),
        "draft": gate.get("note") or values.get("draft"),
        "check": gate.get("check") or values.get("check"),
    }


def create_app(
    ui: Any | None = None,
    runner: ResearchRunner | None = None,
    run_loader: Callable[[str], Awaitable[dict[str, Any]]] | None = None,
) -> FastAPI:
    """Create the API service and optionally mount the existing Gradio Blocks UI."""
    app = FastAPI(title="Analyst Desk API", version="1.0.0")
    run_research = runner or _run_until_gate
    load_run = run_loader or _load_run

    @app.get("/healthz", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readiness() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/api/research", tags=["research"])
    async def research(body: ResearchRequest) -> StreamingResponse:
        request_text = body.request.strip()
        analyst = body.analyst.strip()
        if not request_text:
            raise HTTPException(status_code=422, detail="request must not be blank")
        if not analyst:
            raise HTTPException(status_code=422, detail="analyst must not be blank")

        run_id = uuid.uuid4().hex
        payload = {
            "request": request_text,
            "mode": body.mode,
            "analyst": analyst,
            "memory_on": body.memory_on,
        }
        return StreamingResponse(
            stream_run(run_id, payload),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/research/{run_id}/decision", tags=["research"])
    async def decide(run_id: str, body: ResearchDecision) -> StreamingResponse:
        snapshot = await load_run(run_id)
        if not snapshot.get("values"):
            raise HTTPException(status_code=404, detail="research run not found")
        interrupts = snapshot.get("interrupts", [])
        if not interrupts:
            raise HTTPException(status_code=409, detail="research run is not waiting for approval")

        gate = interrupts[0].get("gate")
        decision = body.model_dump(exclude={"plan", "note", "approver", "reason"})
        if gate == "plan":
            if body.action == "reject":
                raise HTTPException(status_code=422, detail="the plan gate supports approve or edit")
            if body.action == "edit":
                if body.plan is None:
                    raise HTTPException(status_code=422, detail="an edited plan is required")
                decision["plan"] = body.plan
        elif gate == "note":
            if body.action == "edit":
                if not body.note or not isinstance(body.note.get("body"), str):
                    raise HTTPException(status_code=422, detail="an edited note body is required")
                decision["note"] = body.note
            elif body.action == "approve":
                if not body.approver.strip():
                    raise HTTPException(status_code=422, detail="approver must not be blank")
                decision["approver"] = body.approver.strip()
            else:
                decision["reason"] = body.reason or "no reason given"
        else:
            raise HTTPException(status_code=409, detail="research run has an unknown approval gate")

        return StreamingResponse(
            stream_run(run_id, {"resume": decision}),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def stream_run(run_id: str, payload: dict[str, Any]):
        events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        async def on_event(event: dict[str, Any]) -> None:
            await events.put(event)

        task = asyncio.create_task(run_research(run_id, payload, on_event))
        try:
            yield _event("started", {"run_id": run_id})
            while not (task.done() and events.empty()):
                try:
                    event = await asyncio.wait_for(events.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield _event("progress", event)
            yield _event("result", _run_summary(run_id, task.result()))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Research run %s failed", run_id)
            yield _event(
                "error",
                {
                    "run_id": run_id,
                    "error": "research_run_failed",
                    "detail": "The research run failed; check the application logs.",
                },
            )
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    if ui is not None:
        import gradio as gr

        app = gr.mount_gradio_app(app, ui, path="/", theme=gr.themes.Soft())

    return app
