"""edgar MCP server — 10-K filings list and XBRL facts (read-only, cached).

Tools:
    list_filings     the company's 10-K filings: fiscal year, accession, dates
    get_financials   revenue + operating/pre-tax income for one fiscal year,
                     each with its fact_id (as originally reported)
    get_fact         look up one fact_id and return its value and source

All data comes from the local EDGAR cache (data/edgar_cache, committed), so
tool calls never hit SEC: no rate-limit risk and reproducible results.

No ratios are computed here. The quant agent computes them in the sandbox
from these facts, and the critic re-checks each cited number with get_fact.

Run standalone (stdio):  python -m analystdesk.servers.edgar_server
"""

from __future__ import annotations

import json
import re
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .. import edgar, source_review
from ..scope import COMPANIES
from .common import COVERED_YEARS, READ_ONLY, ToolResult, fail, serve, structured_errors

mcp = FastMCP(
    "edgar",
    instructions=(
        "Reported financial facts (SEC XBRL) for 15 companies, FY2022-2024, in USD. "
        "Every value has a fact_id that must be cited next to the number. "
        "Do not do arithmetic yourself: compute ratios with the python-sandbox."
    ),
)

_BY_TICKER = {c.ticker: c for c in COMPANIES}
_FACT_ID = re.compile(r"^(?P<concept>[A-Za-z]+)/(?P<year>\d{4})/(?P<accn>\d{10}-\d{2}-\d{6})$")


class Filing(BaseModel):
    fiscal_year: int = Field(description="Year the reporting period ends")
    period_end: str
    accession: str
    filed: str
    form: str


class FactVersion(BaseModel):
    value_usd: int
    period_start: str | None = None
    period_end: str
    accession: str
    filed: str | None = None
    form: str
    fact_id: str


class Fact(BaseModel):
    concept: str = Field(description="XBRL concept, e.g. OperatingIncomeLoss")
    value_usd: int = Field(description="Exact reported value in US dollars")
    period_start: str | None = None
    period_end: str
    accession: str = Field(description="SEC accession number of the filing that reported it")
    filed: str
    fact_id: str = Field(description="Cite this next to the number: concept/fiscal_year/accession")
    eligibility: str = Field("unverified", description="Unverified or eligible according to the configured review register")
    source_review: dict | None = Field(None, description="Reviewer, evidence and decision for the selected fact")
    versions: list[FactVersion] = Field(default_factory=list, description="Cached annual 10-K and 10-K/A presentations")
    restated_value_usd: int | None = Field(
        None, description="A different value a later 10-K reports for this year, if any (not used in "
                          "notes). It may be a restatement, recast or reclassification; the data does "
                          "not say which.")


class FilingsResult(ToolResult):
    ticker: str | None = None
    company: str | None = None
    filings: list[Filing] = []


class FinancialsResult(ToolResult):
    ticker: str | None = None
    company: str | None = None
    fiscal_year: int | None = None
    margin_basis: str | None = Field(
        None, description="'operating' (operating income / revenue) or 'pretax' (banks: "
                          "pre-tax income / net revenue). Never compare across bases.")
    revenue: Fact | None = None
    operating_income: Fact | None = None
    pretax_income: Fact | None = None
    warnings: list[str] = []


class FactResult(ToolResult):
    ticker: str | None = None
    fact: Fact | None = None


def _ticker_or_error(ticker: str, result_cls):
    t = ticker.strip().upper()
    if t not in _BY_TICKER:
        return None, fail(result_cls, "NOT_IN_COVERAGE",
                          f"{ticker} is not covered. Covered: {', '.join(sorted(_BY_TICKER))}")
    return _BY_TICKER[t], None


def _concept_of(fact_id: str) -> str:
    return fact_id.split("/", 1)[0]


def _fact(raw: dict) -> Fact:
    return Fact(
        concept=_concept_of(raw["fact_id"]), value_usd=raw["val"],
        period_start=raw.get("start"), period_end=raw["end"],
        accession=raw["accn"], filed=raw["filed"], fact_id=raw["fact_id"],
        restated_value_usd=(raw.get("restated") or {}).get("val"),
        eligibility=raw.get("eligibility", "unverified"),
        source_review=raw.get("source_review"),
        versions=[FactVersion(value_usd=v["val"], period_start=v.get("start"), period_end=v["end"],
                              accession=v["accn"], filed=v.get("filed"), form=v["form"],
                              fact_id=v["fact_id"]) for v in raw.get("versions", [])],
    )


