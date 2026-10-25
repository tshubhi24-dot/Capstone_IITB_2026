"""Actual browser handlers with fictional quotation menus and no HTTP/model calls."""
from pathlib import Path
import shutil
import subprocess

import pytest

from test_run_selection_ui import HARNESS

ROOT = Path(__file__).resolve().parents[1]

FIXTURES = r"""
function citationRun(h,id='research',hash='version-one'){
 const run=noteRun(h,id,hash);
 const claims=[{claim_id:'risk-1',text:'Earlier selected wording.',confidence:'test-only',citations:[{source_id:'a24',quote:'Current earlier public quotation.'},{source_id:'a25',quote:'Current later public quotation.'}]},{claim_id:'writer-1',text:'Bounded summary.',confidence:'test-only',citations:[{source_id:'summary',quote:'Current summary public quotation.'}]}];
 const body='## Fixed heading\n- Earlier selected wording. [a24] [a25]\n- Bounded summary. [summary]\n\n| Fixed financial table |\n\n## Fixed limits\nPartial public evidence.';
 run.draft={...run.draft,narrative_claims:claims,live_sections:{risk_ids:['risk-1'],writer_ids:['writer-1']},body};run.pending.payload=run.draft;
 return run;
}
function citationMenu(run){
 return {draft_hash:run.pending.payload_hash,claims:run.draft.narrative_claims.map(claim=>({claim_id:claim.claim_id,text:claim.text,slots:claim.citations.map((citation,index)=>{const year=claim.claim_id==='risk-1'?2024+index:2025,current={quote_id:'q-'+citation.source_id,source_id:citation.source_id,quote:citation.quote};return {ticker:'AAPL',year,current,options:[{...current,ticker:'AAPL',year,start:0,end:citation.quote.length,fragment:false},{quote_id:'new-'+citation.source_id,source_id:'changed-'+citation.source_id,ticker:'AAPL',year,quote:'Full alternative public quotation for '+citation.source_id+'.\nSecond sentence stays visible.',start:10,end:90,fragment:false}]};})}))};
}
async function openCitationRun(h,run){const request=h.desk.selectRun(run.id);h.calls.at(-1).resolve(run);await request;}
async function loadMenu(h,run,menu=citationMenu(run)){const request=h.desk.loadCitationOptions();h.calls.at(-1).resolve(menu);await request;return h.desk.state.citationReview;}
"""


