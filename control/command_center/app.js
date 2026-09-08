let DATA=null,REQFILTER='ALL',GATEFILTER='ALL';
const $=id=>document.getElementById(id);
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function badge(s){let v=String(s??'OPEN').toUpperCase();let c=v.includes('PASS')||v==='RELEASED'||v==='CURRENT'?'PASS':v.includes('STALE')?'STALE':v.includes('PARTIAL')||v.includes('CANDIDATE')||v.includes('UNHASHED')?'PARTIAL':'HOLD';return `<span class="badge ${c}">${esc(v)}</span>`}
async function api(path,opt={}){let r=await fetch(path,opt);let t=await r.text();if(!r.ok)throw new Error(t);return t?JSON.parse(t):{}}
async function action(id){return api('/api/action?id='+encodeURIComponent(id),{method:'POST'})}

document.querySelectorAll('.nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));b.classList.add('active');$(b.dataset.page).classList.add('active')});
document.querySelectorAll('[data-rq]').forEach(b=>b.onclick=()=>{REQFILTER=b.dataset.rq;document.querySelectorAll('[data-rq]').forEach(x=>x.classList.remove('active'));b.classList.add('active');renderRequirements()});
document.querySelectorAll('[data-gate]').forEach(b=>b.onclick=()=>{GATEFILTER=b.dataset.gate;document.querySelectorAll('[data-gate]').forEach(x=>x.classList.remove('active'));b.classList.add('active');renderFilter()});

function renderOverview(){
 let s=DATA.state, r=s.requirements, g=s.gates, p=s.provenance;
 $('overviewMetrics').innerHTML=[
  ['Requirements released',`${r.released}/${r.total}`],
  ['Requirement blockers',r.blockers],
  ['Gate blockers',g.blockers],
  ['Unhashed evidence',p.unhashed],
  ['Current action',s.current_action]
 ].map(([a,b])=>`<div class=card><div class=metric>${esc(b)}</div><small>${esc(a)}</small></div>`).join('');
 let blockers=[...r.rows.filter(x=>x.release_blocker).map(x=>({name:x.id+' · '+x.title,why:x.statement,status:x.requirement_status})),...g.rows.filter(x=>/^(HOLD|STALE|OPEN)/.test(x.status)).map(x=>({name:x.gate,why:x.reason,status:x.status}))];
 $('overviewBlockers').innerHTML=blockers.length?blockers.map(x=>`<div class="item hold"><b>${esc(x.name)}</b> ${badge(x.status)}<div class=muted>${esc(x.why)}</div></div>`).join(''):'<div class="item pass">No current release blockers.</div>';
 $('engineeringActions').innerHTML=`<button class=action onclick="action('RUN_P006_SERVICE')">Build/verify P006 service candidate</button> <button class=secondary onclick="action('OPEN_FILE:CAD-R1-ASM')">Open full C2R1 assembly</button> <button class=secondary onclick="action('OPEN_FILE:CAD-A001')">Open production A001</button> <button class=secondary onclick="action('REPORT_REQUIREMENTS')">Requirements coverage</button> <button class=secondary onclick="action('CHECK_FEMM_INSTALL')">Check FEMM</button> <button class=secondary onclick="action('REFRESH_BOM')">Refresh BOM</button>`;
 $('provenanceSummary').innerHTML=`Tracked evidence: <b>${p.tracked}</b> · Unhashed: <b>${p.unhashed}</b><br><small>STALE is computed from recorded SHA-256 input/tool hashes where provenance sidecars exist. UNHASHED means provenance migration is still required.</small><div style="margin-top:8px"><button class=action onclick="action('BACKFILL_PROVENANCE')">Backfill current C2R1 hashes</button></div>`;
}
function renderRequirements(){
 let rows=DATA.state.requirements.rows;
 if(REQFILTER==='BLOCKER')rows=rows.filter(x=>x.release_blocker); if(REQFILTER==='RELEASED')rows=rows.filter(x=>x.requirement_status==='RELEASED');
 $('reqMetrics').innerHTML=`<div class=card><div class=metric>${DATA.state.requirements.total}</div><small>Total</small></div><div class=card><div class=metric>${DATA.state.requirements.released}</div><small>Released</small></div><div class=card><div class=metric>${DATA.state.requirements.blockers}</div><small>Blockers</small></div>`;
 $('requirementsTable').innerHTML=`<table><thead><tr><th>ID</th><th>Requirement</th><th>Status</th><th>Verification</th><th>Linked gates</th></tr></thead><tbody>${rows.map(x=>`<tr><td class=mono>${esc(x.id)}</td><td><b>${esc(x.title)}</b><br>${esc(x.statement)}</td><td>${badge(x.requirement_status)}</td><td>${esc(x.verification_method)}</td><td>${esc((x.gates||[]).join(', '))}</td></tr>`).join('')}</tbody></table>`;
}
function renderFilter(){
 let rows=DATA.state.gates.rows;
 if(GATEFILTER==='BLOCKER')rows=rows.filter(x=>/^(HOLD|STALE|OPEN)/.test(x.status)); if(GATEFILTER==='PASS')rows=rows.filter(x=>x.status==='PASS');
 $('filterList').innerHTML=rows.map(x=>`<div class="item ${/^(HOLD|STALE|OPEN)/.test(x.status)?'hold':'pass'}"><b>${esc(x.gate)}</b> ${badge(x.status)}<div class=muted>${esc(x.reason)}</div>${(x.requirement_ids||[]).length?`<div class=mono>blocked by: ${esc(x.requirement_ids.join(', '))}</div>`:''}</div>`).join('');
}
function renderSolidWorks(){
 let sw=DATA.solidworks||null;
 if(!sw){$('solidworksPanel').innerHTML=`No live bridge state. <div style="margin-top:8px"><button class=action onclick="action('START_SW_BRIDGE')">Start SOLIDWORKS live bridge</button></div>`;return}
 $('solidworksPanel').innerHTML=`${badge(sw.status||'OPEN')}<br>Revision: <b>${esc(sw.solidworks_revision||'—')}</b><br>Active: <span class=mono>${esc(sw.active_document?.title||'—')}</span><br>Type: <b>${esc(sw.active_document?.document_type||'—')}</b><br>Dirty: <b>${esc(sw.active_document?.dirty??'—')}</b><div style="margin-top:8px"><button class=secondary onclick="action('START_SW_BRIDGE')">Restart bridge</button></div>`;
}
function renderHandoff(){
 $('handoffPanel').innerHTML=`Build one current ZIP for AI/review containing requirements, state, BOM, CAD evidence, Git/FEMM state and hashes.<div style="margin-top:8px"><button class=action onclick="action('BUILD_AI_HANDOFF')">Build AI Handoff ZIP</button></div>`;
}
function renderProduct(){
 let b=DATA.bom||DATA.state.bom;
 if(!b){$('bomPanel').innerHTML=`No current BOM JSON found. <div style="margin-top:8px"><button class=action onclick="action('REFRESH_BOM')">Generate/refresh BOM</button></div>`}
 else{
   let rows=b.rows||[];
   $('bomPanel').innerHTML=`${badge(b.status||'OPEN')}<br>Rows: <b>${esc(b.row_count??b.unique_rows??rows.length)}</b><br>Source issues: <b>${esc(b.issue_count??b.release_blockers??'—')}</b><div style="margin-top:8px"><button class=action onclick="action('REFRESH_BOM')">Refresh BOM</button> <button class=secondary onclick="action('NORMALIZE_BOM')">Normalize review identity</button></div><small>BOM availability is independent of metadata projection. OPEN metadata remains visible as HOLD.</small>${rows.length?`<div style="max-height:420px;overflow:auto;margin-top:10px"><table><thead><tr><th>Part</th><th>Qty</th><th>Description</th><th>Observed material</th><th>Release status</th></tr></thead><tbody>${rows.map(r=>`<tr><td class=mono>${esc(r.PartNo||r.observed_part_no||'')}</td><td>${esc(r.Qty??r.qty??'')}</td><td>${esc(r.Description||r.description||'')}</td><td>${esc(r.SolidWorksMaterial||r.solidworks_material||'')}</td><td>${esc(r.MaterialReleaseStatus||r.status||'')}</td></tr>`).join('')}</tbody></table></div>`:''}`;
 }
 $('drawingPanel').innerHTML=`${badge('REJECTED_FOR_PRODUCTION')}<br><b>Drawing V3 is retained as negative evidence.</b><br><small>Next implementation is a native SOLIDWORKS TPD compiler driven by released requirements, datums, tolerance stacks and Drawing Definition data. No AutoDimension and no hard-coded engineering values in UI/layout code.</small><div style="margin-top:8px"><button class=secondary onclick="action('OPEN_TPD_ARCH')">Open TPD architecture</button></div>`;
}
function renderFiles(){
 let rows=DATA.files?.entries||[];
 $('filesPanel').innerHTML=`<table><thead><tr><th>Artifact</th><th>Status</th><th>Action</th></tr></thead><tbody>${rows.slice(0,30).map(x=>`<tr><td><b>${esc(x.name)}</b><br><span class=mono>${esc(x.path)}</span></td><td>${x.exists?badge('FOUND'):badge('MISSING')}</td><td>${x.exists?`<button class=secondary onclick="action('OPEN_FILE:${esc(x.id)}')">Open</button>`:''}</td></tr>`).join('')}</tbody></table>`;
 let g=DATA.git||{};$('gitPanel').innerHTML=`Local status: ${badge(g.status||'OPEN')}<br>Branch: <b>${esc(g.branch||'—')}</b><br>Dirty: <b>${esc(g.dirty??'—')}</b><br>Untracked: <b>${esc(g.untracked??'—')}</b><br>Origin: <span class=mono>${esc(g.origin||'—')}</span><br>Remote: ${g.remote_health?badge(g.remote_health.status||'OPEN'):'not checked'}<div style="margin-top:8px"><button class=action onclick="action('CHECK_GITHUB_REMOTE')">Check remote</button> <button class=secondary onclick="action('RUN_GIT_CLASSIFIER')">Classify changes</button></div>`;
}
function renderAll(){renderOverview();renderRequirements();renderFilter();renderProduct();renderFiles();renderSolidWorks();renderHandoff()}
async function refresh(){
 try{
  let [state,files,git,bom,sw]=await Promise.all([api('/api/state'),api('/api/files'),api('/api/git'),api('/api/bom'),api('/api/solidworks')]);
  DATA={state:state.state,files:files.files,git:git.git,bom:bom.bom,solidworks:sw.solidworks};renderAll();$('error').innerHTML='';
 }catch(e){$('error').innerHTML=`<div class=err>${esc(e.message)}</div>`}
}
refresh();setInterval(refresh,8000);