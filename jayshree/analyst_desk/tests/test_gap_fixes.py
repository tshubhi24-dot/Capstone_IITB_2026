"""Regressions for the implementation gap analysis (docs/gap_closure.md).

Each test names the gap-analysis IDs it closes.
"""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk import lessons, memory
from analystdesk.agent import checks, figures
from analystdesk.agent.checks import check_note
from analystdesk.agent.figures import build_figures, half_up, money
from analystdesk.agent.graph import common_nodes, plan_assumptions, plan_scope_errors
from analystdesk.agent.team import claim_lines, make_judge
from analystdesk.evaluation import figure_present, score

REV = "Revenues/2024/0000000000-24-000001"
REV0 = "Revenues/2023/0000000000-23-000001"
INC = "OperatingIncomeLoss/2024/0000000000-24-000001"
INC0 = "OperatingIncomeLoss/2023/0000000000-23-000001"


def facts(values):
    return patch.object(checks, "_fact_value", side_effect=lambda fid, cache: values.get(fid))


class RoundingAndSignTests(unittest.TestCase):   # F12, F17
    def test_half_up(self):
        self.assertEqual(str(half_up(20.125)), "20.13")
        self.assertEqual(str(half_up(-20.125)), "-20.13")
        self.assertEqual(f"{round(20.125, 2)}", "20.12")   # why round() is not used

    def test_money_keeps_the_sign_in_front(self):
        self.assertEqual(money(245_122_000_000), "$245,122.0M")
        self.assertEqual(money(-1_234_500_000), "-$1,234.5M")

    def test_negative_fact_is_counted_and_verified(self):
        with facts({INC: -1_234_500_000}):
            r = check_note(f"Operating loss was -$1,234.5M [fact: {INC}].")
        self.assertEqual((r.verified_numbers, r.total_numbers), (1, 1))
        with facts({INC: -1_234_500_000}):
            r = check_note(f"Operating loss was $1,234.5M [fact: {INC}].")   # sign dropped
        self.assertFalse(r.ok)


class DenominatorTests(unittest.TestCase):   # F13, F18, F38
    def test_margin_on_negative_revenue_is_refused(self):
        with facts({INC: 20, REV: -100}):
            r = check_note(f"Margin -20.00% [calc: {INC} / {REV}].")
        self.assertIn("not positive", r.issues[0])

    def test_a_ratio_cannot_mix_years(self):   # F07
        with facts({INC0: 20, REV: 100}):
            r = check_note(f"Margin 20.00% [calc: {INC0} / {REV}].")
        self.assertIn("mixes FY2023 and FY2024", r.issues[0])

    def test_a_ratio_cannot_mix_companies(self):   # F07, AE01
        cache = {("ticker", INC): "MSFT", ("ticker", REV): "GOOGL"}
        self.assertEqual(checks._mismatch([(INC, REV)], cache), "mixes MSFT and GOOGL")
        msft = "OperatingIncomeLoss/2024/0000950170-24-087843"
        goog = "RevenueFromContractWithCustomerExcludingAssessedTax/2024/0001652044-25-000014"
        r = check_note(f"Margin 31.00% [calc: {msft} / {goog}].")   # real facts: MSFT income / GOOGL revenue
        self.assertTrue(any("a ratio needs one company" in i for i in r.issues), r.issues)

    def test_growth_from_a_loss_is_refused(self):
        with facts({INC: -10, INC0: -20}):
            r = check_note(f"Income grew -50.00% [growth: {INC} / {INC0}].")
        self.assertIn("zero or negative", r.issues[0])

    def test_figures_offer_no_growth_from_a_loss_but_keep_change_from_zero(self):
        def fin(cik, year):
            return {"revenue": {"val": 100.0 if year == 2024 else 100.0, "fact_id": REV if year == 2024 else REV0,
                                "end": f"{year}-12-31", "start": f"{year}-01-01"},
                    "operating_income": {"val": 5.0 if year == 2024 else 0.0,
                                         "fact_id": INC if year == 2024 else INC0},
                    "pretax_income": None}
        with patch.object(figures, "get_financials", side_effect=fin):
            f = build_figures(["MSFT"], [2023, 2024])
        self.assertEqual(f["MSFT_2024_margin_change"]["text"].split(" [")[0], "+5.00 pp")
        self.assertNotIn("MSFT_2024_income_growth", f)   # from zero: no growth rate

    def test_no_margin_on_non_positive_revenue(self):
        def fin(cik, year):
            return {"revenue": {"val": -100.0, "fact_id": REV, "end": "2024-12-31"},
                    "operating_income": {"val": 20.0, "fact_id": INC}, "pretax_income": None}
        with patch.object(figures, "get_financials", side_effect=fin):
            self.assertNotIn("MSFT_2024_margin", build_figures(["MSFT"], [2024]))


