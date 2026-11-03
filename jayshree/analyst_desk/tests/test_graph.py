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


if __name__ == "__main__":
    unittest.main()
