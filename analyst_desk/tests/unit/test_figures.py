import unittest

from analystdesk.governance.checks import check_note
from analystdesk.finance.figures import build_figures
from analystdesk.finance.figures import comparability_notes
from analystdesk.finance.figures import render


class FiguresTests(unittest.TestCase):
    def test_rendered_figures_always_pass_the_checker(self):
        figures = build_figures(["MSFT", "GOOGL", "JPM"], [2022, 2023, 2024])
        body = "\n".join(f"{{{k}}}" for k in figures if not k.endswith("period_end"))
        rendered, issues = render(body, figures)
        self.assertEqual(issues, [])
        r = check_note(rendered)
        self.assertTrue(r.ok, r.issues[:3])
        self.assertEqual(r.verified_share, 100.0)

    def test_bank_uses_pretax_figures(self):
        f = build_figures(["JPM"], [2024])
        self.assertIn("JPM_2024_pretax_income", f)
        self.assertNotIn("JPM_2024_operating_income", f)

    def test_unknown_placeholder_reported(self):
        _, issues = render("{MSFT_2019_revenue}", build_figures(["MSFT"], [2024]))
        self.assertEqual(issues, ["Unknown placeholder {MSFT_2019_revenue}."])

    def test_square_bracket_placeholders(self):
        """Live run 1cc35ab6 (3 Nov): the writer typed [GS_2024_margin] in a peer table; it was
        neither filled nor flagged, and the note was published with the blanks."""
        figures = build_figures(["JPM"], [2024])
        rendered, issues = render("| JPM | [JPM_2024_margin] |\n| GS | [GS_2024_margin] |", figures)
        self.assertIn(figures["JPM_2024_margin"]["text"], rendered)    # known: filled
        self.assertEqual(issues, ["Unknown placeholder {GS_2024_margin}."])   # unknown: flagged

    def test_checker_rejects_leftover_placeholders(self):
        """A note edited by hand is re-checked without render(), so the checker must catch them."""
        r = check_note("GS margin: {GS_2024_margin}; BAC margin: [BAC_2024_margin] [JPM_2024_item7_001].")
        self.assertFalse(r.ok)
        self.assertIn("Unknown placeholder {GS_2024_margin}.", r.issues)
        self.assertIn("Unknown placeholder {BAC_2024_margin}.", r.issues)
        self.assertFalse(any("item7" in i for i in r.issues))          # a passage id is not a placeholder


class LikeForLikeTests(unittest.TestCase):
    """Signature challenge A: fiscal years, 53-week years and margin bases differ."""

    def test_one_line_must_not_set_operating_against_pretax_margin(self):
        figures = build_figures(["MSFT", "JPM"], [2024])
        mixed, _ = render("Microsoft {MSFT_2024_margin} is ahead of JPMorgan {JPM_2024_margin}.", figures)
        separate, _ = render("Microsoft: {MSFT_2024_margin}\nJPMorgan (pre-tax): {JPM_2024_margin}", figures)
        self.assertTrue(any("not comparable" in i for i in check_note(mixed).issues))
        self.assertTrue(check_note(separate).ok)

    def test_same_basis_on_one_line_is_fine(self):
        figures = build_figures(["MSFT", "GOOGL"], [2024])
        body, _ = render("Microsoft {MSFT_2024_margin} vs Alphabet {GOOGL_2024_margin}", figures)
        self.assertTrue(check_note(body).ok)

    def test_notes_name_different_year_ends_and_mixed_bases(self):
        notes = comparability_notes(["MSFT", "JPM"], [2024])
        self.assertIn("Microsoft on 30 June", notes[0])
        self.assertIn("JPMorgan Chase on 31 December", notes[0])
        self.assertTrue(any("pre-tax margin" in n and "not comparable" in n for n in notes))

    def test_53_week_year_is_flagged(self):
        notes = comparability_notes(["AAPL"], [2022, 2023, 2024])
        self.assertEqual(len(notes), 1)
        self.assertIn("FY2023 had 53 weeks (2022-09-25 to 2023-09-30)", notes[0])

    def test_nothing_to_say_for_one_ordinary_company(self):
        self.assertEqual(comparability_notes(["GOOGL"], [2023, 2024]), [])


if __name__ == "__main__":
    unittest.main()
