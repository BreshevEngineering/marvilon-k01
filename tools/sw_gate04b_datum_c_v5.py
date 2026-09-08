from __future__ import annotations
import json,math,os,shutil,traceback
from datetime import datetime,timezone
from pathlib import Path
import pythoncom,win32com.client
from sw_com import member0,call,as_list

REPO=Path(r"D:\BreshevEngineering\marvilon-k01")
CAD=Path(r"D:\Marvilon\K01\cad")
ASM=CAD/"assemblies"/"K01-A-001_Calibration_Module.SLDASM"
P003=CAD/"parts"/"K01-P-003_Cartridge_Body.SLDPRT"
P016=CAD/"parts"/"K01-P-016_Long_Run_Interface_Boss.SLDPRT"
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
def tra(c):
    t=mem(c,"Transform2",None);a=mem(t,"ArrayData",None)
    if a is None:raise RuntimeError("Transform2 ArrayData")
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
    if m is None:raise RuntimeError(f"OpenDoc6 failed {p}; e={er.value}, w={wr.value}")
    title=mem(m,"GetTitle","");ae=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc2(title,False,ae);a=mem(sw,"ActiveDoc",None)
    if np(mem(a,"GetPathName",""))!=np(p):raise RuntimeError("Document activation failed")
    return a
def body(m):
    b,e=call(m,"GetBodies2",0,True,default=None)
    if e:raise RuntimeError(e)
    r=[x for x in as_list(b) if x is not None]
    if len(r)!=1:raise RuntimeError(f"Body count {len(r)}")
    return r[0]
def faces(m):
    f,e=member0(body(m),"GetFaces",default=None)
    if e:raise RuntimeError(e)
    return as_list(f)
def cyls(m):
    out=[]
    for i,f in enumerate(faces(m)):
        s=mem(f,"GetSurface",None)
        if s is None or not bool(mem(s,"IsCylinder",False)):continue
        p=mem(s,"CylinderParams",None)
        if p is None:continue
        p=[float(v) for v in list(p)];ar=mem(f,"GetArea",None);own=mem(f,"GetFeature",None)
        out.append({"face":f,"i":i,"origin":p[:3],"axis":p[3:6],"D":2000*p[6],
                    "area":None if ar is None else float(ar)*1e6,
                    "owner":own,"owner_name":str(mem(own,"Name","") or ""),
                    "owner_type":str(mem(own,"GetTypeName2","") or "")})
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
                    "area":None if ar is None else float(ar)*1e6})
    return out
def select(o,label):
    ok,e=call(o,"Select2",False,0,default=False)
    if e or not ok:raise RuntimeError(f"{label}.Select2 failed: {e or ok}")
def suppress_feature(m,f):
    call(m,"ClearSelection2",True,default=None);select(f,"legacy C feature")
    rc,e=call(m,"EditSuppress2",default=False)
    if not e and rc:
        return "ModelDoc2.EditSuppress2"
    # Official SW2018 fallback: swSuppressFeature=0, swThisConfiguration=1.
    rc2,e2=call(f,"SetSuppression2",0,1,None,default=False)
    if e2 or not rc2:
        raise RuntimeError(f"Feature suppression failed; EditSuppress2={e or rc}; SetSuppression2={e2 or rc2}")
    return "IFeature.SetSuppression2(0,1,None)"
def save(m,p):
    rc,e=call(m,"SaveAs3",str(p),0,1,default=None)
    if e or not p.exists():raise RuntimeError(e or f"SaveAs3 {p}")
def last_profile(m):
    f,e=member0(m,"FirstFeature",default=None);rows=[]
    while f is not None:
        if str(mem(f,"GetTypeName2",""))=="ProfileFeature":rows.append(f)
        f,e=member0(f,"GetNextFeature",default=None)
        if e:break
    return rows[-1] if rows else None
def target_c(rows):
    c=[r for r in rows if abs(r["D"]-3.3)<0.02 and abs(abs(r["axis"][2])-1)<1e-6]
    if not c:raise RuntimeError("No D3.3 P016 holes found")
    return min(c,key=lambda r:abs(r["origin"][0]-0.012)*1000+abs(r["origin"][1])*1000+abs(r["origin"][2]-0.020)*1000)
