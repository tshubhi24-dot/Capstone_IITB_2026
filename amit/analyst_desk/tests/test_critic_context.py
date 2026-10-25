"""Canonical reporting context informs a critic without excusing real defects."""
from copy import deepcopy

import pytest

from desk.reasoning import Reasoner, ReasoningError


@pytest.fixture
def review():
    facts, metrics, periods = [], [], []
    for ticker, filed in (("ABT", "2026-02-20"), ("AMGN", "2026-02-13")):
        for year in (2024, 2025):
            ids = [f"fact-{ticker}-{year}-{concept}" for concept in ("revenue", "operating_income")]
            start, end = f"{year}-01-01", f"{year}-12-31"
            for identifier, concept, amount in zip(ids, ("revenue", "operating_income"), (1000, 200)):
                facts.append({"id": identifier, "ticker": ticker, "fiscal_year": year, "concept": concept,
                              "value": amount, "unit": "USD", "start": start, "end": end})
            metrics.append({"ticker": ticker, "year": year, "period_start": start, "period_end": end,
                            "revenue": "1000", "operating_income": "200", "margin_pct": "20.00",
                            "fact_ids": ids})
            periods.append({"ticker": ticker, "fiscal_year": year, "start": start, "end": end,
                            "filed": filed if year == 2025 else filed.replace("2026", "2025"), "source_ids": list(ids)})
    quote = "Product supply may be affected by manufacturing disruption."
    sources = [{"id": f"risk-ABT-{year}", "ticker": "ABT", "year": year, "text": quote} for year in (2024, 2025)]
    claim = {"claim_id": "risk-ABT-2024-2025-1", "ticker": "ABT", "before_year": 2024, "after_year": 2025,
             "category": "risk_observation", "confidence": "low",
             "text": "Selected disclosures describe conditional manufacturing disruption.",
             "citations": [{"source_id": source["id"], "quote": quote} for source in sources]}
    draft = {"body": "The financial table is code-owned. Selected disclosures are partial and original boundaries are unverified.",
             "source_fingerprint": "a" * 64, "metrics": metrics, "narrative_claims": [claim]}
    context = {"as_of": "2026-10-25", "source_fingerprint": draft["source_fingerprint"],
               "financial_checks": {"passed": True, "verified_numbers": 12, "total_numbers": 12},
               "source_periods": periods,
               "evidence_scope": {"selection": "partial", "original_item_boundaries_verified": False}}
    return draft, sources + facts, context


def reply(request, *, supported=True, issues=None, blockers=None, limitations=None):
    verdicts = [{"claim_id": claim["claim_id"], "supported": supported,
                 "reason": "Selected evidence supports the conditional disclosure."}
                for claim in request["context"]["claims"]]
    if "review_context" in request["context"]:
        return {"verdicts": verdicts,
                "blockers": blockers if blockers is not None else [
                    {"kind": "source_contradiction", "body_quote": "The financial table is code-owned.", "reason": issue}
                    for issue in issues or []], "limitations": limitations or []}
    return {"verdicts": verdicts, "issues": issues or []}


def test_reported_fiscal_periods_and_code_checks_reach_critic_with_explicit_review_date(review):
    draft, evidence, context = review
    unchanged = deepcopy(context)
    captured = []
    def model(stage, **request):
        captured.append(request)
        return reply(request)
    result = Reasoner(model).critique(draft, evidence, review_context=context)
    request = captured[0]
    assert result["passed"]
    assert request["context"]["review_context"] == unchanged == context
    assert request["context"]["body"] == draft["body"]
    assert set(row["id"] for row in request["context"]["evidence"]) == set(row["id"] for row in evidence)
    assert "do not substitute your training cutoff" in request["system"]
    assert "actual completed code verification, not an assertion made by the writer" in request["system"]
    assert "That disclosed limitation alone is not a body defect" in request["system"]
    assert "report any real contradiction" in request["system"]


@pytest.mark.parametrize("supported,issues", [
    (False, []), (True, ["The displayed value contradicts the supplied canonical financial input."]),
])
def test_valid_temporal_context_does_not_override_rejected_claim_or_real_body_issue(review, supported, issues):
    draft, evidence, context = review
    result = Reasoner(lambda stage, **request: reply(request, supported=supported, issues=issues)).critique(
        draft, evidence, review_context=context)
    assert result["passed"] is False
    assert result["verdicts"][0]["supported"] is supported
    assert result["issues"] == issues


def test_fresh_model_can_acknowledge_disclosed_scope_without_classifying_a_defect(review):
    draft, evidence, context = review
    limitations = ["Selected excerpts are partial and original Item boundaries remain unverified.",
                   "This bounded review does not independently audit full original filing HTML."]
    result = Reasoner(lambda stage, **request: reply(request, limitations=limitations)).critique(
        draft, evidence, review_context=context)
    assert result["passed"] and result["issues"] == [] and result["body_findings"] == []
    assert result["limitations"] == limitations


