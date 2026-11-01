import asyncio
import unittest
from unittest.mock import patch

import gradio as gr

from agent_ui import (
    _can_start_agent_run,
    _can_add_preference,
    _can_use_run_actions,
    _drive,
    _has_run_id,
    _parse_edited_plan,
    _playbook_button_states,
    build_agent_panel,
)


class AgentPanelTests(unittest.TestCase):
    def test_start_enabled_only_for_nonblank_c1_or_c2_when_idle(self):
        self.assertFalse(_can_start_agent_run("", "c1"))
        self.assertFalse(_can_start_agent_run("   ", "c2"))
        self.assertFalse(_can_start_agent_run("Compare margins", "c0"))
        self.assertFalse(_can_start_agent_run("Compare margins", "c1", running=True))
        self.assertFalse(_can_start_agent_run("Compare margins", "c2", running=True))
        self.assertTrue(_can_start_agent_run("Compare margins", "c1"))
        self.assertTrue(_can_start_agent_run("Compare margins", "c2"))

    def test_load_and_rerun_enabled_only_when_run_id_is_nonblank(self):
        self.assertFalse(_has_run_id(None))
        self.assertFalse(_has_run_id(""))
        self.assertFalse(_has_run_id("   "))
        self.assertTrue(_has_run_id("run-123"))
        self.assertFalse(_can_use_run_actions("run-123", running=True))
        self.assertFalse(_can_use_run_actions("   ", running=False))
        self.assertTrue(_can_use_run_actions("run-123", running=False))

    def test_add_preference_requires_nonblank_text(self):
        self.assertFalse(_can_add_preference(None))
        self.assertFalse(_can_add_preference(""))
        self.assertFalse(_can_add_preference(" \t\n "))
        self.assertTrue(_can_add_preference("Always include a comparison"))

    def test_playbook_controls_require_a_selected_row(self):
        self.assertEqual(_playbook_button_states(None, None, False), (False, False, False, False))
        self.assertEqual(
            _playbook_button_states("lesson-1", "pending", False),
            (True, True, True, False),
        )
        self.assertEqual(
            _playbook_button_states("lesson-1", "approved", False),
            (False, False, True, False),
        )
        self.assertEqual(
            _playbook_button_states("lesson-1", "pending", True),
            (False, False, False, True),
        )

    def test_edited_plan_requires_valid_substantive_change(self):
        baseline = (
            '{"companies":["MSFT"],"fiscal_years":[2024],'
            '"sub_questions":["What changed?"],"outline":["Summary"]}'
        )
        self.assertEqual(
            _parse_edited_plan(baseline, baseline)[0],
            None,
        )
        self.assertEqual(
            _parse_edited_plan(
                '{\n  "companies": ["MSFT"], "fiscal_years": [2024], '
                '"sub_questions": ["What changed?"], "outline": ["Summary"]\n}',
                baseline,
            )[0],
            None,
        )
        self.assertIsNone(_parse_edited_plan("{", baseline)[0])
        self.assertIsNone(_parse_edited_plan('{"companies": ["MSFT"]}', baseline)[0])
        edited_plan, _ = _parse_edited_plan(
            '{"companies":["MSFT","GOOGL"],"fiscal_years":[2024],'
            '"sub_questions":["What changed?"],"outline":["Summary"]}',
            baseline,
        )
        self.assertEqual(edited_plan["companies"], ["MSFT", "GOOGL"])

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
        run_id = next(
            component for component in config["components"]
            if component["type"] == "textbox" and component["props"].get("label") == "Run id (paste one to resume)"
        )
        load_button = next(
            component for component in config["components"]
            if component["type"] == "button" and component["props"].get("value") == "⟳ Load run"
        )
        rerun_button = next(
            component for component in config["components"]
            if component["type"] == "button"
            and component["props"].get("value") == "↻ Re-run this request without memory"
        )
        edit_plan_button = next(
            component for component in config["components"]
            if component["type"] == "button"
            and component["props"].get("value") == "Approve the edited plan"
        )
        plan_editor = next(
            component for component in config["components"]
            if component["type"] == "code" and component["props"].get("label") == "Plan"
        )
        preference_input = next(
            component for component in config["components"]
            if component["type"] == "textbox"
            and component["props"].get("label") == "Add a standing preference"
        )
        add_preference_button = next(
            component for component in config["components"]
            if component["type"] == "button" and component["props"].get("value") == "Add"
        )
        delete_memory_button = next(
            component for component in config["components"]
            if component["type"] == "button"
            and component["props"].get("value") == "🗑 Delete selected memory"
        )
        playbook_buttons = [
            next(
                component for component in config["components"]
                if component["type"] == "button" and component["props"].get("value") == label
            )
            for label in (
                "✅ Approve lesson", "🛑 Reject lesson", "🧊 Freeze playbook", "Unfreeze",
            )
        ]
        self.assertFalse(load_button["props"]["interactive"])
        self.assertFalse(rerun_button["props"]["interactive"])
        self.assertFalse(edit_plan_button["props"]["interactive"])
        self.assertFalse(add_preference_button["props"]["interactive"])
        self.assertFalse(delete_memory_button["props"]["interactive"])
        self.assertTrue(all(not button["props"]["interactive"] for button in playbook_buttons))
        preference_change_events = [
            event for event in config["dependencies"]
            if (preference_input["id"], "input") in event.get("targets", [])
            or (preference_input["id"], "change") in event.get("targets", [])
        ]
        self.assertTrue(preference_change_events)
        self.assertTrue(all(add_preference_button["id"] in event.get("outputs", [])
                            for event in preference_change_events))
        add_preference_event = next(
            event for event in config["dependencies"]
            if event.get("api_name") == "on_add_pref"
        )
        self.assertIn(add_preference_button["id"], add_preference_event["outputs"])
        memory_selection_events = [
            event for event in config["dependencies"]
            if event.get("api_name") in {"on_pick_pref", "on_pick_note_mem"}
        ]
        self.assertEqual(len(memory_selection_events), 2)
        self.assertTrue(all(delete_memory_button["id"] in event.get("outputs", [])
                            for event in memory_selection_events))
        delete_event = next(
            event for event in config["dependencies"]
            if event.get("api_name") == "on_delete_mem"
        )
        self.assertIn(delete_memory_button["id"], delete_event.get("outputs", []))
        self.assertTrue(any(
            event.get("targets") == [(delete_memory_button["id"], "click")]
            and "window.confirm" in event.get("js", "")
            for event in config["dependencies"]
        ))
        lesson_tables = [
            component for component in config["components"]
            if component["type"] == "dataframe"
            and component["props"].get("label") in {
                "Pending your review", "Approved (used by agents)",
                "Rejected (kept as evidence)",
            }
        ]
        self.assertEqual(len(lesson_tables), 3)
        lesson_selection_events = [
            event for event in config["dependencies"]
            if any((table["id"], "select") in event.get("targets", []) for table in lesson_tables)
        ]
        self.assertEqual(len(lesson_selection_events), 3)
        self.assertTrue(all(
            all(button["id"] in event.get("outputs", []) for button in playbook_buttons)
            for event in lesson_selection_events
        ))
        id_change_events = [
            event for event in config["dependencies"]
            if (run_id["id"], "input") in event.get("targets", [])
            or (run_id["id"], "change") in event.get("targets", [])
        ]
        self.assertTrue(id_change_events)
        self.assertTrue(all(
            load_button["id"] in event.get("outputs", [])
            and rerun_button["id"] in event.get("outputs", [])
            for event in id_change_events
        ))

        start_events = [
            event for event in config["dependencies"]
            if workflow._id in event.get("inputs", [])
        ]
        self.assertTrue(any(event["api_name"] == "on_start" for event in start_events))

        start_event = next(event for event in start_events if event["api_name"] == "on_start")
        start_button_id = start_event["targets"][0][0]
        start_button = next(
            component for component in config["components"]
            if component["id"] == start_button_id
        )
        self.assertFalse(start_button["props"]["interactive"])
        request = next(
            component for component in config["components"]
            if component["type"] == "textbox" and component["props"].get("label") == "Research request"
        )
        busy_state_id = start_event["inputs"][3]
        control_events = [
            event for event in config["dependencies"]
            if start_button_id in event.get("outputs", [])
            and busy_state_id in event.get("inputs", [])
        ]
        self.assertTrue(any((request["id"], "input") in event.get("targets", []) for event in control_events))
        self.assertTrue(any((workflow._id, "change") in event.get("targets", []) for event in control_events))
        streamed_actions = {
            "on_start",
            "on_rerun_without_memory",
            "on_approve_plan",
            "on_cancel_plan",
            "on_edit_plan",
            "on_approve_note",
            "on_edit_note",
            "on_reject",
        }
        run_events = [
            event for event in config["dependencies"]
            if event.get("api_name") in streamed_actions
        ]
        self.assertEqual({event["api_name"] for event in run_events}, streamed_actions)
        self.assertTrue(all(
            start_button_id in event.get("outputs", [])
            and busy_state_id in event.get("outputs", [])
            and load_button["id"] in event.get("outputs", [])
            and rerun_button["id"] in event.get("outputs", [])
            for event in run_events
        ))

        load_event = next(
            event for event in config["dependencies"]
            if event.get("api_name") == "on_load"
        )
        self.assertIn(busy_state_id, load_event["inputs"])
        self.assertIn(load_button["id"], load_event.get("outputs", []))
        self.assertIn(rerun_button["id"], load_event.get("outputs", []))
        rerun_event = next(
            event for event in config["dependencies"]
            if event.get("api_name") == "on_rerun_without_memory"
        )
        self.assertIn(busy_state_id, rerun_event["inputs"])
        self.assertIn(load_button["id"], rerun_event.get("outputs", []))
        self.assertIn(rerun_button["id"], rerun_event.get("outputs", []))
        edit_events = [
            event for event in config["dependencies"]
            if (plan_editor["id"], "input") in event.get("targets", [])
            or (plan_editor["id"], "change") in event.get("targets", [])
        ]
        self.assertTrue(edit_events)
        self.assertTrue(all(edit_plan_button["id"] in event.get("outputs", [])
                            for event in edit_events))
        edit_submit_event = next(
            event for event in config["dependencies"]
            if event.get("api_name") == "on_edit_plan"
        )
        self.assertIn(edit_plan_button["id"], edit_submit_event["outputs"])
        self.assertEqual(len(edit_submit_event["inputs"]), 6)

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
