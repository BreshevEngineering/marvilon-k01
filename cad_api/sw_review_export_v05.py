r"""
K01 REVIEW EXPORT v05 — native dimensions + BREP geometry fingerprint

Purpose
-------
Create a compact, read-only engineering review JSON from the ACTIVE saved
SOLIDWORKS Part. v05 is designed to remove the need for routine screenshots.

Compared with v04 it fixes two weak points:
1) Feature dimensions are explicitly shown before IFeature display-dimension
   traversal (SOLIDWORKS requires this).
2) Geometry is also read directly from the BREP body, so review does not
   depend on sketch dimension visibility.

Output includes:
- material;
- FeatureManager tree;
- feature display dimensions;
- equations/global variables when accessible;
- body bounding box;
- cylindrical face diameters and axes;
- inferred principal revolved axis;
- unique axial geometry stations from vertices;
- planar-face axial stations;
- basic custom properties.

Geometry is NEVER modified. The only temporary document-display change is
showing feature dimensions; the original preference is restored when possible.

Release rule
------------
D1@Sketch-style names are evidence only.
Stable K01 master/global-variable names remain release authority.
"""

from __future__ import annotations

import json
import math
import re
import sys
import traceback
from collections import Counter
from pathlib import Path

import pythoncom
import win32com.client

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "review_upload"

SW_DOC_PART = 1
SW_SOLID_BODY = 0

# Historical/current SOLIDWORKS enum value. We prefer constants from generated
# COM support when available; this value is only the compatibility fallback.
SW_DISPLAY_FEATURE_DIMENSIONS_FALLBACK = 32


def ensure_gitignore():
    gi = REPO_ROOT / ".gitignore"
    text = gi.read_text(encoding="utf-8", errors="ignore") if gi.exists() else ""
    normalized = {x.strip() for x in text.splitlines()}
    if "review_upload/" not in normalized:
        with gi.open("a", encoding="utf-8", newline="\n") as f:
            if text and not text.endswith(("\n", "\r")):
                f.write("\n")
            f.write("\n# Generated direct review exports\nreview_upload/\n")


def safe_name(value):
    value = re.sub(r"\.[Ss][Ll][Dd][Pp][Rr][Tt]$", "", str(value))
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "ACTIVE_PART"


def as_list(value):
    if value is None:
        return []
    if isinstance(value, (tuple, list)):
        return list(value)
    try:
        return list(value)
    except Exception:
        return [value]


def round_f(v, nd=9):
    try:
        return round(float(v), nd)
    except Exception:
        return None


def unit(v):
    n = math.sqrt(sum(float(x) ** 2 for x in v))
    if n <= 1e-15:
        return None
    return tuple(float(x) / n for x in v)


def canonical_dir(v):
    """Normalize direction and remove +/- ambiguity."""
    u = unit(v)
    if u is None:
        return None
    # Force first significant component positive.
    for x in u:
        if abs(x) > 1e-9:
            if x < 0:
                u = tuple(-q for q in u)
            break
    return u


def dot(a, b):
    return sum(float(x) * float(y) for x, y in zip(a, b))


def get_sw_constant(name, fallback):
    try:
        return int(getattr(win32com.client.constants, name))
    except Exception:
        return int(fallback)


def show_feature_dimensions(model):
    """
    SOLIDWORKS API requires feature dimensions to be displayed before
    GetFirstDisplayDimension / GetNextDisplayDimension returns them.
    """
    enum_value = get_sw_constant(
        "swDisplayFeatureDimensions",
        SW_DISPLAY_FEATURE_DIMENSIONS_FALLBACK,
    )
    old_value = None
    changed = False

    try:
        old_value = bool(model.GetUserPreferenceToggle(enum_value))
    except Exception:
        old_value = None

    # Preferred supported path.
    try:
        model.SetUserPreferenceToggle(enum_value, True)
        changed = True
        return enum_value, old_value, changed
    except Exception:
        pass

    # Compatibility path; documented as obsolete but still present.
    try:
        model.ShowFeatureDimensions()
        changed = True
    except Exception:
        pass

    return enum_value, old_value, changed


def restore_feature_dimensions(model, enum_value, old_value):
    if old_value is None:
        return
    try:
        model.SetUserPreferenceToggle(enum_value, bool(old_value))
    except Exception:
        pass


def get_dim_value(dim):
    # IDisplayDimension -> IDimension
    try:
        value = dim.SystemValue
        if isinstance(value, (int, float)):
            return float(value)
    except Exception:
        pass

    try:
        value = dim.GetSystemValue3(1, None)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, (tuple, list)):
            return [float(x) for x in value]
    except Exception:
        pass

    return None


