"""Part 1: define and validate the supported research request.

Covers 15 companies across two sectors (Technology and Finance) over three
fiscal years. Scope validation happens once here; every later module consumes
the typed contract without re-validating.
"""

from dataclasses import asdict, dataclass
from typing import Tuple


class ScopeError(ValueError):
    """The requested comparison falls outside this baseline's scope."""


@dataclass(frozen=True)
class Company:
    name: str
    ticker: str
    cik: str
    sector: str
    # Headline margin. Banks don't report OperatingIncomeLoss in XBRL, so they
    # use pre-tax margin (pre-tax income / net revenue). Fixed per company so
    # the basis never switches between years; the two are never compared.
    margin_basis: str = "operating"


# ── Technology sector ────────────────────────────────────────────────────────
TECH = (
    Company("Microsoft",            "MSFT",  "0000789019", "Technology"),
    Company("Alphabet",             "GOOGL", "0001652044", "Technology"),
    Company("Apple",                "AAPL",  "0000320193", "Technology"),
    Company("Amazon",               "AMZN",  "0001018724", "Technology"),
    Company("Meta",                 "META",  "0001326801", "Technology"),
    Company("NVIDIA",               "NVDA",  "0001045810", "Technology"),
    Company("Advanced Micro Devices","AMD",  "0000002488", "Technology"),
    Company("Oracle",               "ORCL",  "0001341439", "Technology"),
)

# ── Finance sector ────────────────────────────────────────────────────────────
FINANCE = (
    Company("JPMorgan Chase",  "JPM", "0000019617", "Finance", "pretax"),
    Company("Goldman Sachs",   "GS",  "0000886982", "Finance", "pretax"),
    Company("Bank of America", "BAC", "0000070858", "Finance", "pretax"),
    Company("Visa",            "V",   "0001403161", "Finance"),
    Company("Morgan Stanley",  "MS",  "0000895421", "Finance", "pretax"),
    Company("Mastercard",      "MA",  "0001141391", "Finance"),
    Company("Wells Fargo",     "WFC", "0000072971", "Finance", "pretax"),
)

COMPANIES: Tuple[Company, ...] = TECH + FINANCE

SUPPORTED_METRICS = ("revenue", "operating_income", "operating_margin")

# C0 baseline is fixed to this pair (PDF example request)
C0_COMPANIES = (
    next(c for c in COMPANIES if c.ticker == "MSFT"),
    next(c for c in COMPANIES if c.ticker == "GOOGL"),
)


def resolve_company(value: str) -> Company:
    """Accept a company name or ticker (case-insensitive)."""
    if not isinstance(value, str):
        raise ScopeError("Company must be a name or ticker.")
    key = value.strip().casefold()
    for company in COMPANIES:
        if key in (company.name.casefold(), company.ticker.casefold()):
            return company
    tickers = ", ".join(c.ticker for c in COMPANIES)
    raise ScopeError(f"Unsupported company: {value!r}. Supported: {tickers}")


def companies_by_sector(sector: str) -> Tuple[Company, ...]:
    """Return all companies in a sector ('Technology' or 'Finance')."""
    return tuple(c for c in COMPANIES if c.sector.casefold() == sector.casefold())


@dataclass(frozen=True)
class ResearchRequest:
    """An immutable, validated contract for the rest of the pipeline."""

    companies: tuple
    fiscal_years: tuple
    metrics: tuple = SUPPORTED_METRICS

    def __post_init__(self) -> None:
        if not isinstance(self.companies, tuple) or len(self.companies) < 1:
            raise ScopeError("Provide at least one company.")
        if any(not isinstance(c, Company) or c not in COMPANIES for c in self.companies):
            raise ScopeError("All companies must be from the supported list.")
        if len(set(self.companies)) != len(self.companies):
            raise ScopeError("Companies must be distinct.")
        years = self.fiscal_years
        if not isinstance(years, tuple) or len(years) < 1:
            raise ScopeError("Provide at least one fiscal year.")
        if any(type(year) is not int or not 1000 <= year <= 9999 for year in years):
            raise ScopeError("Fiscal years must be four-digit integers.")
        if len(set(years)) != len(years):
            raise ScopeError("Fiscal years must be distinct.")
        if not isinstance(self.metrics, tuple) or self.metrics != SUPPORTED_METRICS:
            raise ScopeError("This baseline supports revenue, operating income and operating margin together.")
        object.__setattr__(self, "fiscal_years", tuple(sorted(years)))

    def to_dict(self) -> dict:
        result = asdict(self)
        result["companies"] = list(result["companies"])
        result["fiscal_years"] = list(self.fiscal_years)
        result["metrics"] = list(self.metrics)
        return result


def create_request(companies: list, fiscal_years: list) -> ResearchRequest:
    """Validate user selections and return the contract used by later parts."""
    resolved = tuple(
        resolve_company(c) if isinstance(c, str) else c
        for c in companies
    )
    return ResearchRequest(
        companies=resolved,
        fiscal_years=tuple(fiscal_years),
    )
