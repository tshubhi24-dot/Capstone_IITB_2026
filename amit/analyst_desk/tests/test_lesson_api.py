"""Lesson review API checks on declared synthetic development events, never real review."""
from copy import deepcopy
import hashlib

import pytest

from desk.development import admit_development, public_cases
from desk.store import canonical_hash
from test_memory_api import memory_client
from test_workflow import fixture


def failure(store,source,*,actor='local-analyst',stage='critic_reject'):
    case=public_cases()[0]
    request=admit_development({'question':case['question'],'tickers':case['tickers'],'years':case['years'],
        'learning_split':'development','development_case_id':case['case_id'],'memory_enabled':False,'mode':'offline'},source)
    run=store.create_run(request,actor)
    run.update(status='awaiting_note',source_fingerprint=source.fingerprint,
               plan={'tickers':case['tickers'],'years':case['years'],'outline':['Invented fixture only']})
    store.save_run(run)
    details={'passed':False,'issues':['Numeric table differs from current facts.'],'source_fingerprint':source.fingerprint,
             'draft_hash':'a'*64,'body_hash':'b'*64}
    if stage=='note_edit': details.update(before_draft_hash='a'*64,before_body_hash='b'*64,after_body_hash='c'*64)
    event=store.event(run['id'],'human' if stage=='note_edit' else 'critic',stage,'Declared synthetic fixture, not a genuine research failure or human review.',details)
    return run,event


def reflect(client,run,event,revision=0):
    return client.post('/api/lessons/reflect',json={'run_id':run['id'],'event_id':event['id'],'mode':'rules','expected_revision':revision})


def test_lesson_routes_authenticate_and_reject_cross_origin_changes(memory_client):
    client,*_=memory_client
    for path in ('/api/lessons','/api/development/cases'):
        assert client.get(path,headers={'X-Analyst-Token':''}).status_code==401
    assert client.post('/api/playbooks',headers={'Origin':'https://untrusted.example'},json={'expected_revision':0,'lesson_ids':['a'*32]}).status_code==403
    assert client.get('/api/lessons').json()['bank']['revision']==0


def test_registered_development_catalogue_has_no_expected_answers_and_admission_rejects_changes(memory_client):
    client,*_=memory_client
    value=client.get('/api/development/cases').json()
    assert len(value['cases'])==20 and value['expected_answers_included'] is False and value['publication_allowed'] is False
    case=value['cases'][0]
    request={k:case[k] for k in ('question','tickers','years')}
    request.update(learning_split='development',development_case_id=case['case_id'],memory_enabled=False)
    assert client.post('/api/runs',json={**request,'question':'A different arbitrary question'}).status_code==400
    assert client.post('/api/runs',json={**request,'memory_enabled':True}).status_code==400
    assert client.post('/api/runs',json={**request,'development_admission':{'trusted':True}}).status_code==422
    assert client.post('/api/runs',json={**request,'learning_split':'held_out'}).status_code==422


def test_reflection_creates_only_a_pending_proposal_without_model_or_playbook(memory_client):
    client,engine,store,source=memory_client
    run,event=failure(store,source)
    response=reflect(client,run,event)
    assert response.status_code==200,response.text
    value=response.json();proposal=value['proposal']
    assert proposal['status']=='pending' and proposal['action']=='verify_current_facts'
    assert value['accepted'] is False and value['human_review_required'] is True and value['model_calls_requested']==0
    assert engine.model_client is None and store.notes()==[]
    listing=client.get('/api/lessons').json()
    assert listing['playbooks']==[] and len(listing['lessons'])==1


def test_production_or_foreign_origin_cannot_be_reflected(memory_client):
    client,_,store,source=memory_client
    run,event=failure(store,source,actor='other-analyst')
    assert reflect(client,run,event).status_code==404
    run,event=failure(store,source)
    run['request']['learning_split']='production';store.save_run(run)
    assert reflect(client,run,event).status_code==400
    assert client.get('/api/lessons').json()['bank']['revision']==0


def test_live_reflection_rejects_unapproved_offline_origin_without_any_call(memory_client):
    client,_,store,source=memory_client
    run,event=failure(store,source)
    response=client.post('/api/lessons/reflect',json={'run_id':run['id'],'event_id':event['id'],'mode':'live','expected_revision':0})
    assert response.status_code==400
    assert client.get('/api/lessons').json()['lessons']==[]


