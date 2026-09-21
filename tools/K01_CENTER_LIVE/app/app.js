'use strict';
let refreshing=false,lastSequence=null;
let state=null,tab='p007',query='',bomTab='ebom',busy=false;
const $=id=>document.getElementById(id);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const value=x=>typeof x==='object'?JSON.stringify(x):String(x??'—');
const tag=x=>`<span class="tag" data-status="${esc(x)}">${esc(x??'NOT_DECLARED')}</span>`;
const empty=x=>`<div class="empty">${esc(x)}</div>`;
const raw=x=>`<details><summary>Source record</summary><pre>${esc(JSON.stringify(x,null,2))}</pre></details>`;
const matches=x=>!query||JSON.stringify(x).toLowerCase().includes(query);
const fileLink=(id,text)=>id?`<a href="/artifact?id=${encodeURIComponent(id)}" target="_blank" rel="noopener">${esc(text)}</a>`:'';
function card(x){return `<article class="card"><div class="card-head"><h3>${esc(x.id||x.node||x.name||'Record')} ${esc(x.title||'')}</h3>${tag(x.status||x.severity)}</div>${(x.reasons||[]).map(r=>`<div class="reason">${esc(value(r))}</div>`).join('')||'<p class="muted">No explanation is included in this record.</p>'}${x.next_action?`<p>Next action: ${esc(value(x.next_action))}</p>`:''}${x.depends_on?`<p class="muted">Depends on: ${esc(value(x.depends_on))}</p>`:''}${taskLinks(x)}${raw(x)}</article>`}

function taskLinks(x){
 const id=String(x.id||'').toUpperCase();
 const dest=/BOM|NM-/.test(id)?'bom':/GIT/.test(id)?'history':'artifacts';
 const term=/FEMM/.test(id)?'FEMM':/P007|D-006|DRAWING/.test(id)?'P007':/BOM/.test(id)?'':id;
 return `<div class="links"><button data-go="${dest}" data-query="${esc(term)}">${dest==='bom'?'Review BOM items':dest==='history'?'Review Git revisions':'Find related evidence'}</button>${fileLink(state.sources.verdict.file_id,'Open project report')}</div>`;
}
function workspace(){return `<div class="section-tabs"><button data-go="bom" data-query="">Review parts and materials</button><button data-go="artifacts" data-query="">Open project files</button><button data-go="graph" data-query="">Inspect dependencies</button><button data-go="sources" data-query="">Check connections</button></div><p>Start with an open item below. Review its source and related files, update the responsible project definition, then run the project workflow and refresh this view.</p><p class="muted">Refresh reads saved reports; it does not run CAD or recalculate engineering results.</p>`}

