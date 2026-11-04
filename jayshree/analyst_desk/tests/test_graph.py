import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from analystdesk.agent.runtime import _NoModel
from analystdesk.agent.graph import Plan, build_graph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command


class _PlanModel:
    def with_structured_output(self, model, include_raw=False):
        return self

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, messages):
        plan = Plan(
            companies=["MSFT"],
            fiscal_years=[2024],
            sub_questions=["What changed in Microsoft's financials?"],
            outline=["Financial performance"],
        )
        return {"parsed": plan, "raw": SimpleNamespace(usage_metadata={"total_tokens": 1})}


async def _resume_plan_gate(graph, action="cancel"):
    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "cancel-plan-test"}}
    async for _ in app.astream(
        {"request": "Compare Microsoft margins in 2024", "memory_on": False},
        config,
        stream_mode="updates",
    ):
        pass

    snapshot = await app.aget_state(config)
    if not snapshot.tasks or not snapshot.tasks[0].interrupts:
        raise AssertionError("workflow did not pause at the plan approval gate")

    updates = []
    async for update in app.astream(
        Command(resume={"action": action}),
        config,
        stream_mode="updates",
    ):
        updates.extend(update)
    final = await app.aget_state(config)
    return final.values, updates, final.next


class GraphShapeTests(unittest.TestCase):
    def test_nodes_gates_and_loops(self):
        g = build_graph(_NoModel(), [], None).compile().get_graph()
        nodes = set(g.nodes)
        for n in ("input_guard", "plan", "review_plan", "research", "tools", "replan",
                  "write", "check", "review_note", "publish"):
            self.assertIn(n, nodes)
        edges = {(e.source, e.target) for e in g.edges}
        self.assertIn(("tools", "replan"), edges)         # replanning
        self.assertIn(("check", "count_revision"), edges)  # self-correction loop
        self.assertIn(("review_note", "check"), edges)    # edited note is re-checked
        self.assertIn(("review_plan", "__end__"), edges)  # cancelled plan stops before research

    def test_c1_cancel_at_plan_gate_stops_before_research(self):
        import os
        from analystdesk.agent.graph import build_graph

        with patch.dict(os.environ, {"AGENT_LESSONS": "0"}):
            values, updates, next_nodes = asyncio.run(
                _resume_plan_gate(build_graph(_PlanModel(), [], None))
            )

        self.assertEqual(values["outcome"], "cancelled")
        self.assertEqual(next_nodes, ())
        self.assertNotIn("research", [node for update in updates for node in update])
        self.assertNotIn("write", [node for update in updates for node in update])

    def test_invalid_plan_decision_does_not_start_research(self):
        import os
        from analystdesk.agent.graph import build_graph

        with patch.dict(os.environ, {"AGENT_LESSONS": "0"}):
            with self.assertRaisesRegex(ValueError, "approve, edit, or cancel"):
                asyncio.run(_resume_plan_gate(build_graph(_PlanModel(), [], None), action="unexpected"))




class ToolJsonTests(unittest.TestCase):
    def test_parses_adapter_content_blocks(self):
        from analystdesk.agent.graph import tool_json
        inner = '{"ok":true,"note_id":1}'
        self.assertEqual(tool_json([{"type": "text", "text": inner}])["note_id"], 1)
        self.assertEqual(tool_json('[{"type": "text", "text": "{\\"ok\\":true,\\"note_id\\":2}"}]')["note_id"], 2)
        self.assertEqual(tool_json('{"ok": false}'), {"ok": False})
        self.assertEqual(tool_json("not json"), {})


