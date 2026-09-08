from __future__ import annotations
import json, math, os, shutil, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
import pythoncom, win32com.client
from sw_com import member0,call,as_list

REPO=Path(r"D:\BreshevEngineering\marvilon-k01")
CAD=Path(r"D:\Marvilon\K01\cad")
ASM_PATH=CAD/"assemblies"/"K01-A-001_Calibration_Module.SLDASM"
P003_SRC=CAD/"parts"/"K01-P-003_Cartridge_Body.SLDPRT"
P016_SRC=CAD/"parts"/"K01-P-016_Long_Run_Interface_Boss.SLDPRT"
OUT=CAD/"candidates"
REPORT=REPO/"reports"/"cad"/"current"/"K01_GATE04B_DATUM_C_BUILD.json"

def np(p):return os.path.normcase(os.path.normpath(str(p)))
def mem(o,n,d=None):
    v,e=member0(o,n,default=d);return d if e else v
def cp(c):return str(mem(c,"GetPathName","") or "")
def comps(a):
    x,e=call(a,"GetComponents",False,default=None)
    if e:raise RuntimeError(e)
    return [c for c in as_list(x) if c is not None]
def find(rows,p):return [c for c in rows if np(cp(c))==np(p)]
def T(c):
    t=mem(c,"Transform2",None);a=mem(t,"ArrayData",None)
    if a is None:raise RuntimeError("Transform2")
    return [float(v) for v in list(a)]
def l2a(t,p):
    ex=t[:3];ey=t[3:6];ez=t[6:9];tr=t[9:12]
    return [tr[i]+ex[i]*p[0]+ey[i]*p[1]+ez[i]*p[2] for i in range(3)]
def a2l(t,q):
    ex=t[:3];ey=t[3:6];ez=t[6:9];tr=t[9:12];d=[q[i]-tr[i] for i in range(3)]
    return [sum(ex[i]*d[i] for i in range(3)),
            sum(ey[i]*d[i] for i in range(3)),
            sum(ez[i]*d[i] for i in range(3))]
def openp(sw,p):
    er=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    wr=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    m=sw.OpenDoc6(str(p),1,1,"",er,wr)
    if isinstance(m,tuple):m=next((x for x in m if x is not None and hasattr(x,"_oleobj_")),None)
    if m is None:raise RuntimeError(f"OpenDoc6 {p}: e={er.value} w={wr.value}")
    title=mem(m,"GetTitle","");ae=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc2(title,False,ae);a=mem(sw,"ActiveDoc",None)
    if np(mem(a,"GetPathName",""))!=np(p):raise RuntimeError("activation")
    return a
def body(m):
    b,e=call(m,"GetBodies2",0,True,default=None)
    if e:raise RuntimeError(e)
    r=[x for x in as_list(b) if x is not None]
    if len(r)!=1:raise RuntimeError(f"body count {len(r)}")
    return r[0]
def faces(m):
    f,e=member0(body(m),"GetFaces",default=None)
    if e:raise RuntimeError(e)
    return as_list(f)
def cylinders(m):
    out=[]
    for i,f in enumerate(faces(m)):
        s=mem(f,"GetSurface",None)
        if s is None or not bool(mem(s,"IsCylinder",False)):continue
        p=mem(s,"CylinderParams",None)
        if p is None:continue
        p=[float(v) for v in list(p)]
        ar=mem(f,"GetArea",None)
        owner=mem(f,"GetFeature",None)
        out.append({"face":f,"i":i,"origin":p[:3],"axis":p[3:6],
                    "D_mm":2000*p[6],"area_mm2":None if ar is None else float(ar)*1e6,
                    "owner":owner,"owner_name":str(mem(owner,"Name","") or ""),
                    "owner_type":str(mem(owner,"GetTypeName2","") or "")})
    return out
def planes(m):
    out=[]
    for i,f in enumerate(faces(m)):
        s=mem(f,"GetSurface",None)
        if s is None or not bool(mem(s,"IsPlane",False)):continue
        p=mem(s,"PlaneParams",None)
        if p is None:continue
        p=[float(v) for v in list(p)];ar=mem(f,"GetArea",None)
        out.append({"face":f,"i":i,"normal":p[:3],"point":p[3:6],
                    "area_mm2":None if ar is None else float(ar)*1e6})
    return out
