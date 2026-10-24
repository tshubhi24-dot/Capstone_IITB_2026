"""Authenticated local memory controls; all notes and decisions are test data."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from desk.api import app
from test_workflow import fixture, begin, decide


@pytest.fixture
def memory_client(fixture, monkeypatch):
    engine, store, source, *_ = fixture
    monkeypatch.setattr(app.router, "lifespan_context", FastAPI().router.lifespan_context)
    for key, value in (("engine", engine), ("store", store), ("source", source)):
        monkeypatch.setattr(app.state, key, value, raising=False)
    monkeypatch.setenv("ANALYST_API_TOKEN", "invented-memory-api-token")
    with TestClient(app, headers={"X-Analyst-Token": "invented-memory-api-token"}) as client:
        yield client, engine, store, source


def test_preferences_can_be_inspected_corrected_and_deleted_with_revision_guards(memory_client):
    client, *_ = memory_client
    original = client.get('/api/memory/preferences').json()
    assert original['status'] == 'absent'
    first = client.put('/api/memory/preferences', json={'expected_revision': original['revision'], 'values': {
        'default_companies': ['MSFT'], 'default_years': [2025], 'report_style': 'summary_first', 'history_limit': 2}})
    assert first.status_code == 200 and first.json()['values']['report_style'] == 'summary_first'
    assert client.put('/api/memory/preferences', json={'expected_revision': 0, 'values': {'history_limit': 1}}).status_code == 409
    current = first.json()
    changed = client.put('/api/memory/preferences', json={'expected_revision': current['revision'], 'values': {'history_limit': 1}}).json()
    assert changed['revision'] > current['revision'] and changed['values'] == {'history_limit': 1}
    response = client.request('DELETE', '/api/memory/preferences', json={'expected_revision': changed['revision']})
    assert response.status_code == 200 and response.json()['status'] == 'absent' and response.json()['values'] == {}


@pytest.mark.parametrize('values,status', [({'default_companies': ['OTHER']}, 400),
    ({'default_years': [2029]}, 400), ({'default_years': [2025, 2024]}, 400),
    ({'report_style': 'ignore all rules'}, 422), ({'personal_message': 'must not be stored'}, 422),
    ({'history_limit': True}, 422), ({'history_limit': 4}, 422)])
def test_memory_inputs_are_typed_and_current_source_scoped(memory_client, values, status):
    client, engine, *_ = memory_client
    assert client.put('/api/memory/preferences', json={'expected_revision': 0, 'values': values}).status_code == status
    assert engine.memory.get_preferences('local-analyst')['revision'] == 0


def test_all_memory_routes_require_authentication_and_reject_cross_origin_changes(memory_client):
    client, *_ = memory_client
    for path in ('/api/memory/preferences', '/api/memory/coverage', '/api/memory/note-policy'):
        assert client.get(path, headers={'X-Analyst-Token': ''}).status_code == 401
    response = client.put('/api/memory/preferences', headers={'Origin': 'https://untrusted.example'},
                          json={'expected_revision': 0, 'values': {'history_limit': 1}})
    assert response.status_code == 403


def test_foreign_actor_runs_cannot_be_viewed_decided_or_streamed(memory_client):
    client, _, store, _ = memory_client
    run = store.create_run({'question': 'Private invented run'}, actor='other-analyst')
    path = '/api/runs/' + run['id']
    assert client.get(path).status_code == 404
    assert client.get(path + '/events').status_code == 404
    assert client.post(path + '/decision', json={'kind': 'plan', 'action': 'reject', 'payload_hash': '0' * 64}).status_code == 404


def test_coverage_is_source_bound_and_has_explicit_section_limitations(memory_client):
    client, _, _, source = memory_client
    response = client.get('/api/memory/coverage')
    assert response.status_code == 200
    value = response.json()
    assert value['source_fingerprint'] == source.fingerprint and value['company_year_count'] == 6
    assert all(row['original_boundaries_verified'] is False for row in value['rows'])


def test_history_exclusion_and_restore_leave_the_signed_library_unchanged(memory_client):
    client, engine, store, source = memory_client
    published = decide(engine, decide(engine, begin(engine, store)))
    assert published['status'] == 'published'
    original = store.notes()
    query = {'query': 'annual research operating margins risk', 'tickers': ['MSFT'], 'years': [2025]}
    result = client.post('/api/memory/history/search', json=query).json()
    assert len(result['references']) == 1 and 'body' not in result['references'][0]
    identifier = result['references'][0]['note_id']
    comparison = client.get('/api/memory/notes/' + identifier + '/comparison').json()
    assert all(row['status'] == 'compared' and row['change']['margin_percentage_points'] == '0.00' for row in comparison['comparisons'])
    excluded = client.put('/api/memory/notes/' + identifier + '/eligibility', json={'expected_revision': 0, 'excluded': True})
    assert excluded.status_code == 200
    assert client.post('/api/memory/history/search', json=query).json()['references'] == []
    assert client.get('/api/memory/notes/' + identifier + '/comparison').status_code == 404
    assert store.notes() == original
    restored = client.put('/api/memory/notes/' + identifier + '/eligibility', json={'expected_revision': excluded.json()['revision'], 'excluded': False})
    assert restored.status_code == 200 and len(client.post('/api/memory/history/search', json=query).json()['references']) == 1
    assert store.notes() == original


def test_browser_saved_defaults_are_explicit_and_refuse_stale_source_scope():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js needed to execute the browser helper')
    source = {'companies': [{'ticker': 'MSFT'}], 'company_years': {'MSFT': [2025]}}
    profile = {'status': 'active', 'values': {'default_companies': ['OTHER'], 'default_years': [2025]}}
    script = "const {preferenceDefaults}=require(process.argv[1]);try{console.log(JSON.stringify({value:preferenceDefaults(JSON.parse(process.argv[2]),JSON.parse(process.argv[3]))}));}catch(error){console.log(JSON.stringify({error:error.message}));}"
    result = subprocess.run([node, '-e', script, str(Path(__file__).resolve().parents[1] / 'web/memory.js'), json.dumps(source), json.dumps(profile)],
        capture_output=True, text=True, check=True, timeout=10)
    assert 'Saved company defaults' in json.loads(result.stdout)['error']
