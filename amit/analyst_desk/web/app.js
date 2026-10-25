'use strict';
const $ = id => document.getElementById(id);
const state = {run:null,selectedRunId:null,selectionVersion:0,refreshVersion:0,renderedVersion:null,renderedSnapshot:null,loading:false,deciding:false,creating:false,runMessage:false,reviewKey:null,citationReview:null,timer:null,connected:false,config:null};
const element = (tag,text) => {const value=document.createElement(tag);if(text!==undefined)value.textContent=String(text);return value;};
function message(text){$('message').textContent=text;}
function runErrorMessage(error,validation){
 const text=String(error||'');
 if(text.includes('provider_http_429'))return 'The AI provider rate-limited this request (HTTP 429). This run has stopped; it will not retry automatically. Wait before starting a new live request, or explicitly choose Offline. Any reserved model budget remains visible below. Diagnostic: '+text;
 if(validation?.code==='duplicate_source_citation')return 'The AI output selected multiple quotations from the same source record as separate evidence. The citation check stopped this run. The revised request format requires a separate quotation for each compared year. Resuming is explicit and may use the remaining approved model budget. Diagnostic: duplicate_source_citation.';
 return text;
}
function modelRouteDescription(config){
 const models=config?.model_routes?.producer?.models;
 return Array.isArray(models)&&models.length>1?`${models[0]} produces; backup: ${models.slice(1).join(', ')}. ${config.models.critic} reviews independently.`:`${config?.models?.producer} produces; ${config?.models?.critic} reviews.`;
}
function completedModels(usage){
 return [...new Set((usage?.calls||[]).map(call=>call.returned_model||call.model).filter(value=>typeof value==='string'&&value.length<=180))];
}
function sourceCatalogue(config){
 const companies=config?.companies,coverage=config?.company_years;
 if(!Array.isArray(companies)||!companies.length||!coverage||typeof coverage!=='object')throw new Error('The source catalogue is unavailable.');
 const seen=new Set();
 return companies.map(company=>{
  const ticker=company?.ticker,years=coverage[ticker];
  if(typeof ticker!=='string'||seen.has(ticker)||typeof company.sector!=='string'||!company.sector.trim()||!Array.isArray(years)||!years.length||years.some(year=>!Number.isInteger(year))||years.join(',')!==[...new Set(years)].sort((a,b)=>a-b).join(','))throw new Error('The source catalogue contains invalid or missing company coverage.');
  seen.add(ticker);return {...company,years:[...years]};
 });
}
function researchScope(config,tickers,years,mode){
 const catalogue=sourceCatalogue(config),known=new Map(catalogue.map(company=>[company.ticker,company]));
 if(!Array.isArray(tickers)||!tickers.length||tickers.length>4||new Set(tickers).size!==tickers.length||tickers.some(ticker=>!known.has(ticker)))throw new Error('Choose between one and four covered companies.');
 if(!Array.isArray(years)||!years.length||years.length>3||years.some(year=>!Number.isInteger(year))||years.join(',')!==[...new Set(years)].sort((a,b)=>a-b).join(',')||tickers.some(ticker=>years.some(year=>!known.get(ticker).years.includes(year))))throw new Error('Choose up to three fiscal years covered by every selected company.');
 if(mode==='live'&&tickers.length*(years.length-1)>4)throw new Error('Live AI supports up to four adjacent-year risk comparisons. Choose fewer companies or fiscal years; your selection has been kept.');
 return {tickers:[...tickers],years:[...years]};
}
function selectedValues(id){return Array.from($(id).selectedOptions,option=>option.value);}
function updateScope(){
 try{if($('development-mode').checked&&!$('development-case').value)throw new Error('Choose a registered public development case.');if(state.config?.retrieval_details?.ready===false)throw new Error('The search index is unavailable or needs preparation. Research is paused until it is ready.');const scope=researchScope(state.config,selectedValues('companies'),selectedValues('years').map(Number),$('mode').value);$('request-scope').textContent=`Selected: ${scope.tickers.join(' / ')} · fiscal ${scope.years.join(', ')}`;$('start').disabled=!state.connected||state.creating;}
 catch(error){$('request-scope').textContent=error.message;$('start').disabled=true;}
}
function renderScopeOptions(config){
 const catalogue=sourceCatalogue(config),sectors=[...new Set(catalogue.map(company=>company.sector))].sort();
 $('companies').replaceChildren();
 sectors.forEach(sector=>{const group=element('optgroup');group.label=sector;
  catalogue.filter(company=>company.sector===sector).forEach(company=>{const option=element('option',`${company.ticker} · ${company.company||company.name||company.ticker}`);option.value=company.ticker;option.selected=['MSFT','AAPL'].includes(company.ticker);group.append(option);});$('companies').append(group);
 });
 const years=[...new Set(catalogue.flatMap(company=>company.years))].sort((a,b)=>a-b);$('years').replaceChildren();
 years.forEach(year=>{const option=element('option',year);option.value=String(year);option.selected=true;$('years').append(option);});
 $('companies').disabled=false;$('years').disabled=false;
 $('catalogue-summary').textContent=`${catalogue.length} covered companies · ${sectors.join(' / ')} · actual SEC filings · fiscal ${years.join(', ')}${config.retrieval==='hybrid_rerank'&&config.retrieval_details?.ready?' · hybrid search with local AI reranking':''}`;
}
function modeDescription(){
 const live=$('mode').value==='live',budget=state.config?.live_budget;
 $('mode-notice').textContent=live?'Live AI pilot: models plan, select queries and draft cited interpretations. A separate model reviews support; its judgment is not ground truth. Figures stay code-checked and publication needs your approval.':'Offline workflow: no model calls or model charges. Code checks figures; risk interpretation needs your review.';
 $('mode-budget').textContent=live?`Approved model budget remaining: $${budget?.remaining_authorization_usd||'0'} · up to 12 model calls and 250,000 tokens per request. ${modelRouteDescription(state.config)}`:(state.config?.live_enabled?'Live AI is available within its approved budget when selected.':'Live AI is disabled until its gateway, provider credential and spending authorization are ready. Offline requests remain explicit.');
 if(state.connected)updateScope();
}
async function api(path,options={}){
 const headers={'Content-Type':'application/json','X-Analyst-Token':sessionStorage.getItem('analyst-token')||''};
 const response=await fetch(path,{...options,headers});const data=await response.json();
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;
}
async function connect(){
 try{sessionStorage.setItem('analyst-token',$('token').value.trim());const config=await api('/api/config');
  if(config.data_source!=='sec_edgar')throw new Error('This desk requires the actual SEC source snapshot.');
  state.config=config;const live=$('mode').querySelector('option[value="live"]');live.disabled=!config.live_enabled;$('mode').value=config.live_enabled?'live':'offline';modeDescription();
  renderScopeOptions(config);state.connected=true;updateScope();$('connection').textContent=`Connected · real SEC snapshot · HTTP MCP · live AI ${config.live_enabled?'available':'disabled'}`;
  await window.AnalystMemory.load(config);await window.AnalystLessons.load();await loadRuns();await loadNotes();const requested=new URLSearchParams(location.search).get('run');if(requested)await selectRun(requested);
 }catch(error){state.connected=false;$('start').disabled=true;$('connection').textContent='Not connected';message(error.message);}
}
function runLabel(run){return `${run.request?.tickers?.join(' / ')||run.id} · ${run.mode||run.request?.mode||'offline'} · ${run.status} · ${run.id.slice(0,8)}`;}
async function loadRuns(){
 const runs=await api('/api/runs');$('runs').replaceChildren(element('option','Select a saved run'));$('runs').firstChild.value='';
 runs.forEach(run=>{const option=element('option',runLabel(state.run?.id===run.id?state.run:run));option.value=run.id;$('runs').append(option);});
 if(state.selectedRunId)$('runs').value=state.selectedRunId;
}
function selectedRun(id,version){return state.selectedRunId===id&&state.selectionVersion===version;}
function canResume(run){return run?.status==='error'&&run.continuation?.available===true&&run.continuation.failure_kind==='content_validation'&&typeof run.continuation.plan_hash==='string'&&/^[a-f0-9]{64}$/.test(run.continuation.plan_hash);}
function citationReviewKey(run){return run?.status==='awaiting_note'&&run.pending?.kind==='note'&&(run.mode||run.request?.mode)==='live'?`${run.id}:note:${run.pending.payload_hash}`:null;}
function clearCitationReview(){state.citationReview=null;$('citation-options').replaceChildren();$('citation-options-status').textContent='';}
function reviewControls(){
 const run=state.run,pending=run?.status.startsWith('awaiting_')?run.pending:null;
 const blocked=state.loading||state.deciding||run?.id!==state.selectedRunId,unavailable=blocked||!pending;
 ['approve','edit','reject'].forEach(id=>$(id).disabled=unavailable);$('editor').disabled=unavailable;
 $('resume-research').disabled=blocked||!canResume(run);
 $('load-citation-options').disabled=blocked||!citationReviewKey(run)||Boolean(state.citationReview?.loading);
 (state.citationReview?.controls||[]).forEach(control=>control.disabled=unavailable);
 if(!unavailable)$('approve').disabled=pending.kind==='note'&&(!run.critic?.passed||run.request?.learning_split==='development');
}
async function selectRun(id){
 clearTimeout(state.timer);state.timer=null;state.selectionVersion++;
 clearCitationReview();
 if(state.selectedRunId!==id){state.run=null;state.reviewKey=null;}
 state.selectedRunId=id||null;$('runs').value=id||'';state.loading=Boolean(id);state.runMessage=Boolean(id);message(id?'Loading selected research…':'');
 ['current','review','continuation','figures','risk-panel','reasoning-panel','run-memory','run-lessons','reflect-development','evidence-panel'].forEach(id=>$(id).hidden=true);
 reviewControls();if(id)await refresh(id,state.selectionVersion);
}
async function refresh(id,version=state.selectionVersion){
 if(!selectedRun(id,version))return;
 clearTimeout(state.timer);state.timer=null;const request=++state.refreshVersion;
 try{const run=await api(`/api/runs/${encodeURIComponent(id)}`);
  if(!selectedRun(id,version)||request!==state.refreshVersion)return;
  if(run.id!==id)throw new Error('The server returned a different research run. Select your run again.');
  state.loading=false;render(run);
  if(!['published','rejected','error'].includes(run.status))state.timer=setTimeout(()=>refresh(id,version),run.status.startsWith('awaiting_')?5000:1200);
  else{await loadRuns();await loadNotes();}
 }catch(error){if(selectedRun(id,version)&&request===state.refreshVersion){message(error.message);state.runMessage=true;}}
}
function render(run){
 const snapshot=JSON.stringify(run),option=Array.from($('runs').options).find(option=>option.value===run.id);
 if(option)option.textContent=runLabel(run);
 state.run=run;
 if(state.renderedVersion===state.selectionVersion&&state.renderedSnapshot===snapshot){
  if(!run.error&&state.runMessage){message('');state.runMessage=false;}
  reviewControls();return;
 }
 window.AnalystMemory.renderRun(run);
 window.AnalystLessons.renderRun(run);
 state.run=run;const live=(run.mode||run.request?.mode||'offline')==='live';$('current').hidden=false;$('status').textContent=`${live?'Live AI':'Offline'} · ${run.status.replaceAll('_',' ')} · run ${run.id}`;
 const rawCost=run.usage?.cost_usd,unknown=rawCost===null||rawCost===undefined||run.usage?.accounting_status==='unknown_after_failure',cost=unknown?NaN:Number(rawCost),held=run.usage?.held_usd;
 $('usage').textContent=`${run.usage?.tool_calls||0} tool calls · ${run.usage?.model_calls||0} recorded model calls · ${run.usage?.tokens||0} ${run.usage?.accounting_status==='provider_reported_with_holds'?'reported/reserved tokens':'tokens'} · reported model cost ${Number.isFinite(cost)?'$'+cost.toFixed(6):'unknown'}${held!==null&&held!==undefined?' · reserved model budget $'+held:''}${unknown?' · accounting unavailable; a failed request may still have incurred a charge':''}`;
 const actualModels=completedModels(run.usage);if(actualModels.length)$('usage').textContent+=` · completed responses: ${actualModels.join(', ')}`;
 $('events').replaceChildren();(run.events||[]).forEach(event=>$('events').append(element('li',`${event.agent}: ${event.message}`)));
 $('checks').textContent=run.critic?`Financial values checked: ${run.critic.verified_numbers} / ${run.critic.total_numbers}\nOverall checks: ${run.critic.passed?'passed':'blocked'}\nNarrative model review: ${run.critic.semantic_review==='not_run_offline'?'not run in offline mode':run.critic.semantic_review==='model_assisted_not_gold'?'completed · fallible model judgment':run.critic.semantic_review||'pending'}${run.critic.issues?.length?'\nIssues:\n'+run.critic.issues.map(value=>'• '+value).join('\n'):''}`:'Checks have not run.';
 if(run.error)message(runErrorMessage(run.error,run.validation_error));else if(state.runMessage)message('');state.runMessage=Boolean(run.error);
 const resumable=canResume(run);$('continuation').hidden=!resumable;$('continuation-plan').textContent=resumable?`Original approved plan: ${run.continuation.plan_hash}`:'';
 const pending=run.status.startsWith('awaiting_')?run.pending:null;$('review').hidden=!pending;
 if(pending){const key=`${run.id}:${pending.kind}:${pending.payload_hash}`;
  if(key!==state.reviewKey){state.reviewKey=key;const plan=pending.kind==='plan';
   clearCitationReview();
   $('review-title').textContent=plan?'Review the research plan':'Review this exact note';$('editor-label').textContent=plan?'Outline · one task per line':'Note body · edits trigger fresh checks';
   $('editor').value=plan?pending.payload.outline.join('\n'):pending.payload.body;
   $('scope').textContent=plan?`${pending.payload.tickers.join(' / ')} · fiscal ${pending.payload.years.join(', ')} · ${pending.payload.caveats.join(' ')}`:'Inspect the financial sources, narrative citations, model review and limitations before deciding.';
   $('edit-policy').textContent=!plan&&live?'Edit the wording of existing claim bullets. Keep the table, headings and limitations unchanged. To change quotations, review the evidence choices below. Saving wording or evidence changes invalidates the previous review and requires fresh checks.':'';
   $('fingerprint').textContent=`Exact version: ${pending.payload_hash}`;$('approve').textContent=plan?'Approve plan and continue':run.request?.learning_split==='development'?'Development review only · publication blocked':'Approve and publish this exact note';
  }
 }
 $('citation-review').hidden=!citationReviewKey(run);
 reviewControls();
 const rows=run.draft?.metrics||run.metrics||[];$('figures').hidden=!rows.length;$('rows').replaceChildren();
 rows.forEach(row=>{const tr=element('tr');[`${row.ticker} / ${row.year}`,`${row.period_start} to ${row.period_end}`,row.revenue,row.operating_income,`${row.margin_pct}%`].forEach(text=>tr.append(element('td',text)));
  const refs=element('td');row.fact_ids.forEach((id,index)=>{const button=element('button',index?'Operating income':'Revenue');button.className='secondary';button.onclick=()=>showEvidence(id);refs.append(button);});tr.append(refs);$('rows').append(tr);});
 const risks=run.risks||[];$('risk-panel').hidden=!risks.length;$('risks').replaceChildren();
 risks.forEach(risk=>{const detail=element('details');detail.append(element('summary',`${risk.ticker}: ${risk.before_year} to ${risk.after_year} · ${risk.text_changed?'text differs':'unchanged text'}`),element('p',risk.interpretation));
  risk.source_ids.forEach(id=>{const button=element('button',id);button.className='secondary';button.onclick=()=>showEvidence(id);detail.append(button);});$('risks').append(detail);});
 const claims=run.draft?.narrative_claims||[];$('reasoning-panel').hidden=!claims.length;$('claims').replaceChildren();
 claims.forEach(claim=>{const detail=element('details');detail.append(element('summary',claim.text),element('p',`Model confidence: ${claim.confidence}. This label is not a correctness score.`));
  claim.citations.forEach(citation=>{detail.append(element('blockquote',citation.quote));const button=element('button',citation.source_id);button.className='secondary';button.onclick=()=>showEvidence(citation.source_id);detail.append(button);});$('claims').append(detail);});
 state.renderedVersion=state.selectionVersion;state.renderedSnapshot=snapshot;
}
function currentCitationReview(){
 const review=state.citationReview;
 return review&&selectedRun(review.runId,review.version)&&review.key===citationReviewKey(state.run)?review:null;
}
function hasCitationChanges(){
 const review=currentCitationReview();return Boolean(review?.claims.some(claim=>claim.slots.some((slot,index)=>review.selections[claim.claim_id][index]!== (slot.current.quote_id||''))));
}
function citationEdits(body){
 const review=currentCitationReview();if(!review||!hasCitationChanges())return {body};
 const draft=state.run.pending.payload,ordered=[...draft.live_sections.risk_ids,...draft.live_sections.writer_ids];
 const lines=body.split('\n'),indices=[];lines.forEach((line,index)=>{if(line.startsWith('- '))indices.push(index);});
 if(indices.length!==ordered.length)throw new Error('Keep the existing claim bullets when changing evidence.');
 const selections={};
 review.claims.forEach(claim=>{
  const selected=review.selections[claim.claim_id];
  if(!claim.slots.some((slot,index)=>selected[index]!== (slot.current.quote_id||'')))return;
  const options=claim.slots.map((slot,index)=>slot.options.find(option=>option.quote_id===selected[index]));
  if(options.some(option=>!option))throw new Error('Choose a listed quotation for every evidence slot in the changed claim. You can leave the whole claim unchanged.');
  const claimIndex=ordered.indexOf(claim.claim_id),lineIndex=indices[claimIndex];
  if(claimIndex<0)throw new Error('The note version changed. Load its evidence choices again.');
  const oldSuffix=' '+claim.slots.map(slot=>`[${slot.current.source_id}]`).join(' ');
  if(!lines[lineIndex].endsWith(oldSuffix))throw new Error('Keep the existing evidence references in the editor; your evidence choices will update them when saved.');
  lines[lineIndex]=lines[lineIndex].slice(0,-oldSuffix.length)+' '+options.map(option=>`[${option.source_id}]`).join(' ');
  selections[claim.claim_id]=[...selected];
 });
 return {body:lines.join('\n'),citation_selections:selections};
}
function renderCitationOptions(review){
 $('citation-options').replaceChildren();review.controls=[];
 review.claims.forEach((claim,claimIndex)=>{
  const section=element('div');section.className='citation-claim';section.append(element('h3',`Evidence for this edit · claim ${claimIndex+1}`),element('p',claim.text));
  claim.slots.forEach((slot,slotIndex)=>{
   const id=`citation-choice-${claimIndex}-${slotIndex}`,label=element('label',`${slot.ticker} · fiscal ${slot.year} · quotation ${slotIndex+1}`),select=element('select'),preview=element('blockquote');label.htmlFor=id;select.id=id;
   if(!slot.current.quote_id){const preserve=element('option','Keep current quotation · choose a listed quotation to change this claim');preserve.value='';select.append(preserve);}
   const group=element('optgroup');group.label=`${slot.ticker} · fiscal ${slot.year}`;
   slot.options.forEach(option=>{const item=element('option',option.quote.replaceAll('\n',' ').slice(0,150));item.value=option.quote_id;group.append(item);});select.append(group);select.value=review.selections[claim.claim_id][slotIndex];
   const show=()=>{const selected=slot.options.find(option=>option.quote_id===select.value);preview.textContent=(selected||slot.current).quote;};show();
   select.onchange=()=>{if(currentCitationReview()!==review||state.loading||state.deciding)return;review.selections[claim.claim_id][slotIndex]=select.value;show();$('citation-options-status').textContent=hasCitationChanges()?'Evidence changes are unsaved. Saving will update the references and require fresh checks.':'Current quotations retained.';};
   review.controls.push(select);section.append(label,select,preview);
  });$('citation-options').append(section);
 });
}
async function loadCitationOptions(){
 const run=state.run,key=citationReviewKey(run),version=state.selectionVersion;
 if(!key||state.loading||state.deciding||run.id!==state.selectedRunId||state.citationReview?.loading)return;
 if(hasCitationChanges())return message('Save or restore your evidence choices before loading them again.');
 const review={key,runId:run.id,version,loading:true,claims:[],selections:{},controls:[]};state.citationReview=review;
 $('citation-options-status').textContent='Loading evidence choices for this exact note…';reviewControls();
 try{
  const options=await api(`/api/runs/${encodeURIComponent(run.id)}/citation-options?draft_hash=${encodeURIComponent(run.pending.payload_hash)}`);
  if(currentCitationReview()!==review)return;
  if(options.draft_hash!==run.pending.payload_hash||!Array.isArray(options.claims))throw new Error('The note version changed. Load its evidence choices again.');
  const draft=run.pending.payload,ordered=[...draft.live_sections.risk_ids,...draft.live_sections.writer_ids],known=new Map(draft.narrative_claims.map(claim=>[claim.claim_id,claim]));
  if(options.claims.length!==ordered.length||new Set(options.claims.map(claim=>claim.claim_id)).size!==ordered.length)throw new Error('Evidence choices do not match this note.');
  const byId=new Map(options.claims.map(claim=>[claim.claim_id,claim]));
  review.claims=ordered.map(identifier=>{
   const claim=byId.get(identifier),original=known.get(identifier);
   if(!claim||!original||claim.text!==original.text||!Array.isArray(claim.slots)||claim.slots.length!==original.citations.length)throw new Error('Evidence choices do not match this note.');
   claim.slots.forEach((slot,index)=>{
    const citation=original.citations[index];
    if(!slot.current||slot.current.source_id!==citation.source_id||slot.current.quote!==citation.quote||!Array.isArray(slot.options)||slot.options.some(option=>typeof option.quote_id!=='string'||!option.quote_id||typeof option.quote!=='string'||typeof option.source_id!=='string'||option.ticker!==slot.ticker||option.year!==slot.year)||new Set(slot.options.map(option=>option.quote_id)).size!==slot.options.length)throw new Error('Evidence choices do not match their company and fiscal year.');
    if(slot.current.quote_id!==null&&!slot.options.some(option=>option.quote_id===slot.current.quote_id&&option.source_id===citation.source_id&&option.quote===citation.quote))throw new Error('The current quotation cannot be matched safely.');
   });
   review.selections[identifier]=claim.slots.map(slot=>slot.current.quote_id||'');return claim;
  });
  review.loading=false;renderCitationOptions(review);$('citation-options-status').textContent='Current quotations retained. Choose evidence only if this edit needs a different quotation.';
 }catch(error){if(currentCitationReview()===review){clearCitationReview();$('citation-options-status').textContent=error.message;}}
 finally{if(currentCitationReview()===review)review.loading=false;reviewControls();}
}
async function decide(action){
 const run=state.run,pending=run?.pending,version=state.selectionVersion;if(state.loading||state.deciding||run?.id!==state.selectedRunId||!pending||!run.status.startsWith('awaiting_'))return;
 const plan=pending.kind==='plan',original=plan?pending.payload.outline.join('\n'):pending.payload.body,current=$('editor').value;
 if(action==='approve'&&(current!==original||hasCitationChanges()))return message('Save your edits first, then review the new version before approving.');
 let edits=null;
 try{if(action==='edit')edits=plan?{outline:current.split('\n').map(text=>text.trim()).filter(Boolean)}:citationEdits(current);}
 catch(error){return message(error.message);}
 state.deciding=true;reviewControls();
 try{message('');
  await api(`/api/runs/${encodeURIComponent(run.id)}/decision`,{method:'POST',body:JSON.stringify({kind:pending.kind,action,payload_hash:pending.payload_hash,edits})});
  if(selectedRun(run.id,version)){state.reviewKey=null;await refresh(run.id,version);}
 }catch(error){if(selectedRun(run.id,version))message(error.message);}finally{state.deciding=false;reviewControls();}
}
async function resumeResearch(){
 const run=state.run,version=state.selectionVersion;
 if(state.loading||state.deciding||run?.id!==state.selectedRunId||!canResume(run))return;
 const planHash=run.continuation.plan_hash;state.deciding=true;reviewControls();
 try{message('');
  await api(`/api/runs/${encodeURIComponent(run.id)}/continue`,{method:'POST',body:JSON.stringify({plan_hash:planHash})});
  if(selectedRun(run.id,version)){state.loading=true;await refresh(run.id,version);}
 }catch(error){if(selectedRun(run.id,version))message(error.message);}finally{state.deciding=false;reviewControls();}
}
async function showEvidence(id){try{$('evidence').textContent=JSON.stringify(await api(`/api/evidence/${encodeURIComponent(id)}`),null,2);$('evidence-panel').hidden=false;$('evidence-panel').scrollIntoView({behavior:'smooth'});}catch(error){message(error.message);}}
async function loadNotes(){const notes=await api('/api/notes');$('notes').replaceChildren();if(!notes.length)$('notes').append(element('p','No approved notes yet.'));
 notes.forEach(note=>{const detail=element('details');detail.append(element('summary',note.title||note.id),element('p',`${note.model_mode==='live'?'Live AI':'Offline'} · approved version: ${note.payload_hash||note.digest||''}`),element('pre',note.body||JSON.stringify(note)));window.AnalystMemory.renderNote(note,detail);$('notes').append(detail);});}
