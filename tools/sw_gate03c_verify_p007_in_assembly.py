from __future__ import annotations

import json
import math
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client

from sw_com import member0, call, as_list


ROOT = Path(__file__).resolve().parents[1]
BUILD_REPORT = ROOT / "reports" / "cad" / "current" / "K01_P007_GATE03B_BUILD.json"
OUT_REPORT = ROOT / "reports" / "cad" / "current" / "K01_GATE03C_ASSEMBLY_VERIFY.json"
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

VERIFY_DIR = Path(r"D:\Marvilon\K01\cad\candidates")
VERIFY_BASE = "K01-A-001_GATE03C_P007_VERIFY"

PRODUCTION_ASSEMBLY_NAME = "K01-A-001_Calibration_Module.SLDASM"
P003_SUFFIX = "K01-P-003_Cartridge_Body.SLDPRT"
P007_SUFFIX = "K01-P-007_Hermetic_Magnetic_Can.SLDPRT"

TOL_STATION_MM = 0.002
TOL_SECTION_AREA_MM2 = 0.005
TOL_AXIS = 1.0e-8
TOL_TRANSFORM = 1.0e-10


def v3(a):
    return [float(a[0]), float(a[1]), float(a[2])]


def add(a, b):
    return [a[i] + b[i] for i in range(3)]


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def scale(v, s):
    return [float(s) * x for x in v]


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def norm(v):
    return math.sqrt(dot(v, v))


def unit(v):
    n = norm(v)
    if n <= 0:
        raise RuntimeError("zero-length vector")
    return [x / n for x in v]


def distance_mm(a_m, b_m):
    return 1000.0 * norm(sub(a_m, b_m))


def transform_array(comp):
    tr, err = member0(comp, "Transform2", default=None)
    if err or tr is None:
        raise RuntimeError(err or "Component.Transform2 returned None")
    data, err = member0(tr, "ArrayData", default=None)
    if err or data is None:
        raise RuntimeError(err or "Transform2.ArrayData returned None")
    vals = [float(x) for x in list(data)]
    if len(vals) != 16:
        raise RuntimeError(f"Expected 16 transform values, got {len(vals)}")
    return vals


def transform_point(T, p):
    """
    SOLIDWORKS MathTransform ArrayData:
    first 9 = local axes rows, [9:12] = translation.
    A local point is translated by the weighted local axis rows.
    """
    ex = T[0:3]
    ey = T[3:6]
    ez = T[6:9]
    t = T[9:12]
    return add(t, add(scale(ex, p[0]), add(scale(ey, p[1]), scale(ez, p[2]))))


def axis_x(T):
    return unit(T[0:3])


def component_path(comp):
    p, err = member0(comp, "GetPathName", default="")
    if err:
        raise RuntimeError(err)
    return str(p or "")


def component_name(comp):
    n, _ = member0(comp, "Name2", default="")
    return str(n or "")


def find_components(assembly):
    comps, err = call(assembly, "GetComponents", False, default=None)
    if err:
        raise RuntimeError(f"GetComponents(False) failed: {err}")
    return as_list(comps)


def find_by_suffix(comps, suffix):
    matches = []
    low_suffix = suffix.lower()
    for c in comps:
        p = component_path(c)
        if p.lower().endswith(low_suffix):
            matches.append(c)
    return matches


def solid_body(model):
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


def model_of_component(comp):
    m, err = member0(comp, "GetModelDoc2", default=None)
    if err or m is None:
        raise RuntimeError(err or f"{component_name(comp)} is unresolved")
    return m


