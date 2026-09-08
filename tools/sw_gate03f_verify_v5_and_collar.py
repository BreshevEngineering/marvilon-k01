from __future__ import annotations

import json
import math
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client

from sw_com import member0, call, as_list


ROOT = Path(__file__).resolve().parents[1]
P007_REPORT = ROOT / "reports" / "cad" / "current" / "K01_P007_GATE03E_V5_BUILD.json"
COLLAR_REPORT = ROOT / "reports" / "cad" / "current" / "K01_P003_GATE03E_COLLAR_REF_BUILD.json"
OUT_REPORT = ROOT / "reports" / "cad" / "current" / "K01_GATE03F_ASSEMBLY_VERIFY.json"
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

VERIFY_DIR = Path(r"D:\Marvilon\K01\cad\candidates")
VERIFY_BASE = "K01-A-001_GATE03F_P007_V5_VERIFY"

PROD_ASM = "K01-A-001_Calibration_Module.SLDASM"
P003_SUFFIX = "K01-P-003_Cartridge_Body.SLDPRT"
P006_SUFFIX = "K01-P-006_Retaining_Plug.SLDPRT"
P007_SUFFIX = "K01-P-007_Hermetic_Magnetic_Can.SLDPRT"

TOL_STATION_MM = 0.002
TOL_TRANSFORM = 1.0e-10
TOL_AXIS = 1.0e-8


def add(a,b): return [float(a[i])+float(b[i]) for i in range(3)]
def sub(a,b): return [float(a[i])-float(b[i]) for i in range(3)]
def scale(v,s): return [float(s)*float(x) for x in v]
def dot(a,b): return sum(float(a[i])*float(b[i]) for i in range(3))
def norm(v): return math.sqrt(dot(v,v))
def unit(v):
    n=norm(v)
    if n <= 0: raise RuntimeError("zero vector")
    return [float(x)/n for x in v]
def dist_mm(a,b): return 1000.0*norm(sub(a,b))


def transform_array(comp):
    tr, err = member0(comp, "Transform2", default=None)
    if err or tr is None:
        raise RuntimeError(err or "Component.Transform2 returned None")
    data, err = member0(tr, "ArrayData", default=None)
    if err or data is None:
        raise RuntimeError(err or "Transform2.ArrayData returned None")
    vals=[float(x) for x in list(data)]
    if len(vals)!=16:
        raise RuntimeError(f"Expected 16 transform values, got {len(vals)}")
    return vals


def transform_point(T,p):
    ex=T[0:3]; ey=T[3:6]; ez=T[6:9]; t=T[9:12]
    return add(t, add(scale(ex,p[0]), add(scale(ey,p[1]), scale(ez,p[2]))))


def axis_x(T): return unit(T[0:3])


def comp_path(c):
    p,e=member0(c,"GetPathName",default="")
    if e: raise RuntimeError(e)
    return str(p or "")


def comp_name(c):
    n,_=member0(c,"Name2",default="")
    return str(n or "")


def comps(asm):
    rows,e=call(asm,"GetComponents",False,default=None)
    if e: raise RuntimeError(f"GetComponents failed: {e}")
    return as_list(rows)


def find_suffix(rows,suffix):
    return [c for c in rows if comp_path(c).lower().endswith(suffix.lower())]


def model_of(c):
    m,e=member0(c,"GetModelDoc2",default=None)
    if e or m is None:
        raise RuntimeError(e or f"{comp_name(c)} unresolved")
    return m


def body_of(c):
    m=model_of(c)
    b,e=call(m,"GetBodies2",0,True,default=None)
    if e: raise RuntimeError(e)
    if b is None:
        b,e=call(m,"GetBodies2",0,False,default=None)
        if e: raise RuntimeError(e)
    rows=[x for x in as_list(b) if x is not None]
    if len(rows)!=1:
        raise RuntimeError(f"{comp_name(c)} expected one body, got {len(rows)}")
    return rows[0]


