"""
K01 Gate04C1 v02 — J2 NATIVE PREFLIGHT / READ-ONLY
==================================================

Fix vs v01
----------
v01 incorrectly called GetRootComponent3 on ModelDoc2.
GetRootComponent3 belongs to IConfiguration.
v02 obtains:
    model.ConfigurationManager.ActiveConfiguration.GetRootComponent3(True)

A fallback component enumeration path is also included.

READ-ONLY GUARANTEE
-------------------
This script does NOT call:
- Save / SaveAs / Save3
- Feature creation/deletion/suppression
- ReplaceComponents*
- Mate creation/deletion
- Master/BOM mutation

It only opens/activates the stable assembly and interrogates CAD.

Expected environment
--------------------
SOLIDWORKS 2018 / revision 26.0.1
Python 3.12 + pywin32
"""

from __future__ import annotations
import json
import math
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
from win32com.client import dynamic

SW_DOC_PART = 1
SW_DOC_ASM = 2
SW_OPEN_SILENT = 1
SW_BODY_SOLID = 0

STABLE_ASM = r"D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM"
P003_STABLE = r"D:\Marvilon\K01\cad\parts\K01-P-003_Cartridge_Body.SLDPRT"
P007_STABLE = r"D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT"

P003_TOKEN = "K01-P-003_Cartridge_Body"
P007_TOKEN = "K01-P-007_Hermetic_Magnetic_Can"

TARGET = {
    "P003_material": "AISI 316L / EN 1.4404",
    "P007_material": "AISI 316L / EN 1.4404",
    "P003_current_rear_OD_mm": 16.0,
    "P003_current_rear_zone_L_mm": 5.0,
    "P007_OAL_mm": 35.0,
    "P007_current_root_ID_mm": 14.10,
    "P007_thin_OD_mm": 10.0,
    "P007_thin_ID_mm": 9.4,
    "P007_thin_wall_mm": 0.30,
    "J2_flange_OD_mm": 36.0,
    "J2_PCD_mm": 28.0,
    "J2_M3_clearance_D_mm": 3.4,
    "J2_pilot_nominal_D_mm": 14.10,
    "J2_pilot_male_L_mm": 1.50,
    "J2_pilot_female_depth_mm": 1.70,
    "J2_seal_size": "16x1.5 mm",
    "J2_gland_ID_mm": 16.00,
    "J2_gland_radial_width_mm": 2.10,
    "J2_gland_depth_mm": 1.10,
    "J2_gland_OD_nominal_mm": 20.20,
    "J2_gland_OD_design_max_mm": 20.60,
}

TOL_D_MM = 0.05
TOL_OAL_MM = 0.15


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def norm_path(p):
    if not p:
        return ""
    return os.path.normcase(os.path.abspath(p))


def repo_root():
    here = Path(__file__).resolve()
    for p in [here.parent] + list(here.parents):
        if (p / "reports").exists() and ((p / "master").exists() or (p / "control").exists()):
            return p
    return here.parent


def report_path():
    p = repo_root() / "reports" / "cad" / "current"
    p.mkdir(parents=True, exist_ok=True)
    return p / "K01_GATE04C1_J2_NATIVE_PREFLIGHT.json"


def connect_sw():
    pythoncom.CoInitialize()
    sw = dynamic.Dispatch("SldWorks.Application")
    sw.Visible = True
    try:
        sw.UserControl = True
    except Exception:
        pass
    return sw


def sw_revision(sw):
    for expr in (
        lambda: sw.RevisionNumber(),
        lambda: sw.RevisionNumber,
    ):
        try:
            return str(expr())
        except Exception:
            pass
    return "UNKNOWN"


def doc_type(doc):
    try:
        return int(doc.GetType())
    except Exception:
        return None


def doc_path(doc):
    try:
        return str(doc.GetPathName())
    except Exception:
        return ""


