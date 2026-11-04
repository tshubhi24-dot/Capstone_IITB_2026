"""The memory evaluation's seeding and scoring, offline (no model calls)."""

import asyncio
import unittest

from analystdesk import memory
from analystdesk.agent.figures import build_figures
from analystdesk.agent.graph import insert_changes
from analystdesk.memory_eval import load_cases, score_off, score_on, seed
from tests.test_memory import TempMemory

CASES = {c["id"]: c for c in load_cases()}


def note_like_the_graph(tickers: list[str], years: list[int]) -> str:
    """What the writer step produces when the model adds nothing: the code-computed
    'what changed' lines (as graph._changes builds them) under their heading."""
    figures = build_figures(tickers, years)
    current = memory.figures_from_note(" ".join(f["text"] for f in figures.values()))
    lines = []
    for t in tickers:
        previous = asyncio.run(memory.last_note(t))
        if previous:
            lines += memory.what_changed(t, previous, current.get(t, {}))
        else:
            lines.append(f"No previous note on {t} in memory, so there is nothing to compare against.")
    return insert_changes("Body of the note.", "\n".join(f"- {ln}" for ln in lines))


def state(body: str, companies: list[str], years: list[int], issues=None) -> dict:
    return {"draft": {"body": body}, "plan": {"companies": companies, "fiscal_years": years},
            "check": {"issues": issues or []}}


class MemoryEvalTests(TempMemory):
    def test_cases_are_well_formed(self):
        self.assertGreaterEqual(len(CASES), 10)
        for c in CASES.values():
            self.assertTrue(c["expect"], c["id"])
            self.assertIn(c["kind"], ("change", "restated", "no_previous", "preference", "scope", "deleted"))

    def test_seeded_move_is_found(self):
        asyncio.run(seed(CASES["m01"]))
        body = note_like_the_graph(["MSFT"], [2024])
        self.assertIn("+2.87 pp", body)                      # 41.77% (FY2023) -> 44.64% (FY2024)
        self.assertTrue(score_on(CASES["m01"], state(body, ["MSFT"], [2024]))["success"])

    def test_seeded_unchanged_and_restated(self):
        asyncio.run(seed(CASES["m02"]))
        body = note_like_the_graph(["JPM"], [2024])
        self.assertTrue(score_on(CASES["m02"], state(body, ["JPM"], [2024]))["success"], body)
        asyncio.run(seed(CASES["m03"]))
        body = note_like_the_graph(["BAC"], [2024])
        self.assertIn("$105,856.0M", body)                  # the seeded (restated) value
        self.assertIn("$101,887.0M", body)                  # as reported in the FY2024 10-K
        self.assertTrue(score_on(CASES["m03"], state(body, ["BAC"], [2024]))["success"], body)

    def test_two_tickers_are_scored_separately(self):
        asyncio.run(seed(CASES["m05"]))
        body = note_like_the_graph(["V", "MA"], [2024])
        self.assertTrue(score_on(CASES["m05"], state(body, ["V", "MA"], [2024]))["success"], body)
        # MA's move line must not count for V
        only_ma = ("## What changed since our last note\n- Previous note on V: #105.\n"
                   "- Previous note on MA: #106.\n- margin: 55.31% (FY2023, last note) → 58.37% (FY2024).")
        checks = score_on(CASES["m05"], state(only_ma, ["V", "MA"], [2024]))["checks"]
        self.assertFalse(checks["change:V=move"])
        self.assertTrue(checks["change:MA=move"])

    def test_deleted_note_is_not_used(self):
        asyncio.run(seed(CASES["m10"]))
        self.assertIsNone(asyncio.run(memory.last_note("MSFT")))
        body = note_like_the_graph(["MSFT"], [2024])
        self.assertTrue(score_on(CASES["m10"], state(body, ["MSFT"], [2024]))["success"], body)

    def test_deleted_preference_is_gone(self):
        asyncio.run(seed(CASES["m11"]))
        self.assertEqual(asyncio.run(memory.preferences("memeval")), [])

    def test_preference_checks(self):
        ok = state("Revenue grew.\n\nPrepared for the Analyst Desk.", ["NVDA"], [2024])
        self.assertTrue(score_on(CASES["m06"], ok)["success"])
        dated = state("MSFT (year ended 2024-06-30) and GOOGL (December 31, 2024).", ["MSFT", "GOOGL"], [2024])
        self.assertTrue(score_on(CASES["m07"], dated)["success"])
        self.assertFalse(score_on(CASES["m07"], state("MSFT 2024-06-30 only.", ["MSFT", "GOOGL"], [2024]))["success"])
        self.assertTrue(score_on(CASES["m08"], state("| Metric | Value |\n|---|---|\n| x | 1 |", ["AMZN"], [2023]))["success"])

    def test_scope_case(self):
        good = state("JPM margin. Peers are outside this note's plan.", ["JPM"], [2024])
        self.assertTrue(score_on(CASES["m09"], good)["success"])
        widened = state("JPM vs GS.", ["JPM", "GS"], [2024])
        self.assertFalse(score_on(CASES["m09"], widened)["checks"]["scope:plan"])
        blanks = state("| GS | [GS_2024_margin] |", ["JPM"], [2024])
        self.assertFalse(score_on(CASES["m09"], blanks)["checks"]["scope:no_placeholder"])

    def test_off_run_must_have_no_memory_text(self):
        self.assertTrue(score_off(CASES["m01"], state("Margin was 44.64%.", ["MSFT"], [2024]))["success"])
        leaked = score_off(CASES["m01"], state("- Previous note on MSFT: #101.", ["MSFT"], [2024]))
        self.assertEqual(leaked["memory_text_found"], ["Previous note on"])
        self.assertFalse(score_off(CASES["m06"], state("Prepared for the Analyst Desk.", ["NVDA"], [2024]))["success"])
        # the writer may echo the request's heading; only an unfilled slot is a failure
        echoed = "### What changed since our last note\nMemory was not used for this note, so it is not compared."
        self.assertTrue(score_off(CASES["m01"], state(echoed, ["MSFT"], [2024]))["success"])
        slot = score_off(CASES["m01"], state("### What changed since our last note\n{WHAT_CHANGED}", ["MSFT"], [2024]))
        self.assertEqual(slot["memory_text_found"], ["{WHAT_CHANGED}"])


if __name__ == "__main__":
    unittest.main()
