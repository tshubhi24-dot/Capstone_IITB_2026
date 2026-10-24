'use strict';
const $ = id => document.getElementById(id);
const state = {run:null,reviewKey:null,timer:null,connected:false};
const element = (tag,text) => {const value=document.createElement(tag);if(text!==undefined)value.textContent=String(text);return value;};
function message(text){$('message').textContent=text;}
async function api(path,options={}){
 const headers={'Content-Type':'application/json','X-Analyst-Token':sessionStorage.getItem('analyst-token')||''};
 const response=await fetch(path,{...options,headers});const data=await response.json();
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;
}
async function connect(){
 try{sessionStorage.setItem('analyst-token',$('token').value.trim());const config=await api('/api/config');
  if(config.mode!=='offline'||config.data_source!=='sec_edgar')throw new Error('This journey requires offline mode with actual SEC data.');
  state.connected=true;$('connection').textContent='Connected · real SEC snapshot · HTTP MCP · no model calls';$('start').disabled=false;
  await loadRuns();await loadNotes();const requested=new URLSearchParams(location.search).get('run');if(requested)await selectRun(requested);
 }catch(error){message(error.message);}
}
async function loadRuns(){
 const runs=await api('/api/runs');$('runs').replaceChildren(element('option','Select a saved run'));$('runs').firstChild.value='';
 runs.forEach(run=>{const option=element('option',`${run.request?.tickers?.join(' / ')||run.id} · ${run.status} · ${run.id.slice(0,8)}`);option.value=run.id;$('runs').append(option);});
 if(state.run)$('runs').value=state.run.id;
}
async function selectRun(id){clearTimeout(state.timer);state.reviewKey=null;await refresh(id);}
async function refresh(id){
 try{const run=await api(`/api/runs/${encodeURIComponent(id)}`);render(run);
  if(!['published','rejected','error'].includes(run.status))state.timer=setTimeout(()=>refresh(id),run.status.startsWith('awaiting_')?5000:1200);
  else{await loadRuns();await loadNotes();}
 }catch(error){message(error.message);}
}
function render(run){
 state.run=run;$('current').hidden=false;$('status').textContent=`${run.status.replaceAll('_',' ')} · run ${run.id}`;
 $('usage').textContent=`${run.usage?.tool_calls||0} tool calls · ${run.usage?.model_calls||0} model calls · model charges $0`;
 $('events').replaceChildren();(run.events||[]).forEach(event=>$('events').append(element('li',`${event.agent}: ${event.message}`)));
 $('checks').textContent=run.critic?JSON.stringify(run.critic,null,2):'Checks have not run.';
 if(run.error)message(run.error);
 const pending=run.status.startsWith('awaiting_')?run.pending:null;$('review').hidden=!pending;
 if(pending){const key=`${run.id}:${pending.kind}:${pending.payload_hash}`;
  if(key!==state.reviewKey){state.reviewKey=key;const plan=pending.kind==='plan';
   $('review-title').textContent=plan?'Review the research plan':'Review this exact note';$('editor-label').textContent=plan?'Outline · one task per line':'Note body · edits trigger fresh checks';
   $('editor').value=plan?pending.payload.outline.join('\n'):pending.payload.body;
   $('scope').textContent=plan?`${pending.payload.tickers.join(' / ')} · fiscal ${pending.payload.years.join(', ')} · ${pending.payload.caveats.join(' ')}`:'Code checks support the financial rows. Inspect the sources and risk interpretation before deciding.';
   $('fingerprint').textContent=`Exact version: ${pending.payload_hash}`;$('approve').textContent=plan?'Approve plan and continue':'Approve and publish this exact note';
  }
  $('approve').disabled=pending.kind==='note'&&!run.critic?.passed;
 }
 const rows=run.draft?.metrics||run.metrics||[];$('figures').hidden=!rows.length;$('rows').replaceChildren();
 rows.forEach(row=>{const tr=element('tr');[`${row.ticker} / ${row.year}`,`${row.period_start} to ${row.period_end}`,row.revenue,row.operating_income,`${row.margin_pct}%`].forEach(text=>tr.append(element('td',text)));
  const refs=element('td');row.fact_ids.forEach((id,index)=>{const button=element('button',index?'Operating income':'Revenue');button.className='secondary';button.onclick=()=>showEvidence(id);refs.append(button);});tr.append(refs);$('rows').append(tr);});
 const risks=run.risks||[];$('risk-panel').hidden=!risks.length;$('risks').replaceChildren();
 risks.forEach(risk=>{const detail=element('details');detail.append(element('summary',`${risk.ticker}: ${risk.before_year} to ${risk.after_year} · ${risk.text_changed?'text differs':'unchanged text'}`),element('p',risk.interpretation));
  risk.source_ids.forEach(id=>{const button=element('button',id);button.className='secondary';button.onclick=()=>showEvidence(id);detail.append(button);});$('risks').append(detail);});
}
async function decide(action){
 const run=state.run,pending=run?.pending;if(!pending||!run.status.startsWith('awaiting_'))return;
 const plan=pending.kind==='plan',original=plan?pending.payload.outline.join('\n'):pending.payload.body,current=$('editor').value;
 if(action==='approve'&&current!==original)return message('Save your edits first, then review the new version before approving.');
 const edits=action==='edit'?(plan?{outline:current.split('\n').map(text=>text.trim()).filter(Boolean)}:{body:current}):null;
 try{['approve','edit','reject'].forEach(id=>$(id).disabled=true);message('');
  await api(`/api/runs/${encodeURIComponent(run.id)}/decision`,{method:'POST',body:JSON.stringify({kind:pending.kind,action,payload_hash:pending.payload_hash,edits})});
  clearTimeout(state.timer);state.reviewKey=null;await refresh(run.id);
 }catch(error){message(error.message);}finally{['edit','reject'].forEach(id=>$(id).disabled=false);}
}
async function showEvidence(id){try{$('evidence').textContent=JSON.stringify(await api(`/api/evidence/${encodeURIComponent(id)}`),null,2);$('evidence-panel').hidden=false;$('evidence-panel').scrollIntoView({behavior:'smooth'});}catch(error){message(error.message);}}
async function loadNotes(){const notes=await api('/api/notes');$('notes').replaceChildren();if(!notes.length)$('notes').append(element('p','No approved notes yet.'));
 notes.forEach(note=>{const detail=element('details');detail.append(element('summary',note.title||note.id),element('p',`Approved version: ${note.payload_hash||note.digest||''}`),element('pre',note.body||JSON.stringify(note)));$('notes').append(detail);});}
$('connect').onclick=connect;$('runs').onchange=()=>{if($('runs').value)selectRun($('runs').value);};
$('research-form').onsubmit=async event=>{event.preventDefault();try{$('start').disabled=true;const run=await api('/api/runs',{method:'POST',body:JSON.stringify({question:$('question').value,tickers:['MSFT','AAPL'],years:[2023,2024,2025],strategy:'multi',max_tool_calls:60,max_tokens:100000,learning_split:'production'})});await loadRuns();await selectRun(run.id);}catch(error){message(error.message);}finally{$('start').disabled=!state.connected;}};
$('approve').onclick=()=>decide('approve');$('edit').onclick=()=>decide('edit');$('reject').onclick=()=>decide('reject');$('close-evidence').onclick=()=>{$('evidence-panel').hidden=true;};
$('token').value=sessionStorage.getItem('analyst-token')||'';if($('token').value)connect();