class WhatChangedSectionTests(unittest.TestCase):
    """Live run 1cc35ab6 (3 Nov): the writer left {WHAT_CHANGED} with no heading, so the
    comparison with the last note read as the note's last lines and went unnoticed."""

    CHANGED = "- margin FY2024: unchanged since the last note at 42.29%."

    def test_bare_placeholder_gets_the_heading(self):
        from analystdesk.agent.graph import insert_changes
        body = insert_changes("Margin was 42.29%.\n\n{WHAT_CHANGED}", self.CHANGED)
        self.assertIn("## What changed since our last note\n" + self.CHANGED, body)

    def test_writer_heading_is_not_repeated(self):
        from analystdesk.agent.graph import insert_changes
        body = insert_changes("Text.\n\n## What changed since our last note\n{WHAT_CHANGED}", self.CHANGED)
        self.assertEqual(body.count("What changed since our last note"), 1)
        self.assertIn(self.CHANGED, body)

    def test_no_placeholder_appends_the_section(self):
        from analystdesk.agent.graph import insert_changes
        body = insert_changes("Text.", self.CHANGED)
        self.assertTrue(body.endswith("## What changed since our last note\n" + self.CHANGED))

    def test_slot_is_filled_when_there_is_nothing_to_compare(self):
        """Memory eval m01/m04 (4 Nov): with memory off, the writer echoed the request's
        "what changed" heading and left {WHAT_CHANGED}, which nothing filled."""
        from analystdesk.agent.graph import insert_changes
        off = insert_changes("### What changed since our last note\n{WHAT_CHANGED}", "", memory_on=False)
        self.assertNotIn("{WHAT_CHANGED}", off)
        self.assertIn("Memory was not used", off)
        on = insert_changes("{WHAT_CHANGED}", "", memory_on=True)
        self.assertIn("no previous note", on)
        self.assertEqual(insert_changes("Text.", ""), "Text.")



class TeamGraphTests(unittest.TestCase):
    def test_team_shape(self):
        from analystdesk.agent.team import build_team_graph
        g = build_team_graph(_NoModel(), [], None).compile().get_graph()
        for n in ("researcher", "quant", "risk_diff", "gather", "replan", "write", "check", "publish"):
            self.assertIn(n, set(g.nodes))
        edges = {(e.source, e.target) for e in g.edges}
        for a in ("researcher", "quant", "risk_diff"):
            self.assertIn(("review_plan", a), edges)   # parallel fan-out
            self.assertIn((a, "gather"), edges)
        self.assertIn(("gather", "replan"), edges)
        self.assertIn(("review_plan", "__end__"), edges)

    def test_c2_cancel_at_plan_gate_prevents_team_fanout(self):
        import os
        from analystdesk.agent.team import build_team_graph

        with patch.dict(os.environ, {"AGENT_LESSONS": "0"}):
            values, updates, next_nodes = asyncio.run(
                _resume_plan_gate(build_team_graph(_PlanModel(), [], None))
            )

        self.assertEqual(values["outcome"], "cancelled")
        self.assertEqual(next_nodes, ())
        executed_nodes = [node for update in updates for node in update]
        self.assertFalse({"researcher", "quant", "risk_diff", "gather", "write"} & set(executed_nodes))


class HooksTests(unittest.TestCase):
    def test_permission_budget_and_logging(self):
        import asyncio
        from analystdesk.agent.hooks import Hooks
        h = Hooks(max_calls_per_agent=2)
        self.assertEqual(asyncio.run(h.pre("researcher", "run_python"))["error"]["code"], "PERMISSION_DENIED")
        self.assertIsNone(asyncio.run(h.pre("researcher", "search_filings", "researcher/MSFT")))
        self.assertIsNone(asyncio.run(h.pre("researcher", "search_filings", "researcher/MSFT")))
        self.assertEqual(asyncio.run(h.pre("researcher", "search_filings", "researcher/MSFT"))["error"]["code"],
                         "BUDGET_EXCEEDED")
        self.assertIsNone(asyncio.run(h.pre("researcher", "search_filings", "researcher/GOOGL")))
        ev = h.post("quant", "get_fact", {}, '{"ok": true}', 3.2)
        self.assertTrue(ev["ok"])
        self.assertFalse(asyncio.run(h.pre("publisher", "publish_note")))   # only the publisher may write


class _ScriptedModel:
    """Fake chat model for tests: replays fixed replies, no API calls."""
    def __init__(self, replies):
        self.replies = list(replies)

    def bind_tools(self, tools):
        return self

    async def ainvoke(self, msgs):
        return self.replies.pop(0)


class _FakeTool:
    def __init__(self, name, result):
        self.name, self.result = name, result

    async def ainvoke(self, args):
        return self.result


def _reply(prompt_tokens, total_tokens, tool_calls=None, text=""):
    from langchain_core.messages import AIMessage
    return AIMessage(content=text, tool_calls=tool_calls or [],
                     usage_metadata={"input_tokens": prompt_tokens, "output_tokens": total_tokens - prompt_tokens,
                                     "total_tokens": total_tokens})


