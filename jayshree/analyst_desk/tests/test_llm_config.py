import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from analystdesk.llm_config import (
    CONFIG_PATH,
    LLM_CONFIG,
    LLMConfigError,
    load_llm_config,
    max_output_tokens,
)


class LLMConfigTests(unittest.TestCase):
    def test_optional_output_limit_and_invalid_values(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(max_output_tokens())
        with patch.dict("os.environ", {"AGENT_MAX_OUTPUT_TOKENS": "1024"}):
            self.assertEqual(max_output_tokens(), 1024)
        for value in ("0", "-1", "invalid", ""):
            with self.subTest(value=value), patch.dict("os.environ", {"AGENT_MAX_OUTPUT_TOKENS": value}):
                with self.assertRaises(LLMConfigError):
                    max_output_tokens()

    def test_output_limit_is_applied_to_agent_and_judge(self):
        from analystdesk.agent.runtime import make_llm
        from analystdesk.agent.team import make_judge_llm

        with patch.dict("os.environ", {"AGENT_MAX_OUTPUT_TOKENS": "1024", "OPENROUTER_API_KEY": "test-key"}), \
                patch("langchain_openai.ChatOpenAI") as constructor:
            make_llm()
            make_judge_llm()
        self.assertEqual(constructor.call_count, 2)
        self.assertTrue(all(call.kwargs["max_tokens"] == 1024 for call in constructor.call_args_list))

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

    def test_reply_length_is_capped(self):
        # every call must cap its reply, or OpenRouter reserves 65,536 tokens per call
        self.assertEqual(LLM_CONFIG.max_output_tokens, 4096)
        from analystdesk.agent.runtime import make_llm
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test"}):
            self.assertEqual(make_llm().max_tokens, 4096)
        content = CONFIG_PATH.read_text(encoding="utf-8").replace(
            "max_output_tokens = 4096", "max_output_tokens = 0", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "llm.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(LLMConfigError, "max_output_tokens"):
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
