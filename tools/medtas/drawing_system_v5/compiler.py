
from __future__ import annotations
from typing import Any, Dict, List

def _job_for_characteristic(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    cls = c["semantic_class"]
    req = c["requirement"]
    base = {
        "characteristic_id": c["id"],
        "authority_state": c["state"],
        "view_id": c["view_id"],
        "bindings": c.get("bindings", []),
        "source_authority": c["source_authority"],
    }

    jobs = []
    def emit(op, payload):
        j = dict(base)
        j["op"] = op
        j["payload"] = payload
        jobs.append(j)

    if c["drawing_projection"] != "REQUIRED":
        emit("QA.OPEN_OR_NONRELEASED", {
            "projection": c["drawing_projection"],
            "requirement": req,
            "notes": c.get("notes"),
        })
        return jobs

    if cls == "THREAD_EXTERNAL":
        emit("ANNOTATION.THREAD_CALLOUT", {
            "designation": req["designation"],
            "tolerance_class": req["tolerance_class"],
            "length_mm": req["length_mm"],
        })
    elif cls == "DIAMETER_FIT_SHAFT":
        emit("DIMENSION.DIAMETER_FIT", {
            "diameter_mm": req["diameter_mm"],
            "fit": req["fit"],
        })
    elif cls == "DIAMETER_THROUGH":
        emit("DIMENSION.DIAMETER", {
            "diameter_mm": req["diameter_mm"],
            "suffix": " THRU" if req.get("through") else "",
        })
    elif cls == "BLIND_HOLE_PATTERN":
        emit("ANNOTATION.HOLE_PATTERN", req)
    elif cls == "GTOL_POSITION":
        emit("GTOL.POSITION", req)
    elif cls == "FUNCTIONAL_RELIEF":
        emit("DIMENSION.DIAMETER", {"diameter_mm": req["diameter_mm"], "role": "RELIEF_OD"})
        emit("DIMENSION.LINEAR", {"nominal_mm": req["width_mm"], "role": "RELIEF_WIDTH"})
        emit("NOTE.FUNCTIONAL_RANGE", {"label": "P002 AXIAL FLOAT", "range_mm": req["resulting_axial_float_mm"]})
    elif cls == "MATERIAL":
        emit("TITLE.MATERIAL", req)
    else:
        emit("UNSUPPORTED.CHARACTERISTIC", {"semantic_class": cls, "requirement": req})
    return jobs

def compile_manifest(contract: Dict[str, Any], family: Dict[str, Any], mode: str) -> Dict[str, Any]:
    views = []
    for v in contract["views"]:
        views.append({
            "id": v["id"],
            "kind": v["kind"],
            "published": v["published"],
            "role": v["role"],
            "orientation": v.get("orientation"),
            "dependency_of": v.get("dependency_of"),
        })

    jobs = []
    for c in contract["characteristics"]:
        jobs.extend(_job_for_characteristic(c))

    # Document jobs are generated from contract; no engineering value lives in the engine.
    jobs.extend([
        {
            "op": "DOCUMENT.SHEET",
            "payload": {
                "sheet": contract["document"]["sheet"],
                "units": contract["document"]["units"],
                "projection": contract["document"]["projection"],
                "scale": contract["document"]["scale"],
            }
        },
        {
            "op": "TITLE.BLOCK",
            "payload": {
                "drawing_id": contract["drawing_id"],
                "part_id": contract["part_id"],
                "title": contract["document"]["title"],
                "material": contract["document"]["material"],
                "revision": contract["document"]["revision"],
                "status": "ENGINEERING REVIEW" if mode == "review" else "RELEASE CANDIDATE",
            }
        }
    ])

    gt = contract["document"]["general_tolerance"]
    sf = contract["document"]["surface_texture"]

    if gt["state"] == "CONTROLLED":
        jobs.append({"op": "NOTE.GENERAL_TOLERANCE", "payload": gt})
    else:
        jobs.append({"op": "QA.OPEN_DOCUMENT_REQUIREMENT", "payload": {"field": "general_tolerance", "state": gt["state"]}})

    if sf["state"] == "CONTROLLED":
        jobs.append({"op": "ANNOTATION.GENERAL_SURFACE_TEXTURE", "payload": sf})
    else:
        jobs.append({"op": "QA.OPEN_DOCUMENT_REQUIREMENT", "payload": {"field": "surface_texture", "state": sf["state"]}})

    return {
        "schema": "marvilon.drawing_build_manifest.v1",
        "drawing_id": contract["drawing_id"],
        "part_id": contract["part_id"],
        "family_id": contract["drawing_family"],
        "mode": mode,
        "model": contract["model"],
        "bindings": contract["model_bindings"],
        "views": views,
        "jobs": jobs,
        "document": contract["document"],
        "release": contract["release"],
        "manual_after_build": family["manual_after_build_allowed"],
        "manual_engineering_changes_prohibited": family["manual_after_build_prohibited"],
    }
