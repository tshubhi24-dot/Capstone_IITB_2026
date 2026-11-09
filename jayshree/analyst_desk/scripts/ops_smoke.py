"""Check a running Analyst Desk deployment without creating notes or spending tokens.

Run from the host after Docker Compose is healthy:
    python scripts/ops_smoke.py
    python scripts/ops_smoke.py --app-url http://127.0.0.1:7861

Checks actual HTTP endpoints, Prometheus scraping and the configured alert,
plus Grafana. No OpenRouter request is made by this script. This is a smoke
check, not a replacement for an agent evaluation or a security assessment.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _get_json(url: str, timeout: float = 8.0) -> dict:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(2_000_000)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"cannot fetch {url}: {exc}") from exc
    try:
        result = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{url} did not return valid JSON") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"{url} returned an unexpected JSON payload")
    return result


def check_deployment(app_url: str, prometheus_url: str, grafana_url: str) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn) -> None:
        try:
            fn()
        except (RuntimeError, KeyError, TypeError, ValueError, IndexError) as exc:
            results.append((name, False, str(exc)))
        else:
            results.append((name, True, "OK"))

    def require(ok: bool, message: str) -> None:
        if not ok:
            raise RuntimeError(message)

    def health() -> None:
        data = _get_json(app_url + "/healthz")
        require(data.get("status") == "ok", f"unexpected health: {data}")

    def ready() -> None:
        data = _get_json(app_url + "/readyz")
        require(data.get("status") == "ready", f"app not ready: {data}")

    def alert_api() -> None:
        data = _get_json(app_url + "/api/alerts")
        require(data.get("status") == "available" and isinstance(data.get("alerts"), list),
                "in-app alert endpoint is not connected to Prometheus")

    def scrape() -> None:
        query = urlencode({"query": 'up{job="analyst-desk"}'})
        data = _get_json(prometheus_url + "/api/v1/query?" + query)
        require(data.get("status") == "success", "Prometheus query failed")
        series = data.get("data", {}).get("result", [])
        require(len(series) == 1 and series[0].get("value", [None, None])[1] == "1",
                "Prometheus is not successfully scraping app:9464")

    def rule() -> None:
        data = _get_json(prometheus_url + "/api/v1/rules?type=alert")
        require(data.get("status") == "success", "Prometheus rules endpoint failed")
        alerts = [r.get("name") for group in data.get("data", {}).get("groups", [])
                  for r in group.get("rules", [])]
        require("VerifiedShareBelow98" in alerts,
                "VerifiedShareBelow98 rule is not loaded in Prometheus")

    def grafana() -> None:
        data = _get_json(grafana_url + "/api/health")
        require(data.get("database") == "ok", f"Grafana health is not OK: {data}")

    for name, fn in [
        ("FastAPI liveness", health),
        ("FastAPI readiness", ready),
        ("In-app alerts", alert_api),
        ("Prometheus scrape", scrape),
        ("98% accuracy alert loaded", rule),
        ("Grafana health", grafana),
    ]:
        check(name, fn)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-url", default="http://127.0.0.1:7861")
    parser.add_argument("--prometheus-url", default="http://127.0.0.1:9090")
    parser.add_argument("--grafana-url", default="http://127.0.0.1:3000")
    parser.add_argument("--output", type=Path,
                        help="save real HTTP smoke-test results as JSON for the submission")
    args = parser.parse_args()
    results = check_deployment(args.app_url.rstrip("/"), args.prometheus_url.rstrip("/"),
                               args.grafana_url.rstrip("/"))
    if args.output:
        evidence = {
            "kind": "real_deployment_http_smoke_test",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "checks": [{"name": name, "passed": ok, "detail": detail} for name, ok, detail in results],
            "overall_passed": all(ok for _, ok, _ in results),
            "limitations": "Read-only HTTP checks only; not proof of live agents, tracing, alert firing or CI.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} | {name}: {detail}")
    print(f"{sum(ok for _, ok, _ in results)}/{len(results)} checks passed")
    if args.output:
        print(f"saved deployment evidence: {args.output}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
