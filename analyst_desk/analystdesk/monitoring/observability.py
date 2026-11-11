"""Traces and metrics (L13, L16).

Traces — as in the L14 lecture notebook: OpenTelemetry with OpenLLMetry's
LangChain auto-instrumentation (a span for every model and tool step), one
business span per agent run ("analystdesk.run", with run id, mode, outcome,
numbers verified, tokens), exported over OTLP to Jaeger. Enabled when
OTEL_EXPORTER_OTLP_ENDPOINT is set (Docker Compose sets it). Prompt and
completion text are NOT captured by default (TRACELOOP_TRACE_CONTENT=false):
traces must not become a second copy of everything the analyst typed.

Metrics — prometheus_client on /metrics (port METRICS_PORT, default 9464),
scraped by Prometheus and shown in Grafana:
    ad_runs_total{mode,outcome}           runs reaching a gate or the end
    ad_run_seconds{mode}                  run latency (histogram → median, p95)
    ad_tokens_total{mode}, ad_cost_usd_total{mode}
    ad_numbers_total{status}              verified / unverified numbers in drafts
    ad_critic_rejections_total{mode}      drafts sent back by the checker/critic
    ad_tool_calls_total{agent,tool,ok}    every tool call (from the hooks)
    ad_tool_denied_total{agent,reason}    hook denials (permission, budget)
    ad_edgar_requests_total{source}       EDGAR lookups: cache vs network
    ad_notes_published_total
Alert (docker/prometheus/alerts.yml): verified share below 98% over the
last hour.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

from prometheus_client import Counter, Histogram, start_http_server

PRICE_PER_M = float(os.getenv("PRICE_PER_M_TOKENS", "0.52"))   # see scripts/run.py eval

RUNS = Counter("ad_runs_total", "Agent runs reaching a gate or the end", ["mode", "outcome"])
RUN_SECONDS = Histogram("ad_run_seconds", "Agent run step latency", ["mode"],
                        buckets=(1, 5, 10, 20, 30, 60, 90, 120, 180, 300, 600))
TOKENS = Counter("ad_tokens_total", "Model tokens used", ["mode"])
COST = Counter("ad_cost_usd_total", "Estimated model cost in USD", ["mode"])
NUMBERS = Counter("ad_numbers_total", "Numbers in drafts at the note gate", ["status"])
REJECTIONS = Counter("ad_critic_rejections_total", "Drafts sent back for revision", ["mode"])
TOOL_CALLS = Counter("ad_tool_calls_total", "Tool calls", ["agent", "tool", "ok"])
TOOL_DENIED = Counter("ad_tool_denied_total", "Tool calls denied by hooks", ["agent", "reason"])
EDGAR = Counter("ad_edgar_requests_total", "EDGAR company-facts lookups", ["source"])
PUBLISHED = Counter("ad_notes_published_total", "Notes published after approval")

_metrics_started = False
_tracer = None


def start_metrics_server() -> None:
    """Expose /metrics once per process (the app calls this at start-up)."""
    global _metrics_started
    if not _metrics_started:
        start_http_server(int(os.getenv("METRICS_PORT", "9464")), addr=os.getenv("METRICS_HOST", "127.0.0.1"))
        _metrics_started = True


def init_tracing(service: str = "analyst-desk"):
    """OpenTelemetry → OTLP (Jaeger), plus LangChain auto-instrumentation."""
    global _tracer
    if _tracer is not None:
        return _tracer
    from opentelemetry import trace
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            provider = TracerProvider(resource=Resource.create({"service.name": service}))
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
            trace.set_tracer_provider(provider)
            from opentelemetry.instrumentation.langchain import LangchainInstrumentor
            LangchainInstrumentor().instrument()
    _tracer = trace.get_tracer("analystdesk")
    return _tracer


@contextmanager
def run_span(run_id: str, mode: str):
    """The business span around one agent step (start → gate)."""
    tracer = _tracer or init_tracing()
    with tracer.start_as_current_span("analystdesk.run") as span:
        span.set_attribute("analystdesk.run_id", run_id)
        span.set_attribute("analystdesk.mode", mode)
        yield span


def record_run(mode: str, values: dict, interrupts: list, seconds: float, span=None) -> None:
    """Metrics (and span attributes) for one run step that reached a gate or the end."""
    gate = interrupts[0]["gate"] if interrupts else None
    outcome = (f"waiting_{gate}" if gate else values.get("outcome")
               or ("out_of_scope" if values.get("guard") and not values["guard"].get("ok") else "stopped"))
    RUNS.labels(mode, outcome).inc()
    RUN_SECONDS.labels(mode).observe(seconds)
    if gate == "note" and values.get("check"):
        c = values["check"]
        NUMBERS.labels("verified").inc(c.get("verified", 0))
        NUMBERS.labels("unverified").inc(max(c.get("total", 0) - c.get("verified", 0), 0))
        REJECTIONS.labels(mode).inc(values.get("revisions", 0))
    if outcome == "published":
        PUBLISHED.inc()
    if span is not None:
        span.set_attribute("analystdesk.outcome", outcome)
        span.set_attribute("analystdesk.tokens", int(values.get("tokens", 0) or 0))
        span.set_attribute("analystdesk.tool_calls", int(values.get("tool_calls", 0) or 0))
        if values.get("check"):
            span.set_attribute("analystdesk.verified_share", float(values["check"].get("verified_share", 0)))


def record_tokens(mode: str, tokens: int) -> None:
    if tokens > 0:
        TOKENS.labels(mode).inc(tokens)
        COST.labels(mode).inc(tokens * PRICE_PER_M / 1e6)


def record_tool(event: dict) -> None:
    agent = event["agent"].split("/")[0]
    TOOL_CALLS.labels(agent, event["tool"], str(event["ok"]).lower()).inc()
    if event.get("denied"):
        TOOL_DENIED.labels(agent, event.get("error") or "denied").inc()