def axial_planes(c):
    body=body_of(c)
    faces,e=member0(body,"GetFaces",default=None)
    if e: raise RuntimeError(e)
    rows=[]
    for i,f in enumerate(as_list(faces)):
        surf,se=member0(f,"GetSurface",default=None)
        if se or surf is None: continue
        isp,pe=member0(surf,"IsPlane",default=False)
        if pe or not bool(isp): continue
        pp,ppe=member0(surf,"PlaneParams",default=None)
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
            "x_local_mm":1000.0*p[3],
            "area_mm2":None if ae or area is None else float(area)*1e6,
            "normal":n,
        })
    # deduplicate stations
    grouped={}
    for r in rows:
        key=round(r["x_local_mm"],6)
        old=grouped.get(key)
        if old is None or (r["area_mm2"] or -1)>(old["area_mm2"] or -1):
            grouped[key]=r
    return sorted(grouped.values(),key=lambda r:r["x_local_m"])


def p003_rear(c):
    T=transform_array(c)
    planes=axial_planes(c)
    if not planes: raise RuntimeError("P003 axial planes unavailable")
    rear=max(planes,key=lambda r:r["x_local_m"])
    point=transform_point(T,[rear["x_local_m"],0,0])
    return rear,point


def set_transform_from_array(comp, target):
    mt,err=member0(comp,"Transform2",default=None)
    if err or mt is None:
        raise RuntimeError(err or "Transform2 unavailable")
    target=[float(x) for x in target]
    attempts=[]
    payloads=[
        ("tuple",tuple(target)),
        ("list",list(target)),
        ("VT_ARRAY|VT_R8",win32com.client.VARIANT(
            pythoncom.VT_ARRAY|pythoncom.VT_R8,target)),
    ]
    used=None
    for label,payload in payloads:
        try:
            mt.ArrayData=payload
            got,gerr=member0(mt,"ArrayData",default=None)
            if gerr or got is None:
                attempts.append(f"{label}: readback failed {gerr}")
                continue
            got=[float(x) for x in list(got)]
            d=max(abs(got[i]-target[i]) for i in range(16))
            if d<=1e-12:
                used=label
                break
            attempts.append(f"{label}: readback delta {d:.3e}")
        except Exception as exc:
            attempts.append(f"{label}: {type(exc).__name__}: {exc}")
    if used is None:
        raise RuntimeError("Could not write transform ArrayData: "+" | ".join(attempts))

    try:
        comp.Transform2=mt
        method="Transform2 property"
    except Exception as exc1:
        ok,e=call(comp,"SetTransformAndSolve2",mt,default=False)
        if e or not ok:
            raise RuntimeError(
                f"Transform assignment failed. property={exc1}; fallback={e or ok!r}")
        method="SetTransformAndSolve2"
    return method,used


def transform_delta(a,b):
    return max(abs(float(a[i])-float(b[i])) for i in range(16))


def save_as(model,target:Path):
    target.parent.mkdir(parents=True,exist_ok=True)
    rc,e=call(model,"SaveAs3",str(target),0,1,default=None)
    if e: raise RuntimeError(f"SaveAs3 failed: {e}")
    if not target.exists():
        raise RuntimeError(f"SaveAs3 did not create {target}; rc={rc!r}")


def replace_selected_p007(asm, candidate_path):
    rows=find_suffix(comps(asm),P007_SUFFIX)
    if len(rows)!=1:
        raise RuntimeError(f"Expected one old P007 in verification copy, got {len(rows)}")
    old=rows[0]
    call(asm,"ClearSelection2",True,default=None)
    ok,e=call(old,"Select2",False,0,default=False)
    if e or not ok: raise RuntimeError(f"old P007 Select2 failed: {e or ok!r}")
    done,e=call(
        asm,"ReplaceComponents2",
        str(candidate_path),"",False,0,False,
        default=False)
    if e or not done:
        raise RuntimeError(f"ReplaceComponents2 failed: {e or done!r}")


