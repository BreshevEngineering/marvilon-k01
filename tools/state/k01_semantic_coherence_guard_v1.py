from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
P={
 'epoch':Path('control/state/K01_STATE_EPOCH_CURRENT.json'),
 'temporal':Path('reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json'),
 'frontier':Path('control/state/K01_COMPLETION_FRONTIER_CURRENT.json'),
 'goal':Path('control/project/K01_GOAL_LOCK_CURRENT.json'),
 'next':Path('control/project/K01_NEXT_ACTIONS_CURRENT.json'),
 'gate':Path('control/project/K01_ACTIVE_STEP_GATE.json'),
 'report':Path('reports/control/K01_SEMANTIC_COHERENCE_CURRENT.json')}

def rd(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def hold(issues,rule,detail): issues.append({'rule':rule,'detail':detail})

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default=str(R));ap.add_argument('--write-report',action='store_true');a=ap.parse_args();repo=Path(a.repo_root)
 x={};issues=[]
 for k,r in P.items():
  if k=='report':continue
  q=repo/r
  if not q.exists():hold(issues,'REQUIRED_STATE_MISSING',str(r));continue
  x[k]=rd(q)
 epoch=x.get('epoch',{}).get('state_epoch')
 t=json.dumps(x.get('temporal',{}),ensure_ascii=False).upper()
 if 'PASS_TEMPORAL_COHERENCE' not in t or 'HOLD_TEMPORAL_COHERENCE' in t:hold(issues,'TEMPORAL_NOT_PASS','Temporal coherence must PASS.')

 f=x.get('frontier',{});g=x.get('goal',{});n=x.get('next',{});gate=x.get('gate',{})
 if f.get('state_epoch')!=epoch:hold(issues,'INV-03',f"Completion Frontier epoch {f.get('state_epoch')!r} != global epoch {epoch!r}.")
 if g.get('state_epoch')!=epoch:hold(issues,'INV-03',f"Goal Lock epoch {g.get('state_epoch')!r} != global epoch {epoch!r}.")
 if n.get('state_epoch')!=epoch:hold(issues,'INV-03',f"Next Actions epoch {n.get('state_epoch')!r} != global epoch {epoch!r}.")
 if gate.get('state_epoch')!=epoch:hold(issues,'INV-03',f"Active Step epoch {gate.get('state_epoch')!r} != global epoch {epoch!r}.")
 level=f.get('current_lifecycle_level');deliver=f.get('current_deliverable');active=f.get('active_engineering_object')
 ab=f.get('active_blocker');blocker=ab.get('id') if isinstance(ab,dict) else ab
 nxt=f.get('next_allowed_action') or {};nid=nxt.get('id');exp=nxt.get('expected_closure');mode=nxt.get('execution_mode')
 timing=f.get('timing') or {}
 if not level:hold(issues,'INV-03','Completion Frontier missing lifecycle level.')
 if not deliver:hold(issues,'INV-04','Completion Frontier missing active deliverable.')
 if not active:hold(issues,'INV-04','Completion Frontier missing active engineering object.')
 if f.get('wip_limit')!=1:hold(issues,'INV-05',f"WIP limit {f.get('wip_limit')!r} != 1.")
 if len(timing.get('ACTIVE_NOW') or [])!=1:hold(issues,'INV-05',f"Expected exactly one ACTIVE_NOW; got {timing.get('ACTIVE_NOW')!r}.")
 if not blocker:hold(issues,'INV-01','Active blocker missing.')
 if not nid:hold(issues,'INV-11','NEXT id missing.')
 if not exp:hold(issues,'INV-11','Expected closure missing.')
 if g.get('current_deliverable')!=deliver:hold(issues,'INV-04',f"Goal Lock deliverable {g.get('current_deliverable')!r} != frontier {deliver!r}.")
 if g.get('current_lifecycle_level') and g.get('current_lifecycle_level')!=level:hold(issues,'INV-03','Goal Lock lifecycle differs from frontier.')
 if g.get('active_engineering_object') and g.get('active_engineering_object')!=active:hold(issues,'INV-04','Goal Lock active engineering object differs from frontier.')
 if g.get('next_action_id') and g.get('next_action_id')!=nid:hold(issues,'INV-01/11',f"Goal Lock NEXT {g.get('next_action_id')!r} != frontier {nid!r}.")
 fdep=f.get('active_dependency')
 if fdep and g.get('active_dependency') and g.get('active_dependency')!=fdep:hold(issues,'INV-04','Goal Lock active dependency differs from frontier.')

 if n.get('next_action_id')!=nid:hold(issues,'INV-01/11',f"Next Actions id {n.get('next_action_id')!r} != frontier {nid!r}.")
 if n.get('active_blocker')!=blocker:hold(issues,'INV-01',f"Next Actions blocker {n.get('active_blocker')!r} != frontier {blocker!r}.")
 if n.get('expected_closure')!=exp:hold(issues,'INV-11','Next Actions expected_closure differs from frontier.')
 if n.get('current_lifecycle_level')!=level:hold(issues,'INV-03','Next Actions lifecycle differs from frontier.')
 if n.get('current_deliverable')!=deliver:hold(issues,'INV-04','Next Actions deliverable differs from frontier.')
 if gate.get('intent')!=nid:hold(issues,'INV-01',f"Active Step intent {gate.get('intent')!r} != frontier {nid!r}.")
 if gate.get('active_blocker')!=blocker:hold(issues,'INV-01','Active Step blocker differs from frontier.')
 if gate.get('expected_closure')!=exp:hold(issues,'INV-11','Active Step expected_closure differs from frontier.')
 if gate.get('current_lifecycle_level')!=level:hold(issues,'INV-03','Active Step lifecycle differs from frontier.')

 # Closed-item protection: authority may explicitly list closed ids/tokens.
 closed=set(str(x).lower() for x in (f.get('closed_blocker_ids') or []))
 blob=(str(n.get('next_action_id',''))+' '+str(n.get('next_1',''))+' '+str(blocker)).lower()
 for c in closed:
  if c and c in blob:hold(issues,'INV-02',f"NEXT references closed blocker token {c!r}.")

 read_only=str(mode or '').upper().startswith('READ_ONLY')
 if read_only and gate.get('mutation_authorized') is not False:hold(issues,'INV-10','Read-only frontier requires mutation_authorized=false.')
 if gate.get('mutation_authorized') is True and not gate.get('mutation_scope'):hold(issues,'INV-10','Authorized mutation requires explicit mutation_scope.')

 o={'schema':'k01.semantic_coherence.current.v4_global_frontier','generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
    'state_epoch':epoch,
    'status':'PASS_SEMANTIC_COHERENCE' if not issues else 'HOLD_SEMANTIC_COHERENCE',
    'current_lifecycle_level':level,'current_deliverable':deliver,'active_engineering_object':active,
    'active_blocker':blocker,'next_action_id':nid,'expected_closure':exp,'issues':issues}
 if a.write_report:wr(repo/P['report'],o)
 print(o['status'],'issues=',len(issues))
 for i in issues:print('HOLD:',json.dumps(i,ensure_ascii=False))
 if not issues:
  print('FRONTIER:',level,'/',deliver)
  print('OBJECT:',active)
  print('BLOCKER:',blocker)
  print('NEXT:',n.get('next_1'))
  print('EXPECTED:',exp)
 return 0 if not issues else 2
if __name__=='__main__':raise SystemExit(main())
