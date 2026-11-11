"""End-to-end test of the C2 team, offline (no API key, no cost).

The whole graph runs: input guard -> plan -> plan gate (interrupt) -> five
specialists in parallel -> gather -> writer -> compliance critic -> note gate
(interrupt) -> publish. Every tool call goes through the real MCP servers in
memory (filings-kb with a small fake index, edgar on the cached SEC data, the
local sandbox, a throwaway portal DB), through the real hooks, with a SQLite
checkpointer in a temp folder so both gates are a real stop-and-resume.

Only the language model is scripted: it behaves like a well-behaved model
that follows the specialist prompts. Live model behaviour is checked with a
real run on the developer's machine; this test guards the plumbing.
"""

import asyncio
import contextlib
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage, ToolMessage

PASSAGES = {
    "MSFT_2024_item7_020": ("MSFT", 2024, "item7", "Microsoft Cloud growth drove Intelligent Cloud revenue."),
    "GOOGL_2024_item7_012": ("GOOGL", 2024, "item7", "Google Search and Google Cloud drove revenue growth."),
    "MSFT_2024_item1a_008": ("MSFT", 2024, "item1a", "AI regulation and competition may harm our business."),
    "MSFT_2023_item1a_007": ("MSFT", 2023, "item1a", "Competition in cloud services may harm our business."),
    "GOOGL_2024_item1a_020": ("GOOGL", 2024, "item1a", "We rely on third parties for manufacturing."),
    "GOOGL_2023_item1a_019": ("GOOGL", 2023, "item1a", "Privacy and data protection rules may affect us."),
}


class _FakeRetriever:
    pid_to_passage = {pid: {"passage_id": pid, "company": c, "fiscal_year": y, "item": i, "kind": "text",
                            "accession": None, "text": t} for pid, (c, y, i, t) in PASSAGES.items()}

    def search(self, query, top_k=5, company=None, year=None, item=None, **_):
        return [{**p, "score": 1.0} for p in self.pid_to_passage.values()
                if (not company or p["company"] == company) and (not year or p["fiscal_year"] == year)
                and (not item or p["item"] == item)][:top_k]


def _usage(n=100):
    return {"input_tokens": n, "output_tokens": 20, "total_tokens": n + 20}


def _ai(text="", calls=()):
    return AIMessage(content=text, usage_metadata=_usage(),
                     tool_calls=[{"name": n, "args": a, "id": f"call{i}"} for i, (n, a) in enumerate(calls)])


PROMPTS = []        # every system prompt the scripted model was given, for assertions


class _Specialist:
    """Scripted ReAct turns for one specialist (C2) or the single agent (C1), chosen from the prompt."""

    async def ainvoke(self, msgs):
        system = msgs[0].content
        if not any(isinstance(m, AIMessage) for m in msgs):
            PROMPTS.append(system)
        step = sum(isinstance(m, AIMessage) for m in msgs)       # model turns so far
        m = re.search(r"covering (\w+)|factors \(10-K Item 1A\) for (\w+)", system)
        company = next((g for g in m.groups() if g), None) if m else None
        if system.startswith("ROLE: You are a filings researcher"):
            if step == 0:
                return _ai(calls=[("search_filings", {"query": "operating income drivers", "company": company,
                                                      "item": "item7", "fiscal_year": 2024})])
            pid = next(p for p in PASSAGES if p.startswith(f"{company}_2024_item7"))
            return _ai(f"FY2024: cloud growth drove results [{pid}].")
        if system.startswith("ROLE: You are the quant"):
            if step == 0:
                return _ai(calls=[("get_financials", {"ticker": "MSFT", "fiscal_year": 2024}),
                                  ("get_financials", {"ticker": "GOOGL", "fiscal_year": 2024})])
            if step == 1:
                return _ai(calls=[("run_python", {"code": "result = round(data['op'] / data['rev'] * 100, 2)",
                                                  "data": {"op": 109433, "rev": 245122}})])
            return _ai("Margins computed in the sandbox; figures from get_financials with their fact ids.")
        if system.startswith("ROLE: You compare risk factors"):
            if step == 0:
                return _ai(calls=[("search_filings", {"query": "risk factors", "company": company,
                                                      "item": "item1a", "fiscal_year": y}) for y in (2024, 2023)])
            return _ai(f"Changed: AI and competition wording [{company}_2024_item1a].")
        if system.startswith("ROLE: You are an equity research analyst"):      # C1 single agent
            if step == 0:
                return _ai(calls=[("get_financials", {"ticker": "MSFT", "fiscal_year": 2024}),
                                  ("get_financials", {"ticker": "GOOGL", "fiscal_year": 2024}),
                                  ("search_filings", {"query": "operating income drivers", "company": "MSFT",
                                                      "item": "item7", "fiscal_year": 2024})])
            return _ai("Findings with fact ids and passage ids [MSFT_2024_item7_020].")
        raise AssertionError("unexpected specialist prompt: " + system[:80])


