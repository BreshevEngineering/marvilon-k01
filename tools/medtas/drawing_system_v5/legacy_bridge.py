
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Tuple
import json, re, subprocess, sys, os
from .utils import load_json, save_json

def _slot(family, name):
    p = family["legacy_bridge_layout"]["annotation_slots"][name]
    return float(p[0]), float(p[1])

def _binding_to_legacy(name: str, b: Dict[str, Any]) -> Dict[str, Any]:
    sig = b.get("geometry_signature") or {}
    kind = b["kind"]

    if kind in {"CYLINDER", "CYLINDER_SET"}:
        result = {
            "kind": "CYLINDER_SET" if kind == "CYLINDER_SET" else "CYLINDER",
            "diameter_mm": float(sig["diameter_mm"]),
            "count": int(sig.get("count", 1)),
        }
        return result

    if kind == "THREAD_SEMANTIC":
        # Legacy geometric resolver needs the modeled cylindrical thread region, while
        # thread designation/class remains controlled semantic data.
        d = sig.get("model_geometry_diameter_mm")
        if d is None:
            raise RuntimeError(f"{name}: THREAD_SEMANTIC lacks model_geometry_diameter_mm")
        return {"kind": "CYLINDER", "diameter_mm": float(d), "count": 1}

    if kind == "PLANE_PAIR":
        # PLANE_PAIR is materialized below as two derived PLANE_AT_CYL_END bindings.
        return {"kind": "PLANE_PAIR_META", "separation_mm": float(sig["separation_mm"])}

    if kind == "AXIS":
        return {"kind": "OPEN_AXIS_SEMANTIC"}

    raise RuntimeError(f"Unsupported binding kind for legacy bridge: {name} / {kind}")

