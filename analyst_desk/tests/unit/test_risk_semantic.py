import asyncio
import json
import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage

from analystdesk.evaluation.scoring import review_risk_change
from analystdesk.evaluation.scoring import run_one
from analystdesk.evaluation.scoring import score


CASE = {
    "id": "risk", "type": "risk_change",
    "request": "How did MSFT risks change?",
    "expect": {"risk_change": {"ticker": "MSFT", "years": [2023, 2024],
                                "expected_interpretation": "The disclosure became more specific."}},
}
ANSWER = ("The disclosure became more specific [MSFT_2023_item1a_001] "
          "[MSFT_2024_item1a_002].")


class Judge:
    def __init__(self, response):
        self.response = response
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        if isinstance(self.response, Exception):
            raise self.response
        return AIMessage(content=self.response)


class RiskSemanticTests(unittest.TestCase):
    def test_judge_receives_reference_only_at_evaluation_boundary(self):
        judge = Judge(json.dumps({"supported": True, "reason": "supported"}))
        review = asyncio.run(review_risk_change(CASE, {"text": ANSWER}, judge, lambda _: "filing text"))
        self.assertEqual(review["status"], "complete")
        self.assertTrue(review["supported"])
        self.assertIn(CASE["expect"]["risk_change"]["expected_interpretation"], judge.messages[1].content)
        with patch('analystdesk.evaluation.scoring.run_c0', return_value={"text": ANSWER}) as run_c0, \
             patch("analystdesk.agent.team.make_judge_llm", return_value=judge), \
             patch("analystdesk.agent.runtime.passage_text", return_value="filing text"):
            result = asyncio.run(run_one("c0", CASE, "offline"))
        self.assertTrue(result["success"])
        self.assertEqual(result["scorer_version"], "risk-semantic-v1")
        self.assertEqual(run_c0.call_args.args[0], {"id": CASE["id"], "request": CASE["request"]})

    def test_citations_alone_are_not_a_pass(self):
        self.assertFalse(score(CASE, {"text": ANSWER})["success"])

    def test_incorrect_answer_fails_even_with_both_citations(self):
        judge = Judge('{"supported": false, "reason": "wrong interpretation"}')
        review = asyncio.run(review_risk_change(CASE, {"text": ANSWER}, judge, lambda _: "filing text"))
        self.assertFalse(score(CASE, {"text": ANSWER, "risk_review": review})["success"])

    def test_missing_labels_or_passages_fail_closed(self):
        case = {**CASE, "expect": {"risk_change": {"ticker": "MSFT", "years": [2023, 2024]}}}
        judge = Judge("not called")
        for selected, lookup in ((case, lambda _: "text"), (CASE, lambda _: None)):
            review = asyncio.run(review_risk_change(selected, {"text": ANSWER}, judge, lookup))
            self.assertEqual(review["status"], "incomplete")
            self.assertFalse(score(selected, {"text": ANSWER, "risk_review": review})["success"])
        self.assertIsNone(judge.messages)

    def test_malformed_and_unavailable_judge_fail_closed(self):
        for response in ('{"supported": "yes", "reason": "ok"}', "bad json", RuntimeError("offline")):
            review = asyncio.run(review_risk_change(CASE, {"text": ANSWER}, Judge(response), lambda _: "text"))
            self.assertEqual(review["status"], "incomplete")
            self.assertFalse(score(CASE, {"text": ANSWER, "risk_review": review})["success"])

    def test_run_errors_do_not_record_secret_bearing_provider_messages(self):
        class ProviderError(Exception):
            status_code = 402

        with patch('analystdesk.evaluation.scoring.run_c0', side_effect=ProviderError("secret-in-provider-url")):
            result = asyncio.run(run_one("c0", CASE, "offline"))
        self.assertEqual(result["error"], "ProviderError: HTTP 402")
        self.assertNotIn("secret-in-provider-url", result["reason"])


if __name__ == "__main__":
    unittest.main()
