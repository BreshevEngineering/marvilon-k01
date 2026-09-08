from __future__ import annotations

import json
import math
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from sw_com import member0, call, as_list


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "cad" / "current" / "K01_P007_GATE03H_BUILD.json"
REPORT.parent.mkdir(parents=True, exist_ok=True)

SOURCE = Path(r"D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT")
OUTDIR = Path(r"D:\Marvilon\K01\cad\candidates")
BASE = "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE"

TRIM_MM = 5.0
EXPECTED_FINAL_LENGTH_MM = 35.0
EXPECTED_FINAL_VOLUME_MM3 = 583.4408796614285
VOLUME_TOL_MM3 = 0.10
BBOX_TOL_MM = 0.02


def m(v_mm):
    return float(v_mm) / 1000.0


def open_doc6(sw, path):
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)

    loaded = sw.OpenDoc6(
        str(path),
        1,      # swDocPART
        1,      # swOpenDocOptions_Silent
        "",
        errors,
        warnings,
    )

    if isinstance(loaded, tuple):
        model = next(
            (x for x in loaded if x is not None and hasattr(x, "_oleobj_")),
            None,
        )
    else:
        model = loaded

    if model is None:
        raise RuntimeError(
            f"OpenDoc6 returned no ModelDoc2; "
            f"errors={errors.value}, warnings={warnings.value}"
        )

    return model, int(errors.value), int(warnings.value)


def activate_model(sw, model, expected_path):
    title, terr = member0(model, "GetTitle", default="")
    if terr or not title:
        raise RuntimeError(terr or "Could not read candidate title.")

    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)

    activated = sw.ActivateDoc2(str(title), False, errors)

    if isinstance(activated, tuple):
        active = next(
            (x for x in activated if x is not None and hasattr(x, "_oleobj_")),
            None,
        )
    else:
        active = activated

    if active is None:
        active, aerr = member0(sw, "ActiveDoc", default=None)
        if aerr or active is None:
            raise RuntimeError(
                f"ActivateDoc2 produced no active document; "
                f"error={errors.value}; ActiveDoc={aerr}"
            )

    active_path, perr = member0(active, "GetPathName", default="")
    if perr:
        raise RuntimeError(perr)

    if str(Path(str(active_path))).lower() != str(Path(str(expected_path))).lower():
        raise RuntimeError(
            f"Wrong document active. Expected={expected_path}; Active={active_path}"
        )

    return active, int(errors.value)


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
    return float(vals[3]) * 1.0e9


def axial_planes(model):
    body = one_body(model)
    faces, err = member0(body, "GetFaces", default=None)
    if err:
        raise RuntimeError(err)

    rows = []
    for i, face in enumerate(as_list(faces)):
        surf, e = member0(face, "GetSurface", default=None)
        if e or surf is None:
            continue

        is_plane, e = member0(surf, "IsPlane", default=False)
        if e or not bool(is_plane):
            continue

        pp, e = member0(surf, "PlaneParams", default=None)
        if e or pp is None:
            continue

        p = [float(x) for x in list(pp)]
        if len(p) < 6:
            continue

        nx, ny, nz = p[0], p[1], p[2]
        if abs(abs(nx) - 1.0) > 1e-7 or abs(ny) > 1e-7 or abs(nz) > 1e-7:
            continue

        area, ae = member0(face, "GetArea", default=None)
        rows.append({
            "face_index": i,
            "x_local_m": p[3],
            "x_local_mm": 1000.0 * p[3],
            "area_mm2": None if ae or area is None else float(area) * 1e6,
        })

    # unique stations
    grouped = {}
    for r in rows:
        key = round(r["x_local_mm"], 6)
        old = grouped.get(key)
        if old is None or (r["area_mm2"] or -1) > (old["area_mm2"] or -1):
            grouped[key] = r

    return sorted(grouped.values(), key=lambda r: r["x_local_m"])


