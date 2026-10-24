"""Local-only first research journey; all model behaviour is explicitly offline."""
from contextlib import asynccontextmanager
import asyncio
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

ROOT = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app):
    if os.getenv("ANALYST_MODE", "offline") != "offline":
        raise RuntimeError("This first journey supports offline mode only; live operation is not silently substituted.")
    app.state.source = Corpus(os.getenv("CORPUS_PATH", "/sources/corpus.json"))
    app.state.store = Store()
    app.state.engine = Engine(app.state.store, app.state.source, os.getenv("RUNTIME_DIR", "/runtime"))
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
    max_tool_calls: int = Field(default=60, ge=1, le=200)
    max_tokens: int = Field(default=100000, ge=100, le=100000)
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


@app.get("/api/config")
def config():
    source = app.state.source
    companies = source.companies()
    return {"mode": "offline", "data_source": "sec_edgar", "transport": "http", "semantic_retrieval": False,
            "retrieval": "BM25 lexical teaching retrieval; learned vectors and reranker are not active",
            "model_config_version": "fresh-step4-offline-v1", "source_fingerprint": source.fingerprint,
            "companies": companies, "years": sorted({year for company in companies for year in source.years(company["ticker"])}),
            "company_years": {company["ticker"]: source.years(company["ticker"]) for company in companies}}


@app.get("/api/budget")
def budget():
    return {"cap_usd": 0, "spent_usd": 0, "model_calls": 0, "mode": "offline", "provider_key_configured": False}


@app.post("/api/runs", status_code=202)
def create(value: ResearchRequest, background: BackgroundTasks):
    request = value.model_dump()
    try:
        validate_scope(request, app.state.source)
    except ReviewError as exc:
        raise HTTPException(400, str(exc)) from exc
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
    return f"analyst_verified_number_share {ratio}\nanalyst_research_runs_total {len(saved)}\nanalyst_model_calls_total 0\nanalyst_tool_calls_total {sum(item.get('usage', {}).get('tool_calls', 0) for item in saved)}\nanalyst_published_notes {len(app.state.store.notes('local-analyst'))}\n"
