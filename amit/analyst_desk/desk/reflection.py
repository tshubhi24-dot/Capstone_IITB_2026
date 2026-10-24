"""Bounded development reflection; proposals always await a separate human decision."""
from .development import validate_development_run
from .store import canonical_hash

STAGES = ['planner','researcher','risk','writer']


def reflection_input(engine, run_id, event_id, actor='local-analyst'):
    run = engine.store.get_run(run_id)
    if run is None or run.get('actor') != actor:
        raise ValueError('Development run is unavailable.')
    validate_development_run(run)
    engine.lessons.validate_origin(run_id,event_id,actor=actor)
    if run.get('source_fingerprint') != engine.source.fingerprint:
        raise ValueError('Reflection requires the original source snapshot.')
    if run.get('status') in {'queued','running'}:
        raise ValueError('Wait for development research to pause before reflecting.')
    matches = [event for event in engine.store.events(run_id) if event['id'] == event_id]
    if len(matches) != 1:
        raise ValueError('Choose an actual critic rejection or analyst edit.')
    event = matches[0]
    details = event.get('details',{})
    kind = event.get('stage')
    if kind == 'critic_reject':
        if event.get('agent') != 'critic' or details.get('passed') is not False:
            raise ValueError('The selected event is not a failed development check.')
        messages = ' '.join(str(value)[:500] for value in details.get('issues',[])[:16]).casefold()
        codes = []
        for words,code in ((('fiscal','period','unit'),'fiscal_comparability'),
                           (('number','numeric','table','fact'),'numeric_verification'),
                           (('citation','provenance','source'),'source_provenance'),
                           (('unsupported','semantic','risk','claim'),'claim_support')):
            if any(word in messages for word in words): codes.append(code)
        codes = codes or ['failed_code_or_support_check']
    elif kind == 'note_edit':
        if event.get('agent') != 'human':
            raise ValueError('The selected edit lacks analyst provenance.')
        codes = ['analyst_changed_note']
    else:
        raise ValueError('Only actual critic rejections or analyst note edits support lessons.')
    plan = run.get('plan') or {}
    scope = {'tickers':run['request']['tickers'],'years':run['request']['years']}
    if plan and (sorted(plan['tickers']) != sorted(scope['tickers']) or plan['years'] != scope['years']):
        raise ValueError('The development plan differs from its admitted case.')
    return run, {'event_kind':kind,'failure_codes':codes,'scope':scope}


def rule_reflection(summary):
    """Reflect only on code-decidable categories; this is not an LLM judgment."""
    from .lessons import ACTION_HINTS
    codes = summary['failure_codes']
    if 'fiscal_comparability' in codes: action='align_fiscal_periods'
    elif 'numeric_verification' in codes: action='verify_current_facts'
    elif 'source_provenance' in codes: action='cite_exact_evidence'
    elif 'claim_support' in codes: action='preserve_risk_qualifiers'
    else: action='verify_current_facts'
    return {'action':action,'summary':ACTION_HINTS[action],
            'applicability':'Apply to the registered company and fiscal-year scope when this development check or edit pattern recurs.',
            'counterexamples':('A wording-only analyst edit does not establish a financial error. Evidence and applicability need human review.'
                               if summary['event_kind']=='note_edit' else
                               'A rejected draft does not establish that every claim is wrong. Confirm the selected failure category against the cited source.')}


def propose_reflection(engine, run_id, event_id, expected_revision, mode='rules', actor='local-analyst'):
    from .lessons import ACTION_HINTS, LessonConflict
    run, summary = reflection_input(engine,run_id,event_id,actor)
    if engine.lessons.get_bank(actor)['revision'] != expected_revision:
        raise LessonConflict('Lessons changed; reload before reflecting.')
    if mode == 'rules':
        candidate = rule_reflection(summary)
        method = 'code_owned_category_reflection'
    elif mode == 'live':
        approval = run.get('plan_approval') or {}
        review_events = [event for event in engine.store.events(run_id)
                         if event['id'] == approval.get('event_id')]
        if (run['request'].get('mode') != 'live' or not run.get('plan')
                or approval.get('payload_hash') != canonical_hash(run['plan'])
                or approval.get('request_hash') != canonical_hash(run['request'])
                or approval.get('source_fingerprint') != engine.source.fingerprint
                or len(review_events) != 1 or review_events[0].get('agent') != 'human'
                or review_events[0].get('stage') != 'plan_approved'
                or review_events[0].get('details',{}).get('payload_hash') != canonical_hash(run['plan'])):
            raise ValueError('AI reflection requires this development run\'s original approved live plan and budget.')
        state = {**run,'run_id':run_id}
        result = engine.reasoner(state,'development-reflection:'+str(event_id)+':'+canonical_hash(summary)).reflect_lesson(summary,ACTION_HINTS)
        candidate = {key:result[key] for key in ('action','summary','applicability','counterexamples')}
        method = 'model_assisted_unreviewed_reflection'
    else:
        raise ValueError('Choose code reflection or explicitly requested live reflection.')
    proposal = engine.lessons.propose(actor=actor,run_id=run_id,event_id=event_id,
        expected_revision=expected_revision,scope={**summary['scope'],'stages':STAGES},**candidate)
    return {'proposal':proposal,'reflection_method':method,'human_review_required':True,
            'accepted':False,'model_calls_requested':1 if mode=='live' else 0}