def feature_count(model):
    feat, err = member0(model, "FirstFeature", default=None)
    if err:
        raise RuntimeError(err)
    count = 0
    names = []
    while feat is not None:
        count += 1
        nm, _ = member0(feat, "Name", default="")
        typ, _ = member0(feat, "GetTypeName2", default="")
        names.append({"name": str(nm), "type": str(typ)})
        feat, err = member0(feat, "GetNextFeature", default=None)
        if err:
            raise RuntimeError(err)
    return count, names


def active_sketch(sm):
    return member0(sm, "ActiveSketch", default=None)


def close_sketch(sm):
    _, err = call(sm, "InsertSketch", True, default=None)
    if err:
        raise RuntimeError(f"Close sketch failed: {err}")
    sk, e = active_sketch(sm)
    if e:
        raise RuntimeError(e)
    if sk is not None:
        raise RuntimeError("Sketch is still active after close.")


def latest_profile(model):
    feat, err = member0(model, "FirstFeature", default=None)
    if err:
        raise RuntimeError(err)

    rows = []
    while feat is not None:
        typ, _ = member0(feat, "GetTypeName2", default="")
        if str(typ) == "ProfileFeature":
            rows.append(feat)
        feat, err = member0(feat, "GetNextFeature", default=None)
        if err:
            raise RuntimeError(err)

    return rows[-1] if rows else None


def find_feature(model, name):
    feat, err = member0(model, "FirstFeature", default=None)
    if err:
        raise RuntimeError(err)
    while feat is not None:
        nm, _ = member0(feat, "Name", default="")
        if str(nm) == name:
            return feat
        feat, err = member0(feat, "GetNextFeature", default=None)
        if err:
            raise RuntimeError(err)
    return None


def select2(obj, append=False, mark=0, label="object"):
    ok, err = call(obj, "Select2", bool(append), int(mark), default=False)
    if err or not ok:
        raise RuntimeError(f"{label}.Select2 failed: {err or ok!r}")


def save(model, path):
    rc, err = call(model, "SaveAs3", str(path), 0, 1, default=None)
    if err:
        raise RuntimeError(f"SaveAs3 failed: {err}")
    if not path.exists():
        raise RuntimeError(f"SaveAs3 did not create {path}; rc={rc!r}")