def activate_or_open_stable_asm(sw):
    active = sw.ActiveDoc
    if active is not None and doc_type(active) == SW_DOC_ASM:
        if norm_path(doc_path(active)) == norm_path(STABLE_ASM):
            return active, "already_active"

    # Try ActivateDoc3 by title, in case already open.
    try:
        title = os.path.basename(STABLE_ASM)
        act = sw.ActivateDoc3(title, True, 0, 0)
        if act is not None and doc_type(act) == SW_DOC_ASM:
            if norm_path(doc_path(act)) == norm_path(STABLE_ASM):
                return act, "activated_existing"
    except Exception:
        pass

    if not os.path.exists(STABLE_ASM):
        raise RuntimeError(f"Stable A001 not found: {STABLE_ASM}")

    doc = None
    try:
        doc = sw.OpenDoc6(STABLE_ASM, SW_DOC_ASM, SW_OPEN_SILENT, "", 0, 0)
    except Exception:
        pass
    if doc is None:
        try:
            doc = sw.OpenDoc(STABLE_ASM, SW_DOC_ASM)
        except Exception:
            pass
    if doc is None:
        raise RuntimeError("SOLIDWORKS could not open stable A001.")
    if doc_type(doc) != SW_DOC_ASM:
        raise RuntimeError(f"Opened document is not an assembly. GetType={doc_type(doc)}")
    return doc, "opened_stable"


def get_root_component(model):
    """
    Correct SW API path:
        IModelDoc2.ConfigurationManager
        -> IConfigurationManager.ActiveConfiguration
        -> IConfiguration.GetRootComponent3(True)
    """
    diagnostics = []

    try:
        cm = model.ConfigurationManager
        cfg = cm.ActiveConfiguration
        root = cfg.GetRootComponent3(True)
        if root is not None:
            diagnostics.append("ConfigurationManager.ActiveConfiguration.GetRootComponent3(True): PASS")
            return root, diagnostics
        diagnostics.append("GetRootComponent3 returned None")
    except Exception as e:
        diagnostics.append(f"Configuration root path failed: {type(e).__name__}: {e}")

    # Some COM wrappers expose GetRootComponent3 as a property-like late-bound member.
    try:
        cm = model.ConfigurationManager
        cfg = cm.ActiveConfiguration
        fn = getattr(cfg, "GetRootComponent3")
        root = fn(True)
        if root is not None:
            diagnostics.append("late-bound IConfiguration.GetRootComponent3(True): PASS")
            return root, diagnostics
    except Exception as e:
        diagnostics.append(f"late-bound IConfiguration path failed: {type(e).__name__}: {e}")

    raise RuntimeError("Cannot obtain assembly root component. " + " | ".join(diagnostics))


def safe_children(comp):
    try:
        arr = comp.GetChildren()
        return list(arr) if arr else []
    except Exception:
        return []


def walk_components(root):
    q = safe_children(root)
    seen = set()
    while q:
        c = q.pop(0)
        ident = id(c)
        if ident in seen:
            continue
        seen.add(ident)
        yield c
        q.extend(safe_children(c))


def comp_name(c):
    for f in (lambda: c.Name2, lambda: c.Name):
        try:
            return str(f())
        except Exception:
            pass
    return ""


def comp_path(c):
    try:
        return str(c.GetPathName())
    except Exception:
        return ""


def comp_model(c):
    try:
        return c.GetModelDoc2()
    except Exception:
        return None


def find_component(root, token, expected_path):
    exact, token_hits = [], []
    for c in walk_components(root):
        p, n = comp_path(c), comp_name(c)
        if p and norm_path(p) == norm_path(expected_path):
            exact.append(c)
        if token.lower() in n.lower() or (p and token.lower() in os.path.basename(p).lower()):
            token_hits.append(c)

    candidates = exact or token_hits
    if not candidates:
        raise RuntimeError(f"Component not found in stable A001: {token}")

    for c in candidates:
        if comp_model(c) is not None:
            return c

    raise RuntimeError(f"Component found but unresolved: {token}")


def to_list(v):
    if v is None:
        return None
    try:
        return [float(x) for x in list(v)]
    except Exception:
        return None


def component_transform(comp):
    try:
        t = comp.Transform2
        if t is not None:
            return to_list(t.ArrayData)
    except Exception:
        pass
    return None