class SpecialistMeteringTests(unittest.TestCase):
    """L11: each specialist records its own calls, tokens and largest prompt."""

    def test_specialist_records_its_own_cost(self):
        import asyncio
        from analystdesk.agent.hooks import Hooks
        from analystdesk.agent.team import run_specialist
        search = _FakeTool("search_filings",
                           '{"ok": true, "passages": [{"passage_id": "MSFT_2024_item7_017"}]}')
        model = _ScriptedModel([
            _reply(1200, 1300, tool_calls=[{"name": "search_filings", "args": {"query": "drivers"},
                                            "id": "c1"}]),
            _reply(2500, 2650, text="FY2024: cloud growth [MSFT_2024_item7_017]"),
        ])
        handoff, tokens = asyncio.run(run_specialist(
            "researcher", "MSFT", model, {"search_filings": search}, "system", Hooks(), 6))
        self.assertEqual(handoff.model_calls, 2)
        self.assertEqual(handoff.largest_prompt, 2500)
        self.assertEqual(handoff.tokens, 1300 + 2650)
        self.assertEqual(tokens, handoff.tokens)          # run total unchanged in meaning
        self.assertEqual(handoff.tool_calls, 1)
        self.assertEqual(handoff.passage_ids, ["MSFT_2024_item7_017"])


class SpecialistPromptTests(unittest.TestCase):
    """The specialist prompts must show search_filings with its required query.

    Live run c5test (31 Oct): the prompts showed search_filings(company=..., item=...) without a
    query, so every researcher's and risk-diff's first search was rejected by the tool and 7 of 24
    tool calls were wasted.
    """

    def _rendered(self):
        from analystdesk.agent.team import specialist_budgets
        from analystdesk.llm_config import LLM_CONFIG
        return {agent: LLM_CONFIG.format_prompt(f"specialist_{agent}", company="MSFT",
                                                companies="MSFT, GOOGL", years=[2023, 2024],
                                                latest=2024, prior=2023,
                                                budget=specialist_budgets(2)[agent], plan="{}")
                for agent in ("researcher", "quant", "risk_diff")}

    def test_prompts_render(self):
        for agent, text in self._rendered().items():
            self.assertNotIn("{", text.replace("{}", ""), agent)   # no placeholder left unfilled

    def test_every_search_filings_example_shows_a_query(self):
        import re
        rendered = self._rendered()
        for agent in ("researcher", "risk_diff"):
            text = rendered[agent]
            examples = re.findall(r"search_filings\s*\(([^)]*)\)", text)
            self.assertTrue(examples, f"{agent} prompt shows no search_filings example")
            for args in examples:
                self.assertIn("query=", args, f"{agent}: search_filings example without query: {args}")
            self.assertIn("needs a query", text)

    def test_prompts_say_search_results_already_hold_the_text(self):
        """Change 2b: live runs c2test and 0c8cbf5f - risk-diffs spent their budget re-reading
        passages one by one with get_passage although the search had returned their text."""
        rendered = self._rendered()
        for agent in ("researcher", "risk_diff"):
            self.assertIn("already contain each passage's full text", rendered[agent], agent)
            self.assertIn("get_passage only for a passage id you have not seen", rendered[agent], agent)
        self.assertIn("Search both years (2023 and 2024) before anything else", rendered["risk_diff"])

    def test_search_results_carry_the_full_passage_text(self):
        """The prompt's claim is true at the real MCP server: search_filings returns full text."""
        import asyncio
        from fastmcp import Client
        from analystdesk.servers import filings_kb
        long_text = "Azure and other cloud services revenue grew. " * 40

        class _Retriever:
            pid_to_passage = {}

            def search(self, query, top_k=5, company=None, year=None, item=None, **_):
                return [{"passage_id": "MSFT_2024_item1a_001", "company": "MSFT", "fiscal_year": 2024,
                         "item": "item1a", "kind": "text", "accession": None, "text": long_text,
                         "score": 1.0}]

        async def call():
            async with Client(filings_kb.mcp) as client:
                return await client.call_tool("search_filings", {"query": "cloud", "company": "MSFT",
                                                                   "item": "item1a"})

        filings_kb.set_retriever(_Retriever())
        try:
            res = asyncio.run(call())
        finally:
            filings_kb.set_retriever(None)
        self.assertEqual(res.structured_content["passages"][0]["text"], long_text)

    def test_search_without_query_is_rejected_by_the_tool(self):
        """Reproduces the live failure at the real MCP server: no query -> not ok; with query -> ok."""
        import asyncio
        from fastmcp import Client
        from analystdesk.servers import filings_kb

        class _Retriever:
            pid_to_passage = {}

            def search(self, query, top_k=5, company=None, year=None, item=None, **_):
                return [{"passage_id": "MSFT_2024_item7_020", "company": "MSFT", "fiscal_year": 2024,
                         "item": "item7", "kind": "text", "accession": None, "text": "Cloud grew.",
                         "score": 1.0}]

        async def call(args):
            async with Client(filings_kb.mcp) as client:
                return await client.call_tool("search_filings", args, raise_on_error=False)

        filings_kb.set_retriever(_Retriever())
        try:
            without = asyncio.run(call({"company": "MSFT", "item": "item7", "fiscal_year": 2024}))
            with_query = asyncio.run(call({"query": "cloud growth", "company": "MSFT", "item": "item7",
                                           "fiscal_year": 2024}))
        finally:
            filings_kb.set_retriever(None)
        self.assertTrue(without.is_error)
        self.assertTrue(with_query.structured_content["ok"])


