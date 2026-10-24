'use strict';
// Private memory is displayed locally. Only the chosen research scope is submitted.
(function(root){
 const byId=id=>document.getElementById(id);
 const node=(tag,text)=>{const item=document.createElement(tag);if(text!==undefined)item.textContent=String(text);return item;};
 let client=null,profile=null,policy={revision:0,excluded_note_ids:[]};
 function preferenceDefaults(config,record){
  if(record?.status!=='active')return null;
  const values=record.values||{},companies=values.default_companies,years=values.default_years;
  const catalogue=new Set((config.companies||[]).map(item=>item.ticker));
  if(companies&&(!companies.length||companies.length>4||new Set(companies).size!==companies.length||companies.some(ticker=>!catalogue.has(ticker))))throw new Error('Saved company defaults need updating for this source catalogue.');
  if(years&&(!years.length||years.length>3||years.some(year=>!Number.isInteger(year))||years.join(',')!==[...new Set(years)].sort((a,b)=>a-b).join(',')||(companies||[...catalogue]).some(ticker=>years.some(year=>!config.company_years?.[ticker]?.includes(year)))))throw new Error('Saved fiscal-year defaults need updating for this source catalogue.');
  return {companies,years,report_style:values.report_style||'table_first',history_limit:values.history_limit??3};
 }
 function status(text){byId('memory-status').textContent=text;}
 async function showNote(ref){
  const value=await client.api('/api/notes/'+encodeURIComponent(ref.note_id));
  if(ref.payload_hash&&value.payload_hash!==ref.payload_hash)throw new Error('The referenced historical version changed.');
  client.showEvidence(value.body||'No note body is available.');
 }
 function showComparison(value){
  const panel=byId('memory-comparison');panel.replaceChildren(node('h3','Approved history compared with the current snapshot'));
  const citation=node('p','note:'+value.note_id+'@'+value.note_payload_hash);citation.className='fingerprint';panel.append(citation,node('p',value.archive_only?'The compared note uses an earlier source snapshot.':'The compared note uses the same source snapshot.'));
  const original=node('button','Read the compared note');original.type='button';original.className='secondary';original.onclick=()=>showNote({note_id:value.note_id,payload_hash:value.note_payload_hash}).catch(error=>status(error.message));panel.append(original);
  const table=node('table'),head=node('thead'),header=node('tr');
  ['Company / fiscal year','Earlier margin','Current margin','Change in percentage points','Result','Current SEC evidence'].forEach(text=>header.append(node('th',text)));head.append(header);table.append(head);
  const body=node('tbody');
  value.comparisons.forEach(row=>{const tr=node('tr');[`${row.ticker} / ${row.fiscal_year}`,row.prior?row.prior.margin_pct+'%':'Unavailable',row.current?row.current.margin_pct+'%':'Unavailable',row.change?.margin_percentage_points??'Not calculated',row.status==='compared'?'Current facts verified':row.reason].forEach(text=>tr.append(node('td',text)));const refs=node('td');(row.current?.fact_ids||[]).forEach((id,index)=>{const button=node('button',index?'Operating income':'Revenue');button.className='secondary';button.onclick=()=>client.showFact(id);refs.append(button);});tr.append(refs);body.append(tr);});
  table.append(body);const wrap=node('div');wrap.className='table-wrap';wrap.append(table);panel.append(wrap);
  value.limitations.forEach(text=>panel.append(node('p',text)));panel.hidden=false;
 }
 function renderReferences(refs,container,{editable=false}={}){
  container.replaceChildren();
  if(!refs.length){container.append(node('p','No relevant approved history selected.'));return;}
  refs.forEach(ref=>{
   const detail=node('details');detail.append(node('summary',ref.title));
   detail.append(node('p',ref.archive_only?'Earlier source snapshot · use as historical context.':'Same source snapshot · use as historical context.'));
   const citation=node('p',ref.citation);citation.className='fingerprint';detail.append(citation);
   const controls=node('div');controls.className='row';
   const read=node('button','Read approved note');read.type='button';read.className='secondary';read.onclick=()=>showNote(ref).catch(error=>status(error.message));controls.append(read);
   const compare=node('button','Compare current facts');compare.type='button';compare.className='secondary';compare.onclick=async()=>{try{showComparison(await client.api('/api/memory/notes/'+encodeURIComponent(ref.note_id)+'/comparison'));}catch(error){status(error.message);}};controls.append(compare);
   if(editable){const forget=node('button','Forget for future research');forget.type='button';forget.className='secondary';forget.onclick=()=>setEligibility(ref.note_id,true).catch(error=>status(error.message));controls.append(forget);}
   detail.append(controls);container.append(detail);
  });
 }
 function renderPolicy(){
  const container=byId('forgotten-notes');container.replaceChildren();
  if(!policy.excluded_note_ids.length){container.append(node('p','No approved notes are excluded from future memory.'));return;}
  policy.excluded_note_ids.forEach(id=>{const row=node('div');row.className='row';row.append(node('span','Forgotten approved note · '+id.slice(0,8)));
   const read=node('button','Read original');read.type='button';read.className='secondary';read.onclick=()=>showNote({note_id:id}).catch(error=>status(error.message));
   const restore=node('button','Restore to memory');restore.type='button';restore.className='secondary';restore.onclick=()=>setEligibility(id,false).catch(error=>status(error.message));row.append(read,restore);container.append(row);});
 }
 async function setEligibility(id,excluded){
  policy=await client.api('/api/memory/notes/'+encodeURIComponent(id)+'/eligibility',{method:'PUT',body:JSON.stringify({excluded,expected_revision:policy.revision})});
  renderPolicy();await searchHistory();status(excluded?'The note is excluded from future memory. Its approved publication remains in the library.':'The approved note is eligible for future memory again.');
 }
 async function searchHistory(){
  const scope=client.getSelection();
  const result=await client.api('/api/memory/history/search',{method:'POST',body:JSON.stringify({query:scope.question,tickers:scope.tickers,years:scope.years,k:3})});
  byId('memory-history-scope').textContent=`Results for ${scope.tickers.join(' / ')} · fiscal ${scope.years.join(', ')}. Search again after changing the research question or scope.`;
  policy=result.note_policy;renderPolicy();renderReferences(result.references,byId('memory-history'),{editable:true});
 }
 async function load(config){
  byId('analyst-memory').hidden=false;
  const [saved,coverage,notePolicy]=await Promise.all([client.api('/api/memory/preferences'),client.api('/api/memory/coverage'),client.api('/api/memory/note-policy')]);
  profile=saved;policy=notePolicy;renderPolicy();
  byId('memory-style').value=saved.values.report_style||'table_first';byId('memory-limit').value=String(saved.values.history_limit??3);
  const expiry=saved.expires_at?new Date(saved.expires_at*1000).toLocaleDateString():'';
  status(saved.status==='active'?'Preferences saved · expire '+expiry:saved.status==='expired'?'Saved preferences expired. Choose and save current defaults.':'No saved analyst preferences.');
  const defaults=preferenceDefaults(config,saved);if(defaults)client.applyDefaults(defaults);
  const container=byId('memory-coverage');container.replaceChildren();
  const issuers=[...new Set(coverage.rows.map(row=>row.ticker))];
  issuers.forEach(ticker=>{const rows=coverage.rows.filter(row=>row.ticker===ticker);container.append(node('p',`${ticker} · fiscal ${rows.map(row=>row.fiscal_year).join(', ')} · ${rows.reduce((n,row)=>n+row.fact_count,0)} financial inputs · ${rows.reduce((n,row)=>n+row.passage_count,0)} passages`));});
  coverage.limitations.forEach(text=>container.append(node('p',text)));
 }
 function initialize(options){
  client=options;
  byId('save-memory').onclick=async()=>{try{const scope=client.getSelection();profile=await client.api('/api/memory/preferences',{method:'PUT',body:JSON.stringify({expected_revision:profile.revision,values:{default_companies:scope.tickers,default_years:scope.years,report_style:byId('memory-style').value,history_limit:Number(byId('memory-limit').value)}})});status('Preferences saved for thirty days. Pending research using older memory needs a fresh plan.');}catch(error){status(error.message);}};
  byId('delete-memory').onclick=async()=>{try{profile=await client.api('/api/memory/preferences',{method:'DELETE',body:JSON.stringify({expected_revision:profile.revision})});byId('memory-style').value='table_first';byId('memory-limit').value='3';status('Saved preferences deleted. Earlier research and approval records remain in the library.');}catch(error){status(error.message);}};
  byId('search-memory').onclick=()=>searchHistory().catch(error=>status(error.message));
 }
 function renderRun(run){
  const panel=byId('run-memory'),snapshot=run.pending?.payload?.memory_context||run.draft?.memory_context||run.plan?.memory_context||run.memory_context;
  panel.hidden=!snapshot;if(!snapshot)return;
  byId('run-memory-description').textContent=snapshot.enabled?'These local references are bound to this research version. Historical content remains separate from the current SEC evidence.':'Analyst memory is off for this research.';
  renderReferences(snapshot.note_refs||[],byId('run-memory-references'));
 }
 function renderNote(value,container){if(value.memory_context?.note_refs?.length){const refs=node('div');renderReferences(value.memory_context.note_refs,refs);container.append(node('p','Local history references saved with this approved note:'),refs);}}
 const api={initialize,load,renderRun,renderNote,preferenceDefaults};
 if(typeof module!=='undefined'&&module.exports)module.exports={preferenceDefaults};
 if(root)root.AnalystMemory=api;
})(typeof window!=='undefined'?window:null);
