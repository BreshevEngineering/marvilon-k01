"""
K01 SOLIDWORKS API Gate 01 — READ-ONLY probe v06 (minimal/stable).

Goal:
- prove reliable COM connection;
- identify active native part;
- read FeatureManager tree;
- verify named Datum A / Datum B;
- write JSON even if optional fields fail.

This probe DOES NOT modify the model.

Output:
    reports\CAD_SNAPSHOT_probe_v06.json
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import win32com.client

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "reports" / "CAD_SNAPSHOT_probe_v06.json"

EXPECTED = (
    "K01_DATUM_A_MATING",
    "K01_DATUM_B_AXIS",
)

def read0(obj, name, default=None):
    """
    Robust read of a zero-argument SOLIDWORKS COM member.

    With pywin32 late binding, some no-argument API members are exposed
    already evaluated (string/int/COM object), while others are Python
    callables. A returned COM dispatch object is callable too, so a generic
    `if callable(...)` test is unsafe. We first accept common evaluated
    values/dispatches; otherwise we attempt a zero-arg call.
    """
    try:
        attr = getattr(obj, name)
    except Exception:
        return default

    # Already-evaluated scalar / tuple / list / None.
    if attr is None or isinstance(attr, (str, int, float, bool, tuple, list)):
        return attr

    # A returned COM interface object has _oleobj_; do NOT call it.
    if hasattr(attr, "_oleobj_"):
        return attr

    # Normal bound method/function.
    try:
        return attr()
    except Exception:
        return default

def feature_tree(model):
    rows = []
    warnings = []

    feat = read0(model, "FirstFeature")
    if feat is None:
        warnings.append("FirstFeature could not be read.")
        return rows, warnings

    for idx in range(1, 10001):
        name = read0(feat, "Name", "<unreadable>")
        ftype = read0(feat, "GetTypeName2", "<unknown>")
        suppressed = read0(feat, "IsSuppressed", None)

        rows.append({
            "index": idx,
            "name": str(name),
            "type": str(ftype),
            "suppressed": suppressed,
        })

        nxt = read0(feat, "GetNextFeature")
        if nxt is None:
            break
        feat = nxt
    else:
        warnings.append("Feature traversal stopped at safety limit 10000.")

    return rows, warnings

def write_snapshot(data):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )

def main():
    sw = win32com.client.GetActiveObject("SldWorks.Application")

    # IMPORTANT: ActiveDoc is a COM PROPERTY.
    model = sw.ActiveDoc
    if model is None:
        raise SystemExit("FAIL: no active SOLIDWORKS document.")

    title = read0(model, "GetTitle", "<unknown>")
    path = read0(model, "GetPathName", "")
    doc_type = read0(model, "GetType", None)

    # Write minimal evidence immediately.
    snapshot = {
        "probe_revision": "v06",
        "read_only": True,
        "document": {
            "title": title,
            "path": path,
            "type": doc_type,
        },
        "feature_tree": [],
        "expected_named_objects": {},
        "warnings": [],
    }
    write_snapshot(snapshot)

    features, warnings = feature_tree(model)
    names = {row["name"] for row in features}

    snapshot["feature_tree"] = features
    snapshot["expected_named_objects"] = {
        name: (name in names) for name in EXPECTED
    }
    snapshot["warnings"] = warnings
    write_snapshot(snapshot)

    print("============================================================")
    print("K01 SOLIDWORKS API Gate 01 - v06")
    print("============================================================")
    print(f"Document: {title}")
    print(f"Path:     {path or '[UNSAVED]'}")
    print(f"Type:     {doc_type}")
    print(f"Features: {len(features)}")
    for name, ok in snapshot["expected_named_objects"].items():
        print(f"{'[PASS]' if ok else '[OPEN]'} {name}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    print(f"\nSnapshot: {OUT}")
    print("\nPASS: reliable read-only COM/FeatureManager probe completed.")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("FAIL: unhandled probe error")
        traceback.print_exc()
        sys.exit(1)
