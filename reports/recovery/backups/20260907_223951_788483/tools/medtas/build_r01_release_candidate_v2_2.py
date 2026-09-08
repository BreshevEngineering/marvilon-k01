from pathlib import Path
import argparse, shutil, zipfile, json, time
from v22_common import load,save,sha256_file
REQUIRED=[
 ('final_assembly','reports/control/K01_FINAL_ASSEMBLY_PROMOTION_CURRENT.json',{'PASS_PENDING_SEMANTIC_EQUIVALENCE','PASS'}),
 ('technical_filter','reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json',{'PASS'}),
 ('ebom','reports/bom/current/K01_EBOM_A001_CURRENT.json',{'PASS'}),
 ('structure','reports/control/K01_PROJECT_STRUCTURE_AUDIT_CURRENT.json',{'PASS','PASS_WITH_LIMITATIONS'}),
 ('git','reports/control/K01_GIT_AUDIT_CURRENT.json',{'PASS','PASS_WITH_LIMITATIONS'}),
]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve(); blockers=[]; checks=[]
 for name,rel,ok in REQUIRED:
  d=load(r/rel,{}) or {}; st=d.get('status','MISSING'); checks.append({'id':name,'path':rel,'status':st});
  if st not in ok: blockers.append(name+':'+st)
 # drawing and requirements are release-critical and must explicitly pass before immutable R01
 for name,rels in [('drawing',['reports/drawing/current/K01_DRAWING_QA_CURRENT.json','reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json']),('requirements',['reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json'])]:
  found=None
  for rel in rels:
   if (r/rel).exists(): found=(rel,load(r/rel,{}) or {}); break
  st=(found[1].get('status') or found[1].get('verdict')) if found else 'MISSING'; checks.append({'id':name,'path':found[0] if found else rels[0],'status':st})
  if st not in {'PASS','RELEASE_READY'}: blockers.append(name+':'+str(st))
 rep={'schema':'k01.r01_release_candidate.v2_2','status':'HOLD' if blockers else 'READY_TO_BUILD','blockers':blockers,'checks':checks}
 rp=save(r/'reports/control/K01_R01_RELEASE_READINESS_CURRENT.json',rep); print(rep['status']); [print(' -',x) for x in blockers]
 if blockers: return 2
 out=r/'release/R01'; out.mkdir(parents=True,exist_ok=True); manifest=[]
 candidates=[r/'cad/final_candidate/R01',r/'reports/drawing/current',r/'reports/bom/current',r/'reports/control/K01_CALCULATION_EVIDENCE_INDEX_CURRENT.json',r/'control/requirements/requirements.json',r/'control/product/parts.json']
 for c in candidates:
  if not c.exists(): continue
  files=[c] if c.is_file() else [p for p in c.rglob('*') if p.is_file() and not p.name.startswith('~$')]
  for p in files:
   rel=p.relative_to(r); dest=out/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest); manifest.append({'path':str(rel).replace('\\','/'),'sha256':sha256_file(p),'size':p.stat().st_size})
 save(out/'K01_R01_MANIFEST.json',{'schema':'k01.release_manifest.v2_2','immutable_candidate':True,'files':manifest})
 print('R01 candidate built files=',len(manifest)); return 0
if __name__=='__main__': raise SystemExit(main())
