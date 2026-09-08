from __future__ import annotations

import json
import math
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client

# Use the already-proven K01 COM compatibility layer.
from sw_com import member0, call, as_list


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "cad" / "current" / "K01_P003_P007_INTERFACE_PROBE.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "P003": "K01-P-003_Cartridge_Body.SLDPRT",
    "P007": "K01-P-007_Hermetic_Magnetic_Can.SLDPRT",
}


def norm(v):
    if not v or len(v) < 3:
        return None
    n = math.sqrt(sum(float(x) ** 2 for x in v[:3]))
    if n <= 0:
        return None
    return [float(x) / n for x in v[:3]]


def to_float_list(v):
    if v is None:
        return None
    try:
        return [float(x) for x in list(v)]
    except Exception:
        return None


def face_info(face, idx):
    errors = []
    row = {
        "index": idx,
        "kind": "other",
        "area_mm2": None,
        "diameter_mm": None,
        "axis_origin_mm": None,
        "axis_direction": None,
        "normal": None,
        "surface_params_raw_SI": None,
        "errors": errors,
    }

    area, e = member0(face, "GetArea", default=None)
    if e:
        errors.append(e)
    elif area is not None:
        try:
            row["area_mm2"] = float(area) * 1e6
        except Exception as exc:
            errors.append(f"GetArea conversion: {type(exc).__name__}: {exc}")

    surf, e = member0(face, "GetSurface", default=None)
    if e:
        errors.append(e)
    if surf is None:
        row["kind"] = "unread"
        return row

    is_cyl, e = member0(surf, "IsCylinder", default=False)
    if e:
        errors.append(e)

    if bool(is_cyl):
        row["kind"] = "cylinder"
        p, e = member0(surf, "CylinderParams", default=None)
        if e:
            errors.append(e)
        p = to_float_list(p)
        row["surface_params_raw_SI"] = p
        if p and len(p) >= 7:
            row["axis_origin_mm"] = [1000.0 * x for x in p[:3]]
            row["axis_direction"] = norm(p[3:6])
            row["diameter_mm"] = 2000.0 * float(p[6])
        return row

    is_plane, e = member0(surf, "IsPlane", default=False)
    if e:
        errors.append(e)

    if bool(is_plane):
        row["kind"] = "plane"
        p, e = member0(surf, "PlaneParams", default=None)
        if e:
            errors.append(e)
        p = to_float_list(p)
        row["surface_params_raw_SI"] = p
        if p and len(p) >= 3:
            row["normal"] = norm(p[:3])
        return row

    return row


def extract_component(comp, tag):
    errors = []

    path, e = member0(comp, "GetPathName", default="")
    if e:
        errors.append(e)
    name, e = member0(comp, "Name2", default="")
    if e:
        errors.append(e)

    transform_data = None
    tr, e = member0(comp, "Transform2", default=None)
    if e:
        errors.append(e)
    if tr is not None:
        ad, e = member0(tr, "ArrayData", default=None)
        if e:
            errors.append(e)
        transform_data = to_float_list(ad)

    model, e = member0(comp, "GetModelDoc2", default=None)
    if e:
        errors.append(e)

    if model is None:
        return {
            "tag": tag,
            "name": str(name),
            "path": str(path),
            "resolved": False,
            "component_transform_raw": transform_data,
            "solid_body_count": None,
            "bodies": [],
            "errors": errors + ["GetModelDoc2 returned None; resolve component and rerun."],
        }

    title, e = member0(model, "GetTitle", default="")
    if e:
        errors.append(e)

    bodies, e = call(model, "GetBodies2", 0, True, default=None)
    if e:
        errors.append(e)
    if bodies is None:
        bodies, e2 = call(model, "GetBodies2", 0, False, default=None)
        if e2:
            errors.append(e2)

    body_list = as_list(bodies)
    out_bodies = []

    for bi, body in enumerate(body_list):
        b_errors = []

        faces, e = member0(body, "GetFaces", default=None)
        if e:
            b_errors.append(e)
        face_list = as_list(faces)

        bbox, e = member0(body, "GetBodyBox", default=None)
        if e:
            b_errors.append(e)

        bbox_mm = None
        if bbox is not None:
            try:
                bbox_mm = [1000.0 * float(x) for x in list(bbox)]
            except Exception as exc:
                b_errors.append(f"GetBodyBox conversion: {type(exc).__name__}: {exc}")

        out_bodies.append({
            "index": bi,
            "body_box_mm": bbox_mm,
            "face_count": len(face_list),
            "faces": [face_info(face, i) for i, face in enumerate(face_list)],
            "errors": b_errors,
        })

    return {
        "tag": tag,
        "name": str(name),
        "path": str(path),
        "model_title": str(title),
        "resolved": True,
        "component_transform_raw": transform_data,
        "solid_body_count": len(out_bodies),
        "bodies": out_bodies,
        "errors": errors,
    }


