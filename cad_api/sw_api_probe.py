\
"""
K01 SolidWorks API capability probe.

Safe first test:
- connects to a running SOLIDWORKS instance;
- reads the active document;
- exports feature-tree metadata and model bounding box;
- does NOT edit geometry.

Requirements on Windows:
    pip install pywin32

Run:
    python sw_api_probe.py

Open a K01 part in SOLIDWORKS before running.
"""
from __future__ import annotations
import json
from pathlib import Path
import win32com.client

OUT = Path(__file__).resolve().parents[1] / "reports" / "CAD_SNAPSHOT_probe.json"

def feature_tree(model):
    rows = []
    feat = model.FirstFeature()
    while feat is not None:
        try:
            rows.append({
                "name": feat.Name,
                "type": feat.GetTypeName2(),
                "suppressed": bool(feat.IsSuppressed()),
            })
        except Exception as exc:
            rows.append({"name": "<unreadable>", "error": str(exc)})
        feat = feat.GetNextFeature()
    return rows

def main():
    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise SystemExit("Open a K01 part in SOLIDWORKS first.")

    ext = model.Extension
    box = ext.GetBox(0)  # metres: xmin,ymin,zmin,xmax,ymax,zmax
    snapshot = {
        "title": model.GetTitle(),
        "path": model.GetPathName(),
        "doc_type": model.GetType(),
        "bbox_m": list(box) if box is not None else None,
        "feature_tree": feature_tree(model),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"PASS: SolidWorks COM read connection works.")
    print(f"Snapshot: {OUT}")
    print(f"Features read: {len(snapshot['feature_tree'])}")

if __name__ == "__main__":
    main()
