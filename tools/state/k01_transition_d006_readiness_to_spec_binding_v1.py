from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
REP=Path('reports/drawing/current/K01-D-006_RELEASE_READINESS_CURRENT.json')
FRONT=Path('control/state/K01_COMPLETION_FRONTIER_CURRENT.json'); NEXT=Path('control/project/K01_NEXT_ACTIONS_CURRENT.json'); GATE=Path('control/project/K01_ACTIVE_STEP_GATE.json'); CENTER=Path('control/center/K01_CENTER_INPUT_CURRENT.json')
def rd(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=str(R)); a=ap.parse_args(); repo=Path(a.repo_root)
 if not (repo/REP).exists(): raise SystemExit('HOLD: release-readiness report missing')
 rep=rd(repo/REP)
 if rep.get('status')!='PASS_D006_RELEASE_READINESS__SPEC_PROMOTION_BINDING_REQUIRED': raise SystemExit('HOLD: release-readiness review did not identify controlled spec promotion as the next blocker.')
 n0=rd(repo/NEXT); g0=rd(repo/GATE); f0=rd(repo/FRONT); epoch=n0.get('state_epoch'); blocker='D006-SPEC-PROMOTION-BINDING'; nid='K01-NA-D006-SPEC-PROMOTION-BINDING'; exp='PASS_D006_SPEC_PROMOTED__READY_FOR_NATIVE_CANDIDATE_LEASE'
 text='Promote/bind a Drawing System-compatible K01-D-006 runtime spec from the compiled release-candidate wrapper. No native CAD/drawing mutation.'
 authority=['reports/drawing/current/K01-D-006_RELEASE_READINESS_CURRENT.json','control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_RELEASE_CANDIDATE.json','control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v1.json','control/drawings/K01_DRAWING_REGISTRY_CURRENT.json']
 n=dict(n0); n.update({'schema':'k01.next_actions.current.v21_lifecycle','current_lifecycle_level':'L6','active_dependency':'K01-D006 RELEASE PIPELINE','active_engineering_object':'K01-D-006','active_line':'K01-D006 RELEASE PIPELINE','active_blocker':blocker,'current_blocker':blocker+':OPEN','next_1':text,'next_action_id':nid,'expected_closure':exp,'execution_mode':'CONTROL_REPO_SPEC_PROMOTION_NO_NATIVE_MUTATION','authority_set':authority,'release_blockers':[{'id':blocker,'state':'OPEN','role':'Promote final D006 Drawing System runtime spec','class':'L6_EXECUTABLE_BLOCKER'}]})
 g={'schema':'k01.active_step_gate.v5_lifecycle','state_epoch':epoch,'generated_utc':now(),'step_id':'K01-STEP-D006-L6-SPEC-PROMOTION','current_lifecycle_level':'L6','active_line':'K01-D006-RELEASE-PIPELINE','checkpoint_id':g0.get('checkpoint_id'),'intent':nid,'intent_text':text,'active_blocker':blocker,'expected_closure':exp,'mutation_authorized':True,'mutation_scope':'CONTROL_REPOSITORY_DRAWING_SPEC_AND_REGISTRY_ONLY; NO NATIVE SAVE','result_on_pass':exp,'required_files':authority,'impact_declarations':{'engineering_values':'No new value may be invented; promotion consumes EDR-035/037 and existing release-candidate wrapper.','native_cad':'No native CAD/drawing write authorized.','drawing_system':'Frozen subsystem; only spec input is promoted.','center':'Projection only.'}}
 f=dict(f0); f.update({'generated_utc':now(),'active_blocker':{'id':blocker,'state':'OPEN','timing':'ACTIVE_NOW'},'next_allowed_action':{'id':nid,'text':text,'authority_set':authority,'expected_closure':exp,'execution_mode':'CONTROL_REPO_SPEC_PROMOTION_NO_NATIVE_MUTATION'}})
 timing=f.setdefault('timing',{}); timing['ACTIVE_NOW']=[blocker]; timing['WAITING_DEPENDENCY']=['D006-NATIVE-MUTATION-LEASE','D006-CANDIDATE-AUTHORING','D006-SEMANTIC-NATIVE-QA','D006-D8-VISUAL-QA']
 wr(repo/NEXT,n); wr(repo/GATE,g); wr(repo/FRONT,f)
 c=rd(repo/CENTER) if (repo/CENTER).exists() else {}; c.update({'generated_utc':now(),'active_blocker':blocker,'next_action_id':nid,'current_lifecycle_level':'L6'}); wr(repo/CENTER,c)
 subprocess.run([sys.executable,'tools/state/k01_semantic_coherence_guard_v1.py','--repo-root',str(repo),'--write-report'],cwd=repo,check=True,text=True)
 print('PASS: D006 release-readiness review closed.')
 print('NEXT: D006-SPEC-PROMOTION-BINDING')
 return 0
if __name__=='__main__': raise SystemExit(main())
