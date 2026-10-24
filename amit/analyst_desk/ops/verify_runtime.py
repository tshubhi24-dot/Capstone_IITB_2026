"""Record read-only readiness checks for this journey, without advancing a run."""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import re
import stat
import sys
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ops import start_journey as launch


INSPECT = '''{"project":{{json (index .Config.Labels "com.docker.compose.project")}},"service":{{json (index .Config.Labels "com.docker.compose.service")}},"state":{{json .State.Status}},"network_mode":{{json .HostConfig.NetworkMode}},"read_only":{{json .HostConfig.ReadonlyRootfs}},"memory":{{json .HostConfig.Memory}},"pids_limit":{{json .HostConfig.PidsLimit}},"nano_cpus":{{json .HostConfig.NanoCpus}},"cap_drop":{{json .HostConfig.CapDrop}},"ports":{{json .HostConfig.PortBindings}},"mounts":[{{range $i,$m := .Mounts}}{{if $i}},{{end}}{"destination":{{json $m.Destination}},"writable":{{json $m.RW}}}{{end}}]}'''
PROMETHEUS_CHECK = '''import json,urllib.request
d=json.load(urllib.request.urlopen("http://prometheus:9090/api/v1/targets",timeout=5))
t=[t for t in d.get("data",{}).get("activeTargets",[]) if t.get("labels",{}).get("job")=="analyst-desk" and t.get("labels",{}).get("instance")=="app:8000"]
print(json.dumps({"api_ok":d.get("status")=="success","matching_targets":len(t),"up":len(t)==1 and t[0].get("health")=="up","no_scrape_error":len(t)==1 and not t[0].get("lastError")}))
'''


