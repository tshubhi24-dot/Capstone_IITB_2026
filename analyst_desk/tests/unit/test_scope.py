import unittest

from analystdesk.research.scope import ResearchRequest
from analystdesk.research.scope import ScopeError
from analystdesk.research.scope import create_request


class ScopeTests(unittest.TestCase):
    def test_normalizes_names_tickers_and_year_order(self):
        request = create_request([" googl ", "msft"], [2024, 2022, 2023])
        self.assertEqual(request.to_dict()["fiscal_years"], [2022, 2023, 2024])
        self.assertEqual([c.name for c in request.companies], ["Alphabet", "Microsoft"])

    def test_accepts_any_supported_company_and_year_count(self):
        request = create_request(["Apple", "JPM"], [2024])
        self.assertEqual([c.ticker for c in request.companies], ["AAPL", "JPM"])

    def test_rejects_unsupported_or_duplicate_companies(self):
        for companies in (["Tesla", "Microsoft"], ["Microsoft", "MSFT"], []):
            with self.subTest(companies=companies), self.assertRaises(ScopeError):
                create_request(companies, [2022, 2023, 2024])

    def test_rejects_invalid_years(self):
        for years in ([], [2022, 2022, 2024], [22, 23, 24], [True, 2023, 2024], ["2022", 2023, 2024]):
            with self.subTest(years=years), self.assertRaises(ScopeError):
                create_request(["Microsoft", "Alphabet"], years)

    def test_direct_construction_cannot_bypass_scope(self):
        valid = create_request(["Microsoft", "Alphabet"], [2022, 2023, 2024])
        with self.assertRaises(ScopeError):
            ResearchRequest(valid.companies, valid.fiscal_years, ("stock_price",))


if __name__ == "__main__":
    unittest.main()
