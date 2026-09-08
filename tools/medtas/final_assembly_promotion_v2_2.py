"""Promotion repair: explicit CAD root, non-overwriting apply, read-only CAD verify."""
from pathlib import Path
import argparse, subprocess
from v22_common import load, save, sha256_file

BASE='control/baseline/K01_FINAL_ASSEMBLY_BASELINE_v2_2.json'
MANIFEST='K01_PACKANDGO_RECEIPT.json'

def paths(r,base,cad_root=None):
    cfg=load(r/'control/configuration/K01_LOCAL_PATHS.json',{}) or {}
    root=Path(cad_root or cfg.get('cad_workspace_root') or r).resolve()
    if not base.get('source') or not base.get('target'):
        raise ValueError('Baseline source/target missing')
    src=(root/base['source']).resolve(); target=(r/base['target']).resolve()
    if not src.is_relative_to(root) or not target.is_relative_to(r/'cad/final_candidate'):
        raise ValueError('Source/target outside controlled roots')
    return src,target

def verify_target(r,base,target):
    checks=[]; receipt=load(target.parent/MANIFEST,{}) or {}
    if not target.is_file(): checks.append('TARGET_MISSING')
    if receipt.get('baseline_sha256')!=sha256_file(r/BASE): checks.append('BASELINE_RECEIPT_MISSING_OR_STALE')
    files=receipt.get('files',[])
    if not files: checks.append('PACKANDGO_RECEIPT_MISSING')
    recorded=set()
    for item in files:
        name=item.get('name',''); p=target.parent/name
        if not name or Path(name).name!=name:
            checks.append('INVALID_RECEIPT_PATH'); continue
        recorded.add(name)
        if not p.is_file() or sha256_file(p)!=item.get('sha256'): checks.append('FILE_MISSING_OR_CHANGED:'+name)
    actual={p.name for p in target.parent.iterdir() if p.is_file() and p.name!=MANIFEST and not p.name.startswith('~$')} if target.parent.is_dir() else set()
    if actual!=recorded: checks.append('DESTINATION_INVENTORY_CHANGED')
    for name in actual:
        if any(x in name.upper() for x in ('GATE','CANDIDATE','VERIFY','REFERENCE')): checks.append('UNMIGRATED_IDENTITY:'+name)
    return checks

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); ap.add_argument('--cad-root'); ap.add_argument('--mode',choices=['preflight','apply','verify'],default='preflight'); a=ap.parse_args()
    r=Path(a.repo_root).resolve(); report=r/'reports/control/K01_FINAL_ASSEMBLY_PROMOTION_CURRENT.json'
    out={'schema':'k01.final_assembly_promotion.v2_2_repair1','mode':a.mode,'status':'HOLD','checks':[]}
    try:
        base=load(r/BASE,{}) or {}; src,target=paths(r,base,a.cad_root)
        out.update(source=str(src),target=str(target))
        if a.mode=='verify':
            # No COM, no executable launch, no mkdir/copy/save of native CAD.
            out['checks']=verify_target(r,base,target)
            if not out['checks']: out['status']='PASS_PENDING_SEMANTIC_EQUIVALENCE'
        else:
            if not src.is_file(): out['checks'].append('SOURCE_MISSING: no automatic historical/stable substitution')
            if target.parent.exists() and any(target.parent.iterdir()): out['checks'].append('TARGET_NOT_EMPTY: retain existing candidate')
            exe=r/'cad_api/medtas/bin/MedtasPackAndGoPromotion.exe'
            cs=r/'cad_api/medtas/MedtasPackAndGoPromotion.cs'
            build=load(exe.parent/'MedtasPackAndGoPromotion.build.json',{}) or {}
            if not exe.is_file() or build.get('source_sha256')!=sha256_file(cs) or build.get('exe_sha256')!=sha256_file(exe): out['checks'].append('ADAPTER_MISSING_OR_STALE')
            if not out['checks']:
                out['source_sha256']=sha256_file(src)
                if a.mode=='preflight': out['status']='READY_FOR_PACKANDGO_DEPENDENCY_CHECK'
                else:
                    cp=subprocess.run([str(exe),str(src),str(target.parent),str(r/BASE)],text=True,capture_output=True,timeout=300)
                    out.update(adapter_rc=cp.returncode,stdout=cp.stdout,stderr=cp.stderr)
                    if cp.returncode or not target.is_file(): out['checks'].append('PACKANDGO_FAILED: retain partial output for investigation')
                    else:
                        files=[{'name':p.name,'sha256':sha256_file(p)} for p in sorted(target.parent.iterdir()) if p.is_file()]
                        save(target.parent/MANIFEST,{'baseline_sha256':sha256_file(r/BASE),'source_sha256':out['source_sha256'],'source':str(src),'files':files})
                        out['status']='PROMOTED_UNVERIFIED'
    except Exception as exc: out['checks'].append(type(exc).__name__+': '+str(exc))
    save(report,out); print(out['status']); [print(' -',x) for x in out['checks']]; print(report)
    return 2 if out['status']=='HOLD' else 0
if __name__=='__main__': raise SystemExit(main())