def main():
    pythoncom.CoInitialize()

    sw = win32com.client.GetActiveObject("SldWorks.Application")

    # Critical fix: ActiveDoc is commonly an already-returned COM interface
    # under late-bound pywin32. member0 from sw_com does NOT invoke it again.
    model, e = member0(sw, "ActiveDoc", default=None)
    if e:
        raise RuntimeError(f"ActiveDoc read failed: {e}")
    if model is None:
        raise RuntimeError(
            "SOLIDWORKS COM connection succeeded but ActiveDoc is None. "
            "Click once inside K01-A-001 assembly window and rerun."
        )

    title, e_title = member0(model, "GetTitle", default="")
    dtype, e_type = member0(model, "GetType", default=None)

    if e_title:
        raise RuntimeError(f"GetTitle failed: {e_title}")
    if e_type:
        raise RuntimeError(f"GetType failed: {e_type}")

    print(f"[INFO] Active document: {title}")
    print(f"[INFO] Document type:   {dtype}")

    if int(dtype) != 2:
        raise RuntimeError(
            f"Active document must be an Assembly (type 2). "
            f"Current: title={title!r}, type={dtype!r}."
        )

    components, e = call(model, "GetComponents", False, default=None)
    if e:
        raise RuntimeError(f"GetComponents(False) failed: {e}")

    component_list = as_list(components)
    found = {}
    inventory = []

    for comp in component_list:
        p, pe = member0(comp, "GetPathName", default="")
        n, ne = member0(comp, "Name2", default="")
        inventory.append({
            "name": str(n),
            "path": str(p),
            "errors": [x for x in (pe, ne) if x],
        })

        low = str(p).lower()
        for tag, filename in TARGETS.items():
            if low.endswith(filename.lower()):
                found[tag] = comp

    missing = [tag for tag in TARGETS if tag not in found]
    if missing:
        raise RuntimeError(
            "Target component(s) not found in active assembly: "
            + ", ".join(missing)
            + ". Ensure assembly is fully resolved."
        )

    parts = {
        "P003": extract_component(found["P003"], "P003"),
        "P007": extract_component(found["P007"], "P007"),
    }

    candidates = {}
    for tag, pdata in parts.items():
        rows = []
        for body in pdata.get("bodies", []):
            for f in body.get("faces", []):
                if f.get("kind") == "cylinder":
                    d = f.get("diameter_mm")
                    if isinstance(d, (int, float)) and 9.0 <= d <= 18.0:
                        rows.append({
                            "body_index": body["index"],
                            "face_index": f["index"],
                            "kind": "cylinder",
                            "diameter_mm": d,
                            "area_mm2": f.get("area_mm2"),
                            "axis_origin_mm": f.get("axis_origin_mm"),
                            "axis_direction": f.get("axis_direction"),
                            "errors": f.get("errors", []),
                        })
                elif f.get("kind") == "plane":
                    a = f.get("area_mm2")
                    if isinstance(a, (int, float)) and a <= 250.0:
                        rows.append({
                            "body_index": body["index"],
                            "face_index": f["index"],
                            "kind": "plane",
                            "area_mm2": a,
                            "normal": f.get("normal"),
                            "errors": f.get("errors", []),
                        })
        candidates[tag] = rows

    result = {
        "schema": "k01_p003_p007_interface_probe_v2",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "active_assembly": {
            "title": str(title),
            "doc_type": int(dtype),
        },
        "manual_reference": {
            "current_P003_to_P007_station_mm": 27.00,
            "status": "user-measured reference only",
        },
        "parts": parts,
        "interface_candidates": candidates,
        "assembly_inventory": inventory,
    }

    OUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    fatal = []
    for tag in ("P003", "P007"):
        p = parts[tag]
        if not p.get("resolved"):
            fatal.append(f"{tag}: unresolved")
        if p.get("solid_body_count") != 1:
            fatal.append(f"{tag}: solid_body_count={p.get('solid_body_count')}")
        face_count = sum(b.get("face_count", 0) for b in p.get("bodies", []))
        if face_count == 0:
            fatal.append(f"{tag}: no faces captured")

    print("=" * 68)
    print("K01 Gate 03A - P003/P007 READ-ONLY INTERFACE PROBE v2")
    print("=" * 68)
    for tag in ("P003", "P007"):
        p = parts[tag]
        face_count = sum(b.get("face_count", 0) for b in p.get("bodies", []))
        print(
            f"{tag}: bodies={p.get('solid_body_count')} "
            f"faces={face_count} candidates={len(candidates[tag])}"
        )
    print(f"JSON: {OUT}")

    if fatal:
        print("[FAIL]")
        for item in fatal:
            print(" -", item)
        return 2

    print("[PASS] Gate 03A completed. No screenshots required.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: Gate 03A interface probe")
        traceback.print_exc()
        sys.exit(1)
