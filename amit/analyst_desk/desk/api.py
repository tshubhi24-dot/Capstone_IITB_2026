"""Local analyst desk with explicit offline or budget-authorized live runs."""
from contextlib import asynccontextmanager
import asyncio
from decimal import Decimal
import hmac
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .data import Corpus
from .store import Store
from .workflow import Engine, ReviewError, validate_scope
from .provider import ModelGatewayClient, ProviderError

ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app):
    if os.getenv("ANALYST_MODE", "offline") != "offline":
        raise RuntimeError("The desk's default stays offline; choose live mode explicitly per research run.")
    app.state.source = Corpus(os.getenv("CORPUS_PATH", "/sources/corpus.json"))
    app.state.store = Store()
    client = None
    if os.getenv("MODEL_GATEWAY_URL"):
        try:
            client = ModelGatewayClient.from_environment()
        except ProviderError:
            # Offline inspection remains available, but live creation is blocked.
            pass
    app.state.engine = Engine(app.state.store, app.state.source, os.getenv("RUNTIME_DIR", "/runtime"), model_client=client)
    yield
    app.state.engine.close()


app = FastAPI(title="Analyst Desk · first research journey", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


@app.middleware("http")
async def boundary(request, call_next):
    path = request.url.path
    if path.startswith("/api/") or path in {"/metrics", "/docs", "/openapi.json"}:
        token = os.getenv("ANALYST_API_TOKEN", "")
        supplied = request.headers.get("X-Analyst-Token", "")
        metrics_ok = path == "/metrics" and bool(os.getenv("ANALYST_METRICS_TOKEN")) and hmac.compare_digest(request.headers.get("X-Analyst-Metrics-Token", ""), os.environ["ANALYST_METRICS_TOKEN"])
        if not metrics_ok and (not token or not hmac.compare_digest(token, supplied)):
            return JSONResponse({"detail": "Enter the local analyst token in Connection settings."}, status_code=401)
        origin = request.headers.get("Origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and urlsplit(origin).netloc != request.url.netloc:
            return JSONResponse({"detail": "Cross-origin changes are not allowed."}, status_code=403)
    response = await call_next(request)
    response.headers.update({"X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin", "Content-Security-Policy": "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"})
    return response


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=8, max_length=3000)
    tickers: list[str] = Field(default_factory=lambda: ["MSFT", "AAPL"])
    years: list[int] = Field(default_factory=lambda: [2023, 2024, 2025])
    strategy: Literal["multi"] = "multi"
    mode: Literal["offline", "live"] = "offline"
    max_tool_calls: int = Field(default=60, ge=1, le=200)
    max_tokens: int = Field(default=100000, ge=100, le=500000)
    max_model_calls: int = Field(default=12, ge=1, le=12)
    memory_enabled: Literal[True] = True
    critic_enabled: Literal[True] = True
    table_aware: Literal[True] = True
    defences_enabled: Literal[True] = True
    plant_error: Literal[False] = False
    inject_article: Literal[False] = False
    learning_split: Literal["production"] = "production"


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["plan", "note"]
    action: Literal["approve", "edit", "reject"]
    payload_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    edits: dict | None = None


def owned(run_id):
    run = app.state.engine.view(run_id)
    if not run:
        raise HTTPException(404, "Research run not found.")
    return run


@app.get("/")
def home():
    return FileResponse(ROOT / "web/index.html")


@app.get("/health")
def health():
    return {"status": "ok", "mode": "offline", "data_source": "sec_edgar"}


def gateway_budget():
    """Read safe accounting metadata only; this never requests a completion."""
    client = getattr(app.state.engine, "model_client", None)
    if client is None:
        return None, False
    try:
        value = client.budget()
        if not isinstance(value, dict):
            raise ValueError
        safe = {}
        for key in ("cap_usd", "per_run_usd", "reported_spend_usd", "held_usd", "committed_usd",
                    "authorization_committed_usd", "remaining_authorization_usd"):
            amount = Decimal(str(value[key]))
            if not amount.is_finite() or amount < 0:
                raise ValueError
            safe[key] = str(amount)
        for key in ("model_calls", "tokens", "uncertain_calls"):
            if type(value[key]) is not int or value[key] < 0:
                raise ValueError
            safe[key] = value[key]
        for key in ("enabled", "blocked", "provider_key_configured"):
            if type(value[key]) is not bool:
                raise ValueError
            safe[key] = value[key]
        version = value.get("config_version")
        if isinstance(version, str) and len(version) <= 180 and all(c.isalnum() or c in "_.:-" for c in version):
            safe["config_version"] = version
        ready = (safe["enabled"] and safe["provider_key_configured"] and not safe["blocked"]
                 and Decimal(safe["remaining_authorization_usd"]) > 0)
        return safe, ready
    except Exception:
        # Provider errors, credentials and gateway response bodies stay private.
        return {"gateway_status": "unavailable"}, False


@app.get("/api/config")
def config():
    source = app.state.source
    companies = source.companies()
    live_budget, live_enabled = gateway_budget()
    return {"mode": "offline", "data_source": "sec_edgar", "transport": "http", "semantic_retrieval": False,
            "available_modes": ["offline", "live"] if live_enabled else ["offline"], "live_enabled": live_enabled,
            "models": {"producer": "openai/gpt-4.1-mini", "critic": "openai/gpt-4.1"},
            "live_budget": live_budget, "live_model_config_version": (live_budget or {}).get("config_version"),
            "retrieval": "BM25 lexical teaching retrieval; learned vectors and reranker are not active",
            "model_config_version": "fresh-step4-offline-v1", "source_fingerprint": source.fingerprint,
            "companies": companies, "years": sorted({year for company in companies for year in source.years(company["ticker"])}),
            "company_years": {company["ticker"]: source.years(company["ticker"]) for company in companies}}


@app.get("/api/budget")
def budget():
    live_budget, live_enabled = gateway_budget()
    offline = {"cap_usd": 0, "spent_usd": 0, "model_calls": 0, "mode": "offline", "provider_key_configured": False}
    if live_budget is None:
        return offline
    if live_budget.get("gateway_status") == "unavailable":
        return {**offline, "cap_usd": None, "spent_usd": None, "model_calls": None,
                "provider_key_configured": None, "gateway_status": "unavailable",
                "accounting_status": "unavailable", "live_enabled": False}
    return {**live_budget, "spent_usd": float(live_budget["reported_spend_usd"]),
            "mode": "live" if live_enabled else "offline", "live_enabled": live_enabled}


@app.post("/api/runs", status_code=202)
def create(value: ResearchRequest, background: BackgroundTasks):
    request = value.model_dump()
    try:
        validate_scope(request, app.state.source)
    except ReviewError as exc:
        raise HTTPException(400, str(exc)) from exc
    if value.mode == "live":
        _, enabled = gateway_budget()
        if not enabled:
            raise HTTPException(409, "Live AI is unavailable or its approved budget is disabled, blocked or exhausted. No offline run was substituted.")
    if any(run["status"] in {"queued", "running"} for run in app.state.store.list_runs("local-analyst")):
        raise HTTPException(409, "Wait for the current research operation to pause.")
    run = app.state.store.create_run(request)
    background.add_task(app.state.engine.execute, run["id"])
    return run


@app.get("/api/runs")
def runs():
    return app.state.store.list_runs("local-analyst")


@app.get("/api/runs/{run_id}")
def run(run_id: str):
    return owned(run_id)


@app.post("/api/runs/{run_id}/decision", status_code=202)
def decision(run_id: str, value: Decision, background: BackgroundTasks):
    current = owned(run_id)
    if value.action == "edit" and not value.edits or value.action != "edit" and value.edits is not None:
        raise HTTPException(400, "Only edit decisions accept an edits object, and an edit needs that object.")
    if value.action == "edit":
        try:
            if value.kind == "plan":
                if set(value.edits) - {"tickers", "years", "outline"}:
                    raise ReviewError("Unsupported plan edit fields.")
                validate_scope({**(current.get("pending") or {}).get("payload", {}), **value.edits}, app.state.source)
            elif set(value.edits) != {"body"} or not isinstance(value.edits["body"], str) or len(value.edits["body"]) > 100000:
                raise ReviewError("A note edit needs only a body string within the size limit.")
        except (ReviewError, TypeError) as exc:
            raise HTTPException(400, str(exc)) from exc
    try:
        app.state.engine.claim(run_id, value.model_dump())
    except ReviewError as exc:
        raise HTTPException(409, str(exc)) from exc
    background.add_task(app.state.engine.execute, run_id)
    return owned(run_id)


@app.get("/api/runs/{run_id}/events")
async def events(run_id: str, request: Request):
    owned(run_id)
    async def stream():
        for _ in range(600):
            if await request.is_disconnected():
                break
            value = owned(run_id)
            yield "event: update\ndata: " + json.dumps(value) + "\n\n"
            if value["status"] in {"published", "rejected", "error"}:
                break
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/evidence/{evidence_id:path}")
def evidence(evidence_id: str):
    source = app.state.source
    for reader in (source.fact, source.passage):
        try:
            return reader(evidence_id)
        except ValueError:
            continue
    raise HTTPException(404, "Evidence is not in this frozen source snapshot.")


@app.get("/api/notes")
def notes():
    return [{**item["payload"], **{key: value for key, value in item.items() if key != "payload"}} for item in app.state.store.notes("local-analyst")]


@app.get("/api/notes/{note_id}")
def note(note_id: str):
    found = next((item for item in notes() if item["id"] == note_id), None)
    if not found:
        raise HTTPException(404, "Approved note not found.")
    return found


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    saved = app.state.store.list_runs("local-analyst")
    ratio = next((item["critic"]["verified_share"] for item in saved if item.get("critic")), "NaN")
    usage = [item.get("usage", {}) for item in saved]
    costs = [item.get("cost_usd", 0) for item in usage]
    spend = sum(float(value) for value in costs) if all(value is not None for value in costs) else "NaN"
    return (f"analyst_verified_number_share {ratio}\nanalyst_research_runs_total {len(saved)}\n"
            f"analyst_model_calls_total {sum(item.get('model_calls', 0) for item in usage)}\n"
            f"analyst_model_tokens_total {sum(item.get('tokens', 0) for item in usage)}\n"
            f"analyst_model_spend_usd_total {spend}\n"
            f"analyst_tool_calls_total {sum(item.get('tool_calls', 0) for item in usage)}\n"
            f"analyst_published_notes {len(app.state.store.notes('local-analyst'))}\n")
