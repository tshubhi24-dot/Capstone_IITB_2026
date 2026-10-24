"""Manual, hash-bound client for the first Docker research journey.

This helper prepares research and reports the current review. It never chooses
an approval. Every decision requires the exact reviewed hash and an explicit
operator-supplied human confirmation. That text is evidence supplied by the
operator, not identity verification performed by this script.

An explicit continuation can resume a failed content check under its existing
approved plan and original budgets; it records no new human approval.

API contract: /api/config, /api/runs, /api/runs/{id}/continue and /api/runs/{id}/decision, with
pending={kind,payload,payload_hash}. This serves the fresh teaching implementation. No application import is
required. Full run snapshots and confirmation text remain in private storage.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:18080"
DEFAULT_CREDENTIALS = ROOT / ".runtime/journey/credentials.env"
DEFAULT_SESSION = ROOT / ".runtime/journey/session.json"
DEFAULT_RECEIPT = ROOT / "evidence/two_company_journey.json"
REQUEST = {
    "question": "Compare Microsoft and Apple's operating margins for fiscal 2023, 2024 and 2025, and explain source-backed changes in their disclosed risk factors. Show actual fiscal periods and cite each financial input. State uncertainty and comparability limits.",
    "tickers": ["MSFT", "AAPL"],
    "years": [2023, 2024, 2025],
    "strategy": "multi",
    "max_tokens": 100000,
    "max_tool_calls": 60,
    "plant_error": False,
    "inject_article": False,
    "memory_enabled": True,
    "critic_enabled": True,
    "table_aware": True,
    "defences_enabled": True,
    "learning_split": "production",
}
PAUSED_OR_TERMINAL = {"awaiting_plan", "awaiting_note", "published", "rejected", "error", "failed", "cancelled", "budget_exceeded"}


class JourneyError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    """Never forward the local analyst credential to a redirect destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def local_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
        raise JourneyError("Use a loopback HTTP(S) base URL with no credentials, path or query.")
    try:
        parsed.port
    except ValueError as exc:
        raise JourneyError("The service port is invalid.") from exc
    return value.rstrip("/")


def read_token(path: Path, environment: str = "ANALYST_API_TOKEN") -> str:
    token = os.environ.get(environment, "").strip()
    if not token:
        try:
            lines = path.read_text().splitlines()
        except OSError as exc:
            raise JourneyError("The analyst credential is unavailable; prepare the private credential file or token environment variable.") from exc
        for line in lines:
            key, separator, value = line.strip().partition("=")
            if separator and key == "ANALYST_API_TOKEN":
                token = value.strip()
                if len(token) > 1 and token[0] == token[-1] and token[0] in "\"'":
                    token = token[1:-1]
                break
    if not token or "\n" in token or "\r" in token:
        raise JourneyError("The private analyst token is missing or invalid.")
    return token


