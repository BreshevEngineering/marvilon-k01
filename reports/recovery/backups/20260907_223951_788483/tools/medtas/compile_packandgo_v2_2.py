from pathlib import Path
import argparse, subprocess, shutil, os, glob

def main():
 a=argparse.ArgumentParser(); a.add_argument('--repo-root',required=True); x=a.parse_args(); r=Path(x.repo_root)
 red=Path(r'C:/Program Files/SOLIDWORKS Corp/SOLIDWORKS/api/redist')
 candidates=[Path('C:/Program Files/SOLIDWORKS Corp/SOLIDWORKS/api/redist'),Path('C:/Program Files/SOLIDWORKS Corp/SOLIDWORKS 2026/api/redist')]
 red=next((p for p in candidates if p.exists()),None)
 if not red: print('HOLD SolidWorks API redist not found'); return 2
 sld=red/'SolidWorks.Interop.sldworks.dll'; swc=red/'SolidWorks.Interop.swconst.dll'
 csc=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
 out=r/'cad_api/medtas/bin/MedtasPackAndGoPromotion.exe'; out.parent.mkdir(parents=True,exist_ok=True)
 cp=subprocess.run([str(csc),'/nologo','/target:exe','/out:'+str(out),'/reference:'+str(sld),'/reference:'+str(swc),str(r/'cad_api/medtas/MedtasPackAndGoPromotion.cs')],text=True,capture_output=True)
 print(cp.stdout); print(cp.stderr)
 if cp.returncode: return cp.returncode
 for dll in red.glob('SolidWorks.Interop*.dll'): shutil.copy2(dll,out.parent/dll.name)
 print('PASS compiled',out); return 0
if __name__=='__main__': raise SystemExit(main())
