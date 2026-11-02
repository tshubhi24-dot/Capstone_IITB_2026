import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk import lessons, memory

L1 = {"when": "comparing companies with different fiscal year ends",
      "do": "state each company's period end next to its figures", "applies_to": ["comparison", "fiscal-year"],
      "source_case": "d09", "source_issue": "x"}
L2 = {"when": "a bank's margin is asked for", "do": "use pre-tax margin and say why",
      "applies_to": ["bank", "margin"], "source_case": "d04", "source_issue": "y"}


class PlaybookTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = patch.object(memory, "MEMORY_DB", Path(tmp.name) / "m.sqlite")
        p.start()
        self.addCleanup(p.stop)

    def test_pending_lessons_are_not_used_until_approved(self):
        k1 = asyncio.run(lessons.add_pending(L1))
        self.assertEqual(asyncio.run(lessons.relevant("Compare Microsoft and Alphabet margins")), [])
        self.assertTrue(asyncio.run(lessons.review(k1, True, "Jayshree")))
        used = asyncio.run(lessons.relevant("Compare Microsoft and Alphabet margins, fiscal year ends differ"))
        self.assertEqual([u["key"] for u in used], [k1])

    def test_exact_duplicate_lessons_merge_sources_and_keep_one_review_status(self):
        async def exercise():
            first_key = await lessons.add_pending(L1)
            duplicate = {
                **L1,
                "when": "  COMPARING companies with different fiscal year ends. ",
                "do": "state each company's period end next to its figures",
                "applies_to": ["FISCAL-YEAR", "comparison"],
                "source_case": "d10",
                "source_config": "c2",
                "source_issue": "same lesson from another case",
            }
            self.assertIsNone(await lessons.add_pending(duplicate))
            pending = await lessons.list_lessons("pending")
            self.assertEqual([item["key"] for item in pending], [first_key])
            self.assertEqual(
                {source["source_case"] for source in pending[0]["source_cases"]},
                {"d09", "d10"},
            )

            self.assertTrue(await lessons.review(first_key, True, "Reviewer"))
            self.assertIsNone(await lessons.add_pending({**L1, "source_case": "d11"}))
            self.assertEqual(await lessons.list_lessons("pending"), [])
            approved = await lessons.list_lessons("approved")
            self.assertEqual([item["key"] for item in approved], [first_key])
            self.assertEqual(
                {source["source_case"] for source in approved[0]["source_cases"]},
                {"d09", "d10", "d11"},
            )
            self.assertEqual(await lessons.list_lessons("rejected"), [])

        asyncio.run(exercise())

    def test_conflicting_legacy_duplicates_return_to_pending_review(self):
        async def exercise():
            async with memory.open_store() as store:
                await store.aput(("lessons", "approved"), "approved-copy",
                                 {**L1, "created_at": "2026-01-01T00:00:00+00:00",
                                  "reviewed_by": "Reviewer", "reviewed_at": "2026-01-02T00:00:00+00:00"})
                await store.aput(("lessons", "rejected"), "rejected-copy",
                                 {**L1, "created_at": "2026-01-02T00:00:00+00:00",
                                  "reviewed_by": "Reviewer", "reviewed_at": "2026-01-03T00:00:00+00:00",
                                  "review_reason": "duplicate"})

            pending = await lessons.list_lessons("pending")
            self.assertEqual(len(pending), 1)
            self.assertEqual(await lessons.list_lessons("approved"), [])
            self.assertEqual(await lessons.list_lessons("rejected"), [])
            self.assertEqual(len(pending[0]["review_history"]), 2)

            self.assertTrue(await lessons.review(pending[0]["key"], False, "Reviewer", "reviewed again"))
            self.assertEqual(await lessons.list_lessons("pending"), [])
            self.assertEqual(await lessons.list_lessons("approved"), [])
            self.assertEqual(len(await lessons.list_lessons("rejected")), 1)

        asyncio.run(exercise())

    def test_rejected_lesson_kept_with_reason(self):
        k2 = asyncio.run(lessons.add_pending(L2))
        asyncio.run(lessons.review(k2, False, "Jayshree", "too specific to one case"))
        rej = asyncio.run(lessons.list_lessons("rejected"))
        self.assertEqual(rej[0]["review_reason"], "too specific to one case")
        self.assertEqual(asyncio.run(lessons.list_lessons("approved")), [])

    def test_frozen_playbook_blocks_changes(self):
        k1 = asyncio.run(lessons.add_pending(L1))
        asyncio.run(lessons.set_frozen(True, "Jayshree"))
        self.assertFalse(asyncio.run(lessons.review(k1, True, "Jayshree")))
        self.assertIsNone(asyncio.run(lessons.add_pending(L2)))

    def test_only_relevant_lessons_retrieved(self):
        for les in (L1, L2):
            asyncio.run(lessons.review(asyncio.run(lessons.add_pending(les)), True, "J"))
        used = asyncio.run(lessons.relevant("What was JPMorgan's bank pre-tax margin?"))
        self.assertEqual(used[0]["applies_to"], ["bank", "margin"])


if __name__ == "__main__":
    unittest.main()
