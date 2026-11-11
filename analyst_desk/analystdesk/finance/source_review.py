"""Optional, independently maintained decisions for annual XBRL presentations."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class SourceReviewError(ValueError):
    """The configured source-review register is unavailable or invalid."""


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ticker: str = Field(pattern=r"^[A-Z]{1,5}$")
    fiscal_year: int = Field(ge=1900, le=2100)
    concept: str = Field(pattern=r"^[A-Za-z]+$")
    accession: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    period_start: str
    period_end: str
    filed: str
    form: Literal["10-K", "10-K/A"]
    value_usd: int
    decision: Literal["eligible", "excluded"]
    reviewer: str = Field(min_length=1)
    reviewed_at: str
    evidence: str = Field(min_length=1)
    rationale: str = Field(min_length=1)

    @field_validator("reviewer", "evidence", "rationale")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("period_start", "period_end", "filed", "reviewed_at")
    @classmethod
    def valid_date(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("must be an ISO date")
        date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def consistent_dates(self):
        if self.period_start >= self.period_end or int(self.period_end[:4]) != self.fiscal_year:
            raise ValueError("period must end in the stated fiscal year")
        if self.filed < self.period_end or self.reviewed_at < self.filed:
            raise ValueError("filing and review dates must follow the period end")
        return self


class Register(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal[1]
    decisions: list[Decision]

    @model_validator(mode="after")
    def unique_decisions(self):
        keys = [(d.ticker, d.fiscal_year, d.concept, d.accession) for d in self.decisions]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate source-review decision")
        return self


def register_path() -> Path | None:
    raw = os.getenv("SOURCE_REVIEW_FILE")
    if raw is None or raw == "":
        return None
    if not raw.strip():
        raise SourceReviewError("SOURCE_REVIEW_FILE must be a non-empty path when configured.")
    return Path(raw)


def load_register() -> Register | None:
    path = register_path()
    if path is None:
        return None
    try:
        return Register.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, ValidationError) as exc:
        raise SourceReviewError(f"Cannot load source-review register {path}: {exc}") from exc


def decision_for(register: Register | None, ticker: str, year: int, concept: str, entry: dict) -> Decision | None:
    """Return a matching decision only if the reviewed fact matches exactly."""
    if register is None:
        return None
    matches = [d for d in register.decisions if
               (d.ticker, d.fiscal_year, d.concept, d.accession) ==
               (ticker, year, concept, entry.get("accn"))]
    if not matches:
        return None
    d = matches[0]
    actual = (entry.get("start"), entry.get("end"), entry.get("filed"), entry.get("form"), entry.get("val"))
    expected = (d.period_start, d.period_end, d.filed, d.form, d.value_usd)
    if actual != expected:
        raise SourceReviewError(f"Reviewed source {ticker} FY{year} {concept}/{d.accession} differs from cached data.")
    return d


def status(register: Register | None, ticker: str, year: int, concept: str, entry: dict) -> str:
    decision = decision_for(register, ticker, year, concept, entry)
    return decision.decision if decision else "unverified"