@pytest.mark.parametrize("kind", ["source_contradiction", "unsupported_conclusion", "scope_overclaim", "missing_required_limit"])
def test_every_typed_body_blocker_is_retained_and_blocks_even_if_claims_pass(review, kind):
    draft, evidence, context = review
    finding = {"kind": kind, "body_quote": "The financial table is code-owned.",
               "reason": "The model identifies an actual defect in the quoted body passage."}
    result = Reasoner(lambda stage, **request: reply(request, blockers=[finding])).critique(
        draft, evidence, review_context=context)
    assert all(verdict["supported"] for verdict in result["verdicts"])
    assert result["passed"] is False and result["issues"] == [finding["reason"]]
    assert result["body_findings"] == [finding]


@pytest.mark.parametrize("mutation,reason", [
    ("unknown_kind", "Invalid structured model output"),
    ("fabricated_anchor", "exact displayed note"),
    ("short_anchor", "Invalid structured model output"),
    ("unbounded_reason", "Invalid structured model output"),
    ("legacy_issues", "Invalid structured model output"),
])
def test_untyped_or_unanchored_body_issue_cannot_be_accepted(review, mutation, reason):
    draft, evidence, context = review
    def model(stage, **request):
        finding = {"kind": "source_contradiction", "body_quote": "The financial table is code-owned.",
                   "reason": "The displayed value contradicts a canonical source input."}
        if mutation == "unknown_kind":
            finding["kind"] = "acknowledged_limitation"
        elif mutation == "fabricated_anchor":
            finding["body_quote"] = "The issuer's revenue increased dramatically during this period."
        elif mutation == "short_anchor":
            finding["body_quote"] = "The"
        elif mutation == "unbounded_reason":
            finding["reason"] = "A" * 301
        response = reply(request, blockers=[finding])
        if mutation == "legacy_issues":
            response = {"verdicts": response["verdicts"], "issues": [finding["reason"]]}
        return response
    with pytest.raises(ReasoningError, match=reason):
        Reasoner(model).critique(draft, evidence, review_context=context)


@pytest.mark.parametrize("mutation", [
    "future_filing", "earlier_as_of", "filing_before_period_end", "invalid_date", "non_iso_date",
    "source_fingerprint", "source_id", "period_date", "issuer", "fiscal_year", "duplicate_period",
    "missing_period", "unverified_finances", "wrong_count", "boolean_count", "complete_coverage", "extra_metadata",
])
def test_invalid_or_contradictory_context_stops_before_a_critic_request(review, mutation):
    draft, evidence, context = review
    if mutation == "future_filing":
        context["source_periods"][0]["filed"] = "2026-12-01"
    elif mutation == "earlier_as_of":
        context["as_of"] = "2025-01-01"
    elif mutation == "filing_before_period_end":
        context["source_periods"][0]["filed"] = "2024-12-01"
    elif mutation == "invalid_date":
        context["source_periods"][0]["filed"] = "2026-02-30"
    elif mutation == "non_iso_date":
        context["as_of"] = "20261025"
    elif mutation == "source_fingerprint":
        context["source_fingerprint"] = "b" * 64
    elif mutation == "source_id":
        context["source_periods"][0]["source_ids"][0] = "risk-ABT-2024"
    elif mutation == "period_date":
        context["source_periods"][0]["start"] = "2024-01-02"
    elif mutation == "issuer":
        context["source_periods"][0]["ticker"] = "MSFT"
    elif mutation == "fiscal_year":
        context["source_periods"][0]["fiscal_year"] = 2023
    elif mutation == "duplicate_period":
        context["source_periods"][1] = deepcopy(context["source_periods"][0])
    elif mutation == "missing_period":
        context["source_periods"].pop()
    elif mutation == "unverified_finances":
        context["financial_checks"]["passed"] = False
    elif mutation == "wrong_count":
        context["financial_checks"].update(verified_numbers=9, total_numbers=9)
    elif mutation == "boolean_count":
        context["financial_checks"]["verified_numbers"] = True
    elif mutation == "complete_coverage":
        context["evidence_scope"]["original_item_boundaries_verified"] = True
    else:
        context["private_account_metadata"] = "This must not enter a model request."
    calls = []
    with pytest.raises(ReasoningError, match="Critic review context"):
        Reasoner(lambda *args, **kwargs: calls.append(kwargs)).critique(draft, evidence, review_context=context)
    assert calls == []


def test_legacy_critic_request_remains_unchanged_when_context_is_omitted(review):
    draft, evidence, _ = review
    captured = []
    def model(stage, **request):
        captured.append(deepcopy(request))
        return reply(request)
    reasoner = Reasoner(model)
    reasoner.critique(draft, evidence)
    reasoner.critique(draft, evidence, review_context=None)
    assert captured[0] == captured[1]
    assert "review_context" not in captured[0]["context"]
    assert "application-owned metadata" not in captured[0]["system"]
