"""Experiments are config files; their switches change what the code does."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analystdesk import experiments


class ExperimentFileTests(unittest.TestCase):
    def test_every_experiment_file_loads(self):
        names = {Path(e["file"]).stem for e in experiments.all_experiments()}
        self.assertTrue({"e1_c0_c1_c2", "e2_defences_on", "e2_defences_off", "e3_before_playbook",
                         "e3_after_playbook", "e4_critic_off", "e4_plain_passages"} <= names)

    def test_by_name_and_switches(self):
        e = experiments.load("e4_critic_off")
        self.assertEqual((e["runner"], e["env"]), ("eval", {"AGENT_CRITIC": "0"}))

    def test_unknown_switch_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.toml"
            p.write_text('name="x"\nquestion="y"\nrunner="eval"\nconfigs=["c1"]\n[env]\nAGENT_TOKEN_BUDGET="5"\n')
            with self.assertRaises(ValueError):
                experiments.load(str(p))

    def test_apply_clears_the_previous_experiment(self):
        with patch.dict(os.environ, {"AGENT_CRITIC": "0"}):
            experiments.apply(experiments.load("e2_defences_off"))
            self.assertNotIn("AGENT_CRITIC", os.environ)
            self.assertEqual(os.environ["AGENT_DEFENCES"], "0")
        os.environ.pop("AGENT_DEFENCES", None)


class CriticSwitchTests(unittest.TestCase):
    def _after_check(self):
        from analystdesk.agent.graph import common_nodes
        return common_nodes(None, None)["after_check"]

    def test_failed_check_goes_back_to_the_writer(self):
        self.assertEqual(self._after_check()({"check": {"ok": False}, "revisions": 0}), "write")

    def test_critic_off_goes_straight_to_the_analyst(self):
        with patch.dict(os.environ, {"AGENT_CRITIC": "0"}):
            self.assertEqual(self._after_check()({"check": {"ok": False}, "revisions": 0}), "review_note")


class PassageSwitchTests(unittest.TestCase):
    def test_plain_switch_loads_the_plain_chunks(self):
        from analystdesk.ingest import load_passages
        with patch.dict(os.environ, {"AGENT_PASSAGES": "plain"}):
            plain = load_passages()
        tables = load_passages()
        self.assertNotEqual(len(plain), len(tables))
        self.assertTrue(any(p.get("kind") == "table" for p in tables))
        self.assertFalse(any(p.get("kind") == "table" for p in plain))


if __name__ == "__main__":
    unittest.main()
