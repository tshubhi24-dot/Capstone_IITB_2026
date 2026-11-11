"""Memory off means no earlier notes at all: not even through the get_past_notes tool."""

import asyncio
import os
import unittest
from unittest.mock import patch

from analystdesk.agent.runtime import research_tools
from tests.integration.test_graph import _FakeTool
from tests.integration.test_graph import _ScriptedModel
from tests.integration.test_graph import _reply

NAMES = ["search_filings", "get_passage", "get_financials", "get_past_notes", "publish_note"]


def _names(tools):
    return sorted(t.name for t in tools)


class ResearchToolsTests(unittest.TestCase):
    def setUp(self):
        self.tools = [_FakeTool(n, "{}") for n in NAMES]

    def test_memory_on_keeps_past_notes_and_never_the_write_tool(self):
        with patch.dict(os.environ, {"AGENT_EVAL": "0"}):
            names = _names(research_tools(self.tools, True))
        self.assertIn("get_past_notes", names)
        self.assertNotIn("publish_note", names)

    def test_memory_off_drops_past_notes(self):
        names = _names(research_tools(self.tools, False))
        self.assertNotIn("get_past_notes", names)
        self.assertIn("search_filings", names)

    def test_evaluation_runs_never_get_past_notes(self):
        with patch.dict(os.environ, {"AGENT_EVAL": "1"}):
            self.assertNotIn("get_past_notes", _names(research_tools(self.tools, True)))


class MissingToolTests(unittest.TestCase):
    def test_specialist_gets_an_error_not_a_crash_for_a_tool_the_run_lacks(self):
        from analystdesk.agent.hooks import Hooks
        from analystdesk.agent.team import run_specialist
        model = _ScriptedModel([
            _reply(100, 120, tool_calls=[{"name": "get_past_notes", "args": {"ticker": "MSFT"}, "id": "c1"}]),
            _reply(200, 220, text="No earlier notes available."),
        ])
        handoff, _ = asyncio.run(run_specialist("risk_diff", "MSFT", model, {}, "system", Hooks(), 4))
        self.assertEqual(handoff.errors, ["NOT_AVAILABLE"])
        self.assertEqual(handoff.tool_calls, 0)


if __name__ == "__main__":
    unittest.main()