def get_dimension_record(display_dim):
    try:
        dim = display_dim.GetDimension2(0)
    except Exception:
        dim = None
    if dim is None:
        return None

    rec = {
        "name": None,
        "full_name": None,
        "system_value_SI": get_dim_value(dim),
        "read_only": None,
    }
    for key, attr in (("name", "Name"), ("full_name", "FullName"), ("read_only", "ReadOnly")):
        try:
            rec[key] = getattr(dim, attr)
        except Exception:
            pass

    # Helpful human interpretation. SW SystemValue is SI: meters for linear
    # dimensions and radians for angular dimensions. We do not guess the type;
    # both conversions are included for review.
    val = rec["system_value_SI"]
    if isinstance(val, (int, float)):
        rec["candidate_linear_mm"] = float(val) * 1000.0
        rec["candidate_angular_deg"] = math.degrees(float(val))
    return rec


def feature_dimensions(feat):
    rows = []
    try:
        disp = feat.GetFirstDisplayDimension()
    except Exception:
        disp = None

    seen = set()
    guard = 0
    while disp is not None and guard < 2000:
        guard += 1
        rec = get_dimension_record(disp)
        if rec is not None:
            key = str(rec.get("full_name") or rec.get("name") or f"dim_{guard}")
            if key not in seen:
                seen.add(key)
                rows.append(rec)
        try:
            disp = feat.GetNextDisplayDimension(disp)
        except Exception:
            disp = None

    return rows


def feature_tree(model):
    rows = []
    try:
        feat = model.FirstFeature()
    except Exception:
        feat = None

    for idx in range(1, 10001):
        if feat is None:
            break

        try:
            name = feat.Name
        except Exception:
            name = "<unreadable>"

        try:
            ftype = feat.GetTypeName2()
        except Exception:
            ftype = "<unknown>"

        try:
            suppressed = bool(feat.IsSuppressed())
        except Exception:
            suppressed = None

        rows.append({
            "index": idx,
            "name": str(name),
            "type": str(ftype),
            "suppressed": suppressed,
            "dimensions": feature_dimensions(feat),
        })

        try:
            feat = feat.GetNextFeature()
        except Exception:
            feat = None

    return rows


def equation_dump(model):
    out = {"count": None, "items": [], "error": None}
    eq = None

    # Explicit method call first. v04 used late-bound member inspection and
    # some installations reported "Member not found".
    try:
        eq = model.GetEquationMgr()
    except Exception as exc1:
        try:
            attr = getattr(model, "GetEquationMgr")
            eq = attr() if callable(attr) else attr
        except Exception as exc2:
            out["error"] = (
                f"primary={type(exc1).__name__}: {exc1}; "
                f"fallback={type(exc2).__name__}: {exc2}"
            )
            return out

    if eq is None:
        return out

    count = None
    for candidate in ("GetCount", "Count"):
        try:
            member = getattr(eq, candidate)
            count = member() if callable(member) else member
            if count is not None:
                break
        except Exception:
            pass

    if count is None:
        return out

    try:
        count = int(count)
    except Exception:
        return out

    out["count"] = count

    for i in range(count):
        raw = None
        value = None

        # pywin32 may expose indexed COM properties differently depending on
        # generated wrappers, so try several forms.
        for getter in (
            lambda: eq.Equation(i),
            lambda: eq.Equation[i],
        ):
            try:
                raw = getter()
                break
            except Exception:
                pass

        for getter in (
            lambda: eq.Value(i),
            lambda: eq.Value[i],
        ):
            try:
                value = getter()
                break
            except Exception:
                pass

        out["items"].append({
            "index": i,
            "equation": str(raw) if raw is not None else None,
            "value_SI": value,
        })

    return out


def material_info(model):
    raw = ""
    try:
        raw = str(model.MaterialIdName or "")
    except Exception:
        pass
    parts = raw.split("|")
    return {
        "raw": raw,
        "name": parts[1] if len(parts) >= 2 else (raw or None),
        "assigned": bool(raw),
    }


def custom_properties(model):
    out = {}
    try:
        mgr = model.Extension.CustomPropertyManager("")
        names = as_list(mgr.GetNames())
    except Exception:
        return out

    for name in names:
        if not name:
            continue
        raw = resolved = None
        was_resolved = None
        linked = None
        try:
            result = mgr.Get6(str(name), False)
            # Common pywin32 tuple:
            # (status, raw, resolved, wasResolved, linkToProperty)
            if isinstance(result, (tuple, list)):
                if len(result) >= 3:
                    raw = result[1]
                    resolved = result[2]
                if len(result) >= 4:
                    was_resolved = result[3]
                if len(result) >= 5:
                    linked = result[4]
        except Exception:
            try:
                raw = mgr.Get(str(name))
            except Exception:
                pass

        out[str(name)] = {
            "raw": raw,
            "resolved": resolved,
            "was_resolved": was_resolved,
            "linked": linked,
        }
    return out


