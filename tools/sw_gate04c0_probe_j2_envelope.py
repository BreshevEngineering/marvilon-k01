from __future__ import annotations
import itertools,json,math,os,traceback
from datetime import datetime,timezone
from pathlib import Path
import pythoncom,win32com.client
from sw_com import member0,call,as_list

REPO=Path(r"D:\BreshevEngineering\marvilon-k01")
CAD=Path(r"D:\Marvilon\K01\cad")
ASM=CAD/"assemblies"/"K01-A-001_Calibration_Module.SLDASM"
P003=CAD/"parts"/"K01-P-003_Cartridge_Body.SLDPRT"
P007=CAD/"parts"/"K01-P-007_Hermetic_Magnetic_Can.SLDPRT"
REPORT=REPO/"reports"/"cad"/"current"/"K01_GATE04C0_J2_ENVELOPE_PROBE.json"

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
def ensure_asm(sw):
    a=mem(sw,"ActiveDoc",None)
    if a is not None and int(mem(a,"GetType",0))==2 and np(mem(a,"GetPathName",""))==np(ASM):
        return a
    er=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    wr=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    md=sw.OpenDoc6(str(ASM),2,1,"",er,wr)
    if isinstance(md,tuple):md=next((x for x in md if x is not None and hasattr(x,"_oleobj_")),None)
    if md is None:raise RuntimeError(f"Open stable A001 failed e={er.value} w={wr.value}")
    ae=win32com.client.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    sw.ActivateDoc2(mem(md,"GetTitle",""),False,ae)
    return mem(sw,"ActiveDoc",None)
def bodyboxes(model):
    b,e=call(model,"GetBodies2",0,True,default=None)
    if e:return []
    out=[]
    for body in [x for x in as_list(b) if x is not None]:
        bb=mem(body,"GetBodyBox",None)
        if bb is not None:out.append([float(v) for v in list(bb)])
    return out
def model(c):
    m,e=member0(c,"GetModelDoc2",default=None);return None if e else m
def corners(bb):
    x0,y0,z0,x1,y1,z1=bb
    for x in (x0,x1):
        for y in (y0,y1):
            for z in (z0,z1):yield [x,y,z]
def comp_bbox_in_p003(c,t3):
    tc=T(c);pts=[]
    m=model(c)
    if m is None:return None
    for bb in bodyboxes(m):
        for p in corners(bb):
            pts.append(a2l(t3,l2a(tc,p)))
    if not pts:return None
    xs=[p[0]*1000 for p in pts];ys=[p[1]*1000 for p in pts];zs=[p[2]*1000 for p in pts]
    rs=[math.hypot(p[1]*1000,p[2]*1000) for p in pts]
    return {"x_min_mm":min(xs),"x_max_mm":max(xs),"r_box_max_mm":max(rs),
            "y_min_mm":min(ys),"y_max_mm":max(ys),"z_min_mm":min(zs),"z_max_mm":max(zs)}

def main():
    pythoncom.CoInitialize();sw=win32com.client.GetActiveObject("SldWorks.Application")
    a=ensure_asm(sw);rows=comps(a);p3=find(rows,P003);p7=find(rows,P007)
    if len(p3)!=1 or len(p7)!=1:raise RuntimeError(f"P003/P007 count {len(p3)}/{len(p7)}")
    t3=T(p3[0]);m3=model(p3[0]);bbs=bodyboxes(m3)
    if len(bbs)!=1:raise RuntimeError("P003 body box")
    rear=max(bbs[0][0],bbs[0][3])*1000
    slab=(rear-6.0,rear+8.0)
    nearby=[]
    for c in rows:
        b=comp_bbox_in_p003(c,t3)
        if b is None:continue
        if b["x_max_mm"]>=slab[0] and b["x_min_mm"]<=slab[1]:
            nearby.append({"component":str(mem(c,"Name2","") or ""),
                           "file":cp(c),"bbox_P003_local":b})
    print("="*92);print("K01 Gate04C0 — J2 READ-ONLY ENVELOPE / M3 FEASIBILITY");print("="*92)
    print(f"P003 rear station = {rear:.6f} mm; inspected slab={slab[0]:.3f}..{slab[1]:.3f} mm")
    for x in nearby:
        b=x["bbox_P003_local"]
        print(f"{x['component'][:45]:45} x={b['x_min_mm']:.2f}..{b['x_max_mm']:.2f} r_box_max={b['r_box_max_mm']:.2f} mm")

    # Pure radial packaging equations for a 3×M3 service flange.
    Dhole=3.4
    L=2.0  # internal project robustness target, not code minimum
    candidates=[]
    for PCD in (26.0,28.0,30.0):
        odmin=PCD+Dhole+2*L
        grooveODmax=PCD-Dhole-2*L
        candidates.append({"PCD_mm":PCD,"M3_clearance_D_mm":Dhole,
                           "design_ligament_mm":L,
                           "minimum_flange_OD_mm":odmin,
                           "maximum_face_groove_OD_mm":grooveODmax})
        print(f"PCD{PCD:.0f}: ODmin={odmin:.1f} mm; face-groove ODmax={grooveODmax:.1f} mm for 2.0-mm ligaments")

    # Preferred compact screen based on exact algebra, not O-ring-gland guess.
    preferred={"flange_OD_mm":36.0,"PCD_mm":28.0,
               "outer_edge_ligament_mm":(36-28-Dhole)/2,
               "max_face_groove_OD_mm":28-Dhole-2*L,
               "seal_candidate":"16×1.5 O-ring only as screening candidate; exact ISO3601/Parker face gland still OPEN"}
    backup={"flange_OD_mm":38.0,"PCD_mm":30.0,
            "outer_edge_ligament_mm":(38-30-Dhole)/2,
            "max_face_groove_OD_mm":30-Dhole-2*L,
            "seal_candidate":"Allows larger exact face-gland envelope if required"}
    print("Preferred compact screen:",preferred)
    print("Backup screen:",backup)

    rep={"schema":"k01_gate04c0_j2_envelope_probe_v1","status":"PASS_READ_ONLY",
         "created_utc":datetime.now(timezone.utc).isoformat(),
         "P003_rear_station_mm":rear,"axial_slab_mm":slab,
         "nearby_components":nearby,
         "radial_packaging_candidates":candidates,
         "preferred_screen":preferred,"backup_screen":backup,
         "decisions":{
           "three_M3":"KEEP AS CANDIDATE",
           "M3_PCD28_OD34":"REJECT: only 1.3-mm outer ligament with Ø3.4 clearance holes",
           "M3_manual_edit_now":"NO — freeze exact flange/seal envelope after this probe first"
         }}
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.write_text(json.dumps(rep,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] Read-only Gate04C0 complete.");print("Report:",REPORT);return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception:traceback.print_exc();raise SystemExit(1)
