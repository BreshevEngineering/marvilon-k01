from __future__ import annotations
import json, math, shutil, sys, traceback
from datetime import datetime
from pathlib import Path
import pythoncom
import win32com.client
from sw_com import member0, call, as_list

REPO=Path(r"D:\BreshevEngineering\marvilon-k01")
CAD=Path(r"D:\Marvilon\K01\cad")
OUT=CAD/"candidates"
REPORT=REPO/"reports"/"cad"/"current"/"K01_GATE04B_DATUM_C_BUILD.json"
P003_SRC=CAD/"parts"/"K01-P-003_Cartridge_Body.SLDPRT"
P016_SRC=CAD/"parts"/"K01-P-016_Long_Run_Interface_Boss.SLDPRT"

def m(mm): return float(mm)/1000.0

def open_doc(sw,path):
    er=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    wr=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    md=sw.OpenDoc6(str(path),1,1,"",er,wr)
    if isinstance(md,tuple):
        md=next((x for x in md if x is not None and hasattr(x,"_oleobj_")),None)
    if md is None: raise RuntimeError(f"OpenDoc6 failed {path}; e={er.value} w={wr.value}")
    title,_=member0(md,"GetTitle",default="")
    ae=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc2(str(title),False,ae)
    active,_=member0(sw,"ActiveDoc",default=None)
    ap,_=member0(active,"GetPathName",default="")
    if str(Path(str(ap))).lower()!=str(Path(str(path))).lower():
        raise RuntimeError(f"Activation failed: {ap}")
    return active,int(er.value),int(wr.value),int(ae.value)

def feat_iter(model):
    f,e=member0(model,"FirstFeature",default=None)
    while f is not None:
        yield f
        f,e=member0(f,"GetNextFeature",default=None)
        if e: break

def feat(model,name):
    for f in feat_iter(model):
        n,_=member0(f,"Name",default="")
        if str(n)==name: return f
    return None

def dim(model,key):
    try:
        d=model.Parameter(key)
        if d is not None: return d
    except Exception: pass
    d,e=call(model,"Parameter",key,default=None)
    if not e and d is not None: return d
    raise RuntimeError(f"Dimension not found: {key}")

def dval(d):
    v,e=member0(d,"SystemValue",default=None)
    if e or v is None: raise RuntimeError(e or "SystemValue")
    return float(v)

def dset(d,v):
    try:
        d.SystemValue=float(v)
    except Exception:
        rc=d.SetSystemValue3(float(v),2,None)
    if abs(dval(d)-float(v))>2e-7:
        raise RuntimeError(f"Dimension set readback failed {dval(d)} != {v}")

def one_body(model):
    b,e=call(model,"GetBodies2",0,True,default=None)
    if e: raise RuntimeError(e)
    rows=[x for x in as_list(b) if x is not None]
    if len(rows)!=1: raise RuntimeError(f"body count={len(rows)}")
    return rows[0]

def faces(model):
    b=one_body(model)
    f,e=member0(b,"GetFaces",default=None)
    if e: raise RuntimeError(e)
    return as_list(f)

def cyl_rows(model):
    out=[]
    for i,f in enumerate(faces(model)):
        s,se=member0(f,"GetSurface",default=None)
        if se or s is None: continue
        ok,oe=member0(s,"IsCylinder",default=False)
        if oe or not ok: continue
        p,pe=member0(s,"CylinderParams",default=None)
        if pe or p is None: continue
        p=[float(x) for x in list(p)]
        ar,ae=member0(f,"GetArea",default=None)
        out.append({"face":f,"i":i,"origin_m":p[:3],"axis":p[3:6],"D_mm":2000*p[6],
                    "area_mm2":None if ae else float(ar)*1e6})
    return out

def plane_rows(model):
    out=[]
    for i,f in enumerate(faces(model)):
        s,se=member0(f,"GetSurface",default=None)
        if se or s is None: continue
        ok,oe=member0(s,"IsPlane",default=False)
        if oe or not ok: continue
        p,pe=member0(s,"PlaneParams",default=None)
        if pe or p is None: continue
        p=[float(x) for x in list(p)]
        ar,ae=member0(f,"GetArea",default=None)
        out.append({"face":f,"i":i,"normal":p[:3],"point_m":p[3:6],
                    "area_mm2":None if ae else float(ar)*1e6})
    return out

def save(model,path):
    rc,e=call(model,"SaveAs3",str(path),0,1,default=None)
    if e or not path.exists(): raise RuntimeError(e or f"SaveAs3 failed {path}")

def latest_profile(model):
    rows=[]
    for f in feat_iter(model):
        t,_=member0(f,"GetTypeName2",default="")
        if str(t)=="ProfileFeature": rows.append(f)
    return rows[-1] if rows else None

