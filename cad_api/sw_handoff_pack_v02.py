r"""
K01 ENGINEERING HANDOFF PACK v02

One-command review package for the ACTIVE saved SOLIDWORKS Part or Assembly.

Compared with v01:
- automatically ensures `handoff/` is present in repository `.gitignore`;
- fixes the Python docstring escape warning;
- captures feature-tree dimensions for review (names are NOT release-stable);
- captures material and solid-body count for Parts;
- captures assembly components for Assemblies;
- exports STEP;
- saves CURRENT + Front/Right/Top/Isometric BMP views;
- writes MANIFEST.json;
- creates one ZIP ready to upload.

IMPORTANT:
Dimension names like D1@Sketch1 are included only as review evidence.
Release control must use stable K01 parameters/global-variable names.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
import zipfile
from datetime import datetime
from pathlib import Path

import win32com.client

REPO_ROOT = Path(__file__).resolve().parents[1]

SW_DOC_PART = 1
SW_DOC_ASSEMBLY = 2
SW_SOLID_BODY = 0

STANDARD_VIEWS = {
    "FRONT": 1,
    "RIGHT": 4,
    "TOP": 5,
    "ISO": 7,
}

IMAGE_W = 1600
IMAGE_H = 1200


def ensure_gitignore():
    gi = REPO_ROOT / ".gitignore"
    current = gi.read_text(encoding="utf-8", errors="ignore") if gi.exists() else ""
    lines = [line.strip() for line in current.splitlines()]
    changed = False
    if "handoff/" not in lines:
        with gi.open("a", encoding="utf-8", newline="\n") as f:
            if current and not current.endswith(("\n", "\r")):
                f.write("\n")
            f.write("\n# Generated engineering handoff packages\nhandoff/\n")
        changed = True
    return changed


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


def safe_name(value):
    value = str(value or "ACTIVE_MODEL")
    value = re.sub(r"\.[Ss][Ll][Dd](?:[Pp][Rr][Tt]|[Aa][Ss][Mm])$", "", value)
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return value.strip("_") or "ACTIVE_MODEL"


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        return list(value)
    except Exception:
        return [value]


def dimension_value(dim):
    # Late-bound COM can expose this as a property or method depending on member.
    raw = read0(dim, "SystemValue", None)
    if isinstance(raw, (int, float)):
        return float(raw)

    # Fallback to GetSystemValue3 if available.
    try:
        value = dim.GetSystemValue3(1, None)
        if isinstance(value, (tuple, list)):
            return list(value)
        if isinstance(value, (int, float)):
            return float(value)
    except Exception:
        pass

    return None


def feature_dimensions(feat):
    rows = []
    try:
        disp = feat.GetFirstDisplayDimension()
    except Exception:
        disp = None

    guard = 0
    while disp is not None and guard < 1000:
        guard += 1
        try:
            dim = disp.GetDimension2(0)
        except Exception:
            dim = None

        if dim is not None:
            name = read0(dim, "FullName", None) or read0(dim, "Name", None)
            value = dimension_value(dim)
            rows.append({
                "name": str(name) if name else None,
                "system_value_SI": value,
                # This convenience conversion is only for likely linear dims.
                # Do not use it as release authority for angular dimensions.
                "value_mm_if_linear": value * 1000.0 if isinstance(value, (int, float)) else None,
            })

        try:
            disp = feat.GetNextDisplayDimension(disp)
        except Exception:
            disp = None

    return rows


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
            "dimensions": feature_dimensions(feat),
        })
        feat = read0(feat, "GetNextFeature")
    return rows


def material_info(model):
    raw_id = str(read0(model, "MaterialIdName", "") or "")
    raw_user = read0(model, "MaterialUserName", "")
    parts = raw_id.split("|")
    return {
        "id_raw": raw_id,
        "database": parts[0] if len(parts) >= 2 else None,
        "name": parts[1] if len(parts) >= 2 else (raw_id or None),
        "database_id": parts[2] if len(parts) >= 3 else None,
        "user_raw": raw_user,
        "assigned": bool(raw_id),
    }


def part_body_count(model):
    try:
        return len(as_list(model.GetBodies2(SW_SOLID_BODY, False))), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def assembly_components(model):
    out = []
    try:
        comps = as_list(model.GetComponents(False))
    except Exception as exc:
        return out, f"{type(exc).__name__}: {exc}"

    for comp in comps:
        try:
            name2 = comp.Name2
        except Exception:
            name2 = "<unknown>"
        try:
            path = comp.GetPathName()
        except Exception:
            path = ""
        try:
            suppressed = comp.IsSuppressed()
        except Exception:
            suppressed = None

        out.append({
            "name": str(name2),
            "path": str(path),
            "suppressed": suppressed,
        })

    return out, None


def save_bmp(model, path):
    try:
        ok = model.SaveBMP(str(path), IMAGE_W, IMAGE_H)
        return bool(ok), None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def show_view(model, view_id):
    try:
        model.ShowNamedView2("", view_id)
        return True, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def export_step(model, step_path):
    try:
        model.ClearSelection2(True)
    except Exception:
        pass

    try:
        result = model.SaveAs3(str(step_path), 0, 1)
        return result, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def main():
    gitignore_changed = ensure_gitignore()

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    title = read0(model, "GetTitle", "<unknown>")
    native_path = read0(model, "GetPathName", "")
    doc_type = int(read0(model, "GetType", 0) or 0)

    if not native_path:
        raise RuntimeError("Save the native Part/Assembly first, then run HANDOFF PACK.")

    model_name = safe_name(title)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = REPO_ROOT / "handoff" / f"{model_name}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": "k01_handoff_pack_v02",
        "created_local": datetime.now().isoformat(timespec="seconds"),
        "gitignore_handoff_added_this_run": gitignore_changed,
        "document": {
            "title": title,
            "native_path": native_path,
            "doc_type": doc_type,
        },
        "outputs": {},
        "warnings": [],
    }

    current_bmp = out_dir / f"{model_name}_CURRENT.bmp"
    ok, err = save_bmp(model, current_bmp)
    manifest["outputs"]["current_view_bmp"] = {
        "path": current_bmp.name,
        "ok": ok,
        "error": err,
    }

    features = feature_tree(model)
    audit = {
        "schema": "k01_cad_audit_handoff_v02",
        "document": {
            "title": title,
            "native_path": native_path,
            "doc_type": doc_type,
        },
        "feature_count": len(features),
        "feature_tree": features,
        "dimension_note": (
            "D1@Sketch-style names are review-only. "
            "Release authority remains stable K01 parameters/global variables."
        ),
    }

    if doc_type == SW_DOC_PART:
        audit["material"] = material_info(model)
        count, body_err = part_body_count(model)
        audit["solid_body_count"] = count
        audit["solid_body_error"] = body_err

    elif doc_type == SW_DOC_ASSEMBLY:
        comps, comp_err = assembly_components(model)
        audit["components"] = comps
        audit["component_count"] = len(comps)
        audit["component_error"] = comp_err

    audit_path = out_dir / f"{model_name}_CAD_AUDIT.json"
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    manifest["outputs"]["cad_audit"] = audit_path.name

    step_path = out_dir / f"{model_name}.STEP"
    step_result, step_err = export_step(model, step_path)
    manifest["outputs"]["step"] = {
        "path": step_path.name,
        "exists": step_path.exists(),
        "api_result": step_result,
        "error": step_err,
    }

    view_results = {}
    for label, view_id in STANDARD_VIEWS.items():
        shown, show_err = show_view(model, view_id)
        bmp_path = out_dir / f"{model_name}_{label}.bmp"
        saved, save_err = save_bmp(model, bmp_path) if shown else (False, None)
        view_results[label] = {
            "show_ok": shown,
            "show_error": show_err,
            "save_ok": saved,
            "save_error": save_err,
            "path": bmp_path.name,
        }

    manifest["outputs"]["views"] = view_results

    try:
        model.ShowNamedView2("", 7)
    except Exception:
        pass

    manifest_path = out_dir / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    zip_path = out_dir / f"{model_name}_HANDOFF.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in out_dir.iterdir():
            if item.is_file() and item != zip_path:
                zf.write(item, arcname=item.name)

    print("============================================================")
    print("K01 ENGINEERING HANDOFF PACK v02")
    print("============================================================")
    print(f"Document: {title}")
    print(f"ZIP:      {zip_path}")
    print(f".gitignore handoff/ added now: {gitignore_changed}")
    print("")
    print("Upload ONLY this ZIP for routine engineering review.")
    print("PASS: handoff package created.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: K01 handoff pack v02")
        traceback.print_exc()
        sys.exit(1)
