import tempfile
import unittest
from pathlib import Path

from analystdesk.llm_config import (
    CONFIG_PATH,
    LLM_CONFIG,
    LLMConfigError,
    load_llm_config,
)


class LLMConfigTests(unittest.TestCase):
    def test_committed_config_contains_all_roles_and_prompts(self):
        self.assertEqual(LLM_CONFIG.version, 1)
        self.assertEqual(
            set(LLM_CONFIG.models),
            {"c0", "agent", "judge", "reflection"},
        )
        self.assertEqual(
            set(LLM_CONFIG.prompts),
            {
                "c0_system",
                "c0_answer",
                "planner",
                "researcher",
                "writer",
                "specialist_researcher",
                "specialist_quant",
                "specialist_risk_diff",
                "judge",
                "reflection",
            },
        )

    def test_config_templates_render_required_fields(self):
        cases = {
            "c0_answer": {
                "passages": "passage",
                "numbers": "numbers",
                "question": "question",
            },
            "planner": {"tickers": "MSFT", "years": [2022], "feedback": ""},
            "researcher": {"budget": 4, "plan": "{}"},
            "writer": {"figures": "figures", "memory": "", "issues": ""},
            "specialist_researcher": {
                "company": "MSFT",
                "years": [2024],
                "budget": 4,
                "plan": "{}",
            },
            "specialist_quant": {
                "companies": "MSFT",
                "years": [2024],
                "budget": 4,
                "plan": "{}",
            },
            "specialist_risk_diff": {
                "company": "MSFT",
                "years": [2023, 2024],
                "latest": 2024,
                "prior": 2023,
                "budget": 4,
                "plan": "{}",
            },
        }
        for name, values in cases.items():
            with self.subTest(prompt=name):
                rendered = LLM_CONFIG.format_prompt(name, **values)
                self.assertTrue(rendered.strip())
                self.assertIn(str(next(iter(values.values()))), rendered)

    def test_formatting_missing_value_fails_clearly(self):
        with self.assertRaisesRegex(LLMConfigError, "Could not format prompt"):
            LLM_CONFIG.format_prompt("planner", tickers="MSFT")

    def test_missing_config_fails_clearly(self):
        with self.assertRaisesRegex(LLMConfigError, "Could not read LLM config"):
            load_llm_config(CONFIG_PATH.with_name("missing-llm.toml"))

    def test_invalid_prompt_placeholder_fails_validation(self):
        content = CONFIG_PATH.read_text(encoding="utf-8").replace(
            "{tickers}", "{unknown_tickers}", 1
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "llm.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(LLMConfigError, "placeholders must be"):
                load_llm_config(path)

    def test_unknown_config_version_fails_validation(self):
        content = CONFIG_PATH.read_text(encoding="utf-8").replace(
            "version = 1", "version = 2", 1
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "llm.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(LLMConfigError, "version must be 1"):
                load_llm_config(path)

    def test_env_example_contains_only_api_key_setting(self):
        env_example = CONFIG_PATH.parent.parent / ".env.example"
        assignments = [
            line.split("=", 1)[0].strip()
            for line in env_example.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#") and "=" in line
        ]
        self.assertEqual(assignments, ["OPENROUTER_API_KEY"])


if __name__ == "__main__":
    unittest.main()
