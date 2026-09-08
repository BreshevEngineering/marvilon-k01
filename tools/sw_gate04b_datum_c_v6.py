from __future__ import annotations
import itertools,json,math,os,shutil,traceback
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

def np(p): return os.path.normcase(os.path.normpath(str(p)))
def mem(o,n,d=None):
    v,e=member0(o,n,default=d); return d if e else v
def cp(c): return str(mem(c,"GetPathName","") or "")
def comps(a):
    x,e=call(a,"GetComponents",False,default=None)
    if e: raise RuntimeError(e)
    return [c for c in as_list(x) if c is not None]
def find(rows,p): return [c for c in rows if np(cp(c))==np(p)]
def T(c):
    t=mem(c,"Transform2",None); a=mem(t,"ArrayData",None)
    if a is None: raise RuntimeError("Transform2.ArrayData")
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
    if isinstance(m,tuple):
        m=next((x for x in m if x is not None and hasattr(x,"_oleobj_")),None)
    if m is None: raise RuntimeError(f"OpenDoc6 failed {p}; e={er.value} w={wr.value}")
    title=mem(m,"GetTitle","")
    ae=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc2(title,False,ae)
    a=mem(sw,"ActiveDoc",None)
    if np(mem(a,"GetPathName",""))!=np(p): raise RuntimeError("Activation failed")
    return a
def body(m):
    b,e=call(m,"GetBodies2",0,True,default=None)
    if e: raise RuntimeError(e)
    r=[x for x in as_list(b) if x is not None]
    if len(r)!=1: raise RuntimeError(f"Body count={len(r)}")
    return r[0]
def faces(m):
    f,e=member0(body(m),"GetFaces",default=None)
    if e: raise RuntimeError(e)
    return as_list(f)
def cyls(m):
    out=[]
    for i,f in enumerate(faces(m)):
        s=mem(f,"GetSurface",None)
        if s is None or not bool(mem(s,"IsCylinder",False)): continue
        p=mem(s,"CylinderParams",None)
        if p is None: continue
        p=[float(v) for v in list(p)]
        ar=mem(f,"GetArea",None);own=mem(f,"GetFeature",None)
        out.append({"face":f,"i":i,"origin":p[:3],"axis":p[3:6],
                    "D":2000*p[6],"area":None if ar is None else float(ar)*1e6,
                    "owner":own,"owner_name":str(mem(own,"Name","") or ""),
                    "owner_type":str(mem(own,"GetTypeName2","") or "")})
    return out
def planes(m):
    out=[]
    for i,f in enumerate(faces(m)):
        s=mem(f,"GetSurface",None)
        if s is None or not bool(mem(s,"IsPlane",False)): continue
        p=mem(s,"PlaneParams",None)
        if p is None: continue
        p=[float(v) for v in list(p)]
        ar=mem(f,"GetArea",None)
        out.append({"face":f,"i":i,"normal":p[:3],"point":p[3:6],
                    "area":None if ar is None else float(ar)*1e6})
    return out
def feature_rows(m):
    f,e=member0(m,"FirstFeature",default=None);out=[]
    while f is not None:
        out.append((f,str(mem(f,"Name","") or ""),str(mem(f,"GetTypeName2","") or "")))
        f,e=member0(f,"GetNextFeature",default=None)
        if e:break
    return out
def select(o,label):
    ok,e=call(o,"Select2",False,0,default=False)
    if e or not ok: raise RuntimeError(f"{label}.Select2 failed: {e or ok}")
def suppress(m,f):
    call(m,"ClearSelection2",True,default=None);select(f,"legacy C owner")
    rc,e=call(m,"EditSuppress2",default=False)
    if not e and rc:return "EditSuppress2"
    rc2,e2=call(f,"SetSuppression2",0,1,None,default=False)
    if e2 or not rc2:raise RuntimeError(f"Suppress failed: {e or rc}; fallback={e2 or rc2}")
    return "SetSuppression2"
def save(m,p):
    rc,e=call(m,"SaveAs3",str(p),0,1,default=None)
    if e or not p.exists(): raise RuntimeError(e or f"Save failed {p}")
