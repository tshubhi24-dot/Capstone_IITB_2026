"""Bounded OpenRouter access and durable, conservative spending reservations.

Only the model gateway uses the provider credential. Failed or uncertain calls
are never retried automatically. An uncertain charge retains its reservation.
"""
from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

import httpx
from jsonschema import Draft202012Validator

PROVIDER_URL = "https://openrouter.ai/api/v1/chat/completions"
GATEWAY_URL = "http://model-gateway:8020"
ROLES = {"planner", "researcher", "risk", "writer", "critic"}
MODEL_RATES = {
    "openai/gpt-4.1-mini": (Decimal("0.0000004"), Decimal("0.0000016")),
    "openai/gpt-4.1": (Decimal("0.000002"), Decimal("0.000008")),
}
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,180}$")
HTTP_DIAGNOSTIC_STATUSES = frozenset({301, 302, 303, 307, 308, 400, 401, 402, 403, 404, 408, 409, 413, 415, 422, 429, 500, 502, 503, 504})
SAFE_ERROR_CODES = frozenset({
    "invalid_configuration", "authorization_changed", "call_id_conflict", "call_not_retriable", "accounting_blocked",
    "budget_exhausted", "run_limit_exhausted", "call_state_conflict", "accounting_anomaly", "live_not_authorized",
    "provider_key_missing", "invalid_request", "provider_request_failed", "provider_response_invalid", "provider_usage_uncertain",
    "model_output_invalid", "gateway_configuration_invalid", "gateway_request_failed", "gateway_unavailable", "unauthorized",
    "provider_http_3xx", "provider_http_4xx", "provider_http_5xx", "provider_http_unexpected_status",
    "provider_connect_timeout", "provider_read_timeout", "provider_write_timeout", "provider_pool_timeout",
    "provider_timeout", "provider_connect_error", "provider_network_error", "provider_protocol_error",
    "provider_response_too_large", "provider_response_json_invalid", "provider_response_shape_invalid", "provider_error_envelope",
    "provider_usage_missing", "provider_usage_invalid", "provider_usage_tokens_missing", "provider_usage_tokens_invalid",
    "provider_usage_inconsistent", "provider_usage_cost_missing", "provider_usage_cost_invalid",
}) | frozenset(f"provider_http_{status}" for status in HTTP_DIAGNOSTIC_STATUSES)


def safe_error_code(value):
    """Allowlisted public diagnosis only; never echo an arbitrary upstream code."""
    return value if isinstance(value, str) and value in SAFE_ERROR_CODES else "gateway_request_failed"


def http_error_code(status):
    if status in HTTP_DIAGNOSTIC_STATUSES:
        return f"provider_http_{status}"
    if 300 <= status < 400:
        return "provider_http_3xx"
    if 400 <= status < 500:
        return "provider_http_4xx"
    if 500 <= status < 600:
        return "provider_http_5xx"
    return "provider_http_unexpected_status"


def diagnostic_code(error):
    if isinstance(error, ProviderError):
        return safe_error_code(error.code)
    for kind, code in ((httpx.ConnectTimeout, "provider_connect_timeout"), (httpx.ReadTimeout, "provider_read_timeout"),
                       (httpx.WriteTimeout, "provider_write_timeout"), (httpx.PoolTimeout, "provider_pool_timeout"),
                       (httpx.TimeoutException, "provider_timeout"), (httpx.ConnectError, "provider_connect_error"),
                       (httpx.NetworkError, "provider_network_error"), (httpx.ProtocolError, "provider_protocol_error")):
        if isinstance(error, kind):
            return code
    return "provider_usage_uncertain"