def get_vertex_point(vertex):
    if vertex is None:
        return None
    try:
        p = vertex.GetPoint()
    except Exception:
        return None
    if not isinstance(p, (tuple, list)) or len(p) < 3:
        return None
    return tuple(float(x) for x in p[:3])


def unique_points(points, tol_m=1e-8):
    seen = {}
    for p in points:
        if p is None:
            continue
        key = tuple(round(float(x) / tol_m) for x in p)
        seen[key] = p
    return list(seen.values())


def body_geometry(model):
    result = {
        "body_count": 0,
        "bodies": [],
        "principal_axis": None,
        "axial_stations_mm": [],
        "coaxial_cylinder_diameters_mm": [],
        "errors": [],
    }

    try:
        bodies = as_list(model.GetBodies2(SW_SOLID_BODY, False))
    except Exception as exc:
        result["errors"].append(f"GetBodies2: {type(exc).__name__}: {exc}")
        return result

    result["body_count"] = len(bodies)

    all_cylinders = []
    all_vertices = []
    all_planes = []

    for bi, body in enumerate(bodies):
        b = {
            "index": bi,
            "bbox_mm": None,
            "face_count": None,
            "cylinders": [],
            "planes": [],
            "vertices_mm": [],
        }

        try:
            box = body.GetBodyBox()
            if isinstance(box, (tuple, list)) and len(box) >= 6:
                b["bbox_mm"] = [float(x) * 1000.0 for x in box[:6]]
        except Exception as exc:
            result["errors"].append(f"body[{bi}].GetBodyBox: {exc}")

        try:
            faces = as_list(body.GetFaces())
            b["face_count"] = len(faces)
        except Exception as exc:
            faces = []
            result["errors"].append(f"body[{bi}].GetFaces: {exc}")

        for fi, face in enumerate(faces):
            try:
                surf = face.GetSurface()
            except Exception:
                surf = None
            if surf is None:
                continue

            area_mm2 = None
            try:
                area_mm2 = float(face.GetArea()) * 1e6
            except Exception:
                pass

            is_cyl = False
            try:
                is_cyl = bool(surf.IsCylinder())
            except Exception:
                pass

            if is_cyl:
                try:
                    cp = surf.CylinderParams
                    if callable(cp):
                        cp = cp()
                    cp = list(cp)
                    if len(cp) >= 7:
                        axis = canonical_dir(cp[3:6])
                        rec = {
                            "face_index": fi,
                            "origin_mm": [float(x) * 1000.0 for x in cp[0:3]],
                            "axis": list(axis) if axis else None,
                            "radius_mm": float(cp[6]) * 1000.0,
                            "diameter_mm": float(cp[6]) * 2000.0,
                            "area_mm2": area_mm2,
                        }
                        b["cylinders"].append(rec)
                        all_cylinders.append(rec)
                except Exception as exc:
                    result["errors"].append(f"body[{bi}].face[{fi}].CylinderParams: {exc}")

            is_plane = False
            try:
                is_plane = bool(surf.IsPlane())
            except Exception:
                pass

            if is_plane:
                try:
                    pp = surf.PlaneParams
                    if callable(pp):
                        pp = pp()
                    pp = list(pp)
                    if len(pp) >= 6:
                        # SOLIDWORKS PlaneParams: normal + point.
                        normal = canonical_dir(pp[0:3])
                        point = tuple(float(x) for x in pp[3:6])
                        rec = {
                            "face_index": fi,
                            "normal": list(normal) if normal else None,
                            "point_mm": [x * 1000.0 for x in point],
                            "area_mm2": area_mm2,
                            "_point_m": point,
                        }
                        b["planes"].append({k: v for k, v in rec.items() if not k.startswith("_")})
                        all_planes.append(rec)
                except Exception as exc:
                    result["errors"].append(f"body[{bi}].face[{fi}].PlaneParams: {exc}")

        try:
            edges = as_list(body.GetEdges())
        except Exception as exc:
            edges = []
            result["errors"].append(f"body[{bi}].GetEdges: {exc}")

        pts = []
        for edge in edges:
            for method in ("GetStartVertex", "GetEndVertex"):
                try:
                    v = getattr(edge, method)()
                    p = get_vertex_point(v)
                    if p is not None:
                        pts.append(p)
                except Exception:
                    pass

        pts = unique_points(pts)
        all_vertices.extend(pts)
        b["vertices_mm"] = [[x * 1000.0 for x in p] for p in pts]
        result["bodies"].append(b)

    # Infer principal revolved axis from cylindrical face directions.
    axis_candidates = []
    for c in all_cylinders:
        a = c.get("axis")
        if a:
            axis_candidates.append(tuple(round(float(x), 6) for x in a))

    if axis_candidates:
        principal_key, _ = Counter(axis_candidates).most_common(1)[0]
        principal = canonical_dir(principal_key)
        result["principal_axis"] = list(principal) if principal else None
    else:
        principal = None

    if principal:
        all_vertices = unique_points(all_vertices)
        if all_vertices:
            projections = [dot(p, principal) for p in all_vertices]
            p0 = min(projections)
            stations = sorted({round((q - p0) * 1000.0, 6) for q in projections})
            result["axial_stations_mm"] = stations

        # Cylinders parallel to principal axis.
        diams = []
        for c in all_cylinders:
            a = c.get("axis")
            if not a:
                continue
            aa = canonical_dir(a)
            if aa and abs(abs(dot(aa, principal)) - 1.0) < 1e-5:
                diams.append(round(float(c["diameter_mm"]), 6))
        result["coaxial_cylinder_diameters_mm"] = sorted(set(diams))

        # Add axial position for planes normal to principal axis.
        normal_planes = []
        raw_plane_proj = []
        for p in all_planes:
            n = p.get("normal")
            q = p.get("_point_m")
            if not n or q is None:
                continue
            nn = canonical_dir(n)
            if nn and abs(abs(dot(nn, principal)) - 1.0) < 1e-5:
                proj = dot(q, principal)
                raw_plane_proj.append(proj)
                normal_planes.append((p, proj))

        if normal_planes:
            base = min(raw_plane_proj)
            result["axial_planar_faces"] = [
                {
                    "station_mm": (proj - base) * 1000.0,
                    "area_mm2": p.get("area_mm2"),
                    "normal": p.get("normal"),
                    "point_mm": p.get("point_mm"),
                }
                for p, proj in sorted(normal_planes, key=lambda x: x[1])
            ]

    return result


