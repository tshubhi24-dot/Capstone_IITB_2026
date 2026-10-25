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

from desk.model_profiles import MODEL_PROFILES, ROUTE_ONLY_MODEL_POLICIES, UNLIMITED_CALL_PROFILE, model_profile, model_route

PROVIDER_URL = "https://openrouter.ai/api/v1/chat/completions"
GATEWAY_URL = "http://model-gateway:8020"
ROLES = {"planner", "researcher", "risk", "writer", "critic"}
MODEL_RATES = {policy["id"]: (Decimal(policy["prompt_usd_per_token"]), Decimal(policy["completion_usd_per_token"]))
               for profile in MODEL_PROFILES.values() for policy in profile["models"].values()}
MODEL_RATES.update({policy["id"]: (Decimal(policy["prompt_usd_per_token"]), Decimal(policy["completion_usd_per_token"]))
                    for policy in ROUTE_ONLY_MODEL_POLICIES.values()})
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,180}$")
OUTPUT_AUDIT_STAGES = frozenset({"passed", "finish_reason", "content_shape", "json_parse", "schema_validation",
                                "credential_echo", "returned_model", "token_ceiling", "price_ceiling"})
OUTPUT_FINISH_REASONS = frozenset({"stop", "length", "tool_calls", "content_filter", "error"})
OUTPUT_SCHEMA_KEYWORDS = frozenset({"type", "required", "additionalProperties", "properties", "items", "prefixItems", "$ref",
                                    "minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum", "enum", "const",
                                    "pattern", "anyOf", "oneOf", "allOf", "not", "format", "uniqueItems"})
OUTPUT_QUARANTINE_BYTES = 2_000_000
HTTP_DIAGNOSTIC_STATUSES = frozenset({301, 302, 303, 307, 308, 400, 401, 402, 403, 404, 408, 409, 413, 415, 422, 429, 500, 502, 503, 504})
FORBIDDEN_BODY_LIMIT = 16 * 1024
FORBIDDEN_HINT_TYPES = {
    "privacy_policy_violation": "provider_http_403_privacy_policy_hint",
    "data_policy_violation": "provider_http_403_privacy_policy_hint",
    "unsupported_country": "provider_http_403_region_hint",
    "unsupported_region": "provider_http_403_region_hint",
    "unsupported_country_region_territory": "provider_http_403_region_hint",
    "region_restricted": "provider_http_403_region_hint",
    "account_disabled": "provider_http_403_account_access_hint",
    "account_suspended": "provider_http_403_account_access_hint",
    "model_access_denied": "provider_http_403_model_access_hint",
    "model_not_allowed": "provider_http_403_model_access_hint",
    "moderation": "provider_http_403_content_policy_hint",
    "content_policy_violation": "provider_http_403_content_policy_hint",
    "content_filter": "provider_http_403_content_policy_hint",
}
SAFE_ERROR_CODES = frozenset({
    "invalid_configuration", "authorization_changed", "call_id_conflict", "call_not_retriable", "accounting_blocked",
    "budget_exhausted", "run_limit_exhausted", "call_state_conflict", "accounting_anomaly", "live_not_authorized",
    "provider_key_missing", "invalid_request", "desk_budget_increase_forbidden", "provider_request_failed", "provider_response_invalid", "provider_usage_uncertain",
    "model_output_invalid", "gateway_configuration_invalid", "gateway_request_failed", "gateway_unavailable", "unauthorized",
    "provider_http_3xx", "provider_http_4xx", "provider_http_5xx", "provider_http_unexpected_status",
    "provider_connect_timeout", "provider_read_timeout", "provider_write_timeout", "provider_pool_timeout",
    "provider_timeout", "provider_connect_error", "provider_network_error", "provider_protocol_error",
    "provider_response_too_large", "provider_response_json_invalid", "provider_response_shape_invalid", "provider_error_envelope",
    "provider_usage_missing", "provider_usage_invalid", "provider_usage_tokens_missing", "provider_usage_tokens_invalid",
    "provider_usage_inconsistent", "provider_usage_cost_missing", "provider_usage_cost_invalid",
}) | frozenset(f"provider_http_{status}" for status in HTTP_DIAGNOSTIC_STATUSES) | frozenset(FORBIDDEN_HINT_TYPES.values())


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


def forbidden_error_hints(error):
    """Inspect only an error's immediate fixed type/code/message fields."""
    hints = set()
    for field in ("type", "code"):
        value = error.get(field)
        if isinstance(value, str) and value.casefold() in FORBIDDEN_HINT_TYPES:
            hints.add(FORBIDDEN_HINT_TYPES[value.casefold()])
    message = error.get("message")
    if not isinstance(message, str):
        return hints
    text = message.casefold()
    if any(term in text for term in ("privacy settings", "data policy", "data collection")) and any(term in text for term in ("block", "prevent", "not allow", "restricted", "forbidden", "denied")):
        hints.add("provider_http_403_privacy_policy_hint")
    if any(term in text for term in ("country", "region", "location")) and any(term in text for term in ("unsupported", "not supported", "not available", "unavailable", "restricted", "blocked", "not permitted")):
        hints.add("provider_http_403_region_hint")
    if any(term in text for term in ("account", "organization")) and any(term in text for term in ("disabled", "suspended", "banned", "deactivated", "restricted")):
        hints.add("provider_http_403_account_access_hint")
    if any(term in text for term in ("content policy", "moderation", "safety policy")) and any(term in text for term in ("violation", "violates", "blocked", "forbidden", "rejected", "disallowed", "flagged")):
        hints.add("provider_http_403_content_policy_hint")
    if any(term in text for term in ("model", "endpoint")) and any(term in text for term in ("not authorized", "not authorised", "not allowed", "not permitted", "access denied", "permission denied", "access is denied")):
        hints.add("provider_http_403_model_access_hint")
    return hints