def test_exact_hash_and_reasoned_decision_then_explicit_freeze(memory_client):
    client,_,store,source=memory_client
    run,event=failure(store,source)
    proposal=reflect(client,run,event).json()['proposal'];identifier=proposal['lesson_id']
    payload={'proposal_hash':'f'*64,'decision':'accept','reason':'Synthetic fixture decision checks exact version binding.','expected_revision':1}
    assert client.post('/api/lessons/'+identifier+'/decision',json=payload).status_code==409
    payload['proposal_hash']=proposal['proposal_hash']
    accepted=client.post('/api/lessons/'+identifier+'/decision',json=payload)
    assert accepted.status_code==200 and accepted.json()['status']=='accepted'
    assert client.get('/api/lessons').json()['playbooks']==[]
    book=client.post('/api/playbooks',json={'lesson_ids':[identifier],'expected_revision':2})
    assert book.status_code==200 and len(book.json()['id'])==64
    assert client.post('/api/lessons/'+identifier+'/decision',json={**payload,'expected_revision':3}).status_code==409
    assert store.notes()==[]


def test_rejected_lesson_stays_auditable_and_cannot_be_frozen(memory_client):
    client,_,store,source=memory_client
    run,event=failure(store,source)
    proposal=reflect(client,run,event).json()['proposal'];identifier=proposal['lesson_id']
    rejected=client.post('/api/lessons/'+identifier+'/decision',json={'proposal_hash':proposal['proposal_hash'],'decision':'reject','reason':'Synthetic fixture rejection: applicability is too broad.','expected_revision':1})
    assert rejected.status_code==200 and rejected.json()['status']=='rejected'
    assert client.post('/api/playbooks',json={'lesson_ids':[identifier],'expected_revision':2}).status_code==409
    assert len(client.get('/api/lessons').json()['lessons'])==1


def test_request_lesson_switch_and_playbook_are_explicitly_paired(memory_client):
    client,*_=memory_client
    base={'question':'Compare current annual operating margins.','tickers':['MSFT'],'years':[2025]}
    for change in ({'lessons_enabled':True},{'playbook_id':'a'*64},{'lessons_enabled':'yes'}):
        assert client.post('/api/runs',json={**base,**change}).status_code==422


def approved_reflection_fixture(store,source):
    """Fictional approval record for mocked transport tests; not human evidence."""
    run,event=failure(store,source)
    run['request']['mode']='live'
    approved=store.event(run['id'],'human','plan_approved','Fictional test-only plan approval.',{'payload_hash':canonical_hash(run['plan'])})
    run['plan_approval']={'payload_hash':canonical_hash(run['plan']),'request_hash':canonical_hash(run['request']),
                          'source_fingerprint':source.fingerprint,'event_id':approved['id']}
    store.save_run(run)
    return run,event


@pytest.mark.parametrize('mutation',['source','event','event_payload'])
def test_paid_reflection_checks_original_plan_approval_before_transport(memory_client,monkeypatch,mutation):
    client,engine,store,source=memory_client
    run,event=approved_reflection_fixture(store,source)
    if mutation=='source':run['plan_approval']['source_fingerprint']='f'*64
    elif mutation=='event':run['plan_approval']['event_id']=event['id']
    else:
        other=store.event(run['id'],'human','plan_approved','Fictional wrong payload.',{'payload_hash':'f'*64})
        run['plan_approval']['event_id']=other['id']
    store.save_run(run)
    def forbidden(*args,**kwargs):raise AssertionError('Invalid plan proof must not request a model.')
    monkeypatch.setattr(engine,'reasoner',forbidden)
    response=client.post('/api/lessons/reflect',json={'run_id':run['id'],'event_id':event['id'],'mode':'live','expected_revision':0})
    assert response.status_code==400
    assert engine.lessons.list_lessons()==[]


def test_mocked_live_reflection_uses_only_controlled_metadata_and_remains_pending(memory_client,monkeypatch):
    client,engine,store,source=memory_client
    run,event=approved_reflection_fixture(store,source)
    calls=[]
    class FakeReflection:
        def reflect_lesson(self,summary,catalogue):
            calls.append(summary)
            assert set(summary)=={'event_kind','failure_codes','scope'}
            assert 'question' not in summary and 'body' not in summary
            return {'action':'verify_current_facts','summary':catalogue['verify_current_facts'],
                    'applicability':'Fictional applicability for a mock reflection test.',
                    'counterexamples':'Fictional limits: a wording change does not imply arithmetic failure.'}
    def mocked_reasoner(state,purpose):
        assert state['run_id']==run['id'] and purpose.startswith('development-reflection:')
        return FakeReflection()
    monkeypatch.setattr(engine,'reasoner',mocked_reasoner)
    response=client.post('/api/lessons/reflect',json={'run_id':run['id'],'event_id':event['id'],'mode':'live','expected_revision':0})
    assert response.status_code==200,response.text
    assert response.json()['proposal']['status']=='pending' and len(calls)==1
    assert engine.lessons.list_playbooks()==[] and store.notes()==[]