class QuoteScaleTests(unittest.TestCase):   # F11, F22, AE01
    PASSAGE = "Revenue from the segment was $2.2 billion in fiscal 2024."

    def check(self, number):
        return check_note(f"Segment revenue was {number} [MSFT_2024_item7_001].",
                          passage_text=lambda pid: self.PASSAGE)

    def test_same_scale_passes(self):
        self.assertTrue(self.check("$2.2 billion").ok)

    def test_thousands_never_match_billions(self):
        self.assertFalse(self.check("$2.2K").ok)
        self.assertFalse(self.check("$2.2 thousand").ok)

    def test_a_bare_amount_does_not_match_a_scaled_one(self):
        self.assertFalse(self.check("$2.2").ok)


class UnfinishedNoteTests(unittest.TestCase):   # W03
    def test_template_token_is_an_issue(self):
        r = check_note("## What changed\n{WHAT_CHANGED}\n")
        self.assertTrue(any("WHAT_CHANGED" in i for i in r.issues))


class JudgeCoverageTests(unittest.TestCase):   # AE02, AE03, E03
    BODY = "\n".join(f"Claim number {i} about Azure growth in the cloud segment [MSFT_2024_item7_{i:03d}]."
                     for i in range(1, 13))

    class LLM:
        def __init__(self, replies):
            self.replies, self.calls = list(replies), 0

        async def ainvoke(self, msgs):
            self.calls += 1
            reply = self.replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            from langchain_core.messages import AIMessage
            return AIMessage(json.dumps(reply))

    def judge(self, replies, body=None):
        llm = self.LLM(replies)
        out = asyncio.run(make_judge(llm, lambda pid: "passage text")(body or self.BODY))
        return out, llm

    def test_every_cited_claim_is_judged_in_batches(self):
        all_yes = lambda n: {"verdicts": [{"i": i, "supported": True} for i in range(1, n + 1)]}  # noqa: E731
        out, llm = self.judge([all_yes(10), all_yes(2)])
        self.assertEqual((out["checked"], out["reviewed"], out["supported"], llm.calls), (12, 12, 12, 2))
        self.assertEqual(out["issues"], [])

    def test_an_empty_verdict_list_is_not_support(self):
        out, _ = self.judge([{"verdicts": []}], body="A cited claim about margins rising sharply [MSFT_2024_item7_001].")
        self.assertEqual((out["reviewed"], out["supported"]), (0, 0))
        self.assertTrue(out["issues"][0].startswith("Review incomplete"))

    def test_a_judge_outage_blocks(self):
        out, _ = self.judge([TimeoutError()], body="A cited claim about margins rising sharply [MSFT_2024_item7_001].")
        self.assertTrue(out["issues"] and out["issues"][0].startswith("Review incomplete"))
        self.assertIn("TimeoutError", out["error"])

    def test_duplicate_and_out_of_range_verdicts_do_not_count(self):
        body = "First cited claim about the cloud segment growth [MSFT_2024_item7_001].\n" \
               "Second cited claim about the gaming segment decline [MSFT_2024_item7_002]."
        out, _ = self.judge([{"verdicts": [{"i": 1, "supported": True}, {"i": 1, "supported": False},
                                           {"i": 7, "supported": True}, {"i": 2, "supported": "yes"}]}], body)
        self.assertEqual((out["reviewed"], out["supported"]), (1, 1))
        self.assertTrue(out["issues"][-1].startswith("Review incomplete: the judge gave no valid verdict for 1 of 2"))

    def test_code_verified_figures_are_masked_for_the_judge(self):
        line = ("Revenue rose from $307,394.0M [fact: Revenues/2023/0001652044-24-000022] to "
                "$350,018.0M [fact: Revenues/2024/0001652044-25-000014] on cloud growth [GOOGL_2024_item7_044].")
        (text, _), = claim_lines(line)[0]
        self.assertNotIn("307,394", text)
        self.assertEqual(text.count("[code-verified figure]"), 2)
        self.assertIn("on cloud growth", text)

    def test_uncited_lines_are_counted_and_code_sections_skipped(self):
        body = ("# Title\nThe company is expected to keep growing strongly across all of its markets.\n"
                "Cited claim about the cloud segment growing fast [MSFT_2024_item7_001].\n"
                "## Comparability\n- Fiscal years end on different dates for these two companies here.\n")
        cited, uncited = claim_lines(body)
        self.assertEqual((len(cited), uncited), (1, 1))


