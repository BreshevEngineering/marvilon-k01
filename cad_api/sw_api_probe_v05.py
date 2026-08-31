"""
K01 SOLIDWORKS API Gate 01 — READ-ONLY probe v05.

This probe is intentionally defensive with pywin32 dynamic COM dispatch:
some SOLIDWORKS members can appear as callable methods in one dispatch
context and as already-evaluated properties in another.

It does not modify the active model.

Output:
    reports/CAD_SNAPSHOT_probe_v05.json
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import win32com.client

SW_DOC_PART = 1
SW_SOLID_BODY = 0

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "reports" / "CAD_SNAPSHOT_probe_v05.json"

EXPECTED_NAMED_OBJECTS = (
    "K01_DATUM_A_MATING",
    "K01_DATUM_B_AXIS",
)


def member(obj, name, *args):
    """Return a COM member whether pywin32 exposes it as method or property."""
    attr = getattr(obj, name)
    if callable(attr):
        return attr(*args)
    if args:
        raise TypeError(f"{name} is a property in this dispatch context but arguments were supplied")
    return attr


def safe(label, func, warnings, default=None):
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
    try:
        return list(value)
    except Exception:
        return [value]


def feature_tree(model, warnings):
    rows = []
    feat = safe("FirstFeature", lambda: member(model, "FirstFeature"), warnings)
    guard = 0
    while feat is not None and guard < 10000:
        guard += 1
        name = safe("Feature.Name", lambda f=feat: member(f, "Name"), warnings, "<unreadable>")
        ftype = safe("Feature.GetTypeName2", lambda f=feat: member(f, "GetTypeName2"), warnings, "<unknown>")
        suppressed = safe("Feature.IsSuppressed", lambda f=feat: member(f, "IsSuppressed"), warnings, None)
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
        feat = safe("Feature.GetNextFeature", lambda f=feat: member(f, "GetNextFeature"), warnings)
    if guard >= 10000:
        warnings.append("Feature traversal stopped at safety limit 10000.")
    return rows


def body_audit(model, warnings):
    result = {
        "solid_body_count": None,
        "bodies": [],
        "combined_bbox_m": None,
        "combined_bbox_size_mm": None,
    }
    bodies_raw = safe(
        "IPartDoc.GetBodies2",
        lambda: member(model, "GetBodies2", SW_SOLID_BODY, False),
        warnings,
        None,
    )
    bodies = as_list(bodies_raw)
    result["solid_body_count"] = len(bodies)

    boxes = []
    for idx, body in enumerate(bodies, 1):
        bname = safe(f"Body[{idx}].Name", lambda b=body: member(b, "Name"), warnings, f"Body{idx}")
        box = safe(f"Body[{idx}].GetBodyBox", lambda b=body: member(b, "GetBodyBox"), warnings, None)
        box = as_list(box)
        if len(box) == 6:
            box = [float(v) for v in box]
            boxes.append(box)
        else:
            box = None
        faces = safe(f"Body[{idx}].GetFaceCount", lambda b=body: member(b, "GetFaceCount"), warnings, None)
        result["bodies"].append({
            "index": idx,
            "name": str(bname),
            "bbox_m": box,
            "face_count": faces,
        })

    if boxes:
        xmin=min(b[0] for b in boxes); ymin=min(b[1] for b in boxes); zmin=min(b[2] for b in boxes)
        xmax=max(b[3] for b in boxes); ymax=max(b[4] for b in boxes); zmax=max(b[5] for b in boxes)
        result["combined_bbox_m"]=[xmin,ymin,zmin,xmax,ymax,zmax]
        result["combined_bbox_size_mm"]=[
            (xmax-xmin)*1000.0,
            (ymax-ymin)*1000.0,
            (zmax-zmin)*1000.0,
        ]
    return result


def custom_properties(model, warnings):
    out = {}
    ext = safe("Model.Extension", lambda: member(model, "Extension"), warnings, None)
    if ext is None:
        return out
    mgr = safe("CustomPropertyManager", lambda: ext.CustomPropertyManager(""), warnings, None)
    if mgr is None:
        return out
    names = safe("CustomPropertyManager.GetNames", lambda: member(mgr, "GetNames"), warnings, None)
    for name in as_list(names):
        if not name:
            continue
        raw = safe(
            f"property {name}",
            lambda n=str(name): member(mgr, "Get6", n, False),
            warnings,
            None,
        )
        out[str(name)] = raw
    return out


def write_snapshot(snapshot):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def main():
    warnings = []

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = member(sw, "ActiveDoc")
    if model is None:
        raise SystemExit("FAIL: no active SOLIDWORKS document.")

    # Read fundamental fields defensively.
    title = safe("Model.GetTitle", lambda: member(model, "GetTitle"), warnings, None)
    path = safe("Model.GetPathName", lambda: member(model, "GetPathName"), warnings, None)
    doc_type = safe("Model.GetType", lambda: member(model, "GetType"), warnings, None)

    # Write a minimal snapshot immediately so later optional QA cannot erase evidence.
    snapshot = {
        "probe_revision": "v05",
        "read_only": True,
        "solidworks": {
            "revision_number": safe("SW.RevisionNumber", lambda: member(sw, "RevisionNumber"), warnings, None),
            "visible": safe("SW.Visible", lambda: bool(member(sw, "Visible")), warnings, None),
        },
        "document": {
            "title": title,
            "path": path,
            "type": doc_type,
            "saved": bool(path),
        },
        "feature_tree": [],
        "custom_properties": {},
        "part_geometry": None,
        "expected_named_objects": {},
        "warnings": warnings,
    }
    write_snapshot(snapshot)

    snapshot["feature_tree"] = feature_tree(model, warnings)
    snapshot["custom_properties"] = custom_properties(model, warnings)

    try:
        doc_type_int = int(doc_type) if doc_type is not None else None
    except Exception:
        doc_type_int = None
        warnings.append(f"Could not convert document type to int: {doc_type!r}")

    if doc_type_int == SW_DOC_PART:
        snapshot["part_geometry"] = body_audit(model, warnings)
    else:
        warnings.append(f"Part body audit skipped: document type={doc_type!r}, expected PART={SW_DOC_PART}.")

    names = {row["name"] for row in snapshot["feature_tree"]}
    snapshot["expected_named_objects"] = {
        name: name in names for name in EXPECTED_NAMED_OBJECTS
    }

    write_snapshot(snapshot)

    print("============================================================")
    print("K01 SOLIDWORKS API Gate 01 — v05")
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
    print("NOTE: GetBodyBox is approximate QA metadata, not a drawing inspection value.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("FAIL: unhandled probe error")
        traceback.print_exc()
        sys.exit(1)
