from __future__ import annotations
import csv, json, os, re, sys, traceback
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
import pythoncom
import win32com.client
from sw_com import member0, call, as_list

ROOT = Path(r"D:\BreshevEngineering\marvilon-k01")
MASTER = ROOT/"master"/"K01_master.json"
OUTCSV = ROOT/"bom"/"K01_BOM_FROM_SW.csv"
OUTJSON = ROOT/"reports"/"cad"/"current"/"K01_BOM_FROM_SW.json"

PROP_NAMES = [
    "PartNo","Description","MaterialSpec","MakeBuy","Revision","LifecycleStatus"
]

def norm(p): return os.path.normcase(os.path.normpath(str(p)))

def cpath(c):
    p,e=member0(c,"GetPathName",default="")
    if e: return ""
    return str(p or "")

def cname(c):
    n,_=member0(c,"Name2",default="")
    return str(n or "")

def model(c):
    m,e=member0(c,"GetModelDoc2",default=None)
    return None if e else m

def read_cfg_props(m):
    result={}
    if m is None: return result
    ext,_=member0(m,"Extension",default=None)
    cm,_=member0(m,"ConfigurationManager",default=None)
    cfg,_=member0(cm,"ActiveConfiguration",default=None)
    cfg_name,_=member0(cfg,"Name",default="")
    for scope in (str(cfg_name or ""), ""):
        mgr=None
        try:
            mgr=ext.CustomPropertyManager(scope)
        except Exception:
            try:
                mgr,_=call(ext,"get_CustomPropertyManager",scope,default=None)
            except Exception:
                mgr=None
        if mgr is None: continue
        for key in PROP_NAMES:
            if key in result and result[key]:
                continue
            try:
                raw,resolved,was_resolved = mgr.Get2(key)
                val = resolved or raw or ""
            except Exception:
                val=""
            if val: result[key]=str(val)
    return result

def material(m):
    if m is None: return ""
    cm,_=member0(m,"ConfigurationManager",default=None)
    cfg,_=member0(cm,"ActiveConfiguration",default=None)
    cfg_name,_=member0(cfg,"Name",default="Default")
    raw,e=call(m,"GetMaterialPropertyName2",str(cfg_name),default=None)
    if e or raw is None: return ""
    if isinstance(raw,tuple):
        ss=[x for x in raw if isinstance(x,str) and x]
        return ss[-1] if ss else ""
    return str(raw or "")

def partno_from_filename(path):
    stem=Path(path).stem
    m=re.match(r"(K01-[PBA]-\d{3})",stem,re.I)
    return m.group(1).upper() if m else stem

def main():
    pythoncom.CoInitialize()
    if not MASTER.exists(): raise FileNotFoundError(MASTER)
    master=json.loads(MASTER.read_text(encoding="utf-8"))

    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev,_=member0(sw,"RevisionNumber",default="")
    asm,e=member0(sw,"ActiveDoc",default=None)
    if e or asm is None: raise RuntimeError(e or "No active document")
    typ,_=member0(asm,"GetType",default=None)
    if int(typ)!=2: raise RuntimeError("Active doc must be K01 assembly")

    comps,e=call(asm,"GetComponents",False,default=None)
    if e: raise RuntimeError(e)
    comps=[c for c in as_list(comps) if c is not None]

    # Count by exact referenced file. Reference components are kept but marked.
    counts=Counter(norm(cpath(c)) for c in comps if cpath(c))
    first={}
    for c in comps:
        p=cpath(c)
        if p and norm(p) not in first: first[norm(p)]=c

    master_parts = master.get("parts",{})
    rows=[]
    found_partnos=set()

    for key,count in sorted(counts.items(), key=lambda kv: Path(kv[0]).name.lower()):
        c=first[key]; p=cpath(c); m=model(c)
        props=read_cfg_props(m)
        pn=props.get("PartNo") or partno_from_filename(p)
        found_partnos.add(pn)
        mp=master_parts.get(pn,{})
        desc=props.get("Description") or mp.get("description","")
        mat_prop=props.get("MaterialSpec") or mp.get("material","")
        mat_sw=material(m)
        makebuy=props.get("MakeBuy") or ("BUY" if "-B-" in pn else "MAKE" if "-P-" in pn else "")
        status=props.get("LifecycleStatus") or mp.get("status","")
        rows.append({
            "PartNo":pn,"Qty":count,"Description":desc,
            "MakeBuy":makebuy,"MaterialSpec":mat_prop,
            "SWMaterial":mat_sw,"Revision":props.get("Revision",""),
            "LifecycleStatus":status,"File":p,"Source":"ASSEMBLY"
        })

    # Add active purchased/master items not represented by CAD geometry.
    for pn,mp in master_parts.items():
        if pn in found_partnos: continue
        status=str(mp.get("status",""))
        if any(tok in status.upper() for tok in ("RETIRED","OBSOLETE")):
            continue
        if "-B-" in pn:
            rows.append({
                "PartNo":pn,"Qty":"","Description":mp.get("description",""),
                "MakeBuy":"BUY","MaterialSpec":mp.get("material",""),
                "SWMaterial":"","Revision":"","LifecycleStatus":status,
                "File":"","Source":"MASTER_ONLY_QTY_OPEN"
            })

    OUTCSV.parent.mkdir(parents=True,exist_ok=True)
    fields=["PartNo","Qty","Description","MakeBuy","MaterialSpec","SWMaterial","Revision","LifecycleStatus","File","Source"]
    with OUTCSV.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

    missing_identity=[
        r["PartNo"] for r in rows
        if r["Source"]=="ASSEMBLY" and not r["Description"]
    ]
    report={
        "schema":"k01_bom_from_sw_v1","status":"PASS",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "solidworks_revision":str(rev),
        "assembly_component_instances":len(comps),
        "bom_rows":len(rows),
        "missing_description":missing_identity,
        "csv":str(OUTCSV),
        "rule":"Quantity comes from assembly. Design identity/material/lifecycle falls back to K01_master.json. No manually maintained second BOM truth."
    }
    OUTJSON.parent.mkdir(parents=True,exist_ok=True)
    OUTJSON.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] BOM projection generated from active SOLIDWORKS assembly + master.")
    print("CSV:",OUTCSV)
    print("Report:",OUTJSON)
    print("Rows:",len(rows),"Instances:",len(comps))
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception:
        print("FAIL: K01 BOM projection"); traceback.print_exc(); raise SystemExit(1)
