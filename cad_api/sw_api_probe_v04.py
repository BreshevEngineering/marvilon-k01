"""
K01 SOLIDWORKS API Gate 01 — READ-ONLY probe v04.

Purpose
-------
Connect to the running SOLIDWORKS instance and audit the active native part.
This version is deliberately read-only and treats optional QA fields as warnings,
not fatal errors.

Requirements
------------
Windows + SOLIDWORKS 2026 + Python 3.12 x64 + pywin32.

Run from repository root:
    py -3.12 cad_api\sw_api_probe_v04.py

Before running:
    1. Start SOLIDWORKS 2026.
    2. Open and save native K01-P-016.
    3. Keep that part active.

Output
------
reports\CAD_SNAPSHOT_probe_v04.json
"""

from __future__ import annotations

import json
import math
import os
import sys
import traceback
from pathlib import Path

import win32com.client

SW_DOC_PART = 1
SW_SOLID_BODY = 0

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "reports" / "CAD_SNAPSHOT_probe_v04.json"

EXPECTED_NAMED_OBJECTS = (
    "K01_DATUM_A_MATING",
    "K01_DATUM_B_AXIS",
)


def safe_call(label, func, warnings, default=None):
    try:
        return func()
    except Exception as exc:
        warnings.append(f"{label}: {type(exc).__name__}: {exc}")
        return default


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    # pywin32 SAFEARRAY may support iteration without being list/tuple
    try:
        return list(value)
    except Exception:
        return [value]


def feature_tree(model, warnings):
    rows = []
    feat = safe_call("FirstFeature", lambda: model.FirstFeature(), warnings)
    guard = 0
    while feat is not None and guard < 10000:
        guard += 1
        name = safe_call("feature.Name", lambda: feat.Name, warnings, "<unreadable>")
        ftype = safe_call("feature.GetTypeName2", lambda: feat.GetTypeName2(), warnings, "<unknown>")
        suppressed = safe_call("feature.IsSuppressed", lambda: feat.IsSuppressed(), warnings, None)

        if isinstance(suppressed, (list, tuple)):
            suppressed = list(suppressed)
        elif suppressed is not None:
            try:
                suppressed = bool(suppressed)
            except Exception:
                suppressed = str(suppressed)

        rows.append({
            "index": guard,
            "name": str(name),
            "type": str(ftype),
            "suppressed": suppressed,
        })
        feat = safe_call("feature.GetNextFeature", lambda: feat.GetNextFeature(), warnings)
    if guard >= 10000:
        warnings.append("Feature traversal stopped at safety limit 10000.")
    return rows


def part_body_audit(model, warnings):
    """
    For a PART only:
      IPartDoc::GetBodies2(swSolidBody, False)
      IBody2::GetBodyBox()
    Official API notes GetBodyBox is approximate; we use it as a QA snapshot,
    not as a production dimensional inspection method.
    """
    result = {
        "solid_body_count": None,
        "bodies": [],
        "combined_bbox_m": None,
        "combined_bbox_size_mm": None,
    }

    bodies = safe_call(
        "IPartDoc.GetBodies2",
        lambda: model.GetBodies2(SW_SOLID_BODY, False),
        warnings,
        None,
    )
    bodies = as_list(bodies)
    result["solid_body_count"] = len(bodies)

    all_boxes = []
    for idx, body in enumerate(bodies, start=1):
        bname = safe_call(f"Body[{idx}].Name", lambda b=body: b.Name, warnings, f"Body{idx}")
        box = safe_call(f"Body[{idx}].GetBodyBox", lambda b=body: b.GetBodyBox(), warnings, None)
        box_list = as_list(box)
        if len(box_list) == 6:
            box_list = [float(v) for v in box_list]
            all_boxes.append(box_list)
        else:
            box_list = None

        face_count = safe_call(
            f"Body[{idx}].GetFaceCount",
            lambda b=body: b.GetFaceCount(),
            warnings,
            None,
        )

        result["bodies"].append({
            "index": idx,
            "name": str(bname),
            "bbox_m": box_list,
            "face_count": face_count,
        })

    if all_boxes:
        xmin = min(b[0] for b in all_boxes)
        ymin = min(b[1] for b in all_boxes)
        zmin = min(b[2] for b in all_boxes)
        xmax = max(b[3] for b in all_boxes)
        ymax = max(b[4] for b in all_boxes)
        zmax = max(b[5] for b in all_boxes)
        comb = [xmin, ymin, zmin, xmax, ymax, zmax]
        result["combined_bbox_m"] = comb
        result["combined_bbox_size_mm"] = [
            (xmax - xmin) * 1000.0,
            (ymax - ymin) * 1000.0,
            (zmax - zmin) * 1000.0,
        ]

    return result


