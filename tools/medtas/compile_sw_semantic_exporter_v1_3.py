from pathlib import Path
import os, subprocess, sys, argparse, json

def find_file(names):
    roots=[]
    pf=os.environ.get('ProgramFiles')
    pf86=os.environ.get('ProgramFiles(x86)')
    for base in [pf,pf86]:
        if base:
            roots += [Path(base)/'SOLIDWORKS Corp'/'SOLIDWORKS'/'api'/'redist', Path(base)/'SOLIDWORKS Corp']
    # fast exact candidates first
    for r in roots:
        for n in names:
            p=r/n
            if p.exists(): return p
    # bounded recursive fallback under SOLIDWORKS Corp only
    for r in roots:
        if not r.exists(): continue
        try:
            for n in names:
                hits=list(r.rglob(n))
                if hits: return sorted(hits, key=lambda p: len(str(p)))[0]
        except Exception:
            pass
    return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    src=root/'cad_api/medtas/K01CadSemanticA001.cs'
    out=root/'cad_api/medtas/bin/K01CadSemanticA001.exe'; out.parent.mkdir(parents=True,exist_ok=True)
    csc=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not csc.exists(): csc=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework/v4.0.30319/csc.exe'
    if not csc.exists():
        print('ERROR: csc.exe not found', file=sys.stderr); return 10
    sw=find_file(['SolidWorks.Interop.sldworks.dll'])
    const=find_file(['SolidWorks.Interop.swconst.dll'])
    if not sw or not const:
        print('ERROR: SolidWorks interop assemblies not found.', file=sys.stderr)
        print('Expected under Program Files\\SOLIDWORKS Corp\\SOLIDWORKS\\api\\redist', file=sys.stderr)
        print('sldworks=',sw,'swconst=',const,file=sys.stderr)
        return 11
    print('Using interop:')
    print('  ',sw)
    print('  ',const)
    cmd=[str(csc),'/nologo','/optimize+','/target:exe',f'/r:{sw}',f'/r:{const}','/r:System.Web.Extensions.dll',f'/out:{out}',str(src)]
    cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True)
    if cp.stdout: print(cp.stdout,end='')
    if cp.stderr: print(cp.stderr,end='',file=sys.stderr)
    if cp.returncode:
        print('ERROR: C# compile failed rc=',cp.returncode,file=sys.stderr); return cp.returncode
    meta={'schema':'k01.sw_interop_compile.v1','sldworks_interop':str(sw),'swconst_interop':str(const),'compiler':str(csc),'output':str(out)}
    mp=root/'reports/medtas/cad/current/K01_SW_INTEROP_COMPILE_CURRENT.json'; mp.parent.mkdir(parents=True,exist_ok=True)
    mp.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print('PASS compiled',out)
    return 0
if __name__=='__main__': raise SystemExit(main())
