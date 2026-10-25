"""Human citation changes stay within existing approved evidence slots."""
from copy import deepcopy

import pytest

from desk.reasoning import quote_menu
from desk.store import canonical_hash
from desk.workflow import (ReviewError, citation_review_options, edited_live_claims,
                           live_body, verify_draft)
from test_live_workflow import FakeModelClient, begin_live
from test_workflow import fixture, decide


def draft_fixture():
    rows = [
        {"id": "selected:AAPL:2024:privacy", "ticker": "AAPL", "year": 2024,
         "text": "Selected privacy disclosure describes regulatory uncertainty."},
        {"id": "selected:AAPL:2025:privacy", "ticker": "AAPL", "year": 2025,
         "text": "Selected privacy disclosure describes regulatory uncertainty."},
        {"id": "selected:AAPL:2024:disaster", "ticker": "AAPL", "year": 2024,
         "text": "Operations and facilities may face natural disaster exposure."},
        {"id": "selected:AAPL:2025:disaster", "ticker": "AAPL", "year": 2025,
         "text": "Operations, retail stores and facilities may face natural disaster exposure."},
    ]
    menu = quote_menu(rows)
    citations = [{"source_id": row["source_id"], "quote": row["quote"]} for row in menu if row["source_id"].endswith("privacy")]
    claim = {"claim_id": "risk-AAPL", "ticker": "AAPL", "before_year": 2024, "after_year": 2025,
             "category": "risk_observation", "confidence": "low", "text": "Selected excerpts mention privacy-related regulation.", "citations": citations}
    draft = {"plan": {"tickers": ["AAPL"], "years": [2024, 2025]}, "ai_evidence": rows,
             "narrative_claims": [claim], "live_sections": {"risk_ids": ["risk-AAPL"], "writer_ids": []},
             "numeric_table": "| Canonical verified financial table |", "history_sentence": "Analyst memory is off for this research.",
             "model_mode": "live"}
    draft["body"] = live_body(draft)
    return draft


def selected_change(draft):
    menu = citation_review_options(draft)
    claim = menu["claims"][0]
    selections = {claim["claim_id"]: [next(row["quote_id"] for row in slot["options"]
        if row["source_id"].endswith("disaster")) for slot in claim["slots"]]}
    claims = deepcopy(draft["narrative_claims"])
    claims[0]["text"] = "The later selected quotation explicitly mentions retail stores; the earlier quotation mentions operations and facilities."
    for slot, chosen in zip(claims[0]["citations"], selections[claim["claim_id"]]):
        row = next(row for options in claim["slots"] for row in options["options"] if row["quote_id"] == chosen)
        slot.update(source_id=row["source_id"], quote=row["quote"])
    return live_body({**draft, "narrative_claims": claims}), selections, claims


def test_read_only_options_bind_exact_draft_and_existing_issuer_year_slots():
    draft = draft_fixture()
    before = deepcopy(draft)
    menu = citation_review_options(draft)
    assert menu["draft_hash"] == canonical_hash(draft) and draft == before
    assert [item["claim_id"] for item in menu["claims"]] == ["risk-AAPL"]
    for slot in menu["claims"][0]["slots"]:
        assert slot["current"]["quote_id"]
        assert all(row["ticker"] == slot["ticker"] and row["year"] == slot["year"] for row in slot["options"])
        assert all(row["quote"] in next(source["text"] for source in draft["ai_evidence"] if source["id"] == row["source_id"])
                   for row in slot["options"])
    menu["claims"][0]["slots"][0]["options"][0]["quote"] = "Tampered response copy."
    assert draft == before and citation_review_options(draft)["claims"][0]["slots"][0]["options"][0]["quote"] != "Tampered response copy."


