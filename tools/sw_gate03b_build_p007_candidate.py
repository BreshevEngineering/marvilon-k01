from __future__ import annotations

import json
import math
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from sw_com import member0, call


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "cad" / "current" / "K01_P007_GATE03B_BUILD.json"
REPORT.parent.mkdir(parents=True, exist_ok=True)

CANDIDATE_DIR = Path(r"D:\Marvilon\K01\cad\candidates")
BASE_NAME = "K01-P-007_Hermetic_Magnetic_Can_GATE03B_V4_CANDIDATE"

# Axial x / radial y meridian profile, mm.
# CRITICAL: x=35 -> r=0 -> x=34 -> r=4.7 creates the 1.0 mm BLIND rear wall.
P = [
    (0.0, 7.0),
    (1.0, 7.0),
    (1.0, 8.0),
    (3.0, 8.0),
    (3.0, 5.0),
    (35.0, 5.0),
    (35.0, 0.0),
    (34.0, 0.0),
    (34.0, 4.7),
    (2.0, 4.7),
    (2.0, 5.4585),
    (0.0, 5.4585),
]

EXPECTED_VOLUME_MM3 = 661.3981049223248
VOLUME_TOL_MM3 = 0.10


def m(mm):
    return float(mm) / 1000.0


def sw_release_from_revision(revision):
    text = str(revision or "")
    try:
        major = int(text.split(".")[0])
    except Exception:
        return {"revision": text, "major": None, "year": None}
    year = major + 1992 if 19 <= major <= 60 else None
    return {"revision": text, "major": major, "year": year}


def get_active_sketch(sketch_mgr):
    return member0(sketch_mgr, "ActiveSketch", default=None)


def start_2d_sketch(model, sketch_mgr):
    diagnostics = []

    _, err = call(sketch_mgr, "InsertSketch", True, default=None)
    if err:
        diagnostics.append(f"SketchManager.InsertSketch: {err}")

    active, aerr = get_active_sketch(sketch_mgr)
    if aerr:
        diagnostics.append(f"ActiveSketch after InsertSketch: {aerr}")

    if active is not None:
        return active, diagnostics

    # SW2018-compatible fallback.
    _, err = call(model, "InsertSketch2", True, default=None)
    if err:
        diagnostics.append(f"ModelDoc2.InsertSketch2 fallback: {err}")

    active, aerr = get_active_sketch(sketch_mgr)
    if aerr:
        diagnostics.append(f"ActiveSketch after InsertSketch2: {aerr}")

    if active is None:
        raise RuntimeError(
            "Could not enter a 2D sketch. "
            f"Diagnostics: {diagnostics}"
        )

    return active, diagnostics


def close_sketch(sketch_mgr):
    _, err = call(sketch_mgr, "InsertSketch", True, default=None)
    if err:
        raise RuntimeError(f"Closing sketch failed: {err}")

    active, aerr = get_active_sketch(sketch_mgr)
    if aerr:
        raise RuntimeError(f"ActiveSketch check after close failed: {aerr}")
    if active is not None:
        raise RuntimeError("Sketch did not close; ActiveSketch is still non-null.")


def find_latest_profile_feature(model):
    feat, err = member0(model, "FirstFeature", default=None)
    if err:
        raise RuntimeError(err)

    found = []
    while feat is not None:
        typ, _ = member0(feat, "GetTypeName2", default="")
        if str(typ) == "ProfileFeature":
            found.append(feat)
        feat, err = member0(feat, "GetNextFeature", default=None)
        if err:
            raise RuntimeError(err)

    return found[-1] if found else None


def select_feature(feat, append=False, mark=0, label="feature"):
    ok, err = call(feat, "Select2", bool(append), int(mark), default=False)
    if err:
        raise RuntimeError(f"{label}.Select2 failed: {err}")
    if not ok:
        raise RuntimeError(f"{label}.Select2 returned False.")


def select_segment(segment, append=True, mark=16):
    ok, err = call(segment, "Select2", bool(append), int(mark), default=False)
    if err:
        raise RuntimeError(f"centerline.Select2 failed: {err}")
    if not ok:
        raise RuntimeError("centerline.Select2 returned False.")


def clear_selection(model):
    _, err = call(model, "ClearSelection2", True, default=None)
    if err:
        raise RuntimeError(f"ClearSelection2 failed: {err}")


def solid_body(model):
    bodies, err = call(model, "GetBodies2", 0, True, default=None)
    if err:
        raise RuntimeError(err)
    if bodies is None:
        bodies, err = call(model, "GetBodies2", 0, False, default=None)
        if err:
            raise RuntimeError(err)

    try:
        bodies = list(bodies)
    except Exception:
        bodies = [bodies]

    bodies = [b for b in bodies if b is not None]
    if len(bodies) != 1:
        raise RuntimeError(f"Expected exactly 1 solid body, got {len(bodies)}.")
    return bodies[0]


def body_box_mm(body):
    box, err = member0(body, "GetBodyBox", default=None)
    if err or box is None:
        raise RuntimeError(err or "GetBodyBox returned None.")
    return [float(x) * 1000.0 for x in list(box)]