def contract_to_legacy_spec(contract: Dict[str, Any], family: Dict[str, Any], output_root: str) -> Dict[str, Any]:
    layout = family["legacy_bridge_layout"]

    bindings: Dict[str, Any] = {}
    for name, b in contract["model_bindings"].items():
        lb = _binding_to_legacy(name, b)
        if lb["kind"] not in {"PLANE_PAIR_META", "OPEN_AXIS_SEMANTIC"}:
            bindings[name] = lb

    # Generic derived end-plane bindings.
    # Thread length is resolved from the thread-region cylinder.
    if "THREAD_REGION" in contract["model_bindings"]:
        bindings["THREAD_END_1"] = {
            "kind": "PLANE_AT_CYL_END", "cylinder": "THREAD_REGION",
            "end": "MIN_X", "selection": "NEAREST_PLANE_TO_APPROX_CYL_TRIM_X__LARGEST_AREA_IF_COPLANAR"
        }
        bindings["THREAD_END_2"] = {
            "kind": "PLANE_AT_CYL_END", "cylinder": "THREAD_REGION",
            "end": "MAX_X", "selection": "NEAREST_PLANE_TO_APPROX_CYL_TRIM_X__LARGEST_AREA_IF_COPLANAR"
        }

    if "RELIEF_OD" in contract["model_bindings"]:
        bindings["RELIEF_END_1"] = {
            "kind": "PLANE_AT_CYL_END", "cylinder": "RELIEF_OD",
            "end": "MIN_X", "selection": "NEAREST_PLANE_TO_APPROX_CYL_TRIM_X__LARGEST_AREA_IF_COPLANAR"
        }
        bindings["RELIEF_END_2"] = {
            "kind": "PLANE_AT_CYL_END", "cylinder": "RELIEF_OD",
            "end": "MAX_X", "selection": "NEAREST_PLANE_TO_APPROX_CYL_TRIM_X__LARGEST_AREA_IF_COPLANAR"
        }

    # Only published view slots are emitted to the legacy engine.
    view_defs = []
    for v in contract["views"]:
        if not v["published"]:
            continue
        fv = layout["views"][v["id"]]
        item = dict(fv)
        item["id"] = fv["legacy_id"]
        item.pop("legacy_id", None)
        view_defs.append(item)

    # Map contract view IDs to emitted legacy IDs.
    view_map = {
        "LONGITUDINAL_SECTION": layout["views"]["LONGITUDINAL_SECTION"]["legacy_id"],
        "END_VIEW": layout["views"]["END_VIEW"]["legacy_id"],
    }

    annotations: List[Dict[str, Any]] = []
    review_notes: List[str] = ["ENGINEERING REVIEW — NOT FOR MANUFACTURE"]

    for c in contract["characteristics"]:
        cid = c["id"]
        cls = c["semantic_class"]
        req = c["requirement"]

        if c["drawing_projection"] != "REQUIRED":
            review_notes.append(f"OPEN {cid}: {c.get('notes') or req}")
            continue

        if cls == "THREAD_EXTERNAL":
            x, y = _slot(family, "THREAD_CALLOUT")
            text = f'{req["designation"]}-{req["tolerance_class"]}'
            annotations.append({
                "id": cid + "-THREAD", "kind": "BOUND_NOTE",
                "view": view_map[c["view_id"]], "binding": c["bindings"][0],
                "text": text, "state": "CONTROLLED", "x_m": x, "y_m": y
            })
            x, y = _slot(family, "THREAD_LENGTH")
            annotations.append({
                "id": cid + "-LENGTH", "kind": "LINEAR",
                "view": view_map[c["view_id"]],
                "from_binding": "THREAD_END_1", "to_binding": "THREAD_END_2",
                "nominal_mm": float(req["length_mm"]), "precision": 2,
                "state": "CONTROLLED", "x_m": x, "y_m": y
            })

        elif cls == "DIAMETER_FIT_SHAFT":
            x, y = _slot(family, "DIAMETER_FIT")
            annotations.append({
                "id": cid + "-DIAFIT", "kind": "DIAMETER",
                "view": view_map[c["view_id"]],
                "binding": c["bindings"][0],
                "nominal_mm": float(req["diameter_mm"]),
                "shaft_fit": req["fit"], "precision": 2,
                "state": "CONTROLLED", "x_m": x, "y_m": y
            })

        elif cls == "DIAMETER_THROUGH":
            x, y = _slot(family, "THROUGH_BORE")
            annotations.append({
                "id": cid + "-DIA", "kind": "DIAMETER",
                "view": view_map[c["view_id"]],
                "binding": c["bindings"][0],
                "nominal_mm": float(req["diameter_mm"]),
                "suffix": " THRU" if req.get("through") else "",
                "precision": 2, "state": "CONTROLLED", "x_m": x, "y_m": y
            })

        elif cls == "BLIND_HOLE_PATTERN":
            x, y = _slot(family, "HOLE_PATTERN_SIZE")
            full = (
                f'{int(req["count"])}× Ø{req["diameter_mm"]:.2f} '
                f'+{req["upper_tol_mm"]:.2f}/0 BLIND; '
                f'DEPTH {req["depth_mm"]:.2f} ±{req["depth_sym_tol_mm"]:.2f}'
            )
            annotations.append({
                "id": cid + "-HOLE-CALLOUT", "kind": "BOUND_NOTE",
                "view": view_map[c["view_id"]], "binding": c["bindings"][0],
                "text": full, "state": "CONTROLLED", "x_m": x, "y_m": y
            })
            x, y = _slot(family, "HOLE_PATTERN_PCD")
            annotations.append({
                "id": cid + "-PCD", "kind": "TED_NOTE",
                "view": view_map[c["view_id"]],
                "text": f'Ø{req["pcd_mm"]:.2f}', "state": "CONTROLLED",
                "x_m": x, "y_m": y
            })
            x, y = _slot(family, "HOLE_PATTERN_ANGLE")
            annotations.append({
                "id": cid + "-ANGLE", "kind": "TED_NOTE",
                "view": view_map[c["view_id"]],
                "text": f'{int(req["angle_deg"])}°', "state": "CONTROLLED",
                "x_m": x, "y_m": y
            })

        elif cls == "FUNCTIONAL_RELIEF":
            x, y = _slot(family, "RELIEF_OD")
            lo, hi = req["resulting_axial_float_mm"]
            text = (
                f'RELIEF Ø{req["diameter_mm"]:.2f}×{req["width_mm"]:.2f}; '
                f'P002 AXIAL FLOAT {lo:.2f}…{hi:.2f}'
            )
            annotations.append({
                "id": cid + "-RELIEF-CALLOUT", "kind": "BOUND_NOTE",
                "view": view_map[c["view_id"]], "binding": c["bindings"][0],
                "text": text, "state": "CONTROLLED", "x_m": x, "y_m": y
            })

        elif cls == "MATERIAL":
            # title block only
            pass

        else:
            review_notes.append(f"UNSUPPORTED REQUIRED CHARACTERISTIC {cid}: {cls}")

    doc = contract["document"]
    if doc["general_tolerance"]["state"] == "OPEN":
        review_notes.append("OPEN: GENERAL TOLERANCE STANDARD / CLASS.")
    if doc["surface_texture"]["state"] == "OPEN":
        review_notes.append("OPEN: SURFACE TEXTURE / ROUGHNESS REQUIREMENTS.")
    if doc["revision"]["state"] == "OPEN":
        review_notes.append("OPEN: RELEASE REVISION.")

    review_notes.extend([
        "UNSPECIFIED NOMINAL GEOMETRY: CONTROLLED NATIVE SOLIDWORKS MODEL. DO NOT SCALE DRAWING.",
        f'MATERIAL: {doc["material"]}',
    ])

    ox, oy = layout["review_note_origin"]

    title_props = {
        "DrawingNo": contract["drawing_id"],
        "PartNo": contract["part_id"],
        "Title": doc["title"],
        "Material": doc["material"],
        "Status": "ENGINEERING REVIEW",
        "Units": doc["units"],
        "Projection": doc["projection"],
        "Scale": doc["scale"],
        "Revision": doc["revision"].get("value") or "",
    }

    spec = {
        "schema": "k01.drawing_system_spec.v1",
        "drawing_id": contract["drawing_id"],
        "part_id": contract["part_id"],
        "title": doc["title"],
        "status": "ENGINEERING_REVIEW__RESULT_FIRST_V5_1",
        "model_path": contract["model"]["canonical_path"],
        "output_root": output_root,
        "sheet": doc["sheet"],
        "sheet_scale": float(doc["scale"].split(":")[0]) / float(doc["scale"].split(":")[1]),
        "projection": doc["projection"],
        "units": doc["units"],
        "material": doc["material"],
        "view_definitions": view_defs,
        "bindings": bindings,
        "datum_features": [],
        "annotations": annotations,
        "title_block_properties": title_props,
        "release_blockers": list(contract["release"]["blockers"]),
        "review_notes": review_notes,
        "review_note_x_m": ox,
        "review_note_y_m": oy,
        "review_note_step_m": layout["review_note_step_m"],
    }
    return spec

