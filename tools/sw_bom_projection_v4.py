from __future__ import annotations
import csv,json,os,re,traceback
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import pythoncom,win32com.client
from sw_com import member0,call,as_list
R=Path(r"D:\BreshevEngineering\marvilon-k01");M=R/"master"/"K01_master.json"
OUT=R/"bom"/"K01_BOM_FROM_SW.csv";REP=R/"reports"/"cad"/"current"/"K01_BOM_FROM_SW.json"
def norm(p):return os.path.normcase(os.path.normpath(str(p)))
def pth(c):
    p,e=member0(c,"GetPathName",default="");return "" if e else str(p or "")
def mdl(c):
    m,e=member0(c,"GetModelDoc2",default=None);return None if e else m
def fallback(p):
    x=re.match(r"(K01-[PBA]-\d{3})",Path(p).stem,re.I);return x.group(1).upper() if x else Path(p).stem
def props(m):
    if m is None:return {}
    ext,_=member0(m,"Extension",default=None);mgr=ext.CustomPropertyManager("");o={}
    for k in ("PartNo","Description","MaterialSpec","MakeBuy","Revision","LifecycleStatus"):
        try:r,res,w=mgr.Get2(k);v=res or r or ""
        except Exception:v=""
        if v:o[k]=str(v)
    return o
def swmat(m):
    if m is None:return ""
    cm,_=member0(m,"ConfigurationManager",default=None);cf,_=member0(cm,"ActiveConfiguration",default=None);cn,_=member0(cf,"Name",default="Default")
    raw,e=call(m,"GetMaterialPropertyName2",str(cn),default=None)
    if e or raw is None:return ""
    if isinstance(raw,tuple):
        a=[v for v in raw if isinstance(v,str) and v];return a[-1] if a else ""
    return str(raw)
def main():
    pythoncom.CoInitialize();data=json.loads(M.read_text(encoding="utf-8"));mp=data.get("parts",{})
    sw=win32com.client.GetActiveObject("SldWorks.Application");a,_=member0(sw,"ActiveDoc",default=None)
    if a is None or int(member0(a,"GetType",default=0)[0])!=2:raise RuntimeError("Open active K01 assembly")
    cs,e=call(a,"GetComponents",False,default=None)
    if e:raise RuntimeError(e)
    cs=[c for c in as_list(cs) if c is not None and pth(c)]
    cnt=Counter(norm(pth(c)) for c in cs);first={}
    for c in cs:first.setdefault(norm(pth(c)),c)
    rows=[];seen=set()
    for k,q in sorted(cnt.items(),key=lambda x:Path(x[0]).name.lower()):
        c=first[k];path=pth(c);m=mdl(c);pr=props(m);id=pr.get("PartNo") or fallback(path);seen.add(id);d=mp.get(id,{})
        rows.append({"PartNo":id,"Qty":q,"Description":pr.get("Description") or d.get("description",""),
          "MakeBuy":pr.get("MakeBuy") or ("BUY" if "-B-" in id else "MAKE" if "-P-" in id else ""),
          "MaterialSpec":pr.get("MaterialSpec") or d.get("material",""),"SWMaterial":swmat(m),
          "Revision":pr.get("Revision",""),"LifecycleStatus":pr.get("LifecycleStatus") or d.get("status",""),
          "File":path,"Source":"ASSEMBLY"})
    for id,d in sorted(mp.items()):
        if id in seen:continue
        st=str(d.get("status","")).upper();qty=d.get("qty_design",0)
        if not qty or "RETIRED" in st or "OBSOLETE" in st:continue
        rows.append({"PartNo":id,"Qty":qty,"Description":d.get("description",""),
          "MakeBuy":"BUY" if "-B-" in id else "MAKE" if "-P-" in id else "",
          "MaterialSpec":d.get("material",""),"SWMaterial":"","Revision":"",
          "LifecycleStatus":d.get("status",""),"File":"","Source":"MASTER_ONLY_PLANNED"})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    fields=["PartNo","Qty","Description","MakeBuy","MaterialSpec","SWMaterial","Revision","LifecycleStatus","File","Source"]
    with OUT.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    missing=[r["PartNo"] for r in rows if not r["Description"] or not r["MaterialSpec"] or not r["LifecycleStatus"]]
    REP.parent.mkdir(parents=True,exist_ok=True);REP.write_text(json.dumps({
      "schema":"k01_bom_from_sw_v4","status":"PASS" if not missing else "WARN_INCOMPLETE",
      "created_utc":datetime.now(timezone.utc).isoformat(),"instances":len(cs),"rows":len(rows),
      "missing_control_metadata":missing,"csv":str(OUT)},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS]" if not missing else "[WARN]","BOM:",OUT);print("Rows:",len(rows),"Instances:",len(cs),"Missing:",missing);return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:traceback.print_exc();raise
