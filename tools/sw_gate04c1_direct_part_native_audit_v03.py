"""
K01 Gate04C1 v03 — DIRECT-PART NATIVE AUDIT / READ-ONLY
=======================================================

Reason for v03
--------------
v01/v02 spent time on assembly COM-interface casting although Gate04C0 already
proved the assembly envelope. v03 removes assembly traversal completely.

This script opens the two stable PART files directly and audits their native
feature history / bodies / faces. It never asks COM whether A001 is an assembly.

READ-ONLY
---------
No Save, SaveAs, suppression, feature creation, replacement, mate change, master
change or BOM change is performed.

Stable inputs
-------------
D:\\Marvilon\\K01\\cad\\parts\\K01-P-003_Cartridge_Body.SLDPRT
D:\\Marvilon\\K01\\cad\\parts\\K01-P-007_Hermetic_Magnetic_Can.SLDPRT

Output
------
<repo>\\reports\\cad\\current\\K01_GATE04C1_DIRECT_PART_NATIVE_AUDIT.json
"""

from __future__ import annotations
import json
import math
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
from win32com.client import dynamic

SW_DOC_PART = 1
SW_OPEN_SILENT = 1
SW_BODY_SOLID = 0

P003 = r"D:\Marvilon\K01\cad\parts\K01-P-003_Cartridge_Body.SLDPRT"
P007 = r"D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT"

TARGET = {
    "P003_material": "AISI 316L / EN 1.4404",
    "P007_material": "AISI 316L / EN 1.4404",
    "P003_rear_zone_current_D_mm": 16.0,
    "P003_rear_zone_current_L_mm": 5.0,
    "P007_OAL_mm": 35.0,
    "P007_root_ID_mm": 14.10,
    "P007_thin_OD_mm": 10.0,
    "P007_thin_ID_mm": 9.4,
    "J2_flange_OD_mm": 36.0,
    "J2_PCD_mm": 28.0,
    "J2_clearance_D_mm": 3.4,
    "J2_pilot_D_mm": 14.10,
    "J2_male_pilot_L_mm": 1.50,
    "J2_female_locator_depth_mm": 1.70,
    "J2_seal": "16x1.5 mm",
    "J2_gland_ID_mm": 16.00,
    "J2_gland_width_radial_mm": 2.10,
    "J2_gland_depth_mm": 1.10,
    "J2_gland_OD_nominal_mm": 20.20,
    "J2_gland_OD_design_max_mm": 20.60,
}

def utc():
    return datetime.now(timezone.utc).isoformat()

def npath(p):
    return os.path.normcase(os.path.abspath(p)) if p else ""

def repo_root():
    here = Path(__file__).resolve()
    for p in [here.parent] + list(here.parents):
        if (p / "reports").exists() and (p / "control").exists():
            return p
    return here.parent

def report_path():
    p = repo_root() / "reports" / "cad" / "current"
    p.mkdir(parents=True, exist_ok=True)
    return p / "K01_GATE04C1_DIRECT_PART_NATIVE_AUDIT.json"

def connect():
    pythoncom.CoInitialize()
    sw = dynamic.Dispatch("SldWorks.Application")
    sw.Visible = True
    try: sw.UserControl = True
    except Exception: pass
    return sw

def doc_path(doc):
    try: return str(doc.GetPathName())
    except Exception: return ""

def doc_title(doc):
    try: return str(doc.GetTitle())
    except Exception: return ""

def open_part(sw, path):
    if not os.path.exists(path):
        raise RuntimeError(f"Stable part not found: {path}")

    # Re-use open document if SOLIDWORKS can find it.
    doc = None
    try:
        doc = sw.GetOpenDocumentByName(path)
    except Exception:
        pass

    if doc is None:
        try:
            sw.OpenDoc6(path, SW_DOC_PART, SW_OPEN_SILENT, "", 0, 0)
        except Exception:
            try:
                sw.OpenDoc(path, SW_DOC_PART)
            except Exception as e:
                raise RuntimeError(f"Open failed for {path}: {e}")

    # Critical robustness change: always reacquire from the application after open.
    try:
        doc = sw.GetOpenDocumentByName(path)
    except Exception:
        doc = None

    if doc is None:
        # Activate by exact filename and reacquire ActiveDoc.
        try:
            sw.ActivateDoc3(os.path.basename(path), True, 0, 0)
        except Exception:
            try: sw.ActivateDoc(os.path.basename(path))
            except Exception: pass
        doc = sw.ActiveDoc

    if doc is None:
        raise RuntimeError(f"Could not reacquire open part: {path}")

    got = doc_path(doc)
    if got and npath(got) != npath(path):
        # Last attempt: activate exact file.
        try:
            sw.ActivateDoc3(os.path.basename(path), True, 0, 0)
            doc = sw.ActiveDoc
            got = doc_path(doc)
        except Exception:
            pass

    if not got or npath(got) != npath(path):
        raise RuntimeError(
            "SOLIDWORKS returned a different/opaque document after opening. "
            f"Expected={path}; got_path={got!r}; got_title={doc_title(doc)!r}"
        )
    return doc

