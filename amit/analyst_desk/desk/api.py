"""Local analyst desk with explicit offline or budget-authorized live runs."""
from contextlib import asynccontextmanager
import asyncio
from decimal import Decimal
import hmac
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal

from .data import Corpus
from .store import Store, canonical_hash
from .workflow import Engine, ReviewError, validate_scope, citation_review_options
from .provider import ModelGatewayClient, ProviderError
from .model_profiles import model_profile, model_route

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
    max_model_calls: int | None = Field(default=12, ge=1, le=12)
    memory_enabled: bool = Field(default=True, strict=True)
    lessons_enabled: bool = Field(default=False, strict=True)
    playbook_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    critic_enabled: Literal[True] = True
    table_aware: Literal[True] = True
    defences_enabled: Literal[True] = True
    plant_error: Literal[False] = False
    inject_article: Literal[False] = False
    learning_split: Literal["production", "development"] = "production"
    development_case_id: str | None = Field(default=None, pattern=r"^KDEV[0-9]{3}$")

    @model_validator(mode="after")
    def learning_controls(self):
        if self.lessons_enabled != (self.playbook_id is not None):
            raise ValueError("Choose one frozen playbook when enabling reviewed lessons.")
        if self.learning_split == "production" and self.development_case_id is not None:
            raise ValueError("Ordinary research cannot claim a development case.")
        return self


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["plan", "note"]
    action: Literal["approve", "edit", "reject", "recheck"]
    payload_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    edits: dict | None = None


class Continuation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retry_transient: bool = Field(default=False, strict=True)
    replace_critic_policy: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    critic_extension: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def exclusive_continuation_mode(self):
        if sum((self.retry_transient, self.replace_critic_policy is not None, self.critic_extension is not None)) > 1:
            raise ValueError("Choose one explicit continuation mode.")
        return self


def owned(run_id):
    run = app.state.engine.view(run_id)
    if not run or run.get("actor") != "local-analyst":
        raise HTTPException(404, "Research run not found.")
    return run


class MemoryPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    default_companies: list[str] | None = Field(default=None, min_length=1, max_length=4)
    default_years: list[int] | None = Field(default=None, min_length=1, max_length=3)
    report_style: Literal["table_first", "summary_first"] | None = None
    history_limit: int | None = Field(default=None, ge=0, le=3)


class MemoryRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int = Field(ge=0)


class MemoryPreferencesWrite(MemoryRevision):
    values: MemoryPreferences


class MemoryEligibility(MemoryRevision):
    excluded: bool


class MemorySearch(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=1, max_length=3000)
    tickers: list[str] = Field(min_length=1, max_length=4)
    years: list[int] = Field(min_length=1, max_length=3)
    k: int = Field(default=3, ge=1, le=3)


def analyst_memory():
    return app.state.engine.memory


@app.get("/api/memory/preferences")
def memory_preferences():
    return analyst_memory().get_preferences("local-analyst")


@app.put("/api/memory/preferences")
def save_memory_preferences(value: MemoryPreferencesWrite):
    from .memory import MemoryConflict
    values = value.values.model_dump(exclude_none=True)
    companies, years = values.get("default_companies"), values.get("default_years")
    known = {row["ticker"] for row in app.state.source.companies()}
    if companies is not None and (len(set(companies)) != len(companies) or not set(companies) <= known):
        raise HTTPException(400, "Saved defaults must select covered companies without duplicates.")
    if years is not None:
        issuers = companies or sorted(known)
        if years != sorted(set(years)) or any(not set(years) <= set(app.state.source.years(ticker)) for ticker in issuers):
            raise HTTPException(400, "Saved fiscal years must be covered, unique and in ascending order.")
    try:
        return analyst_memory().put_preferences("local-analyst", values, value.expected_revision)
    except MemoryConflict as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.delete("/api/memory/preferences")
def delete_memory_preferences(value: MemoryRevision):
    from .memory import MemoryConflict
    try:
        return analyst_memory().delete_preferences("local-analyst", value.expected_revision)
    except MemoryConflict as error:
        raise HTTPException(409, str(error)) from error


@app.get("/api/memory/coverage")
def memory_coverage():
    return analyst_memory().remember_coverage(app.state.source, "local-analyst")


@app.get("/api/memory/note-policy")
def memory_note_policy():
    return analyst_memory().get_note_policy("local-analyst")