class ProviderError(RuntimeError):
    """A safe public error: never includes request/response bodies or secrets."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def decimal(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ProviderError("invalid_configuration", "A finite nonnegative budget or price is required.") from exc
    if not result.is_finite() or result < 0:
        raise ProviderError("invalid_configuration", "A finite nonnegative budget or price is required.")
    return result


def validate_config(value):
    required = {"enabled", "authorization_id", "version", "cap_usd", "per_run_usd", "max_calls_per_run",
                "max_tokens_per_run", "prompt_token_ceiling", "max_message_bytes", "max_output_tokens", "models"}
    if not isinstance(value, dict) or set(value) != required or type(value.get("enabled")) is not bool:
        raise ProviderError("invalid_configuration", "The live model configuration is incomplete or contains unknown fields.")
    if any(not isinstance(value[key], str) or not IDENTIFIER.fullmatch(value[key]) for key in ("authorization_id", "version")):
        raise ProviderError("invalid_configuration", "A versioned model spending authorization is required.")
    for key in ("cap_usd", "per_run_usd"):
        if decimal(value[key]) <= 0:
            raise ProviderError("invalid_configuration", "Positive authorization and run spending limits are required.")
    if decimal(value["per_run_usd"]) > decimal(value["cap_usd"]):
        raise ProviderError("invalid_configuration", "The run limit exceeds the authorization limit.")
    bounds = {"max_calls_per_run": (1, 20), "max_tokens_per_run": (1, 500000),
              "prompt_token_ceiling": (8192, 65536), "max_message_bytes": (1, 60000), "max_output_tokens": (1, 4096)}
    for key, (low, high) in bounds.items():
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ProviderError("invalid_configuration", "A model call or context limit is invalid.")
    if value["max_message_bytes"] + 4096 > value["prompt_token_ceiling"]:
        raise ProviderError("invalid_configuration", "The prompt reservation must include formatting overhead.")
    models = value["models"]
    if not isinstance(models, dict) or set(models) != {"producer", "critic"}:
        raise ProviderError("invalid_configuration", "Both producing and critic model policies are required.")
    for role, expected in (("producer", "openai/gpt-4.1-mini"), ("critic", "openai/gpt-4.1")):
        policy = models[role]
        if not isinstance(policy, dict) or set(policy) != {"id", "prompt_usd_per_token", "completion_usd_per_token"} or policy["id"] != expected:
            raise ProviderError("invalid_configuration", "Only the reviewed producing and critic model IDs are allowed.")
        for field, ceiling in zip(("prompt_usd_per_token", "completion_usd_per_token"), MODEL_RATES[expected]):
            if not 0 < decimal(policy[field]) <= ceiling:
                raise ProviderError("invalid_configuration", "The model price exceeds the reviewed price ceiling.")
    return json.loads(encoded(value))


class BudgetLedger:
    def __init__(self, path, config):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config
        policy = {key: val for key, val in config.items() if key != "enabled"}
        self.policy_hash = hashlib.sha256(encoded(policy)).hexdigest()
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS authorization(id TEXT PRIMARY KEY,policy_hash TEXT NOT NULL,blocked INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS model_calls(call_id TEXT PRIMARY KEY,authorization_id TEXT NOT NULL,run_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,status TEXT NOT NULL,reserved_usd TEXT NOT NULL,reserved_tokens INTEGER NOT NULL,
                    charged_usd TEXT,usage TEXT,result TEXT,error_code TEXT,created REAL NOT NULL);
            """)
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT policy_hash FROM authorization WHERE id=?", (config["authorization_id"],)).fetchone()
            if previous and previous[0] != self.policy_hash:
                raise ProviderError("authorization_changed", "An existing spending authorization cannot change its model, price or limits.")
            db.execute("INSERT OR IGNORE INTO authorization(id,policy_hash) VALUES(?,?)", (config["authorization_id"], self.policy_hash))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def totals(rows):
        charge = sum((decimal(row["charged_usd"]) for row in rows if row["charged_usd"] is not None), Decimal(0))
        held = sum((decimal(row["reserved_usd"]) for row in rows if row["charged_usd"] is None), Decimal(0))
        tokens = sum(json.loads(row["usage"])["total_tokens"] if row["usage"] else row["reserved_tokens"] for row in rows)
        return charge, held, tokens

    def reserve(self, run_id, call_id, request_hash, usd, tokens):
        config = self.config
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT * FROM model_calls WHERE call_id=?", (call_id,)).fetchone()
            if previous:
                if previous["run_id"] != run_id or previous["request_hash"] != request_hash or previous["authorization_id"] != config["authorization_id"]:
                    raise ProviderError("call_id_conflict", "A model call identifier cannot be reused for different content.")
                if previous["status"] == "succeeded":
                    return json.loads(previous["result"])
                raise ProviderError("call_not_retriable", "This call is pending or failed; it cannot incur another automatic charge.")
            authorization = db.execute("SELECT blocked FROM authorization WHERE id=?", (config["authorization_id"],)).fetchone()
            if authorization[0]:
                raise ProviderError("accounting_blocked", "Model spending is blocked after an accounting anomaly.")
            rows = db.execute("SELECT * FROM model_calls WHERE authorization_id=?", (config["authorization_id"],)).fetchall()
            run_rows = [row for row in rows if row["run_id"] == run_id]
            charge, held, _ = self.totals(rows)
            run_charge, run_held, run_tokens = self.totals(run_rows)
            if charge + held + usd > decimal(config["cap_usd"]) or run_charge + run_held + usd > decimal(config["per_run_usd"]):
                raise ProviderError("budget_exhausted", "The remaining authorized model budget cannot cover this call.")
            if len(run_rows) >= config["max_calls_per_run"] or run_tokens + tokens > config["max_tokens_per_run"]:
                raise ProviderError("run_limit_exhausted", "The original run call or token budget is exhausted.")
            db.execute("INSERT INTO model_calls(call_id,authorization_id,run_id,request_hash,status,reserved_usd,reserved_tokens,created) VALUES(?,?,?,?,?,?,?,?)",
                       (call_id, config["authorization_id"], run_id, request_hash, "reserved", str(usd), tokens, time.time()))
        return None

    def uncertain(self, call_id, code):
        with self.connection() as db:
            db.execute("UPDATE model_calls SET status='uncertain',error_code=? WHERE call_id=? AND status='reserved'", (safe_error_code(code), call_id))

    def settle(self, call_id, usage, result, error_code=None):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM model_calls WHERE call_id=?", (call_id,)).fetchone()
            if not row or row["status"] != "reserved":
                raise ProviderError("call_state_conflict", "The model call is not awaiting accounting.")
            anomaly = decimal(usage["cost_usd"]) > decimal(row["reserved_usd"]) or usage["total_tokens"] > row["reserved_tokens"]
            state = "accounting_anomaly" if anomaly else ("invalid_output" if error_code else "succeeded")
            db.execute("UPDATE model_calls SET status=?,charged_usd=?,usage=?,result=?,error_code=? WHERE call_id=?",
                       (state, str(usage["cost_usd"]), json.dumps(usage), json.dumps(result) if result else None,
                        "accounting_anomaly" if anomaly else error_code, call_id))
            if anomaly:
                db.execute("UPDATE authorization SET blocked=1 WHERE id=?", (row["authorization_id"],))
        if anomaly:
            raise ProviderError("accounting_anomaly", "Provider usage exceeded its reservation; further model spending is blocked.")

    def summary(self, run_id=None):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM model_calls WHERE authorization_id=?", (self.config["authorization_id"],)).fetchall()
            blocked = bool(db.execute("SELECT blocked FROM authorization WHERE id=?", (self.config["authorization_id"],)).fetchone()[0])
        selected = [row for row in rows if row["run_id"] == run_id] if run_id is not None else rows
        charge, held, tokens = self.totals(selected)
        global_charge, global_held, _ = self.totals(rows)
        return {"enabled": self.config["enabled"], "authorization_id": self.config["authorization_id"], "config_version": self.config["version"],
                "cap_usd": str(self.config["cap_usd"]), "per_run_usd": str(self.config["per_run_usd"]),
                "reported_spend_usd": str(charge), "held_usd": str(held), "committed_usd": str(charge + held),
                "authorization_committed_usd": str(global_charge + global_held),
                "remaining_authorization_usd": str(max(Decimal(0), decimal(self.config["cap_usd"]) - global_charge - global_held)),
                "model_calls": len(selected), "tokens": tokens, "uncertain_calls": sum(row["status"] == "uncertain" for row in selected),
                "blocked": blocked, "run_id": run_id}


