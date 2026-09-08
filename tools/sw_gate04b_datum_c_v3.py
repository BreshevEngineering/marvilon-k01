from __future__ import annotations
import json, math, os, shutil, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
import pythoncom
import win32com.client
from sw_com import member0, call, as_list

REPO=Path(r"D:\BreshevEngineering\marvilon-k01")
CAD=Path(r"D:\Marvilon\K01\cad")
ASM_PATH=CAD/"assemblies"/"K01-A-001_Calibration_Module.SLDASM"
P003_SRC=CAD/"parts"/"K01-P-003_Cartridge_Body.SLDPRT"
P016_SRC=CAD/"parts"/"K01-P-016_Long_Run_Interface_Boss.SLDPRT"
OUT=CAD/"candidates"
REPORT=REPO/"reports"/"cad"/"current"/"K01_GATE04B_DATUM_C_BUILD.json"

def normpath(p): return os.path.normcase(os.path.normpath(str(p)))

def member(obj,name,default=None):
    v,e=member0(obj,name,default=default)
    if e: return default
    return v

def cpath(c): return str(member(c,"GetPathName","") or "")
def cname(c): return str(member(c,"Name2","") or "")

def comps(asm):
    x,e=call(asm,"GetComponents",False,default=None)
    if e: raise RuntimeError(e)
    return [c for c in as_list(x) if c is not None]

def find_exact(rows,p):
    q=normpath(p)
    return [c for c in rows if normpath(cpath(c))==q]

def Tarray(comp):
    t,e=member0(comp,"Transform2",default=None)
    if e or t is None: raise RuntimeError(e or f"{cname(comp)} Transform2")
    a,e=member0(t,"ArrayData",default=None)
    if e or a is None: raise RuntimeError(e or "ArrayData")
    a=[float(v) for v in list(a)]
    if len(a)!=16: raise RuntimeError("Transform array length")
    return a

def local_to_asm(T,p):
    ex=T[0:3]; ey=T[3:6]; ez=T[6:9]; tr=T[9:12]
    return [
      tr[i]+ex[i]*p[0]+ey[i]*p[1]+ez[i]*p[2] for i in range(3)
    ]

def asm_to_local(T,q):
    ex=T[0:3]; ey=T[3:6]; ez=T[6:9]; tr=T[9:12]
    d=[q[i]-tr[i] for i in range(3)]
    return [
      sum(ex[i]*d[i] for i in range(3)),
      sum(ey[i]*d[i] for i in range(3)),
      sum(ez[i]*d[i] for i in range(3))
    ]

def open_part(sw,path):
    er=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    wr=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    md=sw.OpenDoc6(str(path),1,1,"",er,wr)
    if isinstance(md,tuple):
        md=next((x for x in md if x is not None and hasattr(x,"_oleobj_")),None)
    if md is None: raise RuntimeError(f"OpenDoc6 failed {path}; e={er.value} w={wr.value}")
    title=member(md,"GetTitle","")
    ae=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc2(str(title),False,ae)
    active=member(sw,"ActiveDoc",None)
    ap=member(active,"GetPathName","")
    if normpath(ap)!=normpath(path): raise RuntimeError(f"Activation failed {ap}")
    return active

def feats(model):
    f,e=member0(model,"FirstFeature",default=None)
    while f is not None:
        yield f
        f,e=member0(f,"GetNextFeature",default=None)
        if e: break

def feat(model,name):
    for f in feats(model):
        if str(member(f,"Name",""))==name: return f
    return None

def dim(model,key):
    try:
        d=model.Parameter(key)
        if d is not None:return d
    except Exception:pass
    d,e=call(model,"Parameter",key,default=None)
    if not e and d is not None:return d
    raise RuntimeError(f"Dimension not found {key}")

def dval(d):
    v,e=member0(d,"SystemValue",default=None)
    if e or v is None: raise RuntimeError(e or "SystemValue")
    return float(v)

def dset(d,v):
    try:d.SystemValue=float(v)
    except Exception:d.SetSystemValue3(float(v),2,None)
    if abs(dval(d)-v)>2e-7: raise RuntimeError("Dimension write readback failed")

