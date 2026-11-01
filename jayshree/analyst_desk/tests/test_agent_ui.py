import asyncio
import unittest
from unittest.mock import patch

import gradio as gr

from agent_ui import _drive, build_agent_panel


class AgentPanelTests(unittest.TestCase):
    def test_agent_panel_embeds_and_receives_selected_workflow(self):
        with gr.Blocks() as demo:
            workflow = gr.Radio(
                [("C0", "c0"), ("C1", "c1"), ("C2", "c2")],
                value="c0",
                label="Workflow",
            )
            with gr.Group(visible=False):
                build_agent_panel(workflow)

        config = demo.get_config_file()
        self.assertFalse(any(c["type"] in ("tab", "tabitem") for c in config["components"]))
        start_events = [
            event for event in config["dependencies"]
            if workflow._id in event.get("inputs", [])
        ]
        self.assertTrue(any(event["api_name"] == "on_start" for event in start_events))

    def test_cancel_plan_button_is_connected_to_plan_resume_handler(self):
        with gr.Blocks() as demo:
            workflow = gr.Radio(
                [("C0", "c0"), ("C1", "c1"), ("C2", "c2")],
                value="c0",
                label="Workflow",
            )
            with gr.Group(visible=False):
                build_agent_panel(workflow)

        config = demo.get_config_file()
        cancel_button = next(
            component for component in config["components"]
            if component["type"] == "button"
            and component["props"].get("value") == "🚫 Cancel plan"
        )
        cancel_event = next(
            event for event in config["dependencies"]
            if event.get("api_name") == "on_cancel_plan"
        )

        self.assertEqual(cancel_event["targets"], [(cancel_button["id"], "click")])
        self.assertTrue(cancel_event["types"]["generator"])
        self.assertTrue(cancel_event["inputs"])

    def test_stopping_drive_cancels_agent_task(self):
        async def exercise_cancellation():
            started = asyncio.Event()
            cancelled = asyncio.Event()

            async def waiting_run(run_id, payload, on_event, transport):
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

            with patch("analystdesk.agent.runtime.run_until_gate", new=waiting_run):
                stream = _drive("test-run", {})
                next_event = asyncio.create_task(stream.__anext__())
                await asyncio.wait_for(started.wait(), timeout=1)
                next_event.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await next_event
                await asyncio.wait_for(cancelled.wait(), timeout=1)

        asyncio.run(exercise_cancellation())


if __name__ == "__main__":
    unittest.main()
