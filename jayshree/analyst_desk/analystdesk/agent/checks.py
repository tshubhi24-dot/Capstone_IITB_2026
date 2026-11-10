"""Code checks on a draft note — the self-correction loop's judge (L8, L13).

Every number in a note must be traceable, in one of three ways:

  1. An XBRL fact, rendered by code from a placeholder (see figures.py):
         $245,122.0M [fact: RevenueFromContract.../2024/0000950170-24-087843]
  2. A ratio, growth rate or margin change computed from facts:
         44.64% [calc: OperatingIncomeLoss/2024/... / RevenueFromContract.../2024/...]
         15.67% [growth: Revenue.../2024/... / Revenue.../2023/...]       (A / B - 1) x 100
         +2.87 pp [diff: OpInc/2024 / Rev/2024 - OpInc/2023 / Rev/2023]   (A/B - C/D) x 100
  3. A figure quoted from a filing: the same line cites the passage, e.g.
     [MSFT_2024_item7_017], and the number appears in that passage's text.

check_note() verifies all three in code, not with an LLM (rule 1):
  * each [fact: ...] value equals the XBRL fact, in $ millions to 1 decimal;
  * each [calc: A / B] percentage equals A / B x 100, to 2 decimals, with A and
    B from the same company and fiscal year (growth: the same item, an earlier year);
  * each [growth: A / B] equals (A / B - 1) x 100 and each [diff: ...] the margin
    change in percentage points;
  * a margin needs positive revenue and a growth rate a positive earlier amount;
  * each quoted number occurs, with the same unit and scale, in a passage cited
    on its line ($2.2K never matches $2.2 billion);
  * cited passages exist, and no template token such as {WHAT_CHANGED} is left;
  * no line sets an operating margin against a pre-tax margin (banks);
  * no investment-advice wording ("buy", "price target", ...), and no company
    from the analyst's private watchlist that the plan does not cover.
The issues it returns are fed back to the writer for a revision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..edgar import OPERATING_INCOME_CONCEPT, PRETAX_INCOME_CONCEPT, REVENUE_CONCEPTS
from ..scope import COMPANIES
from ..servers.edgar_server import get_fact
from .figures import PLACEHOLDER, half_up
from .guards import defences_on, mentions

# A fact_id has its own slashes (Concept/2024/0000950170-24-087843), so the
# division in [calc: A / B] is the " / " between two complete fact_ids
FACT_ID = r"[A-Za-z]+/\d{4}/\d{10}-\d{2}-\d{6}"
FACT = re.compile(r"(-)?\$\s?([\d,]+(?:\.\d+)?)\s?([MB])\s*\[fact:\s*([^\]]+?)\s*\]")
CALC = re.compile(rf"(-?[\d.]+)\s?%\s*\[calc:\s*({FACT_ID})\s*/\s*({FACT_ID})\s*\]")
GROWTH = re.compile(rf"(-?[\d.]+)\s?%\s*\[growth:\s*({FACT_ID})\s*/\s*({FACT_ID})\s*\]")
DIFF = re.compile(rf"([+-]?[\d.]+)\s?pp\s*\[diff:\s*({FACT_ID})\s*/\s*({FACT_ID})\s*-\s*"
                  rf"({FACT_ID})\s*/\s*({FACT_ID})\s*\]")
PASSAGE_ID = re.compile(r"\b([A-Z]{1,5}_\d{4}_item(?:1a|7)_\d{3})\b")
# Any money amount or percentage, to catch numbers with no source
MONEY = re.compile(r"-?\$\s?[\d,]+(?:\.\d+)?\s?(?:[MBK]\b|million|billion|thousand)?")
PERCENT = re.compile(r"-?\d+(?:\.\d+)?\s?%")
POINTS = re.compile(r"[+-]?\d+(?:\.\d+)?\s?(?:pp\b|percentage points?)")
# A writer template token left in the note, e.g. {WHAT_CHANGED}: the note is unfinished
TEMPLATE_TOKEN = re.compile(r"\{([A-Z][A-Z_]{2,})\}")
_SCALE_AFTER = r"(?!\s?(?:thousand|million|billion|[KMB]\b|bn\b|mn\b))"
MARGIN_BASIS = {OPERATING_INCOME_CONCEPT: "operating", PRETAX_INCOME_CONCEPT: "pretax"}
_COMPANIES = {company.ticker: company for company in COMPANIES}
_REVENUE_CONCEPTS = frozenset(concept for concepts in REVENUE_CONCEPTS.values() for concept in concepts)
ADVICE = re.compile(
    r"\b(buy|sell|hold rating|overweight|underweight|outperform|underperform|"
    r"price target|we recommend|strong buy|investors should)\b", re.I)


@dataclass
class CheckResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    verified_numbers: int = 0
    total_numbers: int = 0

    @property
    def verified_share(self) -> float:
        return round(100 * self.verified_numbers / self.total_numbers, 1) if self.total_numbers else 100.0


def _fact_value(fact_id: str, cache: dict) -> float | None:
    if fact_id not in cache:
        r = get_fact(fact_id)
        cache[fact_id] = r.fact.value_usd if r.ok else None
        cache[("ticker", fact_id)] = r.ticker if r.ok else None
        if r.ok and r.fact:
            cache[("period", fact_id)] = (r.fact.period_start, r.fact.period_end)
    return cache[fact_id]


def _mismatch(pairs: list[tuple[str, str]], cache: dict, same_year: bool = True) -> str | None:
    """Why two facts in one calculation do not belong together, or None.
    Each (a, b) pair must be the same company and, for a ratio, the same fiscal year."""
    for a, b in pairs:
        ta, tb = cache.get(("ticker", a)), cache.get(("ticker", b))
        if ta and tb and ta != tb:
            return f"mixes {ta} and {tb}"
        if same_year and a.split("/")[1] != b.split("/")[1]:
            return f"mixes FY{a.split('/')[1]} and FY{b.split('/')[1]}"
        if same_year and a.split("/")[2] != b.split("/")[2]:
            return "mixes filings"
        pa, pb = cache.get(("period", a)), cache.get(("period", b))
        if same_year and pa and pb and pa != pb:
            return f"mixes annual periods {pa} and {pb}"
    return None


def _margin_inputs(numerator: str, denominator: str, cache: dict) -> str | None:
    income, revenue = numerator.split("/")[0], denominator.split("/")[0]
    ticker = cache.get(("ticker", numerator))
    company = _COMPANIES.get(ticker)
    if income not in MARGIN_BASIS:
        return "numerator is not a supported income concept"
    if revenue not in _REVENUE_CONCEPTS:
        return "denominator is not a supported revenue concept"
    if company:
        expected = PRETAX_INCOME_CONCEPT if company.margin_basis == "pretax" else OPERATING_INCOME_CONCEPT
        if income != expected or revenue not in REVENUE_CONCEPTS[company.cik]:
            return f"concepts do not match {ticker}'s supported margin basis"
    return None


def _digits(number: str) -> str:
    """The digits of a quoted number: '$7.74 billion' -> '7.74', '16%' -> '16'."""
    return re.sub(r"[^\d.]", "", number).strip(".")


def _unit_pattern(number: str) -> str:
    """What must follow (or precede) the digits in the passage: the same unit."""
    n = number.lower()
    if "%" in n:
        return r"\s?(?:%|percent)"
    if "pp" in n or "percentage point" in n:
        return r"\s?(?:pp|percentage points?)"
    if "billion" in n or re.search(r"\db\b", n):
        return r"\s?(?:billion|b\b|bn\b)"
    if "million" in n or re.search(r"\dm\b", n):
        return r"\s?(?:million|m\b|mn\b)"
    if "thousand" in n or re.search(r"\dk\b", n):
        return r"\s?(?:thousand|k\b)"
    return _SCALE_AFTER   # no scale in the note: the passage must not give one either


def _quoted_in(number: str, text: str) -> bool:
    """Does the passage contain this number with the same unit?

    "5%" must appear as 5% (or 5 percent), "$2.2 billion" as 2.2 billion:
    a bare digit somewhere in the passage does not count.
    """
    d = _digits(number)
    if not d:
        return False
    plain = re.sub(r"(?<=\d),(?=\d{3})", "", text)   # ignore thousands separators
    digits = re.escape(d.replace(",", ""))
    pattern = rf"(?<![\d.]){digits}(?![\d.]\d){_unit_pattern(number)}"
    if "$" in number:
        pattern = rf"\$\s?" + pattern
    return re.search(pattern, plain, re.I) is not None


def check_note(body: str, passage_exists=None, passage_text=None, private: list[str] | None = None) -> CheckResult:
    """Verify every number and citation in a draft note body.

    passage_text(pid) -> str | None enables checking quoted numbers against
    the cited passage; passage_exists(pid) -> bool only checks citations.
    private: watchlist tickers outside the plan, which the note must not name.
    """
    if passage_exists is None and passage_text is not None:
        passage_exists = lambda pid: passage_text(pid) is not None   # noqa: E731
    issues: list[str] = []
    cache: dict = {}
    verified = total = 0
    covered: list[tuple[int, int]] = []   # spans of numbers that carry a source

    for m in FACT.finditer(body):
        total += 1
        covered.append(m.span())
        sign, number, scale, fid = m.groups()
        shown = float(number.replace(",", "")) * (1000 if scale == "B" else 1) * (-1 if sign else 1)
        actual = _fact_value(fid, cache)
        if actual is None:
            issues.append(f"Unknown fact_id {fid!r} for {m.group(0).split(' [')[0]}.")
        elif abs(shown - float(half_up(actual / 1e6, 1))) > (50 if scale == "B" else 0.05):
            issues.append(f"{m.group(0).split(' [')[0]} does not match {fid} "
                          f"(reported ${actual / 1e6:,.1f}M).")
        else:
            verified += 1

    def two_dp_matches(shown: str, value: float) -> bool:
        return abs(float(shown) - float(half_up(value))) < 0.005

    for m in CALC.finditer(body):
        total += 1
        covered.append(m.span())
        num, den = _fact_value(m.group(2), cache), _fact_value(m.group(3), cache)
        if num is None or den is None:
            issues.append(f"{m.group(1)}% cites an unknown fact in [calc: {m.group(2)} / {m.group(3)}].")
        elif bad := _mismatch([(m.group(2), m.group(3))], cache):
            issues.append(f"{m.group(1)}% [calc] {bad}: a ratio needs one company and one fiscal year.")
        elif bad := _margin_inputs(m.group(2), m.group(3), cache):
            issues.append(f"{m.group(1)}% [calc] {bad}.")
        elif den <= 0:
            issues.append(f"{m.group(1)}% divides by revenue that is not positive; a margin is not meaningful.")
        elif not two_dp_matches(m.group(1), num / den * 100):
            issues.append(f"{m.group(1)}% is wrong: {m.group(2)} / {m.group(3)} = "
                          f"{half_up(num / den * 100)}%.")
        else:
            verified += 1

    for m in GROWTH.finditer(body):
        total += 1
        covered.append(m.span())
        a, b = _fact_value(m.group(2), cache), _fact_value(m.group(3), cache)
        if a is None or b is None:
            issues.append(f"{m.group(1)}% cites an unknown fact in [growth: {m.group(2)} / {m.group(3)}].")
        elif (bad := _mismatch([(m.group(2), m.group(3))], cache, same_year=False)) or                 m.group(2).split("/")[0] != m.group(3).split("/")[0] or                 m.group(2).split("/")[1] <= m.group(3).split("/")[1]:
            issues.append(f"{m.group(1)}% [growth] must compare one company's same item with an earlier year"
                          f"{': ' + bad if bad else ''}.")
        elif b <= 0:
            issues.append(f"{m.group(1)}% growth starts from a zero or negative amount, so a growth rate is "
                          "not meaningful: state both amounts instead.")
        elif not two_dp_matches(m.group(1), (a / b - 1) * 100):
            issues.append(f"{m.group(1)}% growth is wrong: should be {half_up((a / b - 1) * 100)}%.")
        else:
            verified += 1

    for m in DIFF.finditer(body):
        total += 1
        covered.append(m.span())
        a, b, c, d = (_fact_value(m.group(i), cache) for i in (2, 3, 4, 5))
        if None in (a, b, c, d):
            issues.append(f"{m.group(1)} pp cites an unknown fact in its [diff: ...].")
        elif bad := (_mismatch([(m.group(2), m.group(3)), (m.group(4), m.group(5))], cache)
                     or _mismatch([(m.group(2), m.group(4))], cache, same_year=False)):
            issues.append(f"{m.group(1)} pp [diff] {bad}: it must compare one company's margins.")
        elif bad := (_margin_inputs(m.group(2), m.group(3), cache)
                     or _margin_inputs(m.group(4), m.group(5), cache)):
            issues.append(f"{m.group(1)} pp [diff] {bad}.")
        elif (m.group(2).split("/")[0] != m.group(4).split("/")[0]
              or m.group(3).split("/")[0] != m.group(5).split("/")[0]
              or m.group(2).split("/")[1] <= m.group(4).split("/")[1]):
            issues.append(f"{m.group(1)} pp [diff] must compare the same margin concepts with an earlier year.")
        elif b <= 0 or d <= 0:
            issues.append(f"{m.group(1)} pp uses revenue that is not positive; a margin change is not meaningful.")
        elif not two_dp_matches(m.group(1), (a / b - c / d) * 100):
            change = half_up((a / b - c / d) * 100)
            issues.append(f"{m.group(1)} pp is wrong: should be {'+' if change >= 0 else ''}{change} pp.")
        else:
            verified += 1

    def is_covered(span):
        return any(s <= span[0] and span[1] <= e for s, e in covered)

    # Numbers without a fact/calc tag must be quotes from a passage cited on the same line
    line_starts = [0] + [i + 1 for i, ch in enumerate(body) if ch == "\n"]
    def line_of(pos):
        start = max(s for s in line_starts if s <= pos)
        end = body.find("\n", pos)
        return body[start:end if end != -1 else len(body)]

    for pattern in (MONEY, PERCENT, POINTS):
        for m in pattern.finditer(body):
            if is_covered(m.span()):
                continue
            total += 1
            number = m.group().strip()
            cited = PASSAGE_ID.findall(line_of(m.start()))
            if passage_text is not None and cited and any(
                    _quoted_in(number, passage_text(pid) or "") for pid in cited):
                verified += 1
            elif cited:
                issues.append(f"Number {number!r} does not appear in the passage(s) cited on its line "
                              f"({', '.join(cited)}).")
            else:
                issues.append(f"Number {number!r} has no source: use a figure placeholder, or quote "
                              f"it from a filing and cite the passage on the same line.")

    if passage_exists is not None:
        for pid in sorted(set(PASSAGE_ID.findall(body))):
            if not passage_exists(pid):
                issues.append(f"Cited passage {pid} does not exist.")

    # a figure placeholder left in the note means a number is missing (e.g. a peer not in the plan)
    for key in sorted(set(PLACEHOLDER.findall(body))):
        issues.append(f"Unknown placeholder {{{key}}}.")
    for key in sorted(set(TEMPLATE_TOKEN.findall(body))):
        issues.append(f"The note still contains the template token {{{key}}}: it is unfinished.")

    # Like-for-like: one line must not set an operating margin against a pre-tax margin
    for line in body.splitlines():
        bases = {MARGIN_BASIS.get(num.split("/")[0]) for _, num, _ in CALC.findall(line)} - {None}
        if len(bases) > 1:
            issues.append("This line compares an operating margin with a pre-tax margin, which are not "
                          f"comparable; show them separately: {re.sub(r' ?\[[^\]]*\]', '', line).strip()[:120]!r}")

    if defences_on():   # output guardrails (off only for experiment E2)
        for m in ADVICE.finditer(body):
            issues.append(f"Investment-advice wording {m.group()!r} is not allowed in a research note.")
        for t in mentions(body, private or []):
            issues.append(f"The note names {t}, which is on the analyst's private watchlist and not in the "
                          "approved plan. Remove it.")

    return CheckResult(ok=not issues, issues=issues, verified_numbers=verified, total_numbers=total)
