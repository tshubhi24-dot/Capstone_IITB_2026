"""Grounding and live-reasoning control tests; no paid provider calls."""
from copy import deepcopy
from hashlib import sha256

import pytest

from desk.reasoning import (CriticOutput, PlanOutput, QueryOutput, Reasoner,
                            ReasoningError, RiskOutput, WriterOutput,
                            normalize_evidence, render_claims, validate_claims,
                            validate_prose)


@pytest.fixture
def evidence():
    return [
        {"id": "msft-before", "ticker": "MSFT", "year": 2023,
         "text": "Cyber attacks may interrupt services and compromise customer trust. Additional source material."},
        {"id": "msft-after", "ticker": "MSFT", "year": 2024,
         "text": "Cybersecurity threats may disrupt operations and customer trust. Further source material."},
        {"id": "aapl-before", "ticker": "AAPL", "year": 2023,
         "text": "Cyber attacks may interrupt services and compromise customer trust. An issuer-specific source."},
    ]


def claim():
    return {"claim_id": "risk-MSFT-2023-2024-1", "ticker": "MSFT", "before_year": 2023, "after_year": 2024,
            "category": "risk_observation", "confidence": "medium",
            "text": "Cybersecurity remains a disclosed exposure with potential operational disruption.",
            "citations": [{"source_id": "msft-before", "quote": "Cyber attacks may interrupt services"},
                          {"source_id": "msft-after", "quote": "Cybersecurity threats may disrupt operations"}]}


def draft(claims):
    return {"body": "Canonical financial table stays code-owned.\n" + render_claims(claims),
            "narrative_claims": claims, "source_fingerprint": "test-only-source-fingerprint"}


def test_canonical_fact_evidence_preserves_exact_values_and_rejects_id_conflicts():
    fact = {"id": "fact-msft", "ticker": "MSFT", "fiscal_year": 2025, "concept": "revenue", "value": 300,
            "unit": "USD", "start": "2024-07-01", "end": "2025-06-30"}
    row = normalize_evidence([fact, fact])[0]
    assert row == {"id": "fact-msft", "ticker": "MSFT", "year": 2025,
                   "text": "MSFT fiscal 2025: revenue = 300 USD; period 2024-07-01 to 2025-06-30"}
    with pytest.raises(ReasoningError, match="conflicting"):
        normalize_evidence([fact, {**fact, "value": 999}])


def test_real_id_from_wrong_issuer_cannot_support_a_comparison(evidence):
    altered = claim()
    altered["citations"][0]["source_id"] = "aapl-before"
    with pytest.raises(ReasoningError, match="own issuer"):
        validate_claims([altered], evidence)


def test_wrong_period_or_missing_period_is_rejected_despite_exact_quotes(evidence):
    altered = claim()
    altered["after_year"] = 2025
    with pytest.raises(ReasoningError, match="both required years"):
        validate_claims([altered], evidence)
    altered = claim()
    altered["citations"] = altered["citations"][:1]
    with pytest.raises(ReasoningError, match="both required years"):
        validate_claims([altered], evidence)


def test_known_id_does_not_make_a_fabricated_quote_valid(evidence):
    altered = claim()
    altered["citations"][0]["quote"] = "A severe cyber incident definitely occurred."
    with pytest.raises(ReasoningError, match="quote"):
        validate_claims([altered], evidence)
    altered["citations"][0]["source_id"] = "not-in-evidence"
    with pytest.raises(ReasoningError, match="unknown"):
        validate_claims([altered], evidence)


@pytest.mark.parametrize("text", [
    "Revenue doubled during the reporting period.",
    "The firm generated one billion dollars.",
    "The operating margin was twenty percent.",
    "Revenue is 2025 USD according to the source.",
    "The firm experienced ١٢ incidents during the period.",
    "Operating income was halved in the period.",
    "The issuer incurred billions of dollars of losses.",
    "Revenue rose fourfold during the period.",
])
def test_digit_and_implicit_quantities_cannot_escape_the_table(text):
    with pytest.raises(ReasoningError):
        validate_prose(text)


def test_narrow_third_party_idiom_is_not_an_arbitrary_number_exception():
    assert validate_prose("Third-party service providers may expose the issuer to operational disruption.")
    with pytest.raises(ReasoningError):
        validate_prose("Third-party service providers caused one billion dollars of losses.")


@pytest.mark.parametrize("text", [
    "The company removed this risk from its disclosures.",
    "A new risk emerged in the issuer's disclosures.",
    "The issuer no longer discloses cybersecurity exposure.",
])
def test_selected_excerpt_absence_does_not_prove_new_or_removed_risks(text):
    with pytest.raises(ReasoningError, match="Selected excerpts"):
        validate_prose(text)


