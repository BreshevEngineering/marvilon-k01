from __future__ import annotations
import argparse,importlib.util,json,os,shutil
from pathlib import Path
from medtas_v16_common import load,dump

def candidates(names):
    roots=[]
    for env in ('ProgramFiles','ProgramFiles(x86)','LOCALAPPDATA','USERPROFILE'):
        v=os.environ.get(env)
        if v:roots.append(Path(v))
    roots += [Path('C:/CalculiX'),Path('C:/ccx'),Path('C:/gmsh'),Path('C:/Program Files')]
    seen=set();out=[]
    for n in names:
        q=shutil.which(n)
        if q and q not in seen:seen.add(q);out.append(Path(q))
    pats=[]
    for n in names:
        stem=Path(n).stem.lower();pats += [f'**/{n}',f'**/{stem}*.exe']
    for r in roots:
        if not r.exists():continue
        # Keep search bounded: common depth patterns first.
        for pat in pats:
            try:
                for p in list(r.glob(pat))[:20]:
                    s=str(p.resolve())
                    if p.is_file() and s not in seen:seen.add(s);out.append(p.resolve())
            except Exception:pass
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--apply',action='store_true',help='write discovered unique paths into controlled toolchain binding');a=ap.parse_args();root=Path(a.repo_root).resolve();bp=root/'control/medtas/v1/bindings/K01_TOOLCHAIN_BINDING_v1_6.json';b=load(bp) if bp.exists() else {'schema':'k01.toolchain_binding.v1_7','policy':'Explicit paths only'}
    ccx=candidates(['ccx.exe','ccx']);gmsh=candidates(['gmsh.exe','gmsh']);gmsh_py=importlib.util.find_spec('gmsh') is not None
    selected_ccx=str(ccx[0]) if len(ccx)==1 else None;selected_gmsh=str(gmsh[0]) if len(gmsh)==1 else None
    if a.apply:
        if selected_ccx:b['calculix_executable']=selected_ccx
        if selected_gmsh:b['gmsh_executable']=selected_gmsh
        b['discovery_note']='Paths were written only when discovery returned exactly one candidate. Ambiguous candidates remain unbound.'
        dump(bp,b)
    report={'schema':'k01.analysis_toolchain_discovery.v1_7','calculix_candidates':[str(x) for x in ccx],'gmsh_executable_candidates':[str(x) for x in gmsh],'gmsh_python_api':gmsh_py,'selected_if_unique':{'calculix_executable':selected_ccx,'gmsh_executable':selected_gmsh},'binding_updated':bool(a.apply),'binding_path':str(bp),'next_action':('Run with --apply if unique candidates are correct.' if not a.apply else 'Review binding; install missing tool(s) if no candidate exists.')}
    out=root/'reports/medtas/calculix/current/K01_ANALYSIS_TOOLCHAIN_DISCOVERY_CURRENT.json';dump(out,report)
    print('Analysis toolchain discovery');print(' CalculiX candidates:',len(ccx));[print('  -',x) for x in ccx];print(' Gmsh executable candidates:',len(gmsh));[print('  -',x) for x in gmsh];print(' Gmsh Python API:',gmsh_py);print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
