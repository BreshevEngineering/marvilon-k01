from __future__ import annotations
import argparse, datetime as dt, hashlib, json
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
PD=Path('control/product_definition/K01_P007_PRODUCT_DEFINITION_RELEASE_CURRENT.json')
RC=Path('control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_RELEASE_CANDIDATE.json')
REG=Path('control/drawings/K01_DRAWING_REGISTRY_CURRENT.json')
DC=Path('reports/control/K01_DRAWING_CONTROL_CURRENT.json')
REPORT=Path('reports/drawing/current/K01-D-006_RELEASE_READINESS_CURRENT.json')

def rd(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def wr(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def canon(o): return hashlib.sha256(json.dumps(o,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()
def sha(p): h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default=str(R)); a=ap.parse_args(); repo=Path(a.repo_root)
 issues=[]; facts={}; blockers=[]
 for rel in (PD,RC,REG,DC):
  if not (repo/rel).exists(): issues.append('MISSING:'+str(rel))
 if issues:
  out={'schema':'k01.d006.release_readiness.v1','generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'HOLD_REQUIRED_AUTHORITY_MISSING','issues':issues}
  wr(repo/REPORT,out); print(out['status']); [print('HOLD:',x) for x in issues]; return 2
 pd=rd(repo/PD); rc=rd(repo/RC); reg=rd(repo/REG); dc=rd(repo/DC)
 facts['p007_ready']=pd.get('product_definition_ready') is True and pd.get('status')=='READY_FOR_D006_RELEASE_PIPELINE'
 facts['release_candidate_spec_ready']='RELEASE_CANDIDATE_SPEC_READY' in str(rc.get('status',''))
 source_rel=Path(rc.get('source_spec',''))
 source=repo/source_rel
 facts['source_spec']=str(source_rel).replace('\\','/')
 facts['source_spec_exists']=source.is_file()
 if not facts['source_spec_exists']: issues.append('D006 source spec referenced by release-candidate wrapper is missing.')
 else:
  current=rd(source); snap=rc.get('source_spec_snapshot')
  facts['source_spec_sha256']=sha(source)
  facts['source_snapshot_canonical_match']=isinstance(snap,dict) and canon(current)==canon(snap)
  if not facts['source_snapshot_canonical_match']: issues.append('SOURCE_SPEC_DRIFT: current source spec differs from the snapshot used to compile the release-candidate spec.')
 dreg=(reg.get('drawings') or {}).get('K01-D-006') or {}
 dctl=(dc.get('drawings') or {}).get('K01-D-006') or {}
 facts['registry_spec']=dreg.get('spec')
 facts['drawing_control_spec']=dctl.get('spec')
 facts['current_drawing_status']=((dctl.get('current') or {}).get('status'))
 facts['current_drawing_path']=((((dctl.get('current') or {}).get('artifacts') or {}).get('drawing') or {}).get('path'))
 if not facts['p007_ready']: issues.append('P007 Product Definition not READY.')
 if not facts['release_candidate_spec_ready']: issues.append('Final D006 release-candidate spec wrapper not READY.')
 if facts['registry_spec']!=facts['source_spec']: issues.append('Registry source spec does not match compiled release-candidate source_spec.')
 if facts['drawing_control_spec']!=facts['source_spec']: issues.append('Drawing Control source spec does not match compiled release-candidate source_spec.')
 mandatory=rc.get('mandatory_release_additions') or {}
 for k in ('SURFACE_J2','C12','inspection_reference','material'):
  if k not in mandatory: issues.append('Release-candidate wrapper missing mandatory addition '+k)
 # Fastener is assembly/service authority, not a direct P007 manufacturing-drawing characteristic.
 facts['fastener_note_disposition']='TRACE_ONLY__ASSEMBLY_BOM_SERVICE_AUTHORITY__NOT_DIRECT_P007_PART_CHARACTERISTIC'
 if not issues:
  blockers.append({'id':'D006-SPEC-PROMOTION-BINDING','state':'OPEN','class':'L6_EXECUTABLE_BLOCKER','reason':'The compiled final release-candidate wrapper has not yet been converted/promoted into the Drawing System runtime spec authority. Registry/runner still consume the prior source spec.'})
 status='PASS_D006_RELEASE_READINESS__SPEC_PROMOTION_BINDING_REQUIRED' if not issues else 'HOLD_D006_RELEASE_READINESS'
 out={'schema':'k01.d006.release_readiness.v1','generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':status,'drawing_id':'K01-D-006','part_id':'K01-P-007','facts':facts,'blocking_issues':issues,'next_blockers':blockers,'carry_forward_l8':['C12 physical leak qualification','J2 50-cycle service qualification','P007 FAI/process capability','incoming seal/screw qualification'],'release_hold_later':['D8 visual QA','title-block/projection release quality','L8 physical/process qualification','L9 configuration/release approval'],'next':'Promote/bind a Drawing System-compatible D006 spec from the compiled release-candidate wrapper; do not rebuild native drawing before promotion.'}
 wr(repo/REPORT,out)
 print(status)
 print('SOURCE SPEC:',facts.get('source_spec'))
 print('REGISTRY SPEC:',facts.get('registry_spec'))
 print('DRAWING CONTROL SPEC:',facts.get('drawing_control_spec'))
 if issues:
  for x in issues: print('HOLD:',x)
  return 2
 print('BLOCKER: D006-SPEC-PROMOTION-BINDING')
 return 0
if __name__=='__main__': raise SystemExit(main())