def test_exact_provenance_does_not_override_semantic_rejection(evidence):
    altered = claim()
    altered["text"] = "A severe cyber incident occurred and disrupted the issuer's services."
    # Provenance is valid, but the quoted 'may' language does not entail this.
    assert validate_claims([altered], evidence)
    seen = []
    def reviewer(stage, **request):
        seen.append((stage, request))
        return {"verdicts": [{"claim_id": altered["claim_id"], "supported": False,
                              "reason": "Conditional risk language does not establish that an incident occurred."}], "issues": []}
    verdict = Reasoner(reviewer).critique(draft([altered]), evidence)
    assert verdict["passed"] is False
    assert verdict["semantic_review"] == "model_assisted_not_gold"
    assert seen[0][0] == "critic" and "Conditional language" in seen[0][1]["system"]


@pytest.mark.parametrize("verdicts", [[], [{"claim_id": "other", "supported": True, "reason": "Test-only reason."}],
    [{"claim_id": claim()["claim_id"], "supported": True, "reason": "Test-only reason."}] * 2])
def test_critic_cannot_skip_or_duplicate_claim_verdicts(evidence, verdicts):
    with pytest.raises(ReasoningError, match="omitted, duplicated or invented"):
        Reasoner(lambda *args, **kwargs: {"verdicts": verdicts, "issues": []}).critique(draft([claim()]), evidence)


def test_semantic_review_is_of_exact_body_and_source_not_cached_after_edit(evidence):
    calls = []
    def reviewer(stage, **request):
        calls.append(deepcopy(request["context"]))
        return {"verdicts": [{"claim_id": claim()["claim_id"], "supported": True,
                              "reason": "Test-only supported finding."}], "issues": []}
    reasoner = Reasoner(reviewer)
    original = draft([claim()])
    first = reasoner.critique(original, evidence)
    edited = {**original, "body": original["body"] + "\nA human changed the displayed wording."}
    second = reasoner.critique(edited, evidence)
    assert len(calls) == 2
    assert first["body_hash"] == sha256(original["body"].encode()).hexdigest()
    assert second["body_hash"] != first["body_hash"]
    assert second["source_fingerprint"] == original["source_fingerprint"]
    assert calls[1]["body"] == edited["body"]


def test_model_cannot_expand_plan_scope_or_add_publication_actions():
    response = {"outline": ["Inspect annual source data", "Draft cautious cited findings"],
                "caveats": ["Selected evidence is incomplete"], "tickers": ["OTHER"], "publish": True}
    with pytest.raises(ReasoningError, match="Invalid structured"):
        Reasoner(lambda *args, **kwargs: response).plan("Compare the approved issuers", ["MSFT"], [2023])


def test_risk_selection_is_bounded_and_cannot_claim_full_coverage():
    sections = {}
    for year in (2023, 2024, 2025):
        sections[year] = {"ticker": "MSFT", "year": year, "snapshot_complete": True,
                          "chunks": [{"id": f"test-{year}-{index}", "ticker": "MSFT", "year": year,
                                      "text": "Cybersecurity risk and regulatory uncertainty. " * 100} for index in range(20)]}
    calls = []
    def model(stage, **request):
        calls.append(request)
        return {"comparisons": [{"before_year": before, "after_year": after, "status": "insufficient_evidence", "findings": []}
                                for before, after in ((2023, 2024), (2024, 2025))]}
    result = Reasoner(model).compare_risks("MSFT", [2023, 2024, 2025], sections)
    assert len(calls) == 1 and calls[0]["max_output_tokens"] == 2600
    assert len(result["selected_evidence"]) == 12
    assert all(len(row["text"]) <= 1400 for row in result["selected_evidence"])
    assert result["selection"]["complete_original_section"] is False
    assert all(row["cached_chunk_count"] == 20 and row["selected_chunk_count"] == 4 for row in result["selection"]["coverage"])


def test_risk_model_must_preserve_exact_adjacent_periods(evidence):
    sections = {year: {"ticker": "MSFT", "year": year, "snapshot_complete": True,
                       "chunks": [row for row in evidence if row["ticker"] == "MSFT" and row["year"] == year]} for year in (2023, 2024)}
    response = {"comparisons": [{"before_year": 2023, "after_year": 2025, "status": "insufficient_evidence", "findings": []}]}
    with pytest.raises(ReasoningError, match="changed, omitted or repeated"):
        Reasoner(lambda *args, **kwargs: response).compare_risks("MSFT", [2023, 2024], sections)


@pytest.mark.parametrize("response_model", [PlanOutput, QueryOutput, RiskOutput, WriterOutput, CriticOutput])
def test_live_schemas_forbid_extra_fields_and_require_all_properties(response_model):
    def check(schema):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
            assert set(schema.get("required", [])) == set(schema.get("properties", {}))
        for value in schema.values():
            if isinstance(value, dict):
                check(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        check(item)
    check(response_model.model_json_schema())


def test_large_utf8_context_is_refused_before_any_provider_call():
    calls = []
    with pytest.raises(ReasoningError, match="context is too large"):
        Reasoner(lambda *args, **kwargs: calls.append(True)).research_query("अ" * 20000, "MSFT", [2023])
    assert calls == []
