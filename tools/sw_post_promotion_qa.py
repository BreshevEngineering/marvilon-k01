from __future__ import annotations
import hashlib, json, math, os, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
import pythoncom
import win32com.client
from sw_com import member0, call, as_list

REPO=Path(r"D:\BreshevEngineering\marvilon-k01")
CAD=Path(r"D:\Marvilon\K01\cad")
REPORT=REPO/"reports"/"cad"/"current"/"K01_POST_PROMOTION_QA.json"
PROMO=REPO/"reports"/"cad"/"current"/"K01_P003_P007_PRODUCTION_PROMOTION.json"
P003=CAD/"parts"/"K01-P-003_Cartridge_Body.SLDPRT"
P007=CAD/"parts"/"K01-P-007_Hermetic_Magnetic_Can.SLDPRT"
ASM=CAD/"assemblies"/"K01-A-001_Calibration_Module.SLDASM"

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for ch in iter(lambda:f.read(1024*1024),b""): h.update(ch)
    return h.hexdigest()

def comps(asm):
    x,e=call(asm,"GetComponents",False,default=None)
    if e: raise RuntimeError(e)
    return as_list(x)

def cpath(c):
    p,e=member0(c,"GetPathName",default="")
    if e: raise RuntimeError(e)
    return str(p or "")

def cname(c):
    n,_=member0(c,"Name2",default="")
    return str(n or "")

def find_path(rows,path):
    q=os.path.normcase(os.path.normpath(str(path)))
    return [c for c in rows if os.path.normcase(os.path.normpath(cpath(c)))==q]

def one_body(c):
    m,e=member0(c,"GetModelDoc2",default=None)
    if e or m is None: raise RuntimeError(e or f"{cname(c)} unresolved")
    b,e=call(m,"GetBodies2",0,True,default=None)
    if e: raise RuntimeError(e)
    rows=[x for x in as_list(b) if x is not None]
    if len(rows)!=1: raise RuntimeError(f"{cname(c)} body count={len(rows)}")
    return m,rows[0]

def bbox_mm(body):
    a,e=member0(body,"GetBodyBox",default=None)
    if e or a is None: raise RuntimeError(e or "GetBodyBox")
    return [1000*float(x) for x in list(a)]

def cylinders(c):
    m,b=one_body(c)
    fs,e=member0(b,"GetFaces",default=None)
    if e: raise RuntimeError(e)
    out=[]
    for i,f in enumerate(as_list(fs)):
        s,se=member0(f,"GetSurface",default=None)
        if se or s is None: continue
        ok,oe=member0(s,"IsCylinder",default=False)
        if oe or not ok: continue
        p,pe=member0(s,"CylinderParams",default=None)
        if pe or p is None: continue
        p=[float(v) for v in list(p)]
        ar,ae=member0(f,"GetArea",default=None)
        out.append({"i":i,"D_mm":2000*p[6],"area_mm2":None if ae else float(ar)*1e6})
    return out

def mate_audit(model):
    out=[]
    f,e=member0(model,"FirstFeature",default=None)
    while f is not None:
        nm,_=member0(f,"Name",default="")
        ty,_=member0(f,"GetTypeName2",default="")
        if "mate" in str(nm).lower() or "mate" in str(ty).lower():
            sf,_=member0(f,"GetFirstSubFeature",default=None)
            while sf is not None:
                sn,_=member0(sf,"Name",default="")
                st,_=member0(sf,"GetTypeName2",default="")
                code,ce=call(sf,"GetErrorCode2",default=None)
                out.append({"name":str(sn),"type":str(st),"error":None if ce else code})
                sf,_=member0(sf,"GetNextSubFeature",default=None)
        f,e=member0(f,"GetNextFeature",default=None)
        if e: break
    errs=[r for r in out if r["error"] not in (None,0)]
    return {"count":len(out),"error_count":len(errs),"errors":errs}

def main():
    pythoncom.CoInitialize()
    for p in [PROMO,P003,P007,ASM]:
        if not p.exists(): raise FileNotFoundError(p)
    promo=json.loads(PROMO.read_text(encoding="utf-8"))

    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev,_=member0(sw,"RevisionNumber",default="")
    asm,e=member0(sw,"ActiveDoc",default=None)
    if e or asm is None: raise RuntimeError(e or "No active document")
    title,_=member0(asm,"GetTitle",default="")
    path,_=member0(asm,"GetPathName",default="")
    typ,_=member0(asm,"GetType",default=None)
    if int(typ)!=2 or os.path.normcase(os.path.normpath(str(path)))!=os.path.normcase(os.path.normpath(str(ASM))):
        raise RuntimeError(f"Open stable production assembly {ASM}; active={path}")

    call(asm,"ForceRebuild3",False,default=None)
    rows=comps(asm)
    p3=find_path(rows,P003); p7=find_path(rows,P007)
    if len(p3)!=1 or len(p7)!=1:
        raise RuntimeError(f"Stable P003/P007 component count {len(p3)}/{len(p7)}")

    candidate_links=[{"name":cname(c),"path":cpath(c)} for c in rows if "\\candidates\\" in cpath(c).lower()]
    if candidate_links:
        raise RuntimeError(f"Production assembly still links candidates: {candidate_links}")

    _,b7=one_body(p7[0]); bb7=bbox_mm(b7)
    L7=bb7[3]-bb7[0]
    if abs(L7-35.0)>0.02:
        raise RuntimeError(f"P007 stable length {L7:.6f} mm !=35")

    cyl3=cylinders(p3[0])
    od16=[r for r in cyl3 if abs(r["D_mm"]-16.0)<=0.01 and r["area_mm2"] is not None]
    expected=math.pi*16.0*5.0
    if not any(abs(r["area_mm2"]-expected)<=0.5 for r in od16):
        raise RuntimeError(f"P003 OD16x5 rear collar not verified; OD16 faces={od16}")

    candidate_sources=promo.get("source_candidates",{})
    binary={}
    for k,stable in [("P003",P003),("P007",P007)]:
        src=Path(candidate_sources.get(k,""))
        binary[k]={"stable_sha256":sha(stable),"candidate_exists":src.exists()}
        if src.exists():
            binary[k]["candidate_sha256"]=sha(src)
            binary[k]["identical"]=binary[k]["stable_sha256"]==binary[k]["candidate_sha256"]
            if not binary[k]["identical"]:
                raise RuntimeError(f"{k} stable file differs from promoted accepted candidate")

    mates=mate_audit(asm)
    if mates["error_count"]!=0:
        raise RuntimeError(f"Mate errors after promotion: {mates['errors']}")

    rep={
      "schema":"k01_post_promotion_qa_v1","status":"PASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "solidworks_revision":str(rev),"assembly":str(ASM),
      "candidate_links":candidate_links,
      "P007_length_mm":L7,
      "P003_OD16_faces":od16,
      "binary_identity":binary,
      "mates":mates,
      "next":"Archive candidates/history; then continue Datum C and remaining freeze gates."
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] Post-promotion production QA")
    print(f"[PASS] P007 stable L={L7:.6f} mm")
    print("[PASS] P003 rear OD16 x 5 collar verified")
    print(f"[PASS] mate errors={mates['error_count']}")
    print("[PASS] no candidate paths in production assembly")
    print("Report:",REPORT)
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception:
        print("FAIL: K01 post-promotion QA"); traceback.print_exc(); raise SystemExit(1)
