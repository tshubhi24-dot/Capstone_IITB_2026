"""Fingerprint the evidence and checking policy used at a note review."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from analystdesk.governance import approval as approval
from analystdesk.finance import edgar as edgar
from analystdesk.retrieval import ingest as ingest
from analystdesk.finance import source_review as source_review
from analystdesk.config.llm_config import CONFIG_PATH
from analystdesk.config.llm_config import LLM_CONFIG
from analystdesk.research.scope import COMPANIES
from analystdesk.servers.edgar_server import get_fact
from analystdesk.governance.checks import FACT_ID
from analystdesk.governance.checks import PASSAGE_ID

_FACT_IDS = re.compile(FACT_ID)
_ROOT = Path(__file__).resolve().parent.parent
_POLICY_FILES = (
    "governance/checks.py", "finance/figures.py", "agent/guards.py", "agent/team.py",
    "agent/graph.py", "governance/review_snapshot.py", "finance/edgar.py", "research/scope.py",
    "agent/runtime.py", "governance/approval.py", "config/llm_config.py", "finance/source_review.py", "servers/edgar_server.py",
    "servers/portal.py", "servers/signing.py", "paths.py",
)
_COMPANIES = {company.ticker: company for company in COMPANIES}


class SnapshotError(ValueError):
    """Evidence or policy could not be captured for a review."""


class ReviewStaleError(ValueError):
    """A saved run must be restarted because its review is no longer current."""


def _digest(value: object) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def capture(draft: dict, passage_text) -> dict:
    """Capture the exact cited evidence available to this process and its review policy."""
    try:
        source_review.load_register()
    except source_review.SourceReviewError as exc:
        raise SnapshotError(f"Source-review register unavailable: {exc}") from exc
    content = draft["title"] + "\n" + draft["body"]
    passages = {}
    for pid in sorted(set(PASSAGE_ID.findall(content))):
        text = passage_text(pid) if passage_text is not None else None
        if not isinstance(text, str) or not text:
            raise SnapshotError(f"Cited passage {pid} is unavailable for evidence snapshot.")
        passages[pid] = hashlib.sha256(text.encode("utf-8")).hexdigest()

    facts = {}
    source_paths: dict[str, Path] = {}
    passages_dir = ingest.PLAIN_PASSAGES_DIR if os.getenv("AGENT_PASSAGES", "tables") == "plain" else ingest.PASSAGES_DIR
    for pid in passages:
        ticker, year, *_ = pid.split("_")
        source_paths[f"passages/{ticker}_{year}.jsonl"] = passages_dir / f"{ticker}_{year}.jsonl"
    for fid in sorted(set(_FACT_IDS.findall(content))):
        result = get_fact(fid)
        if not result.ok or result.fact is None or not result.ticker:
            raise SnapshotError(f"Cited fact {fid} is unavailable for evidence snapshot.")
        facts[fid] = {"ticker": result.ticker, "fact": result.fact.model_dump(mode="json")}
        company = _COMPANIES.get(result.ticker)
        if company is None:
            raise SnapshotError(f"Cited fact {fid} has an unsupported company.")
        source_paths[f"edgar/{company.cik}.json"] = edgar.CACHE_DIR / f"{company.cik}.json"

    try:
        review_path = source_review.register_path()
        if review_path is not None:
            source_paths["source_review"] = review_path
        source_files = {name: hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
                        for name, path in source_paths.items()}
        policy_files = {name: hashlib.sha256((_ROOT / name).read_bytes()).hexdigest()
                        for name in _POLICY_FILES}
        policy_files["config/llm.toml"] = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
    except OSError as exc:
        raise SnapshotError(f"Review evidence or policy file cannot be read: {type(exc).__name__}.") from exc
    policy = {
        "files": policy_files,
        "effective_models": dict(LLM_CONFIG.models),
        "effective_judge_prompt": LLM_CONFIG.prompt("judge"),
        "defences": os.getenv("AGENT_DEFENCES", "1"),
        "critic": os.getenv("AGENT_CRITIC", "1"),
        "passages": os.getenv("AGENT_PASSAGES", "tables"),
        "source_review_configured": bool(review_path),
    }
    return {"version": 1, "note_sha256": approval.note_hash(draft["title"], draft["body"], draft["tickers"]),
            "passages": passages, "facts": facts, "source_files": source_files,
            "policy_sha256": _digest(policy)}