class ReasoningGateway:
    def __init__(self, config, ledger_path, api_key="", transport=None):
        self.config = validate_config(config)
        self.ledger = BudgetLedger(ledger_path, self.config)
        self.api_key, self.transport = api_key, transport

    def budget(self, run_id=None):
        result = self.ledger.summary(run_id)
        result["provider_key_configured"] = bool(self.api_key)
        return result

    def complete(self, *, run_id, call_id, role, messages, response_schema, max_output_tokens):
        config = self.config
        if not config["enabled"]:
            raise ProviderError("live_not_authorized", "Live model calls have not been authorized.")
        if not self.api_key or len(self.api_key) < 20:
            raise ProviderError("provider_key_missing", "The provider credential is not configured.")
        if role not in ROLES or any(not isinstance(v, str) or not IDENTIFIER.fullmatch(v) for v in (run_id, call_id)):
            raise ProviderError("invalid_request", "A valid run, call and model role are required.")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= config["max_output_tokens"]:
            raise ProviderError("invalid_request", "The requested model output exceeds its limit.")
        if not isinstance(messages, list) or not 1 <= len(messages) <= 12 or any(not isinstance(m, dict) or set(m) != {"role", "content"} or m["role"] not in {"system", "user", "assistant"} or not isinstance(m["content"], str) for m in messages):
            raise ProviderError("invalid_request", "Only bounded text messages are supported.")
        bounded = {"messages": messages, "response_schema": response_schema}
        if len(encoded(bounded)) > config["max_message_bytes"] or self.api_key.encode() in encoded(bounded):
            raise ProviderError("invalid_request", "The model context is too large or contains a provider credential.")
        try:
            def reject_external_refs(node):
                if isinstance(node, dict):
                    if "$ref" in node and (not isinstance(node["$ref"], str) or not node["$ref"].startswith("#/")):
                        raise ValueError("External schema references are forbidden")
                    for child in node.values():
                        reject_external_refs(child)
                elif isinstance(node, list):
                    for child in node:
                        reject_external_refs(child)
            reject_external_refs(response_schema)
            Draft202012Validator.check_schema(response_schema)
            validator = Draft202012Validator(response_schema)
        except Exception as exc:
            raise ProviderError("invalid_request", "A valid local JSON response schema is required.") from exc
        policy = config["models"]["critic" if role == "critic" else "producer"]
        estimate = decimal(policy["prompt_usd_per_token"]) * config["prompt_token_ceiling"] + decimal(policy["completion_usd_per_token"]) * max_output_tokens
        request = {"run_id": run_id, "call_id": call_id, "role": role, **bounded, "max_output_tokens": max_output_tokens,
                   "model": policy["id"], "config_version": config["version"]}
        request_hash = hashlib.sha256(encoded(request)).hexdigest()
        cached = self.ledger.reserve(run_id, call_id, request_hash, estimate, config["prompt_token_ceiling"] + max_output_tokens)
        if cached is not None:
            return {**cached, "cached": True}
        payload = {"model": policy["id"], "messages": messages, "max_tokens": max_output_tokens, "temperature": 0,
                   "response_format": {"type": "json_schema", "json_schema": {"name": "analyst_response", "strict": True, "schema": response_schema}},
                   "provider": {"only": ["openai"], "allow_fallbacks": False, "require_parameters": True, "data_collection": "deny",
                                "max_price": {"prompt": float(decimal(policy["prompt_usd_per_token"]) * 1000000), "completion": float(decimal(policy["completion_usd_per_token"]) * 1000000)}}}
        network_error = None
        try:
            with httpx.Client(transport=self.transport, timeout=120, trust_env=False, follow_redirects=False) as client:
                with client.stream("POST", PROVIDER_URL, headers={"Authorization": "Bearer " + self.api_key}, json=payload) as response:
                    if response.status_code != 200:
                        raise ProviderError(http_error_code(response.status_code), "The model provider refused the request; it will not be retried automatically.")
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 2000000:
                            raise ProviderError("provider_response_too_large", "The model provider response exceeded its limit.")
                        chunks.append(chunk)
            try:
                data = json.loads(b"".join(chunks))
            except (ValueError, UnicodeError):
                raise ProviderError("provider_response_json_invalid", "The provider response is not valid JSON.") from None
            if not isinstance(data, dict):
                raise ProviderError("provider_response_shape_invalid", "The provider response has an invalid shape.")
            if "error" in data:
                raise ProviderError("provider_error_envelope", "The provider returned an error envelope.")
            if "usage" not in data:
                raise ProviderError("provider_usage_missing", "The provider did not report usage.")
            raw_usage = data["usage"]
            if not isinstance(raw_usage, dict):
                raise ProviderError("provider_usage_invalid", "The provider usage has an invalid shape.")
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if key not in raw_usage:
                    raise ProviderError("provider_usage_tokens_missing", "The provider did not report all token counts.")
                if type(raw_usage[key]) is not int or raw_usage[key] < 0:
                    raise ProviderError("provider_usage_tokens_invalid", "The provider token counts are invalid.")
            if raw_usage["total_tokens"] != raw_usage["prompt_tokens"] + raw_usage["completion_tokens"] or raw_usage["total_tokens"] == 0:
                raise ProviderError("provider_usage_inconsistent", "The provider token totals are inconsistent.")
            if "cost" not in raw_usage:
                raise ProviderError("provider_usage_cost_missing", "The provider did not report the call charge.")
            try:
                cost = decimal(raw_usage["cost"])
            except ProviderError:
                raise ProviderError("provider_usage_cost_invalid", "The provider charge is invalid.") from None
            returned_model = data.get("model")
            safe_model = returned_model if isinstance(returned_model, str) and returned_model in MODEL_RATES else "unapproved"
            usage = {"model_calls": 1, **{key: raw_usage[key] for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
                     "cost_usd": str(cost), "model": policy["id"], "requested_model": policy["id"],
                     "returned_model": safe_model, "call_id": call_id}
        except Exception as exc:
            network_error = diagnostic_code(exc)
            self.ledger.uncertain(call_id, network_error)
        # Raise outside the exception handler: a transport/JSON exception can
        # retain private headers or response text in its context or cause.
        if network_error is not None:
            raise ProviderError(network_error, "The provider outcome or charge is uncertain; its full reservation is retained and no automatic retry is allowed.")
        result, output_error = None, None
        try:
            if returned_model != policy["id"]:
                raise ValueError("The returned model is not the exact approved model")
            if raw_usage["prompt_tokens"] > config["prompt_token_ceiling"]:
                raise ValueError("The provider prompt exceeded its token ceiling")
            if raw_usage["completion_tokens"] > max_output_tokens:
                raise ValueError("The provider completion exceeded its token ceiling")
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete model output")
            content = json.loads(choice["message"]["content"])
            if self.api_key.encode() in encoded(content):
                raise ValueError("A provider credential cannot enter a model result")
            validator.validate(content)
            if not isinstance(content, dict):
                raise ValueError("Expected object output")
            result = {"content": content, "usage": usage, "config_version": config["version"], "cached": False}
        except Exception:
            output_error = "model_output_invalid"
        self.ledger.settle(call_id, usage, result, output_error)
        if output_error:
            raise ProviderError(output_error, "The model response failed its schema or completion checks; no automatic paid retry was made.")
        return result


class ModelGatewayClient:
    def __init__(self, token, base_url=GATEWAY_URL, transport=None):
        if base_url != GATEWAY_URL or not isinstance(token, str) or len(token) < 32:
            raise ProviderError("gateway_configuration_invalid", "The internal model gateway address and credential are required.")
        self.token, self.base_url, self.transport = token, base_url, transport

    @classmethod
    def from_environment(cls):
        try:
            config = json.loads(Path(os.environ["SCOPED_CONFIG"]).read_text())
            return cls(config["model_token"], os.getenv("MODEL_GATEWAY_URL", GATEWAY_URL))
        except (KeyError, OSError, ValueError) as exc:
            raise ProviderError("gateway_configuration_invalid", "The internal model gateway configuration is unavailable.") from exc

    def _request(self, method, path, **kwargs):
        try:
            with httpx.Client(transport=self.transport, timeout=180, trust_env=False, follow_redirects=False) as client:
                response = client.request(method, self.base_url + path, headers={"X-Model-Token": self.token}, **kwargs)
            if response.status_code != 200:
                try:
                    code = response.json().get("error", {}).get("code", "gateway_request_failed")
                except Exception:
                    code = "gateway_request_failed"
                raise ProviderError(safe_error_code(code), "The model gateway blocked or failed the operation.")
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Invalid gateway output")
            return result
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError("gateway_unavailable", "The model gateway is unavailable; no automatic paid retry was requested.") from exc

    def complete(self, **kwargs):
        return self._request("POST", "/v1/reason", json=kwargs)

    def budget(self, run_id=None):
        return self._request("GET", "/v1/budget", params={"run_id": run_id} if run_id is not None else None)