def prepared_source_scope(manifest_path=None, corpus_path=None):
    """Use the prepared public source identity instead of a fixed issuer list."""
    manifest = json.loads(Path(manifest_path or ROOT / "data/source_manifest.json").read_bytes())
    tickers, years = manifest.get("tickers"), manifest.get("years")
    fingerprint = manifest.get("snapshot_sha256")
    if (manifest.get("source_kind") != "sec_edgar"
            or not isinstance(tickers, list) or not 1 <= len(tickers) <= 12
            or not all(isinstance(ticker, str) and re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker) for ticker in tickers)
            or len(set(tickers)) != len(tickers)
            or not isinstance(years, list) or not 1 <= len(years) <= 3
            or not all(type(year) is int and 1900 <= year <= 2100 for year in years)
            or years != sorted(set(years))
            or not isinstance(fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", fingerprint)):
        raise ValueError("The public source manifest has an invalid scope or identity.")
    facts = manifest.get("fact_inventory")
    expected = {(ticker, year, concept) for ticker in tickers for year in years
                for concept in ("revenue", "operating_income")}
    if not isinstance(facts, list) or manifest.get("fact_count") != len(expected) or len(facts) != len(expected):
        raise ValueError("The public source manifest has incomplete annual fact coverage.")
    actual, sectors = set(), {}
    for fact in facts:
        if not isinstance(fact, dict):
            raise ValueError("The public source fact inventory is invalid.")
        identity = (fact.get("ticker"), fact.get("fiscal_year"), fact.get("concept"))
        if identity not in expected or identity in actual or not isinstance(fact.get("sector"), str) or not fact["sector"].strip():
            raise ValueError("The public source fact inventory has duplicate or missing coverage.")
        actual.add(identity)
        if fact["ticker"] in sectors and sectors[fact["ticker"]] != fact["sector"]:
            raise ValueError("The public source sector metadata is inconsistent.")
        sectors[fact["ticker"]] = fact["sector"]
    raw = Path(corpus_path or ROOT / ".runtime/journey/sources/corpus.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != fingerprint:
        raise ValueError("The prepared source snapshot differs from its public manifest.")
    return {"company_years": {ticker: years for ticker in tickers},
            "source_fingerprint": fingerprint, "sectors": sectors}


def matches_prepared_source(config, expected):
    """Require exact scope, sectors and bytes, including no extra issuers."""
    companies = config.get("companies")
    if not isinstance(companies, list) or not all(isinstance(company, dict) for company in companies):
        return False
    tickers = [company.get("ticker") for company in companies]
    if not all(isinstance(ticker, str) for ticker in tickers) or len(set(tickers)) != len(tickers):
        return False
    return (config.get("company_years") == expected["company_years"]
            and config.get("source_fingerprint") == expected["source_fingerprint"]
            and {company["ticker"]: company.get("sector") for company in companies} == expected["sectors"]
            and config.get("years") == sorted({year for years in expected["company_years"].values() for year in years}))


def matches_prepared_retrieval(config, artifact_path=None, config_path=None):
    """Match service-reported readiness to the independently prepared local index."""
    from desk.retrieval import canonical_hash, load_config, model_fingerprint
    try:
        manifest = json.loads(Path(artifact_path or ROOT / ".runtime/journey/retrieval/manifest.json").read_text())
        recorded = manifest.pop("index_fingerprint")
        if canonical_hash(manifest) != recorded:
            return False
        policy = load_config(config_path)
        details = config.get("retrieval_details", {})
        return (config.get("semantic_retrieval") is True and config.get("retrieval") == "hybrid_rerank"
                and details.get("mode") == "hybrid_rerank" and details.get("ready") is True
                and details.get("backend") == "chroma_cosine" and details.get("semantic_retrieval") is True
                and details.get("source_fingerprint") == config.get("source_fingerprint") == manifest["corpus_fingerprint"]
                and details.get("index_fingerprint") == recorded
                and details.get("configuration_hash") == manifest["configuration_hash"] == canonical_hash(policy)
                and details.get("model_fingerprint") == manifest["model_fingerprint"] == model_fingerprint(policy)
                and details.get("encoder") == {key: policy["encoder"][key] for key in ("id", "revision")}
                and details.get("reranker") == {key: policy["reranker"][key] for key in ("id", "revision")})
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def analyst_token():
    """Read the existing credential; verification must never create or rotate it."""
    path = launch.ENV_FILE
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ValueError("The prepared private credential file is required.")
    lines = path.read_text().splitlines()
    if len(lines) != 1 or not re.fullmatch(r"ANALYST_API_TOKEN=[A-Za-z0-9_-]{32,}", lines[0]):
        raise ValueError("The prepared private credential format is required.")
    return lines[0].split("=", 1)[1]


def get_json(url, token=None):
    class LocalOnlyRedirects(HTTPRedirectHandler):
        def redirect_request(self, request, response, code, message, headers, new_url):
            return None

    headers = {"X-Analyst-Token": token} if token else {}
    opener = build_opener(ProxyHandler({}), LocalOnlyRedirects())
    try:
        with opener.open(Request(url, headers=headers), timeout=8) as response:
            return response.status, json.loads(response.read(2_000_000))
    except HTTPError as error:
        return error.code, None


def main():
    checks = []

    def record(name, passed, **observed):
        checks.append({"name": name, "passed": bool(passed), "observed": observed})

    def attempt(name, action):
        try:
            action()
        except Exception as error:
            # Exception messages and captured command output can contain private data.
            record(name, False, error_type=type(error).__name__)

    token = None
    try:
        token = analyst_token()
        record("private_credential", True, file_mode="0600")
    except Exception as error:
        record("private_credential", False, error_type=type(error).__name__)

    def health():
        status, data = get_json("http://127.0.0.1:18080/health")
        good = status == 200 and data == {"status": "ok", "mode": "offline", "data_source": "sec_edgar"}
        record("api_health", good, http_status=status, expected_offline_source=good)

    def unauthenticated():
        status, _ = get_json("http://127.0.0.1:18080/api/config")
        record("api_rejects_missing_token", status == 401, http_status=status)

    def configuration():
        if token is None:
            raise ValueError("Credential unavailable")
        status, data = get_json("http://127.0.0.1:18080/api/config", token)
        data = data if isinstance(data, dict) else {}
        source_scope = prepared_source_scope()
        expected = data.get("mode") == "offline" and data.get("data_source") == "sec_edgar" and data.get("transport") == "http" and matches_prepared_retrieval(data) and matches_prepared_source(data, source_scope)
        fingerprint = data.get("source_fingerprint", "")
        safe_fingerprint = fingerprint if isinstance(fingerprint, str) and re.fullmatch(r"[a-f0-9]{64}", fingerprint) else None
        record("authenticated_source_config", status == 200 and expected and bool(safe_fingerprint), http_status=status, expected_company_years=expected, source_sha256=safe_fingerprint)

    def budget():
        if token is None:
            raise ValueError("Credential unavailable")
        status, data = get_json("http://127.0.0.1:18080/api/budget", token)
        expected = {"cap_usd": 0, "spent_usd": 0, "model_calls": 0, "mode": "offline", "provider_key_configured": False}
        good = status == 200 and data == expected
        data = data if isinstance(data, dict) else {}
        record("zero_spend_offline_budget", good, http_status=status, cap_zero=data.get("cap_usd") == 0, spend_zero=data.get("spent_usd") == 0, model_calls_zero=data.get("model_calls") == 0, api_reports_provider_key_absent=data.get("provider_key_configured") is False)

    def notes():
        if token is None:
            raise ValueError("Credential unavailable")
        status, data = get_json("http://127.0.0.1:18080/api/notes", token)
        valid = status == 200 and isinstance(data, list)
        record("approved_notes_readable", valid, http_status=status, note_count=len(data) if valid else None)

    attempt("api_health", health)
    attempt("api_rejects_missing_token", unauthenticated)
    attempt("authenticated_source_config", configuration)
    attempt("zero_spend_offline_budget", budget)
    attempt("approved_notes_readable", notes)

    def docker_checks():
        if token is None:
            raise ValueError("Credential unavailable")
        docker = launch.docker_binary()
        env = launch.clean_environment(docker)
        command = launch.compose(docker)

        def capture(args):
            return launch.capture(args, env, token)

        ids = capture(command + ["ps", "--all", "--quiet"]).splitlines()
        if not ids or any(not re.fullmatch(r"[a-f0-9]{12,64}", value) for value in ids):
            raise ValueError("No unambiguous project containers")
        selected = capture([docker, "--context", launch.CONTEXT, "inspect", "--format", INSPECT, *ids])
        containers = [json.loads(line) for line in selected.splitlines() if line]
        if any(item.get("project") != launch.PROJECT for item in containers):
            raise ValueError("Container ownership mismatch")
        services = {item["service"]: item for item in containers}
        unique = len(services) == len(containers)
        worker = services.get("pandas-worker", {})
        worker_good = unique and worker.get("state") == "running" and worker.get("network_mode") == "none" and worker.get("read_only") is True and worker.get("mounts") == [{"destination": "/queue", "writable": True}] and worker.get("memory") == 268435456 and worker.get("pids_limit") == 32 and worker.get("nano_cpus") == 500000000 and worker.get("cap_drop") == ["ALL"]
        record("isolated_worker_configuration", worker_good, running=worker.get("state") == "running", network_none=worker.get("network_mode") == "none", read_only_root=worker.get("read_only") is True, queue_only=worker.get("mounts") == [{"destination": "/queue", "writable": True}], memory_bytes=worker.get("memory"), pids_limit=worker.get("pids_limit"), nano_cpus=worker.get("nano_cpus"), capabilities_dropped=worker.get("cap_drop") == ["ALL"])
        expected_ports = {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "18080"}], "3000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "13080"}]}
        ingress = services.get("ingress", {})
        other_ports_absent = all(not item.get("ports") for name, item in services.items() if name != "ingress")
        ports_good = unique and ingress.get("state") == "running" and ingress.get("ports") == expected_ports and other_ports_absent
        record("loopback_ingress_ports_only", ports_good, expected_loopback_bindings=ingress.get("ports") == expected_ports, other_services_unpublished=other_ports_absent)
        network_template = '{"internal":{{json .Internal}},"project":{{json (index .Labels "com.docker.compose.project")}}}'
        network = json.loads(capture([docker, "--context", launch.CONTEXT, "network", "inspect", launch.PROJECT + "_backend", "--format", network_template]))
        record("private_backend_network", network.get("internal") is True and network.get("project") == launch.PROJECT, internal=network.get("internal") is True, owned_by_project=network.get("project") == launch.PROJECT)
        targets = json.loads(capture(command + ["exec", "-T", "app", "python", "-c", PROMETHEUS_CHECK]))
        good = targets == {"api_ok": True, "matching_targets": 1, "up": True, "no_scrape_error": True}
        record("prometheus_app_scrape_ready", good, target_up=targets.get("up") is True, exactly_one_app_target=targets.get("matching_targets") == 1, no_scrape_error=targets.get("no_scrape_error") is True)

    attempt("docker_project_readiness", docker_checks)

    def grafana():
        status, data = get_json("http://127.0.0.1:13080/api/health")
        healthy = status == 200 and isinstance(data, dict) and data.get("database") == "ok"
        record("grafana_database_ready", healthy, http_status=status, database_ok=healthy)

    attempt("grafana_database_ready", grafana)
    passed = bool(checks) and all(check["passed"] for check in checks)
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "project": launch.PROJECT,
              "docker_context": launch.CONTEXT, "status": "passed" if passed else "failed", "checks": checks,
              "scope": "Readiness and configured Docker boundaries; no active containment attack or alert firing test.",
              "alert_firing_tested": False, "research_runs_created_by_verifier": 0, "human_decisions_performed": False}
    destination = ROOT / "evidence/runtime_checks.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Runtime readiness: {report['status']}. Sanitized evidence: evidence/runtime_checks.json")
    if not passed:
        print("Failed checks: " + ", ".join(check["name"] for check in checks if not check["passed"]))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
