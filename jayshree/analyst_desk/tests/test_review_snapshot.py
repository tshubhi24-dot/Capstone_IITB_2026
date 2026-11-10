"""Offline tests for approval-time evidence and policy binding."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk.agent.graph import common_nodes
from analystdesk.agent.review_snapshot import SnapshotError, capture
from analystdesk.servers.edgar_server import Fact, FactResult

FID = "OperatingIncomeLoss/2024/0000789019-24-000014"
PID = "MSFT_2024_item7_001"
DRAFT = {"title": "Summary", "body": f"Income was $1.0M [fact: {FID}] [{PID}].",
         "tickers": ["MSFT"]}


def fact(value=1000000):
    return FactResult(ticker="MSFT", fact=Fact(
        concept="OperatingIncomeLoss", value_usd=value, period_start="2023-07-01",
        period_end="2024-06-30", accession="0000789019-24-000014",
        filed="2024-07-30", fact_id=FID))


class SnapshotTests(unittest.TestCase):
    def test_snapshot_binds_fact_passage_policy_and_exact_note(self):
        with patch("analystdesk.agent.review_snapshot.get_fact", return_value=fact()):
            original = capture(DRAFT, lambda _: "first passage")
            self.assertNotEqual(original, capture(DRAFT, lambda _: "changed passage"))
            self.assertNotEqual(original, capture({**DRAFT, "title": "Different"}, lambda _: "first passage"))
            with patch.dict("os.environ", {"AGENT_DEFENCES": "0"}):
                self.assertNotEqual(original, capture(DRAFT, lambda _: "first passage"))
        with patch("analystdesk.agent.review_snapshot.get_fact", return_value=fact(2000000)):
            self.assertNotEqual(original, capture(DRAFT, lambda _: "first passage"))

    def test_missing_evidence_fails_closed(self):
        with self.assertRaisesRegex(SnapshotError, "passage"):
            capture(DRAFT, lambda _: None)
        with patch("analystdesk.agent.review_snapshot.get_fact", return_value=FactResult(ok=False)):
            with self.assertRaisesRegex(SnapshotError, "fact"):
                capture(DRAFT, lambda _: "passage")

    def test_source_file_change_invalidates_snapshot_even_with_cached_passage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MSFT_2024.jsonl"
            path.write_text("first", encoding="utf-8")
            with patch("analystdesk.agent.review_snapshot.ingest.PASSAGES_DIR", Path(directory)), \
                 patch("analystdesk.agent.review_snapshot.get_fact", return_value=fact()), \
                 patch.dict("os.environ", {"AGENT_PASSAGES": "tables"}):
                before = capture(DRAFT, lambda _: "cached passage")
                path.write_text("changed", encoding="utf-8")
                after = capture(DRAFT, lambda _: "cached passage")
        self.assertNotEqual(before["source_files"], after["source_files"])

    def test_source_change_after_review_blocks_approval_and_publication(self):
        state = {"draft": DRAFT, "check": {"ok": True}, "memory_on": False,
                 "review_snapshot": {"snapshot": "old"}, "published": {"approval_token": "token"}}
        nodes = common_nodes(None, None, require_critic=True)
        with patch("analystdesk.agent.graph.interrupt", return_value={"action": "approve"}), \
             patch("analystdesk.agent.review_snapshot.capture", return_value={"snapshot": "new"}):
            with self.assertRaisesRegex(ValueError, "evidence or policy changed"):
                nodes["review_note"](state)
            with self.assertRaisesRegex(ValueError, "evidence or policy changed"):
                asyncio.run(nodes["publish"](state))

    def test_old_checkpoint_without_snapshot_cannot_be_approved(self):
        state = {"draft": DRAFT, "check": {"ok": True}, "memory_on": False}
        with patch("analystdesk.agent.graph.interrupt", return_value={"action": "approve"}):
            with self.assertRaisesRegex(ValueError, "snapshot is missing"):
                common_nodes(None, None, require_critic=True)["review_note"](state)

    def test_change_during_review_makes_check_incomplete(self):
        state = {"draft": {"title": "Summary", "body": "Summary.", "tickers": ["MSFT"]},
                 "plan": {"companies": ["MSFT"]}, "watchlist": []}

        async def critic(_):
            return {"issues": [], "tokens": 0}

        with patch("analystdesk.agent.review_snapshot.capture", side_effect=[{"v": 1}, {"v": 2}]):
            result = asyncio.run(common_nodes(None, None, critic=critic, require_critic=True)["check"](state))
        self.assertFalse(result["check"]["ok"])
        self.assertIn("changed during review", result["check"]["issues"][-1])
        self.assertIsNone(result["review_snapshot"])


if __name__ == "__main__":
    unittest.main()
