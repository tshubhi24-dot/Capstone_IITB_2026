"""C0 baseline pipeline — fixed workflow, no agent decisions, no LLM calls.

This is Experiment Configuration C0. It is the baseline every other experiment
(C1 single agent, C2 team) is compared against in E1.

The pipeline is intentionally simple and deterministic:
  1. Take a validated ResearchRequest (from scope.py)
  2. Fetch XBRL facts from EDGAR for each company + year (edgar.py)
  3. Calculate operating margin in Python — never inside a language model
  4. Build and return a ResearchNote with every number linked to a fact_id

There are no LLM calls here. That is the point. C0 shows what a fixed, rule-based
system can do before we add agent intelligence. The gap between C0 and C1/C2 is
the measured benefit of the agentic approach.
"""

from __future__ import annotations

from .edgar import compatible_annual_facts, get_financials
from .note import MetricRow, ResearchNote
from .agent.figures import half_up
from .scope import ResearchRequest


def _to_millions(val: int | None) -> float | None:
    """Convert raw EDGAR USD to millions, rounded to 1 decimal.

    EDGAR stores values in full USD (e.g. 245122000000 for $245.1B).
    We present numbers in millions for readability.
    """
    if val is None:
        return None
    return round(val / 1_000_000, 1)


def _operating_margin(revenue: float | None, income: float | None) -> float | None:
    """Margin = income / revenue x 100, from the raw reported dollars (never rounded inputs).

    Computed in Python code, never by an LLM. Rounded only for display, halves
    away from zero. None if either input is missing or revenue is not positive.
    """
    if revenue is None or income is None or revenue <= 0:
        return None
    return float(half_up(income / revenue * 100))


def run_baseline(request: ResearchRequest) -> ResearchNote:
    """Run the C0 fixed pipeline and return a draft ResearchNote.

    Iterates over every (company, fiscal_year) pair in the request.
    For each pair, fetches revenue and operating income from EDGAR,
    calculates the margin, and adds a MetricRow with source fact_ids.

    Missing data (e.g. a year not yet filed) is recorded as a warning,
    not an error — the note is still returned with whatever was found.
    """
    rows: list[MetricRow] = []
    warnings: list[str] = []

    for company in request.companies:
        for year in request.fiscal_years:
            data = get_financials(company.cik, year)
            rev = data["revenue"]
            op = data["operating_income"]
            pretax = data.get("pretax_income")
            if any(fact and fact.get("eligibility", "unverified") == "unverified"
                   for fact in (rev, op, pretax)):
                warnings.append(f"{company.name} FY{year}: source eligibility and non-reliance are unverified.")

            rev_m = _to_millions(rev["val"] if rev else None)
            op_m = _to_millions(op["val"] if op else None)
            pretax_m = _to_millions(pretax["val"] if pretax else None)
            margin = (_operating_margin(rev["val"], op["val"])
                      if compatible_annual_facts(rev, op) else None)
            # Same ratio, different income line: pre-tax income / net revenue
            pretax_margin = (_operating_margin(rev["val"], pretax["val"])
                             if compatible_annual_facts(rev, pretax) else None)
            headline_income = pretax if company.margin_basis == "pretax" else op
            if rev and headline_income and not compatible_annual_facts(rev, headline_income):
                warnings.append(f"{company.name} FY{year}: margin unavailable because revenue and income "
                                "do not have the same annual period and filing.")

            if rev is None:
                warnings.append(
                    f"{company.name} FY{year}: revenue missing or not eligible under the source policy"
                )
            for label, fact in (("revenue", rev), ("operating income", op), ("pre-tax income", pretax)):
                if fact and fact.get("restated"):
                    later = fact["restated"]
                    warnings.append(
                        f"{company.name} FY{year}: {label} selected value "
                        f"{_to_millions(fact['val']):,.1f}M; a later 10-K ({later['accn']}) reports "
                        f"{_to_millions(later['val']):,.1f}M for the same year (reason not "
                        f"established); the note uses the selected figure"
                    )
            # Only the headline income line is required for this company
            if company.margin_basis == "pretax" and pretax is None:
                warnings.append(
                    f"{company.name} FY{year}: pre-tax income missing or not eligible under the source policy"
                )
            if company.margin_basis == "operating" and op is None:
                warnings.append(
                    f"{company.name} FY{year}: operating income missing or not eligible under the source policy"
                )

            rows.append(MetricRow(
                company=company.name,
                fiscal_year=year,
                revenue_usd_m=rev_m,
                operating_income_usd_m=op_m,
                operating_margin_pct=margin,
                revenue_fact_id=rev["fact_id"] if rev else None,
                operating_income_fact_id=op["fact_id"] if op else None,
                period_end=rev["end"] if rev else (op["end"] if op else None),
                margin_basis=company.margin_basis,
                pretax_income_usd_m=pretax_m,
                pretax_margin_pct=pretax_margin,
                pretax_income_fact_id=pretax["fact_id"] if pretax else None,
            ))

    years = request.fiscal_years
    title = (
        f"{' vs '.join(c.name for c in request.companies)}: Margins "
        f"FY{years[0]}–FY{years[-1]} (C0 Baseline)"
    )
    return ResearchNote(
        title=title,
        status="draft",
        rows=rows,
        summary=(
            "C0 fixed-workflow baseline. All numbers sourced directly from SEC EDGAR XBRL. "
            "Margins computed in code. No LLM calls. No retrieval. "
            "Use this as the experiment baseline when comparing against C1 and C2."
        ),
        warnings=warnings,
    )
