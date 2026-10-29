"""Analyst Desk — Interactive UI with Dashboard + Chat.

Run with:
    /Users/25.jayshree/Documents/Jayshree.agentic/.venv/bin/python app.py

Opens at http://127.0.0.1:7861

Layout:
  Dashboard      : financial metrics charts + data stats
  Research       : choose C0 baseline, C1 single agent, or C2 team
  Evaluation     : run evaluation cases and review results
  Data Explorer  : browse passages and search the index
  Raw Data       : view baseline JSON output
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analystdesk.baseline import run_baseline
from analystdesk.api import create_app
from analystdesk.edgar import get_quarterly_financials
from analystdesk.ingest import ingest_all, load_passages, PASSAGES_DIR
from analystdesk.scope import COMPANIES, C0_COMPANIES, create_request

_retriever_state = "loading"
_retriever_state_lock = threading.Lock()


def _retriever_readiness() -> str | None:
    with _retriever_state_lock:
        return None if _retriever_state == "ready" else f"retriever_{_retriever_state}"


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_baseline_data(company_names, years=(2022, 2023, 2024)):
    request = create_request(company_names, list(years))
    return run_baseline(request)


def _passage_stats():
    files = list(PASSAGES_DIR.glob("*.jsonl"))
    total = sum(
        sum(1 for l in f.read_text().splitlines() if l.strip())
        for f in files
    )
    return len(files), total


# ── dashboard charts ──────────────────────────────────────────────────────────

def build_revenue_chart(note):
    fig = go.Figure()
    companies = list(dict.fromkeys(row.company for row in note.rows))
    colors = _company_colors(companies)
    for company in companies:
        rows = [row for row in note.rows if row.company == company]
        fig.add_trace(go.Bar(
            name=company,
            x=[row.fiscal_year for row in rows],
            y=[row.revenue_usd_m for row in rows],
            marker_color=colors[company],
            text=[f"${value / 1000:.1f}B" if value is not None else "—"
                  for value in (row.revenue_usd_m for row in rows)],
            textposition="outside",
        ))
    fig.update_layout(
        title="Revenue (USD Millions) — EDGAR XBRL verified",
        barmode="group", xaxis_title="Fiscal Year", yaxis_title="USD Millions",
        legend=dict(orientation="h", y=1.1), height=380,
        margin=dict(t=60, b=40),
    )
    return fig


def build_margin_chart(note):
    fig = go.Figure()
    companies = list(dict.fromkeys(row.company for row in note.rows))
    colors = _company_colors(companies)
    for company in companies:
        rows = [row for row in note.rows if row.company == company]
        basis = rows[0].margin_basis
        margin_type = "Pre-tax" if basis == "pretax" else "Operating"
        margins = [row.headline_margin_pct() for row in rows]
        fig.add_trace(go.Scatter(
            name=f"{company} ({margin_type})",
            x=[row.fiscal_year for row in rows],
            y=margins,
            mode="lines+markers+text",
            text=[f"{margin:.1f}%" if margin is not None else "—" for margin in margins],
            textposition="top center",
            line=dict(color=colors[company], width=3), marker=dict(size=10),
        ))
    fig.update_layout(
        title="Headline Margin (%) — Operating or Pre-tax as applicable",
        xaxis_title="Fiscal Year", yaxis_title="Margin %",
        legend=dict(orientation="h", y=1.1), height=380,
        margin=dict(t=60, b=40),
    )
    return fig


def build_income_chart(note):
    fig = go.Figure()
    companies = list(dict.fromkeys(row.company for row in note.rows))
    colors = _company_colors(companies)
    for company in companies:
        rows = [row for row in note.rows if row.company == company]
        basis = rows[0].margin_basis
        income_type = "Pre-tax income" if basis == "pretax" else "Operating income"
        fig.add_trace(go.Scatter(
            name=f"{company} ({income_type})",
            x=[row.fiscal_year for row in rows],
            y=[row.pretax_income_usd_m if basis == "pretax"
               else row.operating_income_usd_m for row in rows],
            mode="lines+markers",
            line=dict(color=colors[company], width=2),
        ))
    fig.update_layout(
        title="Headline Income (USD Millions) — Operating or Pre-tax as applicable",
        xaxis_title="Fiscal Year", yaxis_title="USD Millions",
        legend=dict(orientation="h", y=1.1), height=380,
        margin=dict(t=60, b=40),
    )
    return fig


def _company_colors(companies):
    palette = [
        "#0078D4", "#34A853", "#F4B400", "#EA4335", "#9334E6",
        "#00ACC1", "#FF7043", "#5C6BC0", "#7CB342", "#8D6E63",
        "#EC407A", "#78909C", "#26A69A", "#AB47BC", "#9E9D24",
    ]
    return {company: palette[index % len(palette)] for index, company in enumerate(companies)}


_CHART_KEYWORDS = {"chart", "plot", "graph", "visuali", "trend", "quarterly", "quarter"}

def _wants_chart(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _CHART_KEYWORDS)


def build_chat_chart(years: list[int]) -> go.Figure | None:
    """Generate a quarterly revenue + margin chart for MSFT and GOOGL."""
    company_map = {c.ticker: c for c in COMPANIES}
    series: dict[str, dict] = {}

    for ticker in ("MSFT", "GOOGL"):
        company = company_map[ticker]
        quarters_x, rev_y, margin_y = [], [], []
        for year in years:
            qtrs = get_quarterly_financials(company.cik, year)
            for q in qtrs:
                label = f"FY{year} {q['quarter']}"
                quarters_x.append(label)
                rev = q["revenue"]
                op  = q["operating_income"]
                rev_y.append(round(rev["val"] / 1_000_000, 1) if rev else None)
                if rev and op and rev["val"]:
                    margin_y.append(round(op["val"] / rev["val"] * 100, 1))
                else:
                    margin_y.append(None)
        series[ticker] = {"x": quarters_x, "rev": rev_y, "margin": margin_y}

    if not any(series[t]["x"] for t in series):
        return None

    colors = {"MSFT": "#0078D4", "GOOGL": "#34A853"}
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=("Quarterly Revenue (USD Millions)", "Quarterly Operating Margin (%)"),
        vertical_spacing=0.12,
    )
    for ticker, s in series.items():
        fig.add_trace(go.Bar(
            name=f"{ticker} Revenue", x=s["x"], y=s["rev"],
            marker_color=colors[ticker], opacity=0.85, legendgroup=ticker,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            name=f"{ticker} Margin", x=s["x"], y=s["margin"],
            mode="lines+markers", line=dict(color=colors[ticker], width=2),
            marker=dict(size=7), legendgroup=ticker, showlegend=False,
        ), row=2, col=1)

    fig.update_layout(
        height=520, barmode="group",
        legend=dict(orientation="h", y=1.08),
        margin=dict(t=80, b=40),
        title_text="MSFT vs GOOGL — Quarterly Profitability (EDGAR XBRL verified)",
    )
    return fig


# ── UI ────────────────────────────────────────────────────────────────────────

def load_dashboard(company_names):
    if not company_names:
        raise gr.Error("Select at least one company to load the dashboard.")
    note = _get_baseline_data(company_names)
    n_files, n_passages = _passage_stats()

    rows = []
    for row in note.rows:
        headline_income = (
            row.pretax_income_usd_m if row.margin_basis == "pretax"
            else row.operating_income_usd_m
        )
        rows.append([
            row.company,
            row.fiscal_year,
            row.period_end,
            f"${row.revenue_usd_m:,.1f}M" if row.revenue_usd_m is not None else "—",
            f"${headline_income:,.1f}M" if headline_income is not None else "—",
            f"{row.headline_margin_pct():.1f}%"
            if row.headline_margin_pct() is not None else "—",
            "✅" if row.revenue_fact_id and row.headline_income_fact_id() else "❌",
        ])

    stats_md = (
        f"| Metric | Value |\n|--------|-------|\n"
        f"| Selected companies | {', '.join(company_names)} |\n"
        f"| Fiscal Years | 2022 · 2023 · 2024 |\n"
        f"| EDGAR Verified | {note.verification_pct()}% |\n"
        f"| 10-K Documents Indexed | {n_files} |\n"
        f"| Text Passages Indexed | {n_passages if n_passages else '⚠️ Run ingestion first'} |\n"
        f"| Pipeline | C0 No-Agent baseline |\n"
    )

    return (
        build_revenue_chart(note),
        build_margin_chart(note),
        build_income_chart(note),
        rows,
        stats_md,
    )


def _try_preload_retriever():
    """Start loading the retriever in a background thread so the UI launches immediately."""
    global _retriever_state
    _, n = _passage_stats()
    if n == 0:
        with _retriever_state_lock:
            _retriever_state = "failed"
        logging.getLogger(__name__).error("Retriever startup failed: no passages are available")
        return

    def _load():
        global _retriever_state
        try:
            from analystdesk.retrieve import get_retriever
            get_retriever()
        except Exception:
            with _retriever_state_lock:
                _retriever_state = "failed"
            logging.getLogger(__name__).exception("Could not preload retriever")
            return
        with _retriever_state_lock:
            _retriever_state = "ready"
        print(f"✓ Retriever ready ({n} passages)")

    threading.Thread(target=_load, daemon=True).start()
    print(f"⏳ Loading retriever in background ({n} passages)...")


def run_ingestion():
    yield "Starting 10-K ingestion (downloading filings from EDGAR)...\n"
    try:
        passages = ingest_all()
        n_files, n_passages = _passage_stats()
        from analystdesk.retrieve import reset_retriever, get_retriever
        reset_retriever()
        get_retriever(passages)   # build index immediately
        yield f"✅ Done — {n_files} documents, {n_passages} passages indexed. Chat is ready."
    except Exception as e:
        yield f"❌ Ingestion failed: {e}"


def _steps_markdown(result: dict) -> str:
    """How C0 built its answer: the fixed searches, EDGAR facts and model."""
    st = result.get("steps", {})
    searches = "\n".join(
        f"| {i} | {s['company'] or 'all'} | {s['year'] or 'all years'} | {s['query']} |"
        for i, s in enumerate(st.get("searches", []), 1))
    annual = "\n".join(f"- {ln.strip()}" for ln in st.get("edgar_numbers", "").splitlines()
                       if "Annual" in ln)
    years = result.get("years") or []
    return (
        f"**Pipeline:** C0 fixed workflow. Code decides every step; one model call "
        f"(`{result.get('model')}`). C1/C2 research modes show real MCP tool calls.\n\n"
        f"**1. Searches over 10-K passages** (BM25 + vectors, reranked; one per company/year):\n\n"
        f"| # | Company | Year | Search text |\n|---|---|---|---|\n{searches}\n\n"
        f"**2. EDGAR XBRL facts given to the model** ({', '.join(st.get('edgar_companies', []))}, "
        f"FY{min(years)}–FY{max(years)}):\n\n{annual or '_none_'}\n\n"
        f"**3. Passages cited:** see the table below."
    )


def chat_fn(message, history, question_mode, conversation_context):
    if not message.strip():
        yield history, "", [], None, "", conversation_context
        return

    history = list(history or [])
    conversation_context = list(conversation_context or [])
    from analystdesk.chat_context import build_chat_question
    try:
        question_for_answer = build_chat_question(
            message, question_mode, conversation_context
        )
    except ValueError as e:
        history.extend([
            {"role": "user", "content": message},
            {
                "role": "assistant",
                "content": str(e),
            },
        ])
        yield history, "", [], None, "", conversation_context
        return

    active_context = conversation_context if question_mode == "follow_up" else []
    # Prefer years in the current question; otherwise inherit years from context.
    from analystdesk.query import find_years
    years = [
        y for y in find_years(message) if y in (2022, 2023, 2024)
    ] or [
        y for y in find_years(question_for_answer) if y in (2022, 2023, 2024)
    ] or [2022, 2023, 2024]

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": "⏳ Searching filings and EDGAR facts..."})
    yield history, "", [], None, "", active_context

    n_files, n_passages = _passage_stats()
    if n_passages == 0:
        history[-1]["content"] = (
            "⚠️ No passages indexed yet. Please click **Run Ingestion** "
            "in the Dashboard tab first."
        )
        yield history, "", [], None, "", active_context
        return

    try:
        from analystdesk.retrieve import get_retriever
        from analystdesk.c0_pipeline import answer
        retriever = get_retriever()
        result = answer(question_for_answer, retriever, years=years)
        ans = result["answer"]
        hits = result["passages"]

        # Generate chart if user asked for one
        chart = build_chat_chart(years) if _wants_chart(question_for_answer) else None

        # Format citations
        cite_rows = [[
            h["passage_id"], h["company"],
            str(h["fiscal_year"]), h.get("item_label", ""),
            f"{h.get('score', 0):.3f}",
            h["text"][:200] + "…"
        ] for h in hits]

        history[-1]["content"] = ans
        updated_context = (active_context + [{"question": message, "answer": ans}])[-3:]
        yield history, "", cite_rows, chart, _steps_markdown(result), updated_context

    except Exception as e:
        history[-1]["content"] = f"❌ Error: {e}"
        yield history, "", [], None, "", active_context


def search_passages(query, company_filter, year_filter):
    n_files, n_passages = _passage_stats()
    if n_passages == 0:
        return [["—", "—", "—", "—", "⚠️ Run ingestion first"]]
    try:
        from analystdesk.retrieve import get_retriever
        company = company_filter if company_filter != "All" else None
        year = int(year_filter) if year_filter != "All" else None
        retriever = get_retriever()
        hits = retriever.search(query, top_k=8, company=company, year=year)
        return [[
            h["passage_id"], h["company"], str(h["fiscal_year"]),
            h.get("item_label", h["item"]),
            f"{h.get('score', 0):.3f}",
            h["text"][:300] + "…"
        ] for h in hits]
    except Exception as e:
        return [["—", "—", "—", "—", str(e), ""]]


# ── Gradio app ────────────────────────────────────────────────────────────────

with gr.Blocks(title="Analyst Desk") as demo:
    gr.Markdown(
        "# 📊 Analyst Desk\n"
        "**15 companies · Tech + Finance · SEC EDGAR XBRL · C0 Fixed RAG Pipeline** · "
        "IIT Bombay Agentic AI Capstone"
    )

    # ── Tab 1: Dashboard ──────────────────────────────────────────────────────
    with gr.Tab("📈 Dashboard"):
        with gr.Row():
            dashboard_companies = gr.Dropdown(
                choices=[company.name for company in COMPANIES],
                value=[company.name for company in C0_COMPANIES],
                multiselect=True,
                label="Companies",
                info="Select one or more companies to populate the charts and metrics.",
                scale=5,
            )
            refresh_btn = gr.Button("🔄 Refresh", size="sm")
        with gr.Row():
            ingest_btn = gr.Button("⬇️ Run Ingestion (downloads 10-K filings)", size="sm", variant="primary")
        ingest_status = gr.Markdown()

        stats_md = gr.Markdown()

        with gr.Row():
            rev_chart = gr.Plot(label="Revenue")
            margin_chart = gr.Plot(label="Headline Margin")

        income_chart = gr.Plot(label="Headline Income")

        metrics_table = gr.Dataframe(
            headers=["Company", "FY", "Period End", "Revenue", "Headline Income", "Headline Margin", "Verified"],
            label="All Metrics (EDGAR XBRL verified)",
            wrap=True,
        )

    # ── Tab 2: Research workflow selection ────────────────────────────────────
    with gr.Tab("🔎 Research"):
        workflow_mode = gr.Radio(
            [
                ("C0 · No-Agent (Baseline)", "c0"),
                ("C1 · Single agent", "c1"),
                ("C2 · Team", "c2"),
            ],
            value="c0",
            label="Choose a research workflow",
            info="C0 answers directly; C1 and C2 run agent workflows with plan and note approval gates.",
        )

        with gr.Group() as baseline_panel:
            gr.Markdown(
                "**C0 · No-Agent (Baseline)** — a fixed retrieval workflow with one model call. "
                "Answers use retrieved 10-K passages and EDGAR-verified numbers with citations. "
                "Name the companies and, optionally, years (default FY2022–2024)."
            )
            chat_mode = gr.Radio(
                [
                    ("New question (independent)", "new"),
                    ("Follow-up (uses recent chat context)", "follow_up"),
                ],
                value="new",
                label="Question type",
                info="Follow-ups use up to the three most recent C0 question-and-answer pairs.",
            )
            chat_context = gr.State([])

            chatbot = gr.Chatbot(
                height=420, label="Research Assistant",
                placeholder="Ask about any of the 15 companies: financials, risk factors or MD&A...",
            )
            with gr.Row():
                chat_input = gr.Textbox(
                    placeholder="e.g. What were the main risk factors for Microsoft in 2024?",
                    label="Question", scale=5,
                )
                send_btn = gr.Button("Run C0 baseline", variant="primary", scale=1)

            gr.Examples(
                examples=[
                    ["Compare Microsoft and Alphabet operating margins over 2022–2024"],
                    ["Visa vs Mastercard net revenue in 2024"],
                    ["What were JPMorgan's main risk factors in 2024?"],
                    ["How does the asset cap affect Wells Fargo in 2022?"],
                    ["What risks did NVIDIA highlight about export controls to China in 2023?"],
                ],
                inputs=chat_input,
            )

            with gr.Accordion("🔧 How this answer was built: searches, EDGAR facts, model", open=False):
                chat_steps = gr.Markdown()

            chat_chart = gr.Plot(label="Chart (auto-generated from EDGAR data)", visible=True)
            citations_table = gr.Dataframe(
                headers=["passage_id", "company", "year", "section", "score", "text preview"],
                label="Retrieved passages (citations)",
                wrap=True,
            )

        with gr.Group(visible=False) as agent_panel:
            from agent_ui import build_agent_panel
            agent_load, agent_load_in, agent_load_out = build_agent_panel(workflow_mode)

        def show_workflow(mode):
            return gr.update(visible=mode == "c0"), gr.update(visible=mode in ("c1", "c2"))

        workflow_mode.change(
            fn=show_workflow,
            inputs=workflow_mode,
            outputs=[baseline_panel, agent_panel],
        )

    demo.load(fn=agent_load, inputs=agent_load_in, outputs=agent_load_out)

    # ── Tab 3: Evaluation (golden set, runs, results, judge calibration) ──────
    from eval_ui import build_eval_tab
    eval_load, eval_load_out = build_eval_tab()
    demo.load(fn=eval_load, outputs=eval_load_out)

    # ── Tab 4: Data Explorer ──────────────────────────────────────────────────
    with gr.Tab("🔍 Data Explorer"):
        gr.Markdown(
            "Search the passage index directly. Useful for understanding what "
            "was retrieved and debugging retrieval quality."
        )
        with gr.Row():
            search_query = gr.Textbox(label="Search query", scale=3)
            company_dd = gr.Dropdown(
                ["All"] + [c.ticker for c in COMPANIES], value="All", label="Company", scale=1
            )
            year_dd = gr.Dropdown(
                ["All", "2022", "2023", "2024"], value="All", label="Year", scale=1
            )
            search_btn = gr.Button("Search", variant="primary", scale=1)

        search_results = gr.Dataframe(
            headers=["passage_id", "company", "year", "section", "score", "text preview"],
            label="Search results (BM25 + vectors + RRF + reranked)",
            wrap=True,
        )

    # ── Tab 5: Raw JSON ───────────────────────────────────────────────────────
    with gr.Tab("🗂️ Raw Data"):
        gr.Markdown("Full `ResearchNote` JSON from the C0 baseline pipeline.")
        raw_btn = gr.Button("Load Raw JSON")
        raw_json = gr.Code(language="json", label="ResearchNote JSON")

    # ── event handlers ────────────────────────────────────────────────────────

    def refresh_dashboard(company_names):
        rev, margin, income, rows, stats = load_dashboard(company_names)
        return rev, margin, income, rows, stats

    def load_raw():
        note = _get_baseline_data([company.name for company in C0_COMPANIES])
        return note.to_json()

    demo.load(
        fn=refresh_dashboard,
        inputs=[dashboard_companies],
        outputs=[rev_chart, margin_chart, income_chart, metrics_table, stats_md],
    )
    # Preload the retriever in the background for baseline research.
    _try_preload_retriever()
    refresh_btn.click(
        fn=refresh_dashboard,
        inputs=[dashboard_companies],
        outputs=[rev_chart, margin_chart, income_chart, metrics_table, stats_md],
    )
    ingest_btn.click(fn=run_ingestion, outputs=ingest_status)

    send_btn.click(
        fn=chat_fn,
        inputs=[chat_input, chatbot, chat_mode, chat_context],
        outputs=[chatbot, chat_input, citations_table, chat_chart, chat_steps, chat_context],
    )
    chat_input.submit(
        fn=chat_fn,
        inputs=[chat_input, chatbot, chat_mode, chat_context],
        outputs=[chatbot, chat_input, citations_table, chat_chart, chat_steps, chat_context],
    )

    search_btn.click(
        fn=search_passages,
        inputs=[search_query, company_dd, year_dd],
        outputs=search_results,
    )
    raw_btn.click(fn=load_raw, outputs=raw_json)

api = create_app(demo, readiness_check=_retriever_readiness)


if __name__ == "__main__":
    # /metrics for Prometheus; traces to Jaeger when OTEL_EXPORTER_OTLP_ENDPOINT is set
    from analystdesk.observability import init_tracing, start_metrics_server
    start_metrics_server()
    init_tracing()
    import uvicorn

    uvicorn.run(
        api,
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "7861")),
    )