function initialize(){
window.AnalystLessons.initialize({api,notify:message,applyCase:value=>{if(value){Array.from($('companies').options).forEach(option=>option.selected=value.tickers.includes(option.value));Array.from($('years').options).forEach(option=>option.selected=value.years.includes(Number(option.value)));$('question').value=value.question;}const locked=$('development-mode').checked;$('companies').disabled=locked;$('years').disabled=locked;$('question').readOnly=locked;updateScope();}});
window.AnalystMemory.initialize({api,getSelection:()=>({question:$('question').value,...researchScope(state.config,selectedValues('companies'),selectedValues('years').map(Number),'offline')}),applyDefaults:values=>{if(values.companies)Array.from($('companies').options).forEach(option=>option.selected=values.companies.includes(option.value));if(values.years)Array.from($('years').options).forEach(option=>option.selected=values.years.includes(Number(option.value)));updateScope();},showFact:showEvidence,showEvidence:text=>{$('evidence').textContent=text;$('evidence-panel').hidden=false;$('evidence-panel').scrollIntoView({behavior:'smooth'});}});
$('connect').onclick=connect;$('runs').onchange=()=>selectRun($('runs').value);
$('mode').onchange=modeDescription;
$('companies').onchange=updateScope;$('years').onchange=updateScope;
$('research-form').onsubmit=async event=>{event.preventDefault();if(state.creating)return;state.creating=true;try{$('start').disabled=true;const mode=$('mode').value,learning=window.AnalystLessons.requestOptions(),scope=researchScope(state.config,learning.tickers||selectedValues('companies'),learning.years||selectedValues('years').map(Number),mode);const run=await api('/api/runs',{method:'POST',body:JSON.stringify({question:$('question').value,...scope,strategy:'multi',mode,memory_enabled:$('use-memory').checked,max_tool_calls:60,max_tokens:mode==='live'?250000:100000,max_model_calls:12,...learning})});await loadRuns();await selectRun(run.id);}catch(error){message(error.message);}finally{state.creating=false;updateScope();}};
$('approve').onclick=()=>decide('approve');$('edit').onclick=()=>decide('edit');$('reject').onclick=()=>decide('reject');$('close-evidence').onclick=()=>{$('evidence-panel').hidden=true;};
$('resume-research').onclick=resumeResearch;
$('load-citation-options').onclick=loadCitationOptions;
$('token').value=sessionStorage.getItem('analyst-token')||'';if($('token').value)connect();
}
if(typeof module!=='undefined'&&module.exports)module.exports={sourceCatalogue,researchScope,runErrorMessage,modelRouteDescription,completedModels};
if(typeof document!=='undefined')initialize();