function render(){if(!state)return;
 $('overall').innerHTML=tag(state.overall);$('date').textContent=kyivTime(state.generated_utc);$('fresh').textContent=state.freshness==='NOT_DECLARED'?'Not assessed by source':value(state.freshness);
 const issues=Object.entries(state.sources).filter(([,s])=>s.state!=='AVAILABLE').map(([k,s])=>`${k}: ${s.state}${s.error?' — '+s.error:''}`);
 const alternatives=(state.source_candidates||[]).filter(p=>p!==state.sources.verdict.path);
 if(alternatives.length)issues.push('Additional state documents found; not used as substitutes: '+alternatives.join(', '));
 const changed=state.input_checks.filter(x=>x.state!=='MATCH');
 $('integrity').innerHTML=(issues.length?`<div class="notice">${issues.map(esc).join('<br>')}</div>`:'')+(changed.length?`<div class="notice">Input file checks: ${esc(changed.map(x=>x.path+' — '+x.state).join('; '))}. The Center has not recalculated the saved engineering verdict.</div>`:'');
 $('integrity').innerHTML+=`<p class="muted">Connected source: ${esc(state.sources.verdict.path)} · ${esc(state.source_mode)}</p>`;
 if(state.source_mode==='LEGACY_REFERENCE')$('integrity').innerHTML+='<div class="notice">Historical project report. Its recorded statuses are shown for reference, not as a current release decision.</div>';
 $('commands').innerHTML=state.commands.map(c=>`<button data-command="${esc(c)}" ${busy?'disabled':''}>${esc(c==='center-build'?'Rebuild Center evidence':c==='pds-status'?'Project status':c==='pds-next'?'Next engineering task':c==='verdict'?'Run verdict':c==='audit'?'Run audit':c==='selftest'?'Run self-test':c)}</button>`).join('')+'<a href="/diagnostics" target="_blank" rel="noopener">Download diagnostics</a>';
 $('commands').innerHTML+=`<button data-command="build-ai-handoff" ${busy||!state.handoff_available?'disabled':''}>Build AI handoff</button>${state.handoff_ready?'<a href="/handoff-download">Download AI handoff ZIP</a>':''}${!state.handoff_available?'<span>Handoff unavailable: project builder tools/medtas/ai_handoff_v2_0.py is missing.</span>':''}`;
 let html='';
 $('commands').innerHTML+='<span class=muted>'+esc(state.capabilities?.state||'NOT_CONNECTED')+': '+esc(state.capabilities?.reason||'Dispatcher capabilities declared')+'</span>';
 if(tab==='p007'){
  const c=state.p007;
  html=`<h2>${esc(c.title)}</h2><p>1. Review the candidate PDF. 2. Select an open requirement below. 3. Open its controlled definition. 4. Update and verify it through the project workflow. 5. Refresh to read the new evidence.</p>`;
  html+='<div class="links"><a href="/integration-package">Download integration package</a><button data-go="bom" data-query="K01-P-007">P007 in EBOM</button></div>';
  html+='<p class="muted">Command execution: '+esc(state.capabilities?.state)+'. The integration package collects the existing dispatcher and P007 definitions for completing this connection.</p>';
  html+='<h2>Drawing and native candidates</h2>';
  const files=c.artifacts.filter(a=>['.pdf','.slddrw','.sldprt','.step'].includes(a.extension));
  html+=files.map(a=>'<article class="card"><h3>'+esc(a.id)+'</h3><p>'+esc(a.path)+'</p>'+tag(a.availability)+' '+fileLink(a.file_id,'Open / download candidate')+'</article>').join('')||empty('No linked candidate files found. Inspect Drawing verification below.');
  html+='<h2>Requirements linked by the drawing definition</h2>'+c.requirements.map(q=>'<article class=card><h3>'+esc(q.id)+' · '+esc(q.title)+'</h3>'+tag(q.requirement_status)+'<p>'+esc(q.statement)+'</p><p>Verification method: '+esc(q.verification_method)+'</p><p>Evidence coverage reported: '+esc(q.covered_by_evidence)+'</p>'+raw(q)+'</article>').join('');
  html+='<h2>Open work and completion evidence</h2><p class="muted">'+esc(c.action_policy)+'</p>';
  html+=c.issues.filter(matches).map(x=>'<article class="card"><div class="card-head"><h3>'+esc(x.id)+'</h3>'+tag(x.status||x.severity)+'</div><p>'+esc(x.reason||value(x.reasons))+'</p><p><strong>Suggested next action:</strong> '+esc(x.suggested_action)+'</p><p><strong>Evidence needed:</strong> '+esc(x.expected_evidence)+'</p>'+c.documents.slice(0,2).map(d=>fileLink(d.file_id,d.label)).join(' · ')+raw(x)+'</article>').join('')||empty('No matching P007/D006 blocker records in the selected report. This is not release approval.');
  html+='<h2>Definitions and verification results</h2>'+c.documents.map(d=>'<article class="card"><h3>'+esc(d.label)+'</h3>'+tag(d.availability)+' '+fileLink(d.file_id,'Open original')+'<p>'+esc(d.path)+'</p>'+raw(d.source_document||{error:d.error||'File missing'})+'</article>').join('');
 }
 if(tab==='overview'){html=workspace()+'<h2>Blockers and open work</h2>'+state.blockers.filter(matches).map(card).join('');if(!state.blockers.filter(matches).length)html+=empty(query?'No matches.':'No blocker records were found in this source. Open Sources or download diagnostics to inspect the connected files.');}
 if(tab==='graph'){
  html=['nodes','requirements','gates'].map((k,i)=>`<h2>${['Nodes and dependencies','Requirements','Gates'][i]}</h2>`+(state.groups[k].filter(matches).map(card).join('')||empty('No matching records in this source.'))).join('');
  html+='<h2>Requirement source documents</h2><p>These explicitly connected documents retain their original schema. Document availability does not mean requirements are approved.</p>'+Object.entries(state.requirement_documents||{}).map(([key,doc])=>'<article class=card><h3>'+esc(key==='requirements'?'Release requirements':'Fixed-coil actuator requirements')+'</h3>'+fileLink(state.sources[key]?.file_id,'Open original document')+'<p>'+esc(state.sources[key]?.note||'')+'</p>'+raw(doc)+'</article>').join('');
  html+='<h2>Dependency records</h2>'+Object.entries(state.graph.nodes||{}).map(([id,x])=>card({...x,id})).join('');
 }
 if(tab==='bom'){
  const b=state.boms[bomTab],rows=b.rows.filter(matches),s=state.sources[bomTab];
  html=`<div class="section-tabs"><button data-bom="ebom">EBOM</button><button data-bom="mbom">MBOM</button></div><p>${tag(b.status)} · Rows in source: ${b.rows.length} · ${fileLink(s.file_id,'Open source')}</p>`+b.reasons.map(r=>`<div class="reason">${esc(value(r))}</div>`).join('');
  const fields=[['part_number','PartNo','part_no','id'],['Description','description','name'],['Qty','qty','quantity'],['Material','material_authority','material'],['MakeBuy','make_buy','makebuy'],['Supplier','supplier'],['release_state','release_status','release','status']];
  html+=rows.length?`<div class="table-wrap"><table><thead><tr>${['Part number','Description','Quantity','Material','Make / buy','Supplier','Status'].map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>'<tr>'+fields.map((fs,i)=>{const v=fs.map(f=>r[f]).find(v=>v!==undefined&&v!==null);return `<td>${i===6?tag(v):esc(value(v))}</td>`}).join('')+'</tr>').join('')}</tbody></table></div>`:empty('No BOM rows match the current filter.');
  if(b.transformations.length)html+='<h2>Manufacturing transformations</h2>'+raw(b.transformations);
 }
 if(tab==='artifacts'){
  html='<h2>Drawings, calculations and source documents</h2>'+state.artifacts.filter(matches).map(a=>`<article class="card"><div class="card-head"><h3>${esc(a.id||a.name||a.path)}</h3>${tag(a.availability)}</div><p>${esc(a.path||a.file_path||'No path supplied')}</p><p>Source status: ${tag(a.status)}</p><div class="links">${fileLink(a.file_id,'Open / download')}${a.file_id&&['.pdf','.png','.jpg','.jpeg','.bmp'].includes(a.extension)?`<button data-preview="${esc(a.file_id)}" data-ext="${esc(a.extension)}">Preview</button>`:''}</div><div id="preview-${esc(a.file_id)}"></div>${raw(a)}</article>`).join('');if(!state.artifacts.filter(matches).length)html+=empty('No artifact records were found in the selected index.');
 }
 if(tab==='history')html='<h2>Dispatcher history</h2><p class="muted">Last 200 records. Execution return codes are shown separately from engineering acceptance. Ledger integrity is not certified by this view.</p>'+state.history_errors.map(x=>`<div class="notice">${esc(x)}</div>`).join('')+(state.history.filter(matches).map(x=>`<article class="card"><h3>${esc(x.command||x.event||x.id||'Event')}</h3><p>${esc(kyivTime(x.utc||x.generated_utc))} · return code ${esc(x.returncode??'—')}</p>${raw(x)}</article>`).join('')||empty('No dispatcher history found.'));
 if(tab==='history')html='<h2>Git revisions</h2>'+(state.git.commits||[]).map(c=>'<p>'+esc(kyivTime(c.date))+' · '+esc(c.hash)+' · '+esc(c.subject)+'</p>').join('')+raw(state.git)+html;
 if(tab==='sources')html='<h2>Connected sources and file versions</h2><p class="muted">SHA-256 identifies source files. Semantic hashes and engineering freshness come from the engine.</p>'+Object.entries(state.sources).filter(matches).map(([k,s])=>`<article class="card"><div class="card-head"><h3>${esc(k)}</h3>${tag(s.state)}</div><p>${esc(s.path)}</p><p class="muted">Modified: ${esc(kyivTime(s.modified))}</p><pre>${esc(s.sha256||'No fingerprint')}</pre>${fileLink(s.file_id,'Open document')}${s.error?`<div class="reason">${esc(s.error)}</div>`:''}</article>`).join('');
 if(tab==='sources'){html+='<h2>Project command catalog</h2><p>These are the project-owned command definitions. Unrecognized launch formats are available for inspection, but are not executed by the Center.</p>'+raw(state.command_catalog||{});}
 if(tab==='overview'&&!state.blockers.length)html+=raw(state.source_document);
 $('content').innerHTML=html;$('footer').textContent=state.repo_root+' · Results from connected project sources';
}
async function refresh(){if(refreshing)return;refreshing=true;try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);state=await r.json();$('error').hidden=true;render()}catch(e){$('error').hidden=false;$('error').textContent='Refresh failed: '+e.message+'. The previous display is not a new calculation.'}finally{refreshing=false}}
async function run(command){busy=true;render();$('job').hidden=false;$('jobstate').textContent='Running '+command;$('joboutput').textContent='';try{const r=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json','X-K01-Token':state.token},body:JSON.stringify({command})});const x=await r.json();if(!r.ok)throw Error(x.error||r.status);poll(x.id)}catch(e){$('jobstate').textContent=e.message;busy=false;render()}}
async function poll(id){try{const r=await fetch('/api/jobs');if(!r.ok)throw Error('HTTP '+r.status);const j=(await r.json())[id];if(!j)throw Error('Job not found');$('jobstate').textContent=j.command+' · '+j.state+(j.returncode!==null?' · return code '+j.returncode:'');$('joboutput').textContent=j.output||'Command running. Output will appear when it completes.';if(j.state==='RUNNING')setTimeout(()=>poll(id),1000);else{busy=false;await refresh()}}catch(e){$('jobstate').textContent=e.message;busy=false;render()}}
$('nav').addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(!b)return;tab=b.dataset.tab;document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('selected',x===b));$('title').textContent=b.textContent;render()});
$('commands').addEventListener('click',e=>{const b=e.target.closest('[data-command]');if(b&&!busy)run(b.dataset.command)});
$('content').addEventListener('click',e=>{const g=e.target.closest('[data-go]');if(g){tab=g.dataset.go;query=(g.dataset.query||'').toLowerCase();$('search').value=query;document.querySelectorAll('[data-tab]').forEach(b=>{b.classList.toggle('selected',b.dataset.tab===tab);if(b.dataset.tab===tab)$('title').textContent=b.textContent});render();return;}const b=e.target.closest('[data-bom]');if(b){bomTab=b.dataset.bom;render()}const p=e.target.closest('[data-preview]');if(p){const d=$('preview-'+p.dataset.preview);d.replaceChildren();const el=document.createElement(p.dataset.ext==='.pdf'?'iframe':'img');el.src='/artifact?id='+encodeURIComponent(p.dataset.preview);el.className='preview';el.title='Artifact preview';if(el.tagName==='IMG')el.alt='Artifact preview';d.append(el)}});
$('search').addEventListener('input',e=>{query=e.target.value.toLowerCase();render()});$('refresh').addEventListener('click',refresh);refresh();

async function activity(){
 try{
  const r=await fetch('/api/activity',{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);
  const m=await r.json();
  $('monitor-status').textContent=m.state+' · Last scan: '+kyivTime(m.checked_utc)+' · '+m.files+' saved files · scan interval: '+m.interval_seconds+' seconds plus scan time';
  $('activity').innerHTML=Object.entries(m.roots).map(([k,v])=>'<p>'+esc(k)+': '+esc(v)+'</p>').join('')+m.errors.map(e=>'<p>'+esc(e)+'</p>').join('')+(m.events.length?'<table><thead><tr><th>Observed</th><th>Change</th><th>File</th></tr></thead><tbody>'+m.events.map(e=>'<tr><td>'+esc(kyivTime(e.observed_utc))+'</td><td>'+esc(e.event)+'</td><td>'+esc(e.root+'/'+e.path)+'</td></tr>').join('')+'</tbody></table>':'<p>No changes observed since monitoring started.</p>');
  if(lastSequence!==m.sequence){lastSequence=m.sequence;await refresh();}
 }catch(e){$('monitor-status').textContent='DISCONNECTED: '+e.message;}
 finally{setTimeout(activity,3000);}
}
activity();