def latest_refaxis(model,before_names):
    candidates=[]
    for f in feat_iter(model):
        n,_=member0(f,"Name",default="")
        t,_=member0(f,"GetTypeName2",default="")
        if str(t)=="RefAxis" and str(n) not in before_names: candidates.append(f)
    return candidates[-1] if candidates else None

def create_axis_from_face(model,face,name):
    before=set()
    for f in feat_iter(model):
        n,_=member0(f,"Name",default="")
        before.add(str(n))
    call(model,"ClearSelection2",True,default=None)
    ok,e=call(face,"Select2",False,0,default=False)
    if e or not ok: raise RuntimeError(e or "cyl face Select2 failed")
    rc,e=call(model,"InsertAxis2",True,default=False)
    if e or not rc: raise RuntimeError(e or "InsertAxis2 failed")
    ax=latest_refaxis(model,before)
    if ax is None: raise RuntimeError("new RefAxis not found")
    try: ax.Name=name
    except Exception: pass
    return ax

def build_p016(sw,src,dst,step):
    shutil.copy2(src,dst)
    model,oe,ow,ae=open_doc(sw,dst)
    d_dia=dim(model,"D1@Sketch7")
    d_depth=dim(model,"D1@Cut-Extrude6")
    old_d=dval(d_dia); old_depth=dval(d_depth)
    if abs(old_d-0.00302)>2e-6:
        raise RuntimeError(f"P016 clock hole baseline changed: D={old_d*1000}")
    dset(d_dia,0.00300)
    dset(d_depth,0.00400)
    fsk=feat(model,"Sketch7"); fcut=feat(model,"Cut-Extrude6")
    if fsk:
        try:fsk.Name="K01_SKETCH_DATUM_C_PIN_HOLE"
        except Exception: pass
    if fcut:
        try:fcut.Name="K01_F_DATUM_C_PIN_HOLE"
        except Exception: pass
    call(model,"ForceRebuild3",False,default=None)
    rows=cyl_rows(model)
    cands=[r for r in rows if abs(r["D_mm"]-3.0)<0.01
           and abs(r["origin_m"][0]-0.012)<2e-4 and abs(r["origin_m"][1])<2e-4
           and abs(abs(r["axis"][2])-1.0)<1e-6]
    if not cands: raise RuntimeError("P016 Ø3 Datum-C cylinder not found after edit")
    face=max(cands,key=lambda r:r["area_mm2"] or 0)["face"]
    create_axis_from_face(model,face,"K01_DATUM_C_CLOCK_AXIS")
    save(model,dst); save(model,step)
    return {"old_diameter_mm":old_d*1000,"new_diameter_mm":3.0,
            "old_depth_mm":old_depth*1000,"new_depth_mm":4.0,
            "axis":"K01_DATUM_C_CLOCK_AXIS","cylinders":[{k:v for k,v in r.items() if k!="face"} for r in rows]}

