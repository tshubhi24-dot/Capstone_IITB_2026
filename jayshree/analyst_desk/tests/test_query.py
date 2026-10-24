import unittest

from analystdesk.query import decompose, find_companies, find_years, search_decomposed


class FindTests(unittest.TestCase):
    def test_names_and_tickers_in_order(self):
        self.assertEqual(find_companies("Compare Microsoft and GOOGL margins"), ["MSFT", "GOOGL"])

    def test_multiword_names(self):
        self.assertEqual(find_companies("Morgan Stanley vs Bank of America"), ["MS", "BAC"])
        self.assertEqual(find_companies("JPMorgan and Wells Fargo"), ["JPM", "WFC"])

    def test_lowercase_short_tickers_are_not_companies(self):
        # "ms" / "v" in ordinary text must not become Morgan Stanley / Visa
        self.assertEqual(find_companies("revenue in ms excel vs plan"), [])

    def test_years(self):
        self.assertEqual(find_years("FY2023 vs fiscal 2024, and 2023 again"), [2023, 2024])
        self.assertEqual(find_years("revenue of $20240 million"), [])


class DecomposeTests(unittest.TestCase):
    def test_one_subquery_per_company_year(self):
        subs = decompose("Microsoft and Alphabet operating margin FY2023 FY2024")
        self.assertEqual([(s.company, s.year) for s in subs],
                         [("MSFT", 2023), ("MSFT", 2024), ("GOOGL", 2023), ("GOOGL", 2024)])

    def test_rewrite_strips_names_tickers_and_years(self):
        subs = decompose("What was Goldman Sachs' provision for credit losses in FY2023?")
        self.assertEqual(subs[0].text, "What was provision for credit losses in")
        self.assertEqual(decompose("JPM vs GS fiscal year 2024 fees")[0].text, "vs fees")

    def test_rewrite_keeps_question_if_nothing_left(self):
        self.assertEqual(decompose("Microsoft 2024")[0].text, "Microsoft 2024")

    def test_no_company_searches_question_as_is(self):
        subs = decompose("What are the main cybersecurity risks?")
        self.assertEqual([(s.company, s.year) for s in subs], [(None, None)])


class FakeRetriever:
    def search(self, query, top_k=5, company=None, year=None, **_):
        return [{"passage_id": f"{company}_{i}"} for i in range(top_k)]


class SearchDecomposedTests(unittest.TestCase):
    def test_round_robin_gives_every_company_evidence(self):
        hits = search_decomposed(FakeRetriever(), "Microsoft vs Alphabet", top_k=5)
        self.assertEqual([h["passage_id"] for h in hits],
                         ["MSFT_0", "GOOGL_0", "MSFT_1", "GOOGL_1", "MSFT_2"])


if __name__ == "__main__":
    unittest.main()
