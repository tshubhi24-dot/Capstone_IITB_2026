"""Checks over the committed EDGAR data for all 45 company-years.

These read data/edgar_cache (committed), so they need no network. They pin
down signature challenge A: every number is verified, and every fact_id
cites the same 10-K that the passages are read from.
"""

import unittest

from analystdesk.baseline import run_baseline
from analystdesk.ingest import _find_10k
from analystdesk.scope import COMPANIES, create_request

YEARS = [2022, 2023, 2024]


class CommittedDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.note = run_baseline(create_request([c.ticker for c in COMPANIES], YEARS))

    def test_every_row_verified(self):
        self.assertEqual(len(self.note.rows), 45)
        self.assertEqual(self.note.verification_pct(), 100.0)

    def test_fact_ids_cite_the_years_own_10k(self):
        by_name = {c.name: c for c in COMPANIES}
        for r in self.note.rows:
            own = _find_10k(by_name[r.company].cik, r.fiscal_year)[0]
            for fact_id in (r.revenue_fact_id, r.headline_income_fact_id()):
                with self.subTest(company=r.company, year=r.fiscal_year):
                    self.assertTrue(fact_id.endswith(own), f"{fact_id} is not from {own}")

    def test_bac_uses_as_reported_revenue(self):
        row = next(r for r in self.note.rows if r.company == "Bank of America" and r.fiscal_year == 2024)
        self.assertEqual(row.revenue_usd_m, 101887.0)   # FY2024 10-K, not the restated 105,856


if __name__ == "__main__":
    unittest.main()