class _Structured:
    def __init__(self, schema, include_raw=False):
        self.schema = schema
        self.include_raw = include_raw

    async def ainvoke(self, msgs):
        name = self.schema.__name__
        if name == "Plan":
            parsed = self.schema(companies=["MSFT", "GOOGL"], fiscal_years=[2023, 2024],
                                 sub_questions=["How did operating margins move?", "What drove them?",
                                                "Which risk factors changed?"],
                                 outline=["Margins", "Drivers", "Risks"])
        elif name == "Draft":
            parsed = self.schema(
                title="Microsoft and Alphabet: operating margins FY2024 [MSFT_2024_item7_020]",
                body=("## Margins\nMicrosoft's FY2024 operating margin was {MSFT_2024_margin}; "
                      "Alphabet's was {GOOGL_2024_margin} [MSFT_2024_item7_020].\n\n## Drivers\n"
                      "- Cloud growth drove Microsoft's results in its latest year [MSFT_2024_item7_020].\n"
                      "- Search and cloud drove Alphabet's results in its latest year [GOOGL_2024_item7_012].\n"),
                tickers=["MSFT", "GOOGL"])
        elif name == "Handoff":
            # Fix 3 (Module 4 - Security): the hand-off turn. A well-behaved
            # specialist copies quotes out of the passages it actually read and
            # names the fact_ids its tool results gave it, inventing neither --
            # so both are taken from the ToolMessages in its own context.
            seen = "\n".join(m.content for m in msgs if isinstance(m, ToolMessage))
            if "fact_id" in msgs[-1].content:
                ids = sorted(set(re.findall(r"[A-Za-z]+/\d{4}/\d{10}-\d{2}-\d{6}", seen)))
                parsed = self.schema(facts=[{"fact_id": f} for f in ids[:3]])
            else:
                parsed = self.schema(claims=[{"passage_id": p, "quote": PASSAGES[p][3]}
                                             for p in PASSAGES if p in seen])
        else:
            raise AssertionError("unexpected structured output: " + name)
        if self.include_raw:
            return {"parsed": parsed, "raw": AIMessage(content="", usage_metadata=_usage())}
        return parsed


class _ScriptedLLM:
    def bind_tools(self, tools):
        return _Specialist()

    def with_structured_output(self, schema, include_raw=False):
        return _Structured(schema, include_raw)


class _Judge:
    async def ainvoke(self, msgs):
        n = msgs[-1].content.count("ITEM ")
        verdicts = [{"i": i, "supported": True, "reason": "passage says so"} for i in range(1, n + 1)]
        return AIMessage(content=json.dumps({"verdicts": verdicts}), usage_metadata=_usage())


