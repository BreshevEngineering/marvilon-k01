#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,hashlib,subprocess,sys,shutil
from datetime import datetime
from pathlib import Path

REFINED=Path("reports/control/K01_D006_REFINED_EXISTING_CURRENT.json")
PMI=Path("reports/control/K01_P007_PMI_PROVEN_CURRENT.json")
OUT=Path("reports/control/K01_D006_IMPORTED_PMI_VERIFY_CURRENT.json")
CS=Path("cad_api/solidworks_2018_proven/current/K01_D006_REFINE_EXISTING/K01D006VerifyImportedPmi_v1.cs")
WORK=Path("reports/cad/d006_refine_existing_current")

def load(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");os.replace(str(t),str(p))
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def run(c,cwd=None,timeout=420):
    return subprocess.run(c,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)
def sw_running():
    cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30)
    return "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower()
def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in [w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"]:
        if p.exists():return p
    raise RuntimeError("csc.exe missing")
def redist():
    for p in [Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")]:
        if (p/"SolidWorks.Interop.sldworks.dll").exists():return p
    raise RuntimeError("SW interop redist missing")
def parse_kv(p):
    d={}
    for line in Path(p).read_text(encoding="utf-8-sig",errors="replace").splitlines():
        if "=" in line:
            k,v=line.split("=",1);d[k.strip()]=v.strip()
    return d

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    rep={"schema":"k01.d006.imported_pmi_verify.current.v1","generated_local":datetime.now().isoformat(),"status":"RUNNING"}
    try:
        need(not sw_running(),"Close SolidWorks before imported-PMI verification so the saved SLDDRW on disk is the source.")
        refined=load(root/REFINED);pmi=load(root/PMI)
        drawing=Path(str(((refined.get("candidate") or {}).get("slddrw") or "")))
        part=Path(str(((pmi.get("candidate") or {}).get("path") or "")))
        need(drawing.is_file(),"refined D006 candidate missing: "+str(drawing))
        need(part.is_file(),"proven P007 PMI candidate missing: "+str(part))
        before=sha(drawing)

        rd=redist();refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll",rd/"SolidWorks.Interop.swdimxpert.dll"]
        for x in refs:need(x.is_file(),"interop missing "+str(x))
        work=root/WORK;build=work/"build_verify";build.mkdir(parents=True,exist_ok=True)
        exe=build/"K01D006VerifyImportedPmi_v1.exe"
        cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]
               +["/reference:"+str(x) for x in refs]+[str(root/CS)],cwd=root)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        if cp.returncode!=0:
            rep["compile"]={"returncode":cp.returncode,"stdout":cp.stdout or "","stderr":cp.stderr or "","source":str(CS).replace("\\","/")}
            write(root/OUT,rep)
        need(cp.returncode==0,"D006 imported-PMI verifier compile failed")
        for x in refs:shutil.copy2(x,build/x.name)

        raw=work/"K01_D006_IMPORTED_PMI_VERIFY_RAW_CURRENT.txt"
        cp=run([str(exe),"--drawing",str(drawing),"--part",str(part),"--report",str(raw)],cwd=root,timeout=420)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        kv=parse_kv(raw) if raw.is_file() else {}
        after=sha(drawing)
        need(after==before,"D006 drawing changed during verification")
        c02=(kv.get("C02","").lower()=="true");c05=(kv.get("C05","").lower()=="true")
        count=int(kv.get("DIMXPERT_ANNOTATION_COUNT","0") or 0)
        refs_count=int(kv.get("P007_VIEW_REFERENCE_COUNT","0") or 0)
        status="PASS_D006_NATIVE_DIMXPERT_C02_C05_VERIFIED" if cp.returncode==0 and c02 and c05 else "HOLD_D006_NATIVE_DIMXPERT_C02_C05_MISSING"
        rep.update({
          "status":status,
          "drawing":{"path":str(drawing),"sha256":before,"invariant":True},
          "source_part":{"path":str(part)},
          "p007_view_reference_count":refs_count,
          "dimxpert":{"count":count,"C02_Cylinder1_Diameter2":c02,"C05_Cylinder2_Diameter4":c05},
          "pdf":kv.get("PDF"),"bmp":kv.get("BMP"),
          "raw_report":str(raw),
          "next":"Professional D006 layout/ISO-GPS QA" if status.startswith("PASS") else "Open this exact SLDDRW in SOLIDWORKS 2018; import native DimXpert annotations into the P007 drawing views, save, close SOLIDWORKS, rerun this verifier. Do not retype C02/C05."
        })
        write(root/OUT,rep)
        print("STATUS:",status)
        print("DRAWING:",drawing)
        print("DIMXPERT:",rep["dimxpert"])
        print("REPORT:",root/OUT)
        return 0 if status.startswith("PASS") else 3
    except Exception as e:
        rep["status"]="HOLD_D006_IMPORTED_PMI_VERIFY";rep["error"]=repr(e);write(root/OUT,rep)
        print("STATUS:",rep["status"]);print("ERROR:",repr(e));print("REPORT:",root/OUT);return 2

if __name__=="__main__":raise SystemExit(main())
