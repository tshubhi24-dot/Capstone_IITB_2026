"""Experiments as config files, one harness (evaluation protocol: "a config file
rather than a separate code branch"). Each file in experiments/ names:

    name, question   what is compared, and why
    runner           "eval" (scripts/run_eval.py) or "redteam" (scripts/run_redteam.py)
    configs          c0 / c1 / c2
    split            dev or heldout (the command line can override it)
    [env]            switches, read by the code at run time:
        AGENT_CRITIC=0      critic loop off: no revisions, no judge (E4)
        AGENT_PASSAGES=plain   plain-text chunks instead of table-aware ones (E4)
        AGENT_DEFENCES=0    guardrails off (E2)
        AGENT_LESSONS=0     no playbook lessons (E3 "before")

Everything else (model, prompts, tools, budget) comes from config/llm.toml and
stays the same across an experiment's arms.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = ROOT / "experiments"
SWITCHES = {"AGENT_CRITIC", "AGENT_PASSAGES", "AGENT_DEFENCES", "AGENT_LESSONS"}


def load(name_or_path: str) -> dict:
    """An experiment by file path or by name (e4_critic_off)."""
    path = Path(name_or_path)
    if not path.exists():
        path = EXPERIMENTS_DIR / f"{name_or_path.removesuffix('.toml')}.toml"
    exp = tomllib.loads(path.read_text(encoding="utf-8"))
    missing = {"name", "question", "runner", "configs"} - set(exp)
    if missing:
        raise ValueError(f"{path.name}: missing {sorted(missing)}")
    if exp["runner"] not in ("eval", "redteam"):
        raise ValueError(f"{path.name}: runner must be eval or redteam")
    if set(exp["configs"]) - {"c0", "c1", "c2"}:
        raise ValueError(f"{path.name}: configs must be c0, c1 or c2")
    env = {k: str(v) for k, v in exp.get("env", {}).items()}
    if set(env) - SWITCHES:
        raise ValueError(f"{path.name}: unknown switch {sorted(set(env) - SWITCHES)}; allowed {sorted(SWITCHES)}")
    return {**exp, "env": env, "file": path.name, "split": exp.get("split", "dev")}


def apply(exp: dict) -> None:
    """Set the experiment's switches for this process (before any run starts)."""
    for k in SWITCHES:
        os.environ.pop(k, None)
    os.environ.update(exp["env"])


def all_experiments() -> list[dict]:
    return [load(str(p)) for p in sorted(EXPERIMENTS_DIR.glob("*.toml"))]