def save(m,p):
    rc,e=call(m,"SaveAs3",str(p),0,1,default=None)
    if e or not p.exists():raise RuntimeError(e or f"Save {p}")
def latest_profile(m):
    f,e=member0(m,"FirstFeature",default=None);r=[]
    while f is not None:
        if str(mem(f,"GetTypeName2",""))=="ProfileFeature":r.append(f)
        f,e=member0(f,"GetNextFeature",default=None)
        if e:break
    return r[-1] if r else None
def select(o,append=False,mark=0,label="obj"):
    ok,e=call(o,"Select2",append,mark,default=False)
    if e or not ok:raise RuntimeError(f"{label} Select2: {e or ok}")
def delete_feature(m,f):
    call(m,"ClearSelection2",True,default=None);select(f,False,0,"feature")
    rc,e=call(m,"EditDelete",default=False)
    if e or not rc:raise RuntimeError(e or "EditDelete failed")
def target_C(rows):
    # Actual P016 BREP proves provisional C is D3.3 at local (12,0,20) mm,
    # while the other three D3.3 holes are the M4 tap-drill pattern.
    def score(r):
        o=r["origin"];ax=r["axis"]
        return (abs(r["D_mm"]-3.3)*100 +
                abs(o[0]-0.012)*1000+abs(o[1])*1000+abs(o[2]-0.020)*1000+
                abs(abs(ax[2])-1)*100)
    c=[r for r in rows if abs(r["D_mm"]-3.3)<0.02 and abs(abs(r["axis"][2])-1)<1e-6]
    if not c:raise RuntimeError("No P016 D3.3 candidates")
    return min(c,key=score)
def build_p016(sw,src,dst,step):
    shutil.copy2(src,dst);m=openp(sw,dst)
    before=cylinders(m);t=target_C(before)
    print(f"[P016] actual provisional C: face={t['i']} D={t['D_mm']:.6f} "
          f"origin={t['origin']} owner={t['owner_name']} / {t['owner_type']}")
    if t["owner"] is None:raise RuntimeError("Target face owner feature unavailable")

    # Ensure the owner is not the three-hole M4 pattern.
    owned=[r for r in before if r["owner_name"]==t["owner_name"] and abs(r["D_mm"]-3.3)<0.02]
    print("[P016] D3.3 cylinders owned by target feature:",len(owned))
    if len(owned)!=1:
        raise RuntimeError("Target C owner also controls other D3.3 holes; refuse destructive edit.")

    center=t["origin"][:]
    delete_feature(m,t["owner"]);call(m,"ForceRebuild3",False,default=None)
    after_delete=cylinders(m)
    old_at_target=[r for r in after_delete if abs(r["D_mm"]-3.3)<0.02 and
                   math.hypot(r["origin"][0]-center[0],r["origin"][1]-center[1])<1e-4]
    if old_at_target:raise RuntimeError("Old C hole still present after feature delete")
    remaining_m4=[r for r in after_delete if abs(r["D_mm"]-3.3)<0.02]
    if len(remaining_m4)!=3:
        raise RuntimeError(f"Expected 3 M4 tap-drill cylinders after C delete; got {len(remaining_m4)}")

    # Datum-A top face z≈20 mm; select large plane normal Z.
    ps=planes(m)
    top=[r for r in ps if abs(r["point"][2]-center[2])<5e-5 and
         abs(abs(r["normal"][2])-1)<1e-6 and (r["area_mm2"] or 0)>300]
    if not top:raise RuntimeError("P016 top Datum-A face not found")
    face=max(top,key=lambda r:r["area_mm2"])["face"]
    call(m,"ClearSelection2",True,default=None);select(face,False,0,"P016 Datum A face")
    sm=mem(m,"SketchManager",None);fm=mem(m,"FeatureManager",None)
    _,e=call(sm,"InsertSketch",True,default=None)
    if e:raise RuntimeError(e)
    sk=mem(sm,"ActiveSketch",None)
    if sk is None:raise RuntimeError("P016 C sketch not active")
    old=None
    try:old=sm.AddToDB;sm.AddToDB=True
    except Exception:pass
    circ,e=call(sm,"CreateCircleByRadius",center[0],center[1],center[2],0.0015,default=None)
    if e or circ is None:raise RuntimeError(e or "P016 CreateCircleByRadius")
    if old is not None:
        try:sm.AddToDB=old
        except Exception:pass
    sf=None
    try:sf=sk.GetFeature()
    except Exception:pass
    call(sm,"InsertSketch",True,default=None)
    if sf is None:sf=latest_profile(m)
    if sf is None:raise RuntimeError("P016 new C sketch")
    try:sf.Name="K01_SKETCH_DATUM_C_PRESS_PIN_HOLE"
    except Exception:pass
    call(m,"ClearSelection2",True,default=None);select(sf,False,0,"P016 C sketch")
    # Blind 4 mm both-sided call: body exists only inward from Datum A.
    cut,e=call(fm,"FeatureCut4",
        False,False,False,0,0,0.004,0.004,
        False,False,False,False,0.0,0.0,
        False,False,False,False,
        False,False,True,False,False,False,
        default=None)
    if e or cut is None:raise RuntimeError(e or "P016 FeatureCut4")
    try:cut.Name="K01_F_DATUM_C_PRESS_PIN_HOLE"
    except Exception:pass
    call(m,"ForceRebuild3",False,default=None)
    aft=cylinders(m)
    new=[r for r in aft if abs(r["D_mm"]-3.0)<0.02 and
         math.hypot(r["origin"][0]-center[0],r["origin"][1]-center[1])<2e-4]
    if not new:
        for r in aft:print("[P016 BREP]",r["i"],r["D_mm"],r["origin"],r["area_mm2"],r["owner_name"])
        raise RuntimeError("New Ø3 C cylinder not found")
    chosen=min(new,key=lambda r:abs((r["area_mm2"] or 0)-math.pi*3*4))
    save(m,dst);save(m,step)
    return {"C_local_center_m":center,"new_D_mm":chosen["D_mm"],
            "new_area_mm2":chosen["area_mm2"],"deleted_owner":t["owner_name"],
            "remaining_M4_D3p3_count":len([r for r in aft if abs(r["D_mm"]-3.3)<0.02])}