def body(model):
    b,e=call(model,"GetBodies2",0,True,default=None)
    if e:raise RuntimeError(e)
    r=[x for x in as_list(b) if x is not None]
    if len(r)!=1:raise RuntimeError(f"body count={len(r)}")
    return r[0]

def face_rows(model):
    fs,e=member0(body(model),"GetFaces",default=None)
    if e:raise RuntimeError(e)
    return as_list(fs)

def cylinders(model):
    out=[]
    for i,f in enumerate(face_rows(model)):
        s=member(f,"GetSurface",None)
        if s is None:continue
        if not bool(member(s,"IsCylinder",False)):continue
        p=member(s,"CylinderParams",None)
        if p is None:continue
        p=[float(v) for v in list(p)]
        ar=member(f,"GetArea",None)
        out.append({"face":f,"i":i,"origin":p[:3],"axis":p[3:6],
                    "D_mm":2000*p[6],"area_mm2":None if ar is None else float(ar)*1e6})
    return out

def planes(model):
    out=[]
    for i,f in enumerate(face_rows(model)):
        s=member(f,"GetSurface",None)
        if s is None or not bool(member(s,"IsPlane",False)):continue
        p=member(s,"PlaneParams",None)
        if p is None:continue
        p=[float(v) for v in list(p)]
        ar=member(f,"GetArea",None)
        out.append({"face":f,"i":i,"normal":p[:3],"point":p[3:6],
                    "area_mm2":None if ar is None else float(ar)*1e6})
    return out

def save(model,path):
    rc,e=call(model,"SaveAs3",str(path),0,1,default=None)
    if e or not path.exists():raise RuntimeError(e or f"Save failed {path}")

def latest_profile(model):
    rows=[]
    for f in feats(model):
        if str(member(f,"GetTypeName2",""))=="ProfileFeature":rows.append(f)
    return rows[-1] if rows else None

def latest_axis(model,oldnames):
    rows=[]
    for f in feats(model):
        if str(member(f,"GetTypeName2",""))=="RefAxis" and str(member(f,"Name","")) not in oldnames:
            rows.append(f)
    return rows[-1] if rows else None

def make_axis(model,face,name):
    old={str(member(f,"Name","")) for f in feats(model)}
    call(model,"ClearSelection2",True,default=None)
    ok,e=call(face,"Select2",False,0,default=False)
    if e or not ok:raise RuntimeError(e or "axis face select")
    rc,e=call(model,"InsertAxis2",True,default=False)
    if e or not rc:raise RuntimeError(e or "InsertAxis2")
    ax=latest_axis(model,old)
    if ax is None:raise RuntimeError("new axis not found")
    try:ax.Name=name
    except Exception:pass
    return ax

def build_p016(sw,src,dst,step):
    shutil.copy2(src,dst)
    m=open_part(sw,dst)
    d_dia=dim(m,"D1@Sketch7")
    d_dep=dim(m,"D1@Cut-Extrude6")
    old_d=dval(d_dia); old_dep=dval(d_dep)
    print(f"[P016] baseline C diameter dim={old_d*1000:.6f} mm; cut depth={old_dep*1000:.6f} mm")
    if abs(old_d-0.00302)>2e-5:
        raise RuntimeError("P016 provisional C diameter no longer near 3.02 mm")
    dset(d_dia,0.00300); dset(d_dep,0.00400)
    call(m,"ForceRebuild3",False,default=None)

    rows=cylinders(m)
    print("[P016] cylindrical BREP after edit:")
    for r in rows:
        print(f"  face {r['i']:2d}: D={r['D_mm']:.6f} area={r['area_mm2']} origin={r['origin']} axis={r['axis']}")
    c=[r for r in rows if abs(r["D_mm"]-3.0)<=0.015]
    if not c:
        raise RuntimeError("No Ø3 cylinder found after edit; see printed BREP list.")
    expected=math.pi*3.0*4.0
    chosen=min(c,key=lambda r:abs((r["area_mm2"] or expected)-expected))
    make_axis(m,chosen["face"],"K01_DATUM_C_PRESS_PIN_AXIS")
    fsk=feat(m,"Sketch7"); fcut=feat(m,"Cut-Extrude6")
    try:
        if fsk:fsk.Name="K01_SKETCH_DATUM_C_PRESS_PIN_HOLE"
        if fcut:fcut.Name="K01_F_DATUM_C_PRESS_PIN_HOLE"
    except Exception:pass
    save(m,dst);save(m,step)
    return {
      "old_diameter_mm":old_d*1000,"new_diameter_mm":3.0,
      "old_depth_mm":old_dep*1000,"new_depth_mm":4.0,
      "C_local_center_m":chosen["origin"],
      "C_axis":chosen["axis"],"C_face_area_mm2":chosen["area_mm2"]
    }