@app.post("/api/memory/history/search")
def search_memory_history(value: MemorySearch):
    from .history import search_approved_notes
    try:
        validate_scope({"tickers": value.tickers, "years": value.years}, app.state.source)
        refs = search_approved_notes(app.state.store, analyst_memory(), value.query,
            value.tickers, value.years, value.k, actor="local-analyst",
            current_source_fingerprint=app.state.source.fingerprint)
        return {"references": refs, "note_policy": memory_note_policy(),
                "source_fingerprint": app.state.source.fingerprint,
                "model_calls": 0, "interpretation": "Historical context; current source analysis is separate."}
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.put("/api/memory/notes/{note_id}/eligibility")
def memory_note_eligibility(note_id: str, value: MemoryEligibility):
    from .memory import MemoryConflict
    if app.state.store.approved_note(note_id, "local-analyst") is None:
        raise HTTPException(404, "Approved note not found.")
    try:
        return analyst_memory().set_note_excluded("local-analyst", note_id, value.excluded, value.expected_revision)
    except MemoryConflict as error:
        raise HTTPException(409, str(error)) from error
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@app.get("/api/memory/notes/{note_id}/comparison")
def compare_memory_note(note_id: str):
    from .memory_comparison import compare_approved_note
    record = app.state.store.approved_note(note_id, "local-analyst")
    if record is None or note_id in memory_note_policy()["excluded_note_ids"]:
        raise HTTPException(404, "Approved note is unavailable for memory use.")
    return compare_approved_note(record, app.state.source)


class LessonReflection(MemoryRevision):
    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    event_id: int = Field(ge=1)
    mode: Literal["rules", "live"] = "rules"


class LessonProposalWrite(MemoryRevision):
    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    event_id: int = Field(ge=1)
    action: Literal["align_fiscal_periods", "verify_current_facts", "preserve_risk_qualifiers", "cite_exact_evidence"]
    scope: dict
    summary: str = Field(min_length=8, max_length=600)
    applicability: str = Field(min_length=8, max_length=600)
    counterexamples: str = Field(min_length=8, max_length=600)
    supersedes: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")


class LessonDecisionWrite(MemoryRevision):
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: Literal["accept", "reject"]
    reason: str = Field(min_length=8, max_length=600)


class LessonRevocationWrite(MemoryRevision):
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    reason: str = Field(min_length=8, max_length=600)


class PlaybookFreeze(MemoryRevision):
    lesson_ids: list[str] = Field(min_length=1, max_length=16)


def lesson_operation(action):
    from .memory import MemoryConflict
    try:
        return action()
    except MemoryConflict as error:
        raise HTTPException(409, str(error)) from error
    except (ValueError, ReviewError) as error:
        raise HTTPException(400, str(error)) from error


@app.get("/api/development/cases")
def development_cases():
    from .development import public_cases
    return {"cases": public_cases(app.state.source), "publication_allowed": False,
            "independent_benchmark": False, "expected_answers_included": False}


@app.get("/api/lessons")
def lessons():
    from .lessons import ACTION_HINTS
    core = app.state.engine.lessons
    return {"bank": core.get_bank(), "lessons": core.list_lessons(),
            "playbooks": core.list_playbooks(), "actions": ACTION_HINTS,
            "human_review_required": True}


@app.post("/api/lessons/reflect")
def reflect_lesson(value: LessonReflection):
    from .reflection import propose_reflection
    owned(value.run_id)
    with app.state.engine.lock(value.run_id):
        return lesson_operation(lambda: propose_reflection(app.state.engine, **value.model_dump()))


@app.post("/api/lessons")
def propose_lesson(value: LessonProposalWrite):
    owned(value.run_id)
    return lesson_operation(lambda: app.state.engine.lessons.propose(**value.model_dump()))


@app.post("/api/lessons/{lesson_id}/decision")
def decide_lesson(lesson_id: str, value: LessonDecisionWrite):
    return lesson_operation(lambda: app.state.engine.lessons.decide(lesson_id, **value.model_dump()))


@app.post("/api/lessons/{lesson_id}/revoke")
def revoke_lesson(lesson_id: str, value: LessonRevocationWrite):
    return lesson_operation(lambda: app.state.engine.lessons.revoke(lesson_id, **value.model_dump()))


@app.post("/api/playbooks")
def freeze_playbook(value: PlaybookFreeze):
    return lesson_operation(lambda: app.state.engine.lessons.freeze_playbook(**value.model_dump()))


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
        profile = model_profile(value.get("model_profile"))
        models = {role: policy["id"] for role, policy in profile["models"].items()}
        if value.get("models") != models or value.get("provider") != profile["provider"]:
            raise ValueError
        safe.update(models=models, model_profile=profile["version"], provider=profile["provider"])
        call_limit = value.get("max_calls_per_run", 12)
        if call_limit is None:
            if profile["version"] != "live-program-models-v1":
                raise ValueError
        elif type(call_limit) is not int or not 1 <= call_limit <= 12:
            raise ValueError
        safe["max_calls_per_run"] = call_limit
        if profile.get("routes"):
            routes = {role: model_route(profile["version"], role) for role in ("producer", "critic")}
            if value.get("model_routes") != routes:
                raise ValueError
            safe["model_routes"] = routes
        version = value.get("config_version")
        if not isinstance(version, str) or not 1 <= len(version) <= 180 or not all(c.isalnum() or c in "_.:-" for c in version):
            raise ValueError
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
    retrieval = retrieval_configuration()
    live_enabled = live_enabled and retrieval.get("ready") is True
    return {"mode": "offline", "data_source": "sec_edgar", "transport": "http", "semantic_retrieval": retrieval.get("semantic_retrieval") is True,
            "available_modes": ["offline", "live"] if live_enabled else ["offline"], "live_enabled": live_enabled,
            "models": (live_budget or {}).get("models", {}),
            "model_routes": (live_budget or {}).get("model_routes", {}),
            "model_profile": (live_budget or {}).get("model_profile"),
            "model_provider": (live_budget or {}).get("provider"),
            "live_budget": live_budget, "live_model_config_version": (live_budget or {}).get("config_version"),
            "retrieval": retrieval.get("mode"), "retrieval_details": retrieval,
            "model_config_version": "fresh-step4-offline-v1", "source_fingerprint": source.fingerprint,
            "companies": companies, "years": sorted({year for company in companies for year in source.years(company["ticker"])}),
            "company_years": {company["ticker"]: source.years(company["ticker"]) for company in companies}}


