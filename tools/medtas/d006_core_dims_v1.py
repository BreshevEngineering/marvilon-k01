#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, shutil, subprocess, time
from pathlib import Path

DRAWING = Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006\manual_exemplar_v12_20260912_165501\K01-D-006_Hermetic_Magnetic_Can_EXEMPLAR_V12_CANDIDATE.SLDDRW")
PART = Path(r"D:\Marvilon\K01\cad\candidates\p007_d2_exemplar\manual_exemplar_20260912_165501\K01-P-007_Hermetic_Magnetic_Can_D2_EXEMPLAR_CANDIDATE.SLDPRT")
CS = Path("cad_api/solidworks_2018_proven/current/K01_D006_CORE_DIMS_V1/K01D006CoreDimsV1.cs")
WORK = Path("reports/cad/d006_core_dims_v1_current")
OUT_ROOT = Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")

def run(cmd,cwd=None,timeout=600):
    return subprocess.run(cmd,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)

def need(ok,msg):
    if not ok: raise RuntimeError(msg)

def sw_running():
    cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30)
    return "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower()

def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in (w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"):
        if p.exists(): return p
    raise RuntimeError("csc.exe missing")

def redist():
    for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
        if (p/"SolidWorks.Interop.sldworks.dll").exists(): return p
    raise RuntimeError("SOLIDWORKS 2018 API redist missing")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",required=True)
    a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    try:
        need(not sw_running(),"Close SolidWorks before core-dimension population; the saved V12 drawing must be the input.")
        need(DRAWING.is_file(),"V12 drawing missing: "+str(DRAWING))
        need(PART.is_file(),"P007 D2 exemplar part missing: "+str(PART))
        need((root/CS).is_file(),"C# helper missing: "+str(root/CS))
        rd=redist(); refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll"]
        for p in refs: need(p.is_file(),"interop missing: "+str(p))
        build=root/WORK/"build";build.mkdir(parents=True,exist_ok=True)
        exe=build/"K01D006CoreDimsV1.exe";raw=root/WORK/"K01_D006_CORE_DIMS_V1_CURRENT.txt"
        cmd=[str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]
        cmd += ["/reference:"+str(x) for x in refs]
        cmd += [str(root/CS)]
        cp=run(cmd,cwd=root)
        if cp.stdout: print(cp.stdout,end="")
        if cp.stderr: print(cp.stderr,end="")
        need(cp.returncode==0,"core-dimension C# compile failed")
        for x in refs: shutil.copy2(x,build/x.name)
        cp=run([str(exe),"--drawing",str(DRAWING),"--part",str(PART),"--out-root",str(OUT_ROOT),"--report",str(raw)],cwd=root,timeout=600)
        if cp.stdout: print(cp.stdout,end="")
        if cp.stderr: print(cp.stderr,end="")
        need(cp.returncode==0,"core-dimension helper failed")
        return 0
    except Exception as e:
        print("STATUS: HOLD_D006_CORE_DIMS_V1")
        print("ERROR:",repr(e))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
