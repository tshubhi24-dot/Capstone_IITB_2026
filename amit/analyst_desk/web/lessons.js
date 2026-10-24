/* Explicit lesson review; no client action accepts or freezes a lesson automatically. */
(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 const node=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
 const state={api:null,notify:null,applyCase:null,bank:null,lessons:[],playbooks:[],actions:{},cases:[],run:null};
 function requestOptions(){
  const enabled=$('use-lessons').checked,playbook=$('playbook').value;
  if(enabled&&!playbook)throw new Error('Choose a frozen reviewed playbook first.');
  const options={lessons_enabled:enabled,playbook_id:enabled?playbook:null,learning_split:'production',development_case_id:null};
  if($('development-mode').checked){const c=state.cases.find(c=>c.case_id===$('development-case').value&&c.available);if(!c)throw new Error('Choose a covered public development case.');
   Object.assign(options,{question:c.question,tickers:c.tickers,years:c.years,memory_enabled:false,learning_split:'development',development_case_id:c.case_id});}
  return options;
 }
 function makeButton(label,action){const b=node('button',label);b.type='button';b.className='secondary';b.onclick=async()=>{b.disabled=true;try{await action();}catch(e){state.notify(e.message);}finally{b.disabled=false;}};return b;}
 function field(label,value){const wrap=node('label',label),input=node('textarea');input.rows=2;input.maxLength=600;input.value=value||'';wrap.append(input);return {wrap,input};}
 function reasonValue(input){const value=input.value.trim();if(value.length<8)throw new Error('Write a review reason of at least eight characters.');return value;}
 async function mutate(path,body){const result=await state.api(path,{method:'POST',body:JSON.stringify({...body,expected_revision:state.bank.revision})});await load();return result;}
 function renderLessons(){
  const target=$('lesson-list');target.replaceChildren();
  if(!state.lessons.length)target.append(node('p','No lesson proposals yet. Start a public development rehearsal, review its output, then reflect on an actual critic rejection or analyst edit.'));
  state.lessons.forEach(lesson=>{
   const detail=node('details');detail.append(node('summary',`${lesson.status} · ${lesson.action.replaceAll('_',' ')} · ${lesson.lesson_id.slice(0,8)}`));
   detail.append(node('p',`Applies to ${lesson.scope.tickers.join(' / ')} · fiscal ${lesson.scope.years.join(', ')} · ${lesson.scope.stages.join(', ')}`));
   detail.append(node('p',`Origin: development run ${lesson.origin.run_id.slice(0,8)} · event ${lesson.origin.event_id}. Exact proposal: ${lesson.proposal_hash}`));
   detail.append(node('p',`Reusable guidance: ${state.actions[lesson.action]}`));
   if(lesson.status==='pending'){
    const action=node('select');Object.entries(state.actions).forEach(([code,hint])=>{const o=node('option',hint);o.value=code;action.append(o);});action.value=lesson.action;const actionLabel=node('label','Proposed guidance');actionLabel.append(action);detail.append(actionLabel);
    const summary=field('Lesson explanation',lesson.summary),applies=field('When it applies',lesson.applicability),counter=field('Counterexamples and limits',lesson.counterexamples),reason=field('Your acceptance or rejection reason','');
    [summary,applies,counter,reason].forEach(v=>detail.append(v.wrap));
    const changed=()=>action.value!==lesson.action||summary.input.value!==lesson.summary||applies.input.value!==lesson.applicability||counter.input.value!==lesson.counterexamples;
    detail.append(makeButton('Save edited proposal for fresh review',async()=>{if(!changed())throw new Error('Change the proposal before saving a new version.');await mutate('/api/lessons',{run_id:lesson.origin.run_id,event_id:lesson.origin.event_id,action:action.value,scope:lesson.scope,summary:summary.input.value,applicability:applies.input.value,counterexamples:counter.input.value,supersedes:lesson.lesson_id});}));
    for(const decision of ['accept','reject'])detail.append(makeButton(decision==='accept'?'Accept this exact proposal':'Reject this exact proposal',async()=>{if(changed())throw new Error('Save your edited proposal, then review its new exact version before deciding.');await mutate(`/api/lessons/${encodeURIComponent(lesson.lesson_id)}/decision`,{proposal_hash:lesson.proposal_hash,decision,reason:reasonValue(reason.input)});}));
   }else{
    detail.append(node('p',lesson.summary),node('p',`Applicability: ${lesson.applicability}`),node('p',`Counterexamples: ${lesson.counterexamples}`));
    if(lesson.decision)detail.append(node('p',`Review reason: ${lesson.decision.reason}`));
    if(lesson.revocation)detail.append(node('p',`Revocation reason: ${lesson.revocation.reason}`));
    if(lesson.status==='accepted'){
     const label=node('label'),check=node('input');check.type='checkbox';check.value=lesson.lesson_id;check.className='freeze-lesson';label.append(check,document.createTextNode(' Include in the next frozen playbook'));detail.append(label);
     const reason=field('Reason to revoke this lesson','');detail.append(reason.wrap,makeButton('Revoke future use',()=>mutate(`/api/lessons/${encodeURIComponent(lesson.lesson_id)}/revoke`,{proposal_hash:lesson.proposal_hash,reason:reasonValue(reason.input)})));
    }
   }
   target.append(detail);
  });
  const books=$('playbook-list');books.replaceChildren();
  if(!state.playbooks.length)books.append(node('p','No frozen playbook. Acceptance alone does not change research behaviour.'));
  state.playbooks.forEach(book=>{const d=node('details');d.append(node('summary',`${book.id.slice(0,12)} · ${book.lesson_refs.length} reviewed lessons`),node('p',`Frozen playbook: ${book.id}`),node('p',`Source snapshot: ${book.source_fingerprint}`));book.lesson_refs.forEach(ref=>d.append(node('p',state.actions[ref.action])));books.append(d);});
 }
 function renderSelection(){const select=$('playbook'),selected=select.value;select.replaceChildren(node('option','Choose a frozen playbook'));select.firstChild.value='';state.playbooks.forEach(book=>{const o=node('option',`${book.id.slice(0,12)} · ${book.lesson_refs.length} lessons`);o.value=book.id;select.append(o);});if(state.playbooks.some(book=>book.id===selected))select.value=selected;select.disabled=!$('use-lessons').checked;}
 async function load(){
  const [value,development]=await Promise.all([state.api('/api/lessons'),state.api('/api/development/cases')]);
  Object.assign(state,{bank:value.bank,lessons:value.lessons,playbooks:value.playbooks,actions:value.actions,cases:development.cases});
  $('reviewed-lessons').hidden=false;renderLessons();renderSelection();
  const select=$('development-case'),selected=select.value;select.replaceChildren(node('option','Choose a public case'));select.firstChild.value='';state.cases.forEach(c=>{const o=node('option',`${c.case_id} · ${c.tickers.join(' / ')} · ${c.years.join(', ')}${c.available?'':' · outside current coverage'}`);o.value=c.case_id;o.disabled=!c.available;select.append(o);});select.value=selected;if($('development-mode').checked)state.applyCase(state.cases.find(c=>c.case_id===select.value));
 }
 function renderRun(run){
  state.run=run;const context=run.lesson_context||run.plan?.lesson_context;
  $('run-lessons').hidden=!context;
  if(context){$('run-lessons-description').textContent=context.enabled?`Reviewed lessons enabled · frozen playbook ${String(context.playbook_id||'').slice(0,12)}. Guidance is advisory; current SEC evidence and checks remain required.`:'Reviewed lessons are off for this research.';$('run-lesson-details').textContent=JSON.stringify(context,null,2);}
  const eligible=run.request?.learning_split==='development';$('reflect-development').hidden=!eligible;
  if(eligible){const select=$('reflection-event'),selected=select.value;select.replaceChildren(node('option','Choose an actual failure or edit'));select.firstChild.value='';(run.events||[]).filter(event=>(event.stage==='critic_reject'&&event.agent==='critic'&&event.details?.passed===false)||(event.stage==='note_edit'&&event.agent==='human')).forEach(event=>{const o=node('option',`${event.stage.replaceAll('_',' ')} · event ${event.id}`);o.value=String(event.id);select.append(o);});select.value=selected;$('reflection-live').disabled=(run.mode||run.request.mode)!=='live';if($('reflection-live').disabled)$('reflection-mode').value='rules';}
 }
 function initialize({api,notify,applyCase}){
  Object.assign(state,{api,notify,applyCase});
  $('use-lessons').onchange=()=>{$('playbook').disabled=!$('use-lessons').checked;};
  $('development-mode').onchange=()=>{$('development-controls').hidden=!$('development-mode').checked;if($('development-mode').checked){$('use-memory').checked=false;$('use-memory').disabled=true;}else{$('use-memory').disabled=false;}state.applyCase($('development-mode').checked?state.cases.find(c=>c.case_id===$('development-case').value):null);};
  $('development-case').onchange=()=>state.applyCase(state.cases.find(c=>c.case_id===$('development-case').value));
  $('freeze-playbook').onclick=async()=>{try{const ids=Array.from(document.querySelectorAll('.freeze-lesson:checked')).map(e=>e.value);if(!ids.length)throw new Error('Choose at least one accepted lesson to freeze.');await mutate('/api/playbooks',{lesson_ids:ids});state.notify('Playbook frozen. Select it explicitly when preparing new research.');}catch(e){state.notify(e.message);}};
  $('propose-reflection').onclick=async()=>{try{const eventId=Number($('reflection-event').value);if(!eventId)throw new Error('Choose an actual critic rejection or analyst edit.');$('propose-reflection').disabled=true;await mutate('/api/lessons/reflect',{run_id:state.run.id,event_id:eventId,mode:$('reflection-mode').value});state.notify('Lesson proposed for your review. It has not been accepted or added to a playbook.');}catch(e){state.notify(e.message);}finally{$('propose-reflection').disabled=false;}};
 }
 window.AnalystLessons={initialize,load,renderRun,requestOptions};
})();
