"""E4 on answers: the passage switch and the scorer (offline)."""

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk.ingest import default_table_aware, load_passages

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_e4_tables.py"
spec = importlib.util.spec_from_file_location("run_e4_tables", SCRIPT)
e4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e4)

IPHONE = {"qid": "r01", "type": "table",
          "targets": [{"company": "AAPL", "fiscal_year": 2024, "evidence": ["201,183", "201.2 billion"]}]}
PASSAGES = {"AAPL_2024_item7_010": "iPhone | $ 201,183 | $ 200,583", "AAPL_2024_item7_011": "Services grew."}


class PassageVariantTests(unittest.TestCase):
    def test_table_aware_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PASSAGES_VARIANT", None)
            self.assertTrue(default_table_aware())
        with patch.dict(os.environ, {"PASSAGES_VARIANT": "plain"}):
            self.assertFalse(default_table_aware())

    def test_variant_selects_the_passage_set(self):
        with patch.dict(os.environ, {"PASSAGES_VARIANT": "plain"}):
            plain = load_passages()
        self.assertEqual(len(plain), len(load_passages(table_aware=False)))
        self.assertTrue(all(p.get("kind", "text") == "text" for p in plain[:500]))


class E4ScoreTests(unittest.TestCase):
    def test_questions_are_numeric(self):
        qs = e4.load_questions()
        self.assertGreaterEqual(len(qs), 15)
        self.assertNotIn("r35", [q["qid"] for q in qs])     # a text comparison, not a number

    def test_expected_figure_forms(self):
        self.assertEqual(e4.expected_figure(["201,183", "201.2 billion"]), "$201,183M")
        self.assertEqual(e4.expected_figure(["46.2"]), "46.2%")

    def test_stated_and_grounded(self):
        good = e4.score(IPHONE, "iPhone revenue was $201.2 billion [AAPL_2024_item7_010].", PASSAGES.get)
        self.assertEqual((good["stated"], good["grounded"]), (True, True))
        wrong_cite = e4.score(IPHONE, "iPhone revenue was $201,183 million [AAPL_2024_item7_011].", PASSAGES.get)
        self.assertEqual((wrong_cite["stated"], wrong_cite["grounded"]), (True, False))
        missing = e4.score(IPHONE, "iPhone revenue grew [AAPL_2024_item7_010].", PASSAGES.get)
        self.assertFalse(missing["stated"])


if __name__ == "__main__":
    unittest.main()
