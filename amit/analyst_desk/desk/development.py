"""Admission for bundled public development questions, without evaluator answers."""
from copy import deepcopy
import json
from pathlib import Path
import re

from .store import canonical_hash

CATALOGUE_PATH = Path(__file__).resolve().parents[1] / 'data/development_cases.json'
DEVELOPMENT_ISSUERS = {'MSFT', 'AAPL', 'ABBV', 'AMGN'}


def _catalogue():
    value = json.loads(CATALOGUE_PATH.read_text())
    digest = value.get('catalogue_hash')
    if (set(value) != {'schema_version','split','final_eligible','source','source_review','cases','catalogue_hash'}
            or value['schema_version'] != 1 or value['split'] != 'development'
            or value['final_eligible'] is not False
            or canonical_hash({k:v for k,v in value.items() if k != 'catalogue_hash'}) != digest):
        raise ValueError('The public development catalogue is invalid.')
    rows = value['cases']
    if (not isinstance(rows,list) or len(rows) != 20
            or len({row['case_id'] for row in rows}) != 20):
        raise ValueError('The public development case registry is invalid.')
    for row in rows:
        if (set(row) != {'case_id','question','tickers','years','case_type','subtype','scenario_group_id'}
                or not re.fullmatch(r'KDEV\d{3}',row['case_id'])
                or not isinstance(row['question'],str) or not 8 <= len(row['question']) <= 3000
                or not row['tickers'] or not set(row['tickers']) <= DEVELOPMENT_ISSUERS
                or not row['years'] or any(type(year) is not int for year in row['years'])):
            raise ValueError('The public development record is invalid.')
    return value


def public_cases(source=None):
    """Expose ordinary public questions and scope, never expected answers."""
    value = _catalogue()
    rows = deepcopy(value['cases'])
    for row in rows:
        row['case_hash'] = canonical_hash({k:row[k] for k in ('case_id','question','tickers','years','case_type','subtype','scenario_group_id')})
        row['available'] = source is None or all(set(row['years']) <= set(source.years(ticker)) for ticker in row['tickers'])
        row['source_review'] = value['source_review']
    return rows


def _registered(request):
    catalogue = _catalogue()
    matches = [row for row in catalogue['cases'] if row['case_id'] == request.get('development_case_id')]
    if len(matches) != 1:
        raise ValueError('Choose a registered public development case.')
    case = matches[0]
    if (request.get('question') != case['question']
            or sorted(request.get('tickers',[])) != sorted(case['tickers'])
            or request.get('years') != case['years']
            or request.get('memory_enabled') is not False
            or request.get('plant_error',False) is not False
            or request.get('inject_article',False) is not False):
        raise ValueError('Development research must match the public case exactly and keep private analyst memory off.')
    return catalogue, case


def _admission(catalogue, case, source_fingerprint):
    if not isinstance(source_fingerprint,str) or not re.fullmatch(r'[a-f0-9]{64}',source_fingerprint):
        raise ValueError('Development admission needs the frozen public source identity.')
    value = {'kind':'registered_public_development','case_id':case['case_id'],
             'case_hash':canonical_hash(case),'catalogue_hash':catalogue['catalogue_hash'],
             'source_fingerprint':source_fingerprint,'final_eligible':False}
    return {**value,'admission_hash':canonical_hash(value)}


def admit_development(request, source):
    """Server-created provenance; clients cannot supply their own admission."""
    value = deepcopy(request)
    split = value.get('learning_split','production')
    if split == 'production':
        if value.get('development_case_id') is not None or value.get('development_admission') is not None:
            raise ValueError('Production research cannot claim development provenance.')
        return value
    if split != 'development':
        raise ValueError('Only production or registered public development research is admitted.')
    catalogue, case = _registered(value)
    if any(not set(case['years']) <= set(source.years(ticker)) for ticker in case['tickers']):
        raise ValueError('This development case requests years outside the current cached source.')
    value['development_admission'] = _admission(catalogue,case,source.fingerprint)
    return value


def validate_development_run(run):
    """Recheck persisted origin before reflection; old production runs stay ineligible."""
    if not isinstance(run,dict) or run.get('request',{}).get('learning_split') != 'development':
        raise ValueError('Only registered development runs may produce lessons.')
    request = run['request']
    catalogue, case = _registered(request)
    expected = _admission(catalogue,case,run.get('source_fingerprint'))
    if request.get('development_admission') != expected:
        raise ValueError('The development origin or frozen source changed.')
    return deepcopy(expected)