def body_volume_mm3(body):
    props, err = call(body, "GetMassProperties", 1.0, default=None)
    if err:
        raise RuntimeError(f"IBody2.GetMassProperties failed: {err}")
    if props is None:
        raise RuntimeError("IBody2.GetMassProperties returned None.")

    vals = list(props)
    if len(vals) < 4:
        raise RuntimeError(f"Unexpected mass-properties array: {vals!r}")

    # SOLIDWORKS API metric volume = m^3.
    return float(vals[3]) * 1.0e9


def save_as(model, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    rc, err = call(model, "SaveAs3", str(target), 0, 1, default=None)
    if err:
        raise RuntimeError(f"SaveAs3({target.suffix}) failed: {err}")
    if not target.exists():
        raise RuntimeError(f"SaveAs3 did not create {target}; rc={rc!r}")
    return rc


def create_line(sketch_mgr, p1, p2, label):
    seg, err = call(
        sketch_mgr,
        "CreateLine",
        m(p1[0]), m(p1[1]), 0.0,
        m(p2[0]), m(p2[1]), 0.0,
        default=None,
    )
    if err:
        raise RuntimeError(f"{label} CreateLine COM error: {err}")
    if seg is None:
        active, aerr = get_active_sketch(sketch_mgr)
        raise RuntimeError(
            f"{label} CreateLine returned None. "
            f"ActiveSketch={'YES' if active is not None else 'NO'}; "
            f"ActiveSketch error={aerr!r}."
        )
    return seg


def main():
    pythoncom.CoInitialize()
    sw = win32com.client.GetActiveObject("SldWorks.Application")

    revision, rerr = member0(sw, "RevisionNumber", default="")
    if rerr:
        raise RuntimeError(f"Cannot read SOLIDWORKS RevisionNumber: {rerr}")
    rel = sw_release_from_revision(revision)

    model, err = member0(sw, "ActiveDoc", default=None)
    if err:
        raise RuntimeError(f"ActiveDoc failed: {err}")
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    title, _ = member0(model, "GetTitle", default="")
    dtype, _ = member0(model, "GetType", default=None)
    path, _ = member0(model, "GetPathName", default="")

    print(f"[INFO] SOLIDWORKS revision: {rel['revision']}")
    if rel["year"]:
        print(f"[INFO] Detected release:    SOLIDWORKS {rel['year']}")
    print(f"[INFO] Active document:    {title}")
    print(f"[INFO] Document type:      {dtype}")
    print(f"[INFO] Path:               {path or '[UNSAVED]'}")

    if int(dtype) != 1:
        raise RuntimeError(f"Gate03B requires a Part. Got {title!r}, type={dtype!r}.")
    if str(path or ""):
        raise RuntimeError(
            "Gate03B requires a NEW UNSAVED blank Part. "
            "Refusing to modify a saved/production file."
        )

    sketch_mgr, err = member0(model, "SketchManager", default=None)
    if err or sketch_mgr is None:
        raise RuntimeError(err or "SketchManager unavailable.")

    feat_mgr, err = member0(model, "FeatureManager", default=None)
    if err or feat_mgr is None:
        raise RuntimeError(err or "FeatureManager unavailable.")

    active_sketch, diag = start_2d_sketch(model, sketch_mgr)
    print("[PASS] 2D sketch is active.")
    for item in diag:
        print("[INFO]", item)

    old_add = None
    old_disp = None
    try:
        old_add = sketch_mgr.AddToDB
        sketch_mgr.AddToDB = True
    except Exception:
        pass
    try:
        old_disp = sketch_mgr.DisplayWhenAdded
        sketch_mgr.DisplayWhenAdded = False
    except Exception:
        pass

    centerline, err = call(
        sketch_mgr, "CreateCenterLine",
        m(-5.0), 0.0, 0.0,
        m(40.0), 0.0, 0.0,
        default=None,
    )
    if err or centerline is None:
        raise RuntimeError(f"CreateCenterLine failed: {err}")

    try:
        centerline.ConstructionGeometry = True
    except Exception:
        pass

    for i, (p1, p2) in enumerate(zip(P, P[1:] + P[:1]), start=1):
        create_line(sketch_mgr, p1, p2, f"profile line {i}")

    if old_disp is not None:
        try:
            sketch_mgr.DisplayWhenAdded = old_disp
        except Exception:
            pass
    if old_add is not None:
        try:
            sketch_mgr.AddToDB = old_add
        except Exception:
            pass

    try:
        model.GraphicsRedraw2()
    except Exception:
        pass

    sketch_feature = None
    try:
        sketch_feature = active_sketch.GetFeature()
    except Exception:
        pass

    close_sketch(sketch_mgr)
    print("[PASS] Profile sketch created and closed.")

    if sketch_feature is None:
        sketch_feature = find_latest_profile_feature(model)
    if sketch_feature is None:
        raise RuntimeError("Could not resolve created sketch Feature.")

    try:
        sketch_feature.Name = "K01_SKETCH_P007_GATE03B_V4_PROFILE"
    except Exception:
        pass

    clear_selection(model)
    select_feature(sketch_feature, append=False, mark=0, label="profile sketch")
    select_segment(centerline, append=True, mark=16)

    revolve, err = call(
        feat_mgr, "FeatureRevolve2",
        True, True, False, False, False, False,
        0, 0,
        2 * math.pi, 0.0,
        False, False,
        0.01, 0.01,
        0,
        0.0, 0.0,
        True, True, True,
        default=None,
    )
    if err or revolve is None:
        raise RuntimeError(f"FeatureRevolve2 failed: {err or 'returned None'}")

    try:
        revolve.Name = "K01_F01_REVOLVE_P007_GATE03B_V4"
    except Exception:
        pass

    call(model, "ForceRebuild3", False, default=None)

    body = solid_body(model)
    box = body_box_mm(body)
    volume = body_volume_mm3(body)

    bbox_checks = {
        "xmin": abs(box[0] - 0.0) <= 0.02,
        "xmax": abs(box[3] - 35.0) <= 0.02,
        "ymin": abs(box[1] + 8.0) <= 0.02,
        "ymax": abs(box[4] - 8.0) <= 0.02,
        "zmin": abs(box[2] + 8.0) <= 0.02,
        "zmax": abs(box[5] - 8.0) <= 0.02,
    }
    if not all(bbox_checks.values()):
        raise RuntimeError(
            f"BREP bbox validation failed. box_mm={box}, checks={bbox_checks}"
        )

    volume_delta = abs(volume - EXPECTED_VOLUME_MM3)
    if volume_delta > VOLUME_TOL_MM3:
        raise RuntimeError(
            "BREP semantic validation failed: volume does not match the required "
            f"BLIND-END geometry. volume={volume:.6f} mm^3, "
            f"expected={EXPECTED_VOLUME_MM3:.6f} mm^3, "
            f"delta={volume_delta:.6f} mm^3."
        )

    print(
        f"[PASS] Blind-end volume check: {volume:.6f} mm^3 "
        f"(expected {EXPECTED_VOLUME_MM3:.6f})"
    )

    material = {
        "requested": "AISI Type 316L stainless steel",
        "authority": "AISI 316L / EN 1.4404",
        "applied": False,
        "error": None,
    }
    try:
        cfg_mgr, _ = member0(model, "ConfigurationManager", default=None)
        cfg, _ = member0(cfg_mgr, "ActiveConfiguration", default=None)
        cfg_name, _ = member0(cfg, "Name", default="Default")
        _, merr = call(
            model, "SetMaterialPropertyName2",
            str(cfg_name), "SOLIDWORKS Materials", material["requested"],
            default=None,
        )
        if merr:
            material["error"] = merr
        else:
            material["applied"] = True
    except Exception as exc:
        material["error"] = f"{type(exc).__name__}: {exc}"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    native = CANDIDATE_DIR / f"{BASE_NAME}_{stamp}.SLDPRT"
    step = CANDIDATE_DIR / f"{BASE_NAME}_{stamp}.STEP"

    save_as(model, native)
    save_as(model, step)

    report = {
        "schema": "k01_p007_gate03b_build_v4_blind_end",
        "status": "PASS",
        "solidworks": rel,
        "production_cad_modified": False,
        "supersedes_candidate": (
            "K01-P-007_Hermetic_Magnetic_Can_GATE03B_CANDIDATE_20260902_085544"
        ),
        "superseded_reason": (
            "v3 had an annular OPEN rear end; v4 restores the 1.0 mm blind rear wall"
        ),
        "native_candidate": str(native),
        "step_candidate": str(step),
        "body_box_mm": box,
        "body_volume_mm3": volume,
        "expected_volume_mm3": EXPECTED_VOLUME_MM3,
        "volume_delta_mm3": volume_delta,
        "material": material,
        "controlled_geometry_mm": {
            "total_length": 35.0,
            "weld_face_OD": 14.0,
            "weld_face_ID": 10.917,
            "weld_wall_radial_thickness": (14.0 - 10.917) / 2.0,
            "weld_land_length": 1.0,
            "root_OD": 16.0,
            "root_outer_start": 1.0,
            "thin_ID": 9.4,
            "thin_ID_start": 2.0,
            "thin_OD": 10.0,
            "thin_OD_start": 3.0,
            "rear_inner_station": 34.0,
            "rear_outer_station": 35.0,
            "rear_wall_axial_thickness": 1.0,
        },
        "release_status": "CANDIDATE_NOT_RELEASED",
    }
    REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 70)
    print("K01 Gate 03B v4 - P007 BLIND-END candidate")
    print("=" * 70)
    print("PASS: native P007 v4 candidate created.")
    print("Native:", native)
    print("STEP:  ", step)
    print("Report:", REPORT)
    print("BREP bbox [mm]:", box)
    print("BREP volume [mm^3]:", volume)
    if material["error"]:
        print("WARN material assignment:", material["error"])
    print("Production P007 was NOT modified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: Gate03B v4 P007 candidate builder")
        traceback.print_exc()
        sys.exit(1)