def retrieval_configuration():
    """Read actual filings service readiness; configuration alone is not evidence."""
    mode = os.getenv("RETRIEVAL_MODE", "bm25")
    if mode == "bm25":
        return {"mode": mode, "ready": True, "semantic_retrieval": False, "backend": "bm25"}
    try:
        value = asyncio.run(app.state.engine._wire_call("planner", "filings-kb", "retrieval_status", {}))
        if (not isinstance(value, dict) or value.get("mode") != mode or value.get("ready") is not True
                or value.get("source_fingerprint") != app.state.source.fingerprint
                or value.get("semantic_retrieval") is not True):
            raise ValueError("Retrieval service identity differs from this desk.")
        return value
    except Exception:
        return {"mode": mode, "ready": False, "semantic_retrieval": False, "backend": "unavailable"}


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
        from .development import admit_development
        request = admit_development(request, app.state.source)
        validate_scope(request, app.state.source)
    except (ReviewError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    if retrieval_configuration().get("ready") is not True:
        raise HTTPException(409, "The configured retrieval index is unavailable or stale. Prepare and verify it before starting research.")
    if value.mode == "live":
        live_budget, enabled = gateway_budget()
        if not enabled:
            raise HTTPException(409, "Live AI is unavailable or its approved budget is disabled, blocked or exhausted. No offline run was substituted.")
        if live_budget["max_calls_per_run"] is None:
            request["max_model_calls"] = None
        elif value.max_model_calls is None:
            raise HTTPException(400, "This model policy requires a call-count limit.")
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


@app.get("/api/runs/{run_id}/citation-options")
def citation_options(run_id: str, draft_hash: str = Query(pattern=r"^[a-f0-9]{64}$")):
    current = owned(run_id)
    pending = current.get("pending") or {}
    draft = pending.get("payload") or {}
    if (current.get("status") != "awaiting_note" or pending.get("kind") != "note"
            or pending.get("payload_hash") != draft_hash or canonical_hash(draft) != draft_hash
            or draft.get("model_mode") != "live"
            or draft.get("source_fingerprint") != app.state.source.fingerprint):
        raise HTTPException(409, "The exact live note review changed; reopen it before choosing evidence.")
    try:
        return citation_review_options(draft)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(409, "The note's selected evidence cannot support citation editing.") from exc


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
                validate_scope({**(current.get("pending") or {}).get("payload", {}), **value.edits,
                                "mode": current["request"].get("mode", "offline")}, app.state.source)
            elif ("body" not in value.edits or set(value.edits) - {"body", "citation_selections"}
                  or not isinstance(value.edits["body"], str) or len(value.edits["body"]) > 100000):
                raise ReviewError("A note edit needs a bounded body and optional selected evidence choices.")
            elif "citation_selections" in value.edits and current.get("request", {}).get("mode") != "live":
                raise ReviewError("Selected evidence choices apply only to live note review.")
        except (ReviewError, TypeError) as exc:
            raise HTTPException(400, str(exc)) from exc
    try:
        app.state.engine.claim(run_id, value.model_dump())
    except ReviewError as exc:
        raise HTTPException(409, str(exc)) from exc
    background.add_task(app.state.engine.execute, run_id)
    return owned(run_id)


@app.post("/api/runs/{run_id}/continue", status_code=202)
def continue_research(run_id: str, value: Continuation, background: BackgroundTasks):
    current = owned(run_id)
    if current.get("actor") != "local-analyst":
        raise HTTPException(404, "Research run not found.")
    if any(run["status"] in {"queued", "running"} for run in app.state.store.list_runs("local-analyst")):
        raise HTTPException(409, "Wait for the current research operation to pause.")
    _, enabled = gateway_budget()
    if not enabled:
        raise HTTPException(409, "Live AI is unavailable or its original spending authorization is disabled, blocked or exhausted.")
    try:
        if value.retry_transient:
            app.state.engine.claim_continuation(run_id, value.plan_hash, retry_transient=True)
        elif value.critic_extension is not None:
            app.state.engine.claim_continuation(run_id, value.plan_hash, critic_extension=value.critic_extension)
        elif value.replace_critic_policy is not None:
            app.state.engine.claim_continuation(run_id, value.plan_hash, replace_critic_policy=value.replace_critic_policy)
        else:
            app.state.engine.claim_continuation(run_id, value.plan_hash)
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
