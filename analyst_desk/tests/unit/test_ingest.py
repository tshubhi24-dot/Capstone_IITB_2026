import unittest

from bs4 import BeautifulSoup

from analystdesk.retrieval.ingest import TABLE_END
from analystdesk.retrieval.ingest import TABLE_START
from analystdesk.retrieval.ingest import _chunk_item
from analystdesk.retrieval.ingest import _chunk_table
from analystdesk.retrieval.ingest import _mark_tables
from analystdesk.retrieval.ingest import _split_sections

BODY = "Body text that is long enough to count as real section content. " * 40


def lines(*parts):
    return "\n".join(parts).split("\n")


class SplitSectionsTests(unittest.TestCase):
    def test_toc_entries_lose_to_real_sections(self):
        doc = lines("Item 1A. Risk Factors", "Item 7. MD&A", "Item 8. Financial Statements",
                    "ITEM 1A. RISK FACTORS", BODY, "ITEM 2. PROPERTIES", "x",
                    "ITEM 7. MANAGEMENT'S DISCUSSION", BODY, "ITEM 7A. MARKET RISK", "x")
        result = _split_sections(doc, use_titles=False)
        self.assertIn("Body text", result["item1a"])
        self.assertIn("Body text", result["item7"])

    def test_running_page_header_continues_section(self):
        # Mastercard repeats the item heading at the top of every page
        doc = lines("ITEM 1A. RISK FACTORS", "page one " + BODY,
                    "ITEM 1A. RISK FACTORS", "page two " + BODY, "ITEM 1B. UNRESOLVED", "x")
        result = _split_sections(doc, use_titles=False)
        self.assertIn("page one", result["item1a"])
        self.assertIn("page two", result["item1a"])

    def test_bare_item_link_is_not_a_heading(self):
        # Visa: cross-reference links render as a bare "Item 8" line
        doc = lines("ITEM 7. MD&A", "first " + BODY, "Item 8", "second " + BODY, "ITEM 7A. RISK", "x")
        self.assertIn("second", _split_sections(doc, use_titles=False)["item7"])

    def test_backward_item_reference_stays_in_section(self):
        # BAC: "Item 1A. Risk Factors" linked on its own line inside MD&A
        doc = lines("ITEM 7. MD&A", "first " + BODY, "Item 1A. Risk Factors", "second " + BODY,
                    "ITEM 7A. RISK", "x")
        self.assertIn("second", _split_sections(doc, use_titles=False)["item7"])

    def test_mdna_ends_at_auditor_report(self):
        # JPM: no numbered heading separates MD&A from the financial statements
        doc = lines("Item 7. MD&A", BODY * 5, "Report of Independent Registered Public Accounting Firm",
                    "FINANCIAL STATEMENTS")
        self.assertNotIn("FINANCIAL STATEMENTS", _split_sections(doc, use_titles=False)["item7"])

    def test_title_headings_for_unnumbered_filers(self):
        # Morgan Stanley / Wells Fargo annual report
        doc = lines("Financial Review", "mdna " + BODY, "Risk Factors", "risks " + BODY,
                    "Controls and Procedures", "x")
        result = _split_sections(doc, use_titles=True)
        self.assertIn("mdna", result["item7"])
        self.assertIn("risks", result["item1a"])


DATA_TABLE = """
<table>
  <tr><td>(In millions)</td><td></td><td>2024</td><td></td><td>2023</td></tr>
  <tr><td>Revenue</td><td>$</td><td>245,122</td><td>$</td><td>211,915</td></tr>
  <tr><td>Other income</td><td></td><td>(1,646</td><td>)</td><td>788</td></tr>
</table>
"""
LAYOUT_TABLE = "<table><tr><td>ITEM 1A.</td><td>RISK FACTORS</td></tr></table>"


class TableTests(unittest.TestCase):
    def test_data_table_becomes_marked_rows_with_merged_cells(self):
        soup = BeautifulSoup(DATA_TABLE, "html.parser")
        _mark_tables(soup)
        text = soup.get_text()
        self.assertIn(TABLE_START, text)
        self.assertIn("Revenue | $245,122 | $211,915", text)
        self.assertIn("Other income | (1,646) | 788", text)

    def test_layout_table_stays_plain_text(self):
        # Item headings laid out in a table must still be seen as headings
        soup = BeautifulSoup(LAYOUT_TABLE, "html.parser")
        _mark_tables(soup)
        self.assertNotIn(TABLE_START, soup.get_text())

    def test_large_table_split_by_rows_repeats_header(self):
        rows = ["Metric | 2024 | 2023"] + [f"Line {i} | {i},000 | {i},100" for i in range(200)]
        chunks = _chunk_table(rows, "Segment results", max_chars=500)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertTrue(c.startswith("Segment results\nMetric | 2024 | 2023"))
        # no row lost or cut in half
        body = [ln for c in chunks for ln in c.split("\n")[2:]]
        self.assertEqual(body, rows[1:])

    def test_item_text_and_tables_become_separate_passages(self):
        text = f"Results of operations\n\n{TABLE_START}\nA | 1 | 2\nB | 3 | 4\n{TABLE_END}\n\nMore text."
        kinds = [k for k, _ in _chunk_item(text)]
        self.assertEqual(kinds, ["text", "table", "text"])
        table = dict((k, c) for k, c in _chunk_item(text))["table"]
        self.assertTrue(table.startswith("Results of operations\nA | 1 | 2"))

    def test_toc_rows_inside_table_are_not_headings(self):
        doc = lines("ITEM 7. MD&A", "first " + BODY, TABLE_START, "Item 8. Financial Statements | 50",
                    "Item 9A. Controls | 90", TABLE_END, "second " + BODY, "ITEM 7A. RISK", "x")
        self.assertIn("second", _split_sections(doc, use_titles=False)["item7"])


if __name__ == "__main__":
    unittest.main()