def make_cut(m,face,center,radius,depth,skname,featname):
    call(m,"ClearSelection2",True,default=None);select(face,"datum face")
    sm=mem(m,"SketchManager",None);fm=mem(m,"FeatureManager",None)
    _,e=call(sm,"InsertSketch",True,default=None)
    if e:raise RuntimeError(e)
    sk=mem(sm,"ActiveSketch",None)
    if sk is None:raise RuntimeError("ActiveSketch is None")
    old=None
    try:old=sm.AddToDB;sm.AddToDB=True
    except Exception:pass
    seg,e=call(sm,"CreateCircleByRadius",center[0],center[1],center[2],radius,default=None)
    if e or seg is None:raise RuntimeError(e or "CreateCircleByRadius failed")
    if old is not None:
        try:sm.AddToDB=old
        except Exception:pass
    sf=None
    try:sf=sk.GetFeature()
    except Exception:pass
    call(sm,"InsertSketch",True,default=None)
    if sf is None:sf=last_profile(m)
    if sf is None:raise RuntimeError("Sketch feature not found")
    try:sf.Name=skname
    except Exception:pass
    call(m,"ClearSelection2",True,default=None);select(sf,"datum C sketch")
    cut,e=call(fm,"FeatureCut4",
        False,False,False,0,0,depth,depth,
        False,False,False,False,0.0,0.0,
        False,False,False,False,
        False,False,True,False,False,False,
        default=None)
    if e or cut is None:raise RuntimeError(e or "FeatureCut4 failed")
    try:cut.Name=featname
    except Exception:pass
    return cut
def build16(sw,src,dst,step):
    shutil.copy2(src,dst);m=openp(sw,dst);before=cyls(m);t=target_c(before)
    print(f"[P016] C target D={t['D']:.6f} at {t['origin']}; owner={t['owner_name']} / {t['owner_type']}")
    owned=[r for r in before if r["owner_name"]==t["owner_name"] and abs(r["D"]-3.3)<0.02]
    if len(owned)!=1:raise RuntimeError("C owner is not unique among D3.3 cylinders")
    method=suppress_feature(m,t["owner"]);call(m,"ForceRebuild3",False,default=None)
    after=cyls(m)
    m4=[r for r in after if abs(r["D"]-3.3)<0.02]
    if len(m4)!=3:raise RuntimeError(f"After suppress expected 3 clamp D3.3 holes; got {len(m4)}")
    residual=[r for r in m4 if math.hypot(r["origin"][0]-t["origin"][0],r["origin"][1]-t["origin"][1])<1e-4]
    if residual:raise RuntimeError("Legacy C BREP still exists after suppression")
    ps=planes(m)
    top=[r for r in ps if abs(r["point"][2]-t["origin"][2])<5e-5 and abs(abs(r["normal"][2])-1)<1e-6 and (r["area"] or 0)>300]
    if not top:raise RuntimeError("P016 top face not found")
    f=max(top,key=lambda r:r["area"])["face"]
    make_cut(m,f,t["origin"],0.0015,0.004,"K01_SKETCH_DATUM_C_PRESS_PIN_HOLE","K01_F_DATUM_C_PRESS_PIN_HOLE")
    call(m,"ForceRebuild3",False,default=None)
    aft=cyls(m)
    new=[r for r in aft if abs(r["D"]-3.0)<0.02 and math.hypot(r["origin"][0]-t["origin"][0],r["origin"][1]-t["origin"][1])<2e-4]
    if not new:
        for r in aft:print("[BREP]",r["i"],r["D"],r["origin"],r["area"],r["owner_name"])
        raise RuntimeError("New Ø3 C hole not found")
    chosen=min(new,key=lambda r:abs((r["area"] or 0)-math.pi*3*4))
    save(m,dst);save(m,step)
    return {"center":t["origin"],"suppression_method":method,"legacy_owner":t["owner_name"],
            "M4_holes_remaining":len([r for r in aft if abs(r["D"]-3.3)<0.02]),
            "new_D_mm":chosen["D"],"new_area_mm2":chosen["area"]}
