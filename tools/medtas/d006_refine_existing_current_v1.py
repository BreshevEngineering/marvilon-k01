#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,hashlib,subprocess,sys,shutil
from datetime import datetime
from pathlib import Path

D006=Path("reports/control/K01_D006_PROFESSIONAL_CANDIDATE_CURRENT.json")
PMI=Path("reports/control/K01_P007_PMI_PROVEN_CURRENT.json")
OUT=Path("reports/control/K01_D006_REFINED_EXISTING_CURRENT.json")
PROFILE=Path("control/drawings/K01_DRAWING_STANDARD_PROFILE_CURRENT.json")
CS=Path("cad_api/solidworks_2018_proven/current/K01_D006_REFINE_EXISTING/K01D006RefineExisting_v1.cs")
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
    rep={"schema":"k01.d006.refine_existing.current.v1","generated_local":datetime.now().isoformat(),"status":"RUNNING"}
    try:
        need(not sw_running(),"Close SolidWorks before API refinement so the saved drawing on disk is the source.")
        prof=load(root/PROFILE)
        need(prof.get("system")=="ISO_TPD_GPS","controlled ISO/GPS drawing profile missing/invalid")
        need((prof.get("projection") or {}).get("method")=="FIRST_ANGLE","K01 controlled projection method must be FIRST_ANGLE")
        scales=(prof.get("scales") or {}).get("current") or {}
        section_scale=float(scales.get("section",0));end_scale=float(scales.get("end_view",0));side_scale=float(scales.get("side_parent",0))
        allowed=set(float(x) for x in ((prof.get("scales") or {}).get("recommended_enlargement") or []))
        need(section_scale in allowed and end_scale in allowed and side_scale in allowed,"view scale not in controlled ISO 5455 preferred scale set")
        d=load(root/D006);p=load(root/PMI)
        need(d.get("status")=="PASS_K01_D006_PROFESSIONAL_DESIGN_REVIEW_CANDIDATE","current D006 build report is not PASS")
        drawing=Path(str(((d.get("candidate") or {}).get("slddrw") or "")))
        part=Path(str(((p.get("candidate") or {}).get("path") or "")))
        need(drawing.is_file(),"existing drawing missing: "+str(drawing))
        need(part.is_file(),"proven PMI part missing: "+str(part))
        source_drawing_sha=sha(drawing);source_part_sha=sha(part)

        rd=redist(); refs=[rd/"SolidWorks.Interop.sldworks.dll",rd/"SolidWorks.Interop.swconst.dll",rd/"SolidWorks.Interop.swdimxpert.dll"]
        for x in refs:need(x.is_file(),"interop missing "+str(x))
        work=root/WORK;build=work/"build";build.mkdir(parents=True,exist_ok=True)
        exe=build/"K01D006RefineExisting_v1.exe"
        cp=run([str(csc()),"/nologo","/langversion:5","/target:exe","/optimize+","/out:"+str(exe)]
               +["/reference:"+str(x) for x in refs]+[str(root/CS)],cwd=root)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        if cp.returncode!=0:
            rep["compile"]={"returncode":cp.returncode,"stdout":cp.stdout or "","stderr":cp.stderr or "","source":str(CS).replace("\\","/")}
            write(root/OUT,rep)
        need(cp.returncode==0,"D006 refinement helper compile failed")
        for x in refs:shutil.copy2(x,build/x.name)

        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        outdir=Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-006")/("refined_existing_"+stamp)
        raw=work/"K01_D006_REFINE_EXISTING_RAW_CURRENT.txt"
        cp=run([str(exe),"--drawing",str(drawing),"--part",str(part),"--outdir",str(outdir),"--report",str(raw),
                "--section-scale",str(section_scale),"--end-scale",str(end_scale),"--side-scale",str(side_scale)],cwd=root,timeout=420)
        if cp.stdout:print(cp.stdout,end="")
        if cp.stderr:print(cp.stderr,end="",file=sys.stderr)
        need(cp.returncode==0,"D006 existing-drawing refinement failed")
        kv=parse_kv(raw)
        need(kv.get("STATUS")=="PASS_D006_EXISTING_DRAWING_REFINED_CANDIDATE","raw refinement status not PASS")
        need(sha(drawing)==source_drawing_sha,"source drawing changed")
        need(sha(part)==source_part_sha,"source part changed")
        dx_count=int(kv.get("DIMXPERT_EXISTING_OR_IMPORTED_COUNT","0") or 0)
        candidate_status="PASS_D006_EXISTING_DRAWING_REFINED_CANDIDATE" if dx_count>=2 else "HOLD_D006_NATIVE_DIMXPERT_TRANSFER_REQUIRED"
        rep.update({
          "status":candidate_status,
          "source_drawing":{"path":str(drawing),"sha256":source_drawing_sha},
          "source_part":{"path":str(part),"sha256":source_part_sha},
          "candidate":{"slddrw":kv.get("OUTPUT_DRAWING"),"pdf":kv.get("OUTPUT_PDF"),"bmp":kv.get("OUTPUT_BMP")},
          "view_layout":{"section":kv.get("SECTION_VIEW"),"end":kv.get("END_VIEW"),"side":kv.get("SIDE_VIEW"),"count":int(kv.get("P007_VIEW_COUNT","0"))},
          "dimxpert":{"count":int(kv.get("DIMXPERT_EXISTING_OR_IMPORTED_COUNT","0")),"new":kv.get("DIMXPERT_NEW",""),"filtered_non_dimxpert":int(kv.get("FILTERED_IMPORTED_ANNOTATIONS","0"))},
          "source_invariant":True,
          "standards_profile":str(PROFILE).replace("\\","/"),
          "projection_method":"FIRST_ANGLE",
          "view_scales":{"section":section_scale,"end_view":end_scale,"side_parent":side_scale},
          "standards_release_status":"HOLD_UNTIL_CONTROLLED_TEMPLATE_AND_FINAL_SEMANTIC_VISUAL_QA",
          "next":"Open refined PDF/BMP; make only final visual moves if needed. Do not recreate the drawing." if candidate_status.startswith("PASS") else "Native C02/C05 DimXpert transfer is still required in SOLIDWORKS 2018. Import from model PMI; do not retype dimensions; save/close and run RUN_K01_D006_VERIFY_IMPORTED_PMI.cmd."
        })
        write(root/OUT,rep)
        print("STATUS:",rep["status"])
        print("DRAWING:",rep["candidate"]["slddrw"])
        print("PDF:",rep["candidate"]["pdf"])
        print("BMP:",rep["candidate"]["bmp"])
        print("DIMXPERT:",rep["dimxpert"])
        if candidate_status.startswith("PASS"):
            print("NEXT: inspect/refine existing drawing; no rebuild from zero")
            return 0
        print("NEXT: native DimXpert C02/C05 transfer required; save/close, then run RUN_K01_D006_VERIFY_IMPORTED_PMI.cmd")
        return 3
    except Exception as e:
        rep["status"]="HOLD_D006_EXISTING_DRAWING_REFINEMENT";rep["error"]=repr(e);write(root/OUT,rep)
        print("STATUS:",rep["status"]);print("ERROR:",repr(e));print("REPORT:",root/OUT);return 2

if __name__=="__main__":raise SystemExit(main())
