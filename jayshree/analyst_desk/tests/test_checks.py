import unittest

from analystdesk.agent.checks import check_note

REV = "RevenueFromContractWithCustomerExcludingAssessedTax/2024/0000950170-24-087843"
OPI = "OperatingIncomeLoss/2024/0000950170-24-087843"


class CheckNoteTests(unittest.TestCase):
    def test_correct_note_passes(self):
        body = (f"Microsoft revenue was $245,122.0M [fact: {REV}] and operating income "
                f"$109,433.0M [fact: {OPI}], a margin of 44.64% [calc: {OPI} / {REV}] "
                f"[MSFT_2024_item7_020].")
        r = check_note(body, passage_exists=lambda pid: True)
        self.assertTrue(r.ok, r.issues)
        self.assertEqual((r.verified_numbers, r.total_numbers), (3, 3))

    def test_planted_wrong_number_is_caught(self):
        r = check_note(f"Revenue was $254,122.0M [fact: {REV}].")
        self.assertFalse(r.ok)
        self.assertIn("does not match", r.issues[0])

    def test_wrong_margin_is_caught(self):
        r = check_note(f"Margin 45.10% [calc: {OPI} / {REV}].")
        self.assertIn("44.64%", r.issues[0])

    def test_billions_form_and_uncited_numbers(self):
        self.assertTrue(check_note(f"Revenue of $245.1B [fact: {REV}].").ok)
        r = check_note("Revenue grew 16% to $245 billion.")
        self.assertEqual(r.total_numbers, 2)
        self.assertTrue(all("has no source" in i for i in r.issues))

    def test_unknown_fact_and_missing_passage(self):
        r = check_note("x $1.0M [fact: Revenues/2024/0000000000-00-000000] [MSFT_2024_item7_999]",
                       passage_exists=lambda pid: False)
        self.assertEqual(len(r.issues), 2)

    def test_quoted_number_must_be_in_the_cited_passage(self):
        texts = {"MSFT_2024_item7_017": "Revenue increased $33.2 billion or 16% driven by Azure."}
        ok = check_note("Revenue increased 16% on Azure [MSFT_2024_item7_017].", passage_text=texts.get)
        self.assertTrue(ok.ok, ok.issues)
        bad = check_note("Revenue increased 18% on Azure [MSFT_2024_item7_017].", passage_text=texts.get)
        self.assertIn("does not appear in the passage", bad.issues[0])

    def test_table_quote_in_millions(self):
        """A table cell has no unit of its own; the caption "(In millions)" gives it one."""
        table = {"MSFT_2024_item7_020": "SEGMENT RESULTS OF OPERATIONS\n(In millions, except percentages) "
                 "| 2024 | 2023\nIntelligent Cloud | 105,362 | 87,907\nTotal | $245,122 | $211,915"}
        for quote in ("$105.362 billion", "$105.4 billion", "$105,362 million", "$245.1 billion"):
            r = check_note(f"Segment revenue was {quote} [MSFT_2024_item7_020].", passage_text=table.get)
            self.assertTrue(r.ok, (quote, r.issues))
        for quote in ("$105.9 billion", "$106 billion", "$105,360 million"):   # outside the stated rounding
            r = check_note(f"Segment revenue was {quote} [MSFT_2024_item7_020].", passage_text=table.get)
            self.assertFalse(r.ok, quote)
        prose = {"MSFT_2024_item7_017": "Intelligent Cloud revenue increased to 105,362."}   # no caption
        self.assertFalse(check_note("It was $105.4 billion [MSFT_2024_item7_017].", passage_text=prose.get).ok)
        self.assertFalse(check_note("It grew 105.4% [MSFT_2024_item7_020].", passage_text=table.get).ok)

    def test_advice_wording_blocked(self):
        r = check_note("We recommend investors buy Microsoft.")
        self.assertFalse(r.ok)
        self.assertTrue(any("advice" in i for i in r.issues))


if __name__ == "__main__":
    unittest.main()
