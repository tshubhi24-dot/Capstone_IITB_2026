"""Tests for edgar.py — cache behaviour, fact_id format, missing data handling."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from analystdesk.edgar import (
    _pad_cik,
    get_annual_fact,
    get_financials,
    fetch_company_facts,
)

MSFT_CIK = "0000789019"
GOOGL_CIK = "0001652044"

# Minimal companyfacts JSON that mimics EDGAR's real response shape
FAKE_FACTS = {
    "cik": 789019,
    "entityName": "FAKE CORP",
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {
                            "start": "2022-07-01", "end": "2023-06-30", "val": 211915000000,
                            "accn": "0000789019-23-000001", "fy": 2023,
                            "fp": "FY", "form": "10-K", "filed": "2023-07-27"
                        },
                        # quarterly entry — must be filtered out
                        {
                            "start": "2023-01-01", "end": "2023-03-31", "val": 52857000000,
                            "accn": "0000789019-23-000099", "fy": 2023,
                            "fp": "Q3", "form": "10-Q", "filed": "2023-04-25"
                        },
                    ]
                }
            },
            "OperatingIncomeLoss": {
                "units": {
                    "USD": [
                        # fourth-quarter figure tagged inside the 10-K
                        {
                            "start": "2023-04-01", "end": "2023-06-30", "val": 24254000000,
                            "accn": "0000789019-23-000001", "fy": 2023,
                            "fp": "FY", "form": "10-K", "filed": "2023-07-27"
                        },
                        {
                            "start": "2022-07-01", "end": "2023-06-30", "val": 88523000000,
                            "accn": "0000789019-23-000001", "fy": 2023,
                            "fp": "FY", "form": "10-K", "filed": "2023-07-27"
                        },
                    ]
                }
            },
        }
    },
}


class TestPadCik(unittest.TestCase):
    def test_pads_short_cik(self):
        self.assertEqual(_pad_cik("789019"), "0000789019")

    def test_leaves_full_cik_unchanged(self):
        self.assertEqual(_pad_cik("0000789019"), "0000789019")


class TempCacheTestCase(unittest.TestCase):
    """Point edgar.py at a temporary cache holding FAKE_FACTS for MSFT.

    Never touch the real data/edgar_cache: it is committed for the team.
    """
    facts = FAKE_FACTS

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        cache_dir = Path(self._tmp.name)
        patcher = patch("analystdesk.edgar.CACHE_DIR", cache_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)
        (cache_dir / f"{_pad_cik(MSFT_CIK)}.json").write_text(
            json.dumps(self.facts), encoding="utf-8"
        )


class TestFetchCompanyFacts(TempCacheTestCase):
    def test_uses_cache_on_second_call(self):
        """Second call must read from disk, not hit the network."""

        with patch("urllib.request.urlopen") as mock_open:
            result = fetch_company_facts(MSFT_CIK)
            mock_open.assert_not_called()   # network must not be touched

        self.assertEqual(result["entityName"], "FAKE CORP")


class TestGetAnnualFact(TempCacheTestCase):
    def test_returns_annual_fact(self):
        fact = get_annual_fact(
            MSFT_CIK,
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            2023,
        )
        self.assertIsNotNone(fact)
        self.assertEqual(fact["val"], 211915000000)

    def test_filters_out_quarterly_entries(self):
        # Q3 entry for the same year must not be returned
        fact = get_annual_fact(
            MSFT_CIK,
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            2023,
        )
        self.assertEqual(fact["end"], "2023-06-30")   # annual, not quarterly

    def test_fact_id_format(self):
        fact = get_annual_fact(
            MSFT_CIK,
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            2023,
        )
        expected = (
            "RevenueFromContractWithCustomerExcludingAssessedTax"
            "/2023/0000789019-23-000001"
        )
        self.assertEqual(fact["fact_id"], expected)

    def test_returns_none_for_missing_year(self):
        fact = get_annual_fact(
            MSFT_CIK,
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            1990,       # year not in our fake data
        )
        self.assertIsNone(fact)

    def test_ignores_quarterly_figures_tagged_in_a_10k(self):
        # 10-Ks tag quarterly tables with fp == "FY" too (BAC); only a
        # full-year duration counts
        fact = get_annual_fact(MSFT_CIK, "OperatingIncomeLoss", 2023)
        self.assertEqual(fact["val"], 88523000000)

    def test_returns_none_for_unknown_concept(self):
        fact = get_annual_fact(MSFT_CIK, "NonExistentConcept", 2023)
        self.assertIsNone(fact)


class TestRestatedFacts(TempCacheTestCase):
    """A later 10-K restating a prior year must not replace the original."""
    facts = copy.deepcopy(FAKE_FACTS)
    facts["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"].append({
        "start": "2022-07-01", "end": "2023-06-30", "val": 215000000000,
        "accn": "0000789019-24-000007", "fy": 2024,
        "fp": "FY", "form": "10-K", "filed": "2024-07-30",
    })

    def test_keeps_original_and_reports_restatement(self):
        fact = get_annual_fact(
            MSFT_CIK, "RevenueFromContractWithCustomerExcludingAssessedTax", 2023
        )
        self.assertEqual(fact["val"], 211915000000)
        self.assertEqual(fact["accn"], "0000789019-23-000001")
        self.assertEqual(fact["restated"]["val"], 215000000000)
        self.assertEqual(fact["restated"]["accn"], "0000789019-24-000007")
        self.assertEqual(fact["eligibility"], "unverified")
        self.assertEqual([version["accn"] for version in fact["versions"]],
                         ["0000789019-23-000001", "0000789019-24-000007"])

    def test_amendment_with_unchanged_value_remains_visible(self):
        data = copy.deepcopy(FAKE_FACTS)
        entries = data["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"]["USD"]
        entries.append({**entries[0], "form": "10-K/A", "accn": "0000789019-23-000002",
                        "filed": "2023-08-01"})
        with patch("analystdesk.edgar.fetch_company_facts", return_value=data):
            fact = get_annual_fact(MSFT_CIK, "RevenueFromContractWithCustomerExcludingAssessedTax", 2023)
        self.assertIsNone(fact["restated"])
        self.assertEqual([version["form"] for version in fact["versions"]], ["10-K", "10-K/A"])


class TestGetFinancials(TempCacheTestCase):
    def test_returns_both_metrics(self):
        result = get_financials(MSFT_CIK, 2023)
        self.assertIsNotNone(result["revenue"])
        self.assertIsNotNone(result["operating_income"])

    def test_missing_year_returns_none_values(self):
        result = get_financials(MSFT_CIK, 1990)
        self.assertIsNone(result["revenue"])
        self.assertIsNone(result["operating_income"])


if __name__ == "__main__":
    unittest.main()