def axial_plane_rows(comp):
    """
    Returns local axial plane stations for a rotational part.
    PlaneParams in the current SW2018 API session are:
    normal xyz + a point xyz.
    """
    model = model_of_component(comp)
    body = solid_body(model)

    faces, err = member0(body, "GetFaces", default=None)
    if err:
        raise RuntimeError(err)

    rows = []
    for i, f in enumerate(as_list(faces)):
        surf, e = member0(f, "GetSurface", default=None)
        if e or surf is None:
            continue
        is_plane, e = member0(surf, "IsPlane", default=False)
        if e or not bool(is_plane):
            continue
        params, e = member0(surf, "PlaneParams", default=None)
        if e or params is None:
            continue
        p = [float(x) for x in list(params)]
        if len(p) < 6:
            continue
        n = unit(p[0:3])
        # Axial face in part-local coordinates.
        if abs(abs(n[0]) - 1.0) > 1.0e-7 or abs(n[1]) > 1.0e-7 or abs(n[2]) > 1.0e-7:
            continue

        area, ae = member0(f, "GetArea", default=None)
        area_mm2 = None
        if not ae and area is not None:
            area_mm2 = float(area) * 1.0e6

        rows.append({
            "face_index": i,
            "x_local_m": float(p[3]),
            "x_local_mm": float(p[3]) * 1000.0,
            "normal": n,
            "area_mm2": area_mm2,
        })

    # Deduplicate by local station; preserve largest face area at station.
    grouped = {}
    for r in rows:
        key = round(r["x_local_mm"], 6)
        old = grouped.get(key)
        if old is None or (r["area_mm2"] or -1) > (old["area_mm2"] or -1):
            grouped[key] = r
    return sorted(grouped.values(), key=lambda r: r["x_local_mm"])


def body_bbox_local_mm(comp):
    body = solid_body(model_of_component(comp))
    box, err = member0(body, "GetBodyBox", default=None)
    if err or box is None:
        raise RuntimeError(err or "GetBodyBox returned None")
    return [float(x) * 1000.0 for x in list(box)]


