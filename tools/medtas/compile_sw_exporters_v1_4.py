from pathlib import Path
import os, subprocess, sys, argparse, json

def find_file(names):
    roots=[]
    pf=os.environ.get('ProgramFiles'); pf86=os.environ.get('ProgramFiles(x86)')
    for base in [pf,pf86]:
        if base:
            roots += [Path(base)/'SOLIDWORKS Corp'/'SOLIDWORKS'/'api'/'redist', Path(base)/'SOLIDWORKS Corp']
    for r in roots:
        for n in names:
            p=r/n
            if p.exists(): return p
    for r in roots:
        if not r.exists(): continue
        try:
            for n in names:
                hits=list(r.rglob(n))
                if hits: return sorted(hits,key=lambda p:len(str(p)))[0]
        except Exception: pass
    return None

def compile_one(csc,root,src,out,refs,label):
    out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():
        try: out.unlink()
        except Exception: pass
    cmd=[str(csc),'/nologo','/optimize+','/target:exe']+[f'/r:{p}' for p in refs]+['/r:System.Web.Extensions.dll',f'/out:{out}',str(src)]
    cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True)
    if cp.stdout: print(cp.stdout,end='')
    if cp.stderr: print(cp.stderr,end='',file=sys.stderr)
    if cp.returncode:
        print(f'ERROR: {label} compile failed rc={cp.returncode}',file=sys.stderr)
        return False
    print('PASS compiled',label,'->',out)
    return True

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    wind=Path(os.environ.get('WINDIR','C:/Windows'))
    csc=wind/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not csc.exists(): csc=wind/'Microsoft.NET/Framework/v4.0.30319/csc.exe'
    if not csc.exists(): print('ERROR: csc.exe not found',file=sys.stderr); return 10
    sw=find_file(['SolidWorks.Interop.sldworks.dll']); const=find_file(['SolidWorks.Interop.swconst.dll']); dx=find_file(['SolidWorks.Interop.swdimxpert.dll','swdimxpert.dll'])
    if not sw or not const:
        print('ERROR: required SolidWorks interop assemblies not found.',file=sys.stderr); print('sldworks=',sw,'swconst=',const,file=sys.stderr); return 11
    print('Using interop:'); print(' ',sw); print(' ',const); print(' ',dx or 'DimXpert interop NOT FOUND')
    cad_ok=compile_one(csc,root,root/'cad_api/medtas/K01CadSemanticA001.cs',root/'cad_api/medtas/bin/K01CadSemanticA001.exe',[sw,const],'CAD semantic exporter')
    if not cad_ok: return 12
    mbd_status='NOT_COMPILED'
    if dx:
        mbd_ok=compile_one(csc,root,root/'cad_api/medtas/K01MbdDimXpertPart.cs',root/'cad_api/medtas/bin/K01MbdDimXpertPart.exe',[sw,const,dx],'MBD/DimXpert exporter')
        mbd_status='PASS' if mbd_ok else 'COMPILE_FAILED'
    else:
        print('WARNING: SolidWorks.Interop.swdimxpert.dll not found; MBD node will remain PASS_WITH_LIMITATIONS/UNAVAILABLE.',file=sys.stderr)
        mbd_status='INTEROP_MISSING'
    meta={'schema':'k01.sw_interop_compile.v1_4','compiler':str(csc),'sldworks_interop':str(sw),'swconst_interop':str(const),'swdimxpert_interop':str(dx) if dx else None,'cad_exporter':'PASS','mbd_exporter':mbd_status}
    mp=root/'reports/medtas/cad/current/K01_SW_INTEROP_COMPILE_CURRENT.json'; mp.parent.mkdir(parents=True,exist_ok=True); mp.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    # MBD compile failure is non-blocking for current geometry pipeline; the MBD node records the limitation.
    return 0
if __name__=='__main__': raise SystemExit(main())