def build_p003(sw,src,dst,step,target_local):
    shutil.copy2(src,dst)
    m=open_part(sw,dst)
    b=body(m)
    bb=member(b,"GetBodyBox",None)
    if bb is None:raise RuntimeError("P003 bbox")
    bb=[float(v) for v in list(bb)]
    # Current pilot tip to Datum A = 3.00 mm.
    datumA_x=bb[0]+0.003
    ps=planes(m)
    cand=[r for r in ps if abs(r["point"][0]-datumA_x)<3e-5 and
          abs(abs(r["normal"][0])-1)<1e-6 and (r["area_mm2"] or 0)>500]
    if not cand:
        raise RuntimeError(f"P003 Datum-A face not found at x={datumA_x}")
    face=max(cand,key=lambda r:r["area_mm2"])["face"]

    # Force target onto Datum-A plane while retaining transverse coordinates
    target=[datumA_x,target_local[1],target_local[2]]
    print("[P003] target C local center from assembly mapping:",target)

    call(m,"ClearSelection2",True,default=None)
    ok,e=call(face,"Select2",False,0,default=False)
    if e or not ok:raise RuntimeError(e or "P003 face select")
    sm=member(m,"SketchManager",None); fm=member(m,"FeatureManager",None)
    _,e=call(sm,"InsertSketch",True,default=None)
    if e:raise RuntimeError(e)
    sk=member(sm,"ActiveSketch",None)
    if sk is None:raise RuntimeError("P003 sketch not active")
    old=None
    try:old=sm.AddToDB;sm.AddToDB=True
    except Exception:pass
    circ,e=call(sm,"CreateCircleByRadius",target[0],target[1],target[2],0.00151,default=None)
    if e or circ is None:raise RuntimeError(e or "CreateCircleByRadius")
    if old is not None:
        try:sm.AddToDB=old
        except Exception:pass
    sf=None
    try:sf=sk.GetFeature()
    except Exception:pass
    call(sm,"InsertSketch",True,default=None)
    if sf is None:sf=latest_profile(m)
    if sf is None:raise RuntimeError("P003 C sketch feature not found")
    try:sf.Name="K01_SKETCH_DATUM_C_MATING_HOLE"
    except Exception:pass

    call(m,"ClearSelection2",True,default=None)
    ok,e=call(sf,"Select2",False,0,default=False)
    if e or not ok:raise RuntimeError(e or "P003 C sketch select")
    # Through flange: cut 4 mm in both directions is robust around 3-mm flange.
    cut,e=call(fm,"FeatureCut4",
        False,False,False,0,0,0.004,0.004,
        False,False,False,False,0.0,0.0,
        False,False,False,False,
        False,False,True,False,False,False,
        default=None)
    if e or cut is None:raise RuntimeError(e or "FeatureCut4")
    try:cut.Name="K01_F_DATUM_C_MATING_HOLE"
    except Exception:pass
    call(m,"ForceRebuild3",False,default=None)
    rows=cylinders(m)
    c=[r for r in rows if abs(r["D_mm"]-3.02)<=0.015]
    if not c:
        print("[P003] cylinders:")
        for r in rows:print(r)
        raise RuntimeError("P003 Ø3.02 mating cylinder not found")
    chosen=min(c,key=lambda r:sum((r["origin"][i]-target[i])**2 for i in range(3)))
    make_axis(m,chosen["face"],"K01_DATUM_C_MATING_AXIS")
    save(m,dst);save(m,step)
    return {
      "hole_diameter_nominal_mm":3.02,
      "drawing_tolerance":"+0.01/0",
      "C_local_center_m":chosen["origin"],
      "C_axis":chosen["axis"],
      "datum_A_x_local_mm":datumA_x*1000
    }

