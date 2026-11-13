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
    def test_only_uncited_lines_can_be_overridden(self):
        self.assertTrue(approval.overridable({"ok": False, "issues": [UNCITED]}))
        for issues in ([UNCITED, "Number '47%' has no source: use a figure placeholder"],
                       [UNCITED, 'Claim not supported by its cited passage (judge): "x"'],
                       ["Review incomplete: the judge gave no valid verdict for 2 of 4 cited claims."],
                       ["Review incomplete: Evidence or policy changed during review."],
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
        check = {"ok": False, "issues": [UNCITED, "Number '15.69%' has no source"]}
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
                                ({"ok": False, "issues": [UNCITED, "Number '47%' has no source"]}, OVERRIDE)):
            with self.subTest(check=check, override=override):
                result, _ = self._publish(check, override)
                result = result if isinstance(result, dict) else result.model_dump()
                self.assertEqual(result["error"]["code"], "APPROVAL_INVALID")


if __name__ == "__main__":
    unittest.main()


class GateDisplayTests(unittest.TestCase):
    def _display(self, issues):
        from agent_ui import _check_display
        return _check_display({"ok": False, "issues": issues, "verified": 3, "total": 3, "verified_share": 100,
                               "claims": {"checked": 1, "reviewed": 1, "supported": 0, "uncited": 2,
                                          "uncited_lines": ["# Title", "## Introduction"]}})

    def test_lists_uncited_lines_and_offers_override_when_they_are_the_only_issue(self):
        text = self._display([UNCITED])
        self.assertIn("`# Title`", text)
        self.assertIn("Override available", text)
        self.assertNotIn("Approval unavailable", text)

    def test_explains_why_override_is_not_available_yet(self):
        text = self._display([UNCITED, 'Claim not supported by its cited passage (judge): "x"'])
        self.assertIn("Approval unavailable", text)
        self.assertIn("Override not available yet", text)
        self.assertIn("the 1 other issue(s)", text)
