from __future__ import annotations

import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client

from sw_com import member0, call, as_list


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "cad" / "current" / "K01_GATE03D_P006_CLEARANCE_PROBE.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

P003_SUFFIX = "K01-P-003_Cartridge_Body.SLDPRT"
P006_SUFFIX = "K01-P-006_Retaining_Plug.SLDPRT"
P007_SUFFIX = "K01-P-007_Hermetic_Magnetic_Can.SLDPRT"


def dot(a,b):
    return sum(float(a[i])*float(b[i]) for i in range(3))

def add(a,b):
    return [float(a[i])+float(b[i]) for i in range(3)]

def scale(v,s):
    return [float(s)*float(x) for x in v]

def norm(v):
    return math.sqrt(dot(v,v))

def unit(v):
    n=norm(v)
    if n <= 0:
        raise RuntimeError("zero vector")
    return [float(x)/n for x in v]

def transform_array(comp):
    tr, err = member0(comp, "Transform2", default=None)
    if err or tr is None:
        raise RuntimeError(err or "Transform2 returned None")
    data, err = member0(tr, "ArrayData", default=None)
    if err or data is None:
        raise RuntimeError(err or "ArrayData returned None")
    vals=[float(x) for x in list(data)]
    if len(vals)!=16:
        raise RuntimeError(f"Unexpected transform length {len(vals)}")
    return vals

def transform_point(T,p):
    ex=T[0:3]; ey=T[3:6]; ez=T[6:9]; t=T[9:12]
    return add(t, add(scale(ex,p[0]), add(scale(ey,p[1]), scale(ez,p[2]))))

def axis_x(T):
    return unit(T[0:3])

def comp_path(c):
    p,e=member0(c,"GetPathName",default="")
    if e: raise RuntimeError(e)
    return str(p or "")

def comp_name(c):
    n,_=member0(c,"Name2",default="")
    return str(n or "")

def components(asm):
    rows,e=call(asm,"GetComponents",False,default=None)
    if e: raise RuntimeError(e)
    return as_list(rows)

def find_one(comps,suffix):
    m=[c for c in comps if comp_path(c).lower().endswith(suffix.lower())]
    if len(m)!=1:
        raise RuntimeError(f"{suffix}: expected one component, got {len(m)}")
    return m[0]

def model_of(c):
    m,e=member0(c,"GetModelDoc2",default=None)
    if e or m is None:
        raise RuntimeError(e or f"{comp_name(c)} unresolved")
    return m

def body_of(c):
    m=model_of(c)
    bodies,e=call(m,"GetBodies2",0,True,default=None)
    if e: raise RuntimeError(e)
    if bodies is None:
        bodies,e=call(m,"GetBodies2",0,False,default=None)
        if e: raise RuntimeError(e)
    b=[x for x in as_list(bodies) if x is not None]
    if len(b)!=1:
        raise RuntimeError(f"{comp_name(c)}: expected one body, got {len(b)}")
    return b[0]

def bbox_local_m(c):
    b=body_of(c)
    box,e=member0(b,"GetBodyBox",default=None)
    if e or box is None:
        raise RuntimeError(e or "GetBodyBox returned None")
    return [float(x) for x in list(box)]

def axial_planes(c):
    b=body_of(c)
    faces,e=member0(b,"GetFaces",default=None)
    if e: raise RuntimeError(e)
    rows=[]
    for i,f in enumerate(as_list(faces)):
        s,se=member0(f,"GetSurface",default=None)
        if se or s is None: continue
        isp,pe=member0(s,"IsPlane",default=False)
        if pe or not bool(isp): continue
        pp,ppe=member0(s,"PlaneParams",default=None)
        if ppe or pp is None: continue
        p=[float(x) for x in list(pp)]
        if len(p)<6: continue
        n=unit(p[:3])
        if abs(abs(n[0])-1.0)>1e-7 or abs(n[1])>1e-7 or abs(n[2])>1e-7:
            continue
        area,ae=member0(f,"GetArea",default=None)
        rows.append({
            "face_index":i,
            "x_local_m":p[3],
            "x_local_mm":1000*p[3],
            "area_mm2":None if ae or area is None else float(area)*1e6,
            "normal":n,
        })
    return sorted(rows,key=lambda r:r["x_local_m"])

def cylinders(c):
    b=body_of(c)
    faces,e=member0(b,"GetFaces",default=None)
    if e: raise RuntimeError(e)
    rows=[]
    for i,f in enumerate(as_list(faces)):
        s,se=member0(f,"GetSurface",default=None)
        if se or s is None: continue
        isc,ce=member0(s,"IsCylinder",default=False)
        if ce or not bool(isc): continue
        cp,cpe=member0(s,"CylinderParams",default=None)
        if cpe or cp is None: continue
        p=[float(x) for x in list(cp)]
        if len(p)<7: continue
        area,ae=member0(f,"GetArea",default=None)
        rows.append({
            "face_index":i,
            "diameter_mm":2000*p[6],
            "axis_origin_local_mm":[1000*x for x in p[:3]],
            "axis_direction_local":unit(p[3:6]),
            "area_mm2":None if ae or area is None else float(area)*1e6,
        })
    return rows

