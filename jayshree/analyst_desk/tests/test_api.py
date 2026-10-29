import json
import unittest

from fastapi.testclient import TestClient

from analystdesk.api import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.saved_runs = {}

        async def runner(run_id, payload, on_event):
            gate = self.saved_runs.get(run_id, {}).get("interrupts", [{}])[0].get("gate")
            if "resume" not in payload:
                plan = {"companies": ["MSFT"]}
                result = {
                    "values": {"plan": plan},
                    "interrupts": [{"gate": "plan", "plan": plan}],
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
                    "interrupts": [{"gate": "note", "note": draft, "check": {"verified_share": 100}}],
                }
                await on_event({"node": "write", "draft": draft})
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
        events = []
        for block in response.text.strip().split("\n\n"):
            event_name, event_data = block.splitlines()
            events.append((
                event_name.removeprefix("event: "),
                json.loads(event_data.removeprefix("data: ")),
            ))
        return events

    def test_health_and_readiness(self):
        self.assertEqual(self.client.get("/healthz").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/readyz").json(), {"status": "ready"})

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
        run_id = events[0][1]["run_id"]

        response = self.client.post(
            f"/api/research/{run_id}/decision",
            json={"action": "approve"},
        )
        events = self._events(response)
        self.assertEqual(events[-1][1]["status"], "waiting_for_note_approval")
        self.assertEqual(events[-1][1]["draft"]["body"], "Evidence-backed draft")

        response = self.client.post(
            f"/api/research/{run_id}/decision",
            json={"action": "approve", "approver": "analyst"},
        )
        self.assertEqual(self._events(response)[-1][1]["status"], "published")

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

    def test_blank_request_is_rejected(self):
        response = self.client.post("/api/research", json={"request": "   "})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "request must not be blank")

    def test_invalid_mode_is_rejected(self):
        response = self.client.post(
            "/api/research",
            json={"request": "Compare margins", "mode": "unsupported"},
        )

        self.assertEqual(response.status_code, 422)

    def test_runner_failure_is_reported_as_stream_error(self):
        async def failing_runner(run_id, payload, on_event):
            raise RuntimeError("upstream model unavailable")

        with TestClient(create_app(runner=failing_runner)) as client:
            with self.assertLogs("analystdesk.api", level="ERROR"):
                response = client.post(
                    "/api/research",
                    json={"request": "Compare margins"},
                )

        events = self._events(response)
        self.assertEqual(events[-1][0], "error")
        self.assertEqual(events[-1][1]["error"], "research_run_failed")


if __name__ == "__main__":
    unittest.main()