def forbidden_response_hint(response):
    """Inspect a small 403 error in memory; retain only a provider-reported hint.

    Unknown, incomplete, HTML, ambiguous, or unreadable bodies stay generic.
    Hitting the limit is conservatively treated as truncation, even if a body
    happens to end at exactly that boundary. One metadata.raw JSON wrapper may
    be inspected; nested metadata/raw wrappers are never traversed. No body,
    message, raw field or header escapes.
    """
    fallback = "provider_http_403"
    try:
        body = bytearray()
        for chunk in response.iter_bytes(chunk_size=4096):
            if len(body) + len(chunk) >= FORBIDDEN_BODY_LIMIT:
                return fallback
            body.extend(chunk)
        data = json.loads(body)
        error = data.get("error") if isinstance(data, dict) else None
        if not isinstance(error, dict):
            return fallback
        hints = forbidden_error_hints(error)
        metadata = error.get("metadata")
        if isinstance(metadata, dict):
            hints.update(forbidden_error_hints({"type": metadata.get("error_type"), "code": metadata.get("provider_code")}))
        if isinstance(metadata, dict) and "raw" in metadata:
            try:
                raw = metadata["raw"]
                if isinstance(raw, str):
                    if len(raw.encode()) >= FORBIDDEN_BODY_LIMIT:
                        return fallback
                    raw = json.loads(raw)
                elif not isinstance(raw, dict) or len(encoded(raw)) >= FORBIDDEN_BODY_LIMIT:
                    raw = None
                nested = raw.get("error", raw) if isinstance(raw, dict) else None
            except Exception:
                nested = None
            if isinstance(nested, dict):
                hints.update(forbidden_error_hints(nested))
        return hints.pop() if len(hints) == 1 else fallback
    except Exception:
        return fallback


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


def contains_provider_credential(value, api_key):
    """Also recognize JSON Unicode escapes without persisting decoded secrets."""
    if not isinstance(value, str) or not api_key:
        return False
    if api_key in value:
        return True
    escaped = "".join("(?:" + re.escape(character) + "|\\\\u" + format(ord(character), "04x") + ")" for character in api_key)
    return re.search(escaped, value, flags=re.IGNORECASE) is not None


