"""Temporal-scope regression checks on synthetic sources and cached fake models."""
from copy import deepcopy

import pytest

from desk.reasoning import ReasoningError, validate_claims, validate_prose
from test_live_workflow import FakeModelClient, begin_live
from test_workflow import fixture, decide


SAFE_LIMITATION = ("Evidence is insufficient to determine whether the scope or framing of natural disaster "
                   "risk disclosures has materially changed between the two periods.")


def evidence():
    return [
        {"id": "test-aapl-before", "ticker": "AAPL", "year": 2024,
         "text": "Synthetic source: facilities may be exposed to natural disasters."},
        {"id": "test-aapl-after", "ticker": "AAPL", "year": 2025,
         "text": "Synthetic source: facilities and retail stores may be exposed to natural disasters."},
    ]


def summary(rows=None, text=SAFE_LIMITATION):
    rows = evidence() if rows is None else rows
    return {"claim_id": "writer-3", "category": "limitation", "confidence": "low", "text": text,
            "citations": [{"source_id": row["id"], "quote": row["text"]} for row in rows]}


@pytest.mark.parametrize("idiom", ["between the two periods", "between the two years",
                                  "between two periods", "between two years"])
def test_summary_temporal_pair_is_verified_from_canonical_citations(idiom):
    value = summary(text=SAFE_LIMITATION.replace("between the two periods", idiom))
    assert validate_claims([value], evidence()) == [value]
    # No context-free exception was added to the prose validator.
    with pytest.raises(ReasoningError, match="quantity"):
        validate_prose(value["text"])


@pytest.mark.parametrize("scope", ["single_year", "same_year_records", "mixed_issuers", "three_years"])
def test_summary_needs_one_issuer_and_exactly_two_distinct_canonical_years(scope):
    rows = evidence()
    if scope == "single_year":
        rows = rows[:1]
    elif scope == "same_year_records":
        rows[1]["year"] = rows[0]["year"]
    elif scope == "mixed_issuers":
        rows[1]["ticker"] = "MSFT"
    else:
        rows.append({**rows[1], "id": "test-aapl-extra", "year": 2023})
    with pytest.raises(ReasoningError, match="quantity"):
        validate_claims([summary(rows)], rows)


@pytest.mark.parametrize("year", [True, "2025", None])
def test_invalid_source_year_cannot_authorize_the_temporal_idiom(year):
    rows = evidence()
    rows[1]["year"] = year
    with pytest.raises(ReasoningError, match="Evidence records"):
        validate_claims([summary(rows)], rows)


@pytest.mark.parametrize("mutation", ["unknown_id", "fabricated_quote", "duplicate_source"])
def test_canonical_provenance_is_checked_before_temporal_inference(mutation):
    value = summary()
    if mutation == "unknown_id":
        value["citations"][1]["source_id"] = "invented-source"
    elif mutation == "fabricated_quote":
        value["citations"][1]["quote"] = "A quotation which is not in the source."
    else:
        value["citations"][1] = deepcopy(value["citations"][0])
    with pytest.raises(ReasoningError, match="unknown|quote is not|Repeat citations"):
        validate_claims([value], evidence())


@pytest.mark.parametrize("text", [
    "The issuer lost two billion dollars between the two periods.",
    "Revenue doubled between the two periods.",
    "The disruption lasted two years.",
    "The disruption lasted two years between the two periods.",
    "There were two disasters between the two periods.",
    "The issuer lost one billion dollars between the two years.",
    "Evidence is insufficient to assess changes between the three periods.",
])
def test_verified_temporal_pair_does_not_exempt_quantities_or_durations(text):
    with pytest.raises(ReasoningError, match="quantity"):
        validate_claims([summary(text=text)], evidence())


@pytest.mark.parametrize("text", [
    "Revenue rose 20 percent between the two periods.",
    "The source [markup] describes exposure between the two periods.",
])
def test_verified_periods_do_not_exempt_numeric_or_marked_up_prose(text):
    with pytest.raises(ReasoningError, match="Numerical or marked-up"):
        validate_claims([summary(text=text)], evidence())


@pytest.mark.parametrize("mutation", [None, "wrong_year", "wrong_issuer", "single_citation", "incomplete_scope"])
def test_explicit_risk_scope_still_requires_its_own_exact_period_pair(mutation):
    value = {**summary(), "ticker": "AAPL", "before_year": 2024, "after_year": 2025}
    if mutation == "wrong_year":
        value["after_year"] = 2023
    elif mutation == "wrong_issuer":
        value["ticker"] = "MSFT"
    elif mutation == "single_citation":
        value["citations"] = value["citations"][:1]
    elif mutation == "incomplete_scope":
        value.pop("before_year")
    if mutation is None:
        assert validate_claims([value], evidence()) == [value]
    else:
        with pytest.raises(ReasoningError, match="both required years|both fiscal periods"):
            validate_claims([value], evidence())


def test_fixed_local_guard_reuses_cached_writer_without_changing_paid_request(fixture, monkeypatch):
    """An invented old-checker failure resumes using the exact cached fake response."""
    from desk import reasoning
    engine, store, _, _, _, _ = fixture

    class TemporalWriter(FakeModelClient):
        def __init__(self):
            super().__init__()
            self.writer_requests = []

        def complete(self, **request):
            if request["role"] == "writer":
                self.writer_requests.append(deepcopy(request))
            result = super().complete(**request)
            if request["role"] == "writer":
                import json
                context = json.loads(request["messages"][-1]["content"])
                options = [next(row["quote_id"] for row in context["quote_menu"]
                                if row["ticker"] == "MSFT" and row["year"] == year) for year in (2023, 2024)]
                result["content"]["claims"] = [{"text": SAFE_LIMITATION, "quote_ids": options,
                                               "confidence": "low", "category": "limitation"}]
                self.cache[request["call_id"]] = deepcopy(result)
            return result

    engine.model_client = TemporalWriter()
    fixed_validator = reasoning.validate_claims

    def previous_guard(claims, known):
        if any(value.get("text") == SAFE_LIMITATION and "ticker" not in value for value in claims):
            raise ReasoningError("A narrative quantity needs a code-verified financial assertion.")
        return fixed_validator(claims, known)

    monkeypatch.setattr(reasoning, "validate_claims", previous_guard)
    plan = begin_live(engine, store)
    failed = decide(engine, plan)
    assert failed["status"] == "error" and failed["failure_kind"] == "content_validation"
    assert failed["usage"]["model_calls"] == 6 and not failed["usage"]["model_reservations"]
    original_calls = deepcopy(failed["usage"]["calls"])
    monkeypatch.setattr(reasoning, "validate_claims", fixed_validator)
    engine.claim_continuation(failed["id"], plan["pending"]["payload_hash"])
    note = engine.execute(failed["id"])
    assert note["status"] == "awaiting_note", note.get("error")
    assert note["critic"]["passed"] and note["usage"]["model_calls"] == 7
    assert note["usage"]["calls"][:6] == original_calls
    assert engine.model_client.writer_requests[0] == engine.model_client.writer_requests[1]
    assert len([call for call in engine.model_client.calls if call["role"] == "writer"]) == 1
    assert len([call for call in engine.model_client.calls if call["role"] == "critic"]) == 1
    assert note["plan"] == plan["plan"] and store.notes() == []
