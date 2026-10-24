"""Grounding and live-reasoning control tests; no paid provider calls."""
from copy import deepcopy
from hashlib import sha256

import pytest
from jsonschema import Draft202012Validator

from desk.reasoning import (ANNUAL_SCOPE_NOTICE, CriticOutput, PlanOutput, QueryOutput, QuoteRiskOutput,
                            QuoteWriterOutput, Reasoner, ReasoningError, RiskOutput, WriterOutput,
                            normalize_evidence, quote_menu, render_claims, validate_claims,
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


def test_planner_receives_reported_annual_periods_and_mandatory_scope_notice():
    coverage = {"annual_financial_inputs_complete": True, "risk_original_sections_complete": False,
                "annual_periods": [{"ticker": "MSFT", "fiscal_year": 2025,
                    "period_start": "2024-07-01", "period_end": "2025-06-30",
                    "revenue_fact_id": "annual-revenue", "operating_income_fact_id": "annual-income"}]}
    seen = []
    def model(stage, **request):
        seen.append(request)
        return {"outline": ["Inspect reported annual inputs", "Compare checked margins and disclosures"],
                "caveats": ["Issuer fiscal calendars differ."]}
    plan = Reasoner(model).plan("Compare annual results", ["MSFT"], [2025], source_coverage=coverage)
    assert seen[0]["context"]["source_coverage"] == coverage
    assert "not a future, estimated, partial-year or unavailable financial result" in seen[0]["system"]
    assert "Do not introduce 10-Q" in seen[0]["system"]
    assert plan["source_coverage"] == coverage and plan["caveats"][0] == ANNUAL_SCOPE_NOTICE
    assert "Risk excerpts remain partial" in plan["caveats"][0]


def test_incomplete_or_mismatched_planning_coverage_fails_before_model_call():
    calls = []
    reasoner = Reasoner(lambda *args, **kwargs: calls.append(True))
    for coverage in ({"annual_financial_inputs_complete": False, "annual_periods": []},
                     {"annual_financial_inputs_complete": True,
                      "annual_periods": [{"ticker": "MSFT", "fiscal_year": 2024}]}):
        with pytest.raises(ReasoningError, match="exact requested scope"):
            reasoner.plan("Compare annual results", ["MSFT"], [2025], source_coverage=coverage)
    assert calls == []


def test_model_cannot_replace_code_owned_source_coverage():
    coverage = {"annual_financial_inputs_complete": True,
                "annual_periods": [{"ticker": "MSFT", "fiscal_year": 2025}]}
    response = {"outline": ["Inspect annual inputs", "Check source periods"], "caveats": ["A source caveat."],
                "source_coverage": {"annual_financial_inputs_complete": False}}
    with pytest.raises(ReasoningError, match="Invalid structured"):
        Reasoner(lambda *args, **kwargs: response).plan("Compare annual results", ["MSFT"], [2025], source_coverage=coverage)


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


@pytest.mark.parametrize("response_model", [PlanOutput, QueryOutput, RiskOutput, WriterOutput, QuoteRiskOutput, QuoteWriterOutput, CriticOutput])
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


def test_quote_menu_is_exact_bounded_stable_and_source_bound(evidence):
    rows = evidence + [{**evidence[0], "id": "same-wording-later", "year": 2025}]
    menu = quote_menu(rows)
    assert menu == quote_menu(list(reversed(rows)))
    for item in menu:
        source = next(row for row in rows if row["id"] == item["source_id"])
        assert source["text"][item["start"]:item["end"]] == item["quote"]
        assert 12 <= len(item["quote"]) <= 240
        assert item["ticker"] == source["ticker"] and item["year"] == source["year"]
    assert all(sum(item["source_id"] == row["id"] for item in menu) <= 2 for row in rows)
    assert len({item["quote_id"] for item in menu}) == len(menu)
    original = quote_menu([evidence[0]])
    changed = quote_menu([{**evidence[0], "text": evidence[0]["text"] + " Changed source context."}])
    assert {item["quote_id"] for item in original}.isdisjoint(item["quote_id"] for item in changed)


def test_quote_menu_keeps_short_sentence_modality_and_marks_long_fragments():
    text = "The issuer may not withstand cyber attacks. " + "Supply uncertainty and operational risk " * 30 + "."
    menu = quote_menu([{"id": "long-source", "ticker": "MSFT", "year": 2025, "text": text}])
    assert len(menu) == 2 and any(item["fragment"] for item in menu)
    assert all(item["quote"] in text and len(item["quote"]) <= 240 for item in menu)
    short = quote_menu([{"id": "conditional", "ticker": "MSFT", "year": 2025,
                         "text": "The issuer may not withstand cyber attacks."}])
    assert short[0]["quote"] == "The issuer may not withstand cyber attacks."
    assert short[0]["fragment"] is False


def risk_sections(evidence):
    return {year: {"ticker": "MSFT", "year": year, "snapshot_complete": True,
                   "chunks": [row for row in evidence if row["ticker"] == "MSFT" and row["year"] == year]}
            for year in (2023, 2024)}


def test_risk_model_selects_finite_quotes_and_code_expands_exact_citations(evidence):
    seen = []
    def model(stage, **request):
        seen.append(request)
        menu = request["context"]["quote_menu"]
        selected = [next(item["quote_id"] for item in menu if item["year"] == year) for year in (2023, 2024)]
        enum = request["schema"]["$defs"]["QuoteFinding"]["properties"]["quote_ids"]["items"]["enum"]
        assert enum == [item["quote_id"] for item in menu]
        assert "citations" not in request["schema"]["$defs"]["QuoteFinding"]["properties"]
        return {"comparisons": [{"before_year": 2023, "after_year": 2024, "status": "evidence_available",
            "findings": [{"text": "Cybersecurity remains a disclosed operational exposure.", "confidence": "low", "quote_ids": selected}]}]}
    result = Reasoner(model).compare_risks("MSFT", [2023, 2024], risk_sections(evidence))
    finding = result["comparisons"][0]["claims"][0]
    assert "quote_ids" not in finding and len(finding["citations"]) == 2
    assert validate_claims([finding], result["selected_evidence"])
    assert "evidence" not in seen[0]["context"]
    assert "Code-selected quote windows" in seen[0]["context"]["evidence_scope"]
    assert result["selection"]["quotation_selection"] == "code_selected_exact_windows"


@pytest.mark.parametrize("selection", ["invented", "duplicate", "wrong-period", "freeform"])
def test_invalid_quote_choices_or_freeform_citations_cannot_be_repaired(evidence, selection):
    def model(stage, **request):
        menu = request["context"]["quote_menu"]
        before = next(item for item in menu if item["year"] == 2023)
        after = next(item for item in menu if item["year"] == 2024)
        choices = {"invented": [before["quote_id"], "fabricated-quote"],
                   "duplicate": [before["quote_id"], before["quote_id"]],
                   "wrong-period": [before["quote_id"]],
                   "freeform": [before["quote_id"], after["quote_id"]]}[selection]
        finding = {"text": "Cybersecurity remains a disclosed operational exposure.", "confidence": "low", "quote_ids": choices}
        if selection == "freeform":
            finding["citations"] = [{"source_id": "invented-source", "quote": "An invented model quotation."}]
        return {"comparisons": [{"before_year": 2023, "after_year": 2024, "status": "evidence_available", "findings": [finding]}]}
    with pytest.raises(ReasoningError):
        Reasoner(model).compare_risks("MSFT", [2023, 2024], risk_sections(evidence))


def test_writer_uses_finite_quotes_but_cannot_repeat_a_source(evidence):
    seen = []
    def model(stage, **request):
        seen.append(request)
        menu = request["context"]["quote_menu"]
        return {"claims": [{"text": "Selected source excerpts provide limited disclosure context.", "confidence": "low",
                            "category": "limitation", "quote_ids": [menu[0]["quote_id"]]}]}
    result = Reasoner(model).write("Compare annual sources", {}, [], [], evidence)
    claim = result["claims"][0]
    assert claim["citations"] == [{"source_id": seen[0]["context"]["quote_menu"][0]["source_id"],
                                   "quote": seen[0]["context"]["quote_menu"][0]["quote"]}]
    assert result["evidence"] == normalize_evidence(evidence)
    assert "evidence" not in seen[0]["context"]
    def duplicate_source(stage, **request):
        choices = [item["quote_id"] for item in request["context"]["quote_menu"] if item["source_id"] == "msft-before"]
        assert len(choices) == 2
        return {"claims": [{"text": "Selected source excerpts provide limited disclosure context.", "confidence": "low",
                            "category": "limitation", "quote_ids": choices}]}
    with pytest.raises(ReasoningError, match="Repeat citations"):
        Reasoner(duplicate_source).write("Compare annual sources", {}, [], [], evidence)


def test_writer_unknown_quote_id_is_rejected_and_not_silently_replaced(evidence):
    response = {"claims": [{"text": "Selected source excerpts provide limited disclosure context.", "confidence": "low",
                            "category": "limitation", "quote_ids": ["invented-quote"]}]}
    with pytest.raises(ReasoningError, match="unknown or repeated"):
        Reasoner(lambda *args, **kwargs: response).write("Compare annual sources", {}, [], [], evidence)


def test_writer_wire_schema_excludes_date_digits_without_changing_risk_schema(evidence):
    captured = []
    def model(stage, **request):
        captured.append(request)
        content = {"claims": [{"text": "Selected source excerpts provide limited disclosure context.",
            "confidence": "low", "category": "limitation",
            "quote_ids": [request["context"]["quote_menu"][0]["quote_id"]]}]}
        validator = Draft202012Validator(request["schema"])
        assert validator.is_valid(content)
        dated = deepcopy(content)
        dated["claims"][0]["text"] = "Selected disclosures discuss operational risks in June 2025."
        assert not validator.is_valid(dated)
        return content
    Reasoner(model).write("Compare annual sources", {}, [], [], evidence)
    writer_text = captured[0]["schema"]["$defs"]["QuoteWriterFinding"]["properties"]["text"]
    assert "pattern" in writer_text
    assert "pattern" not in QuoteRiskOutput.model_json_schema()["$defs"]["QuoteFinding"]["properties"]["text"]
    assert "Calendar dates and fiscal-year numbers" in captured[0]["system"]
    assert "across the compared periods" in captured[0]["system"]


@pytest.mark.parametrize("text", [
    "The issuer reiterated operational exposure in June 30 2024.",
    "The issuer reiterated operational exposure in fiscal 2025.",
    "The issuer reiterated operational exposure.\nAnother claim follows.",
    "The issuer reiterated **operational exposure** in its disclosures.",
])
def test_writer_rejects_dated_or_marked_up_output_without_rewriting_it(evidence, text):
    content = {"claims": [{"text": text, "confidence": "low", "category": "limitation",
                           "quote_ids": [quote_menu(evidence)[0]["quote_id"]]}]}
    original = deepcopy(content)
    with pytest.raises(ReasoningError, match="Invalid structured model output for writer"):
        Reasoner(lambda *args, **kwargs: content).write("Compare annual sources", {}, [], [], evidence)
    assert content == original


@pytest.mark.parametrize("text", [
    "The issuer reported ١٢ security incidents during the period.",
    "The issuer incurred one billion dollars in operational losses.",
])
def test_writer_schema_does_not_replace_full_local_quantity_validation(evidence, text):
    content = {"claims": [{"text": text, "confidence": "low", "category": "limitation",
                           "quote_ids": [quote_menu(evidence)[0]["quote_id"]]}]}
    with pytest.raises(ReasoningError):
        Reasoner(lambda *args, **kwargs: content).write("Compare annual sources", {}, [], [], evidence)


def test_qualitative_writer_claim_keeps_exact_provenance_through_critic(evidence):
    seen = []
    def model(stage, **request):
        seen.append((stage, request))
        if stage == "writer":
            selected = next(item for item in request["context"]["quote_menu"]
                            if item["source_id"] == "msft-before" and "may interrupt" in item["quote"])
            return {"claims": [{"text": "Conditional risk language describes potential operational disruption.",
                "confidence": "low", "category": "risk_observation", "quote_ids": [selected["quote_id"]]}]}
        assert stage == "critic"
        assert request["context"]["claims"][0]["citations"][0]["quote"] in evidence[0]["text"]
        return {"issues": [], "verdicts": [{"claim_id": "writer-1", "supported": True,
                                            "reason": "Fictional test review of the retained conditional source language."}]}
    reasoner = Reasoner(model)
    written = reasoner.write("Compare annual sources", {}, [], [], evidence)
    current = draft(written["claims"])
    verdict = reasoner.critique(current, written["evidence"])
    assert verdict["passed"] is True and verdict["semantic_review"] == "model_assisted_not_gold"
    assert seen[-1][1]["context"]["body"] == current["body"]
    assert written["claims"][0]["text"] == "Conditional risk language describes potential operational disruption."


def test_critic_keeps_full_cited_context_and_financial_facts_without_uncited_bulk(evidence):
    financial = {"id": "financial-table-fact", "ticker": "MSFT", "year": 2025,
                 "text": "A code-canonical financial-table fact with its actual annual period."}
    irrelevant = {"id": "uncited-bulk", "ticker": "AAPL", "year": 2025, "text": "Uncited source text. " * 4000}
    seen = []
    def reviewer(stage, **request):
        seen.append(request["context"])
        return {"issues": [], "verdicts": [{"claim_id": claim()["claim_id"], "supported": False,
                    "reason": "The full source retains conditional language, not an established incident."}]}
    current = {**draft([claim()]), "metrics": [{"fact_ids": [financial["id"]]}]}
    verdict = Reasoner(reviewer).critique(current, evidence + [financial, irrelevant])
    assert verdict["passed"] is False
    reviewed = {row["id"]: row for row in seen[0]["evidence"]}
    assert set(reviewed) == {"msft-before", "msft-after", financial["id"]}
    assert reviewed["msft-before"]["text"] == evidence[0]["text"]
    assert "may interrupt" in reviewed["msft-before"]["text"]
    assert seen[0]["claims"] == [claim()] and seen[0]["body"] == current["body"]
    assert seen[0]["omitted_uncited_source_count"] == 2


def test_critic_still_validates_all_claim_provenance_before_filtering(evidence):
    bad = claim()
    bad["citations"][0]["quote"] = "A quotation not in the original source."
    calls = []
    with pytest.raises(ReasoningError, match="quote is not"):
        Reasoner(lambda *args, **kwargs: calls.append(True)).critique(draft([bad]), evidence)
    assert calls == []


def test_temporal_pair_idiom_requires_scoped_distinct_cited_periods(evidence):
    text = "General source disclosures remain consistent between the two years."
    with pytest.raises(ReasoningError, match="quantity"):
        validate_prose(text)
    assert validate_prose(text, comparison_periods=(2023, 2024)) == text
    for periods in ((2023, 2023), (True, 2024), (2023,), None):
        with pytest.raises(ReasoningError, match="quantity"):
            validate_prose(text, comparison_periods=periods)
    value = claim()
    value["text"] = text
    assert validate_claims([value], evidence)[0]["text"] == text
    value["citations"] = value["citations"][:1]
    with pytest.raises(ReasoningError, match="both required years"):
        validate_claims([value], evidence)


@pytest.mark.parametrize("text", [
    "Revenue doubled between the two years.",
    "The issuer lost two billion dollars between the two years.",
    "The disruption lasted two years.",
])
def test_temporal_idiom_cannot_exempt_financial_quantities_or_durations(text):
    with pytest.raises(ReasoningError, match="quantity"):
        validate_prose(text, comparison_periods=(2023, 2024))
