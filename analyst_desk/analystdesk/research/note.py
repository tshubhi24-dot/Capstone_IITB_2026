"""Research note schema — the typed output contract for the Analyst Desk pipeline.

Every downstream stage (compliance critic, writer, approval gate, portal) consumes
a ResearchNote. Defining the schema here means all stages agree on the shape.

Key invariant: every MetricRow with a non-None value MUST have a corresponding
fact_id. A number without a fact_id cannot be verified and must not appear in a
published note. The compliance critic enforces this with code, not with an LLM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class MetricRow:
    """One company + fiscal year measurement, with sources.

    All dollar values are in USD millions (rounded to 1 decimal place).
    Margins are derived — they have no EDGAR fact_id of their own because
    they are computed in code from revenue and the matching income line.

    margin_basis says which margin is the headline for this company:
    "operating" (operating income / revenue) or "pretax" (pre-tax income /
    net revenue, used for banks). Margins on different bases must not be
    compared with each other.
    """
    company: str
    fiscal_year: int
    revenue_usd_m: float | None
    operating_income_usd_m: float | None
    operating_margin_pct: float | None      # computed, not from EDGAR
    revenue_fact_id: str | None
    operating_income_fact_id: str | None
    period_end: str | None                  # e.g. "2024-06-30" from EDGAR
    margin_basis: str = "operating"
    pretax_income_usd_m: float | None = None
    pretax_margin_pct: float | None = None  # computed, not from EDGAR
    pretax_income_fact_id: str | None = None

    def headline_income_fact_id(self) -> str | None:
        if self.margin_basis == "pretax":
            return self.pretax_income_fact_id
        return self.operating_income_fact_id

    def headline_margin_pct(self) -> float | None:
        if self.margin_basis == "pretax":
            return self.pretax_margin_pct
        return self.operating_margin_pct


@dataclass
class ResearchNote:
    """The output of the Analyst Desk pipeline.

    status:
        "draft"     — produced by the pipeline, not yet reviewed
        "approved"  — analyst signed the exact payload
        "published" — written to the research portal
        "rejected"  — analyst rejected, not published

    rows:     one MetricRow per company per year (6 rows: 2 companies × 3 years)
    summary:  analyst-readable text (empty in C0; written by the writer agent later)
    warnings: any missing data, mismatched periods, or unverified numbers
    """
    title: str
    status: str
    rows: list[MetricRow]
    summary: str = ""
    warnings: list[str] = field(default_factory=list)

    def verified_count(self) -> int:
        """How many rows have fact_ids for revenue and their headline income."""
        return sum(
            1 for r in self.rows
            if r.revenue_fact_id and r.headline_income_fact_id()
        )

    def verification_pct(self) -> float:
        """Percentage of rows where all numbers are EDGAR-verified."""
        if not self.rows:
            return 0.0
        return round(self.verified_count() / len(self.rows) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "verification_pct": self.verification_pct(),
            "warnings": self.warnings,
            "rows": [
                {
                    "company": r.company,
                    "fiscal_year": r.fiscal_year,
                    "period_end": r.period_end,
                    "revenue_usd_m": r.revenue_usd_m,
                    "operating_income_usd_m": r.operating_income_usd_m,
                    "operating_margin_pct": r.operating_margin_pct,
                    "revenue_fact_id": r.revenue_fact_id,
                    "operating_income_fact_id": r.operating_income_fact_id,
                    "margin_basis": r.margin_basis,
                    "pretax_income_usd_m": r.pretax_income_usd_m,
                    "pretax_margin_pct": r.pretax_margin_pct,
                    "pretax_income_fact_id": r.pretax_income_fact_id,
                }
                for r in self.rows
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
