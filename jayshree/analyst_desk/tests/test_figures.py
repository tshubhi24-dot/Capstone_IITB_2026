import unittest

from analystdesk.agent.checks import check_note
from analystdesk.agent.figures import build_figures, render


class FiguresTests(unittest.TestCase):
    def test_rendered_figures_always_pass_the_checker(self):
        figures = build_figures(["MSFT", "GOOGL", "JPM"], [2022, 2023, 2024])
        body = " ".join(f"{{{k}}}" for k in figures if not k.endswith("period_end"))
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

    def test_checker_rejects_an_unfilled_slot(self):
        r = check_note("### What changed since our last note\n{WHAT_CHANGED}")
        self.assertEqual(r.issues, ["Unfilled slot {WHAT_CHANGED}."])
        self.assertTrue(check_note("Lower-case {braces} and {Mixed_Case} are ordinary text.").ok)


if __name__ == "__main__":
    unittest.main()
