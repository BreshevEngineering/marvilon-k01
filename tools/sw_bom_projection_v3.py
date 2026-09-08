from __future__ import annotations
import csv,json,os,re,traceback
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import pythoncom,win32com.client
from sw_com import member0,call,as_list

ROOT=Path(r"D:\BreshevEngineering\marvilon-k01")
MASTER=ROOT/"master"/"K01_master.json";OUT=ROOT/"bom"/"K01_BOM_FROM_SW.csv"
REP=ROOT/"reports"/"cad"/"current"/"K01_BOM_FROM_SW.json"
PROPS=["PartNo","Description","MaterialSpec","MakeBuy","Revision","LifecycleStatus"]

def norm(p):return os.path.normcase(os.path.normpath(str(p)))
def pth(c):
    p,e=member0(c,"GetPathName",default="");return "" if e else str(p or "")
def mdl(c):
    m,e=member0(c,"GetModelDoc2",default=None);return None if e else m
def fallback_pn(p):
    m=re.match(r"(K01-[PBA]-\d{3})",Path(p).stem,re.I);return m.group(1).upper() if m else Path(p).stem
def props(m):
    out={}
    if m is None:return out
    ext,_=member0(m,"Extension",default=None);mgr=ext.CustomPropertyManager("")
    for k in PROPS:
        try:
            raw,res,was=mgr.Get2(k);v=res or raw or ""
        except Exception:v=""
        if v:out[k]=str(v)
    return out
def swmat(m):
    if m is None:return ""
    cm,_=member0(m,"ConfigurationManager",default=None);cfg,_=member0(cm,"ActiveConfiguration",default=None)
    cn,_=member0(cfg,"Name",default="Default")
    raw,e=call(m,"GetMaterialPropertyName2",str(cn),default=None)
    if e or raw is None:return ""
    if isinstance(raw,tuple):
        x=[v for v in raw if isinstance(v,str) and v];return x[-1] if x else ""
    return str(raw)
def main():
    pythoncom.CoInitialize();master=json.loads(MASTER.read_text(encoding="utf-8"));mparts=master.get("parts",{})
    sw=win32com.client.GetActiveObject("SldWorks.Application");asm,_=member0(sw,"ActiveDoc",default=None)
    if asm is None or int(member0(asm,"GetType",default=0)[0])!=2:raise RuntimeError("Open active K01 assembly")
    cs,e=call(asm,"GetComponents",False,default=None)
    if e:raise RuntimeError(e)
    cs=[c for c in as_list(cs) if c is not None and pth(c)]
    cnt=Counter(norm(pth(c)) for c in cs);first={}
    for c in cs:first.setdefault(norm(pth(c)),c)
    rows=[];seen=set()
    for key,q in sorted(cnt.items(),key=lambda kv:Path(kv[0]).name.lower()):
        c=first[key];path=pth(c);m=mdl(c);pr=props(m)
        id=pr.get("PartNo") or fallback_pn(path);seen.add(id);mp=mparts.get(id,{})
        rows.append({
          "PartNo":id,"Qty":q,
          "Description":pr.get("Description") or mp.get("description",""),
          "MakeBuy":pr.get("MakeBuy") or ("BUY" if "-B-" in id else "MAKE" if "-P-" in id else ""),
          "MaterialSpec":pr.get("MaterialSpec") or mp.get("material",""),
          "SWMaterial":swmat(m),"Revision":pr.get("Revision",""),
          "LifecycleStatus":pr.get("LifecycleStatus") or mp.get("status",""),
          "File":path,"Source":"ASSEMBLY"
        })
    for id,mp in mparts.items():
        if id in seen or "-B-" not in id or "RETIRED" in str(mp.get("status","")).upper():continue
        rows.append({"PartNo":id,"Qty":"","Description":mp.get("description",""),"MakeBuy":"BUY",
          "MaterialSpec":mp.get("material",""),"SWMaterial":"","Revision":"",
          "LifecycleStatus":mp.get("status",""),"File":"","Source":"MASTER_ONLY_QTY_OPEN"})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    fields=["PartNo","Qty","Description","MakeBuy","MaterialSpec","SWMaterial","Revision","LifecycleStatus","File","Source"]
    with OUT.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    REP.parent.mkdir(parents=True,exist_ok=True)
    REP.write_text(json.dumps({"schema":"k01_bom_from_sw_v3","status":"PASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),"instances":len(cs),"rows":len(rows),
      "csv":str(OUT),"authority":"Qty=SolidWorks assembly; properties=SW synchronized from master; master fallback allowed"},
      indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] BOM:",OUT);print("Rows:",len(rows),"Instances:",len(cs));return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:traceback.print_exc();raise