def custom_properties(model, warnings):
    out = {}
    mgr = safe_call(
        "CustomPropertyManager",
        lambda: model.Extension.CustomPropertyManager(""),
        warnings,
        None,
    )
    if mgr is None:
        return out

    names = safe_call("GetNames", lambda: mgr.GetNames(), warnings, None)
    for name in as_list(names):
        if not name:
            continue

        def read_prop(n=name):
            # Get6(FieldName, UseCached, ValOut, ResolvedValOut, WasResolved, LinkToProperty)
            return mgr.Get6(str(n), False)

        raw = safe_call(f"property {name}", read_prop, warnings, None)
        out[str(name)] = raw
    return out


def main():
    warnings = []

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise SystemExit("FAIL: no active SOLIDWORKS document.")

    doc_type = int(model.GetType())
    title = model.GetTitle()
    path = model.GetPathName()

    snapshot = {
        "probe_revision": "v04",
        "read_only": True,
        "solidworks": {
            "revision_number": safe_call(
                "SOLIDWORKS RevisionNumber",
                lambda: sw.RevisionNumber(),
                warnings,
                None,
            ),
            "visible": safe_call("SOLIDWORKS Visible", lambda: bool(sw.Visible), warnings, None),
        },
        "document": {
            "title": title,
            "path": path,
            "type": doc_type,
            "saved": bool(path),
        },
        "feature_tree": feature_tree(model, warnings),
        "custom_properties": custom_properties(model, warnings),
        "part_geometry": None,
        "expected_named_objects": {},
        "warnings": warnings,
    }

    if doc_type == SW_DOC_PART:
        snapshot["part_geometry"] = part_body_audit(model, warnings)
    else:
        warnings.append(
            f"Active document type is {doc_type}, not PART ({SW_DOC_PART}); "
            "part body audit skipped."
        )

    names = {row["name"] for row in snapshot["feature_tree"]}
    snapshot["expected_named_objects"] = {
        name: (name in names) for name in EXPECTED_NAMED_OBJECTS
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    print("============================================================")
    print("K01 SOLIDWORKS API Gate 01 — v04")
    print("============================================================")
    print(f"Document: {title}")
    print(f"Path:     {path or '[UNSAVED]'}")
    print(f"Type:     {doc_type}")
    print(f"Features: {len(snapshot['feature_tree'])}")

    pg = snapshot.get("part_geometry") or {}
    print(f"Solid bodies: {pg.get('solid_body_count')}")
    print(f"BBox size mm: {pg.get('combined_bbox_size_mm')}")

    for name, found in snapshot["expected_named_objects"].items():
        print(f"{'[PASS]' if found else '[OPEN]'} named object: {name}")

    print(f"Warnings: {len(warnings)}")
    for w in warnings:
        print(f"  WARN: {w}")

    print(f"\nSnapshot: {OUT}")
    print("\nPASS: COM connection and read-only snapshot completed.")
    print("NOTE: bounding boxes are approximate QA metadata, not drawing inspection values.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: unhandled probe error")
        traceback.print_exc()
        sys.exit(1)
