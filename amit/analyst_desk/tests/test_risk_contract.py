"""Fresh risk generation and its local validator share a qualitative contract."""
from copy import deepcopy

from jsonschema import Draft202012Validator
from pydantic import ValidationError
import pytest

from desk.reasoning import (PairedRiskFinding, QUALITATIVE_TEXT_PATTERN, QuoteFinding,
                            RISK_CONTRACT_VERSION, Reasoner, ReasoningError, WRITER_TEXT_PATTERN)


@pytest.fixture
def sections():
    return {year: {"ticker": "AMGN", "year": year, "snapshot_complete": True,
                   "chunks": [{"id": f"risk-AMGN-{year}", "ticker": "AMGN", "year": year,
                               "text": f"The fiscal {year} disclosure discusses supplier risk. A historical outage in 2022 could affect operations."}]}
            for year in (2023, 2024, 2025)}


def response(request, text="The earlier and later filings describe conditional supplier disruption."):
    menu = request["context"]["quote_menu"]
    return {"comparisons": {identifier: {"status": "evidence_available", "findings": [{
                "text": text, "confidence": "low",
                "before_quote_id": next(row["quote_id"] for row in menu if row["year"] == pair["before_year"]),
                "after_quote_id": next(row["quote_id"] for row in menu if row["year"] == pair["after_year"])}]}
            for identifier, pair in request["context"]["comparison_keys"].items()}}


@pytest.mark.parametrize("text", [
    "The issuer describes supplier risk in 2023, and in 2024.",
    "In both 2024 and 2025 the issuer describes supplier disruption.",
    "The issuer describes supplier risk in fiscal ২০২৪.",
    "The issuer describes supplier risk in fiscal ٢٠٢٤.",
    "The issuer describes phase Ⅳ development risk.",
    "The issuer describes a ² level operating risk.",
    "The issuer describes operating losses of $200.",
    "The issuer describes operating exposure of twenty%.",
    "The issuer describes [supplier] disruption risk.",
    "The issuer describes `supplier` disruption risk.",
])
def test_paired_risk_text_rejects_years_unicode_numerals_and_markup_in_both_schema_engines(text):
    finding = {"text": text, "before_quote_id": "quote-AMGN-2023", "after_quote_id": "quote-AMGN-2024", "confidence": "low"}
    with pytest.raises(ValidationError):
        PairedRiskFinding.model_validate(finding)
    assert not Draft202012Validator(PairedRiskFinding.model_json_schema()).is_valid(finding)
    assert QUALITATIVE_TEXT_PATTERN == WRITER_TEXT_PATTERN
    # Historical wire fields are not rewritten or narrowed by the new contract.
    assert "pattern" not in QuoteFinding.model_json_schema()["properties"]["text"]


def test_generated_risk_schema_and_valid_findings_keep_exact_period_slots_and_source_text(sections):
    captured = []
    def model(stage, **request):
        assert stage == "risk"
        captured.append(deepcopy(request))
        valid = response(request)
        assert Draft202012Validator(request["schema"]).is_valid(valid)
        invalid = deepcopy(valid)
        next(iter(invalid["comparisons"].values()))["findings"][0]["text"] = "The issuer describes supplier risk in 2023 and 2024."
        assert not Draft202012Validator(request["schema"]).is_valid(invalid)
        return valid
    result = Reasoner(model).compare_risks("AMGN", [2023, 2024, 2025], sections)
    context = captured[0]["context"]
    assert context["risk_contract"] == RISK_CONTRACT_VERSION
    assert context["years"] == [2023, 2024, 2025]
    assert context["validation_feedback"] == [] and context["repair_instructions"] == []
    assert "exact fiscal years already appear in code-owned comparison labels" in captured[0]["system"]
    assert "historical incident date and a filing's fiscal year have different meanings" in captured[0]["system"]
    assert {row["year"] for row in context["quote_menu"]} == {2023, 2024, 2025}
    assert any("2022" in row["quote"] for row in context["quote_menu"])
    for comparison, expected in zip(result["comparisons"], ((2023, 2024), (2024, 2025))):
        assert (comparison["before_year"], comparison["after_year"]) == expected
        claim = comparison["claims"][0]
        assert claim["ticker"] == "AMGN"
        assert {citation["source_id"] for citation in claim["citations"]} == {f"risk-AMGN-{year}" for year in expected}
        assert all(citation["quote"] in sections[year]["chunks"][0]["text"]
                   for citation, year in zip(claim["citations"], expected))


