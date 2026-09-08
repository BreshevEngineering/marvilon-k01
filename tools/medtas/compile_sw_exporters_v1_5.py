from pathlib import Path
import os, subprocess, sys, argparse, json, shutil

def candidate_redist_roots():
    roots=[]
    for key in ('ProgramFiles','ProgramFiles(x86)'):
        base=os.environ.get(key)
        if base:
            roots += [Path(base)/'SOLIDWORKS Corp'/'SOLIDWORKS'/'api'/'redist', Path(base)/'SOLIDWORKS Corp']
    return roots

def find_file(names):
    for r in candidate_redist_roots():
        for n in names:
            p=r/n
            if p.exists(): return p
    for r in candidate_redist_roots():
        if not r.exists(): continue
        for n in names:
            try:
                hits=list(r.rglob(n))
                if hits: return sorted(hits,key=lambda p:len(str(p)))[0]
            except Exception: pass
    return None

def compile_one(csc,root,src,out,refs,label):
    out.parent.mkdir(parents=True,exist_ok=True)
    cmd=[str(csc),'/nologo','/optimize+','/platform:x64','/target:exe']+[f'/r:{p}' for p in refs]+['/r:System.Web.Extensions.dll',f'/out:{out}',str(src)]
    cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True)
    if cp.stdout: print(cp.stdout,end='')
    if cp.stderr: print(cp.stderr,end='',file=sys.stderr)
    if cp.returncode:
        print(f'ERROR: {label} compile failed rc={cp.returncode}',file=sys.stderr)
        return False
    print('PASS compiled',label,'->',out)
    return True

def copy_runtime_interops(primary:Path, bin_dir:Path):
    """Copy the exact SolidWorks managed interop set next to the EXE.

    C# compilation alone is not enough: .NET resolves strong-named SolidWorks.Interop.*
    assemblies again at process start. Keeping the exact DLLs beside the exporter makes
    runtime binding deterministic and avoids reliance on the GAC or machine PATH.
    """
    srcdir=primary.parent
    copied=[]
    for p in sorted(srcdir.glob('SolidWorks.Interop.*.dll')):
        try:
            dst=bin_dir/p.name
            shutil.copy2(p,dst)
            copied.append(str(dst))
        except Exception as e:
            print('WARNING runtime interop copy failed:',p,e,file=sys.stderr)
    return copied

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    wind=Path(os.environ.get('WINDIR','C:/Windows'))
    csc=wind/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    if not csc.exists(): csc=wind/'Microsoft.NET/Framework/v4.0.30319/csc.exe'
    if not csc.exists(): print('ERROR: csc.exe not found',file=sys.stderr); return 10
    sw=find_file(['SolidWorks.Interop.sldworks.dll']); const=find_file(['SolidWorks.Interop.swconst.dll']); dx=find_file(['SolidWorks.Interop.swdimxpert.dll','swdimxpert.dll'])
    if not sw or not const:
        print('ERROR: required SolidWorks interop assemblies not found.',file=sys.stderr); return 11
    bin_dir=root/'cad_api/medtas/bin'; bin_dir.mkdir(parents=True,exist_ok=True)
    copied=copy_runtime_interops(sw,bin_dir)
    print('Using interop:'); print(' ',sw); print(' ',const); print(' ',dx or 'DimXpert interop NOT FOUND')
    print('Runtime interop bundle:',len(copied),'DLL(s) copied beside exporter')
    cad_ok=compile_one(csc,root,root/'cad_api/medtas/K01CadSemanticA001.cs',bin_dir/'K01CadSemanticA001.exe',[sw,const],'CAD semantic exporter')
    if not cad_ok: return 12
    mbd_status='NOT_COMPILED'
    if dx:
        mbd_ok=compile_one(csc,root,root/'cad_api/medtas/K01MbdDimXpertPart.cs',bin_dir/'K01MbdDimXpertPart.exe',[sw,const,dx],'MBD/DimXpert exporter')
        mbd_status='PASS' if mbd_ok else 'COMPILE_FAILED'
    else:
        print('WARNING: SolidWorks.Interop.swdimxpert.dll not found; MBD node will remain limited.',file=sys.stderr)
        mbd_status='INTEROP_MISSING'
    required_local=['SolidWorks.Interop.sldworks.dll','SolidWorks.Interop.swconst.dll']
    missing_local=[x for x in required_local if not (bin_dir/x).exists()]
    meta={'schema':'k01.sw_interop_compile.v1_5','compiler':str(csc),'platform':'x64','sldworks_interop':str(sw),'swconst_interop':str(const),'swdimxpert_interop':str(dx) if dx else None,'runtime_bin':str(bin_dir),'runtime_interops_copied':copied,'runtime_required_missing':missing_local,'cad_exporter':'PASS' if cad_ok else 'FAIL','mbd_exporter':mbd_status}
    mp=root/'reports/medtas/cad/current/K01_SW_INTEROP_COMPILE_CURRENT.json'; mp.parent.mkdir(parents=True,exist_ok=True); mp.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    if missing_local:
        print('ERROR: runtime interop bundle incomplete:',missing_local,file=sys.stderr); return 13
    return 0
if __name__=='__main__': raise SystemExit(main())
