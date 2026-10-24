"""Development admission tests use public questions and invented source identity."""
from copy import deepcopy
import json

import pytest

from desk.development import CATALOGUE_PATH, admit_development, public_cases, validate_development_run


class Source:
    fingerprint = 'a'*64
    def years(self,ticker):
        return [2023,2024,2025]


def request():
    case=public_cases()[0]
    return {'question':case['question'],'tickers':case['tickers'],'years':case['years'],
            'learning_split':'development','development_case_id':case['case_id'],'memory_enabled':False}


def test_catalogue_bundles_only_public_questions_and_scope_without_gold():
    raw=json.loads(CATALOGUE_PATH.read_text())
    assert len(public_cases())==20 and raw['final_eligible'] is False
    assert all(set(case)=={'case_id','question','tickers','years','case_type','subtype','scenario_group_id'} for case in raw['cases'])
    assert len([case for case in public_cases(Source()) if case['available']])==19


def test_public_development_admission_matches_exact_registered_case_and_source():
    value=request()
    admitted=admit_development(value,Source())
    assert 'development_admission' not in value
    run={'request':admitted,'source_fingerprint':Source.fingerprint}
    assert validate_development_run(run)==admitted['development_admission']


@pytest.mark.parametrize('field,value',[
 ('question','An arbitrary protected question must never become development.'),
 ('tickers',['UNH']),('years',[2024]),('development_case_id','FINAL001'),
 ('memory_enabled',True),('plant_error',True),('inject_article',True),('learning_split','held_out')])
def test_changed_case_unknown_split_or_private_memory_is_rejected(field,value):
    asked=request();asked[field]=value
    with pytest.raises(ValueError): admit_development(asked,Source())


def test_uncovered_registered_refusal_case_cannot_become_research_run():
    case=next(row for row in public_cases() if row['case_id']=='KDEV007')
    asked={**request(),**{k:case[k] for k in ('question','tickers','years')},'development_case_id':case['case_id']}
    with pytest.raises(ValueError,match='outside'): admit_development(asked,Source())


@pytest.mark.parametrize('mutation',['source','admission','question','split'])
def test_origin_revalidation_catches_tampered_records(mutation):
    run={'request':admit_development(request(),Source()),'source_fingerprint':Source.fingerprint}
    if mutation=='source': run['source_fingerprint']='b'*64
    elif mutation=='admission': run['request']['development_admission']['case_hash']='b'*64
    elif mutation=='question': run['request']['question']='A different question'
    else: run['request']['learning_split']='production'
    with pytest.raises(ValueError): validate_development_run(run)


def test_old_production_runs_cannot_be_relabelled_without_exact_admission():
    with pytest.raises(ValueError): validate_development_run({'request':request(),'source_fingerprint':Source.fingerprint})
    assert admit_development({'question':'Ordinary research'},Source())=={'question':'Ordinary research'}
    with pytest.raises(ValueError): admit_development({'learning_split':'production','development_case_id':'KDEV001'},Source())
