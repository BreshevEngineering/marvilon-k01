from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client

from sw_com import member0, call, as_list


ROOT = Path(__file__).resolve().parents[1]

P003_REPORT = ROOT / "reports" / "cad" / "current" / "K01_P003_GATE03G_BUILD.json"
P007_REPORT = ROOT / "reports" / "cad" / "current" / "K01_P007_GATE03H_BUILD.json"
OUT_REPORT = ROOT / "reports" / "cad" / "current" / "K01_GATE03I_NATIVE_PAIR_VERIFY.json"
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

VERIFY_DIR = Path(r"D:\Marvilon\K01\cad\candidates")
VERIFY_BASE = "K01-A-001_GATE03I_NATIVE_PAIR_VERIFY"

PROD_ASM_NAME = "K01-A-001_Calibration_Module.SLDASM"
P003_PROD_SUFFIX = "K01-P-003_Cartridge_Body.SLDPRT"
P007_PROD_SUFFIX = "K01-P-007_Hermetic_Magnetic_Can.SLDPRT"

TRANSFORM_TOL = 1.0e-9


def normpath(p):
    return os.path.normcase(os.path.normpath(str(p)))


def comp_path(c):
    p, e = member0(c, "GetPathName", default="")
    if e:
        raise RuntimeError(e)
    return str(p or "")


def comp_name(c):
    n, _ = member0(c, "Name2", default="")
    return str(n or "")


def components(asm):
    rows, e = call(asm, "GetComponents", False, default=None)
    if e:
        raise RuntimeError(f"GetComponents(False) failed: {e}")
    return as_list(rows)


def find_by_suffix(rows, suffix):
    return [c for c in rows if comp_path(c).lower().endswith(suffix.lower())]


def find_by_exact_path(rows, path):
    target = normpath(path)
    return [c for c in rows if normpath(comp_path(c)) == target]


def transform_array(comp):
    tr, e = member0(comp, "Transform2", default=None)
    if e or tr is None:
        raise RuntimeError(e or f"{comp_name(comp)} Transform2 unavailable")
    data, e = member0(tr, "ArrayData", default=None)
    if e or data is None:
        raise RuntimeError(e or "Transform2.ArrayData unavailable")
    vals = [float(x) for x in list(data)]
    if len(vals) != 16:
        raise RuntimeError(f"Unexpected transform length: {len(vals)}")
    return vals


def transform_delta(a, b):
    return max(abs(float(a[i]) - float(b[i])) for i in range(16))


