"""Exercise real browser handlers with deliberately reordered fake HTTP responses.

The DOM/transport fixtures create no real research, approvals or network calls.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

HARNESS = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup(){
 const nodes=new Map(),calls=[],timers=new Map(),rendered=[];let nextTimer=0;
 function element(tag){return {tag,children:[],value:'',textContent:'',hidden:false,disabled:false,checked:false,selectedOptions:[],options:[],append(...items){this.children.push(...items);},replaceChildren(...items){this.children=[...items];},get firstChild(){return this.children[0];},querySelector(){return {disabled:false};},scrollIntoView(){}};}
 const get=id=>{if(!nodes.has(id))nodes.set(id,element(id));return nodes.get(id);};
 const sandbox={module:{exports:{}},console,URLSearchParams,location:{search:''},sessionStorage:{getItem:()=>'',setItem(){}},
  window:{AnalystMemory:{initialize(){},renderRun:run=>rendered.push(['memory',run.id]),renderNote(){}},AnalystLessons:{initialize(){},requestOptions:()=>({}),renderRun:run=>rendered.push(['lessons',run.id])}},
  fetch:(path,options)=>{if((path==='/api/runs'&&!options?.method)||path==='/api/notes')return Promise.resolve({ok:true,json:async()=>[]});return new Promise((resolve,reject)=>calls.push({path,options,resolve:value=>resolve({ok:true,json:async()=>value}),fail:text=>resolve({ok:false,json:async()=>({detail:text})}),reject}));},
  setTimeout:(callback,delay)=>{const id=++nextTimer;timers.set(id,{callback,delay});return id;},clearTimeout:id=>timers.delete(id)};
 vm.createContext(sandbox);
 vm.runInContext(fs.readFileSync(process.argv[1],'utf8')+'\n;globalThis.desk={state,selectRun,refresh,decide,resumeResearch,updateScope,initialize};',sandbox);
 sandbox.document={getElementById:get,createElement:element};
 const pending=(id,hash=id+'-exact',status='awaiting_plan')=>({id,status,mode:'live',request:{tickers:['MSFT'],years:[2024,2025]},events:[],pending:{kind:'plan',payload_hash:hash,payload:{outline:['Inspect original evidence'],tickers:['MSFT'],years:[2024,2025],caveats:[]}}});
 return {desk:sandbox.desk,get,calls,timers,rendered,pending};
}
async function tick(){await new Promise(resolve=>setImmediate(resolve));}
function noteRun(h,id='note-run',hash='note-one'){
 const run=h.pending(id,hash,'awaiting_note');run.pending={kind:'note',payload_hash:hash,payload:{body:'Exact reviewed note '+hash}};
 run.critic={passed:true,verified_numbers:6,total_numbers:6};
 run.draft={metrics:[{ticker:'MSFT',year:2025,period_start:'2024-07-01',period_end:'2025-06-30',revenue:100,operating_income:10,margin_pct:10,fact_ids:[]}],narrative_claims:[{text:'Fictional test claim',confidence:'test-only',citations:[{quote:'Fictional public evidence',source_id:'test-source'}]}]};
 run.risks=[{ticker:'MSFT',before_year:2024,after_year:2025,text_changed:true,interpretation:'Fictional test interpretation',source_ids:[]}];return run;
}
"""