def component_box_mm(comp):
    try:
        bb = to_list(comp.GetBox())
        if bb and len(bb) >= 6:
            return [1000.0 * x for x in bb[:6]]
    except Exception:
        pass
    return None


def get_feature_tree(model):
    rows = []
    try:
        f = model.FirstFeature()
    except Exception:
        f = None

    guard = 0
    while f is not None and guard < 2000:
        guard += 1
        try:
            name = str(f.Name)
        except Exception:
            name = ""
        try:
            typ = str(f.GetTypeName2())
        except Exception:
            typ = ""
        try:
            suppressed = bool(f.IsSuppressed())
        except Exception:
            suppressed = None
        rows.append({"name": name, "type": typ, "suppressed": suppressed})

        try:
            f = f.GetNextFeature()
        except Exception:
            break
    return rows


def custom_props(model):
    keys = ["PartNo", "Description", "Material", "MaterialSpec", "Revision", "Status", "Process", "Note"]
    out = {}
    try:
        mgr = model.Extension.CustomPropertyManager("")
    except Exception:
        return out

    for k in keys:
        value = ""
        # Newer API
        try:
            ret = mgr.Get6(k, False, "", "", False, False)
            if isinstance(ret, tuple):
                ss = [x for x in ret if isinstance(x, str)]
                value = ss[-1] if ss else ""
            elif isinstance(ret, str):
                value = ret
        except Exception:
            pass
        # SW2018-safe fallback
        if not value:
            try:
                ret = mgr.Get4(k, False, "", "")
                if isinstance(ret, tuple):
                    ss = [x for x in ret if isinstance(x, str)]
                    value = ss[-1] if ss else ""
                elif isinstance(ret, str):
                    value = ret
            except Exception:
                pass
        if not value:
            try:
                ret = mgr.Get2(k, "", "")
                if isinstance(ret, tuple):
                    ss = [x for x in ret if isinstance(x, str)]
                    value = ss[-1] if ss else ""
                elif isinstance(ret, str):
                    value = ret
            except Exception:
                pass
        out[k] = value
    return out


def material_name(model):
    # Diagnostic only. Master/control is authoritative.
    try:
        cfg = str(model.ConfigurationManager.ActiveConfiguration.Name)
    except Exception:
        cfg = ""
    for c in (cfg, ""):
        try:
            ret = model.GetMaterialPropertyName2(c, "")
            if isinstance(ret, tuple):
                ss = [x for x in ret if isinstance(x, str) and x.strip()]
                if ss:
                    return ss[-1]
            elif isinstance(ret, str) and ret.strip():
                return ret
        except Exception:
            pass
    return ""


def body_sources(comp, model):
    """
    Try several SW2018-compatible body access routes.
    No failure here is fatal; report diagnostics instead.
    """
    notes = []
    bodies = []

    # IComponent2 route
    for meth_name in ("GetBodies2",):
        try:
            meth = getattr(comp, meth_name)
            arr = meth(SW_BODY_SOLID)
            if arr:
                bodies = list(arr)
                notes.append(f"IComponent2.{meth_name}: PASS ({len(bodies)} bodies)")
                return bodies, notes
            notes.append(f"IComponent2.{meth_name}: returned empty")
        except Exception as e:
            notes.append(f"IComponent2.{meth_name}: {type(e).__name__}: {e}")

    # IPartDoc late-bound route
    try:
        arr = model.GetBodies2(SW_BODY_SOLID, True)
        if arr:
            bodies = list(arr)
            notes.append(f"IPartDoc.GetBodies2: PASS ({len(bodies)} bodies)")
            return bodies, notes
        notes.append("IPartDoc.GetBodies2: returned empty")
    except Exception as e:
        notes.append(f"IPartDoc.GetBodies2: {type(e).__name__}: {e}")

    return [], notes


