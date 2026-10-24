"""Writer schema rejects Unicode numerals before authoritative prose checks."""
import re

from jsonschema import Draft202012Validator
from pydantic import ValidationError
import pytest

from desk.reasoning import (QuoteComparisonOutput, QuoteRiskRevision, QuoteWriterFinding,
                            QuoteWriterOutput, ReasoningError, WRITER_TEXT_PATTERN, validate_prose)


def finding(text):
    return {"text": text, "quote_ids": ["quote:AAPL:2024:1", "quote:AAPL:2025:2"],
            "confidence": "low", "category": "limitation"}


def revision(text):
    return {"text": text, "before_quote_id": "quote:AAPL:2024:1", "after_quote_id": "quote:AAPL:2025:2",
            "confidence": "low"}


@pytest.mark.parametrize("model,payload", [(QuoteWriterFinding, finding), (QuoteRiskRevision, revision)])
@pytest.mark.parametrize("numeral", ["2024", "२०२४", "٢٠٢٤", "২০২৪", "２０２４", "²", "Ⅳ", "½", "①"])
def test_writer_numerals_fail_pydantic_and_generated_json_schema(model, payload, numeral):
    value = payload(f"Selected disclosure for fiscal {numeral} discusses exposure.")
    with pytest.raises(ValidationError):
        model.model_validate(value)
    validator = Draft202012Validator(model.model_json_schema())
    assert not validator.is_valid(value)
    # The existing independent local guard remains unchanged and rejects it.
    with pytest.raises(ReasoningError, match="Numerical or marked-up"):
        validate_prose(value["text"])


@pytest.mark.parametrize("model,payload", [(QuoteWriterFinding, finding), (QuoteRiskRevision, revision)])
def test_runtime_bengali_fiscal_year_and_item_suffix_shape_is_rejected(model, payload):
    # Synthetic reproduction of the observed failure shape, not a saved note.
    text = "The fiscal ২০২৪ and ২০২৫ Item ১A excerpts describe natural disaster exposure."
    value = payload(text)
    with pytest.raises(ValidationError):
        model.model_validate(value)
    assert not Draft202012Validator(model.model_json_schema()).is_valid(value)


@pytest.mark.parametrize("text", [
    "Selected disclosures continue to discuss supply chain exposure.",
    "The company’s operations—and suppliers’ facilities—may face disruption.",
    'The “earlier” and “later” excerpts describe shared exposure; economic materiality remains uncertain.',
    "Research & development (R&D) may face disruption: evidence remains partial, with limited scope.",
    "The issuer's operations / facilities may be disrupted; selected evidence remains limited…",
])
@pytest.mark.parametrize("model,payload", [(QuoteWriterFinding, finding), (QuoteRiskRevision, revision)])
def test_reviewed_english_punctuation_is_accepted_by_both_schema_engines(model, payload, text):
    value = payload(text)
    assert model.model_validate(value).text == text
    assert Draft202012Validator(model.model_json_schema()).is_valid(value)
    assert validate_prose(text) == text


@pytest.mark.parametrize("text", [
    "The issuer lost two billion dollars.", "Revenue doubled across compared periods.",
])
def test_character_allowlist_does_not_replace_semantic_quantity_guard(text):
    value = finding(text)
    assert QuoteWriterFinding.model_validate(value).text == text
    assert Draft202012Validator(QuoteWriterFinding.model_json_schema()).is_valid(value)
    with pytest.raises(ReasoningError, match="quantity"):
        validate_prose(text)


def test_numeric_quote_identifiers_and_year_metadata_remain_allowed():
    text = "Selected disclosures continue to discuss supply chain exposure."
    claim = finding(text)
    risk_revision = revision(text)
    writer = {"claims": [claim], "risk_revisions": {}}
    assert QuoteWriterOutput.model_validate(writer).claims[0].quote_ids == claim["quote_ids"]
    assert Draft202012Validator(QuoteWriterOutput.model_json_schema()).is_valid(writer)
    assert QuoteRiskRevision.model_validate(risk_revision).before_quote_id.endswith("2024:1")
    risk = {"before_year": 2024, "after_year": 2025, "status": "evidence_available", "findings": [
        {key: value for key, value in claim.items() if key != "category"}]}
    assert QuoteComparisonOutput.model_validate(risk).before_year == 2024
    assert Draft202012Validator(QuoteComparisonOutput.model_json_schema()).is_valid(risk)
    # Risk response schemas are not narrowed, preserving reusable paid inputs.
    risk_pattern = QuoteComparisonOutput.model_json_schema()["$defs"]["QuoteFinding"]["properties"]["text"]
    assert "pattern" not in risk_pattern


def test_every_unicode_numeric_character_is_outside_writer_pattern():
    pattern = re.compile(WRITER_TEXT_PATTERN)
    assert all(not pattern.fullmatch(f"Selected disclosure contains {chr(code)} exposure.")
               for code in range(0x110000) if chr(code).isnumeric())
