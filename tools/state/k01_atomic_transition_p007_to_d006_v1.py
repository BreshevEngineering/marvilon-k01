from __future__ import annotations
import argparse, copy, datetime as dt, hashlib, json, shutil, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01"); L=Path(r"D:\BreshevEngineering\K01_local")
PD=Path('control/product_definition/K01_P007_PRODUCT_DEFINITION_RELEASE_CURRENT.json')
SPEC=Path('control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_RELEASE_CANDIDATE.json')
READ=Path('reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json')
GAP=Path('control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json')
GOAL=Path('control/project/K01_GOAL_LOCK_CURRENT.json')
WORK=Path('control/workpacks/K01_P007_PRODUCT_DEFINITION_CLOSURE_v1.json')
NEXT=Path('control/project/K01_NEXT_ACTIONS_CURRENT.json')
GATE=Path('control/project/K01_ACTIVE_STEP_GATE.json')
TEMP=Path('reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json')
FRONT=Path('control/state/K01_COMPLETION_FRONTIER_CURRENT.json')
DC=Path('reports/control/K01_DRAWING_CONTROL_CURRENT.json')
CENTER=Path('control/center/K01_CENTER_INPUT_CURRENT.json')
EDRS=[Path('control/decisions/EDR-035_J2_MEDIA_SEAL_LEAK_RELEASE.json'),Path('control/decisions/EDR-036_J2_FASTENER_SERVICE_RELEASE.json'),Path('control/decisions/EDR-037_P007_RELEASE_COMPLETION.json')]
CLOSE={'C01','C05','C06','C12','K01-D006-BLIND-END','PDG-SURFACE-TEXTURE','PDG-EDGE-CONDITION','PDG-INSPECTION-METHODS','PDG-MANUFACTURING-ROUTE','PDG-CONFIG-EFFECTIVITY','PDG-BINDING-INVARIANCE','PDG-MEASUREMENT-CONDITIONS'}

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def rd(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def sha(p): h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def run(cmd,repo): print('>',' '.join(map(str,cmd))); subprocess.run(cmd,cwd=repo,check=True,text=True)
def temp_pass(p):
 if not p.exists(): return False
 b=json.dumps(rd(p),ensure_ascii=False).upper(); return 'PASS_TEMPORAL_COHERENCE' in b and 'HOLD_TEMPORAL_COHERENCE' not in b
def accepted(p):
 if not p.exists(): return False
 s=str(rd(p).get('status','')).upper(); return 'ACCEPT' in s or 'RELEASE' in s or 'PASS' in s
def backup(repo,local,rels):
 out=local/'backups'/('ATOMIC_TRANSITION_P007_TO_D006_'+dt.datetime.now().strftime('%Y%m%d_%H%M%S'))
 for r in rels:
  s=repo/r
  if s.exists(): d=out/r; d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(s,d)
 return out
def close_nodes(o):
 n=0
 if isinstance(o,dict):
  if o.get('id') in CLOSE:
   o['state']='CLOSED_DESIGN_DEFINITION'
   if 'status' in o:o['status']='CLOSED_DESIGN_DEFINITION'
   o['closed_by']='EDR-035/036/037 + P007 Product Definition release'; o['timing']='DONE_L5'; n+=1
  for v in o.values(): n+=close_nodes(v)
 elif isinstance(o,list):
  for v in o:n+=close_nodes(v)
 return n
def upd_read(o):
 o=copy.deepcopy(o); o['schema']='k01.product_definition_readiness.current.v4_transition'; o['generated_utc']=now(); o['status']='READY_FOR_D006_RELEASE_PIPELINE'; o['product_definition_ready']=True; o['qualification_complete']=False
 g=o.setdefault('gates',{}); g.update({'DEFINITION_CONSISTENCY':'PASS','REQUIREMENT_ALLOCATION_IDENTITY':'PASS','DRAWING_CANDIDATE_READY':'PASS','BINDING_INVARIANCE_RELEASE':'PASS_PINNED_CONTROLLED_CONFIGURATION','MANUFACTURING_FEASIBILITY_RELEASE':'DEFINED__CAPABILITY_QUALIFICATION_OPEN','CONFIGURATION_EFFECTIVITY_RELEASE':'PASS_PINNED_CONTROLLED_CONFIGURATION','INSPECTION_DEFINITION':'DEFINED','SURFACE_TEXTURE_RELEASE':'PASS','DRAWING_RELEASE_READY':'READY_FOR_L6_RELEASE_READINESS'})
 s=o.setdefault('safe_projection_ids',[])
 for c in ['C01','C02','C03','C04','C05','C06','C07','C08','C09','C10','C11','C12','K01-D006-BLIND-END']:
  if c not in s:s.append(c)
 o['release_blocker_count']=0; o['release_blockers']=[]; o['chain_open_counts']={'missing_allocations':0,'measurement_conditions':0,'binding_invariance':0,'inspection_strategy':0,'manufacturing_route':0,'configuration_effectivity':0}
 o['carry_forward_qualification']=['C12 physical leak test','J2 50-cycle service qualification','P007 FAI/process capability','seal/screw incoming qualification']
 o['next']='Run final D006 Product Definition/drawing release readiness review; do not broaden scope.'
 return o
def upd_gap(o):
 o=copy.deepcopy(o); n=close_nodes(o); o['generated_utc']=now(); o['status']='P007_PRODUCT_DEFINITION_READY__L8_QUALIFICATION_CARRIED_FORWARD'; o['product_definition_ready']=True
 if 'release_blockers' in o:o['release_blockers']=[]
 for k in ('release_blocker_count','blocking_count','open_blocker_count'):
  if k in o:o[k]=0
 o['closed_gap_nodes_by_transition']=n; o['carry_forward_qualification']=['C12 physical leak test','J2 50-cycle service qualification','P007 FAI/process capability','seal/screw incoming qualification']; o['next']='Run final D006 release-readiness review.'
 return o
def upd_goal(o):
 o=copy.deepcopy(o); o['generated_utc']=now(); o['active_dependency']='K01-D006 RELEASE PIPELINE'; o['current_lifecycle_level']='L6'; o['active_engineering_object']='K01-D-006'; o['current_execution_mode']='READ_ONLY_D006_RELEASE_READINESS'
 s=o.setdefault('state_semantics',{}); s.update({'CURRENT_LIFECYCLE_LEVEL':'L6','CURRENT_DELIVERABLE':'FULL K01-D-006 MANUFACTURING DRAWING','ACTIVE_DEPENDENCY':'K01-D006 RELEASE PIPELINE','ACTIVE_ENGINEERING_OBJECT':'K01-D-006','rule':'P007 Product Definition READY; physical qualification OPEN remains downstream L8.'})
 return o

def normalize_l6_navigation(repo):
 n0=rd(repo/NEXT); g0=rd(repo/GATE) if (repo/GATE).exists() else {}
 # The reducer is allowed to choose the first genuine downstream L6 action.
 rid=n0.get('next_action_id')
 rtext=n0.get('next_1')
 if rid!='K01-NA-D006-RELEASE-READINESS':
  raise SystemExit('HOLD: reducer did not select expected first downstream D006 release-readiness review; got '+repr(rid))
 blocker='D006-RELEASE-READINESS'
 expected='PASS_D006_RELEASE_READINESS__NEXT_EXECUTABLE_IDENTIFIED'
 authority=[str(PD).replace('\\','/'),str(SPEC).replace('\\','/'),'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json','control/drawings/K01_DRAWING_REGISTRY_CURRENT.json',str(DC).replace('\\','/'),'control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v1.json']
 epoch=n0.get('state_epoch')
 n=copy.deepcopy(n0)
 n.update({'schema':'k01.next_actions.current.v20_lifecycle','current_lifecycle_level':'L6','active_dependency':'K01-D006 RELEASE PIPELINE','active_engineering_object':'K01-D-006','active_line':'K01-D006 RELEASE PIPELINE','active_blocker':blocker,'current_blocker':blocker+':OPEN','expected_closure':expected,'execution_mode':'READ_ONLY_D006_RELEASE_READINESS','authority_set':authority})
 n['release_blockers']=[{'id':blocker,'state':'OPEN','role':'Determine first genuine executable D006 release-pipeline blocker from current authorities','class':'L6_EXECUTABLE_BLOCKER'}]
 n['carry_forward_l8']=['C12 physical leak qualification','J2 50-cycle qualification','P007 FAI/process capability','seal/screw incoming qualification']
 n['do_not_do']=['Do not reopen EDR-035/036/037.','Do not push L8 qualification backward into Product Definition.','Do not regenerate D006 from zero.','Do not perform native save during release-readiness review.','Do not make Center or Git cleanup the engineering front.']
 g={'schema':'k01.active_step_gate.v4_lifecycle','state_epoch':epoch,'generated_utc':now(),'step_id':'K01-STEP-D006-L6-RELEASE-READINESS','current_lifecycle_level':'L6','active_line':'K01-D006-RELEASE-PIPELINE','checkpoint_id':g0.get('checkpoint_id','K01-CP-20260910-BASELINE-02C-PROMOTED'),'intent':rid,'intent_text':rtext,'active_blocker':blocker,'expected_closure':expected,'mutation_authorized':False,'mutation_scope':'READ_ONLY_D006_RELEASE_READINESS; NO NATIVE SAVE','result_on_pass':expected,'required_files':authority,'impact_declarations':{'product_definition':'P007 READY and frozen unless stale-triggered.','drawing':'Read-only review; no native save or candidate rebuild.','qualification':'L8 items carried forward.','center':'projection only.','git':'no broad cleanup.'}}
 f={'schema':'k01.completion_frontier.current.v2','generated_utc':now(),'current_lifecycle_level':'L6','lifecycle_name':'Candidate TPD','current_deliverable':'FULL K01-D-006 MANUFACTURING DRAWING','wip_limit':1,'active_engineering_object':'K01-D-006','active_dependency':'K01-D006 RELEASE PIPELINE','active_blocker':{'id':blocker,'state':'OPEN','timing':'ACTIVE_NOW'},'next_allowed_action':{'id':rid,'text':rtext,'authority_set':authority,'expected_closure':expected,'execution_mode':'READ_ONLY_D006_RELEASE_READINESS'},'maturity':{'engineering_definition':'READY','analytical_verification':'ENGINEERING','drawing_tpd':'CANDIDATE','manufacturing_definition':'DEFINED__CAPABILITY_OPEN_L8','inspection_definition':'DEFINED','physical_qualification':'OPEN_L8','configuration':'CONTROLLED_CANDIDATE','release':'HOLD'},'timing':{'ACTIVE_NOW':[blocker],'WAITING_DEPENDENCY':['D006-SPEC-PROMOTION-BINDING','D006-CANDIDATE-AUTHORING','D006-SEMANTIC-NATIVE-QA','D006-D8-VISUAL-QA'],'LATER':['L8 physical qualification','EBOM/MBOM closure','remaining Product Definitions/drawings','release configuration'],'DEBT':['broad Git cleanup','Center UI refresh','SW2026 migration preparation']},'source_identity':{'p007_product_definition_sha256':sha(repo/PD),'d006_release_spec_sha256':sha(repo/SPEC),'drawing_control_sha256':sha(repo/DC) if (repo/DC).exists() else None}}
 wr(repo/NEXT,n); wr(repo/GATE,g); wr(repo/FRONT,f)

 center=rd(repo/CENTER) if (repo/CENTER).exists() else {}
 center.update({'generated_utc':now(),'state_epoch':epoch,'completion_frontier':str(FRONT).replace('\\','/'),'semantic_coherence':'reports/control/K01_SEMANTIC_COHERENCE_CURRENT.json','current_lifecycle_level':'L6','active_engineering_object':'K01-D-006','active_blocker':blocker,'next_action_id':rid,'projection_policy':'Center is presentation/orchestration only. Project lifecycle/navigation authorities remain in control/state + control/project.'})
 wr(repo/CENTER,center)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=str(R)); ap.add_argument('--local-root',default=str(L)); ap.add_argument('--apply',action='store_true'); a=ap.parse_args(); repo=Path(a.repo_root); local=Path(a.local_root)
 print('K01 ATOMIC TRANSITION P007 -> D006 / L6 (v1.1)')
 print('mode:','APPLY' if a.apply else 'DRY-RUN')
 if not temp_pass(repo/TEMP): raise SystemExit('HOLD: temporal coherence not PASS')
 pd=rd(repo/PD) if (repo/PD).exists() else {}; spec=rd(repo/SPEC) if (repo/SPEC).exists() else {}
 if not (pd.get('product_definition_ready') is True and pd.get('status')=='READY_FOR_D006_RELEASE_PIPELINE'): raise SystemExit('HOLD: P007 Product Definition not READY')
 if 'RELEASE_CANDIDATE_SPEC_READY' not in str(spec.get('status','')): raise SystemExit('HOLD: D006 final release spec not ready')
 for e in EDRS:
  if not accepted(repo/e): raise SystemExit('HOLD: missing/not accepted '+str(e))
 print('PRECHECK PASS: P007 READY / EDR-035..037 / D006 final spec / temporal PASS')
 if not a.apply:return 0
 if not (repo/READ).exists() or not (repo/GAP).exists() or not (repo/GOAL).exists(): raise SystemExit('HOLD: required transition authority missing')
 b=backup(repo,local,[READ,GAP,GOAL,WORK,NEXT,GATE,FRONT,CENTER]); print('BACKUP:',b)
 wr(repo/READ,upd_read(rd(repo/READ))); wr(repo/GAP,upd_gap(rd(repo/GAP))); wr(repo/GOAL,upd_goal(rd(repo/GOAL)))
 if (repo/WORK).exists():
  w=rd(repo/WORK); w['transition']={'generated_utc':now(),'status':'CLOSED_PRODUCT_DEFINITION_READY','closed_by':['EDR-035','EDR-036','EDR-037'],'next_lifecycle_level':'L6'}; w['status']='CLOSED_PRODUCT_DEFINITION_READY'; wr(repo/WORK,w)
 run([sys.executable,'tools/state/k01_current_state_reducer_v1.py','--repo-root',str(repo)],repo)
 normalize_l6_navigation(repo)
 run([sys.executable,'tools/state/k01_temporal_coherence_guard_v1.py','--repo-root',str(repo),'--write-report'],repo)
 run([sys.executable,'tools/state/k01_semantic_coherence_guard_v1.py','--repo-root',str(repo),'--write-report'],repo)
 print('PASS: L6 / D006 / D006-RELEASE-READINESS / expected NEXT executable identified')
 return 0

if __name__=='__main__': raise SystemExit(main())