class RiskYearTests(unittest.TestCase):   # found by the held-out v1 run: FY2022-only plans replanned
    def test_risk_years(self):
        from analystdesk.agent.team import risk_years
        self.assertEqual(risk_years([2022, 2024]), (2024, 2022))   # the plan's own years
        self.assertEqual(risk_years([2024]), (2024, 2023))         # one year: the covered year before
        self.assertIsNone(risk_years([2022]))                      # FY2021 is not covered: no risk-diff


class PlanScopeTests(unittest.TestCase):   # F02, S02, F04, B01
    PLAN = {"companies": ["MSFT"], "fiscal_years": [2024], "sub_questions": [], "outline": []}

    def test_dropped_company_is_shown(self):
        out = plan_assumptions("Compare Microsoft and Apple in fiscal 2024", self.PLAN)
        self.assertTrue(any("NOT in this plan: AAPL" in a for a in out), out)

    def test_bank_operating_margin_request_is_explained(self):
        out = plan_assumptions("JPMorgan operating margin in fiscal 2024",
                               {**self.PLAN, "companies": ["JPM"]})
        self.assertIn("you asked for operating margin", out[-1])

    def test_edited_plan_must_stay_in_coverage(self):
        self.assertEqual(plan_scope_errors(self.PLAN), [])
        self.assertTrue(plan_scope_errors({**self.PLAN, "companies": ["TSLA"]}))
        self.assertTrue(plan_scope_errors({**self.PLAN, "fiscal_years": [2025]}))


class PublishOutcomeTests(unittest.TestCase):   # AE13, AE14, AE15, A04, A05
    STATE = {"draft": {"title": "t", "body": "b", "tickers": ["MSFT"]},
             "published": {"approval_token": "tok"}, "memory_on": True, "trace": []}

    class Tool:
        def __init__(self, result):
            self.result = result

        async def ainvoke(self, args):
            if isinstance(self.result, Exception):
                raise self.result
            return json.dumps(self.result)

    def publish(self, result, remember=None):
        node = common_nodes(None, self.Tool(result))["publish"]
        with patch.object(memory, "remember_published_note", side_effect=remember or (lambda *a: {})):
            return asyncio.run(node(dict(self.STATE)))

    def test_success_needs_a_note_id(self):
        self.assertEqual(self.publish({"ok": True})["outcome"], "publish_unconfirmed")

    def test_lost_response_is_unconfirmed_not_failed(self):
        self.assertEqual(self.publish(TimeoutError("read timed out"))["outcome"], "publish_unconfirmed")

    def test_memory_failure_keeps_the_publication(self):
        def boom(*a):
            raise RuntimeError("disk full")
        out = self.publish({"ok": True, "note_id": 7, "published_at": "2026-11-09"}, remember=boom)
        self.assertEqual(out["outcome"], "published")
        self.assertIn("disk full", out["published"]["memory_error"])


class LimitationsTests(unittest.TestCase):   # R02, E01, AE04
    def test_errors_and_missing_risk_year_become_limitations(self):
        state = {"plan": {"companies": ["MSFT"], "fiscal_years": [2022, 2024], "sub_questions": [], "outline": []},
                 "handoffs": [{"agent": "risk_diff", "company": "MSFT", "round": 0, "errors": ["BUDGET_EXCEEDED"],
                               "passage_ids": ["MSFT_2024_item1a_001"], "fact_ids": [],
                               "confidence": "medium", "findings": "..."}]}
        written = {}

        class LLM:
            def with_structured_output(self, *a, **k):
                return self

            async def ainvoke(self, msgs):
                from analystdesk.agent.graph import Draft
                written["prompt"] = msgs[0].content
                return {"parsed": Draft(title="t", body="Body. {WHAT_CHANGED}", tickers=["MSFT"]), "raw": None}

        with patch("analystdesk.agent.graph.build_figures", return_value={}), \
                patch("analystdesk.agent.graph.comparability_notes", return_value=[]):
            out = asyncio.run(common_nodes(LLM(), None)["write"]({**state, "request": "MSFT risks"}))
        body = out["draft"]["body"]
        self.assertIn("## Limitations", body)
        self.assertIn("BUDGET_EXCEEDED", body)
        self.assertIn("FY2022", body)              # the plan's earlier year, not 2023
        self.assertNotIn("{WHAT_CHANGED}", body)


    def test_a_recovered_error_is_not_a_limitation(self):   # R02: recovered vs unresolved
        state = {"plan": {"companies": ["MSFT"], "fiscal_years": [2024], "sub_questions": [], "outline": []},
                 "request": "MSFT margin",
                 "handoffs": [{"agent": "quant", "company": None, "round": 0, "errors": ["EXEC_ERROR"],
                               "passage_ids": [], "fact_ids": [], "confidence": "medium", "findings": "..."}],
                 "trace": [{"node": "handoff", "agent": "quant", "company": None,
                            "tools": [{"tool": "run_python", "ok": False, "error": "EXEC_ERROR"},
                                      {"tool": "run_python", "ok": True, "error": None}]}]}

        class LLM:
            def with_structured_output(self, *a, **k):
                return self

            async def ainvoke(self, msgs):
                from analystdesk.agent.graph import Draft
                return {"parsed": Draft(title="t", body="Body.", tickers=["MSFT"]), "raw": None}

        with patch("analystdesk.agent.graph.build_figures", return_value={}), \
                patch("analystdesk.agent.graph.comparability_notes", return_value=[]):
            out = asyncio.run(common_nodes(LLM(), None)["write"](state))
        self.assertNotIn("Limitations", out["draft"]["body"])