def save_as(model, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    rc, err = call(model, "SaveAs3", str(target), 0, 1, default=None)
    if err:
        raise RuntimeError(f"SaveAs3 failed: {err}")
    if not target.exists():
        raise RuntimeError(f"SaveAs3 did not create {target}; rc={rc!r}")
    return rc


def retarget_existing_component_transform(comp, array16):
    # SW2018 + late-bound pywin32 compatibility path.
    # Reuse Component2.Transform2 instead of IMathUtility.CreateTransform.
    mt, err = member0(comp, "Transform2", default=None)
    if err or mt is None:
        raise RuntimeError(err or "Component.Transform2 returned None")

    target = [float(x) for x in array16]
    attempts = []
    payloads = [
        ("tuple", tuple(target)),
        ("list", list(target)),
        ("VT_ARRAY|VT_R8", win32com.client.VARIANT(
            pythoncom.VT_ARRAY | pythoncom.VT_R8, target)),
    ]

    applied_by = None
    for label, payload in payloads:
        try:
            mt.ArrayData = payload
            got, gerr = member0(mt, "ArrayData", default=None)
            if gerr or got is None:
                attempts.append(f"{label}: readback failed: {gerr}")
                continue
            got = [float(x) for x in list(got)]
            if len(got) != 16:
                attempts.append(f"{label}: readback length={len(got)}")
                continue
            delta = max(abs(got[i] - target[i]) for i in range(16))
            if delta <= 1.0e-12:
                applied_by = label
                break
            attempts.append(f"{label}: readback max delta={delta:.3e}")
        except Exception as exc:
            attempts.append(f"{label}: {type(exc).__name__}: {exc}")

    if applied_by is None:
        raise RuntimeError("Could not write IMathTransform.ArrayData. Attempts: "
                           + " | ".join(attempts))

    transform_method = set_transform(comp, mt)
    return transform_method, applied_by


def set_transform(comp, mt):
    # Direct Transform2 assignment avoids asking the mate solver to reposition
    # other assembly components. Fallback to SetTransformAndSolve2 if this
    # specific late-bound wrapper does not allow the property assignment.
    try:
        comp.Transform2 = mt
        return "Transform2 property"
    except Exception as exc1:
        ok, err = call(comp, "SetTransformAndSolve2", mt, default=False)
        if err or not ok:
            raise RuntimeError(
                "Could not set candidate transform. "
                f"Transform2 property: {type(exc1).__name__}: {exc1}; "
                f"SetTransformAndSolve2: {err or ok!r}"
            )
        return "SetTransformAndSolve2 fallback"


def transform_max_abs_delta(a, b):
    return max(abs(float(a[i]) - float(b[i])) for i in range(16))


def interference_summary(assembly, candidate_path):
    """
    Runs assembly Interference Detection with coincidence disabled.
    Gate03C only fails if the new P007 candidate itself appears in the
    interfering-component list. Other pre-existing/intended K01 interferences
    are reported but do not fail this gate.
    """
    out = {
        "available": False,
        "interference_count": None,
        "interfering_component_count": None,
        "interfering_components": [],
        "candidate_in_interference": None,
        "errors": [],
    }

    mgr, err = member0(assembly, "InterferenceDetectionManager", default=None)
    if err or mgr is None:
        out["errors"].append(err or "InterferenceDetectionManager unavailable")
        return out

    out["available"] = True

    for prop, value in (
        ("TreatCoincidenceAsInterference", False),
        ("IgnoreHiddenBodies", True),
        ("TreatSubAssembliesAsComponents", False),
    ):
        try:
            setattr(mgr, prop, value)
        except Exception as exc:
            out["errors"].append(f"{prop}: {type(exc).__name__}: {exc}")

    count, e = call(mgr, "GetInterferenceCount", default=None)
    if e:
        out["errors"].append(e)
    elif count is not None:
        try:
            out["interference_count"] = int(count)
        except Exception:
            pass

    comps, e = call(mgr, "GetInterferenceComponents", default=None)
    if e:
        out["errors"].append(e)
    else:
        rows = []
        for c in as_list(comps):
            if c is None:
                continue
            try:
                rows.append({
                    "name": component_name(c),
                    "path": component_path(c),
                })
            except Exception as exc:
                out["errors"].append(f"interference component read: {exc}")
        out["interfering_components"] = rows
        out["interfering_component_count"] = len(rows)

        cp = os.path.normcase(os.path.normpath(candidate_path))
        out["candidate_in_interference"] = any(
            os.path.normcase(os.path.normpath(r["path"])) == cp
            for r in rows if r.get("path")
        )

    try:
        call(mgr, "Done", default=None)
    except Exception:
        pass

    return out


def main():
    pythoncom.CoInitialize()

    if not BUILD_REPORT.exists():
        raise RuntimeError(f"Gate03B report missing: {BUILD_REPORT}")

    build = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    if build.get("status") != "PASS":
        raise RuntimeError(f"Gate03B is not PASS: {build.get('status')!r}")
    if build.get("schema") != "k01_p007_gate03b_build_v4_blind_end":
        raise RuntimeError(
            "Gate03C requires the corrected v4 blind-end candidate. "
            f"Got schema={build.get('schema')!r}"
        )

    candidate_path = Path(build["native_candidate"])
    if not candidate_path.exists():
        raise RuntimeError(f"Native v4 candidate not found: {candidate_path}")

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    revision, _ = member0(sw, "RevisionNumber", default="")

    model, err = member0(sw, "ActiveDoc", default=None)
    if err or model is None:
        raise RuntimeError(err or "No active SOLIDWORKS document")

    dtype, _ = member0(model, "GetType", default=None)
    title, _ = member0(model, "GetTitle", default="")
    path, _ = member0(model, "GetPathName", default="")
    dirty, _ = member0(model, "GetSaveFlag", default=False)

    print("=" * 74)
    print("K01 Gate 03C - P007 ASSEMBLY PLACEMENT / INTERFERENCE VERIFY")
    print("=" * 74)
    print(f"[INFO] SOLIDWORKS revision: {revision}")
    print(f"[INFO] Active document:    {title}")
    print(f"[INFO] Path:               {path}")
    print(f"[INFO] Candidate:          {candidate_path}")

    if int(dtype) != 2:
        raise RuntimeError(f"Active document must be an Assembly, got type={dtype!r}")
    if not str(title).lower().endswith(PRODUCTION_ASSEMBLY_NAME.lower()):
        raise RuntimeError(
            f"Active assembly must be {PRODUCTION_ASSEMBLY_NAME}; got {title!r}"
        )
    if bool(dirty):
        raise RuntimeError(
            "Production assembly has unsaved changes. Save or discard them before Gate03C."
        )

    production_path = Path(str(path))
    if not production_path.exists():
        raise RuntimeError(f"Production assembly path does not exist: {production_path}")

    assembly = model
    comps = find_components(assembly)

    p003_matches = find_by_suffix(comps, P003_SUFFIX)
    p007_matches = find_by_suffix(comps, P007_SUFFIX)

    if len(p003_matches) != 1:
        raise RuntimeError(f"Expected one P003 instance, got {len(p003_matches)}")
    if len(p007_matches) != 1:
        raise RuntimeError(f"Expected one production P007 instance, got {len(p007_matches)}")

    p003 = p003_matches[0]
    p007_old = p007_matches[0]

    T003 = transform_array(p003)
    T007_old = transform_array(p007_old)

    ex003 = axis_x(T003)
    ex007 = axis_x(T007_old)
    if abs(abs(dot(ex003, ex007)) - 1.0) > TOL_AXIS:
        raise RuntimeError(
            f"P003/P007 local X axes are not parallel: ex003={ex003}, ex007={ex007}"
        )
    if dot(ex003, ex007) < 0:
        raise RuntimeError(
            "P003 and P007 local X axes are opposite. Gate03C mapping must be reviewed."
        )

    p003_planes = axial_plane_rows(p003)
    p007_planes = axial_plane_rows(p007_old)

    if len(p003_planes) < 2:
        raise RuntimeError(f"Could not resolve P003 axial planes: {p003_planes}")
    if len(p007_planes) != 5:
        raise RuntimeError(
            "Current P007 topology changed: expected exactly 5 unique axial planes, "
            f"got {len(p007_planes)}: {p007_planes}"
        )

    p003_rear = max(p003_planes, key=lambda r: r["x_local_mm"])
    p003_rear_point = transform_point(T003, [p003_rear["x_local_m"], 0.0, 0.0])

    weld = build["controlled_geometry_mm"]
    expected_area = math.pi / 4.0 * (
        float(weld["weld_face_OD"]) ** 2 - float(weld["weld_face_ID"]) ** 2
    )
    actual_area = float(p003_rear["area_mm2"])
    area_delta = abs(actual_area - expected_area)
    if area_delta > TOL_SECTION_AREA_MM2:
        raise RuntimeError(
            "P003 rear section no longer matches Gate03B weld face: "
            f"P003 area={actual_area:.9f} mm^2, "
            f"candidate expected={expected_area:.9f} mm^2, "
            f"delta={area_delta:.9f}"
        )

    # Current P007 station points.
    # Sorted stations:
    # [0] old sleeve front
    # [1] thin ID start
    # [2] thin OD start
    # [3] rear inner face
    # [4] rear outer face
    old_station_points = {
        "old_front": transform_point(T007_old, [p007_planes[0]["x_local_m"], 0.0, 0.0]),
        "thin_ID_start": transform_point(T007_old, [p007_planes[1]["x_local_m"], 0.0, 0.0]),
        "thin_OD_start": transform_point(T007_old, [p007_planes[2]["x_local_m"], 0.0, 0.0]),
        "rear_inner": transform_point(T007_old, [p007_planes[3]["x_local_m"], 0.0, 0.0]),
        "rear_outer": transform_point(T007_old, [p007_planes[4]["x_local_m"], 0.0, 0.0]),
    }

    current_overlap_mm = distance_mm(p003_rear_point, old_station_points["old_front"])

    # Candidate transform:
    # preserve old P007 orientation; put local x=0 exactly at P003 rear-face center.
    T007_new_target = list(T007_old)
    T007_new_target[9:12] = p003_rear_point

    new_station_points = {
        "weld_face": transform_point(T007_new_target, [0.0, 0.0, 0.0]),
        "thin_ID_start": transform_point(
            T007_new_target, [float(weld["thin_ID_start"]) / 1000.0, 0.0, 0.0]
        ),
        "thin_OD_start": transform_point(
            T007_new_target, [float(weld["thin_OD_start"]) / 1000.0, 0.0, 0.0]
        ),
        "rear_inner": transform_point(
            T007_new_target, [float(weld["rear_inner_station"]) / 1000.0, 0.0, 0.0]
        ),
        "rear_outer": transform_point(
            T007_new_target, [float(weld["rear_outer_station"]) / 1000.0, 0.0, 0.0]
        ),
    }

    station_deltas_mm = {
        "weld_face_to_P003_rear": distance_mm(
            new_station_points["weld_face"], p003_rear_point
        ),
        "thin_ID_start": distance_mm(
            new_station_points["thin_ID_start"], old_station_points["thin_ID_start"]
        ),
        "thin_OD_start": distance_mm(
            new_station_points["thin_OD_start"], old_station_points["thin_OD_start"]
        ),
        "rear_inner": distance_mm(
            new_station_points["rear_inner"], old_station_points["rear_inner"]
        ),
        "rear_outer": distance_mm(
            new_station_points["rear_outer"], old_station_points["rear_outer"]
        ),
    }

    if any(v > TOL_STATION_MM for v in station_deltas_mm.values()):
        raise RuntimeError(
            f"Station-preservation calculation failed: {station_deltas_mm}"
        )

    print(f"[PASS] Current P003/P007 telescopic overlap = {current_overlap_mm:.6f} mm")
    print(f"[PASS] P003 rear annulus matches candidate weld face; ΔA={area_delta:.9f} mm^2")
    for k, v in station_deltas_mm.items():
        print(f"[PASS] calculated {k}: Δ={v:.9f} mm")

    # ------------------------------------------------------------------
    # Create a controlled COPY of the real assembly.
    # Production assembly on disk is not overwritten.
    # ------------------------------------------------------------------
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    verify_path = VERIFY_DIR / f"{VERIFY_BASE}_{stamp}.SLDASM"
    save_as(model, verify_path)

    active_path, _ = member0(model, "GetPathName", default="")
    if os.path.normcase(os.path.normpath(str(active_path))) != os.path.normcase(
        os.path.normpath(str(verify_path))
    ):
        raise RuntimeError(
            f"After SaveAs3 active assembly is not verification copy: {active_path}"
        )

    print(f"[PASS] Verification assembly copy created: {verify_path}")

    # Re-read component objects in copied assembly.
    comps_copy = find_components(model)
    old_matches = find_by_suffix(comps_copy, P007_SUFFIX)
    if len(old_matches) != 1:
        raise RuntimeError(
            f"Verification copy expected one old P007 before replacement, got {len(old_matches)}"
        )
    old_copy = old_matches[0]

    # Select old P007 without SelectData/SelectByID2 COM marshaling.
    call(model, "ClearSelection2", True, default=None)
    selected, serr = call(old_copy, "Select2", False, 0, default=False)
    if serr or not selected:
        raise RuntimeError(f"P007 component Select2 failed: {serr or selected!r}")

    replaced, rerr = call(
        model,
        "ReplaceComponents2",
        str(candidate_path),
        "",
        False,   # selected instance only
        0,       # current selected configuration
        False,   # do not reattach mates: placement is controlled explicitly
        default=False,
    )
    if rerr or not replaced:
        raise RuntimeError(f"ReplaceComponents2 failed: {rerr or replaced!r}")

    call(model, "ForceRebuild3", False, default=None)

    comps_after = find_components(model)
    candidate_matches = [
        c for c in comps_after
        if os.path.normcase(os.path.normpath(component_path(c)))
        == os.path.normcase(os.path.normpath(str(candidate_path)))
    ]
    if len(candidate_matches) != 1:
        raise RuntimeError(
            f"Expected one v4 candidate after replacement, got {len(candidate_matches)}"
        )
    candidate = candidate_matches[0]

    transform_method, array_write_method = retarget_existing_component_transform(
        candidate, T007_new_target
    )

    call(model, "ForceRebuild3", False, default=None)

    T007_actual = transform_array(candidate)
    transform_delta = transform_max_abs_delta(T007_actual, T007_new_target)
    if transform_delta > TOL_TRANSFORM:
        raise RuntimeError(
            "Candidate transform does not match target. "
            f"max_abs_delta={transform_delta:.3e}"
        )

    print(f"[PASS] Candidate replacement and placement via {transform_method}; "       f"ArrayData write={array_write_method}")
    print(f"[PASS] Candidate transform max |Δ| = {transform_delta:.3e}")

    # Recalculate physical station points from the ACTUAL placed transform.
    actual_station_points = {
        "weld_face": transform_point(T007_actual, [0.0, 0.0, 0.0]),
        "thin_ID_start": transform_point(
            T007_actual, [float(weld["thin_ID_start"]) / 1000.0, 0.0, 0.0]
        ),
        "thin_OD_start": transform_point(
            T007_actual, [float(weld["thin_OD_start"]) / 1000.0, 0.0, 0.0]
        ),
        "rear_inner": transform_point(
            T007_actual, [float(weld["rear_inner_station"]) / 1000.0, 0.0, 0.0]
        ),
        "rear_outer": transform_point(
            T007_actual, [float(weld["rear_outer_station"]) / 1000.0, 0.0, 0.0]
        ),
    }
    physical_deltas_mm = {
        "weld_face_to_P003_rear": distance_mm(
            actual_station_points["weld_face"], p003_rear_point
        ),
        "thin_ID_start": distance_mm(
            actual_station_points["thin_ID_start"], old_station_points["thin_ID_start"]
        ),
        "thin_OD_start": distance_mm(
            actual_station_points["thin_OD_start"], old_station_points["thin_OD_start"]
        ),
        "rear_inner": distance_mm(
            actual_station_points["rear_inner"], old_station_points["rear_inner"]
        ),
        "rear_outer": distance_mm(
            actual_station_points["rear_outer"], old_station_points["rear_outer"]
        ),
    }
    if any(v > TOL_STATION_MM for v in physical_deltas_mm.values()):
        raise RuntimeError(
            f"Physical assembly station verification failed: {physical_deltas_mm}"
        )

    for k, v in physical_deltas_mm.items():
        print(f"[PASS] physical {k}: Δ={v:.9f} mm")

    # Interference gate.
    interference = interference_summary(model, str(candidate_path))
    if interference["available"] and interference["candidate_in_interference"] is True:
        raise RuntimeError(
            "P007 v4 candidate appears in SOLIDWORKS interference results. "
            f"Details: {interference}"
        )

    if interference["available"] and interference["candidate_in_interference"] is False:
        print(
            "[PASS] Interference Detection: candidate P007 is not in the "
            "interfering-component list."
        )
    else:
        print(
            "[WARN] Interference Detection API could not provide a definitive "
            "candidate result. Run Evaluate > Interference Detection manually "
            "with 'Treat coincidence as interference' OFF."
        )

    # Save final verification state.
    save_as(model, verify_path)

    report = {
        "schema": "k01_gate03c_assembly_verify_v1",
        "status": (
            "PASS"
            if interference.get("candidate_in_interference") is False
            else "PASS_WITH_INTERFERENCE_API_WARN"
        ),
        "solidworks_revision": str(revision),
        "production_assembly": str(production_path),
        "production_assembly_modified": False,
        "verification_assembly": str(verify_path),
        "gate03b_candidate": str(candidate_path),
        "gate03b_schema": build.get("schema"),
        "current_overlap_mm": current_overlap_mm,
        "p003_rear": {
            "local_station_mm": p003_rear["x_local_mm"],
            "area_mm2": actual_area,
            "candidate_expected_area_mm2": expected_area,
            "area_delta_mm2": area_delta,
            "assembly_point_m": p003_rear_point,
        },
        "production_P007_axial_planes_local_mm": [
            r["x_local_mm"] for r in p007_planes
        ],
        "old_P007_transform": T007_old,
        "target_candidate_transform": T007_new_target,
        "actual_candidate_transform": T007_actual,
        "transform_max_abs_delta": transform_delta,
        "transform_write_method": transform_method,
        "transform_array_write_method": array_write_method,
        "calculated_station_deltas_mm": station_deltas_mm,
        "physical_station_deltas_mm": physical_deltas_mm,
        "interference": interference,
        "release_status": "ASSEMBLY_GEOMETRY_GATE_ONLY__NOT_P007_RELEASE",
        "next_gate": (
            "P007 Static +0.20 bar and external-pressure Buckling -0.20 bar "
            "after interference gate is definitive"
        ),
    }

    OUT_REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 74)
    print("K01 Gate 03C RESULT")
    print("=" * 74)
    print("Status:", report["status"])
    print("Verification assembly:", verify_path)
    print("Report:", OUT_REPORT)
    print("Production assembly on disk was NOT overwritten.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: K01 Gate03C assembly verification")
        traceback.print_exc()
        sys.exit(1)