def build3(sw,src,dst,step,target):
    shutil.copy2(src,dst);m=openp(sw,dst);bb=mem(body(m),"GetBodyBox",None)
    if bb is None:raise RuntimeError("P003 bbox")
    bb=[float(v) for v in list(bb)];datumA=bb[0]+0.003;target=[datumA,target[1],target[2]]
    ps=planes(m);cand=[r for r in ps if abs(r["point"][0]-datumA)<3e-5 and abs(abs(r["normal"][0])-1)<1e-6 and (r["area"] or 0)>500]
    if not cand:raise RuntimeError("P003 Datum A face not found")
    f=max(cand,key=lambda r:r["area"])["face"]
    make_cut(m,f,target,0.00151,0.004,"K01_SKETCH_DATUM_C_MATING_HOLE","K01_F_DATUM_C_MATING_HOLE")
    call(m,"ForceRebuild3",False,default=None)
    c=[r for r in cyls(m) if abs(r["D"]-3.02)<0.02]
    if not c:raise RuntimeError("P003 Ø3.02 BREP not found")
    chosen=min(c,key=lambda r:sum((r["origin"][i]-target[i])**2 for i in range(3)))
    save(m,dst);save(m,step)
    return {"target":target,"D_mm":chosen["D"],"drawing_tol":"+0.01/0"}
def main():
    pythoncom.CoInitialize();sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev=str(mem(sw,"RevisionNumber",""));a=mem(sw,"ActiveDoc",None)
    if a is None or int(mem(a,"GetType",0))!=2 or np(mem(a,"GetPathName",""))!=np(ASM):
        raise RuntimeError(f"Open stable {ASM}, Fully Resolved and active.")
    rows=comps(a);c3=find(rows,P003);c16=find(rows,P016)
    if len(c3)!=1 or len(c16)!=1:raise RuntimeError(f"P003/P016 count {len(c3)}/{len(c16)}")
    t3=tra(c3[0]);t16=tra(c16[0]);stamp=datetime.now().strftime("%Y%m%d_%H%M%S");OUT.mkdir(parents=True,exist_ok=True)
    f16=OUT/f"K01-P-016_Long_Run_Interface_Boss_GATE04B_DATUMC_V5_{stamp}.SLDPRT";s16=f16.with_suffix(".STEP")
    f3=OUT/f"K01-P-003_Cartridge_Body_GATE04B_DATUMC_V5_{stamp}.SLDPRT";s3=f3.with_suffix(".STEP")
    print("[INFO] P016: suppress unique provisional M4 Hole Wizard C feature; create Ø3×4 blind hole.")
    r16=build16(sw,P016,f16,s16)
    q=l2a(t16,r16["center"]);p=a2l(t3,q)
    print("[INFO] C assembly:",q);print("[INFO] C mapped to P003:",p)
    r3=build3(sw,P003,f3,s3,p)
    minc=3.020-3.000;maxc=3.030-2.990
    amin=math.degrees(math.atan((minc/2)/12));amax=math.degrees(math.atan((maxc/2)/12))
    rep={"schema":"k01_gate04b_v5_suppress_legacy_holewzd","status":"PASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),"solidworks_revision":rev,
      "P016":{"native":str(f16),"step":str(s16),"result":r16},
      "P003":{"native":str(f3),"step":str(s3),"result":r3},
      "P017":{"press_shank":"Ø3 p6×4 into P016 Ø3 H7","protrusion_mm":2.0,
              "tangential_major_mm":"3.00 -0.01/0","radial_minor_mm":"2.80 ±0.02",
              "P003_hole":"Ø3.02 +0.01/0","clocking_half_angle_clearance_deg":[amin,amax]},
      "datum_scheme":{"A":"mating face","B":"Ø10 H7/g6 pilot","C":"relieved/diamond locator"},
      "release_status":"CANDIDATES_PENDING_ASSEMBLY_QA"}
    REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("="*80);print("K01 Gate04B v5 RESULT: PASS");print("P016:",f16);print("P003:",f3);print("Report:",REPORT);return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:
        print("FAIL: Gate04B v5");traceback.print_exc();raise SystemExit(1)
