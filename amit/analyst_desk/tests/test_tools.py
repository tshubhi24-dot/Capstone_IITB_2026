"""Tools, authority and queue-protocol checks; Docker isolation is verified live."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

from desk.data import Corpus
from desk import tools
from desk.worker import calculate_row


@pytest.fixture
def source(tmp_path):
    common = {"ticker": "MSFT", "fiscal_year": 2025, "start": "2024-07-01", "end": "2025-06-30",
              "unit": "USD", "accession": "test-2025", "source_kind": "sec_edgar"}
    facts = [{**common, "id": "test-revenue", "concept": "revenue", "value": 300},
             {**common, "id": "test-income", "concept": "operating_income", "value": 100}]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"companies": [{"ticker": "MSFT"}], "facts": facts,
                               "passages": [{"id": "test-passage", "ticker": "MSFT", "year": 2025, "item": "1A", "text": "Test source risk evidence."}]}))
    return Corpus(path)


def test_worker_produces_source_linked_correctly_rounded_margin(source):
    row = calculate_row(list(source.canonical_pair("test-revenue", "test-income")))
    assert row["margin_pct"] == "33.33"
    assert row["fact_ids"] == ["test-revenue", "test-income"]
    assert source.verify_row(row)
    row["margin_pct"] = "33.34"
    assert not source.verify_row(row)


@pytest.mark.parametrize("field,value", [("unit", "EUR"), ("fiscal_year", 2024), ("concept", "net_income")])
def test_worker_rechecks_inputs_inside_the_boundary(source, field, value):
    facts = list(source.canonical_pair("test-revenue", "test-income"))
    facts[1][field] = value
    with pytest.raises(ValueError):
        calculate_row(facts)


def test_authenticated_researcher_has_no_publication_authority(monkeypatch):
    monkeypatch.setattr(tools, "get_access_token", lambda: SimpleNamespace(scopes=["role:researcher"]))
    called = []
    result = tools.envelope("publish_note", lambda: called.append("write"))
    assert result["ok"] is False and result["error"]["code"] == "PermissionError"
    assert called == []
    monkeypatch.setattr(tools, "get_access_token", lambda: None)
    assert tools.envelope("get_facts", lambda: called.append("read"))["ok"] is False
    assert called == []


def test_http_mcp_rejects_requests_without_a_bearer_token(source):
    server = tools.create_server("edgar", corpus=source, config={"roles": {"researcher": "r" * 40}})
    with TestClient(server.http_app()) as client:
        response = client.get("/mcp")
    assert response.status_code == 401


def test_real_queue_protocol_does_not_fall_back_to_host_calculation(source, tmp_path, monkeypatch):
    # This checks a real separate-process queue handoff, not OS/Docker isolation.
    queue = tmp_path / "queue"
    queue.mkdir()
    monkeypatch.setenv("CALCULATION_QUEUE", str(queue))
    root = Path(__file__).resolve().parents[1]
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(root), "CALCULATION_QUEUE": str(queue),
           "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    worker = subprocess.Popen([sys.executable, "-m", "desk.worker"], cwd=root, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        row = tools.queue_calculation(source, "test-revenue", "test-income", timeout=15)
        assert row["executor"] == "isolated_pandas_queue" and source.verify_row(row)
    finally:
        worker.terminate()
        worker.wait(timeout=5)
    assert not list(queue.glob("*.request.json"))
    with pytest.raises(TimeoutError):
        tools.queue_calculation(source, "test-revenue", "test-income", timeout=.1)