def main():
    pythoncom.CoInitialize()
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev=str(member(sw,"RevisionNumber",""))
    asm=member(sw,"ActiveDoc",None)
    if asm is None:raise RuntimeError("Open stable K01-A-001 assembly and make it active")
    typ=member(asm,"GetType",None); path=member(asm,"GetPathName","")
    if int(typ)!=2 or normpath(path)!=normpath(ASM_PATH):
        raise RuntimeError(f"Active document must be stable {ASM_PATH}; got {path}")
    rows=comps(asm)
    p3=find_exact(rows,P003_SRC);p16=find_exact(rows,P016_SRC)
    if len(p3)!=1 or len(p16)!=1:
        raise RuntimeError(f"P003/P016 component count {len(p3)}/{len(p16)}")
    T3=Tarray(p3[0]);T16=Tarray(p16[0])

    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT.mkdir(parents=True,exist_ok=True)
    f16=OUT/f"K01-P-016_Long_Run_Interface_Boss_GATE04B_DATUMC_V3_{stamp}.SLDPRT"
    s16=f16.with_suffix(".STEP")
    f3=OUT/f"K01-P-003_Cartridge_Body_GATE04B_DATUMC_V3_{stamp}.SLDPRT"
    s3=f3.with_suffix(".STEP")

    print("[INFO] Build P016 C press-pin hole...")
    r16=build_p016(sw,P016_SRC,f16,s16)
    C_asm=local_to_asm(T16,r16["C_local_center_m"])
    C_p3=asm_to_local(T3,C_asm)
    print("[INFO] Datum C assembly center:",C_asm)
    print("[INFO] Datum C mapped to P003 local:",C_p3)
    print("[INFO] Build P003 mating hole...")
    r3=build_p003(sw,P003_SRC,f3,s3,C_p3)

    # Kinematic C is a DIAMOND/RELIEVED PIN, not a second exact round locator.
    pin={
      "id":"K01-P-017",
      "description":"Datum C relieved/diamond clocking pin",
      "material":"EN 1.4404 / AISI 316L baseline",
      "press_shank":"Ø3 p6 x 4.0 into P016 Ø3 H7",
      "protrusion_mm":2.0,
      "mating_section":{
        "tangential_major_mm":"3.00 -0.01/0",
        "radial_minor_mm":"2.80 ±0.02",
        "orientation":"relief/flats provide radial freedom; major width acts tangentially"
      },
      "P003_hole":"Ø3.02 +0.01/0 THRU"
    }

    rep={
      "schema":"k01_gate04b_datum_c_v3_diamond_locator",
      "status":"PASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "solidworks_revision":rev,
      "datum_scheme":{
        "A":"P003/P016 mating face",
        "B":"Ø10 H7/g6 central pilot",
        "C":"P017 relieved/diamond pin in P003 round hole; tangential clocking only"
      },
      "P016":{"native":str(f16),"step":str(s16),"result":r16},
      "P003":{"native":str(f3),"step":str(s3),"result":r3},
      "P017":pin,
      "release_status":"CANDIDATES_PENDING_ASSEMBLY_QA",
      "note":"Diamond locator avoids radial overconstraint while retaining simple drilled mating holes."
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("="*80)
    print("K01 Gate04B v3 RESULT: PASS")
    print("P016:",f16)
    print("P003:",f3)
    print("P017: relieved/diamond pin concept")
    print("Report:",REPORT)
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:
        print("FAIL: Gate04B v3");traceback.print_exc();raise SystemExit(1)
