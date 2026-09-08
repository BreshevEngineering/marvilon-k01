from __future__ import annotations
import argparse,json,os,re,sys,traceback
from pathlib import Path
import pythoncom,win32com.client
from sw_com import member0,call,as_list

ROOT=Path(r"D:\BreshevEngineering\marvilon-k01")
MASTER=ROOT/"master"/"K01_master.json"

def pth(c):
    p,e=member0(c,"GetPathName",default="");return "" if e else str(p or "")
def pn(path):
    s=Path(path).stem;m=re.match(r"(K01-[PBA]-\d{3})",s,re.I)
    return m.group(1).upper() if m else ""
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    pythoncom.CoInitialize()
    master=json.loads(MASTER.read_text(encoding="utf-8"));parts=master.get("parts",{})
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    asm,_=member0(sw,"ActiveDoc",default=None)
    if asm is None or int(member0(asm,"GetType",default=0)[0])!=2:raise RuntimeError("Open K01 assembly")
    cs,e=call(asm,"GetComponents",False,default=None)
    if e:raise RuntimeError(e)
    seen=set();changes=[]
    for c in as_list(cs):
        path=pth(c);id=pn(path)
        if not id or id in seen or id not in parts:continue
        seen.add(id);m,_=member0(c,"GetModelDoc2",default=None)
        if m is None:continue
        mp=parts[id]
        desired={
          "PartNo":id,
          "Description":str(mp.get("description","")),
          "MaterialSpec":str(mp.get("material","")),
          "MakeBuy":"BUY" if "-B-" in id else "MAKE",
          "LifecycleStatus":str(mp.get("status",""))
        }
        ext,_=member0(m,"Extension",default=None)
        mgr=ext.CustomPropertyManager("")
        for k,v in desired.items():
            old=""
            try:
                raw,res,was=mgr.Get2(k);old=res or raw or ""
            except Exception:pass
            if str(old)!=v:
                changes.append((m,path,k,str(old),v,mgr))
    print("Proposed custom-property changes:",len(changes))
    for _,path,k,old,new,_ in changes:
        print(Path(path).name,":",k,repr(old),"->",repr(new))
    if not a.apply:
        print("[DRY RUN] No CAD saved.");return 0
    touched=set()
    for m,path,k,old,new,mgr in changes:
        # swCustomPropertyReplaceValue = 1
        try:mgr.Add3(k,30,new,1)
        except Exception:
            try:mgr.Set2(k,new)
            except Exception as exc:raise RuntimeError(f"{path} {k}: {exc}")
        touched.add((m,path))
    for m,path in touched:
        rc,e=call(m,"Save3",1,default=None)
        if e:raise RuntimeError(e)
    print("[PASS] Custom properties synchronized and saved for",len(touched),"models.")
    return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:traceback.print_exc();raise