def save_as(model, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    rc, e = call(model, "SaveAs3", str(path), 0, 1, default=None)
    if e:
        raise RuntimeError(f"SaveAs3 failed: {e}")
    if not path.exists():
        raise RuntimeError(f"SaveAs3 did not create {path}; rc={rc!r}")


def iter_features(model):
    f, e = member0(model, "FirstFeature", default=None)
    if e:
        raise RuntimeError(e)
    while f is not None:
        yield f
        f, e = member0(f, "GetNextFeature", default=None)
        if e:
            raise RuntimeError(e)


def iter_subfeatures(feat):
    sf, e = member0(feat, "GetFirstSubFeature", default=None)
    if e:
        return
    while sf is not None:
        yield sf
        yield from iter_subfeatures(sf)
        sf, e = member0(sf, "GetNextSubFeature", default=None)
        if e:
            return


def feature_name_type(feat):
    n, _ = member0(feat, "Name", default="")
    t, _ = member0(feat, "GetTypeName2", default="")
    return str(n or ""), str(t or "")


def feature_error_code(feat):
    code, e = call(feat, "GetErrorCode2", default=None)
    if not e and code is not None:
        try:
            return int(code)
        except Exception:
            pass

    code, e = call(feat, "GetErrorCode", default=None)
    if not e and code is not None:
        try:
            return int(code)
        except Exception:
            pass

    return None


def mate_audit(model):
    """
    Read all mate subfeatures beneath MateGroup-like folders.
    Baseline errors are allowed; Gate03I fails only if the native-candidate
    replacement introduces NEW mate errors compared with production baseline.
    """
    rows = []
    seen = set()

    for feat in iter_features(model):
        name, typ = feature_name_type(feat)
        if "mate" not in typ.lower() and "mate" not in name.lower():
            continue

        candidates = [feat] + list(iter_subfeatures(feat))
        for c in candidates:
            cname, ctyp = feature_name_type(c)
            key = (cname, ctyp)
            if key in seen:
                continue
            seen.add(key)

            # Ignore the MateGroup folder itself; record actual mate-like items.
            if ctyp.lower() in ("mategroup", "matefolder"):
                continue
            if "mate" not in ctyp.lower() and not any(
                token in cname.lower()
                for token in (
                    "coincident", "concentric", "distance", "parallel",
                    "perpendicular", "limit", "angle", "tangent"
                )
            ):
                continue

            rows.append({
                "name": cname,
                "type": ctyp,
                "error_code": feature_error_code(c),
            })

    errors = [
        r for r in rows
        if r["error_code"] not in (None, 0)
    ]

    return {
        "mate_count": len(rows),
        "error_count": len(errors),
        "errors": errors,
        "all": rows,
    }


def replace_component(asm, old_comp, new_path, label):
    call(asm, "ClearSelection2", True, default=None)

    ok, e = call(old_comp, "Select2", False, 0, default=False)
    if e or not ok:
        raise RuntimeError(f"{label}: component Select2 failed: {e or ok!r}")

    # ReAttachMates=True is deliberate here.
    # Both candidates preserve the original native feature history.
    done, e = call(
        asm,
        "ReplaceComponents2",
        str(new_path),
        "",
        False,  # selected instance only
        0,
        True,   # reattach mates
        default=False,
    )
    if e or not done:
        raise RuntimeError(f"{label}: ReplaceComponents2 failed: {e or done!r}")


def rebuild_status(model):
    # ForceRebuild3 returns whether rebuild completed; error detail is audited
    # through mate state and feature state rather than relying on one boolean.
    result, e = call(model, "ForceRebuild3", False, default=None)
    return {
        "return": result,
        "error": e,
    }


def main():
    pythoncom.CoInitialize()

    if not P003_REPORT.exists():
        raise RuntimeError(f"Missing Gate03G report: {P003_REPORT}")
    if not P007_REPORT.exists():
        raise RuntimeError(f"Missing Gate03H report: {P007_REPORT}")

    p003_rep = json.loads(P003_REPORT.read_text(encoding="utf-8"))
    p007_rep = json.loads(P007_REPORT.read_text(encoding="utf-8"))

    if p003_rep.get("status") != "PASS":
        raise RuntimeError("Gate03G P003 candidate is not PASS.")
    if p007_rep.get("status") != "PASS":
        raise RuntimeError("Gate03H P007 candidate is not PASS.")

    p003_candidate = Path(p003_rep["native_candidate"])
    p007_candidate = Path(p007_rep["native_candidate"])

    if not p003_candidate.exists():
        raise RuntimeError(f"P003 candidate missing: {p003_candidate}")
    if not p007_candidate.exists():
        raise RuntimeError(f"P007 candidate missing: {p007_candidate}")

    sw = win32com.client.GetActiveObject("SldWorks.Application")
    revision, _ = member0(sw, "RevisionNumber", default="")

    asm, e = member0(sw, "ActiveDoc", default=None)
    if e or asm is None:
        raise RuntimeError(e or "No active SOLIDWORKS document.")

    typ, _ = member0(asm, "GetType", default=None)
    title, _ = member0(asm, "GetTitle", default="")
    prod_path, _ = member0(asm, "GetPathName", default="")
    dirty, _ = member0(asm, "GetSaveFlag", default=False)

    print("=" * 78)
    print("K01 Gate03I - FINAL NATIVE P003 + P007 ASSEMBLY VERIFY")
    print("=" * 78)
    print(f"[INFO] SOLIDWORKS revision: {revision}")
    print(f"[INFO] Production assembly: {title}")
    print(f"[INFO] P003 candidate:      {p003_candidate}")
    print(f"[INFO] P007 candidate:      {p007_candidate}")

    if int(typ) != 2:
        raise RuntimeError("Active document must be an Assembly.")
    if not str(title).lower().endswith(PROD_ASM_NAME.lower()):
        raise RuntimeError(f"Open production {PROD_ASM_NAME}; got {title!r}")
    if bool(dirty):
        raise RuntimeError("Production assembly has unsaved changes.")

    prod_path = Path(str(prod_path))
    if not prod_path.exists():
        raise RuntimeError(f"Production assembly path missing: {prod_path}")

    base_comps = components(asm)
    p003_old_rows = find_by_suffix(base_comps, P003_PROD_SUFFIX)
    p007_old_rows = find_by_suffix(base_comps, P007_PROD_SUFFIX)

    if len(p003_old_rows) != 1 or len(p007_old_rows) != 1:
        raise RuntimeError(
            f"Expected one production P003/P007; got "
            f"{len(p003_old_rows)}/{len(p007_old_rows)}"
        )

    p003_old = p003_old_rows[0]
    p007_old = p007_old_rows[0]

    T003_base = transform_array(p003_old)
    T007_base = transform_array(p007_old)

    baseline_mates = mate_audit(asm)
    print(
        f"[INFO] Baseline mate audit: count={baseline_mates['mate_count']}, "
        f"errors={baseline_mates['error_count']}"
    )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    verify_path = VERIFY_DIR / f"{VERIFY_BASE}_{stamp}.SLDASM"
    save_as(asm, verify_path)
    print(f"[PASS] Verification assembly copy created: {verify_path}")

    # Re-read current component objects from the verification copy.
    rows = components(asm)
    p003_old = find_by_suffix(rows, P003_PROD_SUFFIX)[0]
    p007_old = find_by_suffix(rows, P007_PROD_SUFFIX)[0]

    replace_component(asm, p003_old, p003_candidate, "P003")
    rebuild_1 = rebuild_status(asm)

    rows = components(asm)
    p003_new_rows = find_by_exact_path(rows, p003_candidate)
    if len(p003_new_rows) != 1:
        raise RuntimeError(f"After replacement expected one P003 candidate, got {len(p003_new_rows)}")

    # Find old P007 again after P003 replacement.
    p007_old_rows = find_by_suffix(rows, P007_PROD_SUFFIX)
    if len(p007_old_rows) != 1:
        raise RuntimeError(f"After P003 replacement expected one production P007, got {len(p007_old_rows)}")

    replace_component(asm, p007_old_rows[0], p007_candidate, "P007")
    rebuild_2 = rebuild_status(asm)

    rows = components(asm)
    p003_new_rows = find_by_exact_path(rows, p003_candidate)
    p007_new_rows = find_by_exact_path(rows, p007_candidate)

    if len(p003_new_rows) != 1 or len(p007_new_rows) != 1:
        raise RuntimeError(
            f"Final candidate instance count P003/P007 = "
            f"{len(p003_new_rows)}/{len(p007_new_rows)}"
        )

    p003_new = p003_new_rows[0]
    p007_new = p007_new_rows[0]

    T003_new = transform_array(p003_new)
    T007_new = transform_array(p007_new)

    dT003 = transform_delta(T003_base, T003_new)
    dT007 = transform_delta(T007_base, T007_new)

    print(f"[PASS] P003 transform delta vs production = {dT003:.3e}")
    print(f"[PASS] P007 transform delta vs production = {dT007:.3e}")

    if dT003 > TRANSFORM_TOL:
        raise RuntimeError(f"P003 moved after mate reattachment: ΔT={dT003:.3e}")
    if dT007 > TRANSFORM_TOL:
        raise RuntimeError(f"P007 moved after mate reattachment: ΔT={dT007:.3e}")

    final_mates = mate_audit(asm)
    print(
        f"[INFO] Final mate audit: count={final_mates['mate_count']}, "
        f"errors={final_mates['error_count']}"
    )

    baseline_error_keys = {
        (r["name"], r["type"], r["error_code"])
        for r in baseline_mates["errors"]
    }
    new_errors = [
        r for r in final_mates["errors"]
        if (r["name"], r["type"], r["error_code"]) not in baseline_error_keys
    ]

    if new_errors:
        print("[FAIL] New mate errors introduced:")
        for r in new_errors:
            print("      ", r)
        status = "FAIL_NEW_MATE_ERRORS"
    else:
        print("[PASS] No new mate errors introduced by native candidate replacement.")
        status = "PASS"

    # Save verification copy in its final replacement/rebuild state.
    save_as(asm, verify_path)

    report = {
        "schema": "k01_gate03i_native_pair_verify_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "solidworks_revision": str(revision),
        "production_assembly": str(prod_path),
        "production_assembly_modified": False,
        "verification_assembly": str(verify_path),
        "P003_candidate": str(p003_candidate),
        "P007_candidate": str(p007_candidate),
        "P003_transform_delta": dT003,
        "P007_transform_delta": dT007,
        "transform_tolerance": TRANSFORM_TOL,
        "rebuild_after_P003": rebuild_1,
        "rebuild_after_P007": rebuild_2,
        "baseline_mates": baseline_mates,
        "final_mates": final_mates,
        "new_mate_errors": new_errors,
        "manual_final_interference_required": True,
        "manual_interference_instruction": (
            "Evaluate > Interference Detection; Treat coincidence as interference OFF. "
            "Candidates P003/P007 must not create any new volumetric interference. "
            "Known old pairs P001-P008 14.05 mm3 and P009-P003 0.13 mm3 are tracked separately."
        ),
        "next_if_pass": (
            "Run one manual Interference Detection on this verification assembly. "
            "If no new P003/P007-related interference exists, CAD migration design is complete."
        ),
    }

    OUT_REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("=" * 78)
    print("K01 Gate03I RESULT")
    print("=" * 78)
    print("Status:", status)
    print("Verification assembly:", verify_path)
    print("Report:", OUT_REPORT)
    print("Production assembly on disk was NOT overwritten.")
    print()
    print("FINAL MANUAL CHECK:")
    print("Evaluate > Interference Detection")
    print("Treat coincidence as interference = OFF")
    print("If no NEW P003/P007 candidate interference appears, stop CAD iteration.")
    print("Proceed to controlled production migration + Static/Buckling.")

    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("FAIL: K01 Gate03I final native pair verification")
        traceback.print_exc()
        sys.exit(1)
