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
REPORT = ROOT / "reports" / "cad" / "current" / "K01_P003_GATE03G_BUILD.json"
REPORT.parent.mkdir(parents=True, exist_ok=True)

SOURCE = Path(r"D:\Marvilon\K01\cad\parts\K01-P-003_Cartridge_Body.SLDPRT")
OUTDIR = Path(r"D:\Marvilon\K01\cad\candidates")
BASE = "K01-P-003_Cartridge_Body_GATE03G_CANDIDATE"

ADD_OD_MM = 16.0
BASE_OD_MM = 14.0
COLLAR_L_MM = 5.0
EXPECTED_DELTA_VOLUME_MM3 = math.pi * ((ADD_OD_MM/2)**2 - (BASE_OD_MM/2)**2) * COLLAR_L_MM
VOL_TOL_MM3 = 0.05


def m(v_mm):
    return float(v_mm) / 1000.0


def open_doc6(sw, path):
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    loaded = sw.OpenDoc6(
        str(path),
        1,  # swDocPART
        1,  # swOpenDocOptions_Silent
        "",
        errors,
        warnings,
    )
    if isinstance(loaded, tuple):
        model = next((x for x in loaded if x is not None and hasattr(x, "_oleobj_")), None)
    else:
        model = loaded
    if model is None:
        raise RuntimeError(
            f"OpenDoc6 returned no ModelDoc2; errors={errors.value}, warnings={warnings.value}"
        )
    return model, int(errors.value), int(warnings.value)


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


def mass_volume_mm3(body):
    props, err = call(body, "GetMassProperties", 1.0, default=None)
    if err or props is None:
        raise RuntimeError(err or "GetMassProperties returned None")
    vals = list(props)
    return float(vals[3]) * 1e9


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
    return sorted(rows, key=lambda r: r["x_local_m"])


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


def select2(obj, append=False, mark=0, label="object"):
    ok, err = call(obj, "Select2", bool(append), int(mark), default=False)
    if err or not ok:
        raise RuntimeError(f"{label}.Select2 failed: {err or ok!r}")


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


def cylinders(model):
    body = one_body(model)
    faces, err = member0(body, "GetFaces", default=None)
    if err:
        raise RuntimeError(err)
    out = []
    for i, f in enumerate(as_list(faces)):
        s, se = member0(f, "GetSurface", default=None)
        if se or s is None:
            continue
        isc, ce = member0(s, "IsCylinder", default=False)
        if ce or not bool(isc):
            continue
        cp, cpe = member0(s, "CylinderParams", default=None)
        if cpe or cp is None:
            continue
        p = [float(x) for x in list(cp)]
        if len(p) < 7:
            continue
        area, ae = member0(f, "GetArea", default=None)
        out.append({
            "face_index": i,
            "diameter_mm": 2000.0 * p[6],
            "area_mm2": None if ae or area is None else float(area) * 1e6,
        })
    return out


def save(model, path):
    rc, err = call(model, "SaveAs3", str(path), 0, 1, default=None)
    if err:
        raise RuntimeError(f"SaveAs3 failed: {err}")
    if not path.exists():
        raise RuntimeError(f"SaveAs3 did not create {path}; rc={rc!r}")


