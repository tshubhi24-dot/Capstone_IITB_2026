"""Strict, offline source-review decisions; all records below are synthetic."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk.finance import edgar as edgar
from analystdesk.finance import source_review as source_review
from analystdesk.governance.review_snapshot import SnapshotError
from analystdesk.governance.review_snapshot import capture
from analystdesk.servers import edgar_server
from tests.unit.test_edgar import FAKE_FACTS
from tests.unit.test_edgar import MSFT_CIK
from tests.integration.test_tools import call

CONCEPT = "RevenueFromContractWithCustomerExcludingAssessedTax"
ORIGINAL = FAKE_FACTS["facts"]["us-gaap"][CONCEPT]["units"]["USD"][0]
LATER = {**ORIGINAL, "val": 215000000000, "accn": "0000789019-24-000007",
         "filed": "2024-07-30", "form": "10-K/A"}


def record(entry, decision):
    return {"ticker": "MSFT", "fiscal_year": 2023, "concept": CONCEPT, "accession": entry["accn"],
            "period_start": entry["start"], "period_end": entry["end"], "filed": entry["filed"],
            "form": entry["form"], "value_usd": entry["val"], "decision": decision,
            "reviewer": "test reviewer", "reviewed_at": "2025-01-01",
            "evidence": "synthetic issuer review", "rationale": "synthetic test"}


class SourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "review.json"
        self.env = patch.dict("os.environ", {"SOURCE_REVIEW_FILE": str(self.path)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.facts = copy.deepcopy(FAKE_FACTS)
        self.facts["facts"]["us-gaap"][CONCEPT]["units"]["USD"].append(LATER)
        self.fetch = patch('analystdesk.finance.edgar.fetch_company_facts', return_value=self.facts)
        self.fetch.start()
        self.addCleanup(self.fetch.stop)

    def register(self, decisions):
        self.path.write_text(json.dumps({"version": 1, "decisions": decisions}), encoding="utf-8")

    def test_excluded_original_and_reviewed_replacement_across_tool_paths(self):
        self.register([record(ORIGINAL, "excluded"), record(LATER, "eligible")])
        selected = edgar.get_annual_fact(MSFT_CIK, CONCEPT, 2023)
        self.assertEqual(selected["accn"], LATER["accn"])
        self.assertEqual(selected["eligibility"], "eligible")
        self.assertEqual(selected["source_review"]["reviewer"], "test reviewer")
        self.assertEqual([version["accn"] for version in selected["versions"]], [LATER["accn"]])
        self.assertIsNone(selected["restated"])
        self.assertEqual(edgar.get_financials(MSFT_CIK, 2023)["revenue"]["accn"], LATER["accn"])
        old = call(edgar_server, "get_fact", fact_id=f"{CONCEPT}/2023/{ORIGINAL['accn']}")
        new = call(edgar_server, "get_fact", fact_id=f"{CONCEPT}/2023/{LATER['accn']}")
        self.assertFalse(old["ok"])
        self.assertEqual(old["error"]["code"], "NOT_FOUND")
        self.assertEqual(new["fact"]["source_review"]["decision"], "eligible")
        self.assertIsNone(edgar.get_financials(MSFT_CIK, 2023)["operating_income"])

    def test_unreviewed_later_value_is_never_used_as_a_replacement(self):
        self.register([record(ORIGINAL, "excluded")])
        self.assertIsNone(edgar.get_annual_fact(MSFT_CIK, CONCEPT, 2023))
        self.assertFalse(call(edgar_server, "get_fact", fact_id=f"{CONCEPT}/2023/{LATER['accn']}")["ok"])

    def test_changed_reviewed_fact_and_bad_register_fail_closed(self):
        self.register([{**record(ORIGINAL, "eligible"), "value_usd": 1}])
        with self.assertRaisesRegex(source_review.SourceReviewError, "differs from cached data"):
            edgar.get_annual_fact(MSFT_CIK, CONCEPT, 2023)
        self.register([record(ORIGINAL, "eligible"), record(ORIGINAL, "excluded")])
        with self.assertRaisesRegex(source_review.SourceReviewError, "duplicate"):
            edgar.get_annual_fact(MSFT_CIK, CONCEPT, 2023)
        self.path.write_text("{", encoding="utf-8")
        with self.assertRaises(source_review.SourceReviewError):
            edgar.get_annual_fact(MSFT_CIK, CONCEPT, 1990)

    def test_missing_registry_and_quarterly_data_fail_explicitly(self):
        with self.assertRaises(source_review.SourceReviewError):
            edgar.get_annual_fact(MSFT_CIK, CONCEPT, 2023)
        self.register([])
        with self.assertRaisesRegex(source_review.SourceReviewError, "Quarterly facts"):
            edgar.get_quarterly_facts(MSFT_CIK, CONCEPT, 2023)
        with self.assertRaisesRegex(SnapshotError, "Source-review register unavailable"):
            self.path.write_text("{", encoding="utf-8")
            capture({"title": "Summary", "body": "Summary", "tickers": ["MSFT"]}, lambda _: None)

    def test_changed_register_invalidates_review_snapshot(self):
        self.register([record(ORIGINAL, "eligible")])
        draft = {"title": "Summary", "body": f"Revenue [fact: {CONCEPT}/2023/{ORIGINAL['accn']}].",
                 "tickers": ["MSFT"]}
        before = capture(draft, lambda _: None)
        self.register([record(ORIGINAL, "excluded"), record(LATER, "eligible")])
        with self.assertRaisesRegex(SnapshotError, "unavailable"):
            capture(draft, lambda _: None)
        self.assertIn("source_review", before["source_files"])

    def test_quarterly_chart_and_c0_disclose_enforced_limit(self):
        from analystdesk.research.c0_pipeline import _format_numbers
        from analystdesk.research.chat_chart import build_chat_chart
        self.register([record(ORIGINAL, "eligible")])
        text = _format_numbers(["MSFT"], [2023])
        self.assertIn("quarterly data is unavailable", text)
        chart, notice = build_chat_chart("Microsoft quarterly revenue", [2023])
        self.assertIsNone(chart)
        self.assertIn("Quarterly charts are unavailable", notice)

    def test_unconfigured_mode_is_marked_unverified(self):
        with patch.dict("os.environ", {"SOURCE_REVIEW_FILE": ""}):
            selected = edgar.get_annual_fact(MSFT_CIK, CONCEPT, 2023)
        self.assertEqual(selected["accn"], ORIGINAL["accn"])
        self.assertEqual(selected["eligibility"], "unverified")

    def test_incompatible_reviewed_inputs_do_not_generate_margins(self):
        from analystdesk.finance.figures import build_figures
        from analystdesk.research.baseline import run_baseline
        from analystdesk.research.c0_pipeline import _format_numbers
        from analystdesk.research.chat_chart import build_chat_chart
        from analystdesk.research.scope import create_request

        self.register([])
        revenue = {"val": 100, "start": "2022-07-01", "end": "2023-06-30",
                   "accn": ORIGINAL["accn"], "fact_id": f"{CONCEPT}/2023/{ORIGINAL['accn']}",
                   "eligibility": "eligible"}
        for change in ({"start": "2022-07-02"}, {"accn": LATER["accn"]}):
            income = {**revenue, **change, "val": 20,
                      "fact_id": f"OperatingIncomeLoss/2023/{change.get('accn', ORIGINAL['accn'])}"}
            financials = {"revenue": revenue, "operating_income": income, "pretax_income": None}
            with self.subTest(change=change), \
                    patch('analystdesk.finance.figures.get_financials', return_value=financials), \
                    patch('analystdesk.research.baseline.get_financials', return_value=financials), \
                    patch('analystdesk.research.c0_pipeline.get_financials', return_value=financials), \
                    patch('analystdesk.research.chat_chart.get_financials', return_value=financials):
                self.assertNotIn("MSFT_2023_margin", build_figures(["MSFT"], [2023]))
                note = run_baseline(create_request(["MSFT"], [2023]))
                self.assertIsNone(note.rows[0].operating_margin_pct)
                self.assertTrue(any("margin unavailable" in warning for warning in note.warnings))
                self.assertIn("margin unavailable", _format_numbers(["MSFT"], [2023]))
                chart, notice = build_chat_chart("Microsoft operating margin", [2023])
                self.assertIsNone(chart)
                self.assertIn("incompatible", notice)