def last_profile(m):
    rows=[r for r in feature_rows(m) if r[2]=="ProfileFeature"]
    return rows[-1][0] if rows else None
def make_axis(m,face,name):
    before={r[1] for r in feature_rows(m) if r[2]=="RefAxis"}
    call(m,"ClearSelection2",True,default=None);select(face,"C cylinder face")
    rc,e=call(m,"InsertAxis2",True,default=False)
    if e or not rc:raise RuntimeError(e or "InsertAxis2 failed")
    after=[r for r in feature_rows(m) if r[2]=="RefAxis" and r[1] not in before]
    if not after:raise RuntimeError("New datum axis not found")
    ax=after[-1][0]
    try:ax.Name=name
    except Exception:pass
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
    if sf is None:raise RuntimeError("New sketch feature not found")
    try:sf.Name=skname
    except Exception:pass
    call(m,"ClearSelection2",True,default=None);select(sf,"C sketch")
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

def polar(row):
    x,y=row["origin"][0],row["origin"][1]
    return math.hypot(x,y), math.degrees(math.atan2(y,x))%360.0
def circular_errors(angles):
    a=sorted(angles);g=[(a[(i+1)%3]-a[i])%360 for i in range(3)]
    return max(abs(x-120.0) for x in g),g
def best_m4_triplet(rows):
    c=[r for r in rows if 3.20 <= r["D"] <= 3.40 and abs(abs(r["axis"][2])-1)<1e-6]
    if len(c)<3:raise RuntimeError(f"Need at least 3 M4 tap-drill cylinders; found {len(c)}")
    best=None
    for comb in itertools.combinations(c,3):
        rad=[polar(r)[0]*1000 for r in comb]
        ang=[polar(r)[1] for r in comb]
        err,gaps=circular_errors(ang)
        score=err + max(abs(x-12.0) for x in rad)*10
        if best is None or score<best[0]:best=(score,list(comb),rad,ang,gaps,err)
    if best[5]>0.25 or max(abs(x-12.0) for x in best[2])>0.05:
        raise RuntimeError(f"No valid 3×120° R12 M4 pattern. Best={best[2:]}")
    return best[1],best[2],best[3],best[4],best[5],c

def gap_midpoints(angles):
    a=sorted(angles)
    mids=[]
    for i in range(3):
        a0=a[i];a1=a[(i+1)%3]
        gap=(a1-a0)%360
        mid=(a0+gap/2)%360
        mids.append((gap,mid,a0,a1))
    return mids

def choose_C_angle(angles):
    mids=gap_midpoints(angles)
    maxgap=max(x[0] for x in mids)
    candidates=[x for x in mids if abs(x[0]-maxgap)<0.1]
    # Deterministic: choose midpoint closest to old +X/0° direction.
    def dist0(deg):return min(deg%360,(360-deg)%360)
    return min(candidates,key=lambda x:dist0(x[1]))

