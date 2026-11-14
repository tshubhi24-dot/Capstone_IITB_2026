"""Role 5 offline evaluation accounting and integrity regressions."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk.evaluation import evaluation_gate_failures, evaluator_path, load_cases

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

    def test_external_heldout_and_results_must_be_outside_repository(self):
        heldout = self.root / "private"
        heldout.mkdir()
        (heldout / "cases.jsonl").write_text(json.dumps(
            {"id": "external01", "split": "heldout", "type": "refusal",
             "request": "test", "expect": {"refusal": "test"}}) + "\n", encoding="utf-8")
        self.assertEqual(load_cases("heldout", heldout_dir=heldout)[0]["id"], "external01")
        self.assertEqual(evaluator_path(self.root), self.root.resolve())
        with self.assertRaisesRegex(ValueError, "outside"):
            load_cases("heldout", heldout_dir=ROOT / "data" / "evaluation" / "heldout")
        with self.assertRaisesRegex(ValueError, "outside"):
            evaluator_path(ROOT / "data" / "evaluation" / "results")
        with self.assertRaisesRegex(ValueError, "only valid"):
            load_cases("dev", heldout_dir=heldout)

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

    def test_error_with_unavailable_tokens_is_auditable(self):
        self.rows[0]["success"] = False
        self.rows[0]["error"] = "APIStatusError: Error code: 402"
        self.rows[0]["tokens"] = None
        self.write()
        report = self.validate()["configurations"]["c1"]
        self.assertEqual(report["tokens_mean"], 10)
        self.assertEqual(report["tokens_recorded_cases"], 1)
        self.assertEqual(report["tokens_unreported_cases"], 1)

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
            rows = copy.deepcopy(self.rows)
            for row in rows:
                row["tokens"] *= 1000
                row["blocks"] = n == 0 and row["id"] == "a1"
            path.write_text(json.dumps({"tag": f"live-run-{n}", "split": "heldout",
                                        "price_per_m": 0.52,
                                        "playbook": {"frozen": True, "version": "test-version", "lessons": 3},
                                        "rows": {"c1": rows}}), encoding="utf-8")
            sources.append(path)
        report = evaluate(sources, self.gold, ["c1"], min_cases=2)
        self.assertEqual(report["run_count"], 3)
        self.assertEqual(report["configurations"]["c1"]["verified_share_pooled_pct"]["median"], 50.0)
        self.assertEqual(report["configurations"]["c1"]["by_type"]["numeric"]["success_runs"], [2, 2, 2])
        self.assertEqual(report["configurations"]["c1"]["false_blocks"]["runs"], [1, 0, 0])
        self.assertEqual(report["configurations"]["c1"]["estimated_cost_per_case_usd"]["runs"],
                         [0.0078, 0.0078, 0.0078])
        self.assertEqual(report["playbook"]["version"], "test-version")

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
