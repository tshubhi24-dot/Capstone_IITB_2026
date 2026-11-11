import asyncio
import json
import unittest

from fastapi.testclient import TestClient

from analystdesk.monitoring.alerts import PrometheusUnavailable
from analystdesk.web.api import ResearchRequest
from analystdesk.web.api import create_app


class ApiTests(unittest.TestCase):
    def test_stale_review_reports_restart_guidance_in_stream(self):
        from analystdesk.governance.review_snapshot import ReviewStaleError
        async def runner(run_id, payload, on_event):
            raise ReviewStaleError("Evidence changed; start a fresh run.")
        with TestClient(create_app(runner=runner)) as client:
            response = client.post("/api/research", json={"request": "Microsoft FY2024"})
        events = self._events(response)
        error = next(data for name, data in events if name == "error")
        self.assertEqual(error["error"], "review_stale")
        self.assertIn("start a fresh run", error["detail"])

    def test_lifecycle_api_reports_success_and_conflict(self):
        from unittest.mock import patch
        from analystdesk.servers.portal import LifecycleError
        payload = {"action": "withdraw", "reason": "incorrect", "actor": "analyst"}
        with patch("analystdesk.servers.portal.change_lifecycle",
                   return_value={"note_id": 7, "action": "withdraw"}) as change:
            response = self.client.post("/api/notes/7/lifecycle", json=payload)
        self.assertEqual(response.status_code, 200)
        change.assert_called_once_with(7, "withdraw", "incorrect", "analyst", None, None)
        with patch("analystdesk.servers.portal.change_lifecycle", side_effect=LifecycleError("already inactive")):
            response = self.client.post("/api/notes/7/lifecycle", json=payload)
        self.assertEqual(response.status_code, 409)
    def setUp(self):
        self.saved_runs = {}
        self.runner_calls = []

        async def runner(run_id, payload, on_event):
            self.runner_calls.append((run_id, payload))
            gate = self.saved_runs.get(run_id, {}).get("interrupts", [{}])[0].get("gate")
            if "resume" not in payload:
                plan = {"companies": ["MSFT"]}
                result = {
                    "values": {"plan": plan},
                    "interrupts": [{"gate": "plan", "plan": plan,
                                    "requires_year_confirmation": True}],
                }
                await on_event({"node": "plan", "plan": plan})
            elif gate == "plan":
                draft = {
                    "title": "Microsoft research",
                    "body": "Evidence-backed draft",
                    "tickers": ["MSFT"],
                }
                result = {
                    "values": {"draft": draft},
                    "interrupts": [{"gate": "note", "note": draft, "check": {"ok": True, "verified_share": 100}}],
                }
                await on_event({"node": "write", "draft": draft})
            elif gate == "note" and payload["resume"]["action"] == "reject":
                result = {"values": {"outcome": "rejected"}, "interrupts": []}
                await on_event({"node": "reject", "reason": payload["resume"]["reason"]})
            else:
                result = {"values": {"outcome": "published"}, "interrupts": []}
                await on_event({"node": "publish", "ok": True})
            self.saved_runs[run_id] = result
            return result

        async def load_run(run_id):
            return self.saved_runs.get(run_id, {"values": {}, "interrupts": []})

        self.client = TestClient(create_app(runner=runner, run_loader=load_run))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    @staticmethod
    def _events(response):
        """Parse SSE data events; ignore standards-compliant keep-alive comments."""
        events = []
        for block in response.text.strip().split("\n\n"):
            lines = block.splitlines()
            names = [line[7:] for line in lines if line.startswith("event: ")]
            payloads = [line[6:] for line in lines if line.startswith("data: ")]
            if not names and not payloads:  # a comment, e.g. ': keep-alive'
                continue
            if len(names) != 1 or len(payloads) != 1:
                raise AssertionError(f"invalid SSE event: {block!r}")
            events.append((names[0], json.loads(payloads[0])))
        return events

    def test_health_and_readiness(self):
        self.assertEqual(self.client.get("/healthz").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/readyz").json(), {"status": "ready"})

    def test_alerts_endpoint_returns_active_prometheus_alerts(self):
        alerts = [
            {
                "state": "firing",
                "name": "VerifiedShareBelow98",
                "severity": "warning",
                "summary": "Verified share below threshold",
                "active_at": "2026-11-05T10:00:00Z",
            }
        ]
        with TestClient(create_app(alert_reader=lambda: alerts)) as client:
            response = client.get("/api/alerts")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "available", "alerts": alerts})

    def test_alerts_endpoint_reports_monitoring_unavailable(self):
        def unavailable():
            raise PrometheusUnavailable("connection refused")

        with TestClient(create_app(alert_reader=unavailable)) as client:
            response = client.get("/api/alerts")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            {
                "status": "unavailable",
                "message": "Prometheus alerts are currently unavailable.",
            },
        )

    def test_readiness_waits_for_dependencies(self):
        state = {"reason": "retriever_loading"}
        app = create_app(readiness_check=lambda: state["reason"])

        with TestClient(app) as client:
            self.assertEqual(client.get("/healthz").status_code, 200)
            response = client.get("/readyz")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["detail"]["reason"], "retriever_loading")

            state["reason"] = None
            self.assertEqual(client.get("/readyz").json(), {"status": "ready"})

    def test_readiness_check_exception_returns_server_error(self):
        def failing_readiness_check():
            raise RuntimeError("readiness dependency failed")

        with TestClient(create_app(readiness_check=failing_readiness_check),
                        raise_server_exceptions=False) as client:
            response = client.get("/readyz")

        self.assertEqual(response.status_code, 500)

    def test_research_streams_plan_draft_and_publication_gates(self):
        response = self.client.post(
            "/api/research",
            json={"request": "Compare Microsoft margins", "mode": "c1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "text/event-stream; charset=utf-8")
        events = self._events(response)
        self.assertEqual([name for name, _ in events], ["started", "progress", "result"])
        self.assertEqual(events[-1][1]["status"], "waiting_for_plan_approval")
        self.assertEqual(events[-1][1]["plan"], {"companies": ["MSFT"]})
        self.assertTrue(events[-1][1]["requires_year_confirmation"])
        run_id = events[0][1]["run_id"]

        response = self.client.post(
            f"/api/research/{run_id}/decision",
            json={"action": "approve", "confirm_years": True},
        )
        self.assertTrue(self.runner_calls[-1][1]["resume"]["confirm_years"])
        events = self._events(response)
        self.assertEqual(events[-1][1]["status"], "waiting_for_note_approval")
        self.assertEqual(events[-1][1]["draft"]["body"], "Evidence-backed draft")

        response = self.client.post(
            f"/api/research/{run_id}/decision",
            json={"action": "approve", "approver": "analyst"},
        )
        self.assertEqual(self._events(response)[-1][1]["status"], "published")

    def test_ambiguous_plan_requires_year_confirmation_through_api(self):
        response = self.client.post(
            "/api/research",
            json={"request": "Compare Microsoft margins", "mode": "c1"},
        )
        run_id = self._events(response)[0][1]["run_id"]
        response = self.client.post(
            f"/api/research/{run_id}/decision",
            json={"action": "approve"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("confirm the proposed fiscal years", response.json()["detail"])
        self.assertEqual(len(self.runner_calls), 1)

        response = self.client.post(
            f"/api/research/{run_id}/decision",
            json={"action": "approve", "confirm_years": True},
        )
        self.assertEqual(response.status_code, 200)

    def test_unverified_note_cannot_be_approved(self):
        self.saved_runs["bad-note"] = {
            "values": {"draft": {"body": "Unsupported 15%"}},
            "interrupts": [{"gate": "note", "check": {"ok": False, "issues": ["unsourced 15%"]}}],
        }
        response = self.client.post(
            "/api/research/bad-note/decision",
            json={"action": "approve", "approver": "reviewer"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("unresolved checks", response.json()["detail"])
        self.assertEqual(len(self.runner_calls), 0)

    def test_existing_gradio_ui_is_mounted_at_root(self):
        import gradio as gr

        with gr.Blocks(title="Analyst Desk test") as ui:
            gr.Markdown("Research UI")

        with TestClient(create_app(ui)) as client:
            response = client.get("/")
            health = client.get("/healthz")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Analyst Desk test", response.text)
        self.assertEqual(health.json(), {"status": "ok"})

    def test_api_can_run_without_gradio_ui(self):
        with TestClient(create_app()) as client:
            health = client.get("/healthz")
            docs = client.get("/docs")
            root = client.get("/")

        self.assertEqual(health.status_code, 200)
        self.assertEqual(docs.status_code, 200)
        self.assertEqual(root.status_code, 404)

    def test_blank_request_is_rejected(self):
        response = self.client.post("/api/research", json={"request": "   "})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "request must not be blank")

    def test_blank_analyst_is_rejected(self):
        response = self.client.post(
            "/api/research",
            json={"request": "Compare Microsoft margins", "analyst": "   "},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "analyst must not be blank")

    def test_invalid_mode_is_rejected(self):
        response = self.client.post(
            "/api/research",
            json={"request": "Compare margins", "mode": "unsupported"},
        )

        self.assertEqual(response.status_code, 422)

    def test_decision_for_unknown_run_returns_not_found(self):
        response = self.client.post(
            "/api/research/missing-run/decision",
            json={"action": "approve"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "research run not found")

    def test_run_loader_exception_returns_server_error(self):
        async def failing_loader(run_id):
            raise RuntimeError("checkpoint database unavailable")

        with TestClient(create_app(run_loader=failing_loader),
                        raise_server_exceptions=False) as client:
            response = client.post(
                "/api/research/failed-load/decision",
                json={"action": "approve"},
            )

        self.assertEqual(response.status_code, 500)

    def test_decision_for_run_not_waiting_for_approval_conflicts(self):
        self.saved_runs["completed-run"] = {
            "values": {"outcome": "published"},
            "interrupts": [],
        }

        response = self.client.post(
            "/api/research/completed-run/decision",
            json={"action": "approve"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "research run is not waiting for approval")

    def test_unknown_approval_gate_conflicts(self):
        self.saved_runs["unknown-gate-run"] = {
            "values": {"plan": {}},
            "interrupts": [{"gate": "other"}],
        }

        response = self.client.post(
            "/api/research/unknown-gate-run/decision",
            json={"action": "approve"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "research run has an unknown approval gate")

    def test_plan_rejection_is_not_supported(self):
        self.saved_runs["plan-run"] = {
            "values": {"plan": {}},
            "interrupts": [{"gate": "plan"}],
        }

        response = self.client.post(
            "/api/research/plan-run/decision",
            json={"action": "reject"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "the plan gate supports approve or edit")

    def test_plan_edit_requires_edited_plan(self):
        self.saved_runs["plan-run"] = {
            "values": {"plan": {}},
            "interrupts": [{"gate": "plan"}],
        }

        response = self.client.post(
            "/api/research/plan-run/decision",
            json={"action": "edit"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "an edited plan is required")

    def test_note_edit_requires_a_string_body(self):
        self.saved_runs["note-run"] = {
            "values": {"draft": {}},
            "interrupts": [{"gate": "note"}],
        }

        response = self.client.post(
            "/api/research/note-run/decision",
            json={"action": "edit", "note": {"title": "Missing body"}},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "an edited note body is required")

    def test_note_approval_requires_nonblank_approver(self):
        self.saved_runs["note-run"] = {
            "values": {"draft": {}},
            "interrupts": [{"gate": "note"}],
        }

        response = self.client.post(
            "/api/research/note-run/decision",
            json={"action": "approve", "approver": "   "},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "approver must not be blank")

    def test_note_rejection_is_forwarded_to_runner(self):
        self.saved_runs["note-run"] = {
            "values": {"draft": {}},
            "interrupts": [{"gate": "note"}],
        }

        response = self.client.post(
            "/api/research/note-run/decision",
            json={"action": "reject", "reason": "Needs stronger citations"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.runner_calls[-1],
            (
                "note-run",
                {"resume": {"action": "reject", "reason": "Needs stronger citations"}},
            ),
        )
        self.assertEqual(self._events(response)[-1][1]["status"], "rejected")

    def test_runner_failure_is_reported_as_stream_error(self):
        async def failing_runner(run_id, payload, on_event):
            raise RuntimeError("upstream model unavailable")

        with TestClient(create_app(runner=failing_runner)) as client:
            with self.assertLogs('analystdesk.web.api', level="ERROR"):
                response = client.post(
                    "/api/research",
                    json={"request": "Compare margins"},
                )

        events = self._events(response)
        self.assertEqual(events[-1][0], "error")
        self.assertEqual(events[-1][1]["error"], "research_run_failed")

    def test_client_disconnect_cancels_runner_task(self):
        async def exercise_disconnect():
            runner_started = asyncio.Event()
            runner_cancelled = asyncio.Event()

            async def waiting_runner(run_id, payload, on_event):
                runner_started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    runner_cancelled.set()

            app = create_app(runner=waiting_runner)
            endpoint = next(
                route.endpoint for route in app.routes
                if getattr(route, "path", None) == "/api/research"
            )
            response = await endpoint(ResearchRequest(request="Compare Microsoft margins"))

            first_chunk = await response.body_iterator.__anext__()
            self.assertIn("event: started", first_chunk)
            await asyncio.wait_for(runner_started.wait(), timeout=1)
            await response.body_iterator.aclose()
            await asyncio.wait_for(runner_cancelled.wait(), timeout=1)

        asyncio.run(exercise_disconnect())


if __name__ == "__main__":
    unittest.main()
