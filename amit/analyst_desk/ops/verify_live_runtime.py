"""Verify live-overlay boundaries without paid requests or research decisions.

An inactive gateway permits one rejected run-creation probe. Enabled gateways
receive only read requests. This helper never requests a model completion.
"""
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ops import prepare_live
from ops import start_journey as base
from ops import start_live as live
from ops.verify_runtime import analyst_token, PROMETHEUS_CHECK
from desk.model_profiles import model_profile

BASE_URL = "http://127.0.0.1:18080"
OFFLINE_NOTE_ID = "c54ab4c70fc64615a95dfc8c462ba0c3"
INSPECT = '''{"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"state":{{json .State.Status}},"network_mode":{{json .HostConfig.NetworkMode}},"networks":{{json .NetworkSettings.Networks}},"read_only":{{json .HostConfig.ReadonlyRootfs}},"ports":{{json .HostConfig.PortBindings}},"env":{{json .Config.Env}},"mounts":{{json .Mounts}},"user":{{json .Config.User}},"cap_drop":{{json .HostConfig.CapDrop}}}'''
GATEWAY_AUTH_CHECK = '''import json,urllib.request,urllib.error
try:
 r=urllib.request.urlopen("http://model-gateway:8020/v1/budget",timeout=8)
 result={"http_status":r.status,"rejected":False}
except urllib.error.HTTPError as e:
 result={"http_status":e.code,"rejected":e.code==401}
print(json.dumps(result))
'''


def request_json(path, token=None, body=None, *, base_url=BASE_URL):
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, request, response, code, message, headers, new_url):
            return None

    headers = {"X-Analyst-Token": token} if token else {}
    encoded = None
    if body is not None:
        encoded = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = Request(base_url + path, data=encoded, headers=headers, method="POST" if encoded is not None else "GET")
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=12) as response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("Response size exceeded")
            return response.status, json.loads(raw)
    except HTTPError as error:
        # Error bodies can contain supplied input. The status is sufficient.
        return error.code, None


def safe_budget(value):
    if not isinstance(value, dict) or type(value.get("enabled")) is not bool:
        raise ValueError("The live ledger is unavailable")
    output = {"enabled": value["enabled"]}
    for name in ("cap_usd", "per_run_usd", "reported_spend_usd", "held_usd", "committed_usd", "remaining_authorization_usd"):
        number = Decimal(str(value[name]))
        if not number.is_finite() or number < 0:
            raise ValueError("The live ledger is invalid")
        output[name] = str(number)
    for name in ("model_calls", "tokens", "uncertain_calls"):
        if type(value.get(name)) is not int or value[name] < 0:
            raise ValueError("The live ledger counts are invalid")
        output[name] = value[name]
    if type(value.get("blocked")) is not bool:
        raise ValueError("The live ledger status is invalid")
    output["blocked"] = value["blocked"]
    profile = model_profile(value.get("model_profile"))
    models = {role: policy["id"] for role, policy in profile["models"].items()}
    if value.get("models") != models or value.get("provider") != profile["provider"]:
        raise ValueError("The live model metadata is inconsistent")
    output.update(models=models, model_profile=profile["version"], provider=profile["provider"])
    return output


def host_path(value):
    # Docker Desktop may expose the VM spelling of an otherwise identical bind.
    for prefix in ("/host_mnt", "/run/host"):
        if value.startswith(prefix + "/"):
            value = value[len(prefix):]
            break
    return Path(value).resolve()


