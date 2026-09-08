from __future__ import annotations
import json, math, sys, traceback
from datetime import datetime
from pathlib import Path
import pythoncom
import win32com.client
from sw_com import member0, call

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports"/"cad"/"current"/"K01_P007_GATE03E_V5_BUILD.json"
REPORT.parent.mkdir(parents=True,exist_ok=True)
OUTDIR=Path(r"D:\Marvilon\K01\cad\candidates")
BASE="K01-P-007_Hermetic_Magnetic_Can_GATE03E_V5_CANDIDATE"
P=[(0.0, 8.0), (3.0, 8.0), (3.0, 5.0), (35.0, 5.0), (35.0, 0.0), (34.0, 0.0), (34.0, 4.7), (2.0, 4.7), (2.0, 7.05), (0.0, 7.05)]
EXPECTED_VOLUME=583.4408796614285

def m(v): return float(v)/1000.0

def active_sketch(sm):
    return member0(sm,"ActiveSketch",default=None)

def start_sketch(model,sm):
    _,e=call(sm,"InsertSketch",True,default=None)
    sk,se=active_sketch(sm)
    if sk is None:
        _,e2=call(model,"InsertSketch2",True,default=None)
        sk,se=active_sketch(sm)
    if sk is None: raise RuntimeError(f"Could not start sketch: {e} / {se}")
    return sk

def close_sketch(sm):
    _,e=call(sm,"InsertSketch",True,default=None)
    if e: raise RuntimeError(e)
    sk,se=active_sketch(sm)
    if sk is not None: raise RuntimeError("Sketch did not close")

def latest_profile(model):
    f,e=member0(model,"FirstFeature",default=None)
    found=[]
    while f is not None:
        typ,_=member0(f,"GetTypeName2",default="")
        if str(typ)=="ProfileFeature": found.append(f)
        f,e=member0(f,"GetNextFeature",default=None)
    return found[-1] if found else None

def select(obj,append=False,mark=0):
    ok,e=call(obj,"Select2",bool(append),int(mark),default=False)
    if e or not ok: raise RuntimeError(e or "Select2 returned False")

def body(model):
    b,e=call(model,"GetBodies2",0,True,default=None)
    rows=list(b) if isinstance(b,(tuple,list)) else [b]
    rows=[x for x in rows if x is not None]
    if len(rows)!=1: raise RuntimeError(f"Expected one body, got {len(rows)}")
    return rows[0]

def volume_mm3(b):
    p,e=call(b,"GetMassProperties",1.0,default=None)
    if e or p is None: raise RuntimeError(e or "GetMassProperties failed")
    return float(list(p)[3])*1e9

def bbox_mm(b):
    q,e=member0(b,"GetBodyBox",default=None)
    if e or q is None: raise RuntimeError(e or "GetBodyBox failed")
    return [1000*float(x) for x in list(q)]

def save(model,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    rc,e=call(model,"SaveAs3",str(path),0,1,default=None)
    if e or not path.exists(): raise RuntimeError(e or f"SaveAs3 failed rc={rc}")

def main():
    pythoncom.CoInitialize()
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev,_=member0(sw,"RevisionNumber",default="")
    model,e=member0(sw,"ActiveDoc",default=None)
    if e or model is None: raise RuntimeError(e or "No active doc")
    typ,_=member0(model,"GetType",default=None)
    title,_=member0(model,"GetTitle",default="")
    path,_=member0(model,"GetPathName",default="")
    if int(typ)!=1 or str(path or ""):
        raise RuntimeError("Active document must be NEW UNSAVED blank Part")
    print(f"[INFO] SOLIDWORKS {rev} / {title}")

    sm,_=member0(model,"SketchManager",default=None)
    fm,_=member0(model,"FeatureManager",default=None)
    sk=start_sketch(model,sm)

    old_add=None
    try:
        old_add=sm.AddToDB; sm.AddToDB=True
    except Exception: pass

    axis,e=call(sm,"CreateCenterLine",m(-5),0,0,m(40),0,0,default=None)
    if e or axis is None: raise RuntimeError(e or "centerline failed")
    try: axis.ConstructionGeometry=True
    except Exception: pass

    for p1,p2 in zip(P,P[1:]+P[:1]):
        seg,e=call(sm,"CreateLine",m(p1[0]),m(p1[1]),0,m(p2[0]),m(p2[1]),0,default=None)
        if e or seg is None: raise RuntimeError(e or f"CreateLine failed {p1} -> {p2}")

    if old_add is not None:
        try: sm.AddToDB=old_add
        except Exception: pass

    sf=None
    try: sf=sk.GetFeature()
    except Exception: pass
    close_sketch(sm)
    if sf is None: sf=latest_profile(model)
    if sf is None: raise RuntimeError("Sketch feature not found")

    call(model,"ClearSelection2",True,default=None)
    select(sf,False,0); select(axis,True,16)
    feat,e=call(fm,"FeatureRevolve2",
        True,True,False,False,False,False,0,0,2*math.pi,0.0,
        False,False,0.01,0.01,0,0.0,0.0,True,True,True,default=None)
    if e or feat is None: raise RuntimeError(e or "FeatureRevolve2 failed")

    call(model,"ForceRebuild3",False,default=None)
    b=body(model); vol=volume_mm3(b); box=bbox_mm(b)
    if abs(vol-EXPECTED_VOLUME)>0.1: raise RuntimeError(f"Volume FAIL {vol} vs {EXPECTED_VOLUME}")
    if max(abs(box[i]-[0,-8,-8,35,8,8][i]) for i in range(6))>0.02:
        raise RuntimeError(f"BBox FAIL {box}")

    # material
    mat={"authority":"AISI 316L / EN 1.4404","applied":False,"error":None}
    try:
        cm,_=member0(model,"ConfigurationManager",default=None)
        cfg,_=member0(cm,"ActiveConfiguration",default=None)
        cn,_=member0(cfg,"Name",default="Default")
        _,me=call(model,"SetMaterialPropertyName2",str(cn),"SOLIDWORKS Materials",
                  "AISI Type 316L stainless steel",default=None)
        if me: mat["error"]=me
        else: mat["applied"]=True
    except Exception as ex: mat["error"]=str(ex)

    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    native=OUTDIR/f"{BASE}_{stamp}.SLDPRT"
    step=OUTDIR/f"{BASE}_{stamp}.STEP"
    save(model,native); save(model,step)

    rep={
      "schema":"k01_p007_gate03e_v5_build_v1","status":"PASS",
      "solidworks_revision":str(rev),"native_candidate":str(native),
      "step_candidate":str(step),"body_box_mm":box,"body_volume_mm3":vol,
      "material":mat,"release_status":"CANDIDATE_NOT_RELEASED"
    }
    REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] P007 v5 candidate created")
    print("Native:",native); print("STEP:",step); print("Report:",REPORT)
    return 0

if __name__=="__main__":
    try: sys.exit(main())
    except Exception:
        print("FAIL: P007 Gate03E v5 builder"); traceback.print_exc(); sys.exit(1)