class ScorerTests(unittest.TestCase):   # G02, G03
    def test_sign_matters_for_percentage_points(self):
        self.assertTrue(figure_present("-12.53 pp", "margin fell -12.53 pp"))
        self.assertFalse(figure_present("-12.53 pp", "margin moved +12.53 pp"))
        self.assertTrue(figure_present("-12.53 pp", "margin declined 12.53 percentage points"))

    def test_rounding_must_be_correct_at_the_shown_precision(self):
        self.assertTrue(figure_present("44.64%", "MSFT margin 44.64%"))
        self.assertTrue(figure_present("44.64%", "MSFT margin 44.6%"))
        self.assertFalse(figure_present("44.64%", "MSFT margin 44.70%"))

    def test_the_figure_must_belong_to_the_right_company(self):
        # the companies swapped: the right digits on the wrong company
        self.assertFalse(figure_present("44.64%", "Alphabet margin 44.64%", "MSFT_2024_margin"))
        self.assertTrue(figure_present("44.64%", "Microsoft margin 44.64%", "MSFT_2024_margin"))
        table = "| Company | Microsoft |\n|---|---|\n| Margin | 44.64% |"
        self.assertTrue(figure_present("44.64%", table, "MSFT_2024_margin"))

    def test_incomplete_review_fails_the_case(self):
        case = {"id": "x", "type": "numeric", "expect": {"figures": [{"text": "44.64%"}]}}
        out = {"text": "Microsoft margin 44.64%",
               "check": {"issues": ["Review incomplete: the judge gave no valid verdict for 1 of 1 cited claims."]}}
        with patch("analystdesk.agent.checks.check_note", return_value=check_note("")):
            r = score(case, out)
        self.assertFalse(r["success"])


class StoreTests(unittest.TestCase):   # L03, M04, M07
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = patch.object(memory, "MEMORY_DB", Path(self.tmp.name) / "m.sqlite")
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_frozen_playbook_is_a_fixed_snapshot(self):
        async def go():
            key = await lessons.add_pending({"when": "comparing margins", "do": "state the basis",
                                             "applies_to": ["margin"]})
            await lessons.review(key, True, "reviewer")
            await lessons.set_frozen(True, "lead")
            frozen = await lessons.frozen_playbook()
            async with memory.open_store() as s:   # the store changes behind the freeze
                await s.adelete(("lessons", "approved"), key)
            used = await lessons.relevant("compare margins")
            return frozen, used
        frozen, used = asyncio.run(go())
        self.assertEqual(len(frozen["version"]), 12)
        self.assertEqual([les["do"] for les in used], ["state the basis"])

    def test_deleted_note_memory_is_not_restored(self):
        async def go():
            await memory.remember_published_note(7, "t", "body", ["MSFT"], "a", "desk")
            message = await memory.forget(("notes", "MSFT"), "note-7")
            again = await memory.remember_published_note(7, "t", "body", ["MSFT"], "a", "desk")
            return message, again, await memory.last_note("MSFT"), await memory.coverage("desk")
        message, again, last, cov = asyncio.run(go())
        self.assertIn("stays in the portal", message)
        self.assertEqual((again, last, cov), ({}, None, []))


class CalibrationTests(unittest.TestCase):   # G06
    def test_undefined_kappa_is_none(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "calibrate_judge", Path(__file__).resolve().parent.parent / "scripts" / "calibrate_judge.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertIsNone(mod.cohen_kappa([True] * 5, [True] * 5))
        self.assertAlmostEqual(mod.cohen_kappa([True, False, True, False], [True, False, True, False]), 1.0)


if __name__ == "__main__":
    unittest.main()
