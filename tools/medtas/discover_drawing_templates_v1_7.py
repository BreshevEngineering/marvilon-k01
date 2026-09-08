from __future__ import annotations
import argparse,json,os
from pathlib import Path
from medtas_v16_common import load,dump

def roots():
    out=[]
    for k in ('ProgramData','ProgramFiles','ProgramFiles(x86)','APPDATA','LOCALAPPDATA','USERPROFILE'):
        v=os.environ.get(k)
        if v:out.append(Path(v))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--apply',action='store_true');a=ap.parse_args();r=Path(a.repo_root).resolve();bp=r/'control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json';b=load(bp) if bp.exists() else {'schema':'k01.drawing_generation_binding.v1_7'}
    found=[];seen=set()
    for root in roots():
        if not root.exists():continue
        # Limit to directories with SOLIDWORKS/solidworks/template in the path to avoid scanning the whole drive indiscriminately.
        try:
            for p in root.rglob('*.drwdot'):
                sp=str(p.resolve());low=sp.lower()
                if 'solidworks' not in low and 'template' not in low:continue
                if sp not in seen:seen.add(sp);found.append(p.resolve())
                if len(found)>=200:break
        except Exception:pass
        if len(found)>=200:break
    # Prefer ISO/A4-like template names but never choose when more than one candidate remains.
    preferred=[p for p in found if any(k in p.name.lower() for k in ('a4','iso','mmgs','metric'))]
    pool=preferred if len(preferred)==1 else found
    selected=str(pool[0]) if len(pool)==1 else None
    if a.apply and selected:
        b['template_path']=selected;b['status']='TEMPLATE_BOUND_MBD_PENDING';b['template_binding_authority']='unique discovered template; review before production release';dump(bp,b)
    report={'schema':'k01.drawing_template_discovery.v1_7','all_candidates':[str(x) for x in found],'preferred_candidates':[str(x) for x in preferred],'selected_if_unique':selected,'binding_updated':bool(a.apply and selected),'policy':'Never silently choose among multiple drawing templates. Template is a release-controlled artifact.'}
    out=r/'reports/drawing/current/K01_DRAWING_TEMPLATE_DISCOVERY_CURRENT.json';dump(out,report);print('Drawing template candidates=',len(found),'preferred=',len(preferred));[print(' -',x) for x in (preferred or found)[:30]];print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
