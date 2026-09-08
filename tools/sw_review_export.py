r"""
K01 SOLIDWORKS fast CAD snapshot exporter.

Stable filename. Git stores history.

Active document:
- Part     -> export that Part.
- Assembly -> export all unique resolved child Parts.

Writes stable text snapshots to:
    reports/cad/current/<part>.json

Checks/extracts:
- native SLDPRT SHA-256
- material
- solid body count
- custom properties
- external EquationMgr link/path
- recursive feature/subfeature tree
- display dimensions with type + SI + mm/deg conversions

Read-only with respect to model geometry.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import traceback
from pathlib import Path
from typing import Any

import pythoncom
import win32com.client

from sw_com import as_list, call, member0, value0


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = REPO_ROOT / "reports" / "cad" / "current"

SW_DOC_PART = 1
SW_DOC_ASSEMBLY = 2
SW_SOLID_BODY = 0
SW_DISPLAY_FEATURE_DIMENSIONS = 32

# swDimensionParamType_e. We only use it to avoid treating angular values as mm.
ANGULAR_TYPES = {3, 16}


def safe_name(title: str) -> str:
    name = re.sub(r"\.(SLDPRT|SLDASM)$", "", str(title), flags=re.I)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "ACTIVE_MODEL"


def file_fingerprint(path: str) -> dict[str, Any]:
    out = {
        "path": path,
        "exists": False,
        "size_bytes": None,
        "mtime_ns": None,
        "sha256": None,
        "error": None,
    }
    try:
        p = Path(path)
        st = p.stat()
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        out.update(
            exists=True,
            size_bytes=st.st_size,
            mtime_ns=st.st_mtime_ns,
            sha256=h.hexdigest(),
        )
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def material_info(model) -> dict:
    raw, err = member0(model, "MaterialIdName", default="")
    raw = str(raw or "")
    parts = raw.split("|")
    return {
        "raw": raw,
        "name": parts[1] if len(parts) >= 2 else (raw or None),
        "assigned": bool(raw),
        "errors": [err] if err else [],
    }


def body_info(model) -> dict:
    bodies, err = call(model, "GetBodies2", SW_SOLID_BODY, False, default=None)
    if err:
        return {"solid_body_count": None, "errors": [err]}
    return {"solid_body_count": len(as_list(bodies)), "errors": []}


def custom_properties(model) -> dict:
    out = {"values": {}, "errors": []}

    ext, err = member0(model, "Extension")
    if err or ext is None:
        out["errors"].append(err or "Extension returned None")
        return out

    mgr, err = call(ext, "CustomPropertyManager", "", default=None)
    if err or mgr is None:
        out["errors"].append(err or "CustomPropertyManager returned None")
        return out

    names, err = member0(mgr, "GetNames", default=None)
    if err:
        out["errors"].append(err)
    names = as_list(names)

    for name in names:
        if not name:
            continue
        rec = {"raw": None, "resolved": None, "error": None}
        got, e = call(mgr, "Get6", str(name), False, default=None)
        if e:
            rec["error"] = e
        elif isinstance(got, (tuple, list)):
            if len(got) >= 3:
                rec["raw"] = got[1]
                rec["resolved"] = got[2]
        else:
            rec["raw"] = got
        out["values"][str(name)] = rec

    return out


def equation_dump(model) -> dict:
    out = {
        "available": False,
        "count": None,
        "link_to_file": None,
        "file_path": None,
        "items": [],
        "errors": [],
    }

    eq, err = member0(model, "GetEquationMgr", default=None)
    if err or eq is None:
        out["errors"].append(err or "GetEquationMgr returned None")
        return out

    out["available"] = True

    linked, e = member0(eq, "LinkToFile", default=None)
    if e:
        out["errors"].append(e)
    else:
        out["link_to_file"] = bool(linked) if linked is not None else None

    fpath, e = member0(eq, "FilePath", default=None)
    if e:
        out["errors"].append(e)
    else:
        out["file_path"] = str(fpath or "")

    count, e = member0(eq, "GetCount", default=None)
    if e or count is None:
        count2, e2 = member0(eq, "Count", default=None)
        if count2 is None:
            if e:
                out["errors"].append(e)
            if e2:
                out["errors"].append(e2)
            return out
        count = count2

    try:
        count = int(count)
    except Exception as exc:
        out["errors"].append(f"equation count conversion: {exc}")
        return out

    out["count"] = count

    for i in range(count):
        rec = {"index": i, "equation": None, "value_SI": None, "errors": []}

        # Indexed COM properties vary under late binding.
        try:
            rec["equation"] = str(eq.Equation(i))
        except Exception as exc1:
            try:
                rec["equation"] = str(eq.Equation[i])
            except Exception as exc2:
                rec["errors"].append(
                    f"Equation[{i}]: {type(exc1).__name__}: {exc1}; "
                    f"fallback: {type(exc2).__name__}: {exc2}"
                )

        try:
            rec["value_SI"] = eq.Value(i)
        except Exception as exc1:
            try:
                rec["value_SI"] = eq.Value[i]
            except Exception as exc2:
                rec["errors"].append(
                    f"Value[{i}]: {type(exc1).__name__}: {exc1}; "
                    f"fallback: {type(exc2).__name__}: {exc2}"
                )

        out["items"].append(rec)

    return out


def set_dimension_display(model) -> dict:
    state = {"old": None, "errors": []}

    old, e = call(
        model, "GetUserPreferenceToggle", SW_DISPLAY_FEATURE_DIMENSIONS,
        default=None,
    )
    if e:
        state["errors"].append(e)
    else:
        state["old"] = bool(old) if old is not None else None

    _, e = call(
        model, "SetUserPreferenceToggle",
        SW_DISPLAY_FEATURE_DIMENSIONS, True, default=None,
    )
    if e:
        state["errors"].append(e)
        # Compatibility fallback.
        _, e2 = member0(model, "ShowFeatureDimensions", default=None)
        if e2:
            state["errors"].append(e2)

    return state


def restore_dimension_display(model, state: dict):
    if state.get("old") is None:
        return
    call(
        model, "SetUserPreferenceToggle",
        SW_DISPLAY_FEATURE_DIMENSIONS, bool(state["old"]), default=None,
    )


def dimension_record(display_dim) -> dict:
    rec = {
        "name": None,
        "full_name": None,
        "type_raw": None,
        "system_value_SI": None,
        "value_mm": None,
        "value_deg": None,
        "errors": [],
    }

    dim, e = call(display_dim, "GetDimension2", 0, default=None)
    if e or dim is None:
        rec["errors"].append(e or "GetDimension2 returned None")
        return rec

    for field, member_name in (("name", "Name"), ("full_name", "FullName")):
        v, e = member0(dim, member_name, default=None)
        if e:
            rec["errors"].append(e)
        elif v is not None:
            rec[field] = str(v)

    dtype, e = member0(dim, "GetType", default=None)
    if e:
        rec["errors"].append(e)
    elif dtype is not None:
        try:
            rec["type_raw"] = int(dtype)
        except Exception as exc:
            rec["errors"].append(f"GetType conversion: {exc}")

    value, e = member0(dim, "SystemValue", default=None)
    if e or not isinstance(value, (int, float)):
        # Fallback with args.
        value2, e2 = call(dim, "GetSystemValue3", 1, None, default=None)
        if isinstance(value2, (int, float)):
            value = value2
        elif e2:
            rec["errors"].append(e2)
        if e:
            rec["errors"].append(e)

    if isinstance(value, (int, float)):
        value = float(value)
        rec["system_value_SI"] = value
        if rec["type_raw"] in ANGULAR_TYPES:
            rec["value_deg"] = math.degrees(value)
        else:
            rec["value_mm"] = value * 1000.0

    return rec


def feature_dimensions(feat) -> tuple[list[dict], list[str]]:
    rows = []
    errors = []

    disp, e = member0(feat, "GetFirstDisplayDimension", default=None)
    if e:
        errors.append(e)

    seen = set()
    guard = 0

    while disp is not None and guard < 5000:
        guard += 1
        rec = dimension_record(disp)
        key = rec.get("full_name") or rec.get("name") or f"unnamed_{guard}"
        if key not in seen:
            seen.add(key)
            rows.append(rec)

        disp, e = call(feat, "GetNextDisplayDimension", disp, default=None)
        if e:
            errors.append(e)
            break

    if guard >= 5000:
        errors.append("display-dimension traversal guard reached")

    return rows, errors


def feature_node(feat, path: str, depth: int = 0) -> dict:
    node = {
        "path": path,
        "name": None,
        "type": None,
        "suppressed": None,
        "dimensions": [],
        "subfeatures": [],
        "errors": [],
    }

    name, e = member0(feat, "Name", default=None)
    if e:
        node["errors"].append(e)
    node["name"] = str(name) if name is not None else None

    ftype, e = member0(feat, "GetTypeName2", default=None)
    if e:
        node["errors"].append(e)
    node["type"] = str(ftype) if ftype is not None else None

    sup, e = member0(feat, "IsSuppressed", default=None)
    if e:
        node["errors"].append(e)
    node["suppressed"] = bool(sup) if sup is not None else None

    dims, errors = feature_dimensions(feat)
    node["dimensions"] = dims
    node["errors"].extend(errors)

    if depth >= 32:
        node["errors"].append("subfeature recursion depth limit reached")
        return node

    sub, e = member0(feat, "GetFirstSubFeature", default=None)
    if e:
        node["errors"].append(e)

    count = 0
    while sub is not None and count < 5000:
        count += 1
        sname = value0(sub, "Name", default=f"sub_{count}")
        node["subfeatures"].append(
            feature_node(sub, f"{path}/{sname}", depth + 1)
        )

        # SOLIDWORKS pattern: the current subfeature returns the next sibling.
        sub, e = member0(sub, "GetNextSubFeature", default=None)
        if e:
            node["errors"].append(e)
            break

    if count >= 5000:
        node["errors"].append("subfeature traversal guard reached")

    return node


def feature_tree(model) -> dict:
    out = {"features": [], "errors": []}

    feat, e = member0(model, "FirstFeature", default=None)
    if e:
        out["errors"].append(e)

    guard = 0
    while feat is not None and guard < 10000:
        guard += 1
        name = value0(feat, "Name", default=f"feature_{guard}")
        out["features"].append(feature_node(feat, str(name)))

        feat, e = member0(feat, "GetNextFeature", default=None)
        if e:
            out["errors"].append(e)
            break

    if guard >= 10000:
        out["errors"].append("top-level feature traversal guard reached")

    return out


def count_dims(nodes: list[dict]) -> int:
    total = 0
    for n in nodes:
        total += len(n.get("dimensions", []))
        total += count_dims(n.get("subfeatures", []))
    return total


def export_part(model) -> tuple[Path | None, dict]:
    title, e_title = member0(model, "GetTitle", default=None)
    path, e_path = member0(model, "GetPathName", default=None)
    dtype, e_type = member0(model, "GetType", default=None)

    payload = {
        "schema": "k01_sw_review_export_2",
        "export_status": "FAIL",
        "document": {
            "title": str(title) if title is not None else None,
            "native_path": str(path) if path is not None else None,
            "doc_type": int(dtype) if isinstance(dtype, (int, float)) else dtype,
        },
        "source_file": file_fingerprint(str(path or "")),
        "material": {},
        "body": {},
        "custom_properties": {},
        "equations": {},
        "feature_tree": {},
        "summary": {},
        "errors": [x for x in (e_title, e_path, e_type) if x],
    }

    if payload["document"]["doc_type"] != SW_DOC_PART:
        payload["errors"].append(
            f"expected Part doc_type=1, got {payload['document']['doc_type']}"
        )
        return None, payload

    if not path:
        payload["errors"].append("part must be saved before export")
        return None, payload

    display_state = set_dimension_display(model)
    payload["errors"].extend(display_state["errors"])

    try:
        payload["material"] = material_info(model)
        payload["body"] = body_info(model)
        payload["custom_properties"] = custom_properties(model)
        payload["equations"] = equation_dump(model)
        payload["feature_tree"] = feature_tree(model)
    finally:
        restore_dimension_display(model, display_state)

    total_dims = count_dims(payload["feature_tree"].get("features", []))
    payload["summary"] = {
        "dimension_count": total_dims,
        "top_level_feature_count": len(
            payload["feature_tree"].get("features", [])
        ),
    }

    # Top-level export failures are kept separate from local feature/member
    # errors; the latter are evidence for the audit rather than hidden.
    payload["export_status"] = (
        "PASS" if not payload["errors"] else "PASS_WITH_WARNINGS"
    )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"{safe_name(str(title or Path(path).stem))}.json"
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return out, payload


def assembly_part_models(assembly) -> tuple[list[tuple[str, object]], list[str]]:
    errors = []
    comps, e = call(assembly, "GetComponents", False, default=None)
    if e:
        return [], [e]

    result = []
    seen = set()

    for comp in as_list(comps):
        suppressed, e = member0(comp, "IsSuppressed", default=False)
        if e:
            errors.append(e)
        if bool(suppressed):
            continue

        path, e = member0(comp, "GetPathName", default="")
        if e:
            errors.append(e)
        path = str(path or "")
        if not path.lower().endswith(".sldprt"):
            continue

        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)

        model, e = member0(comp, "GetModelDoc2", default=None)
        if e:
            errors.append(e)

        if model is None:
            errors.append(
                f"{path}: GetModelDoc2 returned None; resolve/open component"
            )
            continue

        result.append((path, model))

    return result, errors


def main() -> int:
    pythoncom.CoInitialize()

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    active = sw.ActiveDoc
    if active is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    dtype, e = member0(active, "GetType", default=None)
    if e:
        raise RuntimeError(e)

    exported = []
    warnings = []

    if int(dtype) == SW_DOC_PART:
        out, payload = export_part(active)
        if out:
            exported.append(str(out))
        else:
            warnings.extend(payload.get("errors", []))

    elif int(dtype) == SW_DOC_ASSEMBLY:
        parts, errors = assembly_part_models(active)
        warnings.extend(errors)

        for path, model in parts:
            out, payload = export_part(model)
            if out:
                exported.append(str(out))
            else:
                warnings.extend(payload.get("errors", []))

        atitle = value0(active, "GetTitle", default="K01_ASSEMBLY")
        apath = value0(active, "GetPathName", default="")
        manifest = {
            "schema": "k01_sw_review_export_assembly_manifest_2",
            "assembly": {
                "title": str(atitle),
                "native_path": str(apath),
            },
            "part_snapshots": exported,
            "warnings": warnings,
        }
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        mp = REPORT_DIR / f"{safe_name(str(atitle))}_ASSEMBLY_MANIFEST.json"
        mp.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    else:
        raise RuntimeError(f"unsupported active document type: {dtype}")

    print("=" * 60)
    print("K01 SOLIDWORKS FAST CAD SNAPSHOT")
    print("=" * 60)
    print(f"Active doc type: {dtype}")
    print(f"Part snapshots:  {len(exported)}")
    for p in exported:
        print(f"  PASS  {p}")
    for w in warnings:
        print(f"  WARN  {w}")

    if not exported:
        print("FAIL: no part snapshots produced.")
        return 1

    print("PASS: CAD snapshot export completed.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: K01 SOLIDWORKS fast CAD snapshot")
        traceback.print_exc()
        sys.exit(1)