def build16(sw,src,dst,step):
    shutil.copy2(src,dst);m=openp(sw,dst)
    feats=feature_rows(m)
    patterns=[(n,t) for _,n,t in feats if "pattern" in t.lower() or "pattern" in n.lower()]
    print("[P016] pattern features:",patterns)

    before=cyls(m)
    m4,rad,ang,gaps,err,all_d33=best_m4_triplet(before)
    print("[P016] M4 R [mm]:",rad)
    print("[P016] M4 angles [deg]:",sorted(ang),"gaps:",gaps,"max spacing error:",err)

    extra=[r for r in all_d33 if r not in m4]
    suppression=None
    if extra:
        # Only suppress an extra legacy/provisional D3.3 if its owner does not own a clamp hole.
        # This supports older pre-CirPattern baseline without damaging the new circular pattern.
        if len(extra)!=1:raise RuntimeError(f"Unexpected extra D3.3 holes: {len(extra)}")
        ex=extra[0]
        owner=ex["owner"]
        if owner is None:raise RuntimeError("Extra D3.3 owner unavailable")
        owner_name=ex["owner_name"]
        owned_m4=[r for r in m4 if r["owner_name"]==owner_name]
        if owned_m4:raise RuntimeError(f"Extra hole shares owner {owner_name} with M4 pattern; refuse suppression")
        suppression=suppress(m,owner);call(m,"ForceRebuild3",False,default=None)
        chk=cyls(m);m4,rad,ang,gaps,err,all_d33=best_m4_triplet(chk)
        if len(all_d33)!=3:raise RuntimeError(f"After suppression expected exactly 3 D3.3 M4 cylinders; got {len(all_d33)}")
        print("[P016] legacy extra C suppressed via",suppression)

    gap,theta,a0,a1=choose_C_angle(ang)
    R=sum(rad)/len(rad)/1000.0
    z=sum(r["origin"][2] for r in m4)/3.0
    center=[R*math.cos(math.radians(theta)),R*math.sin(math.radians(theta)),z]
    print(f"[P016] Selected Datum C midpoint angle={theta:.6f}° between {a0:.6f}° and {a1:.6f}°, R={R*1000:.6f} mm")

    # Engineering ligament checks for current P016 interface:
    boss_R=16.0; oring_R=7.9; hole_r=1.5
    inner=R*1000-hole_r-oring_R
    outer=boss_R-R*1000-hole_r
    nearest_center=2*(R*1000)*math.sin(math.radians(gap/4.0))  # midpoint to nearest M4
    nearest_lig=nearest_center-1.65-hole_r
    print(f"[P016] Ligaments: O-ring↔C={inner:.3f} mm, C↔OD32={outer:.3f} mm, C↔nearest M4 tap={nearest_lig:.3f} mm")
    if min(inner,outer)<2.0 or nearest_lig<2.0:
        raise RuntimeError("Datum C ligament below 2.0-mm design gate")

    ps=planes(m)
    top=[r for r in ps if abs(r["point"][2]-z)<5e-5 and abs(abs(r["normal"][2])-1)<1e-6 and (r["area"] or 0)>300]
    if not top:raise RuntimeError("P016 Datum-A top face not found")
    f=max(top,key=lambda r:r["area"])["face"]
    make_cut(m,f,center,0.0015,0.004,"K01_SKETCH_DATUM_C_PRESS_PIN_HOLE","K01_F_DATUM_C_PRESS_PIN_HOLE")
    call(m,"ForceRebuild3",False,default=None)
    aft=cyls(m)
    new=[r for r in aft if abs(r["D"]-3.0)<0.02 and math.hypot(r["origin"][0]-center[0],r["origin"][1]-center[1])<2e-4]
    if not new:raise RuntimeError("New Ø3 Datum-C cylinder not found")
    chosen=min(new,key=lambda r:abs((r["area"] or 0)-math.pi*3*4))
    make_axis(m,chosen["face"],"K01_DATUM_C_AXIS")
    save(m,dst);save(m,step)
    return {"M4_angles_deg":sorted(ang),"M4_radii_mm":rad,"M4_spacing_error_deg":err,
            "C_angle_deg":theta,"C_radius_mm":R*1000,"C_center_local_m":center,
            "ligament_to_oring_mm":inner,"ligament_to_outer_edge_mm":outer,
            "ligament_to_nearest_M4_mm":nearest_lig,"legacy_suppression":suppression,
            "new_D_mm":chosen["D"],"new_area_mm2":chosen["area"]}

