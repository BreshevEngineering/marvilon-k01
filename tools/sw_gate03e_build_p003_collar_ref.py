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
REPORT = ROOT / "reports" / "cad" / "current" / "K01_P003_GATE03E_COLLAR_REF_BUILD.json"
REPORT.parent.mkdir(parents=True, exist_ok=True)

OUTDIR = Path(r"D:\Marvilon\K01\cad\candidates")
BASE = "K01-P-003_GATE03E_COLLAR_ADDON_REFERENCE"

# Reference add-on only:
# local x = 0..5 mm, OD16 / ID14.
P = [
    (0.0, 7.0),
    (5.0, 7.0),
    (5.0, 8.0),
    (0.0, 8.0),
]

EXPECTED_VOLUME_MM3 = math.pi * (8.0**2 - 7.0**2) * 5.0
VOLUME_TOL_MM3 = 0.05


def m(v_mm):
    return float(v_mm) / 1000.0


def get_active_sketch(sketch_mgr):
    return member0(sketch_mgr, "ActiveSketch", default=None)


def start_sketch(model, sketch_mgr):
    diagnostics = []

    _, err = call(sketch_mgr, "InsertSketch", True, default=None)
    if err:
        diagnostics.append(f"SketchManager.InsertSketch: {err}")

    active, aerr = get_active_sketch(sketch_mgr)
    if aerr:
        diagnostics.append(f"ActiveSketch after InsertSketch: {aerr}")

    if active is not None:
        return active, diagnostics

    # SW2018 fallback.
    _, err2 = call(model, "InsertSketch2", True, default=None)
    if err2:
        diagnostics.append(f"ModelDoc2.InsertSketch2: {err2}")

    active, aerr = get_active_sketch(sketch_mgr)
    if aerr:
        diagnostics.append(f"ActiveSketch after InsertSketch2: {aerr}")

    if active is None:
        raise RuntimeError(
            "Could not enter 2D sketch. Diagnostics: " + " | ".join(diagnostics)
        )

    return active, diagnostics


def close_sketch(sketch_mgr):
    _, err = call(sketch_mgr, "InsertSketch", True, default=None)
    if err:
        raise RuntimeError(f"Closing sketch failed: {err}")

    active, aerr = get_active_sketch(sketch_mgr)
    if aerr:
        raise RuntimeError(f"ActiveSketch readback failed: {aerr}")
    if active is not None:
        raise RuntimeError("Sketch did not close; ActiveSketch is still non-null.")


def latest_profile(model):
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


def select2(obj, append=False, mark=0, label="object"):
    ok, err = call(obj, "Select2", bool(append), int(mark), default=False)
    if err:
        raise RuntimeError(f"{label}.Select2 failed: {err}")
    if not ok:
        raise RuntimeError(f"{label}.Select2 returned False.")


def one_body(model):
    bodies, err = call(model, "GetBodies2", 0, True, default=None)
    if err:
        raise RuntimeError(err)
    if bodies is None:
        bodies, err = call(model, "GetBodies2", 0, False, default=None)
        if err:
            raise RuntimeError(err)

    try:
        rows = list(bodies)
    except Exception:
        rows = [bodies]

    rows = [b for b in rows if b is not None]
    if len(rows) != 1:
        raise RuntimeError(f"Expected one solid body, got {len(rows)}.")
    return rows[0]


def volume_mm3(body):
    props, err = call(body, "GetMassProperties", 1.0, default=None)
    if err or props is None:
        raise RuntimeError(err or "GetMassProperties returned None.")

    vals = list(props)
    if len(vals) < 4:
        raise RuntimeError(f"Unexpected mass-properties array: {vals!r}")

    return float(vals[3]) * 1.0e9


def bbox_mm(body):
    box, err = member0(body, "GetBodyBox", default=None)
    if err or box is None:
        raise RuntimeError(err or "GetBodyBox returned None.")
    return [float(x) * 1000.0 for x in list(box)]


