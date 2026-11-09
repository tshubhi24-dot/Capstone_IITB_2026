"""Role 6 offline evaluation accounting and integrity regressions."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk.evaluation import evaluation_gate_failures, load_cases

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from audit_eval_results import validate_result, markdown_report  # noqa: E402
from eval_three_runs import evaluate  # noqa: E402


class EvaluationAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.gold = self.root / "dev_cases.jsonl"
        self.gold.write_text("\n".join(json.dumps({"id": f"a{i}", "split": "dev", "type": "numeric"})
                                      for i in (1, 2)) + "\n", encoding="utf-8")
        self.rows = [
            {"id": "a1", "type": "numeric", "config": "c1", "success": True,
             "policy_violation": False, "seconds": 2, "tokens": 10, "error": None,
             "verified": "1/2", "verified_share": 50.0},
            {"id": "a2", "type": "numeric", "config": "c1", "success": True,
             "policy_violation": False, "seconds": 3, "tokens": 20, "error": None,
             "verified": "0/0", "verified_share": 100.0},
        ]
        self.file = self.root / "eval.json"
        self.write()

    def write(self):
        self.file.write_text(json.dumps({"split": "dev", "rows": {"c1": self.rows}}), encoding="utf-8")

    def validate(self):
        return validate_result(self.file, self.gold, ["c1"], min_cases=2)

    def test_pooled_share_excludes_zero_division_rows(self):
        report = self.validate()
        c1 = report["configurations"]["c1"]
        self.assertEqual(c1["verified_share_pooled_pct"], 50.0)
        self.assertEqual(c1["verified_share_case_mean_pct"], 75.0)
        self.assertEqual(c1["verified_share_mean_with_numbers_only_pct"], 50.0)
        self.assertEqual(c1["zero_number_cases"], 1)
        self.assertIn("not a new LLM", markdown_report(report))

    def test_missing_case_fails(self):
        self.rows.pop()
        self.write()
        with self.assertRaisesRegex(ValueError, "missing 1 gold cases"):
            self.validate()

    def test_duplicate_row_fails(self):
        self.rows.append(copy.deepcopy(self.rows[0]))
        self.write()
        with self.assertRaisesRegex(ValueError, "duplicate result IDs"):
            self.validate()

    def test_incorrect_percent_fails(self):
        self.rows[0]["verified_share"] = 95
        self.write()
        with self.assertRaisesRegex(ValueError, "percentage disagrees"):
            self.validate()

    def test_error_cannot_be_marked_success(self):
        self.rows[0]["error"] = "timeout"
        self.write()
        with self.assertRaisesRegex(ValueError, "cannot succeed with an error"):
            self.validate()

    def test_wrong_gold_type_fails(self):
        self.rows[0]["type"] = "refusal"
        self.write()
        with self.assertRaisesRegex(ValueError, "config or type differs"):
            self.validate()

    def test_saved_summary_mismatch_fails(self):
        self.file.write_text(json.dumps({"split": "dev", "rows": {"c1": self.rows},
                                         "summary": {"c1": {"cases": 2, "success": 1}}}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "saved summary field success"):
            self.validate()

    def test_three_run_aggregator_requires_real_distinct_heldout_data(self):
        with self.assertRaisesRegex(ValueError, "at least three"):
            evaluate([self.file], self.gold, ["c1"], min_cases=2)
        with self.assertRaisesRegex(ValueError, "supplied more than once"):
            evaluate([self.file, self.file, self.file], self.gold, ["c1"], min_cases=2)

    def test_heldout_aggregator_happy_path(self):
        self.gold.write_text("\n".join(json.dumps({"id": f"a{i}", "split": "heldout", "type": "numeric"})
                                      for i in (1, 2)) + "\n", encoding="utf-8")
        sources = []
        for n in range(3):
            path = self.root / f"heldout_{n}.json"
            path.write_text(json.dumps({"tag": f"live-run-{n}", "split": "heldout",
                                        "rows": {"c1": self.rows}}), encoding="utf-8")
            sources.append(path)
        report = evaluate(sources, self.gold, ["c1"], min_cases=2)
        self.assertEqual(report["run_count"], 3)
        self.assertEqual(report["configurations"]["c1"]["verified_share_pooled_pct"]["median"], 50.0)

    def test_development_fixture_works(self):
        result = validate_result(ROOT / "data/evaluation/results/eval_dev_merged.json",
                                 ROOT / "data/evaluation/dev_cases.jsonl", ["c0", "c1", "c2"], 20)
        self.assertEqual(result["configurations"]["c1"]["verified_numbers"], 77)
        self.assertEqual(result["configurations"]["c2"]["total_numbers"], 200)


class EvaluationRunnerSafetyTests(unittest.TestCase):
    def test_missing_heldout_is_explicit_error(self):
        # Use a temporary empty evaluation directory: the team's Role 5
        # held-out cases may legitimately be added later.
        with tempfile.TemporaryDirectory() as tmp, patch("analystdesk.evaluation.EVAL_DIR", Path(tmp)):
            with self.assertRaisesRegex(ValueError, "No heldout evaluation cases"):
                load_cases("heldout")

    def test_ci_fails_if_any_agent_run_errors(self):
        errors = evaluation_gate_failures({"cases": 20, "success": 19, "errors": 1,
                                           "policy_violations": 0}, 0.95, 20)
        self.assertTrue(any("1 run error" in error for error in errors))

    def test_ci_allows_verified_success_with_zero_errors(self):
        self.assertEqual(evaluation_gate_failures({"cases": 20, "success": 19, "errors": 0,
                                                   "policy_violations": 0}, 0.95, 20), [])


if __name__ == "__main__":
    unittest.main()
