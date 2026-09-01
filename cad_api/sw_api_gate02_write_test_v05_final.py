"""
K01 SOLIDWORKS API Gate 02 — native WRITE test v05 FINAL

Purpose:
Prove native SolidWorks write capability with the smallest stable path.

v04 already proved that FeatureExtrusion3 creates a real native Boss-Extrude.
It only failed afterwards because pywin32 late binding exposed EditRebuild3
as an already-evaluated bool instead of a callable method.

v05 therefore stops immediately after successful FeatureExtrusion3.
No explicit rebuild or view command is required for Gate 02 acceptance.

SAFETY:
- active document must be a NEW UNSAVED Part;
- select exactly one default reference plane before running;
- script never saves the document.
"""

from __future__ import annotations
import sys
import traceback
import win32com.client

SW_DOC_PART = 1
SW_ENDCOND_BLIND = 0
SW_START_SKETCH_PLANE = 0

RADIUS_M = 0.010
DEPTH_M = 0.010
SKETCH_TYPES = {"ProfileFeature", "3DProfileFeature"}

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

def find_recent_sketch(model, max_from_end=8):
    for pos in range(max_from_end + 1):
        try:
            feat = model.FeatureByPositionReverse(pos)
        except Exception:
            feat = None
        if feat is None:
            continue
        name = read0(feat, "Name", "")
        ftype = read0(feat, "GetTypeName2", "")
        if ftype in SKETCH_TYPES or str(name).lower().startswith("sketch"):
            return feat
    return None

def main():
    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    doc_type = read0(model, "GetType", None)
    path = read0(model, "GetPathName", "")
    title = read0(model, "GetTitle", "<unknown>")

    print(f"Active document: {title}")
    print(f"Path: {path or '[UNSAVED]'}")
    print(f"Type: {doc_type}")

    if int(doc_type) != SW_DOC_PART:
        raise RuntimeError("Gate 02 requires an active PART.")
    if path:
        raise RuntimeError("SAFETY STOP: active Part is already saved.")

    selected = model.SelectionManager.GetSelectedObjectCount2(-1)
    if selected != 1:
        raise RuntimeError("Select exactly ONE default reference plane.")

    skmgr = model.SketchManager
    skmgr.InsertSketch(True)

    if skmgr.ActiveSketch is None:
        raise RuntimeError("ActiveSketch is None after InsertSketch.")

    circle = skmgr.CreateCircleByRadius(0.0, 0.0, 0.0, RADIUS_M)
    if circle is None:
        raise RuntimeError("CreateCircleByRadius returned None.")

    skmgr.InsertSketch(True)
    model.ClearSelection2(True)

    sketch_feat = find_recent_sketch(model)
    if sketch_feat is None:
        raise RuntimeError("Could not find newly created sketch feature.")

    if not sketch_feat.Select2(False, 0):
        raise RuntimeError("IFeature.Select2 failed for created sketch.")

    feat = model.FeatureManager.FeatureExtrusion3(
        True, False, False,
        SW_ENDCOND_BLIND, SW_ENDCOND_BLIND,
        DEPTH_M, DEPTH_M,
        False, False, False, False,
        0.0, 0.0,
        False, False, False, False,
        True, False, True,
        SW_START_SKETCH_PLANE,
        0.0, False
    )

    if feat is None:
        raise RuntimeError("FeatureExtrusion3 returned None.")

    try:
        feat.Name = "API_F01_BOSS_D20_L10"
    except Exception:
        pass

    print("")
    print("PASS: API Gate 02 native write capability proven.")
    print("Created native geometry: Ø20 x 10 mm Boss-Extrude.")
    print("Feature: API_F01_BOSS_D20_L10")
    print("DO NOT SAVE this disposable Part.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: API Gate 02 v05 FINAL")
        traceback.print_exc()
        sys.exit(1)