def surface_record(face):
    r = {
        "kind": "other",
        "area_mm2": None,
        "plane_point_mm": None,
        "plane_normal": None,
        "cylinder_axis_origin_mm": None,
        "cylinder_axis_direction": None,
        "diameter_mm": None,
    }
    try:
        r["area_mm2"] = float(face.GetArea()) * 1e6
    except Exception:
        pass
    try:
        s = face.GetSurface()
    except Exception:
        return r
    if s is None:
        return r

    try:
        if bool(s.IsPlane()):
            r["kind"] = "plane"
            a = to_list(s.PlaneParams)
            if a and len(a) >= 6:
                # SolidWorks PlaneParams: origin point then normal vector.
                # Some wrappers/documentation present ordering ambiguously.
                # We store raw interpretation and later use only robust axis tests.
                p1 = [1000.0*x for x in a[0:3]]
                n1 = a[3:6]
                p2 = [1000.0*x for x in a[3:6]]
                n2 = a[0:3]

                # Choose which triple is more unit-normal-like.
                def norm3(v): return math.sqrt(sum(x*x for x in v))
                if abs(norm3(n1) - 1.0) <= abs(norm3(n2) - 1.0):
                    r["plane_point_mm"] = p1
                    r["plane_normal"] = n1
                else:
                    r["plane_point_mm"] = p2
                    r["plane_normal"] = n2
            return r
    except Exception:
        pass

    try:
        if bool(s.IsCylinder()):
            r["kind"] = "cylinder"
            a = to_list(s.CylinderParams)
            if a and len(a) >= 7:
                # Common SW API order: origin XYZ, axis XYZ, radius.
                r["cylinder_axis_origin_mm"] = [1000.0*x for x in a[0:3]]
                r["cylinder_axis_direction"] = a[3:6]
                r["diameter_mm"] = 2000.0 * abs(a[6])
            return r
    except Exception:
        pass
    return r


def audit_part(comp, label):
    model = comp_model(comp)
    if model is None:
        raise RuntimeError(f"{label}: unresolved component")

    part = {
        "label": label,
        "component_name": comp_name(comp),
        "path": comp_path(comp),
        "component_transform_raw": component_transform(comp),
        "component_box_assembly_mm": component_box_mm(comp),
        "custom_properties": custom_props(model),
        "solidworks_material_diagnostic": material_name(model),
        "feature_tree": get_feature_tree(model),
        "body_access": [],
        "bodies": [],
    }

    bodies, notes = body_sources(comp, model)
    part["body_access"] = notes
    for bi, body in enumerate(bodies):
        br = {"index": bi, "bbox_mm": None, "faces": []}
        try:
            bb = to_list(body.GetBodyBox())
            if bb and len(bb) >= 6:
                br["bbox_mm"] = [1000.0*x for x in bb[:6]]
        except Exception:
            pass
        try:
            faces = body.GetFaces()
            faces = list(faces) if faces else []
        except Exception:
            faces = []
        for face in faces:
            br["faces"].append(surface_record(face))
        part["bodies"].append(br)
    return part


def all_faces(part):
    out = []
    for b in part["bodies"]:
        out.extend(b["faces"])
    return out


def find_axial_cylinders(part, nominal):
    hits = []
    for f in all_faces(part):
        if f.get("kind") != "cylinder":
            continue
        d = f.get("diameter_mm")
        a = f.get("cylinder_axis_direction")
        if d is None or not a:
            continue
        if abs(d - nominal) > TOL_D_MM:
            continue
        # Axis can be +/- X in native part coordinates.
        if abs(abs(a[0]) - 1.0) < 1e-3 and abs(a[1]) < 1e-3 and abs(a[2]) < 1e-3:
            hits.append(f)
    return hits


def bbox_span_x(part):
    xs = []
    for b in part["bodies"]:
        bb = b.get("bbox_mm")
        if bb and len(bb) >= 6:
            xs += [bb[0], bb[3]]
    if len(xs) >= 2:
        return max(xs) - min(xs)
    return None