def main():
    pythoncom.CoInitialize()

    if not SOURCE.exists():
        raise RuntimeError(f"Production P003 source not found: {SOURCE}")

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    revision, _ = member0(sw, "RevisionNumber", default="")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = OUTDIR / f"{BASE}_{stamp}.SLDPRT"
    step = OUTDIR / f"{BASE}_{stamp}.STEP"
    OUTDIR.mkdir(parents=True, exist_ok=True)

    # Filesystem copy preserves native feature history and persistent references.
    shutil.copy2(SOURCE, candidate)

    model, open_errors, open_warnings = open_doc6(sw, candidate)
    print(f"[INFO] SOLIDWORKS revision: {revision}")
    print(f"[PASS] Native P003 copied and opened; OpenDoc6 errors={open_errors}, warnings={open_warnings}")
    print(f"[INFO] Candidate: {candidate}")

    before_body = one_body(model)
    before_volume = mass_volume_mm3(before_body)
    planes = axial_planes(model)
    if not planes:
        raise RuntimeError("Could not resolve P003 axial planes.")
    rear = max(planes, key=lambda r: r["x_local_m"])
    rear_mm = rear["x_local_mm"]
    collar_start_mm = rear_mm - COLLAR_L_MM

    print(f"[INFO] P003 rear local station: {rear_mm:.9f} mm")
    print(f"[INFO] Collar add region:      {collar_start_mm:.9f} .. {rear_mm:.9f} mm")

    # Front Plane selection on the copied native part.
    front = find_feature(model, "Front Plane")
    if front is None:
        raise RuntimeError("Front Plane feature not found.")

    call(model, "ClearSelection2", True, default=None)
    select2(front, False, 0, "Front Plane")

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
        raise RuntimeError(serr or "ActiveSketch is None after selecting Front Plane.")

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
        m(collar_start_mm - 1.0), 0.0, 0.0,
        m(rear_mm + 1.0), 0.0, 0.0,
        default=None,
    )
    if err or axis is None:
        raise RuntimeError(err or "CreateCenterLine failed.")
    try:
        axis.ConstructionGeometry = True
    except Exception:
        pass

    profile = [
        (collar_start_mm, BASE_OD_MM/2),
        (rear_mm, BASE_OD_MM/2),
        (rear_mm, ADD_OD_MM/2),
        (collar_start_mm, ADD_OD_MM/2),
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
        raise RuntimeError("Could not resolve new collar sketch feature.")

    try:
        sketch_feature.Name = "K01_SKETCH_P003_REAR_COLLAR_OD16_L5"
    except Exception:
        pass

    call(model, "ClearSelection2", True, default=None)
    select2(sketch_feature, False, 0, "collar sketch")
    select2(axis, True, 16, "collar revolve axis")

    feature, err = call(
        fm, "FeatureRevolve2",
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
    if err or feature is None:
        raise RuntimeError(err or "FeatureRevolve2 returned None.")

    try:
        feature.Name = "K01_F_REAR_COLLAR_OD16_L5"
    except Exception:
        pass

    call(model, "ForceRebuild3", False, default=None)

    after_body = one_body(model)
    after_volume = mass_volume_mm3(after_body)
    delta_volume = after_volume - before_volume

    if abs(delta_volume - EXPECTED_DELTA_VOLUME_MM3) > VOL_TOL_MM3:
        raise RuntimeError(
            "Integrated collar volume check failed: "
            f"delta={delta_volume:.9f}, expected={EXPECTED_DELTA_VOLUME_MM3:.9f} mm^3"
        )

    cyls = cylinders(model)
    od16 = [
        r for r in cyls
        if abs(r["diameter_mm"] - 16.0) <= 0.005
        and r["area_mm2"] is not None
    ]
    expected_area = math.pi * 16.0 * 5.0
    if not any(abs(r["area_mm2"] - expected_area) <= 0.2 for r in od16):
        raise RuntimeError(
            f"Could not verify expected OD16 x 5 mm cylindrical face. OD16 rows={od16}"
        )

    save(model, candidate)
    save(model, step)

    report = {
        "schema": "k01_p003_gate03g_build_v1",
        "status": "PASS",
        "solidworks_revision": str(revision),
        "source_production_p003": str(SOURCE),
        "production_p003_modified": False,
        "native_candidate": str(candidate),
        "step_candidate": str(step),
        "rear_local_station_mm": rear_mm,
        "collar_start_local_station_mm": collar_start_mm,
        "controlled_geometry_mm": {
            "collar_length": 5.0,
            "old_OD": 14.0,
            "new_OD": 16.0,
            "radial_added_thickness": 1.0,
        },
        "volume_before_mm3": before_volume,
        "volume_after_mm3": after_volume,
        "volume_delta_mm3": delta_volume,
        "expected_volume_delta_mm3": EXPECTED_DELTA_VOLUME_MM3,
        "release_status": "CANDIDATE_NOT_RELEASED",
    }
    REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("="*72)
    print("K01 Gate03G - NATIVE P003 CANDIDATE")
    print("="*72)
    print("[PASS] Existing native P003 history preserved and rear collar integrated.")
    print(f"[PASS] Added volume: {delta_volume:.9f} mm^3")
    print("Native:", candidate)
    print("STEP:  ", step)
    print("Report:", REPORT)
    print("Production P003 was NOT modified.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: K01 Gate03G native P003 candidate builder")
        traceback.print_exc()
        sys.exit(1)
