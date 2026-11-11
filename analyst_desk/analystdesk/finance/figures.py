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

comparability_notes() states, in code, what keeps the figures from being
like-for-like (different fiscal year-ends, 53-week years, mixed margin
bases); the writer node adds them to every note they apply to.

Arithmetic rules (docs_notfor_submission/product_spec.md): every ratio is computed from the
raw reported dollars and rounded only for display, half away from zero
(20.125% -> 20.13%). A margin needs positive revenue. A growth rate needs a
positive earlier amount: from a loss (-20 -> -10) there is no meaningful
growth percentage, so none is offered. A margin change from zero income is
a real change (0.00% -> 5.00% is +5.00 pp) and is kept.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from analystdesk.finance.edgar import compatible_annual_facts
from analystdesk.finance.edgar import get_financials
from analystdesk.research.scope import COMPANIES

_BY_TICKER = {c.ticker: c for c in COMPANIES}
# {MSFT_2024_margin}; [MSFT_2024_margin] too, which the writer sometimes types in tables
PLACEHOLDER = re.compile(r"[{\[]([A-Z]{1,5}_\d{4}_[a-z_]+)[}\]]")


def half_up(x: float, places: int = 2) -> Decimal:
    """Round for display, halves away from zero: 20.125 -> 20.13 (Python's round() gives 20.12)."""
    return Decimal(repr(x)).quantize(Decimal(1).scaleb(-places), ROUND_HALF_UP)


def money(val: float) -> str:
    """Raw USD -> '$245,122.0M'; a loss keeps its sign in front: '-$1,234.5M'."""
    m = half_up(val / 1e6, 1)
    return f"{'-' if m < 0 else ''}${abs(m):,}M"


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
                    "text": f"{money(rev['val'])} [fact: {rev['fact_id']}]",
                    "label": f"{c.name} FY{y} {'net ' if c.margin_basis == 'pretax' else ''}revenue"}
                figures[f"{t}_{y}_period_end"] = {"text": rev["end"],
                                                  "label": f"{c.name} FY{y} period end"}
            if inc:
                figures[f"{t}_{y}_{income_key}"] = {
                    "text": f"{money(inc['val'])} [fact: {inc['fact_id']}]",
                    "label": f"{c.name} FY{y} {income_key.replace('_', ' ')}"}
            if compatible_annual_facts(rev, inc) and rev["val"] > 0:
                figures[f"{t}_{y}_margin"] = {
                    "text": f"{half_up(inc['val'] / rev['val'] * 100)}% [calc: {inc['fact_id']} / {rev['fact_id']}]",
                    "label": f"{c.name} FY{y} {c.margin_basis} margin"}
            prior = get_financials(c.cik, y - 1) if (y - 1) in years else None
            if prior and rev and prior["revenue"] and prior["revenue"]["val"] > 0:
                pr = prior["revenue"]
                figures[f"{t}_{y}_revenue_growth"] = {
                    "text": f"{half_up((rev['val'] / pr['val'] - 1) * 100)}% [growth: {rev['fact_id']} / {pr['fact_id']}]",
                    "label": f"{c.name} FY{y} revenue growth vs FY{y - 1}"}
                pi = prior[income_key]
                if inc and pi and pi["val"] > 0:
                    figures[f"{t}_{y}_income_growth"] = {
                        "text": f"{half_up((inc['val'] / pi['val'] - 1) * 100)}% [growth: {inc['fact_id']} / {pi['fact_id']}]",
                        "label": f"{c.name} FY{y} {income_key.replace('_', ' ')} growth vs FY{y - 1}"}
                if (compatible_annual_facts(rev, inc)
                        and compatible_annual_facts(pr, pi) and rev["val"] > 0):
                    change = half_up((inc["val"] / rev["val"] - pi["val"] / pr["val"]) * 100)
                    figures[f"{t}_{y}_margin_change"] = {
                        "text": f"{'+' if change >= 0 else ''}{change} pp [diff: {inc['fact_id']} / {rev['fact_id']} - "
                                f"{pi['fact_id']} / {pr['fact_id']}]",
                        "label": f"{c.name} FY{y} margin change vs FY{y - 1} (percentage points)"}
    return figures


def _month_day(end: str) -> str:
    return date.fromisoformat(end).strftime("%d %B").lstrip("0")


def comparability_notes(companies: list[str], years: list[int]) -> list[str]:
    """What makes the figures in a note not like-for-like, stated by code.

    * Fiscal years ending on different dates (Microsoft: 30 June, Alphabet: 31 December).
    * A 53-week fiscal year (Apple FY2023), against 52-week years either side.
    * Margins on different bases: banks on pre-tax margin, the others on operating margin.
    """
    notes = []
    ends = {}
    for t in companies:
        c = _BY_TICKER.get(t)
        if c is None:
            continue
        for y in sorted(years):
            rev = get_financials(c.cik, y)["revenue"]
            if not rev:
                continue
            ends.setdefault(t, rev["end"])
            if rev.get("start") and (date.fromisoformat(rev["end"]) - date.fromisoformat(rev["start"])).days + 1 >= 370:
                notes.append(f"{c.name}'s FY{y} had 53 weeks ({rev['start']} to {rev['end']}), one more than a "
                             f"usual year, so growth involving FY{y} is not fully like-for-like.")
    if len({_month_day(e) for e in ends.values()}) > 1:
        notes.insert(0, "Fiscal years end on different dates: " + "; ".join(
            f"{_BY_TICKER[t].name} on {_month_day(e)}" for t, e in ends.items())
            + ". Each figure is for the company's own fiscal year.")
    bases = {_BY_TICKER[t].margin_basis for t in ends}
    if len(bases) > 1:
        banks = ", ".join(_BY_TICKER[t].name for t in ends if _BY_TICKER[t].margin_basis == "pretax")
        notes.append(f"Banks ({banks}) are shown on pre-tax margin and the other companies on operating margin. "
                     "The two are not comparable, so they are not ranked against each other.")
    return notes


def figures_table(figures: dict[str, dict]) -> str:
    """The list shown to the writer: placeholder, meaning, value."""
    return "\n".join(f"{{{k}}}  {v['label']}: {v['text'].split(' [')[0]}" for k, v in figures.items())


def render(body: str, figures: dict[str, dict]) -> tuple[str, list[str]]:
    """Replace placeholders with values + source tags; report unknown ones."""
    unknown = sorted({k for k in PLACEHOLDER.findall(body) if k not in figures})
    rendered = PLACEHOLDER.sub(lambda m: figures[m.group(1)]["text"] if m.group(1) in figures
                               else m.group(0), body)
    return rendered, [f"Unknown placeholder {{{k}}}." for k in unknown]