def main():
    rp = report_path()
    report = {
        "schema": "k01_gate04c1_j2_native_preflight_v2",
        "status": "RUNNING",
        "created_utc": utc_now(),
        "read_only": True,
        "target": TARGET,
        "fix_from_v01": "GetRootComponent3 moved from ModelDoc2 to ActiveConfiguration/IConfiguration.",
    }

    sw = connect_sw()
    report["solidworks_revision"] = sw_revision(sw)
    asm, activation = activate_or_open_stable_asm(sw)
    report["stable_A001_activation"] = activation
    print(f"[INFO] Stable A001 activation: {activation}")

    root, root_diag = get_root_component(asm)
    report["root_component_api"] = root_diag
    print("[INFO] Root component:", comp_name(root))

    p3c = find_component(root, P003_TOKEN, P003_STABLE)
    p7c = find_component(root, P007_TOKEN, P007_STABLE)

    p3 = audit_part(p3c, "P003")
    p7 = audit_part(p7c, "P007")
    report["parts"] = {"P003": p3, "P007": p7}

    p3_d16 = find_axial_cylinders(p3, 16.0)
    p7_d141 = find_axial_cylinders(p7, 14.10)
    p7_d10 = find_axial_cylinders(p7, 10.0)
    p7_d94 = find_axial_cylinders(p7, 9.4)
    p7_span = bbox_span_x(p7)

    checks = [
        {
            "check": "P003 current axial Ø16 cylindrical face exists",
            "pass": len(p3_d16) >= 1,
            "observed_count": len(p3_d16),
        },
        {
            "check": "P007 current axial Ø14.10 cylindrical face exists",
            "pass": len(p7_d141) >= 1,
            "observed_count": len(p7_d141),
        },
        {
            "check": "P007 axial Ø10 thin-wall OD face exists",
            "pass": len(p7_d10) >= 1,
            "observed_count": len(p7_d10),
        },
        {
            "check": "P007 axial Ø9.4 thin-wall ID face exists",
            "pass": len(p7_d94) >= 1,
            "observed_count": len(p7_d94),
        },
        {
            "check": "P007 body X-span approximately 35 mm",
            "pass": p7_span is not None and abs(p7_span - 35.0) <= TOL_OAL_MM,
            "observed_mm": p7_span,
            "note": "Diagnostic based on native body bounding box; final writer still preserves current OAL.",
        },
    ]

    report["derived"] = {
        "P003_D16_hits": p3_d16,
        "P007_D14p10_hits": p7_d141,
        "P007_D10_hits": p7_d10,
        "P007_D9p4_hits": p7_d94,
        "P007_body_X_span_mm": p7_span,
        "checks": checks,
    }

    body_access_ok = bool(p3["bodies"]) and bool(p7["bodies"])
    if not body_access_ok:
        report["status"] = "HOLD_BODY_API_REVIEW"
    elif all(c["pass"] for c in checks):
        report["status"] = "PASS_PREFLIGHT"
    else:
        report["status"] = "HOLD_GEOMETRY_REVIEW"

    report["next_gate_if_pass"] = (
        "Gate04C2 candidate-only native J2 build: P003 + P007 + verification A001 clone; "
        "no stable promotion until geometry, mates and interference all pass."
    )

    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("=" * 96)
    print("K01 Gate04C1 v02 — J2 NATIVE PREFLIGHT / READ-ONLY")
    print("=" * 96)
    print("SOLIDWORKS revision:", report["solidworks_revision"])
    print("P003:", p3["component_name"])
    print("P007:", p7["component_name"])
    print("[P003] body API:", " | ".join(p3["body_access"]))
    print("[P007] body API:", " | ".join(p7["body_access"]))
    print("-" * 96)
    for c in checks:
        observed = c.get("observed_mm", c.get("observed_count", ""))
        print(("[PASS] " if c["pass"] else "[HOLD] ") + c["check"] + f" -> {observed}")
    print("-" * 96)
    print("STATUS:", report["status"])
    print("Report:", rp)
    print("READ-ONLY: no CAD document was modified or saved.")
    return 0 if report["status"] == "PASS_PREFLIGHT" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        traceback.print_exc()
        rp = report_path()
        fail = {
            "schema": "k01_gate04c1_j2_native_preflight_v2",
            "status": "FAIL_EXCEPTION",
            "created_utc": utc_now(),
            "read_only": True,
            "error": repr(exc),
            "traceback": traceback.format_exc(),
        }
        try:
            with open(rp, "w", encoding="utf-8") as f:
                json.dump(fail, f, indent=2, ensure_ascii=False)
            print("Failure report:", rp)
        except Exception:
            pass
        raise