def browser_check(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute the actual browser handlers")
    result = subprocess.run(
        [node, "-e", HARNESS + "\n(async()=>{\n" + script + "\nconsole.log('browser-check-completed');})().catch(error=>{console.error(error);process.exitCode=1;});", str(ROOT / "web/app.js")],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "browser-check-completed" in result.stdout, "Browser check ended before its asynchronous assertions completed"


@pytest.mark.parametrize("obsolete_response", ["success", "failure"])
def test_previous_run_response_cannot_render_message_or_schedule_poll(obsolete_response):
    browser_check(r"""
const h=setup(),a=h.desk.selectRun('old-run'),b=h.desk.selectRun('new-run');
assert.equal(h.get('review').hidden,true);assert.equal(h.get('approve').disabled,true);
h.calls[1].resolve(h.pending('new-run'));await b;
assert.equal(h.desk.state.run.id,'new-run');assert.equal(h.get('runs').value,'new-run');
assert.equal(h.get('message').textContent,'');assert.equal(h.timers.size,1);
""" + (
        "h.calls[0].resolve({...h.pending('old-run'),error:'provider_http_429'});"
        if obsolete_response == "success" else
        "h.calls[0].reject(new Error('obsolete provider error'));"
    ) + r"""
await a;assert.equal(h.desk.state.run.id,'new-run');assert.match(h.get('status').textContent,/new-run/);
assert.equal(h.get('message').textContent,'');assert.equal(h.timers.size,1);
assert.deepEqual(h.rendered,[['memory','new-run'],['lessons','new-run']]);
""")


def test_old_poll_callback_cannot_restart_after_switch_or_clear_selection():
    browser_check(r"""
const h=setup(),a=h.desk.selectRun('old-run');h.calls[0].resolve(h.pending('old-run'));await a;
const oldCallback=[...h.timers.values()][0].callback;
const b=h.desk.selectRun('new-run');assert.equal(h.timers.size,0);assert.equal(h.get('editor').disabled,true);
h.calls[1].resolve(h.pending('new-run'));await b;
await oldCallback();assert.equal(h.calls.length,2);assert.equal(h.desk.state.run.id,'new-run');
const newCallback=[...h.timers.values()][0].callback;
await h.desk.selectRun('');await newCallback();
assert.equal(h.calls.length,2);assert.equal(h.timers.size,0);assert.equal(h.desk.state.run,null);
assert.equal(h.get('current').hidden,true);assert.equal(h.get('review').hidden,true);
""")


def test_switch_clears_old_run_error_and_blocks_review_until_new_payload_loaded():
    browser_check(r"""
const h=setup(),a=h.desk.selectRun('old-run');
h.calls[0].resolve({...h.pending('old-run'),error:'provider_http_429'});await a;
assert.match(h.get('message').textContent,/HTTP 429/);
const b=h.desk.selectRun('new-run');assert.doesNotMatch(h.get('message').textContent,/429/);
await h.desk.decide('approve');await h.desk.decide('edit');await h.desk.decide('reject');
assert.equal(h.calls.length,2);assert.equal(h.get('review').hidden,true);
h.calls[1].resolve(h.pending('new-run','new-exact-hash'));await b;
assert.equal(h.get('message').textContent,'');assert.equal(h.get('approve').disabled,false);
const decision=h.desk.decide('approve');assert.equal(h.calls[2].path,'/api/runs/new-run/decision');
const body=JSON.parse(h.calls[2].options.body);
assert.equal(body.payload_hash,'new-exact-hash');assert.equal(body.action,'approve');
h.calls[2].fail('fictional decision refused');await decision;
""")


def test_same_run_refresh_and_reselection_preserve_unsaved_edits_but_new_hash_requires_review():
    browser_check(r"""
const h=setup(),a=h.desk.selectRun('same-run');h.calls[0].resolve(h.pending('same-run','hash-one'));await a;
h.get('editor').value='Unsaved analyst wording';
const refresh=h.desk.refresh('same-run');h.calls[1].resolve(h.pending('same-run','hash-one'));await refresh;
assert.equal(h.get('editor').value,'Unsaved analyst wording');
const again=h.desk.selectRun('same-run');h.calls[2].resolve(h.pending('same-run','hash-one'));await again;
assert.equal(h.get('editor').value,'Unsaved analyst wording');
await h.desk.decide('approve');assert.equal(h.calls.length,3);assert.match(h.get('message').textContent,/Save your edits first/);
const newer=h.desk.refresh('same-run');h.calls[3].resolve(h.pending('same-run','hash-two'));await newer;
assert.equal(h.get('editor').value,'Inspect original evidence');assert.match(h.get('fingerprint').textContent,/hash-two/);
""")


def test_older_refresh_of_same_run_cannot_restore_a_stale_review_version():
    browser_check(r"""
const h=setup(),a=h.desk.selectRun('same-run');h.calls[0].resolve(h.pending('same-run','hash-one'));await a;
const older=h.desk.refresh('same-run'),newer=h.desk.refresh('same-run');
h.calls[2].resolve(h.pending('same-run','hash-three'));await newer;
h.get('editor').value='Current unsaved edit';
h.calls[1].resolve(h.pending('same-run','hash-two'));await older;
assert.match(h.get('fingerprint').textContent,/hash-three/);assert.equal(h.get('editor').value,'Current unsaved edit');
assert.equal(h.timers.size,1);
""")


@pytest.mark.parametrize("decision_result", ["success", "failure"])
def test_decision_completion_from_old_run_cannot_refresh_or_error_on_new_selection(decision_result):
    browser_check(r"""
const h=setup(),a=h.desk.selectRun('old-run');h.calls[0].resolve(h.pending('old-run'));await a;
const decision=h.desk.decide('approve');
const b=h.desk.selectRun('new-run');h.calls[2].resolve(h.pending('new-run'));await b;
assert.equal(h.get('approve').disabled,true);
""" + (
        "h.calls[1].resolve({status:'accepted'});"
        if decision_result == "success" else
        "h.calls[1].fail('obsolete decision error');"
    ) + r"""
await decision;assert.equal(h.calls.length,3);assert.equal(h.desk.state.run.id,'new-run');
assert.equal(h.get('message').textContent,'');assert.equal(h.get('approve').disabled,false);
assert.equal(h.timers.size,1);
""")


def test_inflight_create_stays_disabled_on_scope_change_and_repeated_submit_makes_one_request():
    browser_check(r"""
const h=setup();h.desk.initialize();h.desk.state.connected=true;
h.desk.state.config={companies:[{ticker:'MSFT',sector:'Technology'}],company_years:{MSFT:[2024,2025]}};
h.get('mode').value='live';h.get('companies').selectedOptions=[{value:'MSFT'}];
h.get('years').selectedOptions=[{value:'2024'},{value:'2025'}];h.get('question').value='Fictional test question';
const first=h.get('research-form').onsubmit({preventDefault(){}});
h.desk.updateScope();assert.equal(h.get('start').disabled,true);
await h.get('research-form').onsubmit({preventDefault(){}});
assert.equal(h.calls.length,1);assert.equal(h.calls[0].path,'/api/runs');
h.calls[0].fail('fictional creation refused');await first;
assert.equal(h.desk.state.creating,false);assert.equal(h.get('start').disabled,false);
""")


@pytest.mark.parametrize("unsupported", ["not_error", "unavailable", "provider_connect_error", "rate_limit", "missing_hash", "invalid_hash"])
def test_resume_is_hidden_and_posts_nothing_for_unsupported_states(unsupported):
    browser_check(r"""
const h=setup(),run={...h.pending('stopped-run'),status:'error',error:'ReasoningError: content_validation',continuation:{available:true,failure_kind:'content_validation',plan_hash:'a'.repeat(64)}};
""" + {
        "not_error": "run.status='awaiting_plan';",
        "unavailable": "run.continuation.available=false;",
        "provider_connect_error": "run.error='ReviewError: provider_connect_error';run.continuation={available:false};",
        "rate_limit": "run.error='ReviewError: provider_http_429';run.continuation={available:false,retry_transient_available:true,failure_kind:'critic_rate_limit',plan_hash:'a'.repeat(64)};",
        "missing_hash": "delete run.continuation.plan_hash;",
        "invalid_hash": "run.continuation.plan_hash='not-an-approved-hash';",
    }[unsupported] + r"""
const selected=h.desk.selectRun(run.id);h.calls[0].resolve(run);await selected;
assert.equal(h.get('continuation').hidden,true);assert.equal(h.get('resume-research').disabled,true);
await h.desk.resumeResearch();assert.equal(h.calls.length,1);
""")


def test_resume_uses_exact_existing_run_and_plan_hash_once_then_only_polls():
    browser_check(r"""
const h=setup();h.desk.initialize();
const selected=h.desk.selectRun('stopped-run');
h.calls[0].resolve({...h.pending('stopped-run'),status:'error',error:'ReasoningError: content_validation',continuation:{available:true,failure_kind:'content_validation',plan_hash:'b'.repeat(64)}});await selected;
assert.equal(h.get('continuation').hidden,false);assert.equal(h.get('resume-research').disabled,false);
assert.match(h.get('continuation-plan').textContent,new RegExp('b'.repeat(64)));
assert.equal(h.calls.length,1);  // Rendering the control never continues automatically.
const resume=h.get('resume-research').onclick();
assert.equal(h.get('resume-research').disabled,true);await h.desk.resumeResearch();
assert.equal(h.calls.length,2);assert.equal(h.calls[1].path,'/api/runs/stopped-run/continue');
assert.deepEqual(JSON.parse(h.calls[1].options.body),{plan_hash:'b'.repeat(64)});
h.calls[1].resolve({status:'queued'});await tick();
assert.equal(h.calls[2].path,'/api/runs/stopped-run');
h.calls[2].resolve({...h.pending('stopped-run'),status:'running',pending:null});await resume;
assert.equal(h.get('continuation').hidden,true);assert.equal(h.get('resume-research').disabled,true);
assert.equal(h.timers.size,1);
await h.desk.resumeResearch();assert.equal(h.calls.length,3);
""")


@pytest.mark.parametrize("result", ["success", "failure"])
def test_resume_completion_from_previous_selection_cannot_refresh_or_show_error(result):
    browser_check(r"""
const h=setup(),selected=h.desk.selectRun('stopped-run');
h.calls[0].resolve({...h.pending('stopped-run'),status:'error',continuation:{available:true,failure_kind:'content_validation',plan_hash:'c'.repeat(64)}});await selected;
const resume=h.desk.resumeResearch(),next=h.desk.selectRun('new-run');
assert.equal(h.get('continuation').hidden,true);
await h.desk.resumeResearch();assert.equal(h.calls.length,3);
h.calls[2].resolve(h.pending('new-run'));await next;
""" + (
        "h.calls[1].resolve({status:'queued'});"
        if result == "success" else
        "h.calls[1].fail('obsolete continuation error');"
    ) + r"""
await resume;assert.equal(h.calls.length,3);assert.equal(h.desk.state.run.id,'new-run');
assert.equal(h.get('message').textContent,'');assert.equal(h.get('approve').disabled,false);
assert.equal(h.get('resume-research').disabled,true);assert.equal(h.timers.size,1);
""")


def test_failed_read_after_accepted_resume_stays_locked_until_fresh_selection():
    browser_check(r"""
const h=setup(),selected=h.desk.selectRun('stopped-run');
h.calls[0].resolve({...h.pending('stopped-run'),status:'error',continuation:{available:true,failure_kind:'content_validation',plan_hash:'d'.repeat(64)}});await selected;
const resume=h.desk.resumeResearch();h.calls[1].resolve({status:'queued'});await tick();
h.calls[2].fail('fictional refresh failed');await resume;
assert.equal(h.get('resume-research').disabled,true);
await h.desk.resumeResearch();assert.equal(h.calls.length,3);
const fresh=h.desk.selectRun('stopped-run');h.calls[3].resolve({...h.pending('stopped-run'),status:'running',pending:null});await fresh;
assert.equal(h.get('continuation').hidden,true);assert.equal(h.desk.state.loading,false);
""")


def test_identical_note_polls_preserve_expanded_evidence_dom_and_unsaved_editor():
    browser_check(r"""
const h=setup(),run=noteRun(h),selected=h.desk.selectRun(run.id);h.calls[0].resolve(run);await selected;
const claim=h.get('claims').firstChild,risk=h.get('risks').firstChild,row=h.get('rows').firstChild;
claim.open=true;risk.open=true;h.get('editor').value='Unsaved note wording';
h.desk.state.deciding=true;
const poll=h.desk.refresh(run.id);h.calls[1].resolve(JSON.parse(JSON.stringify(run)));await poll;
assert.equal(h.get('claims').firstChild,claim);assert.equal(h.get('risks').firstChild,risk);assert.equal(h.get('rows').firstChild,row);
assert.equal(claim.open,true);assert.equal(risk.open,true);assert.equal(h.get('editor').value,'Unsaved note wording');
assert.equal(h.get('approve').disabled,true);assert.equal(h.rendered.length,2);
h.desk.state.deciding=false;
const next=h.desk.refresh(run.id);h.calls[2].resolve(JSON.parse(JSON.stringify(run)));await next;
assert.equal(h.get('approve').disabled,false);assert.equal(h.get('claims').firstChild,claim);assert.equal(h.timers.size,1);
""")


def test_new_note_hash_and_explicit_selection_rebuild_evidence_but_same_version_keeps_edits():
    browser_check(r"""
const h=setup(),first=noteRun(h),selected=h.desk.selectRun(first.id);h.calls[0].resolve(first);await selected;
const oldClaim=h.get('claims').firstChild;oldClaim.open=true;
const changed=noteRun(h,first.id,'note-two');changed.draft.narrative_claims[0].citations[0].quote='Changed fictional public evidence';
const poll=h.desk.refresh(first.id);h.calls[1].resolve(changed);await poll;
assert.notEqual(h.get('claims').firstChild,oldClaim);assert.match(h.get('fingerprint').textContent,/note-two/);
assert.equal(h.get('editor').value,'Exact reviewed note note-two');
const changedClaim=h.get('claims').firstChild;h.get('editor').value='Unsaved current-version edit';
const again=h.desk.selectRun(first.id);h.calls[2].resolve(JSON.parse(JSON.stringify(changed)));await again;
assert.notEqual(h.get('claims').firstChild,changedClaim);assert.equal(h.get('review').hidden,false);
assert.equal(h.get('editor').value,'Unsaved current-version edit');assert.equal(h.rendered.length,6);
""")


def test_current_run_refresh_updates_saved_option_label_without_changing_other_runs():
    browser_check(r"""
const h=setup(),run=noteRun(h),current={value:run.id,textContent:'MSFT · live · error · note-run'},other={value:'other-run',textContent:'Other saved run'};
h.get('runs').options=[current,other];
const selected=h.desk.selectRun(run.id);h.calls[0].resolve(run);await selected;
assert.match(current.textContent,/awaiting_note/);assert.doesNotMatch(current.textContent,/error/);assert.equal(other.textContent,'Other saved run');
const poll=h.desk.refresh(run.id);h.calls[1].resolve({...run,status:'running',pending:null});await poll;
assert.match(current.textContent,/running/);assert.equal(h.get('runs').value,run.id);assert.equal(other.textContent,'Other saved run');
""")
