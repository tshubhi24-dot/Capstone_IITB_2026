"""Analyst Desk — Interactive UI with Dashboard + Chat.

Run with:
    /Users/25.jayshree/Documents/Jayshree.agentic/.venv/bin/python app.py

Opens at http://127.0.0.1:7861

Layout:
  Tab 1 — Dashboard   : financial metrics charts + data stats
  Tab 2 — Chat        : ask research questions, get cited answers
  Tab 3 — Data Explorer: browse passages and search the index
  Tab 4 — Raw Data    : baseline JSON output
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analystdesk.baseline import run_baseline
from analystdesk.edgar import get_quarterly_financials
from analystdesk.ingest import ingest_all, load_passages, PASSAGES_DIR
from analystdesk.scope import COMPANIES, C0_COMPANIES, create_request


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_baseline_data(years=(2022, 2023, 2024)):
    request = create_request([c.name for c in C0_COMPANIES], list(years))
    note = run_baseline(request)
    return note


def _passage_stats():
    files = list(PASSAGES_DIR.glob("*.jsonl"))
    total = sum(
        sum(1 for l in f.read_text().splitlines() if l.strip())
        for f in files
    )
    return len(files), total


# ── dashboard charts ──────────────────────────────────────────────────────────

def build_revenue_chart(note):
    msft = [r for r in note.rows if r.company == "Microsoft"]
    googl = [r for r in note.rows if r.company == "Alphabet"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Microsoft", x=[r.fiscal_year for r in msft],
        y=[r.revenue_usd_m for r in msft],
        marker_color="#0078D4", text=[f"${r.revenue_usd_m/1000:.1f}B" for r in msft],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Alphabet", x=[r.fiscal_year for r in googl],
        y=[r.revenue_usd_m for r in googl],
        marker_color="#34A853", text=[f"${r.revenue_usd_m/1000:.1f}B" for r in googl],
        textposition="outside",
    ))
    fig.update_layout(
        title="Revenue (USD Millions) — EDGAR XBRL Verified",
        barmode="group", xaxis_title="Fiscal Year", yaxis_title="USD Millions",
        legend=dict(orientation="h", y=1.1), height=380,
        margin=dict(t=60, b=40),
    )
    return fig


def build_margin_chart(note):
    msft = [r for r in note.rows if r.company == "Microsoft"]
    googl = [r for r in note.rows if r.company == "Alphabet"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Microsoft", x=[r.fiscal_year for r in msft],
        y=[r.operating_margin_pct for r in msft],
        mode="lines+markers+text",
        text=[f"{r.operating_margin_pct:.1f}%" for r in msft],
        textposition="top center",
        line=dict(color="#0078D4", width=3), marker=dict(size=10),
    ))
    fig.add_trace(go.Scatter(
        name="Alphabet", x=[r.fiscal_year for r in googl],
        y=[r.operating_margin_pct for r in googl],
        mode="lines+markers+text",
        text=[f"{r.operating_margin_pct:.1f}%" for r in googl],
        textposition="bottom center",
        line=dict(color="#34A853", width=3), marker=dict(size=10),
    ))
    fig.update_layout(
        title="Operating Margin (%) — Computed in Code from EDGAR Numbers",
        xaxis_title="Fiscal Year", yaxis_title="Operating Margin %",
        legend=dict(orientation="h", y=1.1), height=380,
        margin=dict(t=60, b=40),
    )
    return fig


def build_income_chart(note):
    msft = [r for r in note.rows if r.company == "Microsoft"]
    googl = [r for r in note.rows if r.company == "Alphabet"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Microsoft", x=[r.fiscal_year for r in msft],
        y=[r.operating_income_usd_m for r in msft],
        mode="lines+markers",
        fill="tozeroy", fillcolor="rgba(0,120,212,0.1)",
        line=dict(color="#0078D4", width=2),
    ))
    fig.add_trace(go.Scatter(
        name="Alphabet", x=[r.fiscal_year for r in googl],
        y=[r.operating_income_usd_m for r in googl],
        mode="lines+markers",
        fill="tozeroy", fillcolor="rgba(52,168,83,0.1)",
        line=dict(color="#34A853", width=2),
    ))
    fig.update_layout(
        title="Operating Income (USD Millions)",
        xaxis_title="Fiscal Year", yaxis_title="USD Millions",
        legend=dict(orientation="h", y=1.1), height=380,
        margin=dict(t=60, b=40),
    )
    return fig


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

def load_dashboard():
    note = _get_baseline_data()
    n_files, n_passages = _passage_stats()

    rows = [[
        r.company, r.fiscal_year, r.period_end,
        f"${r.revenue_usd_m:,.1f}M",
        f"${r.operating_income_usd_m:,.1f}M",
        f"{r.operating_margin_pct:.1f}%",
        "✅" if r.revenue_fact_id else "❌",
    ] for r in note.rows]

    stats_md = (
        f"| Metric | Value |\n|--------|-------|\n"
        f"| Companies in scope | {len(COMPANIES)} (8 Tech + 7 Finance) |\n"
        f"| C0 baseline pair | Microsoft vs Alphabet |\n"
        f"| Fiscal Years | 2022 · 2023 · 2024 |\n"
        f"| EDGAR Verified | {note.verification_pct()}% |\n"
        f"| 10-K Documents Indexed | {n_files} |\n"
        f"| Text Passages Indexed | {n_passages if n_passages else '⚠️ Run ingestion first'} |\n"
        f"| Pipeline | C0 Fixed RAG (no agents) |\n"
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
    _, n = _passage_stats()
    if n > 0:
        import threading
        def _load():
            try:
                from analystdesk.retrieve import get_retriever
                get_retriever()
                print(f"✓ Retriever ready ({n} passages)")
            except Exception as e:
                print(f"⚠ Could not preload retriever: {e}")
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


def chat_fn(message, history, years_str):
    if not message.strip():
        yield history, "", [], None
        return

    # Parse years
    try:
        years = [int(y.strip()) for y in years_str.split(",") if y.strip()]
        if len(years) != 3:
            years = [2022, 2023, 2024]
    except Exception:
        years = [2022, 2023, 2024]

    history = list(history or [])
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": "⏳ Thinking..."})
    yield history, "", [], None

    n_files, n_passages = _passage_stats()
    if n_passages == 0:
        history[-1]["content"] = (
            "⚠️ No passages indexed yet. Please click **Run Ingestion** "
            "in the Dashboard tab first."
        )
        yield history, "", [], None
        return

    try:
        from analystdesk.retrieve import get_retriever
        from analystdesk.c0_pipeline import answer
        retriever = get_retriever()
        result = answer(message, retriever, years=years)
        ans = result["answer"]
        hits = result["passages"]

        # Generate chart if user asked for one
        chart = build_chat_chart(years) if _wants_chart(message) else None

        # Format citations
        cite_rows = [[
            h["passage_id"], h["company"],
            str(h["fiscal_year"]), h.get("item_label", ""),
            f"{h.get('score', 0):.3f}",
            h["text"][:200] + "…"
        ] for h in hits]

        history[-1]["content"] = ans
        yield history, "", cite_rows, chart

    except Exception as e:
        history[-1]["content"] = f"❌ Error: {e}"
        yield history, "", [], None


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
            refresh_btn = gr.Button("🔄 Refresh", size="sm")
            ingest_btn = gr.Button("⬇️ Run Ingestion (downloads 10-K filings)", size="sm", variant="primary")
        ingest_status = gr.Markdown()

        stats_md = gr.Markdown()

        with gr.Row():
            rev_chart = gr.Plot(label="Revenue")
            margin_chart = gr.Plot(label="Operating Margin")

        income_chart = gr.Plot(label="Operating Income")

        metrics_table = gr.Dataframe(
            headers=["Company", "FY", "Period End", "Revenue", "Op. Income", "Margin", "Verified"],
            label="All Metrics (EDGAR XBRL verified)",
            wrap=True,
        )

    # ── Tab 2: Chat ───────────────────────────────────────────────────────────
    with gr.Tab("💬 Research Chat"):
        gr.Markdown(
            "Ask research questions. Answers use **retrieved 10-K passages** + "
            "**EDGAR verified numbers**. Every claim is cited.\n\n"
            "Set `OPENROUTER_API_KEY` in your environment to enable LLM answers."
        )
        with gr.Row():
            years_input = gr.Textbox(
                value="2022, 2023, 2024", label="Fiscal Years", scale=1
            )

        chatbot = gr.Chatbot(
            height=420, label="Research Assistant",
            placeholder="Ask about Microsoft and Alphabet financials, risk factors, or MD&A...",
        )
        with gr.Row():
            chat_input = gr.Textbox(
                placeholder="e.g. What were the main risk factors for Microsoft in 2024?",
                label="Question", scale=5,
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)

        gr.Examples(
            examples=[
                ["Compare Microsoft and Alphabet operating margins over 2022–2024"],
                ["What were Microsoft's main risk factors in FY2024?"],
                ["How did Alphabet's revenue grow from 2022 to 2024?"],
                ["What risks did Alphabet highlight related to AI competition?"],
                ["Compare the MD&A outlook for both companies in 2023"],
            ],
            inputs=chat_input,
        )

        chat_chart = gr.Plot(label="Chart (auto-generated from EDGAR data)", visible=True)

        citations_table = gr.Dataframe(
            headers=["passage_id", "company", "year", "section", "score", "text preview"],
            label="Retrieved passages (citations)",
            wrap=True,
        )

    # ── Tab 3: Data Explorer ──────────────────────────────────────────────────
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

    # ── Tab 4: Raw JSON ───────────────────────────────────────────────────────
    with gr.Tab("🗂️ Raw Data"):
        gr.Markdown("Full `ResearchNote` JSON from the C0 baseline pipeline.")
        raw_btn = gr.Button("Load Raw JSON")
        raw_json = gr.Code(language="json", label="ResearchNote JSON")

    # ── event handlers ────────────────────────────────────────────────────────

    def refresh_dashboard():
        rev, margin, income, rows, stats = load_dashboard()
        return rev, margin, income, rows, stats

    def load_raw():
        note = _get_baseline_data()
        return note.to_json()

    demo.load(
        fn=refresh_dashboard,
        outputs=[rev_chart, margin_chart, income_chart, metrics_table, stats_md],
    )
    # Preload retriever in background so chat works without manual ingestion
    _try_preload_retriever()
    refresh_btn.click(
        fn=refresh_dashboard,
        outputs=[rev_chart, margin_chart, income_chart, metrics_table, stats_md],
    )
    ingest_btn.click(fn=run_ingestion, outputs=ingest_status)

    send_btn.click(
        fn=chat_fn,
        inputs=[chat_input, chatbot, years_input],
        outputs=[chatbot, chat_input, citations_table, chat_chart],
    )
    chat_input.submit(
        fn=chat_fn,
        inputs=[chat_input, chatbot, years_input],
        outputs=[chatbot, chat_input, citations_table, chat_chart],
    )

    search_btn.click(
        fn=search_passages,
        inputs=[search_query, company_dd, year_dd],
        outputs=search_results,
    )
    raw_btn.click(fn=load_raw, outputs=raw_json)


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7861,
        theme=gr.themes.Soft(),
    )
