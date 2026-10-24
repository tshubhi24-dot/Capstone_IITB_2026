"""Readiness must report the deployed index and block unavailable retrieval."""
import json
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from desk import api
from desk.retrieval import canonical_hash, load_config, model_fingerprint
from ops.verify_runtime import matches_prepared_retrieval


def install_service(monkeypatch, value):
    async def status(role, server, tool, arguments):
        assert (role, server, tool, arguments) == ("planner", "filings-kb", "retrieval_status", {})
        if isinstance(value, Exception):
            raise value
        return value
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid_rerank")
    monkeypatch.setattr(api.app.state, "source", SimpleNamespace(fingerprint="f" * 64), raising=False)
    monkeypatch.setattr(api.app.state, "engine", SimpleNamespace(_wire_call=status), raising=False)


@pytest.mark.parametrize("change", ["unavailable", "wrong_source", "wrong_mode", "not_ready", "not_semantic"])
def test_configuration_fails_closed_for_unavailable_or_mismatched_reader(monkeypatch, change):
    value = {"mode": "hybrid_rerank", "ready": True, "semantic_retrieval": True,
             "source_fingerprint": "f" * 64, "backend": "chroma_cosine"}
    if change == "unavailable":
        value = RuntimeError("private diagnostic must remain private")
    elif change == "wrong_source":
        value["source_fingerprint"] = "0" * 64
    elif change == "wrong_mode":
        value["mode"] = "bm25"
    elif change == "not_ready":
        value["ready"] = False
    else:
        value["semantic_retrieval"] = False
    install_service(monkeypatch, value)
    assert api.retrieval_configuration() == {"mode": "hybrid_rerank", "ready": False,
                                           "semantic_retrieval": False, "backend": "unavailable"}


def test_configuration_reports_actual_read_only_service_status(monkeypatch):
    value = {"mode": "hybrid_rerank", "ready": True, "semantic_retrieval": True,
             "source_fingerprint": "f" * 64, "backend": "chroma_cosine"}
    install_service(monkeypatch, value)
    assert api.retrieval_configuration() == value


def test_new_research_is_blocked_before_budget_or_run_creation_when_index_unavailable(monkeypatch):
    install_service(monkeypatch, RuntimeError("service unavailable"))
    monkeypatch.setattr(api, "validate_scope", lambda *_: None)
    def forbidden():
        raise AssertionError("A failed retrieval preflight must precede live budget/run work")
    monkeypatch.setattr(api, "gateway_budget", forbidden)
    background = BackgroundTasks()
    with pytest.raises(HTTPException) as caught:
        api.create(api.ResearchRequest(question="Compare operational risks", mode="live"), background)
    assert caught.value.status_code == 409 and background.tasks == []


def prepared_metadata(tmp_path):
    policy = load_config()
    manifest = {"corpus_fingerprint": "f" * 64, "configuration_hash": canonical_hash(policy),
                "model_fingerprint": model_fingerprint(policy)}
    fingerprint = canonical_hash(manifest)
    manifest["index_fingerprint"] = fingerprint
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    details = {"mode": "hybrid_rerank", "ready": True, "backend": "chroma_cosine",
               "semantic_retrieval": True, "source_fingerprint": "f" * 64,
               "index_fingerprint": fingerprint, "configuration_hash": canonical_hash(policy),
               "model_fingerprint": model_fingerprint(policy),
               **{role: {key: policy[role][key] for key in ("id", "revision")} for role in ("encoder", "reranker")}}
    config = {"retrieval": "hybrid_rerank", "semantic_retrieval": True,
              "source_fingerprint": "f" * 64, "retrieval_details": details}
    return path, config


def test_verifier_matches_actual_prepared_identity(tmp_path):
    path, config = prepared_metadata(tmp_path)
    assert matches_prepared_retrieval(config, artifact_path=path)


@pytest.mark.parametrize("field,value", [("backend", "numpy_exact_cosine"), ("ready", False),
    ("index_fingerprint", "0" * 64), ("model_fingerprint", "0" * 64),
    ("configuration_hash", "0" * 64), ("source_fingerprint", "0" * 64), ("encoder", {})])
def test_verifier_rejects_stale_or_unverified_claims(tmp_path, field, value):
    path, config = prepared_metadata(tmp_path)
    config["retrieval_details"][field] = value
    assert not matches_prepared_retrieval(config, artifact_path=path)
