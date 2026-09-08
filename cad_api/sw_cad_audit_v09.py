"""
K01 SOLIDWORKS API — native CAD audit v09

Fix versus v08:
- v08 printed MaterialUserName first. In the user's pywin32 environment this
  returned the appearance/texture label ("texture") for custom materials.
- v09 treats IPartDoc.MaterialIdName as the authoritative material identifier.
  SOLIDWORKS documents MaterialIdName as:
      DATABASE | MATERIAL NAME | DATABASE ID
- MaterialUserName remains captured only as auxiliary raw data.

Read-only.
"""

from __future__ import annotations
import json, re, sys, traceback
from pathlib import Path
import win32com.client

REPO_ROOT = Path(__file__).resolve().parents[1]
SW_DOC_PART = 1
SW_SOLID_BODY = 0

DATUMS_BY_PART = {
    "K01-P-003_Cartridge_Body": ["K01_DATUM_A_MATING", "K01_DATUM_B_AXIS"],
    "K01-P-016_Long_Run_Interface_Boss": ["K01_DATUM_A_MATING", "K01_DATUM_B_AXIS"],
}

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

def as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    try:
        return list(v)
    except Exception:
        return [v]

def parse_material_id(raw):
    raw = str(raw or "")
    parts = raw.split("|")
    if len(parts) >= 2:
        return {
            "raw": raw,
            "database": parts[0],
            "name": parts[1],
            "database_id": parts[2] if len(parts) >= 3 else None,
            "assigned": True,
        }
    return {
        "raw": raw,
        "database": None,
        "name": raw or None,
        "database_id": None,
        "assigned": bool(raw),
    }

def main():
    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    title = read0(model, "GetTitle", "<unknown>")
    path = read0(model, "GetPathName", "")
    doc_type = read0(model, "GetType", None)
    if int(doc_type) != SW_DOC_PART:
        raise RuntimeError("v09 audit currently supports Part documents only.")

    part_key = safe_name(title)
    features = feature_tree(model)
    names = {r["name"] for r in features}

    raw_id = read0(model, "MaterialIdName", "")
    raw_user = read0(model, "MaterialUserName", "")
    material = parse_material_id(raw_id)
    material["user_name_raw"] = raw_user

    try:
        bodies = as_list(model.GetBodies2(SW_SOLID_BODY, False))
        solid_body_count = len(bodies)
        body_error = None
    except Exception as exc:
        solid_body_count = None
        body_error = f"{type(exc).__name__}: {exc}"

    required_datums = DATUMS_BY_PART.get(part_key, [])
    datum_status = {d: (d in names) for d in required_datums}

    snapshot = {
        "schema": "k01_cad_audit_v09",
        "read_only": True,
        "document": {
            "title": title,
            "part_key": part_key,
            "path": path,
            "type": doc_type,
        },
        "material": material,
        "solid_body_count": solid_body_count,
        "solid_body_error": body_error,
        "feature_count": len(features),
        "feature_tree": features,
        "required_datums": datum_status,
        "dimension_audit": {
            "status": "DEFERRED_UNTIL_STABLE_K01_VARIABLE_NAMES",
            "reason": "Use stable K01 variable/equation names, not D1@Sketch identifiers."
        }
    }

    out = REPO_ROOT / "reports" / f"CAD_AUDIT_{part_key}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("============================================================")
    print("K01 native CAD audit v09")
    print("============================================================")
    print(f"Part:         {part_key}")
    print(f"Material ID:  {material['raw'] or '[OPEN / NOT ASSIGNED]'}")
    print(f"Material:     {material['name'] or '[OPEN / NOT ASSIGNED]'}")
    print(f"User raw:     {raw_user or '[blank]'}")
    print(f"Solid body:   {solid_body_count}")
    for d, ok in datum_status.items():
        print(f"{'[PASS]' if ok else '[OPEN]'} {d}")
    print(f"Features:     {len(features)}")
    print(f"Audit JSON:   {out}")
    print("PASS: read-only CAD audit written.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: K01 CAD audit v09")
        traceback.print_exc()
        sys.exit(1)
