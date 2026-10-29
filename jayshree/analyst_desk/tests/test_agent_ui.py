import unittest

import gradio as gr

from agent_ui import build_agent_panel


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


if __name__ == "__main__":
    unittest.main()
