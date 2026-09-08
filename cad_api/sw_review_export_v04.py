r"""
K01 REVIEW EXPORT v04 — dimensions/equations audit

Read-only export for the ACTIVE saved SOLIDWORKS Part.

Adds to v03:
- all top-level feature names/types;
- display dimensions attached to each feature;
- raw SOLIDWORKS system value (SI/radians as returned by API);
- equation/global-variable strings when readable;
- material and solid-body count.

Purpose:
Use JSON instead of manual screenshots for geometry/interface review.

IMPORTANT:
D1@Sketch-style dimension names are review evidence only.
Release authority remains stable K01 parameter/global-variable names.
"""

from __future__ import annotations
import json, re, sys, traceback
from pathlib import Path
import win32com.client

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "review_upload"
SW_DOC_PART = 1
SW_SOLID_BODY = 0

def ensure_gitignore():
    gi = REPO_ROOT / ".gitignore"
    text = gi.read_text(encoding="utf-8", errors="ignore") if gi.exists() else ""
    lines = [x.strip() for x in text.splitlines()]
    if "review_upload/" not in lines:
        with gi.open("a", encoding="utf-8", newline="\n") as f:
            if text and not text.endswith(("\n", "\r")):
                f.write("\n")
            f.write("\n# Generated direct review exports\nreview_upload/\n")

def read_member(obj, name, *args, default=None):
    try:
        attr = getattr(obj, name)
    except Exception:
        return default
    if args:
        try:
            return attr(*args)
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

def safe_name(v):
    v = re.sub(r"\.[Ss][Ll][Dd][Pp][Rr][Tt]$", "", str(v))
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", v).strip("_") or "ACTIVE_PART"

def as_list(v):
    if v is None:
        return []
    if isinstance(v, (tuple, list)):
        return list(v)
    try:
        return list(v)
    except Exception:
        return [v]

def get_dim_value(dim):
    # Preferred late-bound property
    val = read_member(dim, "SystemValue", default=None)
    if isinstance(val, (int, float)):
        return float(val)

    # Fallback API
    try:
        val = dim.GetSystemValue3(1, None)
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, (tuple, list)):
            return list(val)
    except Exception:
        pass
    return None

def feature_dimensions(feat):
    rows = []
    try:
        disp = feat.GetFirstDisplayDimension()
    except Exception:
        disp = None

    seen = set()
    guard = 0
    while disp is not None and guard < 1000:
        guard += 1
        try:
            dim = disp.GetDimension2(0)
        except Exception:
            dim = None

        if dim is not None:
            full = read_member(dim, "FullName", default=None)
            name = read_member(dim, "Name", default=None)
            key = str(full or name or f"dim_{guard}")
            if key not in seen:
                seen.add(key)
                rows.append({
                    "name": str(name) if name is not None else None,
                    "full_name": str(full) if full is not None else None,
                    "system_value": get_dim_value(dim),
                    "type_raw": read_member(dim, "GetType", default=None),
                    "read_only": read_member(dim, "ReadOnly", default=None),
                })

        try:
            disp = feat.GetNextDisplayDimension(disp)
        except Exception:
            disp = None

    return rows

def feature_tree(model):
    rows = []
    feat = read_member(model, "FirstFeature", default=None)
    for idx in range(1, 10001):
        if feat is None:
            break
        rows.append({
            "index": idx,
            "name": str(read_member(feat, "Name", default="<unreadable>")),
            "type": str(read_member(feat, "GetTypeName2", default="<unknown>")),
            "suppressed": read_member(feat, "IsSuppressed", default=None),
            "dimensions": feature_dimensions(feat),
        })
        feat = read_member(feat, "GetNextFeature", default=None)
    return rows

def equation_dump(model):
    out = {"count": None, "items": [], "error": None}
    try:
        eq = model.GetEquationMgr
        if callable(eq):
            eq = eq()
        if eq is None:
            return out
        count = read_member(eq, "GetCount", default=None)
        if count is None:
            count = read_member(eq, "Count", default=None)
        if count is None:
            return out
        count = int(count)
        out["count"] = count
        for i in range(count):
            raw = None
            value = None
            try:
                raw = eq.Equation(i)
            except Exception:
                try:
                    raw = eq.Equation[i]
                except Exception:
                    pass
            try:
                value = eq.Value(i)
            except Exception:
                try:
                    value = eq.Value[i]
                except Exception:
                    pass
            out["items"].append({
                "index": i,
                "equation": str(raw) if raw is not None else None,
                "value": value,
            })
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out

def material_info(model):
    raw = str(read_member(model, "MaterialIdName", default="") or "")
    parts = raw.split("|")
    return {
        "raw": raw,
        "name": parts[1] if len(parts) >= 2 else (raw or None),
        "assigned": bool(raw),
    }

def main():
    ensure_gitignore()
    OUT.mkdir(parents=True, exist_ok=True)

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    title = read_member(model, "GetTitle", default="<unknown>")
    path = read_member(model, "GetPathName", default="")
    dtype = int(read_member(model, "GetType", default=0) or 0)

    if dtype != SW_DOC_PART:
        raise RuntimeError("v04 currently supports Part documents only.")
    if not path:
        raise RuntimeError("Save the native Part first.")

    name = safe_name(title)

    try:
        bodies = as_list(model.GetBodies2(SW_SOLID_BODY, False))
        body_count = len(bodies)
        body_error = None
    except Exception as exc:
        body_count = None
        body_error = f"{type(exc).__name__}: {exc}"

    payload = {
        "schema": "k01_review_export_v04",
        "document": {
            "title": title,
            "native_path": path,
            "doc_type": dtype,
        },
        "material": material_info(model),
        "solid_body_count": body_count,
        "solid_body_error": body_error,
        "equations": equation_dump(model),
        "feature_tree": feature_tree(model),
        "dimension_policy": (
            "Feature dimensions are review evidence. "
            "Release control shall use stable K01 parameter/global-variable names."
        ),
    }

    out = OUT / f"{name}_REVIEW_V04.json"
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    print("============================================================")
    print("K01 REVIEW EXPORT v04 — DIMENSIONS / EQUATIONS")
    print("============================================================")
    print(f"Part: {title}")
    print(f"JSON: {out}")
    print(f"Material: {payload['material']['name']}")
    print(f"Solid bodies: {body_count}")
    print(f"Features: {len(payload['feature_tree'])}")
    total_dims = sum(len(x['dimensions']) for x in payload['feature_tree'])
    print(f"Dimensions captured: {total_dims}")
    print("PASS: review JSON created.")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: K01 REVIEW EXPORT v04")
        traceback.print_exc()
        sys.exit(1)