def save_as(model, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    rc, err = call(model, "SaveAs3", str(target), 0, 1, default=None)
    if err:
        raise RuntimeError(f"SaveAs3 failed: {err}")
    if not target.exists():
        raise RuntimeError(f"SaveAs3 did not create {target}; rc={rc!r}")


def create_line(sketch_mgr, p1, p2, index):
    seg, err = call(
        sketch_mgr,
        "CreateLine",
        m(p1[0]), m(p1[1]), 0.0,
        m(p2[0]), m(p2[1]), 0.0,
        default=None,
    )
    if err:
        raise RuntimeError(f"profile line {index}: COM error: {err}")

    if seg is None:
        active, aerr = get_active_sketch(sketch_mgr)
        raise RuntimeError(
            f"profile line {index}: CreateLine returned None for {p1}->{p2}; "
            f"ActiveSketch={'YES' if active is not None else 'NO'}; "
            f"ActiveSketch read error={aerr!r}"
        )

    return seg


def main():
    pythoncom.CoInitialize()

    sw = win32com.client.GetActiveObject("SldWorks.Application")

    revision, _ = member0(sw, "RevisionNumber", default="")
    model, err = member0(sw, "ActiveDoc", default=None)
    if err or model is None:
        raise RuntimeError(err or "No active SOLIDWORKS document.")

    dtype, _ = member0(model, "GetType", default=None)
    title, _ = member0(model, "GetTitle", default="")
    path, _ = member0(model, "GetPathName", default="")

    print(f"[INFO] SOLIDWORKS revision: {revision}")
    print(f"[INFO] Active document:    {title}")
    print(f"[INFO] Path:               {path or '[UNSAVED]'}")

    if int(dtype) != 1:
        raise RuntimeError(f"Active document must be Part, got type={dtype!r}.")
    if str(path or ""):
        raise RuntimeError(
            "Builder requires a NEW UNSAVED blank Part. "
            "Refusing to modify a saved file."
        )

    sketch_mgr, err = member0(model, "SketchManager", default=None)
    if err or sketch_mgr is None:
        raise RuntimeError(err or "SketchManager unavailable.")

    feat_mgr, err = member0(model, "FeatureManager", default=None)
    if err or feat_mgr is None:
        raise RuntimeError(err or "FeatureManager unavailable.")

    active_sketch, diag = start_sketch(model, sketch_mgr)
    print("[PASS] 2D sketch is active.")
    for item in diag:
        print("[INFO]", item)

    # Same SW2018-safe strategy as the P007-v5 builder:
    # disable sketch inference / UI update while creating exact segments.
    old_add = None
    old_display = None

    try:
        old_add = sketch_mgr.AddToDB
        sketch_mgr.AddToDB = True
    except Exception:
        pass

    try:
        old_display = sketch_mgr.DisplayWhenAdded
        sketch_mgr.DisplayWhenAdded = False
    except Exception:
        pass

    centerline, err = call(
        sketch_mgr,
        "CreateCenterLine",
        m(-1.0), 0.0, 0.0,
        m(6.0), 0.0, 0.0,
        default=None,
    )
    if err or centerline is None:
        raise RuntimeError(err or "CreateCenterLine returned None.")

    try:
        centerline.ConstructionGeometry = True
    except Exception:
        pass

    for i, (p1, p2) in enumerate(zip(P, P[1:] + P[:1]), start=1):
        create_line(sketch_mgr, p1, p2, i)

    if old_display is not None:
        try:
            sketch_mgr.DisplayWhenAdded = old_display
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
    print("[PASS] Collar profile sketch created and closed.")

    if sketch_feature is None:
        sketch_feature = latest_profile(model)
    if sketch_feature is None:
        raise RuntimeError("Could not resolve collar sketch feature.")

    try:
        sketch_feature.Name = "K01_SKETCH_P003_GATE03E_COLLAR_REF"
    except Exception:
        pass

    call(model, "ClearSelection2", True, default=None)
    select2(sketch_feature, False, 0, "profile sketch")
    select2(centerline, True, 16, "revolve centerline")

    revolve, err = call(
        feat_mgr,
        "FeatureRevolve2",
        True, True, False, False, False, False,
        0, 0,
        2.0 * math.pi, 0.0,
        False, False,
        0.01, 0.01,
        0,
        0.0, 0.0,
        True, True, True,
        default=None,
    )

    if err or revolve is None:
        raise RuntimeError(err or "FeatureRevolve2 returned None.")

    try:
        revolve.Name = "K01_F01_REVOLVE_P003_GATE03E_COLLAR_REF"
    except Exception:
        pass

    call(model, "ForceRebuild3", False, default=None)

    body = one_body(model)
    vol = volume_mm3(body)
    box = bbox_mm(body)

    if abs(vol - EXPECTED_VOLUME_MM3) > VOLUME_TOL_MM3:
        raise RuntimeError(
            f"Volume validation failed: {vol:.9f} vs "
            f"{EXPECTED_VOLUME_MM3:.9f} mm^3"
        )

    expected_box = [0.0, -8.0, -8.0, 5.0, 8.0, 8.0]
    if max(abs(box[i] - expected_box[i]) for i in range(6)) > 0.02:
        raise RuntimeError(f"BBox validation failed: {box}")

    # Assign the same material authority as P003.
    material = {
        "authority": "AISI 316L / EN 1.4404",
        "applied": False,
        "error": None,
    }
    try:
        cfg_mgr, _ = member0(model, "ConfigurationManager", default=None)
        cfg, _ = member0(cfg_mgr, "ActiveConfiguration", default=None)
        cfg_name, _ = member0(cfg, "Name", default="Default")
        _, merr = call(
            model,
            "SetMaterialPropertyName2",
            str(cfg_name),
            "SOLIDWORKS Materials",
            "AISI Type 316L stainless steel",
            default=None,
        )
        if merr:
            material["error"] = merr
        else:
            material["applied"] = True
    except Exception as exc:
        material["error"] = f"{type(exc).__name__}: {exc}"

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    native = OUTDIR / f"{BASE}_{stamp}.SLDPRT"
    step = OUTDIR / f"{BASE}_{stamp}.STEP"

    save_as(model, native)
    save_as(model, step)

    report = {
        "schema": "k01_p003_gate03e_collar_ref_v2_sw2018",
        "status": "PASS",
        "solidworks_revision": str(revision),
        "native_reference": str(native),
        "step_reference": str(step),
        "body_box_mm": box,
        "body_volume_mm3": vol,
        "expected_volume_mm3": EXPECTED_VOLUME_MM3,
        "material": material,
        "controlled_geometry_mm": {
            "length": 5.0,
            "OD": 16.0,
            "ID": 14.0,
        },
        "note": (
            "REFERENCE ADD-ON ONLY. Represents material to be added to P003 "
            "over x=-5..0 mm relative to current P003 rear face. "
            "Not a production P003 part."
        ),
    }

    REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 68)
    print("K01 Gate03E STEP 2 - P003 COLLAR ADD-ON REFERENCE v2")
    print("=" * 68)
    print("[PASS] Native collar reference created.")
    print(f"[PASS] Volume: {vol:.9f} mm^3")
    print("Native:", native)
    print("STEP:  ", step)
    print("Report:", REPORT)
    print("Production P003 was NOT modified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: P003 Gate03E collar reference builder v2")
        traceback.print_exc()
        sys.exit(1)
