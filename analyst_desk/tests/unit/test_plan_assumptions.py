"""The plan gate says how code read the request, so the analyst can correct it."""

import asyncio
import unittest

from analystdesk.agent.graph import build_graph, common_nodes, plan_assumptions
from tests.integration.test_graph import _PlanModel

PLAN = {"companies": ["MSFT", "GOOGL"], "fiscal_years": [2022, 2023, 2024]}


class PlanAssumptionTests(unittest.TestCase):
    def test_explicit_unsupported_periods_are_declined_before_planning(self):
        guard = common_nodes(None, None)["input_guard"]
        for request in ("Microsoft revenue calendar year 2024", "MSFT CY2024 revenue",
                        "MSFT FY2024 as of 2024-08-01", "Microsoft revenue Q1 2024"):
            with self.subTest(request=request):
                result = guard({"request": request, "memory_on": False})
                self.assertFalse(result["guard"]["ok"])
                self.assertIn("not supported", result["guard"]["reason"])
        self.assertTrue(guard({"request": "Microsoft FY2024 revenue", "memory_on": False})["guard"]["ok"])

    def test_baseline_does_not_retrieve_or_call_model_for_unsupported_period(self):
        from analystdesk.research.c0_pipeline import answer
        from unittest.mock import Mock
        retriever = Mock()
        result = answer("Microsoft calendar year 2024 revenue", retriever)
        self.assertTrue(result["refused"])
        self.assertIn("not supported", result["answer"])
        retriever.search.assert_not_called()

    def test_last_three_years_is_spelled_out(self):
        out = plan_assumptions("Compare Microsoft's and Alphabet's operating margins over the last three "
                               "fiscal years", PLAN)
        self.assertEqual(len(out), 1)
        self.assertIn("“last three fiscal years” proposes FY2022–FY2024", out[0])
        self.assertIn("not calendar years", out[0])

    def test_no_year_named(self):
        out = plan_assumptions("Microsoft operating margin", {**PLAN, "fiscal_years": [2024]})
        self.assertEqual(out, ["No year was named, so the proposed default covers FY2024."])

    def test_named_years_need_no_explanation(self):
        self.assertEqual(plan_assumptions("Microsoft and Alphabet in fiscal 2022, 2023 and 2024", PLAN), [])

    def test_banks_are_on_pretax_margin(self):
        out = plan_assumptions("JPMorgan margin in fiscal 2024", {"companies": ["JPM"], "fiscal_years": [2024]})
        self.assertEqual(out, ["JPM is a bank: margins are pre-tax margin, not operating margin."])

    def test_the_plan_gate_carries_them(self):
        from langgraph.checkpoint.memory import MemorySaver

        async def run():
            app = build_graph(_PlanModel(), [], None).compile(checkpointer=MemorySaver())
            config = {"configurable": {"thread_id": "assumptions"}}
            async for _ in app.astream({"request": "Microsoft margins over the last three years",
                                        "memory_on": False}, config):
                pass
            snap = await app.aget_state(config)
            return snap.tasks[0].interrupts[0].value

        gate = asyncio.run(run())
        self.assertEqual(gate["gate"], "plan")
        self.assertIn("last three years", gate["assumptions"][0])
        self.assertTrue(gate["requires_year_confirmation"])

    def test_explicit_years_do_not_require_extra_confirmation(self):
        from langgraph.checkpoint.memory import MemorySaver

        async def run():
            app = build_graph(_PlanModel(), [], None).compile(checkpointer=MemorySaver())
            config = {"configurable": {"thread_id": "explicit-years"}}
            async for _ in app.astream({"request": "Microsoft margins in 2024",
                                        "memory_on": False}, config):
                pass
            snap = await app.aget_state(config)
            return snap.tasks[0].interrupts[0].value

        gate = asyncio.run(run())
        self.assertFalse(gate["requires_year_confirmation"])

    def test_relative_period_selects_latest_covered_years(self):
        from analystdesk.agent.graph import _relative_year_count, year_confirmation_required

        self.assertEqual(_relative_year_count("last three years"), 3)
        self.assertEqual(_relative_year_count("past 2 fiscal years"), 2)
        self.assertEqual(_relative_year_count("most recent three fiscal years"), 3)
        self.assertTrue(year_confirmation_required("Microsoft margins over the last three years"))
        self.assertTrue(year_confirmation_required("Microsoft operating margin"))
        self.assertFalse(year_confirmation_required("Microsoft margins in FY2024"))


if __name__ == "__main__":
    unittest.main()
