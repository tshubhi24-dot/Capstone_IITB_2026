"""Load and validate the versioned prompt and model configuration."""

from __future__ import annotations

import string
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "llm.toml"
CONFIG_VERSION = 1

_REQUIRED_MODELS = frozenset({"c0", "agent", "judge", "reflection"})
_REQUIRED_PROMPTS = frozenset({
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
})
_PROMPT_FIELDS = {
    "c0_answer": frozenset({"passages", "numbers", "question"}),
    "planner": frozenset({"tickers", "years", "feedback"}),
    "researcher": frozenset({"budget", "plan"}),
    "writer": frozenset({"figures", "memory", "issues"}),
    "specialist_researcher": frozenset({"company", "years", "budget", "plan"}),
    "specialist_quant": frozenset({"companies", "years", "budget", "plan"}),
    "specialist_risk_diff": frozenset({"company", "years", "latest", "prior", "budget", "plan"}),
}


class LLMConfigError(ValueError):
    """Raised when the committed LLM configuration is missing or invalid."""


def max_output_tokens() -> int | None:
    """Optional per-call output limit; input tokens and total spend are separate."""
    raw = os.getenv("AGENT_MAX_OUTPUT_TOKENS")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise LLMConfigError("AGENT_MAX_OUTPUT_TOKENS must be a positive integer") from exc
    if value <= 0:
        raise LLMConfigError("AGENT_MAX_OUTPUT_TOKENS must be a positive integer")
    return value


@dataclass(frozen=True)
class LLMConfig:
    version: int
    models: Mapping[str, str]
    prompts: Mapping[str, str]

    def model(self, name: str) -> str:
        return self.models[name]

    def prompt(self, name: str) -> str:
        return self.prompts[name]

    def format_prompt(self, name: str, **values: object) -> str:
        try:
            return self.prompt(name).format(**values)
        except (IndexError, KeyError, ValueError) as exc:
            raise LLMConfigError(f"Could not format prompt {name!r}: {exc}") from exc


def _template_fields(name: str, prompt: str) -> frozenset[str]:
    try:
        return frozenset(
            field_name
            for _, field_name, _, _ in string.Formatter().parse(prompt)
            if field_name is not None
        )
    except ValueError as exc:
        raise LLMConfigError(f"Prompt {name!r} has invalid template syntax: {exc}") from exc


def load_llm_config(path: Path = CONFIG_PATH) -> LLMConfig:
    """Read config from TOML and fail clearly for invalid or incomplete settings."""
    try:
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
    except OSError as exc:
        raise LLMConfigError(f"Could not read LLM config at {path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise LLMConfigError(f"LLM config at {path} is not valid TOML: {exc}") from exc

    version = data.get("version")
    if type(version) is not int or version != CONFIG_VERSION:
        raise LLMConfigError(
            f"LLM config version must be {CONFIG_VERSION}; got {version!r}"
        )

    models = data.get("models")
    if not isinstance(models, dict):
        raise LLMConfigError("LLM config must contain a [models] table")
    missing_models = _REQUIRED_MODELS - models.keys()
    if missing_models:
        raise LLMConfigError(f"LLM config is missing model IDs: {', '.join(sorted(missing_models))}")
    for name in _REQUIRED_MODELS:
        value = models[name]
        if not isinstance(value, str) or not value.strip():
            raise LLMConfigError(f"Model ID {name!r} must be a non-empty string")

    prompts = data.get("prompts")
    if not isinstance(prompts, dict):
        raise LLMConfigError("LLM config must contain a [prompts] table")
    missing_prompts = _REQUIRED_PROMPTS - prompts.keys()
    if missing_prompts:
        raise LLMConfigError(f"LLM config is missing prompts: {', '.join(sorted(missing_prompts))}")
    for name in _REQUIRED_PROMPTS:
        if not isinstance(prompts[name], str) or not prompts[name].strip():
            raise LLMConfigError(f"Prompt {name!r} must be a non-empty string")

    for name, required_fields in _PROMPT_FIELDS.items():
        actual_fields = _template_fields(name, prompts[name])
        if actual_fields != required_fields:
            raise LLMConfigError(
                f"Prompt {name!r} placeholders must be {sorted(required_fields)}; "
                f"got {sorted(actual_fields)}"
            )

    return LLMConfig(
        version=version,
        models=MappingProxyType({name: models[name] for name in _REQUIRED_MODELS}),
        prompts=MappingProxyType({name: prompts[name] for name in _REQUIRED_PROMPTS}),
    )


LLM_CONFIG = load_llm_config()