def parse_legacy_stdout(text: str) -> Dict[str, Any]:
    result = {}
    keys = {
        "DRAWING": "drawing",
        "PDF": "pdf",
        "DXF": "dxf",
        "REPORT": "report",
        "CANDIDATE ROOT": "candidate_root",
        "STATUS": "legacy_status",
    }
    for line in text.splitlines():
        for prefix, key in keys.items():
            marker = prefix + ":"
            if line.startswith(marker):
                result[key] = line.split(":", 1)[1].strip()
    return result

def execute_legacy_bridge(repo_root: str, contract: Dict[str, Any], family: Dict[str, Any], run_dir: str) -> Dict[str, Any]:
    repo = Path(repo_root)
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)

    output_root = str(Path(r"D:\Marvilon\K01\cad\drawings\candidates") / contract["drawing_id"])
    legacy_spec = contract_to_legacy_spec(contract, family, output_root)
    spec_path = run / "legacy_bridge_spec.json"
    save_json(spec_path, legacy_spec)

    wrapper = repo / "tools" / "medtas" / "drawing_system_v1.py"
    if not wrapper.is_file():
        return {
            "adapter_execution_state": "FAILED_UNSAFE",
            "reason": "legacy drawing_system_v1.py not found",
            "legacy_spec": str(spec_path),
        }

    cmd = [
        "py", "-3", str(wrapper),
        "--repo-root", str(repo),
        "--spec", str(spec_path),
        "--mode", "review",
    ]
    cp = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, errors="replace")
    stdout = cp.stdout or ""
    stderr = cp.stderr or ""
    (run / "legacy_stdout.txt").write_text(stdout, encoding="utf-8")
    (run / "legacy_stderr.txt").write_text(stderr, encoding="utf-8")

    parsed = parse_legacy_stdout(stdout)
    drawing = parsed.get("drawing")
    pdf = parsed.get("pdf")
    dxf = parsed.get("dxf")
    artifact_exists = (
        bool(drawing and Path(drawing).exists())
        or bool(pdf and Path(pdf).exists())
        or bool(dxf and Path(dxf).exists())
    )

    return {
        "adapter_execution_state": "GENERATED" if artifact_exists else "FAILED_UNSAFE",
        "legacy_return_code": cp.returncode,
        "legacy_status": parsed.get("legacy_status"),
        "drawing": drawing,
        "pdf": pdf,
        "dxf": dxf,
        "report": parsed.get("report"),
        "candidate_root": parsed.get("candidate_root"),
        "legacy_spec": str(spec_path),
        "stdout": str(run / "legacy_stdout.txt"),
        "stderr": str(run / "legacy_stderr.txt"),
        "artifact_exists": artifact_exists,
        "policy": "Legacy RC=3/HOLD does not fail execution if a usable drawing/PDF artifact exists."
    }
