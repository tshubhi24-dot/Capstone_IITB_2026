"""Read-only evidence menus bind to the exact live note, not client-supplied text."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from desk.api import app
from desk.reasoning import quote_menu
from desk.store import canonical_hash
from desk.workflow import live_body


@pytest.fixture
def review_api(monkeypatch):
    evidence = [
        {'id':'test-source-before','ticker':'AAPL','year':2024,'text':'The selected earlier passage describes operations and facilities exposed to natural disasters.'},
        {'id':'test-source-after','ticker':'AAPL','year':2025,'text':'The selected later passage describes operations, retail stores and facilities exposed to natural disasters.'},
    ]
    menu = quote_menu(evidence)
    claim = {'claim_id':'risk-test','ticker':'AAPL','before_year':2024,'after_year':2025,
             'category':'risk_observation','confidence':'low','text':'Selected excerpts describe natural disaster exposure.',
             'citations':[{'source_id':row['source_id'],'quote':row['quote']} for row in menu]}
    draft = {'model_mode':'live','source_fingerprint':'synthetic-source','plan':{'tickers':['AAPL'],'years':[2024,2025]},
             'ai_evidence':evidence,'narrative_claims':[claim],'live_sections':{'risk_ids':['risk-test'],'writer_ids':[]},
             'numeric_table':'Synthetic checked table','history_sentence':'Analyst memory is off for this research.'}
    draft['body'] = live_body(draft)
    current = {'id':'test-run','actor':'local-analyst','status':'awaiting_note','request':{'mode':'live'},
               'pending':{'kind':'note','payload':draft,'payload_hash':canonical_hash(draft)}}
    class Engine:
        claims = []
        def view(self, rid):return deepcopy(current) if rid=='test-run' else None
        def claim(self,rid,decision):self.claims.append(deepcopy(decision))
        def execute(self,rid):pass
    engine=Engine()
    monkeypatch.setattr(app.router,'lifespan_context',FastAPI().router.lifespan_context)
    monkeypatch.setattr(app.state,'engine',engine,raising=False)
    monkeypatch.setattr(app.state,'source',SimpleNamespace(fingerprint='synthetic-source'),raising=False)
    monkeypatch.setenv('ANALYST_API_TOKEN','synthetic-analyst-token')
    with TestClient(app,headers={'X-Analyst-Token':'synthetic-analyst-token'}) as client:
        yield client,current,engine,menu


def test_exact_menu_read_does_not_mutate_or_queue_work(review_api):
    client,current,engine,menu=review_api
    before=deepcopy(current);fingerprint=current['pending']['payload_hash']
    response=client.get('/api/runs/test-run/citation-options',params={'draft_hash':fingerprint})
    assert response.status_code==200
    value=response.json();assert value['draft_hash']==fingerprint
    assert len(value['claims'])==1 and len(value['claims'][0]['slots'])==2
    assert {row['quote_id'] for slot in value['claims'][0]['slots'] for row in slot['options']}=={row['quote_id'] for row in menu}
    assert current==before and engine.claims==[]


@pytest.mark.parametrize('change',['hash','status','kind','mode','source','changed_payload','actor'])
def test_menu_refuses_stale_or_inapplicable_review(review_api,change):
    client,current,engine,menu=review_api;fingerprint=current['pending']['payload_hash']
    if change=='hash':fingerprint='0'*64
    elif change=='status':current['status']='running'
    elif change=='kind':current['pending']['kind']='plan'
    elif change=='actor':current['actor']='someone-else'
    elif change=='mode':current['pending']['payload']['model_mode']='offline'
    elif change=='source':current['pending']['payload']['source_fingerprint']='different-source'
    else:current['pending']['payload']['body']+=' changed'
    result=client.get('/api/runs/test-run/citation-options',params={'draft_hash':fingerprint})
    assert result.status_code==(404 if change=='actor' else 409)
    assert engine.claims==[]


def test_menu_requires_authentication_and_exact_hash_shape(review_api):
    client,current,engine,menu=review_api
    assert client.get('/api/runs/test-run/citation-options').status_code==422
    assert client.get('/api/runs/test-run/citation-options?draft_hash=bad').status_code==422
    assert client.get('/api/runs/test-run/citation-options',params={'draft_hash':current['pending']['payload_hash']},headers={'X-Analyst-Token':'wrong'}).status_code==401


def test_selected_evidence_edit_is_forwarded_as_structured_choices(review_api):
    client,current,engine,menu=review_api
    edits={'body':current['pending']['payload']['body'],'citation_selections':{'risk-test':[x['quote_id'] for x in menu]}}
    result=client.post('/api/runs/test-run/decision',json={'kind':'note','action':'edit','payload_hash':current['pending']['payload_hash'],'edits':edits})
    assert result.status_code==202 and engine.claims[0]['edits']==edits


@pytest.mark.parametrize('edits',[{'body':'x','unapproved':'value'},{'citation_selections':{}},{'body':[],'citation_selections':{}}])
def test_note_edit_rejects_unrelated_or_malformed_fields_before_queue(review_api,edits):
    client,current,engine,menu=review_api
    response=client.post('/api/runs/test-run/decision',json={'kind':'note','action':'edit','payload_hash':current['pending']['payload_hash'],'edits':edits})
    assert response.status_code==400 and engine.claims==[]
