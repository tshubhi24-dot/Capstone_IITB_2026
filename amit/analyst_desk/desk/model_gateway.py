"""Internal authenticated gateway; provider credentials never reach tool services."""
from contextlib import asynccontextmanager
import hmac
import json
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .provider import ProviderError, ReasoningGateway


def build_app(engine=None, token=None):
    @asynccontextmanager
    async def lifespan(app):
        if engine is None:
            config = json.loads(Path(os.environ["MODEL_CONFIG_FILE"]).read_text())
            key_path = Path(os.environ.get("OPENROUTER_KEY_FILE", "/run/provider/key"))
            key = key_path.read_text().strip() if key_path.is_file() else ""
            app.state.engine = ReasoningGateway(config, os.environ.get("MODEL_LEDGER_PATH", "/model-ledger/usage.sqlite"), key)
            scoped = json.loads(Path(os.environ["SCOPED_CONFIG"]).read_text())
            app.state.token = scoped["model_token"]
        else:
            app.state.engine, app.state.token = engine, token
        if not isinstance(app.state.token, str) or len(app.state.token) < 32:
            raise RuntimeError("The model gateway requires its private internal credential.")
        yield

    app = FastAPI(title="Analyst Desk model gateway", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        if request.url.path != "/health":
            supplied = request.headers.get("X-Model-Token", "")
            if not supplied or not hmac.compare_digest(supplied.encode(), app.state.token.encode()):
                return JSONResponse({"error": {"code": "unauthorized", "message": "The internal model credential is required."}}, status_code=401)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return JSONResponse({"error": {"code": "invalid_request", "message": "The model request does not match its allowed fields and limits."}}, status_code=422)

    @app.exception_handler(ProviderError)
    async def provider_error(request, error):
        status = 403 if error.code in {"live_not_authorized", "provider_key_missing"} else 429 if error.code in {"budget_exhausted", "run_limit_exhausted"} else 409 if error.code in {"call_id_conflict", "call_not_retriable", "accounting_blocked", "authorization_changed"} else 400 if error.code == "invalid_request" else 502
        return JSONResponse({"error": {"code": error.code, "message": str(error)}}, status_code=status)

    @app.get("/health")
    def health():
        return {"status": "ok", "enabled": app.state.engine.config["enabled"], "config_version": app.state.engine.config["version"]}

    @app.get("/v1/budget")
    def budget(run_id: str | None = None):
        return app.state.engine.budget(run_id)

    @app.post("/v1/reason")
    def reason(value: ReasonRequest):
        return app.state.engine.complete(**value.model_dump())

    return app


class ReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(min_length=1, max_length=180)
    call_id: str = Field(min_length=1, max_length=180)
    role: Literal["planner", "researcher", "risk", "writer", "critic"]
    messages: list[dict] = Field(min_length=1, max_length=12)
    response_schema: dict
    max_output_tokens: int = Field(ge=1, le=4096)


app = build_app()