def build_p003(sw,src,dst,step,target):
    shutil.copy2(src,dst);m=openp(sw,dst)
    b=body(m);bb=mem(b,"GetBodyBox",None)
    if bb is None:raise RuntimeError("P003 bbox")
    bb=[float(v) for v in list(bb)]
    datumA=bb[0]+0.003
    target=[datumA,target[1],target[2]]
    ps=planes(m)
    fs=[r for r in ps if abs(r["point"][0]-datumA)<3e-5 and
        abs(abs(r["normal"][0])-1)<1e-6 and (r["area_mm2"] or 0)>500]
    if not fs:raise RuntimeError("P003 Datum-A face")
    face=max(fs,key=lambda r:r["area_mm2"])["face"]
    call(m,"ClearSelection2",True,default=None);select(face,False,0,"P003 Datum A")
    sm=mem(m,"SketchManager",None);fm=mem(m,"FeatureManager",None)
    _,e=call(sm,"InsertSketch",True,default=None)
    if e:raise RuntimeError(e)
    sk=mem(sm,"ActiveSketch",None)
    if sk is None:raise RuntimeError("P003 sketch")
    old=None
    try:old=sm.AddToDB;sm.AddToDB=True
    except Exception:pass
    # CAD nominal 3.02 mm. Drawing tolerance +0.01/0.
    circ,e=call(sm,"CreateCircleByRadius",target[0],target[1],target[2],0.00151,default=None)
    if e or circ is None:raise RuntimeError(e or "P003 C circle")
    if old is not None:
        try:sm.AddToDB=old
        except Exception:pass
    sf=None
    try:sf=sk.GetFeature()
    except Exception:pass
    call(sm,"InsertSketch",True,default=None)
    if sf is None:sf=latest_profile(m)
    try:sf.Name="K01_SKETCH_DATUM_C_MATING_HOLE"
    except Exception:pass
    call(m,"ClearSelection2",True,default=None);select(sf,False,0,"P003 C sketch")
    cut,e=call(fm,"FeatureCut4",
        False,False,False,0,0,0.004,0.004,
        False,False,False,False,0.0,0.0,
        False,False,False,False,
        False,False,True,False,False,False,
        default=None)
    if e or cut is None:raise RuntimeError(e or "P003 C cut")
    try:cut.Name="K01_F_DATUM_C_MATING_HOLE"
    except Exception:pass
    call(m,"ForceRebuild3",False,default=None)
    c=[r for r in cylinders(m) if abs(r["D_mm"]-3.02)<0.02]
    if not c:raise RuntimeError("P003 Ø3.02 mating hole BREP not found")
    chosen=min(c,key=lambda r:sum((r["origin"][i]-target[i])**2 for i in range(3)))
    save(m,dst);save(m,step)
    return {"C_local_target_m":target,"D_mm":chosen["D_mm"],
            "drawing_tolerance":"+0.01/0"}

