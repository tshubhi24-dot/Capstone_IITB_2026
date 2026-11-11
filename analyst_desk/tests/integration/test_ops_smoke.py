"""Tests for the Role 6 operations smoke checker and MCP routing."""

import asyncio
import contextlib
import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

from analystdesk.web import api as api
from scripts import ops as ops_smoke


class DeploymentSmokeTests(unittest.TestCase):
    def test_smoke_passes_only_when_every_service_is_healthy(self):
        def fake_json(url):
            if url.endswith("/healthz"):
                return {"status": "ok"}
            if url.endswith("/readyz"):
                return {"status": "ready"}
            if url.endswith("/api/alerts"):
                return {"status": "available", "alerts": []}
            if "/api/v1/query?" in url:
                return {"status": "success", "data": {"result": [{"value": [123, "1"]}]}}
            if url.endswith("/api/v1/rules?type=alert"):
                return {"status": "success", "data": {"groups": [{"rules": [
                    {"name": "VerifiedShareBelow98"}]}]}}
            if url.endswith("/api/health"):
                return {"database": "ok"}
            raise AssertionError(f"unexpected URL: {url}")

        with patch.object(ops_smoke, "_get_json", side_effect=fake_json):
            results = ops_smoke.check_deployment("http://app", "http://prom", "http://grafana")
        self.assertEqual(len(results), 6)
        self.assertTrue(all(ok for _, ok, _ in results), results)

    def test_smoke_fails_when_metrics_are_not_scraped(self):
        def fake_json(url):
            if "/api/v1/query?" in url:
                return {"status": "success", "data": {"result": []}}
            return {"status": "available", "alerts": [], "database": "ok"}

        with patch.object(ops_smoke, "_get_json", side_effect=fake_json):
            results = ops_smoke.check_deployment("http://app", "http://prom", "http://grafana")
        self.assertIn("Prometheus scrape", [name for name, ok, _ in results if not ok])

    def test_smoke_fails_when_accuracy_alert_is_missing(self):
        with patch.object(ops_smoke, "_get_json", return_value={"status": "success", "data": {"groups": []}}):
            results = ops_smoke.check_deployment("http://app", "http://prom", "http://grafana")
        self.assertIn("98% accuracy alert loaded", [name for name, ok, _ in results if not ok])

    def test_ui_blocks_approval_until_note_is_verified(self):
        import analystdesk.ui.research as agent_ui

        with (
            patch.object(agent_ui, "_past_notes", return_value=[]),
            patch.object(agent_ui, "_board", return_value="board"),
            patch.object(agent_ui, "_note_display", return_value="note"),
            patch.object(agent_ui, "_check_display", return_value="check"),
        ):
            for verified in (False, True):
                gate = {"gate": "note", "note": {"title": "Test", "body": "text"},
                        "check": {"ok": verified}}
                updates = agent_ui._view("run-1", {"values": {}, "interrupts": [gate]}, [])
                self.assertEqual(updates[-3]["interactive"], verified)
                self.assertFalse(updates[-2]["visible"])
                self.assertFalse(updates[-1])
                self.assertEqual("Approval is blocked" in updates[1], not verified)

    def test_api_agent_runner_uses_deployed_mcp_configuration(self):
        callback = AsyncMock()
        with patch("analystdesk.agent.runtime.run_until_gate", new_callable=AsyncMock) as runner:
            asyncio.run(api._run_until_gate("run-1", {"request": "compare"}, callback))
            runner.assert_awaited_once_with("run-1", {"request": "compare"}, callback,
                                            transport="auto")


class OperationsCommandTests(unittest.TestCase):
    def test_smoke_forwards_urls_and_preserves_failure_exit_code(self):
        with patch.object(ops_smoke, "check_deployment", return_value=[("health", False, "unavailable")]) as check, \
             contextlib.redirect_stdout(io.StringIO()):
            code = ops_smoke.main(["smoke", "--app-url", "http://app/", "--prometheus-url", "http://prom/",
                                   "--grafana-url", "http://grafana/"])
        self.assertEqual(code, 1)
        check.assert_called_once_with("http://app", "http://prom", "http://grafana")

    def test_backfill_preserves_deleted_and_inactive_exclusions(self):
        connection = Mock()
        connection.execute.return_value.fetchall.return_value = [
            (1, "kept", "body", '["MSFT"]', "reviewer", "2026-01-01"),
            (2, "deleted", "body", '["MSFT"]', "reviewer", "2026-01-01"),
            (3, "withdrawn", "body", '["MSFT"]', "reviewer", "2026-01-01"),
        ]
        remember = AsyncMock(return_value={"MSFT": {}})
        with tempfile.TemporaryDirectory() as tmp:
            portal = Path(tmp) / "portal.db"
            portal.touch()
            with patch("analystdesk.servers.portal._db_path", return_value=portal), \
                 patch("analystdesk.servers.portal.inactive_note_ids", return_value={3}), \
                 patch("analystdesk.memory.store.suppressed_notes", new=AsyncMock(return_value={2})), \
                 patch("analystdesk.memory.store.remember_published_note", new=remember), \
                 patch.object(ops_smoke.sqlite3, "connect", return_value=connection) as connect, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ops_smoke.main(["backfill-memory", "--analyst", "team"]), 0)
        remember.assert_awaited_once_with(1, "kept", "body", ["MSFT"], "reviewer", "team", "2026-01-01")
        self.assertTrue(connect.call_args.kwargs["uri"])
        self.assertIn("mode=ro", connect.call_args.args[0])
        connection.close.assert_called_once()

    def test_help_and_invalid_options_never_execute_operations(self):
        for argv, expected in [(["--help"], 0), (["smoke", "--help"], 0),
                               (["backfill-memory", "--help"], 0), ([], 2),
                               (["unknown"], 2), (["smoke", "--analyst", "team"], 2)]:
            with self.subTest(argv=argv), patch.object(ops_smoke, "smoke") as smoke, \
                 patch.object(ops_smoke, "backfill_memory") as backfill, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    ops_smoke.main(argv)
                self.assertEqual(error.exception.code, expected)
                smoke.assert_not_called()
                backfill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