@mcp.tool(annotations=READ_ONLY)
@structured_errors(FilingsResult)
def list_filings(
    ticker: Annotated[str, Field(description="Ticker, e.g. MSFT")],
) -> FilingsResult:
    """List the company's 10-K filings in the local cache, newest first."""
    company, err = _ticker_or_error(ticker, FilingsResult)
    if err:
        return err
    path = edgar.CACHE_DIR / f"submissions_{edgar._pad_cik(company.cik)}.json"
    if not path.exists():
        return fail(FilingsResult, "NOT_FOUND", f"No filing list cached for {company.ticker}")
    recent = json.loads(path.read_text(encoding="utf-8"))["filings"]["recent"]
    filings = [
        Filing(fiscal_year=int(rd[:4]), period_end=rd, accession=a, filed=fd, form=f)
        for f, rd, a, fd in zip(recent["form"], recent["reportDate"],
                                recent["accessionNumber"], recent["filingDate"])
        if f in ("10-K", "10-K/A") and rd
    ]
    return FilingsResult(ticker=company.ticker, company=company.name, filings=filings)


@mcp.tool(annotations=READ_ONLY)
@structured_errors(FinancialsResult)
def get_financials(
    ticker: Annotated[str, Field(description="Ticker, e.g. MSFT")],
    fiscal_year: Annotated[int, Field(description="Fiscal year (year the period ends), 2022-2024")],
) -> FinancialsResult:
    """Revenue, operating income and pre-tax income for one company and fiscal year.

    By default the earliest matching filing is unverified. If a reviewed
    source register is configured, only eligible annual facts and versions
    are returned. The register does not itself verify the review evidence.
    """
    company, err = _ticker_or_error(ticker, FinancialsResult)
    if err:
        return err
    if fiscal_year not in COVERED_YEARS:
        return fail(FinancialsResult, "NOT_IN_COVERAGE",
                    f"FY{fiscal_year} is not covered. Covered: {COVERED_YEARS}")

    data = edgar.get_financials(company.cik, fiscal_year)
    facts = {k: _fact(v) if v else None for k, v in data.items()}
    if facts["revenue"] is None:
        return fail(FinancialsResult, "NOT_FOUND",
                    f"No available revenue fact for {company.ticker} FY{fiscal_year}; "
                    "the source may be missing or not eligible under the source policy")
    warnings = [
        f"{name} selected value {f.value_usd:,}; a later filing reports {f.restated_value_usd:,} for the same "
        f"year (reason not established: do not call it a restatement)"
        for name, f in facts.items() if f and f.restated_value_usd is not None
    ]
    if any(f and f.eligibility != "eligible" for f in facts.values()):
        warnings.append("Source eligibility and non-reliance status have not been independently verified.")
    else:
        warnings.append("Eligible facts match the configured register; reviewer identity and evidence are not independently verified.")
    headline = "pretax_income" if company.margin_basis == "pretax" else "operating_income"
    if facts[headline] is None:
        warnings.append(f"{headline.replace('_', ' ')} is unavailable or not eligible under the source policy.")
    return FinancialsResult(
        ticker=company.ticker, company=company.name, fiscal_year=fiscal_year,
        margin_basis=company.margin_basis, warnings=warnings, **facts,
    )


@mcp.tool(annotations=READ_ONLY)
@structured_errors(FactResult)
def get_fact(
    fact_id: Annotated[str, Field(description="concept/fiscal_year/accession, e.g. "
                                  "OperatingIncomeLoss/2024/0000950170-24-087843")],
) -> FactResult:
    """Look up the exact value that a fact_id refers to.

    Matches the concept, the fiscal year and the very filing (accession) the
    fact_id names — used to verify every number cited in a note.
    """
    m = _FACT_ID.match(fact_id.strip())
    if not m:
        return fail(FactResult, "BAD_INPUT",
                    "fact_id must look like Concept/YYYY/0000000000-00-000000")
    concept, year, accn = m["concept"], m["year"], m["accn"]
    register = source_review.load_register()

    # The accession prefix identifies the filing agent, not the company, so
    # search every covered company for this concept/year/filing.
    for company in COMPANIES:
        facts = edgar.fetch_company_facts(company.cik)
        entries = facts.get("facts", {}).get("us-gaap", {}).get(concept, {}).get("units", {}).get("USD", [])
        for e in entries:
            if (e.get("accn") == accn and e.get("end", "")[:4] == year
                    and e.get("fp") == "FY" and e.get("form") in ("10-K", "10-K/A")
                    and 350 <= edgar._duration_days(e) <= 380):
                eligibility = source_review.status(register, company.ticker, int(year), concept, e)
                if register is not None and eligibility != "eligible":
                    return fail(FactResult, "NOT_FOUND", f"Fact {fact_id} is not an eligible reviewed source.")
                decision = source_review.decision_for(register, company.ticker, int(year), concept, e)
                raw = {**e, "fact_id": f"{concept}/{year}/{accn}", "eligibility": eligibility,
                       "source_review": decision.model_dump(mode="json") if decision else None}
                return FactResult(ticker=company.ticker, fact=_fact(raw))
    return fail(FactResult, "NOT_FOUND", f"No full-year fact matches {fact_id}")


if __name__ == "__main__":
    serve(mcp)