def main():
    pythoncom.CoInitialize()
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev=str(mem(sw,"RevisionNumber",""))
    asm=mem(sw,"ActiveDoc",None)
    if asm is None or int(mem(asm,"GetType",0))!=2 or np(mem(asm,"GetPathName",""))!=np(ASM_PATH):
        raise RuntimeError(f"Open stable {ASM_PATH}, Fully Resolved and active.")
    rows=comps(asm);p3=find(rows,P003_SRC);p16=find(rows,P016_SRC)
    if len(p3)!=1 or len(p16)!=1:raise RuntimeError(f"P003/P016 count {len(p3)}/{len(p16)}")
    t3=T(p3[0]);t16=T(p16[0])

    OUT.mkdir(parents=True,exist_ok=True);stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    p16c=OUT/f"K01-P-016_Long_Run_Interface_Boss_GATE04B_DATUMC_V4_{stamp}.SLDPRT"
    p16s=p16c.with_suffix(".STEP")
    p3c=OUT/f"K01-P-003_Cartridge_Body_GATE04B_DATUMC_V4_{stamp}.SLDPRT"
    p3s=p3c.with_suffix(".STEP")

    print("[INFO] P016: replace actual provisional Ø3.3 C feature with Ø3 × 4 blind...")
    r16=build_p016(sw,P016_SRC,p16c,p16s)
    q=l2a(t16,r16["C_local_center_m"]);p=a2l(t3,q)
    print("[INFO] C assembly coordinate:",q)
    print("[INFO] C mapped into P003 local:",p)
    print("[INFO] P003: create Ø3.02 mating hole at mapped C...")
    r3=build_p003(sw,P003_SRC,p3c,p3s,p)

    # Diamond pin specification: round press shank plus radial-relieved locating end.
    # With P003 hole 3.020..3.030 and tangential pin major 2.990..3.000,
    # total tangential clearance is 0.020..0.040 mm.
    # At R12 this corresponds to approx ±0.048..±0.095 deg half-angle play.
    min_clear=3.020-3.000;max_clear=3.030-2.990
    ang_min=math.degrees(math.atan((min_clear/2)/12.0))
    ang_max=math.degrees(math.atan((max_clear/2)/12.0))
    rep={
      "schema":"k01_gate04b_v4_actual_feature_replacement",
      "status":"PASS","created_utc":datetime.now(timezone.utc).isoformat(),
      "solidworks_revision":rev,
      "P016":{"native":str(p16c),"step":str(p16s),"result":r16},
      "P003":{"native":str(p3c),"step":str(p3s),"result":r3},
      "P017":{
        "material":"EN 1.4404 / AISI 316L baseline",
        "press_shank":"Ø3 p6 ×4 into P016 Ø3 H7",
        "protrusion_mm":2.0,
        "locating_end_tangential_major_mm":"3.00 -0.01/0",
        "locating_end_radial_minor_mm":"2.80 ±0.02",
        "P003_mating_hole_mm":"Ø3.02 +0.01/0",
        "clocking_half_angle_clearance_deg":[ang_min,ang_max],
        "note":"Mechanical clocking freeze; optical target angular acceptance remains separate."
      },
      "datum_scheme":{"A":"mating face","B":"Ø10 H7/g6 pilot","C":"relieved/diamond locator"},
      "release_status":"CANDIDATES_PENDING_ASSEMBLY_QA"
    }
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("="*80);print("K01 Gate04B v4 RESULT: PASS")
    print("P016:",p16c);print("P003:",p3c);print("Report:",REPORT)
    return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:
        print("FAIL: Gate04B v4");traceback.print_exc();raise SystemExit(1)
