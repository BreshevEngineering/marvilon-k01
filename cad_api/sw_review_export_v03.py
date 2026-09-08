r"""
K01 REVIEW EXPORT v03

Purpose
-------
Avoid opaque ZIP handoff failures in ChatGPT/file ingestion.

For the ACTIVE saved SOLIDWORKS Part/Assembly, create directly uploadable files:
1) JSON engineering digest (routine authority for review)
2) STEP neutral geometry (only needed at geometry gates)
3) CURRENT BMP (only needed when the visual state/section matters)

Outputs are written to:
    <repo>\review_upload\

The script also adds `review_upload/` to .gitignore if missing.
It does not modify native CAD geometry.
"""

from __future__ import annotations
import json, re, sys, traceback
from pathlib import Path
import win32com.client

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "review_upload"
SW_DOC_PART = 1
SW_DOC_ASSEMBLY = 2
SW_SOLID_BODY = 0

def ensure_gitignore():
    gi = REPO_ROOT / ".gitignore"
    text = gi.read_text(encoding="utf-8", errors="ignore") if gi.exists() else ""
    if "review_upload/" not in [x.strip() for x in text.splitlines()]:
        with gi.open("a", encoding="utf-8", newline="\n") as f:
            if text and not text.endswith(("\n", "\r")):
                f.write("\n")
            f.write("\n# Generated direct review exports\nreview_upload/\n")

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

def safe_name(v):
    v = re.sub(r"\.[Ss][Ll][Dd](?:[Pp][Rr][Tt]|[Aa][Ss][Mm])$", "", str(v))
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", v).strip("_")

def as_list(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return list(v)
    try:
        return list(v)
    except Exception:
        return [v]

def feature_tree(model):
    out = []
    feat = read0(model, "FirstFeature")
    for i in range(1, 10001):
        if feat is None:
            break
        out.append({
            "index": i,
            "name": str(read0(feat, "Name", "<unreadable>")),
            "type": str(read0(feat, "GetTypeName2", "<unknown>")),
            "suppressed": read0(feat, "IsSuppressed", None),
        })
        feat = read0(feat, "GetNextFeature")
    return out

def material(model):
    raw = str(read0(model, "MaterialIdName", "") or "")
    parts = raw.split("|")
    return {
        "raw": raw,
        "name": parts[1] if len(parts) >= 2 else (raw or None),
        "assigned": bool(raw),
    }

def body_count(model):
    try:
        return len(as_list(model.GetBodies2(SW_SOLID_BODY, False)))
    except Exception:
        return None

def components(model):
    rows = []
    try:
        comps = as_list(model.GetComponents(False))
    except Exception:
        return rows
    for c in comps:
        try: name = c.Name2
        except Exception: name = "<unknown>"
        try: path = c.GetPathName()
        except Exception: path = ""
        try: sup = c.IsSuppressed()
        except Exception: sup = None
        rows.append({"name": str(name), "path": str(path), "suppressed": sup})
    return rows

def main():
    ensure_gitignore()
    OUT.mkdir(parents=True, exist_ok=True)

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    title = read0(model, "GetTitle", "<unknown>")
    path = read0(model, "GetPathName", "")
    dtype = int(read0(model, "GetType", 0) or 0)
    if not path:
        raise RuntimeError("Save the native document first.")

    name = safe_name(title)

    digest = {
        "schema": "k01_review_export_v03",
        "document": {"title": title, "native_path": path, "doc_type": dtype},
        "feature_tree": feature_tree(model),
    }

    if dtype == SW_DOC_PART:
        digest["material"] = material(model)
        digest["solid_body_count"] = body_count(model)
    elif dtype == SW_DOC_ASSEMBLY:
        digest["components"] = components(model)

    json_path = OUT / f"{name}_REVIEW.json"
    json_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    step_path = OUT / f"{name}_REVIEW.STEP"
    step_result = None
    step_error = None
    try:
        model.ClearSelection2(True)
        step_result = model.SaveAs3(str(step_path), 0, 1)
    except Exception as exc:
        step_error = f"{type(exc).__name__}: {exc}"

    bmp_path = OUT / f"{name}_CURRENT.bmp"
    bmp_result = None
    bmp_error = None
    try:
        bmp_result = bool(model.SaveBMP(str(bmp_path), 1600, 1200))
    except Exception as exc:
        bmp_error = f"{type(exc).__name__}: {exc}"

    status = {
        "json": str(json_path),
        "step": {"path": str(step_path), "exists": step_path.exists(), "api_result": step_result, "error": step_error},
        "bmp": {"path": str(bmp_path), "exists": bmp_path.exists(), "api_result": bmp_result, "error": bmp_error},
    }
    (OUT / "LAST_EXPORT_STATUS.json").write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")

    print("============================================================")
    print("K01 REVIEW EXPORT v03")
    print("============================================================")
    print("Routine upload:")
    print(f"  {json_path}")
    print("Geometry gate additionally:")
    print(f"  {step_path}")
    print("Visual/section evidence additionally:")
    print(f"  {bmp_path}")
    print("PASS: direct review files created (no ZIP).")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: K01 REVIEW EXPORT v03")
        traceback.print_exc()
        sys.exit(1)