class SameBudgetTests(unittest.TestCase):
    """Change 2: C1 and C2 get the same total tool budget (brief: "same tools and budget")."""

    def setUp(self):
        from unittest.mock import patch
        patcher = patch.dict("os.environ")      # tests must not inherit an override
        patcher.start()
        self.addCleanup(patcher.stop)
        import os
        for k in ("AGENT_MAX_TOOL_CALLS",):
            os.environ.pop(k, None)

    def test_budget_grows_with_companies(self):
        from analystdesk.agent.graph import tool_budget
        self.assertEqual([tool_budget(n) for n in (1, 2, 3)], [24, 36, 48])
        self.assertEqual(tool_budget(0), 24)                 # never below one company

    def test_team_shares_add_up_to_the_single_agent_budget(self):
        from analystdesk.agent.graph import tool_budget
        from analystdesk.agent.team import specialist_budgets
        for n in range(1, 8):
            b = specialist_budgets(n)
            self.assertEqual(b["quant"] + n * (b["researcher"] + b["risk_diff"]), tool_budget(n), n)
            self.assertGreaterEqual(b["quant"], 3 * n + 3, n)          # fetches + run_python with a retry
            self.assertEqual(b["researcher"], b["risk_diff"])
            self.assertGreaterEqual(b["researcher"], 1)

    def test_two_company_split(self):
        from analystdesk.agent.team import specialist_budgets
        self.assertEqual(specialist_budgets(2), {"researcher": 6, "risk_diff": 6, "quant": 12})

    def test_one_and_three_company_splits(self):
        """Change 2b: one company leaves the quant 3 fetches + 3 sandbox calls (was 3 + 1)."""
        from analystdesk.agent.team import specialist_budgets
        self.assertEqual(specialist_budgets(1), {"researcher": 9, "risk_diff": 9, "quant": 6})
        self.assertEqual(specialist_budgets(3), {"researcher": 6, "risk_diff": 6, "quant": 12})

    def test_quant_can_retry_the_sandbox(self):
        """Live run 0c8cbf5f: run_python timed out twice and the third call was refused."""
        from analystdesk.agent.team import specialist_budgets
        for n in range(1, 8):
            self.assertGreaterEqual(specialist_budgets(n)["quant"] - 3 * n, 3, n)

    def test_fixed_override_applies_to_both(self):
        import os
        from analystdesk.agent.graph import tool_budget
        from analystdesk.agent.team import specialist_budgets
        os.environ["AGENT_MAX_TOOL_CALLS"] = "20"
        self.assertEqual(tool_budget(2), 20)
        b = specialist_budgets(2)
        self.assertEqual(b["quant"] + 2 * (b["researcher"] + b["risk_diff"]), 20)


if __name__ == "__main__":
    unittest.main()
