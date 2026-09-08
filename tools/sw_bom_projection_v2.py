from __future__ import annotations
import csv,json,os,re,sys,traceback
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import pythoncom,win32com.client
from sw_com import member0,call,as_list

ROOT=Path(r"D:\BreshevEngineering\marvilon-k01")
MASTER=ROOT/"master"/"K01_master.json"
OUT=ROOT/"bom"/"K01_BOM_FROM_SW.csv"
REP=ROOT/"reports"/"cad"/"current"/"K01_BOM_FROM_SW.json"

def norm(p):return os.path.normcase(os.path.normpath(str(p)))
def pth(c):
    p,e=member0(c,"GetPathName",default="");return "" if e else str(p or "")
def model(c):
    m,e=member0(c,"GetModelDoc2",default=None);return None if e else m
def pn(path):
    s=Path(path).stem
    m=re.match(r"(K01-[PBA]-\d{3})",s,re.I)
    return m.group(1).upper() if m else s
def mat(m):
    if m is None:return ""
    cm,_=member0(m,"ConfigurationManager",default=None);cfg,_=member0(cm,"ActiveConfiguration",default=None)
    cn,_=member0(cfg,"Name",default="Default")
    raw,e=call(m,"GetMaterialPropertyName2",str(cn),default=None)
    if e or raw is None:return ""
    if isinstance(raw,tuple):
        a=[x for x in raw if isinstance(x,str) and x];return a[-1] if a else ""
    return str(raw or "")
def main():
    pythoncom.CoInitialize()
    master=json.loads(MASTER.read_text(encoding="utf-8"))
    parts=master.get("parts",{})
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    asm,_=member0(sw,"ActiveDoc",default=None)
    typ,_=member0(asm,"GetType",default=None)
    if int(typ)!=2:raise RuntimeError("Open active K01 assembly")
    cs,e=call(asm,"GetComponents",False,default=None)
    if e:raise RuntimeError(e)
    cs=[c for c in as_list(cs) if c is not None and pth(c)]
    counts=Counter(norm(pth(c)) for c in cs)
    first={}
    for c in cs:first.setdefault(norm(pth(c)),c)
    rows=[];seen=set()
    for k,q in sorted(counts.items(),key=lambda x:Path(x[0]).name):
        c=first[k];path=pth(c);id=pn(path);seen.add(id);mp=parts.get(id,{})
        rows.append({"PartNo":id,"Qty":q,"Description":mp.get("description",""),
                     "MakeBuy":"BUY" if "-B-" in id else "MAKE" if "-P-" in id else "",
                     "MaterialSpec":mp.get("material",""),"SWMaterial":mat(model(c)),
                     "Status":mp.get("status",""),"File":path,"Source":"ASSEMBLY"})
    for id,mp in parts.items():
        if id in seen or "-B-" not in id:continue
        if "RETIRED" in str(mp.get("status","")).upper():continue
        rows.append({"PartNo":id,"Qty":"","Description":mp.get("description",""),
                     "MakeBuy":"BUY","MaterialSpec":mp.get("material",""),
                     "SWMaterial":"","Status":mp.get("status",""),"File":"",
                     "Source":"MASTER_ONLY_QTY_OPEN"})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    fields=list(rows[0].keys()) if rows else []
    with OUT.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    REP.parent.mkdir(parents=True,exist_ok=True)
    REP.write_text(json.dumps({"schema":"k01_bom_from_sw_v2","status":"PASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),"instances":len(cs),
      "rows":len(rows),"csv":str(OUT),
      "authority":"Qty=active SolidWorks assembly; identity/spec/lifecycle=K01_master.json"},
      indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] BOM generated:",OUT);print("Rows",len(rows),"Instances",len(cs));return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:traceback.print_exc();raise
