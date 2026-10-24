"""Read-only source access and independent financial verification.

The first journey deliberately uses lexical retrieval and makes no model calls.
This module does not import the older reference application.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
import hashlib
import json
import os
from pathlib import Path
import re


class Corpus:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("CORPUS_PATH", "/sources/corpus.json"))
        raw = self.path.read_bytes()
        self.fingerprint = hashlib.sha256(raw).hexdigest()
        document = json.loads(raw)
        self.metadata = document.get("metadata", {})
        self._companies = document["companies"]
        self._facts = {row["id"]: row for row in document["facts"]}
        self._passages = {row["id"]: row for row in document["passages"]}
        if len(self._facts) != len(document["facts"]) or len(self._passages) != len(document["passages"]):
            raise ValueError("Duplicate source identifiers")
        if not self._facts or not self._passages:
            raise ValueError("A real-source snapshot with facts and passages is required")

    def companies(self):
        return deepcopy(self._companies)

    def years(self, ticker):
        return sorted({int(v["fiscal_year"]) for v in self._facts.values() if v["ticker"] == ticker})

    def facts(self, ticker, years):
        if not set(years) <= set(self.years(ticker)):
            raise ValueError("Requested fiscal year is outside the source snapshot")
        return deepcopy([v for v in self._facts.values() if v["ticker"] == ticker and v["fiscal_year"] in years])

    def fact(self, identifier):
        if identifier not in self._facts:
            raise ValueError("Unknown fact identifier")
        return deepcopy(self._facts[identifier])

    def passage(self, identifier):
        if identifier not in self._passages:
            raise ValueError("Unknown passage identifier")
        return deepcopy(self._passages[identifier])

    get_passage = passage

    def section(self, ticker, year, item="1A"):
        chunks = [v for v in self._passages.values() if v["ticker"] == ticker and int(v["year"]) == year and v["item"].upper() == item.upper()]
        if not chunks:
            raise ValueError("Requested section is missing from the snapshot")
        return {"ticker": ticker, "year": year, "item": item, "chunks": deepcopy(chunks),
                "source_ids": [v["id"] for v in chunks], "snapshot_complete": True, "complete_section": False,
                "completeness_basis": "All section chunks in the supplied cached snapshot; original Item boundaries require domain review."}

    def search(self, query, ticker, years, k=5):
        from rank_bm25 import BM25Okapi
        rows = [v for v in self._passages.values() if v["ticker"] == ticker and int(v["year"]) in years]
        if not rows:
            return []
        tokenize = lambda text: re.findall(r"[a-z0-9]+", text.lower())
        index = BM25Okapi([tokenize(v["text"]) or ["empty"] for v in rows])
        scores = index.get_scores(tokenize(query))
        selected = sorted(range(len(rows)), key=lambda i: (-scores[i], rows[i]["id"]))[:max(1, min(k, 10))]
        return [deepcopy({**rows[i], "retrieval_score": float(scores[i])}) for i in selected]

    def canonical_pair(self, revenue_fact_id, operating_income_fact_id):
        revenue, income = self.fact(revenue_fact_id), self.fact(operating_income_fact_id)
        if revenue["concept"] != "revenue" or income["concept"] != "operating_income":
            raise ValueError("Operating margin requires revenue and operating income")
        for field in ("ticker", "fiscal_year", "start", "end", "unit", "accession"):
            if revenue[field] != income[field]:
                raise ValueError(f"Incompatible fact field: {field}")
        duration = (date.fromisoformat(revenue["end"]) - date.fromisoformat(revenue["start"])).days + 1
        if not 330 <= duration <= 380 or revenue["unit"] != "USD":
            raise ValueError("Expected compatible annual USD facts")
        amounts = [Decimal(str(value["value"])) for value in (revenue, income)]
        if not all(value.is_finite() for value in amounts):
            raise ValueError("Financial inputs must be finite")
        if amounts[0] <= 0:
            raise ValueError("Revenue denominator must be positive")
        return revenue, income

    def verify_row(self, row):
        try:
            revenue, income = self.canonical_pair(*row["fact_ids"])
            for key, expected in (("ticker", revenue["ticker"]), ("year", revenue["fiscal_year"]),
                                  ("period_start", revenue["start"]), ("period_end", revenue["end"]), ("unit", revenue["unit"])):
                if row[key] != expected:
                    return False
            if Decimal(str(row["revenue"])) != Decimal(str(revenue["value"])) or Decimal(str(row["operating_income"])) != Decimal(str(income["value"])):
                return False
            with localcontext() as context:
                context.prec = 40
                expected = (Decimal(str(income["value"])) / Decimal(str(revenue["value"])) * 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            actual = Decimal(str(row["margin_pct"]))
            return actual.is_finite() and actual == expected
        except (KeyError, ValueError, TypeError, ArithmeticError):
            return False