def main():
    pythoncom.CoInitialize()

    if not SOURCE.exists():
        raise RuntimeError(f"Production P007 not found: {SOURCE}")

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    revision, _ = member0(sw, "RevisionNumber", default="")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = OUTDIR / f"{BASE}_{stamp}.SLDPRT"
    step = OUTDIR / f"{BASE}_{stamp}.STEP"
    OUTDIR.mkdir(parents=True, exist_ok=True)

    # Preserve existing native history by copying the actual production file.
    shutil.copy2(SOURCE, candidate)

    model, open_errors, open_warnings = open_doc6(sw, candidate)
    model, activate_error = activate_model(sw, model, candidate)

    print(f"[INFO] SOLIDWORKS revision: {revision}")
    print(
        f"[PASS] Native production P007 copied/opened; "
        f"OpenDoc6 errors={open_errors}, warnings={open_warnings}"
    )
    print(f"[PASS] Candidate activated; ActivateDoc2 error={activate_error}")
    print(f"[INFO] Candidate: {candidate}")

    before_body = one_body(model)
    before_box = body_box_mm(before_body)
    before_volume = body_volume_mm3(before_body)
    before_feature_count, before_features = feature_count(model)

    planes = axial_planes(model)
    if len(planes) != 5:
        raise RuntimeError(
            f"Expected 5 unique production P007 axial stations; got {len(planes)}: {planes}"
        )

    x_front = planes[0]["x_local_mm"]
    x_trim_end = x_front + TRIM_MM
    x_rear = planes[-1]["x_local_mm"]

    print(f"[INFO] Production P007 front station: {x_front:.9f} mm")
    print(f"[INFO] Trim interval:                {x_front:.9f} .. {x_trim_end:.9f} mm")
    print(f"[INFO] Production rear station:      {x_rear:.9f} mm")

    # Create a 360-degree revolved CUT that removes the complete first 5 mm slab.
    # This preserves the original Sketch1/Revolve1 feature and adds only one
    # new native cut feature after it.
    front_plane = find_feature(model, "Front Plane")
    if front_plane is None:
        raise RuntimeError("Front Plane not found.")

    call(model, "ClearSelection2", True, default=None)
    select2(front_plane, False, 0, "Front Plane")

    sm, err = member0(model, "SketchManager", default=None)
    if err or sm is None:
        raise RuntimeError(err or "SketchManager unavailable.")
    fm, err = member0(model, "FeatureManager", default=None)
    if err or fm is None:
        raise RuntimeError(err or "FeatureManager unavailable.")

    _, err = call(sm, "InsertSketch", True, default=None)
    if err:
        raise RuntimeError(f"InsertSketch failed: {err}")

    sk, serr = active_sketch(sm)
    if serr or sk is None:
        raise RuntimeError(serr or "ActiveSketch is None.")

    old_add = None
    old_disp = None
    try:
        old_add = sm.AddToDB
        sm.AddToDB = True
    except Exception:
        pass
    try:
        old_disp = sm.DisplayWhenAdded
        sm.DisplayWhenAdded = False
    except Exception:
        pass

    axis, err = call(
        sm, "CreateCenterLine",
        m(x_front - 1.0), 0.0, 0.0,
        m(x_trim_end + 1.0), 0.0, 0.0,
        default=None,
    )
    if err or axis is None:
        raise RuntimeError(err or "CreateCenterLine failed.")
    try:
        axis.ConstructionGeometry = True
    except Exception:
        pass

    # Cut rectangle from axis to R=9 mm; larger than existing OD16 (R8).
    profile = [
        (x_front, 0.0),
        (x_trim_end, 0.0),
        (x_trim_end, 9.0),
        (x_front, 9.0),
    ]

    for i, (p1, p2) in enumerate(zip(profile, profile[1:] + profile[:1]), start=1):
        seg, err = call(
            sm, "CreateLine",
            m(p1[0]), m(p1[1]), 0.0,
            m(p2[0]), m(p2[1]), 0.0,
            default=None,
        )
        if err or seg is None:
            raise RuntimeError(
                f"CreateLine {i} failed {p1}->{p2}: {err or 'returned None'}"
            )

    if old_disp is not None:
        try: sm.DisplayWhenAdded = old_disp
        except Exception: pass
    if old_add is not None:
        try: sm.AddToDB = old_add
        except Exception: pass

    sketch_feature = None
    try:
        sketch_feature = sk.GetFeature()
    except Exception:
        pass

    close_sketch(sm)

    if sketch_feature is None:
        sketch_feature = latest_profile(model)
    if sketch_feature is None:
        raise RuntimeError("Could not resolve trim sketch feature.")

    try:
        sketch_feature.Name = "K01_SKETCH_P007_TRIM_FRONT_5"
    except Exception:
        pass

    call(model, "ClearSelection2", True, default=None)
    select2(sketch_feature, False, 0, "trim sketch")
    select2(axis, True, 16, "trim revolve axis")

    # FeatureRevolve2 with IsCut=True.
    cut, err = call(
        fm, "FeatureRevolve2",
        True,      # SingleDir
        True,      # IsSolid  <-- required for a solid cut-revolve
        False,     # IsThin
        True,      # IsCut
        False,
        False,
        0, 0,
        2.0 * math.pi, 0.0,
        False, False,
        0.01, 0.01,
        0,
        0.0, 0.0,
        True, True, True,
        default=None,
    )

    if err or cut is None:
        raise RuntimeError(
            "Revolved-cut creation failed. "
            f"FeatureRevolve2: {err or 'returned None'}"
        )

    try:
        cut.Name = "K01_F_TRIM_FRONT_SLEEVE_5MM"
    except Exception:
        pass

    call(model, "ForceRebuild3", False, default=None)

    after_body = one_body(model)
    after_box = body_box_mm(after_body)
    after_volume = body_volume_mm3(after_body)
    after_feature_count, after_features = feature_count(model)

    removed_volume = before_volume - after_volume
    expected_removed_volume = 224.58460482350034
    if abs(removed_volume - expected_removed_volume) > VOLUME_TOL_MM3:
        raise RuntimeError(
            "Trim semantic volume FAIL: "
            f"removed={removed_volume:.9f} mm^3, "
            f"expected={expected_removed_volume:.9f} mm^3"
        )

    print(
        f"[PASS] Removed sleeve volume: {removed_volume:.9f} mm^3 "
        f"(expected {expected_removed_volume:.9f})"
    )

    final_length = after_box[3] - after_box[0]

    if abs(final_length - EXPECTED_FINAL_LENGTH_MM) > BBOX_TOL_MM:
        raise RuntimeError(
            f"Final P007 length FAIL: {final_length:.9f} mm, "
            f"expected {EXPECTED_FINAL_LENGTH_MM:.9f}"
        )

    if abs(after_volume - EXPECTED_FINAL_VOLUME_MM3) > VOLUME_TOL_MM3:
        raise RuntimeError(
            f"Final volume FAIL: {after_volume:.9f} mm^3, "
            f"expected {EXPECTED_FINAL_VOLUME_MM3:.9f}"
        )

    # The new front station must be exactly old front + 5 mm.
    after_planes = axial_planes(model)
    new_front = min(r["x_local_mm"] for r in after_planes)
    if abs(new_front - x_trim_end) > BBOX_TOL_MM:
        raise RuntimeError(
            f"New front station FAIL: {new_front:.9f} mm, expected {x_trim_end:.9f}"
        )

    # Rear station must not move.
    new_rear = max(r["x_local_mm"] for r in after_planes)
    if abs(new_rear - x_rear) > BBOX_TOL_MM:
        raise RuntimeError(
            f"Rear station moved: {new_rear:.9f} vs {x_rear:.9f} mm"
        )

    if after_feature_count <= before_feature_count:
        raise RuntimeError(
            f"Native history audit FAIL: feature count did not increase "
            f"({before_feature_count}->{after_feature_count})"
        )

    save(model, candidate)
    save(model, step)

    report = {
        "schema": "k01_p007_gate03h_native_trim_build_v1",
        "status": "PASS",
        "solidworks_revision": str(revision),
        "source_production_p007": str(SOURCE),
        "production_p007_modified": False,
        "native_candidate": str(candidate),
        "step_candidate": str(step),
        "trim_mm": TRIM_MM,
        "before": {
            "body_box_mm": before_box,
            "volume_mm3": before_volume,
            "feature_count": before_feature_count,
            "features": before_features,
            "front_station_local_mm": x_front,
            "rear_station_local_mm": x_rear,
        },
        "after": {
            "body_box_mm": after_box,
            "volume_mm3": after_volume,
            "feature_count": after_feature_count,
            "features": after_features,
            "front_station_local_mm": new_front,
            "rear_station_local_mm": new_rear,
            "final_length_mm": final_length,
        },
        "geometry_equivalence_target": {
            "reference_gate03e_v5_volume_mm3": EXPECTED_FINAL_VOLUME_MM3,
            "reference_gate03e_v5_length_mm": EXPECTED_FINAL_LENGTH_MM,
        },
        "release_status": "CANDIDATE_NOT_RELEASED",
    }

    REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 76)
    print("K01 Gate03H - NATIVE-HISTORY P007 TRIM CANDIDATE")
    print("=" * 76)
    print("[PASS] Production P007 native history preserved.")
    print("[PASS] Only front 5.000 mm sleeve removed by one new native cut feature.")
    print(f"[PASS] Final length: {final_length:.9f} mm")
    print(f"[PASS] Final volume: {after_volume:.9f} mm^3")
    print(f"[PASS] Rear station unchanged: {new_rear:.9f} mm")
    print(f"[PASS] Feature count: {before_feature_count} -> {after_feature_count}")
    print("Native:", candidate)
    print("STEP:  ", step)
    print("Report:", REPORT)
    print("Production P007 was NOT modified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: K01 Gate03H native P007 trim builder")
        traceback.print_exc()
        sys.exit(1)