def private_output_audit(data, api_key):
    """Keep bounded text candidates inside the gateway ledger, never its API."""
    choices = data.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    raw = message.get("content")
    kind = "string" if isinstance(raw, str) else "null" if raw is None else "boolean" if type(raw) is bool else "object" if isinstance(raw, dict) else "array" if isinstance(raw, list) else "number"
    try:
        raw_bytes = raw.encode(errors="replace") if isinstance(raw, str) else encoded(raw)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        # Diagnostics must never prevent accounting for a known paid response.
        raw_bytes = b""
    candidate = raw if (isinstance(raw, str) and len(raw_bytes) <= OUTPUT_QUARANTINE_BYTES
                        and not any(0xD800 <= ord(character) <= 0xDFFF for character in raw)
                        and not contains_provider_credential(raw, api_key)
                        and not re.search(r"(?:sk-or-v1-[a-fA-F0-9]{32,}|sk-proj-[A-Za-z0-9_-]{24,}|AIza[A-Za-z0-9_-]{35})", raw)) else None
    generation = data.get("id")
    if (not isinstance(generation, str) or not re.fullmatch(r"gen-[0-9A-Za-z-]{1,124}", generation)
            or contains_provider_credential(generation, api_key)):
        generation = None
    finish = choice.get("finish_reason")
    return {"generation_id": generation, "finish_reason": finish if isinstance(finish, str) and finish in OUTPUT_FINISH_REASONS else "missing" if finish is None else "other",
            "content_type": kind, "content_bytes": len(raw_bytes), "content_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "validation_stage": "content_shape", "schema_path": [], "schema_keyword": None, "candidate": candidate}


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
        if key == "max_calls_per_run" and value[key] is None and value["version"] == UNLIMITED_CALL_PROFILE:
            continue
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ProviderError("invalid_configuration", "A model call or context limit is invalid.")
    if value["max_message_bytes"] + 4096 > value["prompt_token_ceiling"]:
        raise ProviderError("invalid_configuration", "The prompt reservation must include formatting overhead.")
    models = value["models"]
    if not isinstance(models, dict) or set(models) != {"producer", "critic"}:
        raise ProviderError("invalid_configuration", "Both producing and critic model policies are required.")
    try:
        profile = model_profile(value)
    except ValueError:
        raise ProviderError("invalid_configuration", "Only a reviewed producing and critic model pair is allowed.") from None
    if any(value[key] > ceiling for key, ceiling in profile.get("limits", {}).items()):
        raise ProviderError("invalid_configuration", "The model context exceeds its reviewed profile limit.")
    for role in ("producer", "critic"):
        expected = profile["models"][role]["id"]
        policy = models[role]
        if not isinstance(policy, dict) or set(policy) != {"id", "prompt_usd_per_token", "completion_usd_per_token"} or policy["id"] != expected:
            raise ProviderError("invalid_configuration", "Only the reviewed producing and critic model IDs are allowed.")
        for field, ceiling in zip(("prompt_usd_per_token", "completion_usd_per_token"), MODEL_RATES[expected]):
            if not 0 < decimal(policy[field]) <= ceiling:
                raise ProviderError("invalid_configuration", "The model price exceeds the reviewed price ceiling.")
    return json.loads(encoded(value))


class BudgetLedger:
    def __init__(self, path, config):
        if config.get("max_calls_per_run") is None and model_profile(config)["version"] != UNLIMITED_CALL_PROFILE:
            raise ProviderError("invalid_configuration", "Only the program profile may omit its call-count ceiling.")
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
                CREATE TABLE IF NOT EXISTS desk_budget(singleton INTEGER PRIMARY KEY CHECK(singleton=1),cap_usd TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS run_limits(run_id TEXT PRIMARY KEY,cap_usd TEXT NOT NULL,max_calls INTEGER NOT NULL,max_tokens INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS run_budget_grants(grant_id TEXT PRIMARY KEY,run_id TEXT NOT NULL UNIQUE,
                    proposal_hash TEXT NOT NULL,proposal TEXT NOT NULL,approval_sha256 TEXT NOT NULL,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS grant_consumptions(grant_id TEXT PRIMARY KEY,call_id TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS run_budget_grant_amendments(grant_id TEXT PRIMARY KEY,run_id TEXT NOT NULL UNIQUE,
                    proposal_hash TEXT NOT NULL,proposal TEXT NOT NULL,approval_sha256 TEXT NOT NULL,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS model_output_audit(call_id TEXT PRIMARY KEY,generation_id TEXT,finish_reason TEXT NOT NULL,
                    content_type TEXT NOT NULL,content_bytes INTEGER NOT NULL,content_sha256 TEXT,validation_stage TEXT NOT NULL,
                    schema_path TEXT NOT NULL,schema_keyword TEXT,candidate TEXT,created REAL NOT NULL);
                CREATE TRIGGER IF NOT EXISTS grant_no_update BEFORE UPDATE ON run_budget_grants BEGIN SELECT RAISE(ABORT,'Run grants are append only'); END;
                CREATE TRIGGER IF NOT EXISTS grant_no_delete BEFORE DELETE ON run_budget_grants BEGIN SELECT RAISE(ABORT,'Run grants are append only'); END;
                CREATE TRIGGER IF NOT EXISTS consumption_no_update BEFORE UPDATE ON grant_consumptions BEGIN SELECT RAISE(ABORT,'Grant consumptions are append only'); END;
                CREATE TRIGGER IF NOT EXISTS consumption_no_delete BEFORE DELETE ON grant_consumptions BEGIN SELECT RAISE(ABORT,'Grant consumptions are append only'); END;
                CREATE TRIGGER IF NOT EXISTS amendment_no_update BEFORE UPDATE ON run_budget_grant_amendments BEGIN SELECT RAISE(ABORT,'Run amendments are append only'); END;
                CREATE TRIGGER IF NOT EXISTS amendment_no_delete BEFORE DELETE ON run_budget_grant_amendments BEGIN SELECT RAISE(ABORT,'Run amendments are append only'); END;
            """)
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute("SELECT policy_hash FROM authorization WHERE id=?", (config["authorization_id"],)).fetchone()
            if previous and previous[0] != self.policy_hash:
                raise ProviderError("authorization_changed", "An existing spending authorization cannot change its model, price or limits.")
            # This dedicated ledger carries one original desk-wide ceiling.
            # Migration seeds it from the unchanged, reviewed cumulative cap;
            # a later model policy cannot create a fresh spending allowance.
            existing_ceiling = db.execute("SELECT cap_usd FROM desk_budget WHERE singleton=1").fetchone()
            if not existing_ceiling and not previous and db.execute("SELECT EXISTS(SELECT 1 FROM authorization)").fetchone()[0]:
                raise ProviderError("authorization_changed", "The original authorization must initialize the cumulative desk ledger before a model policy change.")
            db.execute("INSERT OR IGNORE INTO desk_budget VALUES(1,?)", (str(config["cap_usd"]),))
            self.desk_cap = decimal(db.execute("SELECT cap_usd FROM desk_budget WHERE singleton=1").fetchone()[0])
            if decimal(config["cap_usd"]) > self.desk_cap:
                raise ProviderError("desk_budget_increase_forbidden", "A model policy cannot increase the original cumulative desk budget.")
            db.execute("INSERT OR IGNORE INTO authorization(id,policy_hash) VALUES(?,?)", (config["authorization_id"], self.policy_hash))
            # Old rows did not store separate run-limit metadata. The reviewed
            # limits are unchanged during this migration; retain every row.
            db.execute("INSERT OR IGNORE INTO run_limits SELECT DISTINCT run_id,?,?,? FROM model_calls",
                       (str(config["per_run_usd"]), config["max_calls_per_run"] or 0, config["max_tokens_per_run"]))

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
        tokens = sum(json.loads(row["usage"])["total_tokens"] if row["usage"] and row["status"] != "uncertain" else row["reserved_tokens"] for row in rows)
        return charge, held, tokens

    @staticmethod
    def checkpoint_hash(rows):
        fields = ("call_id", "authorization_id", "run_id", "request_hash", "status", "reserved_usd", "reserved_tokens",
                  "charged_usd", "usage", "error_code", "created")
        return hashlib.sha256(encoded([{key: row[key] for key in fields} for row in sorted(rows, key=lambda row: row["call_id"])])).hexdigest()

    def grant_run_extension(self, proposal, expected_hash, human_confirmation):
        """Record one explicit exact-call approval; never alter original limits.

        This trusted local operator method has no HTTP route. Confirmation text
        is operator-supplied evidence; its digest is retained in the ledger.
        """
        fields = {"grant_id", "run_id", "policy_hash", "plan_hash", "draft_hash", "call_id", "request_hash", "checkpoint_hash",
                  "original_calls", "original_tokens", "max_calls", "max_tokens", "checkpoint_calls", "checkpoint_tokens",
                  "checkpoint_uncertain", "checkpoint_reported_spend_usd", "checkpoint_held_usd", "cap_usd", "per_run_usd",
                  "model_profile", "critic_model", "role", "reserved_tokens", "reservation_usd"}
        amendment = isinstance(proposal, dict) and "parent_grant_id" in proposal
        if amendment:
            fields.add("parent_grant_id")
        if (not isinstance(proposal, dict) or set(proposal) != fields
                or expected_hash != hashlib.sha256(encoded(proposal)).hexdigest()
                or not isinstance(human_confirmation, str) or not human_confirmation.strip()):
            raise ProviderError("invalid_configuration", "An exact reviewed grant and explicit human confirmation are required.")
        hashes = ("policy_hash", "plan_hash", "draft_hash", "call_id", "request_hash", "checkpoint_hash")
        if (any(not isinstance(proposal[key], str) or not re.fullmatch(r"[a-f0-9]{64}", proposal[key]) for key in hashes)
                or not isinstance(proposal["grant_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", proposal["grant_id"])
                or not isinstance(proposal["run_id"], str) or not IDENTIFIER.fullmatch(proposal["run_id"])):
            raise ProviderError("invalid_configuration", "The run grant identifiers are invalid.")
        if amendment and (not isinstance(proposal["parent_grant_id"], str) or not re.fullmatch(r"[a-f0-9]{32}", proposal["parent_grant_id"])
                          or proposal["grant_id"] == proposal["parent_grant_id"]):
            raise ProviderError("invalid_configuration", "The parent grant identifier is invalid.")
        exact = {"original_calls": 12, "original_tokens": 250000, "max_calls": 14 if amendment else 13, "max_tokens": 350000 if amendment else 300000,
                 "checkpoint_calls": 13 if amendment else 12, "checkpoint_tokens": 254246 if amendment else 246409, "checkpoint_uncertain": 3, "reserved_tokens": 51152}
        if any(type(proposal[key]) is not int or proposal[key] != value for key, value in exact.items()):
            raise ProviderError("invalid_configuration", "Only the reviewed one-call critic extension is supported.")
        profile = model_profile(self.config)
        price = profile["models"]["critic"]
        estimate = decimal(price["prompt_usd_per_token"]) * self.config["prompt_token_ceiling"] + decimal(price["completion_usd_per_token"]) * 2000
        if (profile["version"] != "live-step10-google-critic-v1" or proposal["model_profile"] != profile["version"]
                or proposal["critic_model"] != "google/gemini-2.5-flash" or proposal["role"] != "critic"
                or proposal["policy_hash"] != self.policy_hash
                or self.config["max_calls_per_run"] != 12 or self.config["max_tokens_per_run"] != 250000
                or self.config["prompt_token_ceiling"] != 49152 or self.config["max_output_tokens"] < 2000
                or decimal(proposal["reservation_usd"]) != estimate
                or decimal(proposal["cap_usd"]) != min(self.desk_cap, decimal(self.config["cap_usd"]))
                or decimal(proposal["per_run_usd"]) != decimal(self.config["per_run_usd"])
                or decimal(proposal["cap_usd"]) > 1 or decimal(proposal["per_run_usd"]) > Decimal(".50")):
            raise ProviderError("invalid_configuration", "The grant differs from the reviewed critic policy or dollar limits.")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            table = "run_budget_grant_amendments" if amendment else "run_budget_grants"
            previous = db.execute(f"SELECT * FROM {table} WHERE run_id=? OR grant_id=?", (proposal["run_id"], proposal["grant_id"])).fetchone()
            if previous:
                if previous["proposal_hash"] == expected_hash and json.loads(previous["proposal"]) == proposal:
                    return {"approved": True, "changed": False, "grant_id": proposal["grant_id"], "proposal_hash": expected_hash}
                raise ProviderError("authorization_changed", "This run already has its one immutable extension grant.")
            if amendment:
                parent_row = db.execute("SELECT * FROM run_budget_grants WHERE run_id=? AND grant_id=?", (proposal["run_id"], proposal["parent_grant_id"])).fetchone()
                parent = json.loads(parent_row["proposal"]) if parent_row else {}
                prior_call = db.execute("SELECT * FROM model_calls WHERE call_id=?", (parent.get("call_id", ""),)).fetchone()
                if (not parent_row or not db.execute("SELECT EXISTS(SELECT 1 FROM grant_consumptions WHERE grant_id=?)", (proposal["parent_grant_id"],)).fetchone()[0]
                        or any(parent.get(key) != proposal[key] for key in ("run_id", "policy_hash", "plan_hash", "draft_hash"))
                        or not prior_call or prior_call["status"] != "invalid_output" or prior_call["usage"] is None
                        or parent.get("max_calls") != 13 or parent.get("max_tokens") != 300000
                        or proposal["call_id"] == parent.get("call_id")):
                    raise ProviderError("authorization_changed", "The amendment requires the exact consumed parent and its billed invalid output.")
            rows = db.execute("SELECT * FROM model_calls WHERE run_id=?", (proposal["run_id"],)).fetchall()
            limits = db.execute("SELECT * FROM run_limits WHERE run_id=?", (proposal["run_id"],)).fetchone()
            all_rows = db.execute("SELECT * FROM model_calls").fetchall()
            charge, held, _ = self.totals(all_rows)
            run_charge, run_held, _ = self.totals(rows)
            if (not limits or limits["max_calls"] != 12 or limits["max_tokens"] != 250000
                    or decimal(limits["cap_usd"]) != decimal(proposal["per_run_usd"])
                    or not self._grant_checkpoint_matches(proposal, rows)
                    or db.execute("SELECT EXISTS(SELECT 1 FROM authorization WHERE blocked<>0)").fetchone()[0]
                    or charge + held + estimate > decimal(proposal["cap_usd"])
                    or run_charge + run_held + estimate > decimal(proposal["per_run_usd"])):
                raise ProviderError("authorization_changed", "The reviewed run checkpoint, holds or dollar allowance changed.")
            db.execute(f"INSERT INTO {table} VALUES(?,?,?,?,?,?)", (proposal["grant_id"], proposal["run_id"], expected_hash,
                       encoded(proposal).decode(), hashlib.sha256(human_confirmation.strip().encode()).hexdigest(), time.time()))
        return {"approved": True, "changed": True, "grant_id": proposal["grant_id"], "proposal_hash": expected_hash}

    def _grant_checkpoint_matches(self, grant, rows):
        charge, held, tokens = self.totals(rows)
        return (len(rows) == grant["checkpoint_calls"] and tokens == grant["checkpoint_tokens"]
                and sum(row["status"] == "uncertain" for row in rows) == grant["checkpoint_uncertain"]
                and self.checkpoint_hash(rows) == grant["checkpoint_hash"]
                and charge == decimal(grant["checkpoint_reported_spend_usd"]) and held == decimal(grant["checkpoint_held_usd"]))

    def reserve(self, run_id, call_id, request_hash, usd, tokens, *, role=None):
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
            blocked = db.execute("SELECT EXISTS(SELECT 1 FROM authorization WHERE blocked<>0)").fetchone()[0]
            if blocked:
                raise ProviderError("accounting_blocked", "Model spending is blocked after an accounting anomaly.")
            rows = db.execute("SELECT * FROM model_calls").fetchall()
            run_rows = [row for row in rows if row["run_id"] == run_id]
            db.execute("INSERT OR IGNORE INTO run_limits VALUES(?,?,?,?)",
                       (run_id, str(config["per_run_usd"]), config["max_calls_per_run"] or 0, config["max_tokens_per_run"]))
            previous_limits = db.execute("SELECT * FROM run_limits WHERE run_id=?", (run_id,)).fetchone()
            run_cap = min(decimal(previous_limits["cap_usd"]), decimal(config["per_run_usd"]))
            # Zero is only the SQLite representation of a newly unlimited
            # run. Existing rows retain their historical count ceiling when an
            # explicitly authorized program policy removes its enforcement.
            call_cap = (None if config["max_calls_per_run"] is None else
                        min(previous_limits["max_calls"] or config["max_calls_per_run"], config["max_calls_per_run"]))
            token_cap = min(previous_limits["max_tokens"], config["max_tokens_per_run"])
            charge, held, _ = self.totals(rows)
            run_charge, run_held, run_tokens = self.totals(run_rows)
            if charge + held + usd > min(self.desk_cap, decimal(config["cap_usd"])) or run_charge + run_held + usd > run_cap:
                raise ProviderError("budget_exhausted", "The remaining authorized model budget cannot cover this call.")
            if (call_cap is not None and len(run_rows) >= call_cap) or run_tokens + tokens > token_cap:
                row = db.execute("SELECT * FROM run_budget_grant_amendments WHERE run_id=?", (run_id,)).fetchone()
                if row is None:
                    row = db.execute("SELECT * FROM run_budget_grants WHERE run_id=?", (run_id,)).fetchone()
                grant = json.loads(row["proposal"]) if row else None
                if (not grant or role != "critic" or grant["policy_hash"] != self.policy_hash or grant["call_id"] != call_id
                        or grant["request_hash"] != request_hash or tokens != grant["reserved_tokens"]
                        or usd != decimal(grant["reservation_usd"]) or not self._grant_checkpoint_matches(grant, run_rows)
                        or db.execute("SELECT EXISTS(SELECT 1 FROM grant_consumptions WHERE grant_id=?)", (grant["grant_id"],)).fetchone()[0]
                        or len(run_rows) + 1 > grant["max_calls"] or run_tokens + tokens > grant["max_tokens"]):
                    raise ProviderError("run_limit_exhausted", "The original run limit is exhausted; no matching unused exact-call grant applies.")
                db.execute("INSERT INTO grant_consumptions VALUES(?,?,?,?)", (grant["grant_id"], call_id, request_hash, time.time()))
            retained_call_cap = previous_limits["max_calls"] if call_cap is None else call_cap
            db.execute("UPDATE run_limits SET cap_usd=?,max_calls=?,max_tokens=? WHERE run_id=?", (str(run_cap), retained_call_cap, token_cap, run_id))
            db.execute("INSERT INTO model_calls(call_id,authorization_id,run_id,request_hash,status,reserved_usd,reserved_tokens,created) VALUES(?,?,?,?,?,?,?,?)",
                       (call_id, config["authorization_id"], run_id, request_hash, "reserved", str(usd), tokens, time.time()))
        return None

    def uncertain(self, call_id, code, *, usage=None, output_audit=None, block=False):
        with self.connection() as db:
            changed = db.execute("UPDATE model_calls SET status='uncertain',error_code=?,usage=COALESCE(?,usage) WHERE call_id=? AND status='reserved'",
                                 (safe_error_code(code), json.dumps(usage) if usage is not None else None, call_id)).rowcount
            if changed and output_audit is not None:
                db.execute("INSERT INTO model_output_audit VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (call_id, output_audit["generation_id"], output_audit["finish_reason"], output_audit["content_type"],
                            output_audit["content_bytes"], output_audit["content_sha256"], output_audit["validation_stage"],
                            json.dumps(output_audit["schema_path"]), output_audit["schema_keyword"], None, time.time()))
            if changed and block:
                db.execute("UPDATE authorization SET blocked=1 WHERE id=(SELECT authorization_id FROM model_calls WHERE call_id=?)", (call_id,))

    def settle(self, call_id, usage, result, error_code=None, *, output_audit=None):
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
            if output_audit is not None:
                db.execute("INSERT INTO model_output_audit VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (call_id, output_audit["generation_id"], output_audit["finish_reason"], output_audit["content_type"],
                            output_audit["content_bytes"], output_audit["content_sha256"], output_audit["validation_stage"],
                            json.dumps(output_audit["schema_path"]), output_audit["schema_keyword"], output_audit["candidate"], time.time()))
            if anomaly:
                db.execute("UPDATE authorization SET blocked=1 WHERE id=?", (row["authorization_id"],))
        if anomaly:
            raise ProviderError("accounting_anomaly", "Provider usage exceeded its reservation; further model spending is blocked.")

    def export_quarantine(self, call_id):
        """Operator-only private export of a failed, already-accounted candidate.

        This has no HTTP route and does not validate, approve, cache as success,
        reopen a call, release a hold or request any provider work.
        """
        if not isinstance(call_id, str) or not IDENTIFIER.fullmatch(call_id):
            raise ProviderError("invalid_request", "A valid private quarantine call identifier is required.")
        with self.connection() as db:
            row = db.execute("SELECT audit.* FROM model_output_audit audit JOIN model_calls calls USING(call_id) WHERE call_id=? AND calls.status='invalid_output'",
                             (call_id,)).fetchone()
        if row is None or row["candidate"] is None:
            raise ProviderError("invalid_request", "No credential-free failed candidate is available in private quarantine.")
        value = dict(row)
        value["schema_path"] = json.loads(value["schema_path"])
        return value

    def summary(self, run_id=None):
        with self.connection() as db:
            rows = db.execute("SELECT * FROM model_calls").fetchall()
            blocked = bool(db.execute("SELECT EXISTS(SELECT 1 FROM authorization WHERE blocked<>0)").fetchone()[0])
            run_limit = db.execute("SELECT * FROM run_limits WHERE run_id=?", (run_id,)).fetchone() if run_id is not None else None
            grant_row = db.execute("SELECT * FROM run_budget_grants WHERE run_id=?", (run_id,)).fetchone() if run_id is not None else None
            grant = {**json.loads(grant_row["proposal"]), "approved": True,
                     "consumed": bool(db.execute("SELECT EXISTS(SELECT 1 FROM grant_consumptions WHERE grant_id=?)", (grant_row["grant_id"],)).fetchone()[0])} if grant_row else None
            parent_grant = None
            amendment_row = db.execute("SELECT * FROM run_budget_grant_amendments WHERE run_id=?", (run_id,)).fetchone() if run_id is not None else None
            if amendment_row:
                parent_grant = grant
                grant = {**json.loads(amendment_row["proposal"]), "approved": True,
                         "consumed": bool(db.execute("SELECT EXISTS(SELECT 1 FROM grant_consumptions WHERE grant_id=?)", (amendment_row["grant_id"],)).fetchone()[0])}
        selected = [row for row in rows if row["run_id"] == run_id] if run_id is not None else rows
        charge, held, tokens = self.totals(selected)
        global_charge, global_held, _ = self.totals(rows)
        effective_cap = min(self.desk_cap, decimal(self.config["cap_usd"]))
        run_cap = min(decimal(run_limit["cap_usd"]), decimal(self.config["per_run_usd"])) if run_limit else decimal(self.config["per_run_usd"])
        settled_calls = []
        observed_tokens = 0
        for row in selected:
            if row["usage"] is None:
                continue
            usage = json.loads(row["usage"])
            observed_tokens += usage["total_tokens"]
            safe_usage = {key: usage[key] for key in ("model_calls", "prompt_tokens", "completion_tokens", "total_tokens")
                          if key in usage and type(usage[key]) is int and usage[key] >= 0}
            if "cost_usd" in usage:
                safe_usage["cost_usd"] = str(decimal(usage["cost_usd"]))
            for key in ("model", "requested_model", "returned_model"):
                if isinstance(usage.get(key), str) and usage[key] in {*MODEL_RATES, "unapproved"}:
                    safe_usage[key] = usage[key]
            safe_usage["call_id"] = row["call_id"]
            if row["status"] in {"succeeded", "invalid_output", "accounting_anomaly"}:
                settled_calls.append({"call_id": row["call_id"], "status": row["status"], "usage": safe_usage})
        return {"enabled": self.config["enabled"], "authorization_id": self.config["authorization_id"], "config_version": self.config["version"],
                "cap_usd": str(effective_cap), "desk_cap_usd": str(self.desk_cap), "per_run_usd": str(run_cap), "ledger_scope": "desk_lifetime",
                "reported_spend_usd": str(charge), "held_usd": str(held), "committed_usd": str(charge + held),
                "authorization_committed_usd": str(global_charge + global_held),
                "remaining_authorization_usd": str(max(Decimal(0), effective_cap - global_charge - global_held)),
                "model_calls": len(selected), "tokens": tokens, "uncertain_calls": sum(row["status"] == "uncertain" for row in selected),
                "observed_tokens": observed_tokens, "settled_calls": settled_calls,
                "blocked": blocked, "run_id": run_id, "ledger_checkpoint_hash": self.checkpoint_hash(selected),
                "original_max_calls_per_run": (run_limit["max_calls"] or None) if run_limit else self.config["max_calls_per_run"],
                "original_max_tokens_per_run": run_limit["max_tokens"] if run_limit else self.config["max_tokens_per_run"],
                "run_budget_grant": grant, "parent_run_budget_grant": parent_grant}


class ReasoningGateway:
    def __init__(self, config, ledger_path, api_key="", transport=None):
        self.config = validate_config(config)
        self.profile = model_profile(self.config)
        self.ledger = BudgetLedger(ledger_path, self.config)
        self.api_key, self.transport = api_key, transport

    def budget(self, run_id=None):
        result = self.ledger.summary(run_id)
        result["provider_key_configured"] = bool(self.api_key)
        result["models"] = {role: policy["id"] for role, policy in self.profile["models"].items()}
        result["model_profile"] = self.profile["version"]
        result["provider"] = self.profile["provider"]
        result["providers"] = self.profile.get("providers", {role: self.profile["provider"] for role in ("producer", "critic")})
        if "routes" in self.profile:
            result["model_routes"] = {role: model_route(self.profile["version"], role) for role in ("producer", "critic")}
        result["policy_hash"] = self.ledger.policy_hash
        for key in ("prompt_token_ceiling", "max_message_bytes", "max_output_tokens", "max_calls_per_run", "max_tokens_per_run"):
            result[key] = self.config[key]
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
        model_role = "critic" if role == "critic" else "producer"
        policy = config["models"][model_role]
        route = model_route(self.profile["version"], model_role)
        bounded_routing = "routes" in self.profile
        # Legacy configurations may use a lower approved price. A fallback
        # profile reserves the maximum reviewed rate across its entire route.
        price = route if bounded_routing else policy
        estimate = decimal(price["prompt_usd_per_token"]) * config["prompt_token_ceiling"] + decimal(price["completion_usd_per_token"]) * max_output_tokens
        request = {"run_id": run_id, "call_id": call_id, "role": role, **bounded, "max_output_tokens": max_output_tokens,
                   "model": policy["id"], "config_version": config["version"]}
        request_hash = hashlib.sha256(encoded(request)).hexdigest()
        cached = self.ledger.reserve(run_id, call_id, request_hash, estimate, config["prompt_token_ceiling"] + max_output_tokens, role=role)
        if cached is not None:
            return {**cached, "cached": True}
        payload = {"model": policy["id"], "messages": messages, "max_tokens": max_output_tokens, "temperature": 0,
                   "response_format": {"type": "json_schema", "json_schema": {"name": "analyst_response", "strict": True, "schema": response_schema}},
                   "provider": {"only": route["providers"], "allow_fallbacks": route["allow_fallbacks"], "require_parameters": True, "data_collection": "deny",
                                "max_price": {"prompt": float(decimal(price["prompt_usd_per_token"]) * 1000000), "completion": float(decimal(price["completion_usd_per_token"]) * 1000000)}}}
        if route["allow_fallbacks"]:
            # OpenRouter tries this fixed list inside one HTTP request. The
            # application never loops, switches keys or retries a paid call.
            payload.pop("model")
            payload["models"] = route["models"]
        if role == "critic" and "critic_reasoning" in self.profile:
            payload["reasoning"] = self.profile["critic_reasoning"]
        network_error = None
        uncertain_usage, uncertain_audit, block_accounting = None, None, False
        try:
            with httpx.Client(transport=self.transport, timeout=120, trust_env=False, follow_redirects=False) as client:
                with client.stream("POST", PROVIDER_URL, headers={"Authorization": "Bearer " + self.api_key}, json=payload) as response:
                    if response.status_code != 200:
                        code = forbidden_response_hint(response) if response.status_code == 403 else http_error_code(response.status_code)
                        raise ProviderError(code, "The model provider refused the request; it will not be retried automatically.")
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
            if bounded_routing:
                uncertain_usage = usage
                stage = None
                token_breach = (raw_usage["prompt_tokens"] > config["prompt_token_ceiling"]
                                or raw_usage["completion_tokens"] > max_output_tokens)
                price_breach = cost > (decimal(price["prompt_usd_per_token"]) * raw_usage["prompt_tokens"]
                                       + decimal(price["completion_usd_per_token"]) * raw_usage["completion_tokens"])
                block_accounting = token_breach or price_breach
                if not isinstance(returned_model, str) or returned_model not in route["models"]:
                    stage = "returned_model"
                elif token_breach:
                    stage = "token_ceiling"
                elif price_breach:
                    stage = "price_ceiling"
                if stage:
                    uncertain_audit = {**private_output_audit(data, self.api_key), "validation_stage": stage, "candidate": None}
                    raise ProviderError("provider_response_invalid", "The returned route or accounting did not match its reviewed bounds.")
        except Exception as exc:
            network_error = diagnostic_code(exc)
            self.ledger.uncertain(call_id, network_error, usage=uncertain_usage, output_audit=uncertain_audit, block=block_accounting)
        # Raise outside the exception handler: a transport/JSON exception can
        # retain private headers or response text in its context or cause.
        if network_error is not None:
            raise ProviderError(network_error, "The provider outcome or charge is uncertain; its full reservation is retained and no automatic retry is allowed.")
        result, output_error = None, None
        audit = private_output_audit(data, self.api_key)
        validation_stage = "returned_model"
        try:
            if returned_model not in route["models"]:
                raise ValueError("The returned model is not an exact approved role model")
            validation_stage = "token_ceiling"
            if raw_usage["prompt_tokens"] > config["prompt_token_ceiling"]:
                raise ValueError("The provider prompt exceeded its token ceiling")
            if raw_usage["completion_tokens"] > max_output_tokens:
                raise ValueError("The provider completion exceeded its token ceiling")
            validation_stage = "content_shape"
            if not isinstance(data.get("choices"), list) or not data["choices"] or not isinstance(data["choices"][0], dict):
                raise ValueError("Missing structured completion choice")
            choice = data["choices"][0]
            validation_stage = "finish_reason"
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete model output")
            validation_stage = "content_shape"
            message = choice.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ValueError("Expected a text completion")
            validation_stage = "credential_echo"
            if contains_provider_credential(message["content"], self.api_key):
                raise ValueError("A provider credential cannot enter a model result")
            validation_stage = "json_parse"
            content = json.loads(message["content"])
            validation_stage = "credential_echo"
            if self.api_key.encode() in encoded(content):
                raise ValueError("A provider credential cannot enter a model result")
            validation_stage = "schema_validation"
            schema_error = next(validator.iter_errors(content), None)
            if schema_error is not None:
                audit["schema_keyword"] = schema_error.validator if schema_error.validator in OUTPUT_SCHEMA_KEYWORDS else None
                audit["schema_path"] = [item if isinstance(item, int) and 0 <= item <= 1000000 else item if isinstance(item, str)
                                        and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$-]{0,63}", item)
                                        and not contains_provider_credential(item, self.api_key) else "field"
                                        for item in list(schema_error.absolute_schema_path)[:16]]
                raise ValueError("The structured completion failed its schema")
            validation_stage = "content_shape"
            if not isinstance(content, dict):
                raise ValueError("Expected object output")
            result = {"content": content, "usage": usage, "config_version": config["version"], "cached": False}
            audit["validation_stage"] = "passed"
            audit["candidate"] = None
        except Exception:
            output_error = "model_output_invalid"
            audit["validation_stage"] = validation_stage if validation_stage in OUTPUT_AUDIT_STAGES else "content_shape"
            if validation_stage == "credential_echo":
                audit["candidate"] = None
        self.ledger.settle(call_id, usage, result, output_error, output_audit=audit)
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
