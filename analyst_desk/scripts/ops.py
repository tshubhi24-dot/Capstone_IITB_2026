"""Operations workflows: deployment smoke checks and published-note memory recovery.

    python scripts/ops.py smoke [--app-url URL] [--output FILE]
    python scripts/ops.py backfill-memory [--analyst NAME]

Smoke checks read deployment HTTP endpoints without model calls. Memory recovery
updates the local memory store and preserves deleted/withdrawn-note exclusions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


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


def smoke(args: argparse.Namespace) -> int:
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


def backfill_memory(args: argparse.Namespace) -> None:
    from analystdesk.memory.store import remember_published_note, suppressed_notes
    from analystdesk.servers.portal import _db_path, inactive_note_ids

    path = _db_path()
    if not path.exists():
        print("No portal database yet: nothing to backfill.")
        return
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = con.execute("SELECT id, title, body, tickers, approver, published_at FROM notes ORDER BY id").fetchall()
    con.close()
    deleted = asyncio.run(suppressed_notes())
    inactive = inactive_note_ids()
    for note_id, title, body, tickers, approver, published_at in rows:
        if note_id in inactive:
            print(f"note #{note_id}: skipped, withdrawn or superseded")
            continue
        if note_id in deleted:
            print(f"note #{note_id}: skipped, deleted from memory by the analyst")
            continue
        figures = asyncio.run(remember_published_note(
            note_id, title, body, json.loads(tickers), approver, args.analyst, published_at))
        print(f"note #{note_id}: remembered figures for {', '.join(sorted(figures)) or 'none'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    workflows = parser.add_subparsers(dest="workflow", required=True)
    check = workflows.add_parser("smoke", help="Read-only HTTP checks of app, metrics, alerts and Grafana")
    check.add_argument("--app-url", default="http://127.0.0.1:7861")
    check.add_argument("--prometheus-url", default="http://127.0.0.1:9090")
    check.add_argument("--grafana-url", default="http://127.0.0.1:3000")
    check.add_argument("--output", type=Path, help="Save actual HTTP check results as JSON")
    recovery = workflows.add_parser("backfill-memory", help="Recover memory from eligible published notes")
    recovery.add_argument("--analyst", default="analyst", help="Whose coverage list to update")
    args = parser.parse_args(argv)
    if args.workflow == "smoke":
        return smoke(args)
    backfill_memory(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
