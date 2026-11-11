"""Unified CLI routing uses mocks; no evaluation datasets or providers are used."""

import contextlib
import io
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from scripts import run, report


class EvaluationCommandTests(unittest.TestCase):
    def test_async_evaluation_arguments_are_forwarded_and_argv_restored(self):
        for command, module_name in [("eval", "run_eval"), ("redteam", "run_redteam")]:
            observed = []
            async def evaluate():
                observed.append(sys.argv[1:])
            with self.subTest(command=command), patch.object(
                run, "import_module", return_value=SimpleNamespace(main=evaluate)
            ) as load:
                previous = sys.argv
                self.assertEqual(run.main([command, "--experiment", "example", "--split", "dev"]), 0)
                self.assertEqual(observed, [["--experiment", "example", "--split", "dev"]])
                self.assertIs(sys.argv, previous)
                load.assert_called_once_with("analystdesk.evaluation.workflows." + module_name)

    def test_retrieval_and_financebench_dispatch(self):
        for command, name in [("retrieval", "eval_retrieval"), ("financebench", "eval_financebench")]:
            operation = Mock(return_value=None)
            with self.subTest(command=command), patch.object(
                run, "import_module", return_value=SimpleNamespace(main=operation)
            ) as load:
                self.assertEqual(run.main([command]), 0)
                operation.assert_called_once_with()
                load.assert_called_once_with("analystdesk.evaluation.workflows." + name)

    def test_memory_calibration_and_reflection_dispatch(self):
        from pathlib import Path
        cases = [
            (["memory"], "main", ("default request",)),
            (["memory", "custom request"], "main", ("custom request",)),
            (["memory", "--rescore", "saved.json"], "rescore", (Path("saved.json"),)),
            (["calibrate", "sample", "--n", "12"], "sample", (12,)),
            (["calibrate", "score"], "score", ()),
            (["reflect", "dev.json"], "main", (Path("dev.json"),)),
        ]
        for argv, method, expected in cases:
            operation = AsyncMock(return_value=None)
            module = SimpleNamespace(REQUEST="default request", **{method: operation})
            with self.subTest(argv=argv), patch.object(run, "import_module", return_value=module):
                self.assertEqual(run.main(argv), 0)
                operation.assert_awaited_once_with(*expected)

    def test_reports_forward_options_and_exit_status(self):
        for command, name in [("audit", "audit_eval_results"), ("repeats", "eval_three_runs")]:
            operation = Mock(return_value=1)
            with self.subTest(command=command), patch.object(
                report, "import_module", return_value=SimpleNamespace(main=operation)
            ) as load:
                self.assertEqual(report.main([command, "--input", "saved.json"]), 1)
                operation.assert_called_once_with(["--input", "saved.json"])
                load.assert_called_once_with("analystdesk.evaluation.workflows." + name)

    def test_local_help_does_not_import_workflows(self):
        for argv in [["--help"], ["financebench", "--help"], ["memory", "--help"],
                     ["reflect", "--help"], ["calibrate", "--help"]]:
            with self.subTest(argv=argv), patch.object(run, "import_module") as load, \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    run.main(argv)
                self.assertEqual(error.exception.code, 0)
                load.assert_not_called()

    def test_invalid_command_does_not_import_or_execute_workflows(self):
        for argv in [["unknown"], ["reflect"], ["memory", "request", "--rescore", "saved.json"]]:
            with self.subTest(argv=argv), patch.object(run, "import_module") as load, \
                 contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    run.main(argv)
                self.assertEqual(error.exception.code, 2)
                load.assert_not_called()
