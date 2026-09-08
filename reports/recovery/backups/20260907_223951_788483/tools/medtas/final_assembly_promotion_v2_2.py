from pathlib import Path
import argparse, json, subprocess, shutil, sys, os
from v22_common import load, save, sha256_file

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); ap.add_argument('--mode',choices=['preflight','apply','verify'],default='preflight'); a=ap.parse_args()
    r=Path(a.repo_root).resolve(); base=load(r/'control/baseline/K01_FINAL_ASSEMBLY_BASELINE_v2_2.json',{}) or {}
    src=(r/base.get('source','')).resolve(); target=(r/base.get('target','')).resolve(); report=r/'reports/control/K01_FINAL_ASSEMBLY_PROMOTION_CURRENT.json'
    out={'schema':'k01.final_assembly_promotion.v2_2','mode':a.mode,'source':str(src),'target':str(target),'status':'HOLD','checks':[]}
    if not src.exists():
        out['checks'].append({'id':'PROMO-SRC-001','status':'FAIL','detail':'verified Gate04E source assembly missing'}); save(report,out); print('HOLD source assembly missing:',src); return 2
    out['checks'].append({'id':'PROMO-SRC-001','status':'PASS','sha256':sha256_file(src)})
    if a.mode=='preflight':
        out['status']='READY_FOR_SOLIDWORKS_PACK_AND_GO'; save(report,out); print('READY final assembly promotion preflight'); print(report); return 0
    exe=r/'cad_api/medtas/bin/MedtasPackAndGoPromotion.exe'
    if not exe.exists():
        out['checks'].append({'id':'PROMO-EXE-001','status':'FAIL','detail':'PackAndGo adapter not compiled; run compile step'}); save(report,out); print('HOLD adapter missing:',exe); return 3
    target.parent.mkdir(parents=True,exist_ok=True)
    cp=subprocess.run([str(exe),str(src),str(target.parent),str(r/'control/baseline/K01_FINAL_ASSEMBLY_BASELINE_v2_2.json')],text=True,capture_output=True)
    out['adapter_rc']=cp.returncode; out['stdout']=cp.stdout[-12000:]; out['stderr']=cp.stderr[-12000:]
    if cp.returncode!=0:
        out['checks'].append({'id':'PROMO-API-001','status':'FAIL','detail':'SolidWorks Pack and Go adapter failed'}); save(report,out); print('HOLD PackAndGo failed'); print(cp.stdout); print(cp.stderr); return 4
    if a.mode=='apply':
        out['status']='PROMOTED_UNVERIFIED'; save(report,out); print('PROMOTED; run verify immediately'); return 0
    # verify stable target existence + no stateful names in target folder; semantic equivalence is a separate CAD extraction gate
    expected=target
    if not expected.exists():
        out['checks'].append({'id':'PROMO-TGT-001','status':'FAIL','detail':'stable target assembly missing'}); save(report,out); print('HOLD target missing'); return 5
    bad=[]
    for p in target.parent.glob('*'):
        n=p.name.upper()
        if any(x in n for x in ['GATE','CANDIDATE','VERIFY','REFERENCE']): bad.append(p.name)
    out['checks'].append({'id':'PROMO-ID-001','status':'PASS' if not bad else 'FAIL','bad_names':bad})
    out['status']='PASS_PENDING_SEMANTIC_EQUIVALENCE' if not bad else 'HOLD'
    save(report,out); print(out['status']); print(report); return 0 if not bad else 6
if __name__=='__main__': raise SystemExit(main())
