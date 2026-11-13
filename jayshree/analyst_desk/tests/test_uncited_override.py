"""Analyst override for lines without a passage citation (and only for those)."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk import approval
from analystdesk.agent.team import claim_lines, uncited_lines

UNCITED = ("Review incomplete: 3 substantive line(s) lack a passage citation. "
           "Add supporting evidence or remove the unsupported claims before approval.")
OVERRIDE = {"uncited": True, "reason": "Headings and code-verified figures; read every line."}


class OverrideRuleTests(unittest.TestCase):
    def test_only_judgement_findings_can_be_overridden(self):
        judge_rejected = 'Claim not supported by its cited passage (judge): "x" — no support'
        no_verdict = "Review incomplete: the judge gave no valid verdict for 2 of 4 cited claims."
        for issues in ([UNCITED], [judge_rejected], [no_verdict], [UNCITED, judge_rejected, no_verdict]):
            with self.subTest(issues=issues):
                self.assertTrue(approval.overridable({"ok": False, "issues": issues}))
        for issues in ([UNCITED, "12.3% is wrong: OperatingIncomeLoss / Revenues = 12.4%."],
                       [judge_rejected, "12.3% is wrong: a / b = 12.4%."],
                       [UNCITED, "Investment-advice wording 'buy' is not allowed in a research note."],
                       [UNCITED, "The note names NVDA, which is on the analyst's private watchlist"],
                       ["Review incomplete: Evidence or policy changed during review."],
                       ["Review incomplete: automated claim review is unavailable."],
                       []):
            with self.subTest(issues=issues):
                self.assertFalse(approval.overridable({"ok": False, "issues": issues}))
        self.assertFalse(approval.overridable({"ok": True, "issues": []}))
        self.assertFalse(approval.overridable(None))

    def test_override_needs_a_reason_and_an_explicit_flag(self):
        check = {"ok": False, "issues": [UNCITED]}
        self.assertTrue(approval.review_passed(check, OVERRIDE))
        self.assertFalse(approval.review_passed(check, None))
        self.assertFalse(approval.review_passed(check, {"uncited": True, "reason": "   "}))
        self.assertFalse(approval.review_passed(check, {"uncited": "yes", "reason": "ok"}))
        self.assertTrue(approval.review_passed({"ok": True, "issues": []}))

    def test_override_never_covers_other_issues(self):
        check = {"ok": False, "issues": [UNCITED, "12.3% is wrong: OperatingIncomeLoss / Revenues = 12.4%."]}
        self.assertFalse(approval.review_passed(check, OVERRIDE))

    def test_uncited_lines_are_listed_for_the_analyst(self):
        body = ("# Apple revenue\n"
                "## Summary\n"
                "Revenue grew modestly [AAPL_2024_item7_010].\n"
                "This note examines Apple's revenue.\n"
                "| Year | Revenue |\n|---|---|\n")
        lines = uncited_lines(body)
        self.assertEqual(lines, ["# Apple revenue", "This note examines Apple's revenue.", "| Year | Revenue |"])
        self.assertEqual(claim_lines(body)[1], len(lines))


class PortalOverrideTests(unittest.TestCase):
    NOTE = {"title": "Apple revenue", "body": "Revenue grew.", "tickers": ["AAPL"]}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"PORTAL_DB": str(Path(self.tmp.name) / "p.db"),
                                           "APPROVAL_SECRET": "test-secret"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def _publish(self, check, override=None):
        from analystdesk.servers import portal
        digest = approval.note_hash(self.NOTE["title"], self.NOTE["body"], self.NOTE["tickers"])
        context = {"version": 2, "check": check,
                   "evidence_snapshot": {"version": 1, "note_sha256": digest, "facts": {},
                                         "passages": {}, "policy_sha256": "a" * 64}}
        if override is not None:
            context["override"] = override
        token = approval.sign(self.NOTE["title"], self.NOTE["body"], self.NOTE["tickers"], "analyst",
                              context=context)
        return portal.publish_note(**self.NOTE, approval_token=token), portal

    def test_portal_accepts_signed_override_of_uncited_lines_and_keeps_it(self):
        result, portal = self._publish({"ok": False, "issues": [UNCITED]}, OVERRIDE)
        result = result if isinstance(result, dict) else result.model_dump()
        self.assertTrue(result["ok"], result)
        with portal._connect() as con:
            row = con.execute("SELECT context_json FROM approval_context WHERE note_id = ?",
                              (result["note_id"],)).fetchone()
        self.assertEqual(json.loads(row["context_json"])["override"], OVERRIDE)

    def test_portal_refuses_without_override_or_for_other_issues(self):
        for check, override in (({"ok": False, "issues": [UNCITED]}, None),
                                ({"ok": False, "issues": [UNCITED, "12.3% is wrong: OperatingIncomeLoss / Revenues = 12.4%."]}, OVERRIDE)):
            with self.subTest(check=check, override=override):
                result, _ = self._publish(check, override)
                result = result if isinstance(result, dict) else result.model_dump()
                self.assertEqual(result["error"]["code"], "APPROVAL_INVALID")


if __name__ == "__main__":
    unittest.main()


class GateDisplayTests(unittest.TestCase):
    CLAIMS = {"checked": 2, "reviewed": 2, "supported": 1, "uncited": 2,
              "uncited_lines": ["## Introduction", "This note looks at Apple."],
              "rejected_lines": ["Growth came from services [AAPL_2024_item7_010]."]}

    def _display(self, issues):
        from agent_ui import _check_display
        return _check_display({"ok": False, "issues": issues, "verified": 3, "total": 3,
                               "verified_share": 100, "claims": self.CLAIMS})

    def test_offers_override_for_judgement_findings(self):
        text = self._display([UNCITED, 'Claim not supported by its cited passage (judge): "x"'])
        self.assertIn("Override available", text)
        self.assertIn("🟥", text)
        self.assertIn("🟨", text)
        self.assertNotIn("Approval unavailable", text)

    def test_code_failures_block_and_are_named(self):
        text = self._display([UNCITED, "12.3% is wrong: OperatingIncomeLoss / Revenues = 12.4%."])
        self.assertIn("Approval unavailable", text)
        self.assertIn("⛔ 12.3% is wrong: OperatingIncomeLoss / Revenues = 12.4%.", text)
        self.assertIn("Once those are fixed", text)

    def test_note_highlights_uncited_and_rejected_lines(self):
        from agent_ui import _note_display
        body = ("## Introduction\nThis note looks at Apple.\n"
                "Growth came from services [AAPL_2024_item7_010].\n| Year | Revenue |\n|---|---|\n"
                "Revenue was flat [AAPL_2024_item7_011].")
        claims = {**self.CLAIMS, "uncited_lines": [*self.CLAIMS["uncited_lines"], "| Year | Revenue |"]}
        text = _note_display(body, {"claims": claims})
        self.assertIn("## 🟨 <mark", text)
        self.assertIn("🟨 <mark style=\"background:#ffe08a;color:#14213D\">This note looks at Apple.</mark>", text)
        self.assertIn("🟥 <mark", text)
        self.assertIn("| 🟨 Year | Revenue |", text)
        self.assertIn("Revenue was flat", text)
        self.assertNotIn("🟥 <mark style=\"background:#f8c4c4;color:#14213D\">Revenue was flat", text)
        self.assertNotIn("🟨", _note_display(body, None))


class UntracedNumberTests(unittest.TestCase):
    NO_SOURCE = ("Number '8.68%' has no source: use a figure placeholder, or quote it from a filing "
                 "and cite the passage on the same line.")
    NOT_IN_PASSAGE = "Number '$4.2 billion' does not appear in the passage(s) cited on its line (MSFT_2024_item7_001)."

    def test_untraced_numbers_can_be_overridden_but_wrong_numbers_cannot(self):
        self.assertEqual(approval.unverified_number(self.NO_SOURCE), "8.68%")
        self.assertEqual(approval.unverified_number(self.NOT_IN_PASSAGE), "$4.2 billion")
        self.assertTrue(approval.overridable({"ok": False, "issues": [UNCITED, self.NO_SOURCE, self.NOT_IN_PASSAGE]}))
        self.assertFalse(approval.overridable({"ok": False, "issues": [self.NO_SOURCE, "8.68% growth is wrong: should be 8.7%."]}))
        self.assertFalse(approval.overridable({"ok": False, "issues": ["Cited passage MSFT_2024_item7_999 does not exist."]}))

    def test_line_with_untraced_number_is_orange(self):
        from agent_ui import _check_display, _note_display
        body = "Revenue rose to $307,394.0M, an 8.68% rise.\nOther line [MSFT_2024_item7_001]."
        check = {"ok": False, "issues": [self.NO_SOURCE], "verified": 1, "total": 2, "verified_share": 50,
                 "claims": {}}
        note = _note_display(body, check)
        self.assertIn("🟧 <mark", note)
        self.assertEqual(note.count("🟧 <mark"), 1)
        shown = _check_display(check)
        self.assertIn("Override available", shown)
        self.assertIn("8.68%", shown)