async def _run(tmp: Path, mode: str = "c2") -> dict:
    from fastmcp import Client
    from langchain_mcp_adapters.tools import load_mcp_tools
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.types import Command
    from analystdesk.agent.runtime import RESEARCH_TOOLS
    from analystdesk.agent.graph import build_graph
    from analystdesk.agent.team import build_team_graph, make_judge
    from analystdesk.servers import edgar_server, filings_kb, portal, sandbox

    filings_kb.set_retriever(_FakeRetriever())
    try:
        async with contextlib.AsyncExitStack() as stack:
            tools = []
            for module in (filings_kb, edgar_server, sandbox, portal):
                client = await stack.enter_async_context(Client(module.mcp))
                tools += await load_mcp_tools(client.session)
            research = [t for t in tools if t.name in RESEARCH_TOOLS]
            publish = next(t for t in tools if t.name == "publish_note")
            saver = await stack.enter_async_context(AsyncSqliteSaver.from_conn_string(str(tmp / "ck.sqlite")))
            text = lambda pid: PASSAGES.get(pid, (None,) * 4)[3]
            if mode == "c2":
                graph = build_team_graph(_ScriptedLLM(), research, publish, text,
                                         judge_llm=_Judge(), require_critic=True)
            else:
                graph = build_graph(_ScriptedLLM(), research, publish, text,
                                    critic=make_judge(_Judge(), text), require_critic=True)
            graph = graph.compile(checkpointer=saver)
            config = {"configurable": {"thread_id": "e2e"}, "recursion_limit": 150}
            request = "Compare Microsoft's and Alphabet's operating margins in fiscal 2023 and 2024"
            await graph.ainvoke({"request": request, "mode": mode, "memory_on": False}, config)
            gates = [(await graph.aget_state(config)).next]
            await graph.ainvoke(Command(resume={"action": "approve"}), config)          # plan gate
            gates.append((await graph.aget_state(config)).next)
            gate = (await graph.aget_state(config)).tasks[0].interrupts[0].value
            await graph.ainvoke(Command(resume={"action": "approve", "approver": "tester"}), config)  # note gate
            final = await graph.aget_state(config)
            with portal._connect() as con:
                row = con.execute("SELECT context_json FROM approval_context WHERE note_id = ?",
                                  (final.values["published"]["note_id"],)).fetchone()
            return {"gates": gates, "values": final.values, "next": final.next,
                    "gate_context": gate["review_context"], "stored_context": json.loads(row["context_json"])}
    finally:
        filings_kb.set_retriever(None)


def _offline(mode="c2", **extra_env):
    """Run one request end to end, offline, and return the final state."""
    PROMPTS.clear()
    with tempfile.TemporaryDirectory() as d:
        env = {"PORTAL_DB": str(Path(d) / "portal.db"), "APPROVAL_SECRET": "test-secret",
               "AGENT_LESSONS": "0", "SANDBOX_MODE": "local", **extra_env}
        with patch.dict(os.environ, env):
            os.environ.pop("AGENT_MAX_TOOL_CALLS", None) if "AGENT_MAX_TOOL_CALLS" not in extra_env else None
            return asyncio.run(_run(Path(d), mode))


