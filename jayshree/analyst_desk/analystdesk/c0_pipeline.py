"""C0 fixed RAG pipeline — retrieval + EDGAR facts + LLM with fixed prompt.

This is the complete C0 experiment configuration. It is a fixed workflow:
  1. Retrieve top-k passages: hybrid index + reranker, decomposed into one
     filtered search per company/year named (code decides, not an agent)
  2. Fetch XBRL numbers from EDGAR for the companies mentioned
  3. Fill a fixed prompt template with the retrieved content + numbers
  4. Call the LLM once with that prompt (no tool loop, no planning)
  5. Return the answer with passage citations and fact_ids

C0 uses the model configured for the `c0` role in the versioned LLM config
via OpenRouter's OpenAI-compatible API. The model is fixed in config — not chosen by an agent.
"""

from __future__ import annotations

import os
from pathlib import Path

from .edgar import get_financials, get_quarterly_financials
from .llm_config import LLM_CONFIG
from .query import decompose, find_companies, search_decomposed
from .scope import COMPANIES, C0_COMPANIES

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def _format_passages(hits: list[dict]) -> str:
    parts = []
    for h in hits:
        pid = h["passage_id"]
        company = h["company"]
        year = h["fiscal_year"]
        item = h.get("item_label", h["item"])
        score = h.get("score", 0)
        parts.append(
            f"[{pid}] {company} FY{year} — {item} (relevance: {score:.2f})\n"
            f"{h['text'][:800]}"
        )
    return "\n\n---\n\n".join(parts) if parts else "(no passages retrieved)"


def _format_numbers(companies_in_query: list[str], years: list[int]) -> str:
    lines = []
    company_map = {c.ticker: c for c in COMPANIES}
    for ticker in companies_in_query:
        company = company_map.get(ticker)
        if not company:
            continue
        for year in years:
            # Annual totals
            data = get_financials(company.cik, year)
            rev = data["revenue"]
            op = data["operating_income"]
            if rev:
                rev_m = round(rev["val"] / 1_000_000, 1)
                lines.append(
                    f"{ticker} FY{year} Annual Revenue: ${rev_m:,.1f}M "
                    f"[fact_id: {rev['fact_id']}]"
                )
            if op:
                op_m = round(op["val"] / 1_000_000, 1)
                margin = round(op_m / (rev["val"] / 1_000_000) * 100, 2) if rev else None
                lines.append(
                    f"{ticker} FY{year} Annual Operating Income: ${op_m:,.1f}M"
                    + (f" → Margin: {margin}%" if margin else "")
                    + f" [fact_id: {op['fact_id']}]"
                )
            pretax = data["pretax_income"]
            if company.margin_basis == "pretax" and pretax:
                pt_m = round(pretax["val"] / 1_000_000, 1)
                pt_margin = round(pt_m / (rev["val"] / 1_000_000) * 100, 2) if rev else None
                lines.append(
                    f"{ticker} FY{year} Annual Pre-tax Income: ${pt_m:,.1f}M"
                    + (f" → Pre-tax Margin: {pt_margin}% (banks report no operating income;"
                       f" do not compare with operating margins)" if pt_margin else "")
                    + f" [fact_id: {pretax['fact_id']}]"
                )
            # Quarterly breakdown
            qtrs = get_quarterly_financials(company.cik, year)
            for q in qtrs:
                qrev = q["revenue"]
                qop  = q["operating_income"]
                qrev_str = f"Revenue ${round(qrev['val']/1_000_000,1):,.1f}M [fact_id: {qrev['fact_id']}]" if qrev else "Revenue N/A"
                if qop:
                    qop_m = round(qop["val"] / 1_000_000, 1)
                    qmargin = round(qop_m / (qrev["val"] / 1_000_000) * 100, 2) if qrev else None
                    qop_str = (f"Op.Income ${qop_m:,.1f}M"
                               + (f" ({qmargin}% margin)" if qmargin else "")
                               + f" [fact_id: {qop['fact_id']}]")
                else:
                    qop_str = "Op.Income N/A"
                lines.append(f"  {ticker} FY{year} {q['quarter']} (ends {q['end']}): {qrev_str} | {qop_str}")
    return "\n".join(lines) if lines else "(no EDGAR numbers fetched)"


def answer(
    question: str,
    retriever,
    years: list[int] | None = None,
    top_k: int = 5,
) -> dict:
    """Run the C0 fixed pipeline. Returns answer dict with citations."""
    years = years or [2022, 2023, 2024]

    # Step 1 — fixed retrieval (no agent decides what to retrieve). Same
    # decomposed retrieval as C1/C2 will use, so E1 compares orchestration,
    # not retrieval quality.
    hits = search_decomposed(retriever, question, top_k=top_k)

    # Step 2 — fixed EDGAR fetch for the companies named in the question
    # (the C0 pair when none is named)
    tickers = find_companies(question) or [c.ticker for c in C0_COMPANIES]
    numbers_text = _format_numbers(tickers, years)

    # Step 3 — fill fixed prompt template
    user_content = LLM_CONFIG.format_prompt(
        "c0_answer",
        passages=_format_passages(hits),
        numbers=numbers_text,
        question=question,
    )

    # Step 4 — single LLM call, no tool loop
    answer_text = "(LLM not configured — set OPENROUTER_API_KEY)"
    tokens = 0
    if OPENROUTER_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY,
            )
            response = client.chat.completions.create(
                model=LLM_CONFIG.model("c0"),
                messages=[
                    {"role": "system", "content": LLM_CONFIG.prompt("c0_system")},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=800,
                temperature=0.1,
            )
            answer_text = response.choices[0].message.content or "(empty response)"
            tokens = getattr(response.usage, "total_tokens", 0) or 0
        except Exception as e:
            answer_text = f"(LLM error: {e})"

    return {
        "answer": answer_text,
        "passages": hits,
        "years": years,
        "model": LLM_CONFIG.model("c0"),
        "pipeline": "C0-fixed-RAG",
        "tokens": tokens,
        # how the answer was built, for display: the fixed steps C0 took
        "steps": {
            "searches": [{"query": sq.text, "company": sq.company, "year": sq.year}
                         for sq in decompose(question)],
            "edgar_companies": tickers,
            "edgar_numbers": numbers_text,
        },
    }