def test_selected_change_replaces_citations_and_keeps_all_claim_metadata():
    draft = draft_fixture()
    body, selections, expected = selected_change(draft)
    before = deepcopy(draft)
    changed = edited_live_claims(draft, body, selections)
    assert changed == expected and draft == before
    for key in ("claim_id", "ticker", "before_year", "after_year", "category", "confidence"):
        assert changed[0][key] == draft["narrative_claims"][0][key]
    assert [row["source_id"] for row in changed[0]["citations"]] == [
        "selected:AAPL:2024:disaster", "selected:AAPL:2025:disaster"]


@pytest.mark.parametrize("mutation", ["unknown_claim", "unknown_quote", "wrong_year", "wrong_issuer", "missing_slot",
    "extra_slot", "duplicate_quote", "string_list", "null_list", "null_quote", "map_list", "stale_quote"])
def test_invalid_or_out_of_slot_selection_is_rejected_without_mutation(mutation):
    draft = draft_fixture()
    body, selection, _ = selected_change(draft)
    before = deepcopy(draft)
    if mutation == "unknown_claim":
        selection["invented"] = selection.pop("risk-AAPL")
    elif mutation == "unknown_quote":
        selection["risk-AAPL"][0] = "quote-unknown"
    elif mutation == "wrong_year":
        selection["risk-AAPL"] = selection["risk-AAPL"][::-1]
    elif mutation == "wrong_issuer":
        alien = {"id": "selected:MSFT:2024:disaster", "ticker": "MSFT", "year": 2024, "text": "Other issuer operations face natural disasters."}
        selection["risk-AAPL"][0] = quote_menu([alien])[0]["quote_id"]
    elif mutation == "missing_slot":
        selection["risk-AAPL"].pop()
    elif mutation == "extra_slot":
        selection["risk-AAPL"].append("quote-unknown")
    elif mutation == "duplicate_quote":
        selection["risk-AAPL"][1] = selection["risk-AAPL"][0]
    elif mutation == "string_list":
        selection["risk-AAPL"] = "quote-unknown"
    elif mutation == "null_list":
        selection["risk-AAPL"] = None
    elif mutation == "null_quote":
        selection["risk-AAPL"][0] = None
    elif mutation == "map_list":
        selection = []
    else:
        old = {**draft["ai_evidence"][2], "text": "An older source window describes changed disaster exposure."}
        selection["risk-AAPL"][0] = quote_menu([old])[0]["quote_id"]
    with pytest.raises(ValueError):
        edited_live_claims(draft, body, selection)
    assert draft == before


@pytest.mark.parametrize("mutation", ["table", "heading", "limits", "added_claim", "removed_claim", "old_suffix", "number", "markup"])
def test_citation_change_cannot_tamper_with_body_structure_or_prose(mutation):
    draft = draft_fixture()
    body, selection, _ = selected_change(draft)
    if mutation == "table":
        body = body.replace("Canonical verified financial table", "Fabricated financial table")
    elif mutation == "heading":
        body = body.replace("## AI research summary", "## New heading")
    elif mutation == "limits":
        body = body.replace("Selected risk excerpts are partial", "Selected risk excerpts are complete")
    elif mutation == "added_claim":
        body += "\n- An extra invented claim."
    elif mutation == "removed_claim":
        body = "\n".join(line for line in body.splitlines() if not line.startswith("- "))
    elif mutation == "old_suffix":
        body = draft["body"]
    elif mutation == "number":
        body = body.replace("The later selected quotation", "The 2025 selected quotation")
    else:
        body = body.replace("retail stores", "[retail stores]")
    with pytest.raises(ValueError):
        edited_live_claims(draft, body, selection)


def test_legacy_body_only_edit_remains_compatible_and_keeps_evidence():
    draft = draft_fixture()
    body = draft["body"].replace("Selected excerpts mention privacy-related regulation.", "Selected privacy excerpts discuss regulatory obligations.")
    result = edited_live_claims(draft, body)
    assert result[0]["text"] == "Selected privacy excerpts discuss regulatory obligations."
    assert result[0]["citations"] == draft["narrative_claims"][0]["citations"]


