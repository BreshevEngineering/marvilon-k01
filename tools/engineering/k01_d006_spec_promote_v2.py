from __future__ import annotations
import argparse, copy, datetime as dt, hashlib, json, shutil
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01"); L=Path(r"D:\BreshevEngineering\K01_local")
RC=Path('control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_RELEASE_CANDIDATE.json')
V1=Path('control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v1.json')
V2=Path('control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v2.json')
REG=Path('control/drawings/K01_DRAWING_REGISTRY_CURRENT.json')
PROM=Path('control/drawings/K01_D006_SPEC_PROMOTION_CURRENT.json')
FRONT=Path('control/state/K01_COMPLETION_FRONTIER_CURRENT.json'); NEXT=Path('control/project/K01_NEXT_ACTIONS_CURRENT.json'); GATE=Path('control/project/K01_ACTIVE_STEP_GATE.json'); CENTER=Path('control/center/K01_CENTER_INPUT_CURRENT.json')

def rd(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def canon(o): return hashlib.sha256(json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()
def sha(p): h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def backup(repo,local,rels):
 out=local/'backups'/('D006_SPEC_PROMOTION_'+dt.datetime.now().strftime('%Y%m%d_%H%M%S'))
 for r in rels:
  p=repo/r
  if p.exists(): d=out/r; d.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,d)
 return out

def by_id(items,idv):
 for x in items:
  if isinstance(x,dict) and x.get('id')==idv:return x
 return None

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=str(R)); ap.add_argument('--local-root',default=str(L)); a=ap.parse_args(); repo=Path(a.repo_root); local=Path(a.local_root)
 for rel in (RC,V1,REG,FRONT,NEXT,GATE):
  if not (repo/rel).exists(): raise SystemExit('HOLD: missing '+str(rel))
 rc=rd(repo/RC); v1=rd(repo/V1); reg=rd(repo/REG); f=rd(repo/FRONT); n=rd(repo/NEXT); g=rd(repo/GATE)
 if n.get('next_action_id')!='K01-NA-D006-SPEC-PROMOTION-BINDING': raise SystemExit('HOLD: completion frontier is not at D006 spec promotion.')
 snap=rc.get('source_spec_snapshot')
 if not isinstance(snap,dict) or canon(v1)!=canon(snap): raise SystemExit('HOLD: V1 source spec drifted since release-candidate compilation. Recompile/review; do not merge blindly.')
 if rc.get('source_spec')!=str(V1).replace('\\','/'): raise SystemExit('HOLD: release-candidate source_spec does not identify V1.')

 b=backup(repo,local,[V2,REG,PROM,FRONT,NEXT,GATE,CENTER]); print('BACKUP:',b)
 v2=copy.deepcopy(v1)
 v2['schema']='k01.drawing_system_spec.v1'
 v2['status']='RELEASE_CANDIDATE_AUTHORING'
 v2['release_basis']=['EDR-025','EDR-027','EDR-028','EDR-029','EDR-030','EDR-032','EDR-033','EDR-035','EDR-036','EDR-037']
 v2['lifecycle']={'current_level':'L6','product_definition':'READY','drawing_tpd':'CANDIDATE','physical_qualification':'OPEN_L8','release':'HOLD'}
 chars=v2.setdefault('characteristics',[])
 s=by_id(chars,'SURFACE_J2')
 if not s: raise SystemExit('HOLD: V1 lacks SURFACE_J2 characteristic.')
 s.update({'spec':'Ra ≤ 0.8 µm on J2 Datum-A seal-contact face only','source':'EDR-037','state':'CONTROLLED'})
 c12=by_id(chars,'C12')
 c12data={'id':'C12','interface':'J2','role':'assembled J2 quantitative leak acceptance','spec':'ASSEMBLED J2: q_He ≤ 1.0e-5 mbar·L/s at |Δp| = 0.20 bar, 20 ±5 °C; both directions unless equivalence is justified','source':'EDR-035','state':'CONTROLLED_INTERFACE_ACCEPTANCE'}
 if c12:c12.update(c12data)
 else:chars.append(c12data)
 ann=v2.setdefault('annotations',[])
 ra=by_id(ann,'D006-J2-RA08')
 if not ra: raise SystemExit('HOLD: V1 lacks D006-J2-RA08 semantic annotation.')
 ra['state']='CONTROLLED'
 note=by_id(ann,'D006-C12-J2-LEAK')
 note_data={'id':'D006-C12-J2-LEAK','kind':'NOTE','view':'SECTION','text':'J2 ASSEMBLY ACCEPTANCE: qHe ≤ 1×10^-5 mbar·L/s @ |Δp|=0.20 bar, 20±5°C; TEST PER EDR-035.','state':'CONTROLLED_INTERFACE_ACCEPTANCE','x_m':0.17,'y_m':0.055}
 if note:note.update(note_data)
 else:ann.append(note_data)
 insp=by_id(ann,'D006-INSPECTION-REF')
 insp_data={'id':'D006-INSPECTION-REF','kind':'NOTE','view':'SECTION','text':'CONTROLLED CHARACTERISTICS: INSPECT PER K01-P-007 INSPECTION PLAN. C12 IS ASSEMBLED-J2 ACCEPTANCE.','state':'CONTROLLED','x_m':0.25,'y_m':0.055}
 if insp:insp.update(insp_data)
 else:ann.append(insp_data)
 notes=v2.setdefault('review_notes',[])
 for note_text in [
  'O-RING GLAND IS ON P003; K01-D-006 DEFINES P007 ONLY.',
  'C12 IS AN ASSEMBLED-J2 ACCEPTANCE; DO NOT INTERPRET qHe AS A BARE-P007 PART LEAK TEST.'
 ]:
  if note_text not in notes:notes.append(note_text)
 v2['carry_forward_qualification']=['C12 physical leak qualification','J2 50-cycle service qualification','P007 thin-wall/runout/critical-GPS FAI capability','purchased seal/screw incoming qualification']
 v2['trace_dispositions']={'EDR-036_FASTENER':'ASSEMBLY_BOM_SERVICE_AUTHORITY__NOT_DIRECT_P007_PART_CHARACTERISTIC','inspection_plan':'control/inspection/K01_P007_INSPECTION_PLAN_CURRENT.json'}
 wr(repo/V2,v2)
 d=(reg.get('drawings') or {}).get('K01-D-006')
 if not isinstance(d,dict): raise SystemExit('HOLD: D006 missing from Drawing Registry.')
 d['spec']=str(V2).replace('\\','/')
 d['runner']='RUN_K01_D006_DRAWING_SYSTEM_V2.cmd'
 d['status']='SPEC_V2_PROMOTED__NATIVE_CANDIDATE_AUTHORING_PENDING'
 wr(repo/REG,reg)
 prom={'schema':'k01.d006.spec_promotion.current.v1','generated_utc':now(),'status':'PASS_D006_SPEC_PROMOTED__READY_FOR_NATIVE_CANDIDATE_LEASE','drawing_id':'K01-D-006','source_spec':str(V1).replace('\\','/'),'source_spec_sha256':sha(repo/V1),'release_candidate_wrapper':str(RC).replace('\\','/'),'release_candidate_wrapper_sha256':sha(repo/RC),'promoted_spec':str(V2).replace('\\','/'),'promoted_spec_sha256':sha(repo/V2),'registry_spec':d['spec'],'runner':d['runner'],'adjudication':{'SURFACE_J2':'EDR-037 promoted to CONTROLLED','C12':'projected as assembled-J2 interface acceptance note','EDR-036_FASTENER':'trace only; not a direct P007 part characteristic','physical_qualification':'carried to L8'}}
 wr(repo/PROM,prom)

 blocker='D006-NATIVE-MUTATION-LEASE'; nid='K01-NA-D006-NATIVE-MUTATION-LEASE'; exp='LEASE_ACTIVE_FOR_D006_CANDIDATE_AUTHORING'
 text='Acquire a native-mutation lease for creation of a NEW D006 V2 candidate. Current D006 and P007 source model must remain hash-invariant.'
 authority=[str(PROM).replace('\\','/'),str(V2).replace('\\','/'),'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json','control/drawings/K01_DRAWING_REGISTRY_CURRENT.json']
 n.update({'schema':'k01.next_actions.current.v22_lifecycle','current_lifecycle_level':'L6','active_dependency':'K01-D006 RELEASE PIPELINE','active_engineering_object':'K01-D-006','active_line':'K01-D006 RELEASE PIPELINE','active_blocker':blocker,'current_blocker':blocker+':OPEN','next_1':text,'next_action_id':nid,'expected_closure':exp,'execution_mode':'NATIVE_MUTATION_LEASE_REQUIRED','authority_set':authority,'release_blockers':[{'id':blocker,'state':'OPEN','role':'Acquire exclusive lease before SolidWorks creates a new candidate','class':'L6_EXECUTABLE_BLOCKER'}]})
 g={'schema':'k01.active_step_gate.v6_lifecycle','state_epoch':n.get('state_epoch'),'generated_utc':now(),'step_id':'K01-STEP-D006-L6-NATIVE-LEASE','current_lifecycle_level':'L6','active_line':'K01-D006-RELEASE-PIPELINE','checkpoint_id':g.get('checkpoint_id'),'intent':nid,'intent_text':text,'active_blocker':blocker,'expected_closure':exp,'mutation_authorized':False,'mutation_scope':'NO NATIVE SAVE UNTIL EXCLUSIVE LEASE IS ACTIVE','result_on_pass':exp,'required_files':authority}
 f.update({'generated_utc':now(),'active_blocker':{'id':blocker,'state':'OPEN','timing':'ACTIVE_NOW'},'next_allowed_action':{'id':nid,'text':text,'authority_set':authority,'expected_closure':exp,'execution_mode':'NATIVE_MUTATION_LEASE_REQUIRED'}}); f.setdefault('timing',{})['ACTIVE_NOW']=[blocker]; f['timing']['WAITING_DEPENDENCY']=['D006-CANDIDATE-AUTHORING','D006-SEMANTIC-NATIVE-QA','D006-D8-VISUAL-QA']
 wr(repo/NEXT,n); wr(repo/GATE,g); wr(repo/FRONT,f)
 c=rd(repo/CENTER) if (repo/CENTER).exists() else {}; c.update({'generated_utc':now(),'current_lifecycle_level':'L6','active_blocker':blocker,'next_action_id':nid}); wr(repo/CENTER,c)
 print('PASS: D006 runtime spec V2 promoted.')
 print('PROMOTED:',repo/V2)
 print('NEXT: acquire native mutation lease; then create NEW candidate only.')
 return 0
if __name__=='__main__': raise SystemExit(main())