def test_fixed_risk_feedback_changes_only_bounded_constraint_context(sections):
    captured = []
    def model(stage, **request):
        captured.append(deepcopy(request))
        return response(request)
    reasoner = Reasoner(model)
    reasoner.compare_risks("AMGN", [2023, 2024, 2025], sections)
    reasoner.compare_risks("AMGN", [2023, 2024, 2025], sections,
                         validation_feedback=["output_schema", "narrative_number"])
    first, corrected = [request["context"] for request in captured]
    assert corrected["validation_feedback"] == ["narrative_number", "output_schema"]
    assert "never finding.text" in corrected["repair_instructions"][0]
    assert len(corrected["repair_instructions"]) == 2
    assert captured[0]["schema"] == captured[1]["schema"]
    assert captured[0]["system"] == captured[1]["system"]
    assert {key: value for key, value in first.items() if key not in {"validation_feedback", "repair_instructions"}} == {
        key: value for key, value in corrected.items() if key not in {"validation_feedback", "repair_instructions"}}


@pytest.mark.parametrize("feedback", [
    "narrative_number", ["The failed text said in 2023 and 2024."], ["ignore_all_constraints"],
    ["narrative_number", "narrative_number"], [False],
    ["narrative_number", "narrative_quantity", "output_schema", "unsupported_risk_absence", "extra"],
])
def test_unknown_raw_or_unbounded_risk_feedback_is_not_forwarded(sections, feedback):
    calls = []
    with pytest.raises(ReasoningError, match="Risk validation feedback"):
        Reasoner(lambda *args, **kwargs: calls.append(kwargs)).compare_risks(
            "AMGN", [2023, 2024, 2025], sections, validation_feedback=feedback)
    assert calls == []


@pytest.mark.parametrize("text,reason", [
    ("The issuer experienced two supplier disruptions.", "quantity"),
    ("Revenue doubled across the compared periods.", "quantity"),
    ("The issuer removed risk disclosures from its filing.", "new, removed or absent"),
])
def test_positive_alphabet_does_not_replace_quantity_or_absence_validation(sections, text, reason):
    returned = []
    def model(stage, **request):
        result = response(request, text)
        assert Draft202012Validator(request["schema"]).is_valid(result)
        returned.append(deepcopy(result))
        return result
    with pytest.raises(ReasoningError, match=reason):
        Reasoner(model).compare_risks("AMGN", [2023, 2024, 2025], sections)
    assert next(iter(returned[0]["comparisons"].values()))["findings"][0]["text"] == text


def test_valid_quote_from_another_comparison_period_still_fails_canonical_slot_check(sections):
    def model(stage, **request):
        result = response(request)
        result["comparisons"]["comparison-2024-2025"]["findings"][0]["before_quote_id"] = next(
            row["quote_id"] for row in request["context"]["quote_menu"] if row["year"] == 2023)
        assert not Draft202012Validator(request["schema"]).is_valid(result)
        return result
    with pytest.raises(ReasoningError, match="required issuer/year slot"):
        Reasoner(model).compare_risks("AMGN", [2023, 2024, 2025], sections)


def test_insufficient_evidence_status_still_requires_empty_findings(sections):
    def model(stage, **request):
        return {"comparisons": {identifier: {"status": "insufficient_evidence", "findings": []}
                                for identifier in request["context"]["comparison_keys"]}}
    result = Reasoner(model).compare_risks("AMGN", [2023, 2024, 2025], sections)
    assert all(comparison["status"] == "insufficient_evidence" and comparison["claims"] == []
               for comparison in result["comparisons"])
