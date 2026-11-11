"""Tests for baseline.py — the C0 fixed pipeline.

These tests verify the three invariants of C0:
  1. Margin is computed in Python code (not in an LLM)
  2. Every row with a value must have a fact_id
  3. Missing EDGAR data is recorded as a warning, not a crash
"""

import unittest
from unittest.mock import patch

from analystdesk.research.baseline import _operating_margin
from analystdesk.research.baseline import _to_millions
from analystdesk.research.baseline import run_baseline
from analystdesk.research.scope import create_request


class TestHelpers(unittest.TestCase):
    def test_to_millions_rounds_correctly(self):
        self.assertEqual(_to_millions(211915000000), 211915.0)
        self.assertEqual(_to_millions(88523000000), 88523.0)

    def test_to_millions_none_input(self):
        self.assertIsNone(_to_millions(None))

    def test_operating_margin_correct(self):
        # 88523 / 211915 * 100 = 41.77...
        result = _operating_margin(211915.0, 88523.0)
        self.assertAlmostEqual(result, 41.77, places=1)

    def test_operating_margin_zero_revenue(self):
        self.assertIsNone(_operating_margin(0.0, 100.0))

    def test_operating_margin_none_inputs(self):
        self.assertIsNone(_operating_margin(None, 88523.0))
        self.assertIsNone(_operating_margin(211915.0, None))
        self.assertIsNone(_operating_margin(None, None))


# Fake EDGAR response for two companies, two years
FAKE_MSFT = {
    "revenue": {
        "val": 211915000000, "start": "2022-07-01", "end": "2023-06-30",
        "accn": "0000789019-23-001", "filed": "2023-07-27",
        "fact_id": "RevenueFromContractWithCustomerExcludingAssessedTax/2023/0000789019-23-001",
    },
    "operating_income": {
        "val": 88523000000, "start": "2022-07-01", "end": "2023-06-30",
        "accn": "0000789019-23-001", "filed": "2023-07-27",
        "fact_id": "OperatingIncomeLoss/2023/0000789019-23-001",
    },
}
FAKE_GOOGL = {
    "revenue": {
        "val": 282836000000, "start": "2023-01-01", "end": "2023-12-31",
        "accn": "0001652044-24-001", "filed": "2024-01-30",
        "fact_id": "Revenues/2023/0001652044-24-001",
    },
    "operating_income": {
        "val": 84293000000, "start": "2023-01-01", "end": "2023-12-31",
        "accn": "0001652044-24-001", "filed": "2024-01-30",
        "fact_id": "OperatingIncomeLoss/2023/0001652044-24-001",
    },
}
MISSING = {"revenue": None, "operating_income": None}


def fake_get_financials(cik, fiscal_year):
    if fiscal_year == 2023:
        return FAKE_MSFT if "789019" in cik else FAKE_GOOGL
    return MISSING


class TestRunBaseline(unittest.TestCase):
    def setUp(self):
        self.request = create_request(["Microsoft", "Alphabet"], [2022, 2023, 2024])

    @patch('analystdesk.research.baseline.get_financials', side_effect=fake_get_financials)
    def test_produces_six_rows(self, _mock):
        note = run_baseline(self.request)
        self.assertEqual(len(note.rows), 6)   # 2 companies × 3 years

    @patch('analystdesk.research.baseline.get_financials', side_effect=fake_get_financials)
    def test_every_value_has_fact_id(self, _mock):
        note = run_baseline(self.request)
        for row in note.rows:
            if row.revenue_usd_m is not None:
                self.assertIsNotNone(
                    row.revenue_fact_id,
                    f"{row.company} FY{row.fiscal_year}: revenue has no fact_id"
                )
            if row.operating_income_usd_m is not None:
                self.assertIsNotNone(
                    row.operating_income_fact_id,
                    f"{row.company} FY{row.fiscal_year}: op income has no fact_id"
                )

    @patch('analystdesk.research.baseline.get_financials', side_effect=fake_get_financials)
    def test_margin_computed_from_row_values(self, _mock):
        note = run_baseline(self.request)
        for row in note.rows:
            if row.revenue_usd_m and row.operating_income_usd_m:
                expected = round(
                    row.operating_income_usd_m / row.revenue_usd_m * 100, 2
                )
                self.assertAlmostEqual(row.operating_margin_pct, expected, places=1)

    @patch('analystdesk.research.baseline.get_financials', side_effect=fake_get_financials)
    def test_missing_year_adds_warning_not_crash(self, _mock):
        note = run_baseline(self.request)
        # Years 2022 and 2024 return MISSING — should produce warnings
        self.assertTrue(len(note.warnings) > 0)
        self.assertEqual(note.status, "draft")   # still returns a note

    @patch('analystdesk.research.baseline.get_financials', side_effect=fake_get_financials)
    def test_status_is_draft(self, _mock):
        note = run_baseline(self.request)
        self.assertEqual(note.status, "draft")

    @patch('analystdesk.research.baseline.get_financials', side_effect=fake_get_financials)
    def test_to_dict_is_json_serialisable(self, _mock):
        import json
        note = run_baseline(self.request)
        # Must not raise
        json.dumps(note.to_dict())


# Banks report pre-tax income but no operating income
FAKE_JPM = {
    "revenue": {
        "val": 180000000000, "start": "2024-01-01", "end": "2024-12-31",
        "accn": "0000019617-25-001", "filed": "2025-02-14",
        "fact_id": "RevenuesNetOfInterestExpense/2024/0000019617-25-001",
    },
    "operating_income": None,
    "pretax_income": {
        "val": 72000000000, "start": "2024-01-01", "end": "2024-12-31",
        "accn": "0000019617-25-001", "filed": "2025-02-14",
        "fact_id": "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"
                   "ExtraordinaryItemsNoncontrollingInterest/2024/0000019617-25-001",
    },
}


class TestBankRows(unittest.TestCase):
    @patch('analystdesk.research.baseline.get_financials', return_value=FAKE_JPM)
    def test_bank_uses_pretax_margin_and_counts_as_verified(self, _mock):
        note = run_baseline(create_request(["JPM"], [2024]))
        row = note.rows[0]
        self.assertEqual(row.margin_basis, "pretax")
        self.assertIsNone(row.operating_margin_pct)
        self.assertAlmostEqual(row.headline_margin_pct(), 40.0)
        self.assertEqual(note.verification_pct(), 100.0)
        self.assertTrue(any("source eligibility" in warning for warning in note.warnings))


if __name__ == "__main__":
    unittest.main()