def build3(sw,src,dst,step,target):
    shutil.copy2(src,dst);m=openp(sw,dst)
    bb=mem(body(m),"GetBodyBox",None)
    if bb is None:raise RuntimeError("P003 bbox")
    bb=[float(v) for v in list(bb)]
    datumA=bb[0]+0.003
    target=[datumA,target[1],target[2]]
    ps=planes(m)
    cand=[r for r in ps if abs(r["point"][0]-datumA)<3e-5 and abs(abs(r["normal"][0])-1)<1e-6 and (r["area"] or 0)>500]
    if not cand:raise RuntimeError("P003 Datum-A face not found")
    f=max(cand,key=lambda r:r["area"])["face"]
    make_cut(m,f,target,0.00151,0.004,"K01_SKETCH_DATUM_C_MATING_HOLE","K01_F_DATUM_C_MATING_HOLE")
    call(m,"ForceRebuild3",False,default=None)
    aft=cyls(m)
    c=[r for r in aft if abs(r["D"]-3.02)<0.02]
    if not c:raise RuntimeError("P003 Ø3.02 Datum-C cylinder not found")
    chosen=min(c,key=lambda r:sum((r["origin"][i]-target[i])**2 for i in range(3)))
    make_axis(m,chosen["face"],"K01_DATUM_C_AXIS")
    # P003 flange OD34 edge ligament at R12:
    R=math.hypot(target[1],target[2])*1000
    outer=17.0-R-1.51
    if outer<2.0:raise RuntimeError(f"P003 C outer edge ligament {outer:.3f}<2.0 mm")
    save(m,dst);save(m,step)
    return {"C_center_local_m":target,"D_mm":chosen["D"],"drawing_tolerance":"+0.01/0",
            "outer_edge_ligament_mm":outer}

def main():
    pythoncom.CoInitialize()
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev=str(mem(sw,"RevisionNumber",""))
    a=mem(sw,"ActiveDoc",None)
    if a is None or int(mem(a,"GetType",0))!=2 or np(mem(a,"GetPathName",""))!=np(ASM):
        raise RuntimeError(f"Open stable {ASM}, Fully Resolved and active.")
    rows=comps(a);c3=find(rows,P003);c16=find(rows,P016)
    if len(c3)!=1 or len(c16)!=1:raise RuntimeError(f"P003/P016 count {len(c3)}/{len(c16)}")
    t3=T(c3[0]);t16=T(c16[0])
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S");OUT.mkdir(parents=True,exist_ok=True)
    f16=OUT/f"K01-P-016_Long_Run_Interface_Boss_GATE04B_DATUMC_V6_{stamp}.SLDPRT";s16=f16.with_suffix(".STEP")
    f3=OUT/f"K01-P-003_Cartridge_Body_GATE04B_DATUMC_V6_{stamp}.SLDPRT";s3=f3.with_suffix(".STEP")
    print("[INFO] P016: audit actual circular M4 pattern and derive Datum C from the free angular gap.")
    r16=build16(sw,P016,f16,s16)
    q=l2a(t16,r16["C_center_local_m"]);p=a2l(t3,q)
    print("[INFO] C assembly:",q);print("[INFO] C mapped to P003:",p)
    r3=build3(sw,P003,f3,s3,p)

    minc=3.020-3.000;maxc=3.030-2.990
    amin=math.degrees(math.atan((minc/2)/r16["C_radius_mm"]))
    amax=math.degrees(math.atan((maxc/2)/r16["C_radius_mm"]))
    rep={"schema":"k01_gate04b_v6_pattern_derived_datum_c","status":"PASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),"solidworks_revision":rev,
      "P016":{"native":str(f16),"step":str(s16),"result":r16},
      "P003":{"native":str(f3),"step":str(s3),"result":r3},
      "P017":{"press_shank":"Ø3 p6×4 into P016 Ø3 H7","protrusion_mm":2.0,
              "tangential_major_mm":"3.00 -0.01/0","radial_minor_mm":"2.80 ±0.02",
              "P003_hole":"Ø3.02 +0.01/0",
              "clocking_half_angle_clearance_deg":[amin,amax]},
      "datum_scheme":{"A":"mating face","B":"Ø10 H7/g6 pilot","C":"pattern-derived relieved/diamond locator"},
      "design_logic":"C is separate from the M4 circular pattern and placed at the midpoint of a 120° free gap, maximizing distance to clamp holes while R≈12 mm balances O-ring and boss-edge ligament.",
      "release_status":"CANDIDATES_PENDING_ASSEMBLY_QA"}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("="*84);print("K01 Gate04B v6 RESULT: PASS")
    print("P016:",f16);print("P003:",f3);print("Report:",REPORT);return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:
        print("FAIL: Gate04B v6");traceback.print_exc();raise SystemExit(1)