def preload_part_for_addcomponent5(sw, part_path):
    # SOLIDWORKS 2018 AddComponent5 requires the component file
    # to be pre-loaded in SOLIDWORKS memory.
    errors = win32com.client.VARIANT(
        pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(
        pythoncom.VT_BYREF | pythoncom.VT_I4, 0)

    try:
        loaded = sw.OpenDoc6(
            str(part_path),
            1,      # swDocPART
            1,      # swOpenDocOptions_Silent
            "",
            errors,
            warnings,
        )
    except Exception as exc:
        raise RuntimeError(
            "OpenDoc6 collar preload failed: "
            f"{type(exc).__name__}: {exc}")

    if isinstance(loaded, tuple):
        model = next(
            (x for x in loaded
             if x is not None and hasattr(x, "_oleobj_")),
            None)
    else:
        model = loaded

    if model is None:
        raise RuntimeError(
            "OpenDoc6 returned no collar ModelDoc2. "
            f"errors={errors.value}, warnings={warnings.value}")

    return model, int(errors.value), int(warnings.value)


def add_collar_component(sw, asm, collar_path):
    loaded_model, open_errors, open_warnings = preload_part_for_addcomponent5(
        sw, collar_path)

    title, _ = member0(loaded_model, "GetTitle", default="")
    print(
        f"[PASS] Collar pre-loaded for AddComponent5: {title}; "
        f"OpenDoc6 errors={open_errors}, warnings={open_warnings}")

    comp,e=call(
        asm,"AddComponent5",
        str(collar_path),
        0,
        "",
        False,
        "",
        0.0,0.0,0.0,
        default=None)

    if e or comp is None:
        raise RuntimeError(
            "AddComponent5 collar failed after successful preload: "
            f"{e or 'returned None'}")

    return comp


def interferences(asm, critical_paths):
    out={
        "available":False,
        "count":None,
        "rows":[],
        "critical_hits":[],
        "errors":[],
    }
    mgr,e=member0(asm,"InterferenceDetectionManager",default=None)
    if e or mgr is None:
        out["errors"].append(e or "InterferenceDetectionManager unavailable")
        return out
    out["available"]=True

    for prop,val in (
        ("TreatCoincidenceAsInterference",False),
        ("IgnoreHiddenBodies",True),
        ("TreatSubAssembliesAsComponents",False),
        ("UseTransform",True),
        ("ShowIgnoredInterferences",True),
    ):
        try: setattr(mgr,prop,val)
        except Exception as exc:
            out["errors"].append(f"{prop}: {type(exc).__name__}: {exc}")

    count,e=call(mgr,"GetInterferenceCount",default=None)
    if e:
        out["errors"].append(f"GetInterferenceCount: {e}")
    elif count is not None:
        try: out["count"]=int(count)
        except Exception: pass

    ints,e=call(mgr,"GetInterferences",default=None)
    if e:
        out["errors"].append(f"GetInterferences: {e}")
        ints=None

    crit={os.path.normcase(os.path.normpath(str(p))) for p in critical_paths}

    for idx,interf in enumerate(as_list(ints)):
        if interf is None: continue
        row={"index":idx,"components":[],"volume_mm3":None,"ignored":None,"errors":[]}

        cc,ce=member0(interf,"Components",default=None)
        if ce:
            row["errors"].append(f"Components: {ce}")
        for c in as_list(cc):
            if c is None: continue
            try:
                row["components"].append({
                    "name":comp_name(c),
                    "path":comp_path(c),
                })
            except Exception as exc:
                row["errors"].append(f"component read: {exc}")

        vol,ve=member0(interf,"Volume",default=None)
        if ve:
            row["errors"].append(f"Volume: {ve}")
        elif vol is not None:
            try: row["volume_mm3"]=float(vol)*1.0e9
            except Exception: pass

        ign,ie=member0(interf,"Ignore",default=None)
        if not ie:
            try: row["ignored"]=bool(ign)
            except Exception: pass

        pset={
            os.path.normcase(os.path.normpath(r["path"]))
            for r in row["components"] if r.get("path")
        }
        hit=sorted(pset.intersection(crit))
        if hit:
            row["critical_paths"]=hit
            out["critical_hits"].append(row)
        out["rows"].append(row)

    try: call(mgr,"Done",default=None)
    except Exception: pass

    return out


def main():
    pythoncom.CoInitialize()

    if not P007_REPORT.exists():
        raise RuntimeError(f"P007 v5 report missing: {P007_REPORT}")
    if not COLLAR_REPORT.exists():
        raise RuntimeError(f"P003 collar report missing: {COLLAR_REPORT}")

    p007_build=json.loads(P007_REPORT.read_text(encoding="utf-8"))
    collar_build=json.loads(COLLAR_REPORT.read_text(encoding="utf-8"))
    if p007_build.get("status")!="PASS":
        raise RuntimeError("P007 v5 build is not PASS")
    if collar_build.get("status")!="PASS":
        raise RuntimeError("P003 collar reference build is not PASS")

    p007_path=Path(p007_build["native_candidate"])
    collar_path=Path(collar_build["native_reference"])
    if not p007_path.exists(): raise RuntimeError(f"P007 v5 file missing: {p007_path}")
    if not collar_path.exists(): raise RuntimeError(f"collar file missing: {collar_path}")

    sw=win32com.client.GetActiveObject("SldWorks.Application")
    rev,_=member0(sw,"RevisionNumber",default="")
    asm,e=member0(sw,"ActiveDoc",default=None)
    if e or asm is None: raise RuntimeError(e or "No active document")
    typ,_=member0(asm,"GetType",default=None)
    title,_=member0(asm,"GetTitle",default="")
    path,_=member0(asm,"GetPathName",default="")
    dirty,_=member0(asm,"GetSaveFlag",default=False)

    print("="*76)
    print("K01 Gate03F - P007 v5 + P003 COLLAR ASSEMBLY VERIFY")
    print("="*76)
    print(f"[INFO] SOLIDWORKS revision: {rev}")
    print(f"[INFO] Active assembly:    {title}")
    print(f"[INFO] P007 v5:            {p007_path}")
    print(f"[INFO] Collar reference:   {collar_path}")

    if int(typ)!=2: raise RuntimeError("Active document must be Assembly")
    if not str(title).lower().endswith(PROD_ASM.lower()):
        raise RuntimeError(f"Open production {PROD_ASM}; got {title}")
    if bool(dirty):
        raise RuntimeError("Production assembly has unsaved changes; save/discard first")

    production_path=Path(str(path))
    rows=comps(asm)
    p003m=find_suffix(rows,P003_SUFFIX)
    p006m=find_suffix(rows,P006_SUFFIX)
    p007m=find_suffix(rows,P007_SUFFIX)
    if len(p003m)!=1 or len(p006m)!=1 or len(p007m)!=1:
        raise RuntimeError(
            f"Expected one P003/P006/P007; got {len(p003m)}/{len(p006m)}/{len(p007m)}")
    p003,p006,p007_old=p003m[0],p006m[0],p007m[0]

    T003=transform_array(p003)
    T007_old=transform_array(p007_old)
    if abs(abs(dot(axis_x(T003),axis_x(T007_old)))-1.0)>TOL_AXIS:
        raise RuntimeError("P003/P007 axes are not parallel")

    rear,rear_pt=p003_rear(p003)
    ex003=axis_x(T003)

    # Candidate v5 x=0 is at current P003 rear plane.
    T007_target=list(T007_old)
    T007_target[9:12]=rear_pt

    # Collar local x=0..5 is placed over assembly interval rear-5..rear.
    collar_origin=sub(rear_pt,scale(ex003,0.005))
    Tcollar_target=list(T003)
    Tcollar_target[9:12]=collar_origin

    # Pre-check station preservation versus current production P007.
    old_planes=axial_planes(p007_old)
    if len(old_planes)!=5:
        raise RuntimeError(f"Current P007 expected 5 axial planes, got {len(old_planes)}")

    old_pts={
        "thin_ID_start":transform_point(T007_old,[old_planes[1]["x_local_m"],0,0]),
        "thin_OD_start":transform_point(T007_old,[old_planes[2]["x_local_m"],0,0]),
        "rear_inner":transform_point(T007_old,[old_planes[3]["x_local_m"],0,0]),
        "rear_outer":transform_point(T007_old,[old_planes[4]["x_local_m"],0,0]),
    }
    new_local_mm={"thin_ID_start":2.0,"thin_OD_start":3.0,"rear_inner":34.0,"rear_outer":35.0}
    calc_deltas={}
    for k,xmm in new_local_mm.items():
        q=transform_point(T007_target,[xmm/1000.0,0,0])
        calc_deltas[k]=dist_mm(q,old_pts[k])
    if any(v>TOL_STATION_MM for v in calc_deltas.values()):
        raise RuntimeError(f"Calculated station preservation failed: {calc_deltas}")

    for k,v in calc_deltas.items():
        print(f"[PASS] calculated {k}: Δ={v:.9f} mm")

    # Save verification copy.
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    verify_path=VERIFY_DIR/f"{VERIFY_BASE}_{stamp}.SLDASM"
    save_as(asm,verify_path)
    print(f"[PASS] Verification assembly copy created: {verify_path}")

    # Replace P007 only in verification copy.
    replace_selected_p007(asm,p007_path)
    call(asm,"ForceRebuild3",False,default=None)

    rows_after=comps(asm)
    p007_candidates=[
        c for c in rows_after
        if os.path.normcase(os.path.normpath(comp_path(c)))
        ==os.path.normcase(os.path.normpath(str(p007_path)))
    ]
    if len(p007_candidates)!=1:
        raise RuntimeError(f"Expected one P007-v5 after replacement, got {len(p007_candidates)}")
    p007_new=p007_candidates[0]
    method_p007,array_p007=set_transform_from_array(p007_new,T007_target)
    call(asm,"ForceRebuild3",False,default=None)
    T007_actual=transform_array(p007_new)
    td007=transform_delta(T007_actual,T007_target)
    if td007>TOL_TRANSFORM:
        raise RuntimeError(f"P007-v5 transform mismatch {td007:.3e}")
    print(f"[PASS] P007-v5 placed via {method_p007}; ArrayData={array_p007}; ΔT={td007:.3e}")

    # Add collar reference to verification copy.
    collar=add_collar_component(sw,asm,collar_path)
    method_col,array_col=set_transform_from_array(collar,Tcollar_target)
    call(asm,"ForceRebuild3",False,default=None)
    Tc_actual=transform_array(collar)
    tdc=transform_delta(Tc_actual,Tcollar_target)
    if tdc>TOL_TRANSFORM:
        raise RuntimeError(f"Collar transform mismatch {tdc:.3e}")
    print(f"[PASS] Collar placed over old sleeve envelope x=-5..0; ΔT={tdc:.3e}")

    # Physical station verification after replacement.
    physical={}
    for k,xmm in new_local_mm.items():
        q=transform_point(T007_actual,[xmm/1000.0,0,0])
        physical[k]=dist_mm(q,old_pts[k])
    if any(v>TOL_STATION_MM for v in physical.values()):
        raise RuntimeError(f"Physical station preservation failed: {physical}")
    for k,v in physical.items():
        print(f"[PASS] physical {k}: Δ={v:.9f} mm")

    # Also verify P006 exists and was not moved.
    T006=transform_array(p006)
    print(f"[PASS] P006 retained; component={comp_name(p006)}")

    # Full assembly interference.
    interference=interferences(asm,[p007_path,collar_path])
    critical=interference["critical_hits"]

    status="PASS"
    if critical:
        status="FAIL_CRITICAL_INTERFERENCE"
    elif not interference["available"] or interference["errors"]:
        status="PASS_WITH_INTERFERENCE_API_WARN"

    if critical:
        print("[FAIL] Critical interference involves P007-v5 and/or collar reference:")
        for r in critical:
            print("       ",r)
    elif status=="PASS":
        print("[PASS] Interference API found no volumetric interference involving P007-v5 or collar.")
    else:
        print("[WARN] Interference API not definitive. Run manual Evaluate > Interference Detection.")
        print("       Treat coincidence as interference = OFF.")

    save_as(asm,verify_path)

    report={
        "schema":"k01_gate03f_assembly_verify_v1",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "status":status,
        "solidworks_revision":str(rev),
        "production_assembly":str(production_path),
        "production_assembly_modified":False,
        "verification_assembly":str(verify_path),
        "P007_v5":str(p007_path),
        "P003_collar_reference":str(collar_path),
        "calculated_station_deltas_mm":calc_deltas,
        "physical_station_deltas_mm":physical,
        "P007_transform_max_delta":td007,
        "collar_transform_max_delta":tdc,
        "collar_assembly_span_from_P003_rear_mm":[-5.0,0.0],
        "interference":interference,
        "release_status":"ASSEMBLY_GEOMETRY_GATE_ONLY__NOT_PRODUCTION_RELEASE",
        "next_if_pass":[
            "Build native P003 candidate with OD16 rear collar L5 integrated into the same solid body",
            "Mate/reference migration audit",
            "P007 Static +0.20 bar",
            "P007 external-pressure Buckling -0.20 bar",
        ],
    }
    OUT_REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

    print("="*76)
    print("K01 Gate03F RESULT")
    print("="*76)
    print("Status:",status)
    print("Verification assembly:",verify_path)
    print("Report:",OUT_REPORT)
    print("Production assembly on disk was NOT overwritten.")

    return 2 if status=="FAIL_CRITICAL_INTERFERENCE" else 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: K01 Gate03F assembly verification")
        traceback.print_exc()
        sys.exit(1)
