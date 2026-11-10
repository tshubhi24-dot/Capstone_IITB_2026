"""Build EDGAR charts from the company, metric, and periods in a C0 question."""

from __future__ import annotations

import re

import plotly.graph_objects as go

from .edgar import compatible_annual_facts, get_financials, get_quarterly_financials
from .query import find_companies
from .scope import COMPANIES

_METRIC_PATTERNS = (
    ("operating_margin", re.compile(r"\boperating\s+margins?\b", re.I)),
    ("pretax_margin", re.compile(r"\b(?:pre[- ]?tax|pretax)\s+margins?\b", re.I)),
    ("operating_income", re.compile(r"\boperating\s+(?:income|profit)\b", re.I)),
    ("pretax_income", re.compile(r"\b(?:pre[- ]?tax|pretax)\s+income\b", re.I)),
    ("margin", re.compile(r"\bmargins?\b", re.I)),
    ("revenue", re.compile(r"\b(?:net\s+)?revenues?\b|\bsales\b", re.I)),
)
_QUARTERLY_PATTERN = re.compile(r"\b(?:quarterly|by\s+quarter|each\s+quarter)\b", re.I)
_PALETTE = (
    "#0078D4", "#34A853", "#F4B400", "#EA4335", "#9334E6",
    "#00ACC1", "#FF7043", "#5C6BC0", "#7CB342", "#8D6E63",
    "#EC407A", "#78909C", "#26A69A", "#AB47BC", "#9E9D24",
)


def _metric_from_question(question: str) -> str | None:
    matches = [
        (match.start(), match.end(), metric)
        for metric, pattern in _METRIC_PATTERNS
        if (match := pattern.search(question))
    ]
    if not matches:
        return None
    specific_spans = [
        (start, end)
        for start, end, metric in matches
        if metric in ("operating_margin", "pretax_margin")
    ]
    matches = [
        item for item in matches
        if item[2] != "margin"
        or not any(start <= item[0] and item[1] <= end for start, end in specific_spans)
    ]
    matches.sort()
    metrics = {metric for _, _, metric in matches}
    return matches[0][2] if len(metrics) == 1 else None


def _financial_value(financials: dict, metric: str, margin_basis: str, *, annual: bool = True) -> float | None:
    revenue = financials.get("revenue")
    if metric == "revenue":
        value = revenue
    elif metric == "operating_income":
        value = financials.get("operating_income")
    elif metric == "pretax_income":
        value = financials.get("pretax_income")
    else:
        income_key = "pretax_income" if metric == "pretax_margin" or (
            metric == "margin" and margin_basis == "pretax"
        ) else "operating_income"
        income = financials.get(income_key)
        if not revenue or not income or not revenue["val"]:
            return None
        if annual and not compatible_annual_facts(revenue, income):
            return None
        return round(income["val"] / revenue["val"] * 100, 2)

    return round(value["val"] / 1_000_000, 1) if value else None


def build_chat_chart(
    question: str, years: list[int]
) -> tuple[go.Figure | None, str | None]:
    """Return a chart and optional explanation when requested data is unavailable."""
    companies_by_ticker = {company.ticker: company for company in COMPANIES}
    companies = [
        companies_by_ticker[ticker]
        for ticker in find_companies(question)
        if ticker in companies_by_ticker
    ]
    metric = _metric_from_question(question)
    if not companies or metric is None:
        return None, None

    if metric == "margin":
        bases = {company.margin_basis for company in companies}
        if len(bases) > 1:
            return None, "A comparable chart is unavailable because the companies use different margin definitions."

    quarterly = bool(_QUARTERLY_PATTERN.search(question))
    quarterly_pretax = metric in ("pretax_income", "pretax_margin") or (
        metric == "margin" and companies[0].margin_basis == "pretax"
    )
    if quarterly and quarterly_pretax:
        return None, "Quarterly pre-tax data is not available from the current EDGAR chart source."
    if quarterly:
        from .source_review import load_register
        if load_register() is not None:
            return None, "Quarterly charts are unavailable under annual source-review enforcement."
    if metric == "operating_margin" and any(
        company.margin_basis != "operating" for company in companies
    ):
        return None, "A comparable chart is unavailable because not all companies report operating margin."
    if metric == "pretax_margin" and any(
        company.margin_basis != "pretax" for company in companies
    ):
        return None, "A comparable chart is unavailable because not all companies use pre-tax margin."

    if metric in ("revenue",):
        metric_label = "Revenue"
    elif metric == "operating_income":
        metric_label = "Operating Income"
    elif metric == "pretax_income":
        metric_label = "Pre-tax Income"
    elif metric == "operating_margin":
        metric_label = "Operating Margin"
    elif metric == "pretax_margin":
        metric_label = "Pre-tax Margin"
    else:
        metric_label = "Pre-tax Margin" if companies[0].margin_basis == "pretax" else "Operating Margin"

    period_labels: list[str] = []
    values_by_company: dict[str, list[float | None]] = {
        company.ticker: [] for company in companies
    }

    for year in years:
        if quarterly:
            quarter_data = {
                company.ticker: get_quarterly_financials(company.cik, year)
                for company in companies
            }
            quarter_order = sorted(
                {
                    quarter["quarter"]
                    for quarters in quarter_data.values()
                    for quarter in quarters
                }
            )
            for quarter in quarter_order:
                period_labels.append(f"FY{year} {quarter}")
                for company in companies:
                    record = next(
                        (item for item in quarter_data[company.ticker]
                         if item["quarter"] == quarter),
                        {},
                    )
                    values_by_company[company.ticker].append(
                        _financial_value(record, metric, company.margin_basis, annual=False)
                    )
        else:
            period_labels.append(f"FY{year}")
            for company in companies:
                financials = get_financials(company.cik, year)
                values_by_company[company.ticker].append(
                    _financial_value(financials, metric, company.margin_basis)
                )

    if not period_labels or not any(
        value is not None
        for company_values in values_by_company.values()
        for value in company_values
    ):
        return None, (f"No EDGAR data was found for the requested {metric_label.lower()} period(s); "
                      "facts may be unavailable, ineligible, or from incompatible annual periods or filings.")

    figure = go.Figure()
    for index, company in enumerate(companies):
        figure.add_trace(go.Bar(
            name=company.name,
            x=period_labels,
            y=values_by_company[company.ticker],
            marker_color=_PALETTE[index % len(_PALETTE)],
        ))

    unit = "%" if "margin" in metric else "USD millions"
    period_type = "Quarterly" if quarterly else "Annual"
    figure.update_layout(
        title=f"{period_type} {metric_label} — EDGAR XBRL",
        barmode="group",
        xaxis_title="Fiscal Period",
        yaxis_title=unit,
        legend=dict(orientation="h", y=1.1),
        height=420,
        margin=dict(t=70, b=40),
    )
    missing = any(value is None for values in values_by_company.values() for value in values)
    notice = ("Some requested values are unavailable, ineligible, or from incompatible annual periods or filings."
              if missing else None)
    return figure, notice