def arr(v):
    if v is None: return None
    try: return [float(x) for x in list(v)]
    except Exception: return None

def feature_tree(doc):
    rows = []
    try: f = doc.FirstFeature()
    except Exception as e:
        return [{"error": f"FirstFeature failed: {type(e).__name__}: {e}"}]
    guard = 0
    while f is not None and guard < 1000:
        guard += 1
        try: name = str(f.Name)
        except Exception: name = ""
        try: typ = str(f.GetTypeName2())
        except Exception: typ = ""
        try: supp = bool(f.IsSuppressed())
        except Exception: supp = None
        rows.append({"index": guard-1, "name": name, "type": typ, "suppressed": supp})
        try: f = f.GetNextFeature()
        except Exception: break
    return rows

def part_box(doc):
    # GetPartBox exists on IPartDoc and is useful even if body COM calls are awkward.
    for arg in (True, False):
        try:
            bb = arr(doc.GetPartBox(arg))
            if bb and len(bb) >= 6:
                return [1000*x for x in bb[:6]], f"GetPartBox({arg})"
        except Exception:
            pass
    return None, "unavailable"

def bodies(doc):
    notes = []
    for visible in (True, False):
        try:
            vv = doc.GetBodies2(SW_BODY_SOLID, visible)
            if vv:
                b = list(vv)
                notes.append(f"GetBodies2({SW_BODY_SOLID},{visible}) PASS count={len(b)}")
                return b, notes
            notes.append(f"GetBodies2({SW_BODY_SOLID},{visible}) empty")
        except Exception as e:
            notes.append(f"GetBodies2({SW_BODY_SOLID},{visible}) {type(e).__name__}: {e}")
    return [], notes

def surf_rec(face):
    r = {"kind":"other","area_mm2":None,"raw":None,"diameter_mm":None,
         "axis":None,"origin_mm":None,"plane_normal":None,"plane_origin_mm":None}
    try: r["area_mm2"] = float(face.GetArea()) * 1e6
    except Exception: pass
    try: s = face.GetSurface()
    except Exception: return r
    if s is None: return r

    try:
        if bool(s.IsCylinder()):
            a = arr(s.CylinderParams)
            r["kind"] = "cylinder"; r["raw"] = a
            if a and len(a) >= 7:
                r["origin_mm"] = [1000*x for x in a[0:3]]
                r["axis"] = a[3:6]
                r["diameter_mm"] = 2000*abs(a[6])
            return r
    except Exception:
        pass

    try:
        if bool(s.IsPlane()):
            a = arr(s.PlaneParams)
            r["kind"] = "plane"; r["raw"] = a
            if a and len(a) >= 6:
                # Preserve both triples explicitly; report is for topology review,
                # not for making a destructive decision in this gate.
                r["plane_triplet_1"] = a[0:3]
                r["plane_triplet_2"] = a[3:6]
            return r
    except Exception:
        pass
    return r

def body_audit(doc):
    bs, notes = bodies(doc)
    out = []
    for i,b in enumerate(bs):
        rec = {"index":i,"bbox_mm":None,"faces":[]}
        try:
            bb = arr(b.GetBodyBox())
            if bb and len(bb)>=6: rec["bbox_mm"]=[1000*x for x in bb[:6]]
        except Exception: pass
        try:
            ff=b.GetFaces()
            ff=list(ff) if ff else []
        except Exception:
            ff=[]
        rec["faces"]=[surf_rec(f) for f in ff]
        out.append(rec)
    return out, notes

def props(doc):
    out={}
    try: mgr=doc.Extension.CustomPropertyManager("")
    except Exception: return out
    for k in ("PartNo","Description","Material","MaterialSpec","Revision","Status","Process","Note"):
        val=""
        for mode in (6,4,2):
            try:
                if mode==6: ret=mgr.Get6(k,False,"","",False,False)
                elif mode==4: ret=mgr.Get4(k,False,"","")
                else: ret=mgr.Get2(k,"","")
                if isinstance(ret,tuple):
                    ss=[x for x in ret if isinstance(x,str) and x.strip()]
                    if ss: val=ss[-1]
                elif isinstance(ret,str): val=ret
                if val: break
            except Exception: pass
        out[k]=val
    return out