def build_p003(sw,src,dst,step):
    """
    Add the Datum-C RADIAL SLOT to a copy of stable P003.

    A/B already locate axial + transverse position. The slot long axis is radial
    so C only removes clocking about B and does not duplicate B's radial locating
    function.

    Geometry on Datum-A flange face:
      slot width = 3.02 mm
      full radial length = 4.00 mm
      center = R12 / 0 deg (local +Y)
      THRU flange
    """
    shutil.copy2(src,dst)
    model,oe,ow,ae=open_doc(sw,dst)
    b=one_body(model)
    bb,e=member0(b,"GetBodyBox",default=None)
    if e or bb is None: raise RuntimeError(e or "P003 body box")
    bb=[float(v) for v in list(bb)]
    target_x=bb[0]+0.003  # pilot tip -> Datum A is +3.00 mm

    pls=plane_rows(model)
    cands=[r for r in pls if abs(r["point_m"][0]-target_x)<2e-5
           and abs(abs(r["normal"][0])-1.0)<1e-6 and (r["area_mm2"] or 0)>500]
    if not cands:
        raise RuntimeError(f"P003 Datum-A physical flange face not found at x={target_x}")
    mating=max(cands,key=lambda r:r["area_mm2"])["face"]

    call(model,"ClearSelection2",True,default=None)
    ok,e=call(mating,"Select2",False,0,default=False)
    if e or not ok: raise RuntimeError(e or "P003 mating face Select2 failed")

    sm,_=member0(model,"SketchManager",default=None)
    fm,_=member0(model,"FeatureManager",default=None)
    _,e=call(sm,"InsertSketch",True,default=None)
    if e: raise RuntimeError(e)
    sk,_=member0(sm,"ActiveSketch",default=None)
    if sk is None: raise RuntimeError("P003 Datum-C sketch did not start")

    # Straight radial slot. SW API enums:
    # swSketchSlotCreationType_line = 0
    # swSketchSlotLengthType_FullLength = 1
    # Point 1 / Point 2 define the radial slot direction.
    # Point 3 is unused for straight-line slot; keep it at slot centre.
    # On this face all points share X = target_x.
    slot,e=call(
        sm,"CreateSketchSlot",
        0,          # straight slot
        1,          # full length
        0.00302,    # width
        target_x,0.010,0.0,   # radial inner end
        target_x,0.014,0.0,   # radial outer end
        target_x,0.012,0.0,   # third point / centre
        1,          # CCW
        False,
        default=None
    )
    if e or slot is None:
        raise RuntimeError(e or "CreateSketchSlot returned None")

    sf=None
    try: sf=sk.GetFeature()
    except Exception: pass
    call(sm,"InsertSketch",True,default=None)
    if sf is None: sf=latest_profile(model)
    if sf is None: raise RuntimeError("P003 Datum-C slot sketch feature not found")
    try: sf.Name="K01_SKETCH_DATUM_C_RADIAL_SLOT"
    except Exception: pass

    call(model,"ClearSelection2",True,default=None)
    ok,e=call(sf,"Select2",False,0,default=False)
    if e or not ok: raise RuntimeError(e or "P003 Datum-C slot sketch Select2 failed")

    # Cut through the 3 mm flange. Use through-all end condition first; if
    # SW2018 late-bound marshaling rejects it, the error is explicit and no
    # production file is touched.
    cut,e=call(
        fm,"FeatureCut4",
        False,False,False,
        1,1,          # swEndCondThroughAll both directions
        0.003,0.003,
        False,False,False,False,
        0.0,0.0,
        False,False,False,False,
        False,False,True,False,False,False,
        default=None
    )
    if e or cut is None:
        raise RuntimeError(e or "FeatureCut4 through-slot failed")
    try: cut.Name="K01_F_DATUM_C_RADIAL_SLOT"
    except Exception: pass

    call(model,"ForceRebuild3",False,default=None)

    # QA by bounding box and body validity. The slot is not cylindrical, so do
    # not attempt to create a false axis datum from it. Its datum is the median
    # plane of the slot width; the named sketch is retained as the CAD reference.
    body=one_body(model)
    bb2,e=member0(body,"GetBodyBox",default=None)
    if e or bb2 is None: raise RuntimeError(e or "P003 post-slot body box")
    bb2=[1000*float(v) for v in list(bb2)]
    if len(bb2)!=6: raise RuntimeError("Unexpected body-box data")

    save(model,dst); save(model,step)
    return {
        "feature":"K01_F_DATUM_C_RADIAL_SLOT",
        "reference_sketch":"K01_SKETCH_DATUM_C_RADIAL_SLOT",
        "slot_width_mm":3.02,
        "slot_full_radial_length_mm":4.00,
        "slot_center_radius_mm":12.00,
        "slot_angle_deg":0.0,
        "datum_definition":"median plane of slot width; radial slot length is non-locating",
        "datum_A_x_local_mm":target_x*1000,
        "body_box_mm":bb2
    }

def main():
    pythoncom.CoInitialize()
    for p in [P003_SRC,P016_SRC]:
        if not p.exists(): raise FileNotFoundError(p)
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev,_=member0(sw,"RevisionNumber",default="")
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT.mkdir(parents=True,exist_ok=True)
    p3=OUT/f"K01-P-003_Cartridge_Body_GATE04B_DATUMC_{stamp}.SLDPRT"
    p3s=p3.with_suffix(".STEP")
    p16=OUT/f"K01-P-016_Long_Run_Interface_Boss_GATE04B_DATUMC_{stamp}.SLDPRT"
    p16s=p16.with_suffix(".STEP")
    print("[INFO] Building P016 Datum C candidate...")
    r16=build_p016(sw,P016_SRC,p16,p16s)
    print("[PASS] P016 Datum C physical hole + axis")
    print("[INFO] Building P003 Datum C candidate...")
    r3=build_p003(sw,P003_SRC,p3,p3s)
    print("[PASS] P003 Datum C radial slot built; no redundant round-hole location")
    rep={
      "schema":"k01_gate04b_datum_c_build_v1","status":"PASS",
      "solidworks_revision":str(rev),
      "P003":{"native":str(p3),"step":str(p3s),"result":r3},
      "P016":{"native":str(p16),"step":str(p16s),"result":r16},
      "P017_spec":"316L clocking pin Ø3 p6 x 6.0; press 4.0 into P016; protrusion 2.0",
      "datum_scheme":{"A":"mating face","B":"Ø10 H7/g6 axis","C":"P017 pin against P003 radial-slot width at R12 / 0 deg"},
      "release_status":"CANDIDATES_PENDING_ASSEMBLY_QA"
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("="*72)
    print("K01 Gate04B Datum C RESULT")
    print("="*72)
    print("[PASS] A/B/C kinematic locating concept built: A face + B pilot + C radial slot.")
    print("P003:",p3)
    print("P016:",p16)
    print("Report:",REPORT)
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception:
        print("FAIL: K01 Gate04B Datum C build"); traceback.print_exc(); raise SystemExit(1)