def p003_rear_center(c):
    T=transform_array(c)
    planes=axial_planes(c)
    if not planes:
        raise RuntimeError("P003 axial planes unavailable")
    rear=max(planes,key=lambda r:r["x_local_m"])
    pt=transform_point(T,[rear["x_local_m"],0,0])
    return rear,pt

def project_bbox_to_axis(c, origin, axis):
    T=transform_array(c)
    box=bbox_local_m(c)
    xs=[box[0],box[3]]
    ys=[box[1],box[4]]
    zs=[box[2],box[5]]
    vals=[]
    pts=[]
    for x in xs:
        for y in ys:
            for z in zs:
                pa=transform_point(T,[x,y,z])
                q=[pa[i]-origin[i] for i in range(3)]
                s=dot(q,axis)
                vals.append(s)
                pts.append(pa)
    return {
        "min_from_P003_rear_mm":1000*min(vals),
        "max_from_P003_rear_mm":1000*max(vals),
        "bbox_local_mm":[1000*x for x in box],
    }

def plane_stations_from_weld(c, origin, axis):
    T=transform_array(c)
    rows=[]
    for r in axial_planes(c):
        p=transform_point(T,[r["x_local_m"],0,0])
        q=[p[i]-origin[i] for i in range(3)]
        rows.append({
            **r,
            "station_from_P003_rear_mm":1000*dot(q,axis),
        })
    return rows

def main():
    pythoncom.CoInitialize()
    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev,_=member0(sw,"RevisionNumber",default="")
    asm,e=member0(sw,"ActiveDoc",default=None)
    if e or asm is None:
        raise RuntimeError(e or "No active document")
    typ,_=member0(asm,"GetType",default=None)
    title,_=member0(asm,"GetTitle",default="")
    path,_=member0(asm,"GetPathName",default="")
    if int(typ)!=2:
        raise RuntimeError(f"Active document must be assembly; got {typ}")
    if "K01-A-001_Calibration_Module" not in str(title):
        raise RuntimeError(f"Open production K01-A-001 assembly; got {title}")

    comps=components(asm)
    p003=find_one(comps,P003_SUFFIX)
    p006=find_one(comps,P006_SUFFIX)
    p007=find_one(comps,P007_SUFFIX)

    T003=transform_array(p003)
    axis=axis_x(T003)
    rear,rear_pt=p003_rear_center(p003)

    T006=transform_array(p006)
    T007=transform_array(p007)

    # Require same axial direction for P003/P006, but still report if not.
    axis006=axis_x(T006)
    axis007=axis_x(T007)

    result={
        "schema":"k01_gate03d_p006_clearance_probe_v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "solidworks_revision":str(rev),
        "assembly":{"title":str(title),"path":str(path)},
        "P003_rear":{
            "local_station_mm":rear["x_local_mm"],
            "area_mm2":rear["area_mm2"],
            "assembly_center_m":rear_pt,
            "axis":axis,
        },
        "axis_dot":{
            "P003_vs_P006":dot(axis,axis006),
            "P003_vs_P007":dot(axis,axis007),
        },
        "P006":{
            "name":comp_name(p006),
            "path":comp_path(p006),
            "bbox_projection":project_bbox_to_axis(p006,rear_pt,axis),
            "axial_planes":plane_stations_from_weld(p006,rear_pt,axis),
            "cylinders":cylinders(p006),
            "transform":T006,
        },
        "P007_current":{
            "name":comp_name(p007),
            "path":comp_path(p007),
            "bbox_projection":project_bbox_to_axis(p007,rear_pt,axis),
            "axial_planes":plane_stations_from_weld(p007,rear_pt,axis),
            "cylinders":cylinders(p007),
            "transform":T007,
        },
        "candidate_v4_front_internal_envelope":{
            "x_0_to_2_mm_ID_mm":10.917,
            "x_2_to_34_mm_ID_mm":9.4,
            "note":"Gate03B v4 candidate that interfered with P006 in manual SW Interference Detection."
        },
        "manual_interference_observation":{
            "P006_vs_P007_v4_volume_mm3":20.53,
            "status":"OBSERVED_IN_SOLIDWORKS_SCREENSHOT",
        },
    }

    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

    proj=result["P006"]["bbox_projection"]
    cyls=sorted(result["P006"]["cylinders"],key=lambda r:r["diameter_mm"],reverse=True)

    print("="*72)
    print("K01 Gate 03D - P006 / P007 FRONT CLEARANCE PROBE")
    print("="*72)
    print(f"[INFO] SOLIDWORKS revision: {rev}")
    print(f"[INFO] Assembly: {title}")
    print(f"[PASS] P003 rear reference acquired.")
    print(
        "[INFO] P006 axial bbox relative to P003 rear: "
        f"{proj['min_from_P003_rear_mm']:.6f} .. "
        f"{proj['max_from_P003_rear_mm']:.6f} mm"
    )
    if cyls:
        print("[INFO] P006 cylindrical face diameters [mm]:")
        for r in cyls:
            print(
                f"       face {r['face_index']:>2}: "
                f"D={r['diameter_mm']:.6f}, area={r['area_mm2']}"
            )
    print(f"[PASS] JSON: {OUT}")
    print("Production CAD was NOT modified.")
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: Gate03D P006 clearance probe")
        traceback.print_exc()
        sys.exit(1)
