from __future__ import annotations
import argparse,json,subprocess,sys,time
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def role_key(m):
    out={}
    for k,v in (m or {}).items():
        if k=='CONTACT':out[k]=v;continue
        out[k]=sorted((x.get('part_no'),x.get('face_signature')) for x in (v or []))
    return out

def run_bind(root):
    cp=subprocess.run([sys.executable,str(root/'tools/medtas/auto_bind_structural_face_roles_v1_7.py'),'--repo-root',str(root)],cwd=str(root),text=True,capture_output=True,timeout=240)
    return cp

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();out=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_QUAL_P006_v1_7.json';fmp=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json';issues=[];runs=[]
    cp1=run_bind(root);fm1=load(fmp) if fmp.exists() else {};runs.append({'stage':'BEFORE_REBUILD','return_code':cp1.returncode,'role_map':role_key(fm1.get('confirmed_role_map'))})
    if cp1.returncode:issues.append('FACE-QUAL-BIND-001: baseline automatic study binding did not PASS')
    # No parameter or geometry write. ForceRebuild3 only rebuilds the active in-memory model.
    try:
        import win32com.client
        sw=win32com.client.GetActiveObject('SldWorks.Application');model=sw.ActiveDoc
        if model is None:raise RuntimeError('no active SOLIDWORKS document')
        model.ForceRebuild3(False)
    except Exception as e:issues.append('FACE-QUAL-REBUILD-001:'+str(e))
    cp2=run_bind(root);fm2=load(fmp) if fmp.exists() else {};runs.append({'stage':'AFTER_NOOP_REBUILD','return_code':cp2.returncode,'role_map':role_key(fm2.get('confirmed_role_map'))})
    if cp2.returncode:issues.append('FACE-QUAL-BIND-002: post-rebuild automatic study binding did not PASS')
    if runs[0]['role_map']!=runs[1]['role_map']:issues.append('FACE-QUAL-IDENTITY-001: semantic role mapping changed after no-op rebuild')
    amb=fm2.get('signature_ambiguities',[]) or []
    used={x[1] for k,v in runs[1]['role_map'].items() if k!='CONTACT' for x in v}
    if any(x in used for x in amb):issues.append('FACE-QUAL-AMBIG-001: a confirmed role maps to a non-unique signature')
    verdict='PASS' if not issues else 'HOLD';payload={'schema':'k01.structural_face_map_qualification.p006.v1_7','verdict':verdict,'test':'automatic Simulation entity mapping before/after SOLIDWORKS ForceRebuild3(false); no CAD save or parameter write','runs':runs,'issues':issues,'ambiguity_rule':'zero or multiple semantic matches => HOLD; never choose the first candidate'};dump(out,payload);register_build(root,'K01.STRUCT.FACE_MAP.QUAL.P006',{'tool':'qualify_structural_face_map_v1_7.py'});register_verify(root,'K01.STRUCT.FACE_MAP.QUAL.P006',verdict,metrics={'mapping_equal':runs[0]['role_map']==runs[1]['role_map'],'ambiguous_signature_count':len(amb)},limitations=issues)
    print(verdict,'structural face-map qualification');[print(' -',x) for x in issues];return 0 if verdict=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