def main():
    pythoncom.CoInitialize()
    ensure_gitignore()
    OUT.mkdir(parents=True, exist_ok=True)

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    model = sw.ActiveDoc
    if model is None:
        raise RuntimeError("No active SOLIDWORKS document.")

    try:
        title = model.GetTitle()
    except Exception:
        title = "<unknown>"
    try:
        path = model.GetPathName()
    except Exception:
        path = ""
    try:
        dtype = int(model.GetType())
    except Exception:
        dtype = 0

    if dtype != SW_DOC_PART:
        raise RuntimeError("v05 currently supports Part documents only.")
    if not path:
        raise RuntimeError("Save the native Part first.")

    enum_value, old_dim_pref, _ = show_feature_dimensions(model)

    try:
        tree = feature_tree(model)
        geometry = body_geometry(model)
    finally:
        restore_feature_dimensions(model, enum_value, old_dim_pref)

    payload = {
        "schema": "k01_review_export_v05",
        "document": {
            "title": title,
            "native_path": path,
            "doc_type": dtype,
        },
        "material": material_info(model),
        "custom_properties": custom_properties(model),
        "equations": equation_dump(model),
        "feature_tree": tree,
        "geometry": geometry,
        "dimension_policy": (
            "Display dimensions and BREP geometry are review evidence. "
            "Release control remains stable K01 master/global-variable names."
        ),
    }

    name = safe_name(title)
    out = OUT / f"{name}_REVIEW_V05.json"
    out.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    total_dims = sum(len(x.get("dimensions", [])) for x in tree)

    print("============================================================")
    print("K01 REVIEW EXPORT v05 - DIMENSIONS + BREP GEOMETRY")
    print("============================================================")
    print(f"Part:              {title}")
    print(f"JSON:              {out}")
    print(f"Material:          {payload['material']['name']}")
    print(f"Features:          {len(tree)}")
    print(f"Dimensions:        {total_dims}")
    print(f"Solid bodies:      {geometry.get('body_count')}")
    print(f"Principal axis:    {geometry.get('principal_axis')}")
    print(f"Axial stations:    {len(geometry.get('axial_stations_mm', []))}")
    print(f"Cylinder diameters:{geometry.get('coaxial_cylinder_diameters_mm')}")
    if geometry.get("errors"):
        print("WARN: geometry export completed with non-fatal API warnings:")
        for e in geometry["errors"][:10]:
            print("  -", e)
    print("PASS: native review JSON created.")
    print("Upload ONLY the *_REVIEW_V05.json for routine part review.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("FAIL: K01 REVIEW EXPORT v05")
        traceback.print_exc()
        sys.exit(1)