def test_quote_not_in_menu_can_be_left_unchanged_without_a_selection_sentinel():
    draft = draft_fixture()
    draft["narrative_claims"][0]["citations"][0]["quote"] = "privacy disclosure describes regulatory"
    draft["body"] = live_body(draft)
    assert citation_review_options(draft)["claims"][0]["slots"][0]["current"]["quote_id"] is None
    assert edited_live_claims(draft, draft["body"], {}) == draft["narrative_claims"]


def test_options_reject_outside_approved_evidence_scope():
    draft = draft_fixture()
    draft["ai_evidence"].append({"id": "foreign", "ticker": "MSFT", "year": 2024, "text": "Outside scope selected source evidence."})
    with pytest.raises(ValueError, match="approved evidence scope"):
        citation_review_options(draft)


@pytest.mark.parametrize("mutation", ["quote", "body", "malformed", "stale_hash"])
def test_engine_rejects_invalid_citation_edit_before_queue_or_event_mutation(fixture, mutation):
    engine, store, _, _, _, _ = fixture
    engine.model_client = FakeModelClient()
    note = decide(engine, begin_live(engine, store))
    option = citation_review_options(note["draft"])["claims"][0]
    selected = {option["claim_id"]: [slot["current"]["quote_id"] for slot in option["slots"]]}
    edits = {"body": note["draft"]["body"], "citation_selections": selected}
    version = note["pending"]["payload_hash"]
    if mutation == "quote":
        edits["citation_selections"][option["claim_id"]][0] = "quote-unknown"
    elif mutation == "body":
        edits["body"] += "\nAn unverified conclusion."
    elif mutation == "malformed":
        edits["citation_selections"] = None
    else:
        version = "0" * 64
    before, events, calls = deepcopy(store.get_run(note["id"])), deepcopy(store.events(note["id"])), len(engine.model_client.calls)
    with pytest.raises(ReviewError):
        engine.claim(note["id"], {"kind": "note", "action": "edit", "payload_hash": version, "edits": edits})
    assert store.get_run(note["id"]) == before and store.events(note["id"]) == events
    assert len(engine.model_client.calls) == calls and store.notes() == []


def test_valid_citation_edit_invalidates_verdict_and_runs_only_fresh_critic(fixture):
    engine, store, source, _, _, _ = fixture
    engine.model_client = FakeModelClient()
    note = decide(engine, begin_live(engine, store))
    draft = note["draft"]
    options = citation_review_options(draft)["claims"][0]
    selected_rows = [next((row for row in slot["options"] if row["quote_id"] != slot["current"]["quote_id"]), slot["options"][0])
                     for slot in options["slots"]]
    claims = deepcopy(draft["narrative_claims"])
    target = next(claim for claim in claims if claim["claim_id"] == options["claim_id"])
    target["text"] = "Selected supplied source excerpts provide limited evidence."
    target["citations"] = [{"source_id": row["source_id"], "quote": row["quote"]} for row in selected_rows]
    body = live_body({**draft, "narrative_claims": claims})
    selection = {options["claim_id"]: [row["quote_id"] for row in selected_rows]}
    old_model_calls = len(engine.model_client.calls)
    changed = decide(engine, note, "edit", {"body": body, "citation_selections": selection})
    assert changed["status"] == "awaiting_note", changed.get("error")
    assert changed["critic"]["passed"] and len(engine.model_client.calls) == old_model_calls + 1
    assert engine.model_client.calls[-1]["role"] == "critic"
    assert changed["draft"]["narrative_claims"] == claims and "citation_selections" not in changed["draft"]
    assert changed["pending"]["payload_hash"] != note["pending"]["payload_hash"]
    assert changed["draft"]["semantic_verdict"]["body_hash"] != draft["semantic_verdict"]["body_hash"]
    assert verify_draft(changed["draft"], source)["passed"]
    assert len([event for event in store.events(note["id"]) if event["stage"] == "note_edit"]) == 1
    assert store.notes() == []