def browser_check(script):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required to execute browser handlers")
    harness = HARNESS.replace(
        "resumeResearch,updateScope,initialize};",
        "resumeResearch,updateScope,initialize,loadCitationOptions,citationEdits,hasCitationChanges};",
    )
    result = subprocess.run(
        [node, "-e", harness + FIXTURES + "\n(async()=>{\n" + script + "\nconsole.log('citation-browser-completed');})().catch(error=>{console.error(error);process.exitCode=1;});", str(ROOT / "web/app.js")],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "citation-browser-completed" in result.stdout


def test_read_only_menu_defaults_to_exact_current_quotes_and_renders_full_preview():
    browser_check(r"""
const h=setup(),run=citationRun(h);await openCitationRun(h,run);
assert.equal(h.calls.length,1);assert.equal(h.get('citation-review').hidden,false);
const review=await loadMenu(h,run);assert.equal(h.calls[1].path,'/api/runs/research/citation-options?draft_hash=version-one');
assert.equal(h.calls[1].options.method,undefined);assert.equal(review.controls.length,3);
assert.equal(review.controls[0].value,'q-a24');assert.equal(h.desk.hasCitationChanges(),false);
assert.equal(h.get('citation-options').children[0].children[4].textContent,'Current earlier public quotation.');
assert.deepEqual(JSON.parse(JSON.stringify(h.desk.citationEdits(run.draft.body))),{body:run.draft.body});
""")


def test_save_updates_only_changed_claim_source_suffix_and_keeps_all_other_body_content():
    browser_check(r"""
const h=setup(),run=citationRun(h);await openCitationRun(h,run);const review=await loadMenu(h,run);
review.controls[0].value='new-a24';review.controls[0].onchange();review.controls[1].value='new-a25';review.controls[1].onchange();
assert.match(h.get('citation-options').children[0].children[4].textContent,/Second sentence stays visible/);
h.get('editor').value=run.draft.body.replace('Earlier selected wording.','Precise corrected wording.');
const saving=h.desk.decide('edit'),body=JSON.parse(h.calls[2].options.body);
assert.deepEqual(body.edits.citation_selections,{'risk-1':['new-a24','new-a25']});
assert.equal(body.edits.body,run.draft.body.replace('Earlier selected wording. [a24] [a25]','Precise corrected wording. [changed-a24] [changed-a25]'));
assert.equal(body.payload_hash,'version-one');assert.equal(body.kind,'note');assert.equal(body.action,'edit');
assert.equal(review.controls[0].disabled,true);h.calls[2].fail('Fictional validation response');await saving;
assert.equal(review.controls[0].disabled,false);
""")


def test_evidence_only_changes_must_be_saved_before_approval_and_returning_to_current_is_clean():
    browser_check(r"""
const h=setup(),run=citationRun(h);await openCitationRun(h,run);const review=await loadMenu(h,run);
review.controls[0].value='new-a24';review.controls[0].onchange();await h.desk.decide('approve');
assert.equal(h.calls.length,2);assert.match(h.get('message').textContent,/Save your edits first/);
review.controls[0].value='q-a24';review.controls[0].onchange();assert.equal(h.desk.hasCitationChanges(),false);
assert.deepEqual(JSON.parse(JSON.stringify(h.desk.citationEdits(run.draft.body))),{body:run.draft.body});
""")


@pytest.mark.parametrize("obsolete_response", ["success", "failure"])
def test_stale_menu_after_switch_cannot_render_choices_or_old_error(obsolete_response):
    browser_check(r"""
const h=setup(),old=citationRun(h,'old');await openCitationRun(h,old);const loading=h.desk.loadCitationOptions();
const next=citationRun(h,'next','next-version');await openCitationRun(h,next);
""" + ("h.calls[1].resolve(citationMenu(old));" if obsolete_response == "success" else "h.calls[1].fail('Obsolete menu error');") + r"""
await loading;assert.equal(h.desk.state.run.id,'next');assert.equal(h.desk.state.citationReview,null);
assert.equal(h.get('citation-options').children.length,0);assert.equal(h.get('citation-options-status').textContent,'');assert.equal(h.get('message').textContent,'');
""")


def test_stale_menu_for_same_run_old_hash_is_ignored_after_new_note_version():
    browser_check(r"""
const h=setup(),run=citationRun(h);await openCitationRun(h,run);const loading=h.desk.loadCitationOptions();
const refreshed=h.desk.refresh(run.id),next=citationRun(h,run.id,'version-two');h.calls[2].resolve(next);await refreshed;
h.calls[1].resolve(citationMenu(run));await loading;
assert.equal(h.desk.state.citationReview,null);assert.equal(h.get('citation-options').children.length,0);
assert.match(h.get('fingerprint').textContent,/version-two/);
""")


def test_identical_poll_keeps_unsaved_evidence_choices_and_quote_dom():
    browser_check(r"""
const h=setup(),run=citationRun(h);await openCitationRun(h,run);const review=await loadMenu(h,run),section=h.get('citation-options').firstChild;
review.controls[0].value='new-a24';review.controls[0].onchange();h.get('editor').value='Unsaved analyst wording';
const poll=h.desk.refresh(run.id);h.calls[2].resolve(JSON.parse(JSON.stringify(run)));await poll;
assert.equal(h.desk.state.citationReview,review);assert.equal(h.get('citation-options').firstChild,section);
assert.equal(review.controls[0].value,'new-a24');assert.equal(h.get('editor').value,'Unsaved analyst wording');
""")


def test_current_quote_outside_menu_is_preserved_until_every_changed_claim_slot_is_selected():
    browser_check(r"""
const h=setup(),run=citationRun(h),menu=citationMenu(run);menu.claims[0].slots[0].current.quote_id=null;menu.claims[0].slots[0].options.shift();
await openCitationRun(h,run);const review=await loadMenu(h,run,menu);assert.equal(review.controls[0].value,'');assert.equal(h.desk.hasCitationChanges(),false);
assert.equal(h.get('citation-options').children[0].children[4].textContent,'Current earlier public quotation.');
review.controls[1].value='new-a25';review.controls[1].onchange();await h.desk.decide('edit');
assert.equal(h.calls.length,2);assert.match(h.get('message').textContent,/every evidence slot/);
review.controls[0].value='new-a24';review.controls[0].onchange();const edits=h.desk.citationEdits(run.draft.body);
assert.deepEqual(JSON.parse(JSON.stringify(edits.citation_selections)),{'risk-1':['new-a24','new-a25']});
""")


@pytest.mark.parametrize("invalid", ["hash", "year", "source", "duplicate_claim"])
def test_mismatched_or_out_of_scope_options_fail_closed(invalid):
    mutation = {
        "hash": "menu.draft_hash='stale-version';",
        "year": "menu.claims[0].slots[0].options[1].year=2025;",
        "source": "menu.claims[0].slots[0].current.source_id='other-source';",
        "duplicate_claim": "menu.claims[1].claim_id='risk-1';",
    }[invalid]
    browser_check(r"""
const h=setup(),run=citationRun(h),menu=citationMenu(run);await openCitationRun(h,run);
""" + mutation + r"""
await loadMenu(h,run,menu);assert.equal(h.desk.state.citationReview,null);assert.equal(h.get('citation-options').children.length,0);
assert.match(h.get('citation-options-status').textContent,/changed|match/);assert.equal(h.desk.hasCitationChanges(),false);
""")


def test_body_only_edit_keeps_legacy_payload_without_citation_selections():
    browser_check(r"""
const h=setup(),run=citationRun(h);await openCitationRun(h,run);h.get('editor').value=run.draft.body.replace('Earlier selected wording.','A more careful observation.');
const saving=h.desk.decide('edit'),body=JSON.parse(h.calls[1].options.body);
assert.deepEqual(body.edits,{body:h.get('editor').value});h.calls[1].fail('Fictional validation response');await saving;
""")
