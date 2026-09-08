from __future__ import annotations

import json
import math
import os
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from sw_com import member0, call, as_list


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "cad" / "current" / "K01_P008_GATE04A_BUILD.json"
REPORT.parent.mkdir(parents=True, exist_ok=True)

SOURCE = Path(r"D:\Marvilon\K01\cad\parts\K01-P-008_Internal_Magnetic_Follower.SLDPRT")
OUTDIR = Path(r"D:\Marvilon\K01\cad\candidates")
BASE = "K01-P-008_Internal_Magnetic_Follower_GATE04A_POCKET820_CANDIDATE"

SKETCH_NAME = "Sketch1"
EXPECTED_OLD_RADIUS_M = 0.00405       # Ø8.10
TARGET_RADIUS_M = 0.00410             # Ø8.20 nominal
EXPECTED_OD_RADIUS_M = 0.00440        # Ø8.80
EXPECTED_POCKET_DEPTH_M = 0.00820     # 8.20
EXPECTED_ENTRY_CHAMFER_M = 0.00010    # 0.10 x 45°

READBACK_TOL_M = 2.0e-7
BBOX_TOL_MM = 0.01
CYL_TOL_MM = 0.005


def open_doc6(sw, path):
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    loaded = sw.OpenDoc6(str(path), 1, 1, "", errors, warnings)
    if isinstance(loaded, tuple):
        model = next((x for x in loaded if x is not None and hasattr(x, "_oleobj_")), None)
    else:
        model = loaded
    if model is None:
        raise RuntimeError(
            f"OpenDoc6 returned no ModelDoc2; errors={errors.value}, warnings={warnings.value}"
        )
    return model, int(errors.value), int(warnings.value)


def activate_model(sw, model, expected_path):
    title, terr = member0(model, "GetTitle", default="")
    if terr or not title:
        raise RuntimeError(terr or "Could not read candidate title.")
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    activated = sw.ActivateDoc2(str(title), False, errors)
    if isinstance(activated, tuple):
        active = next((x for x in activated if x is not None and hasattr(x, "_oleobj_")), None)
    else:
        active = activated
    if active is None:
        active, aerr = member0(sw, "ActiveDoc", default=None)
        if aerr or active is None:
            raise RuntimeError(
                f"ActivateDoc2 produced no active document; error={errors.value}; ActiveDoc={aerr}"
            )
    active_path, perr = member0(active, "GetPathName", default="")
    if perr:
        raise RuntimeError(perr)
    if str(Path(str(active_path))).lower() != str(Path(str(expected_path))).lower():
        raise RuntimeError(
            f"Wrong document active. Expected={expected_path}; Active={active_path}"
        )
    return active, int(errors.value)


def iter_features(model):
    feat, err = member0(model, "FirstFeature", default=None)
    if err:
        raise RuntimeError(err)
    while feat is not None:
        yield feat
        feat, err = member0(feat, "GetNextFeature", default=None)
        if err:
            raise RuntimeError(err)


def feature_by_name(model, name):
    for feat in iter_features(model):
        n, _ = member0(feat, "Name", default="")
        if str(n) == name:
            return feat
    return None


def dim_full_name(dim):
    fn, e = member0(dim, "FullName", default="")
    if not e and fn:
        return str(fn)
    n, _ = member0(dim, "Name", default="")
    return str(n or "")


def feature_dimensions(feature):
    out = []
    dd, err = member0(feature, "GetFirstDisplayDimension", default=None)
    if err:
        return out
    while dd is not None:
        dim, derr = member0(dd, "GetDimension2", default=None)
        if not derr and dim is not None:
            out.append(dim)
        dd, err = call(feature, "GetNextDisplayDimension", dd, default=None)
        if err:
            break
    return out


def find_dimension(model, sketch_name, dim_name):
    for key in (f"{dim_name}@{sketch_name}",):
        try:
            dim = model.Parameter(key)
            if dim is not None:
                return dim, f"ModelDoc2.Parameter({key})"
        except Exception:
            pass
        dim, err = call(model, "Parameter", key, default=None)
        if not err and dim is not None:
            return dim, f"call(Parameter,{key})"

    feat = feature_by_name(model, sketch_name)
    if feat is None:
        raise RuntimeError(f"{sketch_name} feature not found.")
    for dim in feature_dimensions(feat):
        fn = dim_full_name(dim)
        if fn.split("@")[0] == dim_name:
            return dim, f"{sketch_name} display-dimension enumeration"
    raise RuntimeError(f"Dimension {dim_name}@{sketch_name} not found.")


