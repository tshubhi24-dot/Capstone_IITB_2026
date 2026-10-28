import unittest

from analystdesk.evaluation import evaluation_gate_failures


class EvaluationGateTests(unittest.TestCase):
    def test_baseline_success_rate_passes(self):
        failures = evaluation_gate_failures(
            {"cases": 20, "success": 19, "policy_violations": 0},
            min_success_rate=0.95,
        )

        self.assertEqual(failures, [])

    def test_below_threshold_fails(self):
        failures = evaluation_gate_failures(
            {"cases": 20, "success": 18, "policy_violations": 0},
            min_success_rate=0.95,
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("18/20 (90.0%)", failures[0])

    def test_incomplete_development_set_fails(self):
        failures = evaluation_gate_failures(
            {"cases": 19, "success": 19, "policy_violations": 0},
            min_success_rate=0.95,
            min_cases=20,
        )

        self.assertEqual(failures, ["evaluation ran 19 cases; expected at least 20"])

    def test_policy_violation_fails_even_when_success_threshold_passes(self):
        failures = evaluation_gate_failures(
            {"cases": 20, "success": 20, "policy_violations": 1},
            min_success_rate=0.95,
        )

        self.assertEqual(failures, ["evaluation found 1 policy violation(s)"])

    def test_empty_evaluation_fails(self):
        failures = evaluation_gate_failures(
            {"cases": 0, "success": 0, "policy_violations": 0},
            min_success_rate=0.95,
        )

        self.assertEqual(failures, ["evaluation produced no cases"])

    def test_threshold_outside_fraction_range_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            evaluation_gate_failures(
                {"cases": 20, "success": 20, "policy_violations": 0},
                min_success_rate=95,
            )

    def test_minimum_case_count_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "at least 1"):
            evaluation_gate_failures(
                {"cases": 20, "success": 20, "policy_violations": 0},
                min_success_rate=0.95,
                min_cases=0,
            )


if __name__ == "__main__":
    unittest.main()
