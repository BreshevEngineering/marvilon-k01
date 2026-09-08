from pathlib import Path
import argparse, subprocess, shutil, os, glob
from v22_common import save, sha256_file

def main():
 a=argparse.ArgumentParser(); a.add_argument('--repo-root',required=True); x=a.parse_args(); r=Path(x.repo_root)
 red=Path(r'C:/Program Files/SOLIDWORKS Corp/SOLIDWORKS/api/redist')
 candidates=[Path('C:/Program Files/SOLIDWORKS Corp/SOLIDWORKS/api/redist'),Path('C:/Program Files/SOLIDWORKS Corp/SOLIDWORKS 2026/api/redist')]
 red=next((p for p in candidates if p.exists()),None)
 if not red: print('HOLD SolidWorks API redist not found'); return 2
 sld=red/'SolidWorks.Interop.sldworks.dll'; swc=red/'SolidWorks.Interop.swconst.dll'
 csc=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
 out=r/'cad_api/medtas/bin/MedtasPackAndGoPromotion.exe'; out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists(): out.unlink()  # Never retain a stale runnable adapter after failed compilation.
 cp=subprocess.run([str(csc),'/nologo','/target:exe','/reference:System.Web.Extensions.dll','/out:'+str(out),'/reference:'+str(sld),'/reference:'+str(swc),str(r/'cad_api/medtas/MedtasPackAndGoPromotion.cs')],text=True,capture_output=True)
 print(cp.stdout); print(cp.stderr)
 if cp.returncode: return cp.returncode
 for dll in red.glob('SolidWorks.Interop*.dll'): shutil.copy2(dll,out.parent/dll.name)
 save(out.parent/'MedtasPackAndGoPromotion.build.json',{'source_sha256':sha256_file(r/'cad_api/medtas/MedtasPackAndGoPromotion.cs'),'exe_sha256':sha256_file(out),'sldworks_interop_sha256':sha256_file(sld),'swconst_interop_sha256':sha256_file(swc)})
 print('PASS compiled',out); return 0
if __name__=='__main__': raise SystemExit(main())