class TeamEndToEndTests(unittest.TestCase):
    def test_c2_runs_from_request_to_published_note(self):
        out = _offline("c2")
        v = out["values"]

        # both human gates stopped the run, and it resumed from the checkpoint each time
        self.assertEqual(out["gates"][0], ("review_plan",))
        self.assertEqual(out["gates"][1], ("review_note",))
        self.assertEqual(out["next"], ())

        # five specialists ran in parallel and each handed back a typed message
        handoffs = {(h["agent"], h.get("company")) for h in v["handoffs"]}
        self.assertEqual(handoffs, {("researcher", "MSFT"), ("researcher", "GOOGL"), ("quant", None),
                                    ("risk_diff", "MSFT"), ("risk_diff", "GOOGL")})

        # every tool call succeeded: no failed searches, no budget hits
        tool_events = [t for e in v["trace"] if e["node"] == "handoff" for t in e["tools"]]
        self.assertEqual(len(tool_events), 2 + 3 + 4)
        self.assertTrue(all(t["ok"] for t in tool_events), tool_events)
        self.assertTrue(all(h["errors"] == [] for h in v["handoffs"]))
        for handoff in (h for h in v["handoffs"] if h["agent"] == "risk_diff"):
            pair, = handoff["risk_coverage"]
            self.assertEqual((pair["earlier_year"], pair["later_year"], pair["status"]),
                             (2023, 2024, "excerpt_only"))
            self.assertTrue(pair["earlier_passages"] and pair["later_passages"])
            self.assertEqual(handoff["confidence"], "medium")

        # per-specialist cost is recorded (change 5)
        self.assertTrue(all(h["model_calls"] > 0 and h["tokens"] > 0 for h in v["handoffs"]))

        # the critic passed the note: numbers checked against XBRL in code, claims by the judge
        self.assertTrue(v["check"]["ok"], v["check"])
        self.assertGreater(v["check"]["verified"], 0)
        self.assertEqual(v["check"]["verified"], v["check"]["total"])
        self.assertEqual(v["check"]["claims"]["supported"], v["check"]["claims"]["checked"])
        self.assertIn("44.64%", v["draft"]["body"])          # MSFT FY2024 margin rendered by code

        # the approved note was published through the portal
        self.assertEqual(v["outcome"], "published")
        self.assertTrue(v["published"]["note_id"])
        self.assertEqual(out["stored_context"], out["gate_context"])
        self.assertEqual(out["stored_context"]["plan"], v["plan"])
        self.assertEqual(out["stored_context"]["check"], v["check"])
        self.assertEqual(out["stored_context"]["evidence_snapshot"], v["review_snapshot"])
        self.assertTrue(v["review_snapshot"]["facts"])
        self.assertTrue(v["review_snapshot"]["passages"])

        # change 2/2b: each specialist got its share of the same total C1 gets (2 companies -> 36)
        budgets = {(e["agent"], e.get("company")): e["budget"] for e in v["trace"] if e["node"] == "handoff"}
        self.assertEqual(budgets, {("researcher", "MSFT"): 6, ("researcher", "GOOGL"): 6, ("quant", None): 12,
                                   ("risk_diff", "MSFT"): 6, ("risk_diff", "GOOGL"): 6})
        self.assertEqual(sum(budgets.values()), 36)
        self.assertTrue(any("At most 12 tool calls" in p for p in PROMPTS if "the quant" in p))
        self.assertTrue(any("At most 6 tool calls" in p for p in PROMPTS if "filings researcher" in p))

    def test_c2_specialist_budget_is_enforced_by_the_hook(self):
        # a fixed total of 8 for two companies leaves 1 call per researcher / risk-diff
        v = _offline("c2", AGENT_MAX_TOOL_CALLS="8")["values"]
        risk = [h for h in v["handoffs"] if h["agent"] == "risk_diff"]
        self.assertEqual(len(risk), 2)
        for h in risk:                                  # it asked for 2 searches; the hook refused one
            self.assertEqual(h["tool_calls"], 1)
            self.assertIn("BUDGET_EXCEEDED", h["errors"])
            self.assertEqual(h["risk_coverage"][0]["status"], "missing_evidence")
            self.assertEqual(h["confidence"], "low")
        self.assertEqual(v["outcome"], "published")     # the run still finishes


class SingleAgentEndToEndTests(unittest.TestCase):
    def test_c1_runs_from_request_to_published_note_with_the_same_budget(self):
        from analystdesk.agent import graph as graph_module
        made = []

        class _RecordingHooks(graph_module.Hooks):
            def __init__(self, *args, **kwargs):     # Hooks is a dataclass: record each instance
                super().__init__(*args, **kwargs)
                made.append(self)

        with patch.object(graph_module, "Hooks", _RecordingHooks):
            out = _offline("c1")
        v = out["values"]
        # the pre-tool hook was given the same run budget as the prompt states (2 companies -> 36)
        self.assertTrue(made)
        self.assertEqual({h.max_calls_per_agent for h in made}, {36})
        self.assertEqual(out["gates"], [("review_plan",), ("review_note",)])
        self.assertTrue(any("budget of 36 tool calls" in p for p in PROMPTS), PROMPTS)  # 2 companies
        tool_msgs = [m for m in v["messages"] if isinstance(m, ToolMessage)]
        self.assertEqual(len(tool_msgs), 3)
        self.assertTrue(all('"ok":true' in str(m.content).replace(" ", "") for m in tool_msgs))
        self.assertTrue(v["check"]["ok"], v["check"])
        self.assertIn("44.64%", v["draft"]["body"])
        self.assertEqual(v["outcome"], "published")

    def test_c1_stops_researching_when_a_turn_would_exceed_the_budget(self):
        # Existing C1 behaviour, unchanged: the router counts the calls a turn asks for; if they would
        # pass the budget it goes straight to the writer, so no tool runs at all (the hook is a backstop)
        v = _offline("c1", AGENT_MAX_TOOL_CALLS="2")["values"]
        self.assertTrue(any("budget of 2 tool calls" in p for p in PROMPTS))
        self.assertEqual([m for m in v["messages"] if isinstance(m, ToolMessage)], [])
        self.assertEqual(v["outcome"], "published")


if __name__ == "__main__":
    unittest.main()
