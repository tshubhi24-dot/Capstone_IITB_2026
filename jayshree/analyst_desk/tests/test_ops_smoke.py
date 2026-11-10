"""Tests for the Role 6 operations smoke checker and MCP routing."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from analystdesk import api
from scripts import ops_smoke


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
        import agent_ui

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


if __name__ == "__main__":
    unittest.main()
