"""Read active Prometheus alerts for the Analyst Desk UI and API."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from typing import TypedDict
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class ActiveAlert(TypedDict):
    state: str
    name: str
    severity: str
    summary: str
    active_at: str


class PrometheusUnavailable(RuntimeError):
    """Raised when Prometheus cannot provide a valid active-alert response."""


def fetch_active_alerts() -> list[ActiveAlert]:
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090").rstrip("/")
    try:
        parsed_url = urlsplit(prometheus_url)
        parsed_url.port
    except ValueError as exc:
        raise PrometheusUnavailable("PROMETHEUS_URL is invalid") from exc
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise PrometheusUnavailable("PROMETHEUS_URL must be an absolute HTTP(S) URL")

    request = Request(
        f"{prometheus_url}/api/v1/alerts",
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=3) as response:
            payload = json.loads(response.read())
    except (URLError, TimeoutError, OSError) as exc:
        raise PrometheusUnavailable("Prometheus could not be reached") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PrometheusUnavailable("Prometheus returned invalid JSON") from exc

    if not isinstance(payload, dict) or payload.get("status") != "success":
        raise PrometheusUnavailable("Prometheus returned an unsuccessful response")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise PrometheusUnavailable("Prometheus returned an invalid alerts response")
    if "alerts" not in data:
        raise PrometheusUnavailable("Prometheus response does not contain alerts")
    raw_alerts = data["alerts"]
    if raw_alerts is None:
        raw_alerts = []
    if not isinstance(raw_alerts, list):
        raise PrometheusUnavailable("Prometheus returned an invalid alerts list")

    alerts: list[ActiveAlert] = []
    for raw_alert in raw_alerts:
        if not isinstance(raw_alert, dict):
            raise PrometheusUnavailable("Prometheus returned an invalid alert")
        labels = raw_alert.get("labels") or {}
        annotations = raw_alert.get("annotations") or {}
        if not isinstance(labels, dict) or not isinstance(annotations, dict):
            raise PrometheusUnavailable("Prometheus returned invalid alert labels")
        name = labels.get("alertname")
        state = raw_alert.get("state")
        if not isinstance(name, str) or not isinstance(state, str):
            raise PrometheusUnavailable("Prometheus returned an alert without a name or state")
        severity = labels.get("severity", "unknown")
        summary = annotations.get("summary", "")
        active_at = raw_alert.get("activeAt", "")
        if not all(isinstance(value, str) for value in (severity, summary, active_at)):
            raise PrometheusUnavailable("Prometheus returned invalid alert details")
        alerts.append(
            {
                "state": state,
                "name": name,
                "severity": severity,
                "summary": summary,
                "active_at": active_at,
            }
        )
    return alerts


def alert_panel_data(
    alert_reader: Callable[[], list[ActiveAlert]] = fetch_active_alerts,
) -> tuple[str, list[list[str]]]:
    try:
        alerts = alert_reader()
    except PrometheusUnavailable as exc:
        logger.warning("Unable to refresh in-app alerts: %s", exc)
        return "⚠️ Monitoring is unavailable; Prometheus could not be reached.", []

    if not alerts:
        return "✅ Monitoring is connected; there are no active alerts.", []

    rows = [
        [
            alert["state"],
            alert["name"],
            alert["severity"],
            alert["summary"],
            alert["active_at"],
        ]
        for alert in alerts
    ]
    return f"⚠️ {len(alerts)} active alert(s).", rows