def write_json(path: Path, value, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
    temporary = path.with_name(path.name + ".tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(temporary, flags, 0o600 if private else 0o644)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        if private:
            temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class JourneyClient:
    def __init__(self, *, base_url=DEFAULT_BASE_URL, token: str,
                 session_path: Path = DEFAULT_SESSION, receipt_path: Path = DEFAULT_RECEIPT,
                 timeout: float = 20, wait_seconds: float = 180, poll_seconds: float = 1, mode: str = "offline"):
        self.base_url = local_base_url(base_url)
        self.token = token
        self.session_path, self.receipt_path = Path(session_path), Path(receipt_path)
        self.timeout, self.wait_seconds, self.poll_seconds = timeout, wait_seconds, poll_seconds
        if mode not in {"offline", "live"}:
            raise JourneyError("Choose explicit offline or live research mode.")
        self.mode = mode
        self.research_request = deepcopy(REQUEST)
        if mode == "live":
            self.research_request.update(mode="live", max_tokens=250000, max_model_calls=12)
        # A local-only client must not send its analyst header via an ambient
        # HTTP proxy, and must never forward it to a redirect destination.
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.session = self._load_session()

    def _load_session(self):
        if not self.session_path.exists():
            return {}
        try:
            return json.loads(self.session_path.read_text())
        except (OSError, ValueError) as exc:
            raise JourneyError("The saved private session cannot be read; preserve it before starting a new session.") from exc

    def clean(self, value):
        if isinstance(value, str):
            value = value.replace(self.token, "[REDACTED]") if self.token else value
            return re.sub(r"(?i)((?:api[_ -]?key|password|secret)\s*[:=]\s*)\S+", r"\1[REDACTED]", value)
        if isinstance(value, list):
            return [self.clean(item) for item in value]
        if isinstance(value, dict):
            return {key: self.clean(item) for key, item in value.items() if key not in {"approval_token", "queued_decision", "queued_continuation"}}
        return value

    def request(self, method: str, path: str, body=None):
        encoded = json.dumps(body).encode() if body is not None else None
        request = Request(self.base_url + path, data=encoded, method=method,
                          headers={"Content-Type": "application/json", "X-Analyst-Token": self.token})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(10 * 1024 * 1024 + 1)
                if len(raw) > 10 * 1024 * 1024:
                    raise JourneyError("The service response exceeds the local client limit.")
                result = json.loads(raw)
        except HTTPError as exc:
            try:
                error = json.loads(exc.read(16384))
                detail = error.get("detail", "Request refused") if isinstance(error, dict) else "Request refused"
            except (OSError, ValueError):
                detail = "Request refused"
            raise JourneyError(self.clean(f"Service returned HTTP {exc.code}: {detail}")) from None
        except (URLError, TimeoutError, OSError) as exc:
            raise JourneyError(self.clean(f"Cannot reach the local research service: {exc}")) from None
        except ValueError:
            raise JourneyError("The service returned invalid JSON.") from None
        if not isinstance(result, (dict, list)):
            raise JourneyError("The service returned an invalid response shape.")
        return result

    def wait(self, run_id: str):
        deadline = time.monotonic() + self.wait_seconds
        while True:
            run = self.request("GET", "/api/runs/" + quote(run_id, safe=""))
            if run.get("status") in PAUSED_OR_TERMINAL:
                return run
            if time.monotonic() >= deadline:
                raise JourneyError("Research is still running after the bounded wait. The run ID is saved privately; use status to inspect it.")
            time.sleep(self.poll_seconds)

    def _check_offline_config(self, config):
        if self.mode == "live" and not config.get("live_enabled"):
            raise JourneyError("Live spending must be explicitly authorized before preparing a model-assisted request.")
        if config.get("mode") not in {"offline", "demo"} or config.get("data_source") != "sec_edgar":
            raise JourneyError("Prepare requires offline mode with actual SEC data; no live or synthetic request was started.")
        if config.get("transport") != "http":
            raise JourneyError("Prepare requires the Docker HTTP MCP transport.")
        known = {item.get("ticker") for item in config.get("companies", [])}
        if not set(REQUEST["tickers"]) <= known:
            raise JourneyError("The service does not cover both MSFT and AAPL.")
        coverage = config.get("company_years", {})
        if any(not set(REQUEST["years"]) <= set(coverage.get(ticker, [])) for ticker in REQUEST["tickers"]):
            raise JourneyError("The service lacks a requested fiscal year; no research request was started.")

    def save(self, run, config=None):
        self.session.update({"base_url": self.base_url, "run_id": run["id"], "run": run, "updated_at": now()})
        if config is not None:
            self.session["config"] = config
        write_json(self.session_path, self.clean(self.session), private=True)
        receipt = self.receipt(run)
        write_json(self.receipt_path, receipt)
        return receipt

    def receipt(self, run):
        config, pending = self.session.get("config", {}), run.get("pending") or {}
        payload, request = pending.get("payload") or {}, run.get("request") or {}
        plan = {key: payload[key] for key in ("tickers", "years", "outline", "subquestions", "caveats") if key in payload} if pending.get("kind") == "plan" else None
        usage, critic = run.get("usage") or {}, run.get("critic") or {}
        calls = usage.get("calls") or []
        public = {
            "record_kind": "manual_two_company_learning_journey",
            "updated_at": now(), "base_url": self.base_url, "run_id": run["id"],
            "status": run.get("status"), "stage": run.get("stage"),
            "configuration": {**{key: config.get(key) for key in ("data_source", "transport", "semantic_retrieval")},
                              "mode": run.get("mode", request.get("mode", self.mode)),
                              "model_config_version": config.get("live_model_config_version") if self.mode == "live" else config.get("model_config_version")},
            "request": {key: request.get(key) for key in ("tickers", "years", "strategy", "mode", "max_tokens", "max_model_calls", "max_tool_calls", "learning_split")},
            "pending_review": {"kind": pending.get("kind"), "payload_hash": pending.get("payload_hash"), "plan": plan,
                               "note_title": payload.get("title") if pending.get("kind") == "note" else None},
            "expected_human_action": f"Review the exact {pending['kind']} and explicitly approve, edit or reject it." if pending.get("kind") else None,
            "verification": {key: critic.get(key) for key in ("passed", "verified_share", "verified_numbers", "total_numbers", "semantic_review")},
            "usage": {"tokens": usage.get("tokens", 0), "tool_calls": usage.get("tool_calls", 0),
                      "model_calls": usage.get("model_calls", len(calls)), "cost_usd": usage.get("cost_usd"),
                      **{key: usage[key] for key in ("held_usd", "committed_usd", "accounting_status") if key in usage}},
            "note_id": run.get("note_id"),
            "decision_requests": [{key: item[key] for key in ("time", "kind", "action", "payload_hash", "confirmation_sha256", "accepted_by_api")}
                                  for item in self.session.get("decision_requests", [])],
            "continuation_requests": [{key: item[key] for key in ("time", "plan_hash", "accepted_by_api", "retry_transient", "replace_critic_policy", "critic_extension") if key in item}
                                      for item in self.session.get("continuation_requests", [])],
            "continuation": {key: value for key, value in (run.get("continuation") or {}).items()
                             if key in {"available", "retry_transient_available", "replace_critic_policy_available", "critic_extension_available", "grant_id", "policy_hash", "plan_hash", "failure_kind"}},
            "limitations": ["This is an ordinary learning run, not a protected final benchmark.",
                            "An operator-supplied confirmation records the cited decision; the helper does not independently verify human identity.",
                            "Full outputs, errors and confirmation text are retained privately, not copied into this public receipt."],
        }
        return self.clean(public)

    def prepare(self, *, new_run=False):
        config = self.request("GET", "/api/config")
        self._check_offline_config(config)
        if self.session and not new_run:
            if self.session.get("base_url") != self.base_url or self.session.get("request_digest") != digest(self.research_request):
                raise JourneyError("The saved session belongs to another service or request; preserve it and explicitly use --new-run if needed.")
            return self.status(self.session["run_id"], config=config)
        self.session = {"created_at": now(), "request_digest": digest(self.research_request), "decision_requests": []}
        run = self.request("POST", "/api/runs", self.research_request)
        self.save(run, config)
        return self.save(self.wait(run["id"]))

    def status(self, run_id=None, *, config=None):
        run_id = run_id or self.session.get("run_id")
        if not run_id:
            raise JourneyError("No saved run exists; prepare one or supply a run ID.")
        self._check_session(run_id)
        return self.save(self.wait(run_id), config=config)

    def _check_session(self, run_id):
        if self.session and self.session.get("base_url") != self.base_url:
            raise JourneyError("The saved session belongs to a different service.")
        if self.session.get("run_id") and self.session["run_id"] != run_id:
            raise JourneyError("The saved session belongs to a different run; use a separate --session-file to inspect another journey.")

    def continue_run(self, run_id, *, expected_plan_hash, retry_transient=False, replace_critic_policy=None, critic_extension=None):
        self._check_session(run_id)
        if (self.mode != "live" or type(retry_transient) is not bool
                or not re.fullmatch(r"[a-f0-9]{64}", expected_plan_hash or "")):
            raise JourneyError("Explicit live continuation requires the existing approved plan hash.")
        if sum((bool(retry_transient), replace_critic_policy is not None, critic_extension is not None)) > 1:
            raise JourneyError("Choose one explicit continuation mode.")
        if critic_extension is not None and (not isinstance(critic_extension, str) or not re.fullmatch(r"[a-f0-9]{32}", critic_extension)):
            raise JourneyError("Critic extension requires the exact separately approved grant ID.")
        if replace_critic_policy is not None:
            if (retry_transient or not isinstance(replace_critic_policy, str)
                    or not re.fullmatch(r"[a-f0-9]{64}", replace_critic_policy)):
                raise JourneyError("Critic policy replacement requires its exact hash and an exclusive continuation mode.")
        config = self.request("GET", "/api/config")
        self._check_offline_config(config)
        run = self.request("GET", "/api/runs/" + quote(run_id, safe=""))
        continuation = run.get("continuation") or {}
        eligibility = ("critic_extension_available" if critic_extension is not None
                       else "replace_critic_policy_available" if replace_critic_policy is not None
                       else "retry_transient_available" if retry_transient else "available")
        if (run.get("status") != "error" or run.get("request", {}).get("mode") != "live"
                or continuation.get(eligibility) is not True or continuation.get("plan_hash") != expected_plan_hash
                or replace_critic_policy is not None and continuation.get("policy_hash") != replace_critic_policy
                or critic_extension is not None and continuation.get("grant_id") != critic_extension):
            raise JourneyError("This stopped operation cannot continue under the supplied approved plan and retry mode.")
        body = {"plan_hash": expected_plan_hash}
        record = {"time": now(), "plan_hash": expected_plan_hash, "accepted_by_api": True}
        if retry_transient:
            body["retry_transient"] = True
            record["retry_transient"] = True
        elif critic_extension is not None:
            body["critic_extension"] = critic_extension
            record["critic_extension"] = critic_extension
        elif replace_critic_policy is not None:
            body["replace_critic_policy"] = replace_critic_policy
            record["replace_critic_policy"] = replace_critic_policy
        updated = self.request("POST", "/api/runs/" + quote(run_id, safe="") + "/continue", body)
        self.session.setdefault("continuation_requests", []).append(record)
        self.save(updated, config)
        return self.save(self.wait(run_id))

    def decision(self, run_id, *, kind, action, expected_hash, human_confirmation, edits=None):
        self._check_session(run_id)
        if not human_confirmation or not human_confirmation.strip():
            raise JourneyError("A decision requires explicit human confirmation for this exact review.")
        if kind not in {"plan", "note"} or action not in {"approve", "edit", "reject"}:
            raise JourneyError("Unknown decision kind or action.")
        if not re.fullmatch(r"[a-f0-9]{64}", expected_hash or ""):
            raise JourneyError("Supply the exact 64-character hash that the human reviewed.")
        if (action == "edit" and not isinstance(edits, dict)) or (action != "edit" and edits is not None):
            raise JourneyError("Only an edit decision accepts an edits object; edit requires that object.")
        run = self.request("GET", "/api/runs/" + quote(run_id, safe=""))
        pending = run.get("pending") or {}
        if run.get("status") != "awaiting_" + kind or pending.get("kind") != kind or pending.get("payload_hash") != expected_hash:
            raise JourneyError("The reviewed version is stale or belongs to another stage; inspect the current review before deciding.")
        if kind == "note" and action == "approve" and not (run.get("critic") or {}).get("passed"):
            raise JourneyError("The critic has unresolved issues; approval is blocked.")
        body = {"kind": kind, "action": action, "payload_hash": expected_hash, "edits": edits}
        updated = self.request("POST", "/api/runs/" + quote(run_id, safe="") + "/decision", body)
        self.session.setdefault("decision_requests", []).append({"time": now(), "kind": kind, "action": action,
            "payload_hash": expected_hash, "human_confirmation": human_confirmation.strip(),
            "confirmation_sha256": hashlib.sha256(human_confirmation.strip().encode()).hexdigest(), "accepted_by_api": True})
        self.save(updated)
        return self.save(self.wait(run_id))


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--base-url", default=DEFAULT_BASE_URL)
    cli.add_argument("--credentials-file", type=Path, default=DEFAULT_CREDENTIALS)
    cli.add_argument("--token-env", default="ANALYST_API_TOKEN")
    cli.add_argument("--mode", choices=("offline", "live"), default="offline")
    cli.add_argument("--session-file", type=Path)
    cli.add_argument("--receipt-file", type=Path)
    cli.add_argument("--wait-seconds", type=float, default=180)
    sub = cli.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Create the offline SEC request and stop at human plan review.")
    prepare.add_argument("--new-run", action="store_true")
    status = sub.add_parser("status", help="Wait for the current run's next review or terminal status.")
    status.add_argument("run_id", nargs="?")
    continuation = sub.add_parser("continue", help="Explicitly continue a failed content check using its unchanged approved plan and original budgets.")
    continuation.add_argument("run_id")
    continuation.add_argument("--expected-plan-hash", required=True)
    continuation_mode = continuation.add_mutually_exclusive_group()
    continuation_mode.add_argument("--retry-transient", action="store_true", help="Deliberately request the single eligible critic HTTP-429 retry; retains its old reservation and original budgets.")
    continuation_mode.add_argument("--replace-critic-policy", metavar="EXPECTED_POLICY_HASH", help="Continue only under this exact eligible replacement critic policy; retains old reservations and original budgets.")
    continuation_mode.add_argument("--critic-extension", metavar="GRANT_ID", help="Consume only this separately human-approved exact critic extension grant.")
    decision = sub.add_parser("decision", help="Submit a human's explicit decision for the exact reviewed hash.")
    decision.add_argument("run_id")
    decision.add_argument("--kind", required=True, choices=("plan", "note"))
    decision.add_argument("--action", required=True, choices=("approve", "edit", "reject"))
    decision.add_argument("--expected-hash", required=True)
    decision.add_argument("--human-confirmation", required=True)
    decision.add_argument("--edits-file", type=Path)
    return cli


def main(argv=None):
    arguments = parser().parse_args(argv)
    try:
        if arguments.wait_seconds <= 0:
            raise JourneyError("The wait limit must be positive.")
        client = JourneyClient(base_url=arguments.base_url, token=read_token(arguments.credentials_file, arguments.token_env),
                               session_path=arguments.session_file or (ROOT / ".runtime/live/session.json" if arguments.mode == "live" else DEFAULT_SESSION),
                               receipt_path=arguments.receipt_file or (ROOT / "evidence/live_two_company_journey.json" if arguments.mode == "live" else DEFAULT_RECEIPT),
                               wait_seconds=arguments.wait_seconds, mode=arguments.mode)
        if arguments.command == "prepare":
            result = client.prepare(new_run=arguments.new_run)
        elif arguments.command == "status":
            result = client.status(arguments.run_id)
        elif arguments.command == "continue":
            result = client.continue_run(arguments.run_id, expected_plan_hash=arguments.expected_plan_hash,
                                         retry_transient=arguments.retry_transient,
                                         replace_critic_policy=arguments.replace_critic_policy, critic_extension=arguments.critic_extension)
        else:
            edits = json.loads(arguments.edits_file.read_text()) if arguments.edits_file else None
            result = client.decision(arguments.run_id, kind=arguments.kind, action=arguments.action,
                                     expected_hash=arguments.expected_hash, human_confirmation=arguments.human_confirmation, edits=edits)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (JourneyError, OSError, ValueError) as exc:
        message = client.clean(str(exc)) if "client" in locals() else str(exc)
        print(message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
