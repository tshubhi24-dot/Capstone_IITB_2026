"""Query decomposition — the query-side retrieval technique (L6).

An analyst question often names several companies and years at once:
"Compare Microsoft's and Alphabet's operating margins in FY2023 and FY2024".
Searched as one query, the best five passages can all come from one company,
so the other company gets no evidence at all.

Decomposition splits the question into one sub-query per (company, year)
named in it, runs each with metadata filters, and merges the results
round-robin so every sub-query is represented in the final top-k.

Company and year detection is plain code over the supported company list in
scope.py, not an LLM call: it is deterministic, free, and testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .scope import COMPANIES

# Words that name a company in a question, mapped to its ticker. Names are
# matched on word boundaries; short tickers like "V" and "MS" only match in
# capitals so the words "v" and "ms" in text don't trigger them.
_ALIASES = {
    "microsoft": "MSFT", "alphabet": "GOOGL", "google": "GOOGL", "apple": "AAPL",
    "amazon": "AMZN", "meta": "META", "facebook": "META", "nvidia": "NVDA",
    "advanced micro devices": "AMD", "oracle": "ORCL", "jpmorgan": "JPM",
    "jp morgan": "JPM", "goldman sachs": "GS", "goldman": "GS",
    "bank of america": "BAC", "visa": "V", "morgan stanley": "MS",
    "mastercard": "MA", "wells fargo": "WFC",
}
_TICKERS = {c.ticker for c in COMPANIES}


@dataclass(frozen=True)
class SubQuery:
    text: str
    company: str | None   # ticker
    year: int | None


def find_companies(question: str) -> list[str]:
    """Tickers named in the question, in order of first mention."""
    found: list[tuple[int, str]] = []
    lower = question.lower()
    # Longest aliases first, and each matched span is claimed, so "Bank of
    # America" is not also read as some shorter alias inside it
    taken = [False] * len(lower)
    for alias in sorted(_ALIASES, key=len, reverse=True):
        for m in re.finditer(rf"\b{re.escape(alias)}\b", lower):
            if not any(taken[m.start():m.end()]):
                found.append((m.start(), _ALIASES[alias]))
                for i in range(m.start(), m.end()):
                    taken[i] = True
    for m in re.finditer(r"\b[A-Z]{1,5}\b", question):
        if m.group() in _TICKERS and not any(taken[m.start():m.end()]):
            found.append((m.start(), m.group()))
    tickers: list[str] = []
    for _, t in sorted(found):
        if t not in tickers:
            tickers.append(t)
    return tickers


def find_years(question: str) -> list[int]:
    """Fiscal years named in the question ("FY2024", "2023", "fiscal 2022")."""
    years = []
    for m in re.finditer(r"(?<!\d)(?:fy\s?)?(20\d{2})(?!\d)", question, re.I):
        y = int(m.group(1))
        if y not in years:
            years.append(y)
    return years


def strip_entities(question: str) -> str:
    """Remove company names, tickers and years from a question.

    Once a sub-query is filtered to one company and year, those words only
    add noise: every passage of Goldman Sachs' 2023 10-K carries the footer
    "Goldman Sachs 2023 Form 10-K", so BM25 rewards the footer instead of the
    topic. Falls back to the original if almost nothing is left.
    """
    text = question
    for alias in sorted(_ALIASES, key=len, reverse=True):
        # also the possessive: "Apple's", "Goldman Sachs'"
        text = re.sub(rf"\b{re.escape(alias)}(?:['’]s?)?(?!\w)", " ", text, flags=re.I)
    text = re.sub(
        r"\b(?:" + "|".join(sorted(_TICKERS, key=len, reverse=True)) + r")(?:['’]s?)?(?!\w)", " ", text
    )
    text = re.sub(r"(?<!\d)(?:fiscal\s+year\s+|fiscal\s+|fy\s?)?20\d{2}(?!\d)", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" ,.?()")
    return text if len(text.split()) >= 2 else question


def decompose(question: str, rewrite: bool = True) -> list[SubQuery]:
    """Split a question into one filtered sub-query per (company, year).

    With no company named, the question is searched as is. With companies but
    no year, each company is searched across all years. rewrite strips the
    company and year words the filters already cover.
    """
    companies = find_companies(question)
    if not companies:
        return [SubQuery(question, None, None)]
    years = find_years(question) or [None]
    text = strip_entities(question) if rewrite else question
    return [SubQuery(text, c, y) for c in companies for y in years]


def search_decomposed(retriever, question: str, top_k: int = 5,
                      rewrite: bool = True, **search_kwargs) -> list[dict]:
    """Run each sub-query and merge round-robin into top_k passages.

    Round-robin (1st of each, then 2nd of each, ...) guarantees every
    company/year in the question contributes evidence before any one of them
    contributes a second passage.
    """
    subqueries = decompose(question, rewrite)
    per_query = [
        retriever.search(sq.text, top_k=top_k, company=sq.company, year=sq.year, **search_kwargs)
        for sq in subqueries
    ]
    merged, seen = [], set()
    for rank in range(top_k):
        for hits in per_query:
            if rank < len(hits) and hits[rank]["passage_id"] not in seen:
                merged.append(hits[rank])
                seen.add(hits[rank]["passage_id"])
    return merged[:top_k]