def audit(doc, label):
    pb,pb_src=part_box(doc)
    ba,notes=body_audit(doc)
    return {
        "label":label,
        "title":doc_title(doc),
        "path":doc_path(doc),
        "part_box_mm":pb,
        "part_box_source":pb_src,
        "feature_tree":feature_tree(doc),
        "custom_properties":props(doc),
        "body_api_notes":notes,
        "bodies":ba,
    }

def cylindrical_faces(part, dnom, tol=0.06):
    hits=[]
    for b in part["bodies"]:
        for f in b["faces"]:
            if f.get("kind")=="cylinder" and f.get("diameter_mm") is not None:
                if abs(f["diameter_mm"]-dnom)<=tol:
                    hits.append(f)
    return hits

def box_span_x(part):
    bb=part.get("part_box_mm")
    if bb and len(bb)>=6:
        # SW boxes are xmin,ymin,zmin,xmax,ymax,zmax
        return abs(bb[3]-bb[0])
    for b in part["bodies"]:
        bb=b.get("bbox_mm")
        if bb and len(bb)>=6:
            return abs(bb[3]-bb[0])
    return None

def main():
    rp=report_path()
    report={
        "schema":"k01_gate04c1_direct_part_native_audit_v3",
        "created_utc":utc(),
        "status":"RUNNING",
        "read_only":True,
        "reason":"Bypass assembly COM traversal; Gate04C0 already covers assembly envelope.",
        "target":TARGET,
    }
    sw=connect()

    print("="*92)
    print("K01 Gate04C1 v03 — DIRECT-PART NATIVE AUDIT / READ-ONLY")
    print("="*92)

    p3doc=open_part(sw,P003)
    print("[OPEN] P003:",doc_title(p3doc))
    p3=audit(p3doc,"P003")

    p7doc=open_part(sw,P007)
    print("[OPEN] P007:",doc_title(p7doc))
    p7=audit(p7doc,"P007")

    report["parts"]={"P003":p3,"P007":p7}

    d16=cylindrical_faces(p3,16.0)
    d141=cylindrical_faces(p7,14.10)
    d10=cylindrical_faces(p7,10.0)
    d94=cylindrical_faces(p7,9.4)
    span=box_span_x(p7)

    checks=[
        {"check":"P003 Ø16 cylindrical topology found","pass":len(d16)>0,"count":len(d16)},
        {"check":"P007 Ø14.10 cylindrical topology found","pass":len(d141)>0,"count":len(d141)},
        {"check":"P007 Ø10 thin-wall OD topology found","pass":len(d10)>0,"count":len(d10)},
        {"check":"P007 Ø9.4 thin-wall ID topology found","pass":len(d94)>0,"count":len(d94)},
        {"check":"P007 native X span near 35 mm","pass":span is not None and abs(span-35.0)<=0.20,"mm":span},
    ]
    report["derived"]={
        "P003_D16_hits":d16,
        "P007_D14p10_hits":d141,
        "P007_D10_hits":d10,
        "P007_D9p4_hits":d94,
        "P007_X_span_mm":span,
        "checks":checks,
    }

    # Main success criterion is that direct native topology was actually read.
    body_ok=bool(p3["bodies"]) and bool(p7["bodies"])
    feature_ok=len(p3["feature_tree"])>2 and len(p7["feature_tree"])>2
    if body_ok and feature_ok:
        report["status"]="PASS_NATIVE_TOPOLOGY_CAPTURED"
    else:
        report["status"]="HOLD_NATIVE_API_CAPTURE"

    report["next"]="Use this report directly to generate Gate04C2 candidate writer. No more assembly preflight."
    with open(rp,"w",encoding="utf-8") as f:
        json.dump(report,f,indent=2,ensure_ascii=False)

    for c in checks:
        obs=c.get("mm",c.get("count",""))
        print(("[PASS] " if c["pass"] else "[INFO] ")+c["check"],obs)
    print("STATUS:",report["status"])
    print("Report:",rp)
    print("No CAD was modified or saved.")
    return 0 if report["status"]=="PASS_NATIVE_TOPOLOGY_CAPTURED" else 2

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        traceback.print_exc()
        rp=report_path()
        fail={
            "schema":"k01_gate04c1_direct_part_native_audit_v3",
            "created_utc":utc(),
            "status":"FAIL_EXCEPTION",
            "read_only":True,
            "error":repr(e),
            "traceback":traceback.format_exc(),
        }
        try:
            with open(rp,"w",encoding="utf-8") as f:
                json.dump(fail,f,indent=2,ensure_ascii=False)
            print("Failure report:",rp)
        except Exception:
            pass
        raise
