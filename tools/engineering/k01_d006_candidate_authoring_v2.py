from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, subprocess, sys, time
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
SPEC=Path('control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v2.json')
PROM=Path('control/drawings/K01_D006_SPEC_PROMOTION_CURRENT.json')
DC=Path('reports/control/K01_DRAWING_CONTROL_CURRENT.json')
LEASE=Path('control/state/K01_NATIVE_MUTATION_LEASE_CURRENT.json')
REPORT=Path('reports/drawing/current/K01-D-006_V2_CANDIDATE_AUTHORING_CURRENT.json')
NEXT=Path('control/project/K01_NEXT_ACTIONS_CURRENT.json'); GATE=Path('control/project/K01_ACTIVE_STEP_GATE.json'); FRONT=Path('control/state/K01_COMPLETION_FRONTIER_CURRENT.json'); CENTER=Path('control/center/K01_CENTER_INPUT_CURRENT.json')

def rd(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def semantic_status(candidate):
 p=candidate/'evidence'/'semantic_report.txt'
 if not p.is_file(): return None
 for line in p.read_text(encoding='utf-8-sig',errors='replace').splitlines():
  if line.startswith('STATUS='): return line.split('=',1)[1].strip()
 return None

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=str(R)); ap.add_argument('--owner',default=os.environ.get('USERNAME','K01_USER')); a=ap.parse_args(); repo=Path(a.repo_root)
 for rel in (SPEC,PROM,DC,NEXT,GATE,FRONT):
  if not (repo/rel).exists(): raise SystemExit('HOLD: missing '+str(rel))
 prom=rd(repo/PROM); n=rd(repo/NEXT); spec=rd(repo/SPEC); dc=rd(repo/DC)
 if prom.get('status')!='PASS_D006_SPEC_PROMOTED__READY_FOR_NATIVE_CANDIDATE_LEASE': raise SystemExit('HOLD: D006 V2 spec promotion is not PASS.')
 if n.get('next_action_id')!='K01-NA-D006-NATIVE-MUTATION-LEASE': raise SystemExit('HOLD: project frontier is not at native-mutation lease acquisition.')
 model=Path(spec.get('model_path','')); outroot=Path(spec.get('output_root',''))
 drow=(dc.get('drawings') or {}).get('K01-D-006') or {}; current=((((drow.get('current') or {}).get('artifacts') or {}).get('drawing') or {}).get('path'))
 current_path=Path(current) if current else None
 if not model.is_file(): raise SystemExit('HOLD: P007 native model missing: '+str(model))
 if not current_path or not current_path.is_file(): raise SystemExit('HOLD: current D006 drawing missing.')
 existing={p.name for p in outroot.iterdir() if p.is_dir()} if outroot.is_dir() else set()
 model_pre=sha(model); current_pre=sha(current_path); start=time.time()
 lease={'schema':'k01.native_mutation_lease.current.v1','lease_id':'K01-D006-V2-'+dt.datetime.now().strftime('%Y%m%d_%H%M%S'),'status':'ACTIVE','owner_session':a.owner,'artifact_id':'K01-D006-NEW-CANDIDATE','native_path':str(outroot),'baseline_source_model':str(model),'baseline_source_model_sha256':model_pre,'baseline_current_drawing':str(current_path),'baseline_current_drawing_sha256':current_pre,'allowed_operation':'CREATE_NEW_D006_V2_CANDIDATE_ONLY__DO_NOT_OVERWRITE_CURRENT','start_utc':now(),'auto_expiry_note':'Lease is released by this transaction after post-hash verification; interruption requires manual status review before another native mutation.','rollback_reference':'New candidate directory may be quarantined; current/ remains untouched.'}
 wr(repo/LEASE,lease); print('LEASE ACTIVE:',lease['lease_id'])
 cmd=[sys.executable,'tools/medtas/drawing_system_v1.py','--repo-root',str(repo),'--spec',str(SPEC).replace('\\','/'),'--mode','review']
 cp=subprocess.run(cmd,cwd=repo,text=True,capture_output=True)
 print(cp.stdout)
 if cp.stderr: print(cp.stderr,file=sys.stderr)
 model_post=sha(model); current_post=sha(current_path)
 newdirs=[]
 if outroot.is_dir():
  newdirs=[p for p in outroot.iterdir() if p.is_dir() and p.name not in existing and p.stat().st_mtime>=start-2]
 newdirs.sort(key=lambda p:p.stat().st_mtime,reverse=True)
 candidate=newdirs[0] if newdirs else None
 sem=semantic_status(candidate) if candidate else None
 invariance=(model_pre==model_post and current_pre==current_post)
 passed=(cp.returncode==0 and candidate is not None and sem is not None and sem.startswith('PASS_') and invariance)
 lease.update({'status':'RELEASED_AFTER_PASS' if passed else ('RELEASED_AFTER_FAILED_AUTHORING' if invariance else 'HOLD_UNSAFE_POST_STATE'),'released_utc':now(),'post_source_model_sha256':model_post,'post_current_drawing_sha256':current_post,'source_model_invariant':model_pre==model_post,'current_drawing_invariant':current_pre==current_post,'candidate_root':str(candidate) if candidate else None,'candidate_semantic_status':sem})
 wr(repo/LEASE,lease)
 report={'schema':'k01.d006.v2_candidate_authoring.current.v1','generated_utc':now(),'status':'PASS_NEW_D006_V2_CANDIDATE__CURRENT_UNCHANGED' if passed else 'HOLD_D006_V2_CANDIDATE_AUTHORING','returncode':cp.returncode,'candidate_root':str(candidate) if candidate else None,'semantic_status':sem,'source_model_invariant':model_pre==model_post,'current_drawing_invariant':current_pre==current_post,'current_drawing_pre_sha256':current_pre,'current_drawing_post_sha256':current_post,'source_model_pre_sha256':model_pre,'source_model_post_sha256':model_post,'stdout_tail':cp.stdout[-4000:],'stderr_tail':cp.stderr[-2000:] if cp.stderr else ''}
 wr(repo/REPORT,report)
 if not passed:
  print(report['status']); print('LEASE STATUS:',lease['status']); return 2
 # Advance only to independent semantic/native QA. Do not publish current.
 f=rd(repo/FRONT); n=rd(repo/NEXT); g=rd(repo/GATE); blocker='D006-SEMANTIC-NATIVE-QA'; nid='K01-NA-D006-SEMANTIC-NATIVE-QA'; exp='PASS_D006_SEMANTIC_NATIVE_QA__READY_FOR_D8'
 text='Independently verify the new D006 V2 candidate against promoted spec V2, released P007 Product Definition, source-model invariance and Drawing System evidence. Read-only; do not publish current yet.'
 authority=[str(REPORT).replace('\\','/'),str(SPEC).replace('\\','/'),'control/product_definition/K01_P007_PRODUCT_DEFINITION_RELEASE_CURRENT.json','control/drawings/K01_DRAWING_SYSTEM_CURRENT.json']
 n.update({'schema':'k01.next_actions.current.v23_lifecycle','active_blocker':blocker,'current_blocker':blocker+':OPEN','next_1':text,'next_action_id':nid,'expected_closure':exp,'execution_mode':'READ_ONLY_SEMANTIC_NATIVE_VERIFICATION','authority_set':authority,'release_blockers':[{'id':blocker,'state':'OPEN','role':'Independent semantic/native QA of new V2 candidate','class':'L6_EXECUTABLE_BLOCKER'}]})
 g={'schema':'k01.active_step_gate.v7_lifecycle','state_epoch':n.get('state_epoch'),'generated_utc':now(),'step_id':'K01-STEP-D006-L6-SEMANTIC-NATIVE-QA','current_lifecycle_level':'L6','active_line':'K01-D006-RELEASE-PIPELINE','checkpoint_id':g.get('checkpoint_id'),'intent':nid,'intent_text':text,'active_blocker':blocker,'expected_closure':exp,'mutation_authorized':False,'mutation_scope':'READ_ONLY_DRAWING_SEMANTIC_NATIVE_VERIFICATION; NO NATIVE SAVE; NO CURRENT PUBLICATION','result_on_pass':exp,'required_files':authority}
 f.update({'generated_utc':now(),'active_blocker':{'id':blocker,'state':'OPEN','timing':'ACTIVE_NOW'},'next_allowed_action':{'id':nid,'text':text,'authority_set':authority,'expected_closure':exp,'execution_mode':'READ_ONLY_SEMANTIC_NATIVE_VERIFICATION'}}); f.setdefault('timing',{})['ACTIVE_NOW']=[blocker]; f['timing']['WAITING_DEPENDENCY']=['D006-D8-VISUAL-QA','D006-CURRENT-PUBLICATION']
 wr(repo/NEXT,n); wr(repo/GATE,g); wr(repo/FRONT,f)
 c=rd(repo/CENTER) if (repo/CENTER).exists() else {}; c.update({'generated_utc':now(),'active_blocker':blocker,'next_action_id':nid}); wr(repo/CENTER,c)
 subprocess.run([sys.executable,'tools/state/k01_semantic_coherence_guard_v1.py','--repo-root',str(repo),'--write-report'],cwd=repo,check=True,text=True)
 print(report['status']); print('NEXT: independent semantic/native QA; current drawing remains unchanged.')
 return 0
if __name__=='__main__': raise SystemExit(main())
