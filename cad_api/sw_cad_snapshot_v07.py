"""
K01 SOLIDWORKS API — generic read-only CAD snapshot v07

Use on any saved K01 native Part.
Writes one document-specific JSON file, so P003/P016 snapshots do not overwrite
each other.

Output example:
    reports/CAD_SNAPSHOT_K01-P-003_Cartridge_Body.json

Read-only: does not modify or save the CAD document.
"""

from __future__ import annotations
import json
import re
import sys
import traceback
from pathlib import Path
import win32com.client

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DATUMS = ("K01_DATUM_A_MATING", "K01_DATUM_B_AXIS")

def read0(obj, name, default=None):
    try:
        attr = getattr(obj, name)
    except Exception:
        return default
    if attr is None or isinstance(attr, (str, int, float, bool, tuple, list)):
        return attr
    if hasattr(attr, "_oleobj_"):
        return attr
    try:
        return attr()
    except Exception:
        return default

def safe_name(title):
    base = re.sub(r"\.[Ss][Ll][Dd][Pp][Rr][Tt]$", "", str(title))
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", base).strip("_") or "ACTIVE_PART"

def feature_tree(model):
    rows = []
    feat = read0(model, "FirstFeature")
    for idx in range(1, 10001):
        if feat is None:
            break
        rows.append({
            "index": idx,
            "name": str(read0(feat, "Name", "<unreadable>")),
            "type": str(read0(feat, "GetTypeName2", "<unknown>")),
            "suppressed": read0(feat, "IsSuppressed", None),
        })
        feat = read0(feat, "GetNextFeature")
    return rows

def main():
    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    title = read0(model, "GetTitle", "<unknown>")
    path = read0(model, "GetPathName", "")
    doc_type = read0(model, "GetType", None)
    features = feature_tree(model)
    names = {row["name"] for row in features}

    snapshot = {
        "schema": "k01_cad_snapshot_v1",
        "probe_revision": "v07",
        "read_only": True,
        "document": {
            "title": title,
            "path": path,
            "type": doc_type,
        },
        "feature_count": len(features),
        "feature_tree": features,
        "controlled_objects": {
            name: {"present": name in names} for name in EXPECTED_DATUMS
        }
    }

    out = REPO_ROOT / "reports" / f"CAD_SNAPSHOT_{safe_name(title)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("============================================================")
    print("K01 generic CAD snapshot v07")
    print("============================================================")
    print(f"Document: {title}")
    print(f"Path:     {path or '[UNSAVED]'}")
    print(f"Features: {len(features)}")
    for name in EXPECTED_DATUMS:
        print(f"{'[PASS]' if name in names else '[OPEN]'} {name}")
    print(f"Snapshot: {out}")
    print("PASS: read-only CAD snapshot written.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: generic CAD snapshot")
        traceback.print_exc()
        sys.exit(1)