def dim_value_m(dim):
    val, err = member0(dim, "SystemValue", default=None)
    if err or val is None:
        raise RuntimeError(err or f"Could not read {dim_full_name(dim)} SystemValue")
    return float(val)


def set_dim_value_m(dim, value_m):
    errors = []
    try:
        dim.SystemValue = float(value_m)
        rb = dim_value_m(dim)
        if abs(rb - value_m) <= READBACK_TOL_M:
            return "Dimension.SystemValue"
        errors.append(f"SystemValue readback={rb}")
    except Exception as exc:
        errors.append(f"SystemValue: {type(exc).__name__}: {exc}")

    try:
        rc = dim.SetSystemValue3(float(value_m), 2, None)
        rb = dim_value_m(dim)
        if abs(rb - value_m) <= READBACK_TOL_M:
            return f"SetSystemValue3 rc={rc}"
        errors.append(f"SetSystemValue3 readback={rb}, rc={rc}")
    except Exception as exc:
        errors.append(f"SetSystemValue3: {type(exc).__name__}: {exc}")

    raise RuntimeError("Could not set dimension: " + " | ".join(errors))


def one_body(model):
    bodies, err = call(model, "GetBodies2", 0, True, default=None)
    if err:
        raise RuntimeError(err)
    if bodies is None:
        bodies, err = call(model, "GetBodies2", 0, False, default=None)
        if err:
            raise RuntimeError(err)
    rows = [b for b in as_list(bodies) if b is not None]
    if len(rows) != 1:
        raise RuntimeError(f"Expected one solid body, got {len(rows)}")
    return rows[0]


def body_box_mm(body):
    box, err = member0(body, "GetBodyBox", default=None)
    if err or box is None:
        raise RuntimeError(err or "GetBodyBox returned None")
    return [1000.0 * float(x) for x in list(box)]


def body_volume_mm3(body):
    props, err = call(body, "GetMassProperties", 1.0, default=None)
    if err or props is None:
        raise RuntimeError(err or "GetMassProperties returned None")
    vals = list(props)
    return float(vals[3]) * 1e9


def feature_count(model):
    return sum(1 for _ in iter_features(model))


def cylinders(model):
    body = one_body(model)
    faces, err = member0(body, "GetFaces", default=None)
    if err:
        raise RuntimeError(err)
    out = []
    for i, face in enumerate(as_list(faces)):
        surf, se = member0(face, "GetSurface", default=None)
        if se or surf is None:
            continue
        isc, ce = member0(surf, "IsCylinder", default=False)
        if ce or not bool(isc):
            continue
        cp, cpe = member0(surf, "CylinderParams", default=None)
        if cpe or cp is None:
            continue
        p = [float(x) for x in list(cp)]
        if len(p) < 7:
            continue
        area, ae = member0(face, "GetArea", default=None)
        out.append({
            "face_index": i,
            "diameter_mm": 2000.0 * p[6],
            "area_mm2": None if ae or area is None else float(area) * 1e6,
        })
    return out


def material_name(model):
    cfg_mgr, _ = member0(model, "ConfigurationManager", default=None)
    cfg, _ = member0(cfg_mgr, "ActiveConfiguration", default=None)
    cfg_name, _ = member0(cfg, "Name", default="Default")
    raw, err = call(model, "GetMaterialPropertyName2", str(cfg_name), default=None)
    if err:
        return None, err
    if isinstance(raw, tuple):
        vals = [x for x in raw if isinstance(x, str) and x]
        return (vals[-1] if vals else None), None
    return str(raw) if raw else None, None


def save(model, path):
    rc, err = call(model, "SaveAs3", str(path), 0, 1, default=None)
    if err:
        raise RuntimeError(f"SaveAs3 failed: {err}")
    if not path.exists():
        raise RuntimeError(f"SaveAs3 did not create {path}; rc={rc!r}")