def main():
    checks, state, secrets = [], {}, []
    counters = {"creation_probes_sent": 0, "research_runs_created": 0}

    def record(name, passed, **observed):
        checks.append({"name": name, "passed": bool(passed), "observed": observed})

    def attempt(name, action):
        try:
            action()
        except Exception as error:
            # Never serialize exception messages, response bodies, Env or binds.
            record(name, False, error_type=type(error).__name__)

    def credentials():
        prepared = prepare_live.load_config()
        profile = model_profile(prepared["version"])
        models = {role: policy["id"] for role, policy in profile["models"].items()}
        token = analyst_token()
        key = prepare_live.prepared_key()
        if len(key) < 20:
            raise ValueError("Provider credential unavailable")
        state.update(token=token, provider_key=key, prepared_enabled=prepared["enabled"],
                     models=models, model_profile=profile["version"], provider=profile["provider"])
        secrets.extend((token, key))
        record("private_credentials_available", True, values_disclosed=False)

    def health():
        status, value = request_json("/health")
        record("api_health", status == 200 and value.get("status") == "ok" and value.get("data_source") == "sec_edgar", http_status=status)

    def unauthenticated_api():
        status, _ = request_json("/api/config")
        record("api_missing_token_rejected", status == 401, http_status=status)

    def configuration():
        status, value = request_json("/api/config", state["token"])
        if status != 200 or not isinstance(value, dict):
            raise ValueError("Configuration unavailable")
        expected_years = {"MSFT": [2023, 2024, 2025], "AAPL": [2023, 2024, 2025]}
        expected_models = (value.get("models") == state["models"]
                           and value.get("model_profile") == state["model_profile"]
                           and value.get("model_provider") == state["provider"])
        good = value.get("data_source") == "sec_edgar" and value.get("transport") == "http" and expected_models and value.get("company_years") == expected_years and value.get("semantic_retrieval") is False
        state["config"] = value
        record("live_api_source_and_model_configuration", good, expected_model_ids=expected_models, expected_source_scope=value.get("company_years") == expected_years, learned_retrieval_claimed=value.get("semantic_retrieval") is True)

    def budget():
        status, value = request_json("/api/budget", state["token"])
        safe = safe_budget(value)
        state["budget"] = safe
        state["raw_budget"] = value
        expected_enabled = bool(safe["enabled"] and not safe["blocked"] and Decimal(safe["remaining_authorization_usd"]) > 0)
        config = state["config"]
        matching_policy = (safe["models"] == state["models"] and safe["model_profile"] == state["model_profile"]
                           and safe["provider"] == state["provider"] and safe["enabled"] == state["prepared_enabled"])
        good = status == 200 and matching_policy and value.get("provider_key_configured") is True and config.get("live_enabled") is expected_enabled and ("live" in config.get("available_modes", [])) is expected_enabled
        record("model_ledger_available_and_ui_state_matches", good, **safe)

    def notes():
        status, values = request_json("/api/notes", state["token"])
        if status != 200 or not isinstance(values, list):
            raise ValueError("Approved library unavailable")
        preserved = any(note.get("id") == OFFLINE_NOTE_ID and note.get("model_mode") == "offline" for note in values)
        record("existing_offline_approved_note_preserved", preserved, note_count=len(values), original_offline_note_present=preserved)

    def disabled_gate():
        budget_before = state["budget"]
        if budget_before["enabled"]:
            record("disabled_live_request_gate", True, applicable=False, request_sent=False, reason="Enabled gateway: verifier performs no run-creation requests.")
            return
        # This is an additional local snapshot check before the rejected POST.
        # A tiny token cap also stops the planner before a paid call if an
        # operator enables the gateway during this otherwise read-only check.
        if prepare_live.load_config()["enabled"] is not False:
            raise ValueError("The local authorization changed during verification")
        status, before = request_json("/api/runs", state["token"])
        if status != 200 or not isinstance(before, list):
            raise ValueError("Run list unavailable")
        counters["creation_probes_sent"] += 1
        status, _ = request_json("/api/runs", state["token"], {
            "mode": "live", "question": "Readiness probe: disabled live mode must reject before creating research.",
            "tickers": ["MSFT"], "years": [2025], "max_tokens": 100, "max_model_calls": 1,
        })
        after_status, after = request_json("/api/runs", state["token"])
        budget_status, after_budget_raw = request_json("/api/budget", state["token"])
        after_budget = safe_budget(after_budget_raw)
        count_valid = after_status == 200 and isinstance(after, list)
        created = max(0, len(after) - len(before)) if count_valid else None
        counters["research_runs_created"] = created
        unchanged = count_valid and {item["id"] for item in before} == {item["id"] for item in after}
        no_model_calls = budget_status == 200 and all(after_budget[key] == budget_before[key] for key in ("model_calls", "reported_spend_usd", "held_usd", "committed_usd"))
        record("disabled_live_request_gate", status == 409 and unchanged and no_model_calls, applicable=True, request_sent=True, http_status=status, run_count_unchanged=unchanged, model_accounting_unchanged=no_model_calls, newly_created_runs=created)

    attempt("private_credentials_available", credentials)
    attempt("api_health", health)
    attempt("api_missing_token_rejected", unauthenticated_api)
    attempt("live_api_source_and_model_configuration", configuration)
    attempt("model_ledger_available_and_ui_state_matches", budget)
    attempt("existing_offline_approved_note_preserved", notes)
    attempt("disabled_live_request_gate", disabled_gate)

    def docker_boundaries():
        docker = base.docker_binary()
        command, env = live.compose(docker), live.environment(docker)

        def capture(arguments):
            return base.capture(arguments, env, state["token"])

        ids = capture(command + ["ps", "--all", "--quiet"]).splitlines()
        if not ids or any(not re.fullmatch(r"[a-f0-9]{12,64}", identifier) for identifier in ids):
            raise ValueError("Project containers unavailable")
        selected = capture([docker, "--context", base.CONTEXT, "inspect", "--format", INSPECT, *ids])
        containers = [json.loads(line) for line in selected.splitlines() if line]
        if any(container.get("project") != base.PROJECT for container in containers):
            raise ValueError("Project ownership mismatch")
        services = {container["service"]: container for container in containers}
        unique = len(services) == len(containers)
        all_running = unique and all(services.get(name, {}).get("state") == "running" for name in live.LIVE_ORDER)
        record("project_runtime_services_running", all_running, required_services=len(live.LIVE_ORDER), unique_service_containers=unique)
        provider_in_env = any(state["provider_key"] in value for container in containers for value in (container.get("env") or []))
        record("provider_key_absent_from_all_container_environments", not provider_in_env, inspected_container_count=len(containers), exposed_value=False)
        backend = base.PROJECT + "_backend"
        egress = base.PROJECT + "_provider-egress"
        gateway = services.get("model-gateway", {})
        gateway_networks = set(gateway.get("networks") or {})
        gateway_networks_ok = gateway_networks == {backend, egress} and not gateway.get("ports")
        record("gateway_private_ports_and_egress", gateway_networks_ok, backend_and_provider_egress_only=gateway_networks == {backend, egress}, no_host_ports=not gateway.get("ports"))
        private_readers = ("app", "filings-kb", "edgar", "python-sandbox", "research-portal")
        readers_private = all(set(services.get(name, {}).get("networks") or {}) == {backend} for name in private_readers)
        record("app_and_mcp_remain_backend_only", readers_private, checked_service_count=len(private_readers))
        key_path = prepare_live.KEY_FILE.resolve()
        key_readers = []
        for name, container in services.items():
            for mount in container.get("mounts", []):
                if mount.get("Type") == "bind":
                    source = host_path(mount["Source"])
                    if source == key_path or key_path.is_relative_to(source):
                        key_readers.append((name, mount.get("Destination"), bool(mount.get("RW"))))
        key_isolated = key_readers == [("model-gateway", "/run/provider/key", False)]
        record("provider_key_file_is_gateway_only_and_read_only", key_isolated, matching_mount_count=len(key_readers), gateway_only=key_isolated)
        mounts = {mount["Destination"]: mount for mount in gateway.get("mounts", [])}
        targets = {"/runtime", "/run/credentials", "/run/provider/model_config.json", "/run/provider/key"}
        ledger = mounts.get("/runtime", {})
        scoped = mounts.get("/run/credentials", {})
        history_names = {mount.get("Name") for name in ("app", "research-portal") for mount in services.get(name, {}).get("mounts", []) if mount.get("Destination") == "/runtime"}
        ledger_separate = ledger.get("Type") == "volume" and ledger.get("Name") == base.PROJECT + "_model-ledger" and ledger.get("Name") not in history_names and bool(ledger.get("RW"))
        other_read_only = all(not mount.get("RW") for target, mount in mounts.items() if target != "/runtime")
        gateway_mounts_ok = set(mounts) == targets and ledger_separate and scoped.get("Name") == base.PROJECT + "_gateway-auth" and other_read_only
        record("gateway_has_separate_ledger_and_no_research_history_mount", gateway_mounts_ok, expected_mount_targets_only=set(mounts) == targets, ledger_separate_from_research_history=ledger_separate, other_mounts_read_only=other_read_only)
        gateway_process = gateway.get("read_only") is True and gateway.get("user") == "10001:10001" and gateway.get("cap_drop") == ["ALL"]
        record("gateway_process_restrictions", gateway_process, read_only_root=gateway.get("read_only") is True, nonroot_user=gateway.get("user") == "10001:10001", all_capabilities_dropped=gateway.get("cap_drop") == ["ALL"])
        worker = services.get("pandas-worker", {})
        worker_mounts = worker.get("mounts", [])
        worker_ok = worker.get("network_mode") == "none" and worker.get("read_only") is True and len(worker_mounts) == 1 and worker_mounts[0].get("Destination") == "/queue"
        record("calculation_worker_still_networkless_and_queue_only", worker_ok, network_none=worker.get("network_mode") == "none", queue_only=len(worker_mounts) == 1 and worker_mounts[0].get("Destination") == "/queue", read_only_root=worker.get("read_only") is True)
        auth = json.loads(capture(command + ["exec", "-T", "app", "python", "-c", GATEWAY_AUTH_CHECK]))
        record("model_gateway_rejects_missing_internal_credential", auth == {"http_status": 401, "rejected": True}, http_status=auth.get("http_status"), paid_completion_requested=False)
        network_template = '{"project":{{json (index .Labels "com.docker.compose.project")}},"internal":{{json .Internal}}}'
        network = json.loads(capture([docker, "--context", base.CONTEXT, "network", "inspect", backend, "--format", network_template]))
        record("backend_network_remains_internal", network.get("project") == base.PROJECT and network.get("internal") is True, expected_project=network.get("project") == base.PROJECT, internal=network.get("internal") is True)
        prometheus = json.loads(capture(command + ["exec", "-T", "app", "python", "-c", PROMETHEUS_CHECK]))
        record("prometheus_app_scrape_ready", prometheus == {"api_ok": True, "matching_targets": 1, "up": True, "no_scrape_error": True}, target_up=prometheus.get("up") is True, no_scrape_error=prometheus.get("no_scrape_error") is True)

    attempt("docker_live_boundary_verification", docker_boundaries)

    def grafana():
        status, value = request_json("/api/health", base_url="http://127.0.0.1:13080")
        record("grafana_database_ready", status == 200 and value.get("database") == "ok", http_status=status)

    attempt("grafana_database_ready", grafana)
    passed = bool(checks) and all(check["passed"] for check in checks)
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "project": base.PROJECT, "docker_context": base.CONTEXT,
              "status": "passed" if passed else "failed", "checks": checks,
              "budget": state.get("budget"), "models": state.get("models"),
              "model_profile": state.get("model_profile"), "provider": state.get("provider"),
              "run_creation_probes_sent": counters["creation_probes_sent"],
              "research_runs_created_by_verifier": counters["research_runs_created"], "human_decisions_performed": False,
              "provider_completion_requests_sent_by_verifier": 0,
              "scope": "Live-overlay readiness, disabled-budget rejection when applicable, configured Docker boundaries, and authentication. No paid research, semantic benchmark, active containment attack or alert firing test."}
    output = json.dumps(report, indent=2) + "\n"
    if any(secret and secret in output for secret in secrets):
        # A final guard keeps even unexpected upstream values out of evidence.
        print("Live runtime verification stopped because public evidence was not safe to write.", file=sys.stderr)
        return 2
    path = ROOT / "evidence/live_runtime_checks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output)
    print(f"Live runtime verification: {report['status']}. Sanitized evidence: evidence/live_runtime_checks.json")
    if not passed:
        print("Failed checks: " + ", ".join(check["name"] for check in checks if not check["passed"]))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
