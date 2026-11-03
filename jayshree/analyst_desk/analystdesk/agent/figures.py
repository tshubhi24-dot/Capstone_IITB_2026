"""Key figures the writer may use — produced and rendered by code (rule 1).

The writer never types a reported figure. It writes a placeholder such as
{MSFT_2024_revenue} and code replaces it with the exact value and its
source tag. So the numbers in a note cannot be mistyped or invented: the
model chooses *which* figure to mention; code decides *what it says*.

For every company and fiscal year in the plan:
    {T_Y_revenue}            $245,122.0M [fact: ...]
    {T_Y_operating_income}   (operating-margin companies)
    {T_Y_pretax_income}      (banks)
    {T_Y_margin}             44.64% [calc: income fact / revenue fact]
    {T_Y_period_end}         2024-06-30 (fiscal years differ by company)
    {T_Y_revenue_growth}     15.67% [growth: revenue Y / revenue Y-1]    (when Y-1 is in the plan)
    {T_Y_income_growth}      23.62% [growth: income Y / income Y-1]
    {T_Y_margin_change}      +2.87 pp [diff: margin Y - margin Y-1]
"""

from __future__ import annotations

import re

from ..edgar import get_financials
from ..scope import COMPANIES

_BY_TICKER = {c.ticker: c for c in COMPANIES}
# {MSFT_2024_margin}; [MSFT_2024_margin] too, which the writer sometimes types in tables
PLACEHOLDER = re.compile(r"[{\[]([A-Z]{1,5}_\d{4}_[a-z_]+)[}\]]")


def build_figures(companies: list[str], years: list[int]) -> dict[str, dict]:
    """Key -> {"text": rendered value with source tag, "label": description}."""
    figures: dict[str, dict] = {}
    for t in companies:
        c = _BY_TICKER.get(t)
        if c is None:
            continue
        for y in years:
            data = get_financials(c.cik, y)
            rev = data["revenue"]
            income_key = "pretax_income" if c.margin_basis == "pretax" else "operating_income"
            inc = data[income_key]
            if rev:
                figures[f"{t}_{y}_revenue"] = {
                    "text": f"${rev['val'] / 1e6:,.1f}M [fact: {rev['fact_id']}]",
                    "label": f"{c.name} FY{y} {'net ' if c.margin_basis == 'pretax' else ''}revenue"}
                figures[f"{t}_{y}_period_end"] = {"text": rev["end"],
                                                  "label": f"{c.name} FY{y} period end"}
            if inc:
                figures[f"{t}_{y}_{income_key}"] = {
                    "text": f"${inc['val'] / 1e6:,.1f}M [fact: {inc['fact_id']}]",
                    "label": f"{c.name} FY{y} {income_key.replace('_', ' ')}"}
            if rev and inc and rev["val"]:
                figures[f"{t}_{y}_margin"] = {
                    "text": f"{inc['val'] / rev['val'] * 100:.2f}% [calc: {inc['fact_id']} / {rev['fact_id']}]",
                    "label": f"{c.name} FY{y} {c.margin_basis} margin"}
            prior = get_financials(c.cik, y - 1) if (y - 1) in years else None
            if prior and rev and prior["revenue"] and prior["revenue"]["val"]:
                pr = prior["revenue"]
                figures[f"{t}_{y}_revenue_growth"] = {
                    "text": f"{(rev['val'] / pr['val'] - 1) * 100:.2f}% [growth: {rev['fact_id']} / {pr['fact_id']}]",
                    "label": f"{c.name} FY{y} revenue growth vs FY{y - 1}"}
                pi = prior[income_key]
                if inc and pi and pi["val"]:
                    figures[f"{t}_{y}_income_growth"] = {
                        "text": f"{(inc['val'] / pi['val'] - 1) * 100:.2f}% [growth: {inc['fact_id']} / {pi['fact_id']}]",
                        "label": f"{c.name} FY{y} {income_key.replace('_', ' ')} growth vs FY{y - 1}"}
                    change = (inc["val"] / rev["val"] - pi["val"] / pr["val"]) * 100
                    figures[f"{t}_{y}_margin_change"] = {
                        "text": f"{change:+.2f} pp [diff: {inc['fact_id']} / {rev['fact_id']} - "
                                f"{pi['fact_id']} / {pr['fact_id']}]",
                        "label": f"{c.name} FY{y} margin change vs FY{y - 1} (percentage points)"}
    return figures


def figures_table(figures: dict[str, dict]) -> str:
    """The list shown to the writer: placeholder, meaning, value."""
    return "\n".join(f"{{{k}}}  {v['label']}: {v['text'].split(' [')[0]}" for k, v in figures.items())


def render(body: str, figures: dict[str, dict]) -> tuple[str, list[str]]:
    """Replace placeholders with values + source tags; report unknown ones."""
    unknown = sorted({k for k in PLACEHOLDER.findall(body) if k not in figures})
    rendered = PLACEHOLDER.sub(lambda m: figures[m.group(1)]["text"] if m.group(1) in figures
                               else m.group(0), body)
    return rendered, [f"Unknown placeholder {{{k}}}." for k in unknown]