def main():
    pythoncom.CoInitialize()

    if not SOURCE.exists():
        raise RuntimeError(f"Production P008 not found: {SOURCE}")

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    revision, _ = member0(sw, "RevisionNumber", default="")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = OUTDIR / f"{BASE}_{stamp}.SLDPRT"
    step = OUTDIR / f"{BASE}_{stamp}.STEP"
    OUTDIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SOURCE, candidate)
    model, open_errors, open_warnings = open_doc6(sw, candidate)
    model, activate_error = activate_model(sw, model, candidate)

    print("=" * 78)
    print("K01 Gate04A - P008 MAGNET POCKET Ø8.10 -> Ø8.20 NATIVE EDIT")
    print("=" * 78)
    print(f"[INFO] SOLIDWORKS revision: {revision}")
    print(f"[PASS] Candidate copied/opened; OpenDoc6 errors={open_errors}, warnings={open_warnings}")
    print(f"[PASS] Candidate activated; ActivateDoc2 error={activate_error}")
    print(f"[INFO] Candidate: {candidate}")

    before_body = one_body(model)
    before_box = body_box_mm(before_body)
    before_volume = body_volume_mm3(before_body)
    before_feature_count = feature_count(model)
    before_cylinders = cylinders(model)
    before_material, material_err = material_name(model)

    d1, how_d1 = find_dimension(model, SKETCH_NAME, "D1")
    d4, how_d4 = find_dimension(model, SKETCH_NAME, "D4")
    d5, how_d5 = find_dimension(model, SKETCH_NAME, "D5")
    d8, how_d8 = find_dimension(model, SKETCH_NAME, "D8")

    old_r = dim_value_m(d1)
    od_r = dim_value_m(d4)
    pocket_depth = dim_value_m(d5)
    chamfer = dim_value_m(d8)

    print(f"[INFO] D1@Sketch1 pocket radius: {old_r*1000:.6f} mm via {how_d1}")
    print(f"[INFO] D4@Sketch1 outer radius:  {od_r*1000:.6f} mm via {how_d4}")
    print(f"[INFO] D5@Sketch1 pocket depth:  {pocket_depth*1000:.6f} mm via {how_d5}")
    print(f"[INFO] D8@Sketch1 entry chamfer: {chamfer*1000:.6f} mm via {how_d8}")

    if abs(old_r - EXPECTED_OLD_RADIUS_M) > READBACK_TOL_M:
        raise RuntimeError(
            f"Refusing edit: current pocket radius is {old_r*1000:.6f} mm, expected 4.050000 mm."
        )
    if abs(od_r - EXPECTED_OD_RADIUS_M) > READBACK_TOL_M:
        raise RuntimeError("Refusing edit: P008 OD radius no longer matches Ø8.80 baseline.")
    if abs(pocket_depth - EXPECTED_POCKET_DEPTH_M) > READBACK_TOL_M:
        raise RuntimeError("Refusing edit: pocket depth no longer matches 8.20 mm baseline.")
    if abs(chamfer - EXPECTED_ENTRY_CHAMFER_M) > READBACK_TOL_M:
        raise RuntimeError("Refusing edit: entry chamfer no longer matches 0.10 mm baseline.")

    set_method = set_dim_value_m(d1, TARGET_RADIUS_M)
    print(f"[PASS] Pocket radius changed 4.050 -> 4.100 mm using {set_method}")

    rebuild, rebuild_err = call(model, "ForceRebuild3", False, default=None)
    if rebuild_err:
        raise RuntimeError(f"ForceRebuild3 failed: {rebuild_err}")

    d1_after, _ = find_dimension(model, SKETCH_NAME, "D1")
    d4_after, _ = find_dimension(model, SKETCH_NAME, "D4")
    d5_after, _ = find_dimension(model, SKETCH_NAME, "D5")
    d8_after, _ = find_dimension(model, SKETCH_NAME, "D8")

    new_r = dim_value_m(d1_after)
    od_r_after = dim_value_m(d4_after)
    depth_after = dim_value_m(d5_after)
    chamfer_after = dim_value_m(d8_after)

    if abs(new_r - TARGET_RADIUS_M) > READBACK_TOL_M:
        raise RuntimeError(f"Pocket radius readback FAIL: {new_r*1000:.6f} mm")
    if abs(od_r_after - EXPECTED_OD_RADIUS_M) > READBACK_TOL_M:
        raise RuntimeError("P008 OD changed unexpectedly.")
    if abs(depth_after - EXPECTED_POCKET_DEPTH_M) > READBACK_TOL_M:
        raise RuntimeError("Pocket depth changed unexpectedly.")
    if abs(chamfer_after - EXPECTED_ENTRY_CHAMFER_M) > READBACK_TOL_M:
        raise RuntimeError("Entry chamfer changed unexpectedly.")

    after_body = one_body(model)
    after_box = body_box_mm(after_body)
    after_volume = body_volume_mm3(after_body)
    after_feature_count = feature_count(model)
    after_cylinders = cylinders(model)
    after_material, material_err_after = material_name(model)

    if max(abs(after_box[i] - before_box[i]) for i in range(6)) > BBOX_TOL_MM:
        raise RuntimeError(f"External body envelope changed: before={before_box}, after={after_box}")

    if after_feature_count != before_feature_count:
        raise RuntimeError(
            f"Feature count changed unexpectedly: {before_feature_count}->{after_feature_count}"
        )

    has_820 = any(abs(c["diameter_mm"] - 8.20) <= CYL_TOL_MM for c in after_cylinders)
    has_810 = any(abs(c["diameter_mm"] - 8.10) <= CYL_TOL_MM for c in after_cylinders)

    if not has_820:
        raise RuntimeError(f"BREP validation FAIL: no Ø8.20 cylinder found: {after_cylinders}")
    if has_810:
        raise RuntimeError(f"BREP validation FAIL: old Ø8.10 cylinder still present: {after_cylinders}")

    hole_min = 8.200
    hole_max = 8.236
    magnet_nom = 8.000
    magnet_max = 8.100
    od_nom = 8.800

    nominal_diam_clearance = hole_min - magnet_nom
    worst_diam_clearance = hole_min - magnet_max
    min_radial_wall_at_h9_max = (od_nom - hole_max) / 2.0

    save(model, candidate)
    save(model, step)

    report = {
        "schema": "k01_p008_gate04a_pocket820_native_edit_v1",
        "status": "PASS",
        "solidworks_revision": str(revision),
        "source_production_p008": str(SOURCE),
        "production_p008_modified": False,
        "native_candidate": str(candidate),
        "step_candidate": str(step),
        "edit": {
            "dimension": "D1@Sketch1",
            "old_radius_mm": old_r * 1000.0,
            "new_radius_mm": new_r * 1000.0,
            "old_pocket_diameter_mm": old_r * 2000.0,
            "new_pocket_diameter_mm": new_r * 2000.0,
            "set_method": set_method,
        },
        "preserved": {
            "OD_mm": od_r_after * 2000.0,
            "pocket_depth_mm": depth_after * 1000.0,
            "entry_chamfer_mm": chamfer_after * 1000.0,
            "body_box_before_mm": before_box,
            "body_box_after_mm": after_box,
            "feature_count_before": before_feature_count,
            "feature_count_after": after_feature_count,
            "material_before": before_material,
            "material_after": after_material,
        },
        "volume": {
            "before_mm3": before_volume,
            "after_mm3": after_volume,
            "removed_mm3": before_volume - after_volume,
        },
        "brep": {
            "before_cylinders": before_cylinders,
            "after_cylinders": after_cylinders,
            "has_D8p20": has_820,
            "has_old_D8p10": has_810,
        },
        "tolerance_design": {
            "hole_callout": "Ø8.20 H9",
            "hole_min_mm": hole_min,
            "hole_max_mm": hole_max,
            "B001_nominal_D_mm": magnet_nom,
            "B001_vendor_max_D_mm": magnet_max,
            "nominal_diametral_clearance_mm": nominal_diam_clearance,
            "worst_case_diametral_clearance_mm": worst_diam_clearance,
            "worst_case_radial_clearance_mm": worst_diam_clearance / 2.0,
            "minimum_radial_wall_at_hole_max_mm": min_radial_wall_at_h9_max,
        },
        "release_status": "CANDIDATE_NOT_RELEASED",
        "next": (
            "Verify P008 candidate in K01-A-001 assembly; then update master/drawing "
            "from Ø8.10 to Ø8.20 H9 and keep B001 lot D/L incoming inspection."
        ),
    }

    REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 78)
    print("K01 Gate04A RESULT")
    print("=" * 78)
    print("[PASS] P008 native edit complete.")
    print("[PASS] Magnet pocket: Ø8.10 -> Ø8.20 nominal.")
    print("[PASS] Pocket depth retained: 8.20 mm.")
    print("[PASS] Entry chamfer retained: 0.10 mm.")
    print("[PASS] External OD/envelope unchanged.")
    print(f"[PASS] Worst-case diametral clearance vs B001 Dmax: {worst_diam_clearance:.3f} mm")
    print(f"[PASS] Minimum radial wall at Ø8.236 H9 max: {min_radial_wall_at_h9_max:.3f} mm")
    print("Native:", candidate)
    print("STEP:  ", step)
    print("Report:", REPORT)
    print("Production P008 was NOT modified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: K01 Gate04A P008 native pocket edit")
        traceback.print_exc()
        sys.exit(1)
