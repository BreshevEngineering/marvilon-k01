from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import pythoncom
import win32com.client

BUILD_REL = Path("reports/cad/current/K01_GATE04B_DATUM_C_BUILD.json")
DRYRUN_REL = Path("reports/control/K01_BASELINE_02C_PROMOTION_DRYRUN_CURRENT.json")
STEP_REL = Path("reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json")
QA_REL = Path("reports/cad/current/K01_GATE04B_DATUM_C_ASSEMBLY_QA.json")
OUT_REL = Path("reports/control/K01_BASELINE_02C_CANDIDATE_REQUALIFICATION_CURRENT.json")
QA_SRC_REL = Path("cad_api/gates/gate04b/K01Gate04B_DatumC_AssemblyQA.cs")
APPLY_MODULE_REL = Path("tools/medtas/baseline_02c_promotion_apply.py")
PRODUCER_MODULE_REL = Path("tools/sw_gate04b_datum_c_v7.py")

CHECKPOINT = "K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED"
SW_DOC_PART = 1
SW_OPEN_SILENT = 1
SW_OPEN_READONLY = 2
SW_END_THROUGH_ALL = 1


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_utc(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def candidate_qa_acceptance(qa):
    checks = {
        "component_count": qa.get("component_count") == 14,
        "active_mate_errors": qa.get("active_mate_errors") == 0,
        "p003_fully_constrained": "Fully" in str(qa.get("p003_constrained") or ""),
        "p016_fully_constrained": "Fully" in str(qa.get("p016_constrained") or ""),
        "p017_fully_constrained": "Fully" in str(qa.get("p017_constrained") or ""),
        "c_axis_center_error": float(qa.get("c_axis_center_error_mm", 999.0)) <= 0.002,
        "p017_press_depth": abs(float(qa.get("p017_press_depth_mm", 999.0)) - 4.0) <= 0.02,
        "p017_protrusion": abs(float(qa.get("p017_protrusion_mm", 999.0)) - 2.0) <= 0.02,
        "moving_group": qa.get("moving_group_pass") is True,
        "unexpected_interference": qa.get("unexpected_interference_total") == 0,
        "limit_restored": qa.get("original_limit_restored") is True,
    }
    bad = [k for k, value in checks.items() if not value]
    return checks, bad


def try_resume_close_only_pass(repo: Path, previous_report, paths, current_hashes):
    """
    Reuse the immediately preceding geometry + assembly QA evidence when the only
    failure was failure to terminate the verifier-owned SOLIDWORKS process.

    No engineering evidence is waived:
      * prior candidate geometry must be PASS for P003/P016/P017;
      * current candidate bytes must equal the bytes that were just requalified;
      * candidate assembly QA must be fresh for that run and PASS;
      * verification assembly hash must match the QA report;
      * full semantic acceptance must pass;
      * SOLIDWORKS must now be closed.

    This converts a process-lifecycle HOLD into a resumable transaction instead
    of rerunning expensive engineering QA.
    """
    if not isinstance(previous_report, dict):
        return None
    if previous_report.get("status") != "HOLD_REQUALIFICATION_FAILED":
        return None
    if "SolidWorks remained open after candidate assembly QA" not in str(previous_report.get("error") or ""):
        return None
    if sw_running():
        return None

    geometry = previous_report.get("candidate_geometry")
    if not isinstance(geometry, dict):
        return None
    for key in ("P003", "P016", "P017"):
        if not isinstance(geometry.get(key), dict) or geometry[key].get("status") != "PASS":
            return None

    prior_hash_rows = previous_report.get("artifact_hash_comparison") or {}
    for key in ("P003", "P016", "P017"):
        if str((prior_hash_rows.get(key) or {}).get("current") or "").lower() != current_hashes[key].lower():
            return None

    qa_path = repo / QA_REL
    if not qa_path.is_file():
        return None
    qa = load(qa_path)
    if qa.get("status") != "PASS_CANDIDATE_ASSEMBLY_QA":
        return None

    # Freshness: the QA must have been created during/after the failed
    # requalification run, not inherited from an older successful candidate QA.
    run_started = parse_utc(previous_report.get("generated_utc"))
    qa_created = parse_utc(qa.get("created_utc"))
    if run_started is None or qa_created is None or qa_created < run_started:
        return None

    expected_paths = {
        "p003_candidate": paths["P003"],
        "p016_candidate": paths["P016"],
        "p017_candidate": paths["P017"],
    }
    for field, expected in expected_paths.items():
        actual = qa.get(field)
        if not actual or os.path.normcase(os.path.normpath(str(actual))) != os.path.normcase(os.path.normpath(str(expected))):
            return None

    vasm = Path(str(qa.get("verification_assembly") or ""))
    if not vasm.is_file():
        return None
    if sha256(vasm).lower() != str(qa.get("verification_sha256") or "").lower():
        return None

    acceptance, bad = candidate_qa_acceptance(qa)
    if bad:
        return None

    return {
        "geometry": geometry,
        "qa": qa,
        "acceptance": acceptance,
        "resume_reason": (
            "Reused fresh PASS candidate geometry + full assembly QA after a "
            "process-lifecycle-only HOLD; no engineering criterion was waived."
        ),
    }



def sw_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
            text=True, errors="ignore"
        )
        return "sldworks.exe" in out.lower()
    except Exception:
        return False


def wait_sw_closed(seconds=30):
    end = time.time() + seconds
    while time.time() < end:
        if not sw_running():
            return True
        time.sleep(1.0)
    return not sw_running()


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import " + str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def connect_owned_sw():
    if sw_running():
        raise RuntimeError("SolidWorks must be closed before candidate requalification")
    pythoncom.CoInitialize()
    sw = None
    try:
        sw = win32com.client.DispatchEx("SldWorks.Application")
        sw.Visible = False
        rev_member = sw.RevisionNumber
        rev = str(rev_member() if callable(rev_member) else rev_member)
        if not rev.startswith("26."):
            raise RuntimeError("Expected SOLIDWORKS 2018 / revision 26; got " + rev)
        return sw, rev
    except Exception:
        # If this function created a headless SOLIDWORKS instance and then failed
        # during initialization, it owns that instance and must close it here.
        if sw is not None:
            try:
                sw.ExitApp()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        wait_sw_closed(30)
        raise


def open_part_readonly(sw, path: Path):
    er = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    wr = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = sw.OpenDoc6(str(path), SW_DOC_PART, SW_OPEN_SILENT | SW_OPEN_READONLY, "", er, wr)
    if isinstance(doc, tuple):
        doc = next((x for x in doc if x is not None and hasattr(x, "_oleobj_")), None)
    if doc is None:
        raise RuntimeError("OpenDoc6 read-only failed %s; e=%s w=%s" % (path, er.value, wr.value))
    return doc


def close_doc(sw, doc):
    try:
        sw.CloseDoc(doc.GetTitle())
    except Exception:
        pass


def feature_by_name(mod, doc, name):
    for f, n, t in mod.feature_rows(doc):
        if str(n).lower() == name.lower():
            return f, t
    return None, None


def vec_err_mm(a, b, indices):
    return 1000.0 * math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in indices))


def verify_p003(mod, doc, expected):
    rows = mod.cyls(doc)
    target = [float(x) for x in expected["C_center_local_m"]]
    bb = mod.mem(mod.body(doc), "GetBodyBox", None)
    if bb is None:
        raise RuntimeError("P003 body bbox unavailable")
    bb = [float(x) for x in list(bb)]
    datum_a = bb[0] + 0.003
    datum_a_err = abs(target[0] - datum_a) * 1000.0
    if datum_a_err > 0.02:
        raise RuntimeError("P003 Datum-A mapping drift %.6f mm > 0.02" % datum_a_err)

    flange = [r for r in rows if 33.9 <= r["D"] <= 34.1 and abs(abs(r["axis"][0]) - 1.0) < 1e-6]
    if not flange:
        raise RuntimeError("P003 OD34 flange cylinder missing")
    flange_t = max(mod.cyl_material_length_mm(r) for r in flange)
    if not (2.8 <= flange_t <= 3.2):
        raise RuntimeError("P003 flange thickness %.6f mm outside 2.8..3.2" % flange_t)

    feat, _ = feature_by_name(mod, doc, "K01_F_DATUM_C_MATING_HOLE")
    if feat is None:
        raise RuntimeError("P003 controlled Datum-C cut feature missing")
    ec_fwd, ec_rev = mod.cut_end_conditions(feat)
    if ec_fwd != SW_END_THROUGH_ALL or ec_rev != SW_END_THROUGH_ALL:
        raise RuntimeError("P003 Datum-C cut not Through-All both directions: %s/%s" % (ec_fwd, ec_rev))

    owned = [r for r in rows
             if abs(r["D"] - 3.02) < 0.02
             and str(r.get("owner_name") or "") == "K01_F_DATUM_C_MATING_HOLE"
             and abs(abs(r["axis"][0]) - 1.0) < 1e-6]
    if not owned:
        raise RuntimeError("P003 controlled Ø3.02 cylinder missing")
    chosen = min(owned, key=lambda r: vec_err_mm(r["origin"], target, [1, 2]))
    center_err = vec_err_mm(chosen["origin"], target, [1, 2])
    if center_err > 0.02:
        raise RuntimeError("P003 Datum-C center drift %.6f mm > 0.02" % center_err)
    near = [r for r in owned if vec_err_mm(r["origin"], target, [1, 2]) <= 0.02]
    thru_len = sum(mod.cyl_material_length_mm(r) for r in near)
    if thru_len < flange_t - 0.05:
        raise RuntimeError("P003 Datum-C through span %.6f mm < flange %.6f mm" % (thru_len, flange_t))
    axis, _ = feature_by_name(mod, doc, "K01_DATUM_C_AXIS")
    if axis is None:
        raise RuntimeError("P003 K01_DATUM_C_AXIS missing")
    return {
        "status": "PASS",
        "datumA_mapping_error_mm": datum_a_err,
        "flange_thickness_mm": flange_t,
        "D_mm": chosen["D"],
        "center_error_mm": center_err,
        "through_material_length_mm": thru_len,
        "end_conditions": [ec_fwd, ec_rev],
        "owner_feature": chosen.get("owner_name"),
    }


def circular_delta(a, b):
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def verify_p016(mod, doc, expected):
    rows = mod.cyls(doc)
    _, radii, angles, _, spacing_err, _ = mod.best_m4_triplet(rows)
    exp_angles = sorted(float(x) for x in expected["M4_angles_deg"])
    act_angles = sorted(float(x) for x in angles)
    if len(act_angles) != 3 or max(circular_delta(a, b) for a, b in zip(act_angles, exp_angles)) > 0.25:
        raise RuntimeError("P016 M4 angle pattern drift: %r vs %r" % (act_angles, exp_angles))
    if max(abs(float(r) - 12.0) for r in radii) > 0.05:
        raise RuntimeError("P016 M4 radius drift: %r" % radii)

    center = [float(x) for x in expected["C_center_local_m"]]
    holes = [r for r in rows
             if abs(r["D"] - 3.0) < 0.02
             and abs(abs(r["axis"][2]) - 1.0) < 1e-6
             and vec_err_mm(r["origin"], center, [0, 1]) <= 0.02]
    owned = [r for r in holes if str(r.get("owner_name") or "") == "K01_F_DATUM_C_PRESS_PIN_HOLE"]
    if not owned:
        raise RuntimeError("P016 controlled Ø3 press hole missing/owner mismatch")
    chosen = min(owned, key=lambda r: vec_err_mm(r["origin"], center, [0, 1]))
    depth = mod.cyl_material_length_mm(chosen)
    if not (3.8 <= depth <= 4.2):
        raise RuntimeError("P016 Datum-C press-hole cylindrical depth %.6f mm outside 3.8..4.2" % depth)
    axis, _ = feature_by_name(mod, doc, "K01_DATUM_C_AXIS")
    if axis is None:
        raise RuntimeError("P016 K01_DATUM_C_AXIS missing")
    return {
        "status": "PASS",
        "M4_angles_deg": act_angles,
        "M4_radii_mm": [float(x) for x in radii],
        "M4_spacing_error_deg": float(spacing_err),
        "C_center_error_mm": vec_err_mm(chosen["origin"], center, [0, 1]),
        "C_hole_D_mm": float(chosen["D"]),
        "C_hole_cylindrical_depth_mm": depth,
        "owner_feature": chosen.get("owner_name"),
    }


def verify_p017(mod, doc):
    b = mod.body(doc)
    bb = mod.mem(b, "GetBodyBox", None)
    if bb is None:
        raise RuntimeError("P017 body bbox unavailable")
    bb = [1000.0 * float(x) for x in list(bb)]
    size = [bb[3]-bb[0], bb[4]-bb[1], bb[5]-bb[2]]
    for actual, expected in zip(size, [3.0, 3.0, 6.0]):
        if abs(actual-expected) > 0.02:
            raise RuntimeError("P017 bbox mismatch: %r" % size)
    relief = [r for r in mod.planes(doc)
              if abs(abs(r["normal"][0]) - 1.0) < 1e-4 and 1.5 <= (r["area"] or 0) <= 3.0]
    if len(relief) != 2:
        raise RuntimeError("P017 relief-plane count=%d expected=2" % len(relief))
    xs = sorted(r["point"][0] * 1000.0 for r in relief)
    minor = abs(xs[-1] - xs[0])
    if abs(minor - 2.80) > 0.02:
        raise RuntimeError("P017 radial minor %.6f mm expected 2.80" % minor)
    d3 = [r for r in mod.cyls(doc) if abs(r["D"] - 3.0) < 0.02]
    if not d3:
        raise RuntimeError("P017 Ø3 cylindrical surface missing")

    # IMPORTANT GEOMETRY NOTE:
    # cyl_material_length_mm() is area/(pi*D).  That equals axial length only
    # for a FULL 360-degree cylindrical face.  P017 is intentionally relieved
    # over its 2-mm protruding section, while retaining Ø3 cylindrical arcs in
    # the tangential-major direction.  Therefore the previous 3.8..4.2 check
    # was a false model: the correct area-equivalent value for the nominal
    # 4-mm full-round shank + 2-mm relieved section is ~5.532456 mm.
    radius = 1.5
    flat_offset = minor / 2.0
    if not (0.0 < flat_offset < radius):
        raise RuntimeError("P017 relief geometry invalid: flat offset %.6f" % flat_offset)

    chord_width = 2.0 * math.sqrt(radius*radius - flat_offset*flat_offset)
    relief_lengths = []
    for r in relief:
        area = float(r.get("area") or 0.0)
        relief_lengths.append(area / chord_width)

    relief_length = sum(relief_lengths) / len(relief_lengths)
    if max(relief_lengths) - min(relief_lengths) > 0.02:
        raise RuntimeError("P017 relief axial lengths asymmetric: %r" % relief_lengths)
    if not (1.95 <= relief_length <= 2.05):
        raise RuntimeError(
            "P017 relieved protruding-section length %.6f mm outside 1.95..2.05"
            % relief_length
        )

    full_round_shank = size[2] - relief_length
    if not (3.95 <= full_round_shank <= 4.05):
        raise RuntimeError(
            "P017 derived full-round press shank %.6f mm outside 3.95..4.05"
            % full_round_shank
        )

    cylindrical_area_equivalent = sum(mod.cyl_material_length_mm(r) for r in d3)
    removed_arc_total = 4.0 * math.acos(flat_offset / radius)
    remaining_circumference_fraction = 1.0 - removed_arc_total / (2.0 * math.pi)
    expected_area_equivalent = (
        full_round_shank
        + relief_length * remaining_circumference_fraction
    )
    if abs(cylindrical_area_equivalent - expected_area_equivalent) > 0.03:
        raise RuntimeError(
            "P017 Ø3 cylindrical area-equivalent mismatch actual=%.6f expected=%.6f"
            % (cylindrical_area_equivalent, expected_area_equivalent)
        )

    return {
        "status": "PASS",
        "size_mm": size,
        "radial_minor_mm": minor,
        "relief_plane_count": len(relief),
        "relief_axial_lengths_mm": relief_lengths,
        "relieved_protruding_section_length_mm": relief_length,
        "derived_full_round_press_shank_length_mm": full_round_shank,
        "cylindrical_area_equivalent_length_mm": cylindrical_area_equivalent,
        "expected_cylindrical_area_equivalent_length_mm": expected_area_equivalent,
        "proof_note": (
            "P017 press shank is derived from L=6 minus the 2-mm relieved section; "
            "area/(pi*D) is not axial length for the partially relieved cylinder."
        ),
    }


def geometry_requalify(repo: Path, build, paths):
    tools = repo / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    mod = import_module(repo / PRODUCER_MODULE_REL, "k01_gate04b_producer_helpers")
    sw, rev = connect_owned_sw()
    result = {"solidworks_revision": rev}
    try:
        for key, verifier, expected in [
            ("P003", verify_p003, build["P003"]["result"]),
            ("P016", verify_p016, build["P016"]["result"]),
        ]:
            doc = open_part_readonly(sw, paths[key])
            try:
                result[key] = verifier(mod, doc, expected)
            finally:
                close_doc(sw, doc)
        doc = open_part_readonly(sw, paths["P017"])
        try:
            result["P017"] = verify_p017(mod, doc)
        finally:
            close_doc(sw, doc)
    finally:
        try:
            sw.ExitApp()
        except Exception:
            pass
        pythoncom.CoUninitialize()
    if not wait_sw_closed(30):
        raise RuntimeError("SolidWorks did not close after read-only candidate geometry requalification")
    return result


def graceful_close_verifier_sw():
    if not sw_running():
        return True
    try:
        pythoncom.CoInitialize()
        sw = win32com.client.GetActiveObject("SldWorks.Application")
        sw.ExitApp()
    except Exception:
        return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    return wait_sw_closed(30)


def assembly_requalify(repo: Path):
    applymod = import_module(repo / APPLY_MODULE_REL, "k01_baseline02c_apply_compile")
    exe, comp = applymod.compile_cs(repo, QA_SRC_REL, "K01Gate04B_DatumC_AssemblyQA_REQUALIFY.exe")
    cp = subprocess.run([str(exe)], cwd=str(repo), capture_output=True, text=True, errors="replace")
    # The verifier is required to own and close the SOLIDWORKS instance it
    # creates.  Keep a graceful fallback for older binaries, but do not treat
    # process cleanup as engineering evidence.
    closed = wait_sw_closed(15)
    if not closed:
        closed = graceful_close_verifier_sw()

    qa_path = repo / QA_REL
    qa = load(qa_path) if qa_path.is_file() else {}
    if cp.returncode != 0:
        raise RuntimeError("Gate04B candidate assembly QA failed\n%s\n%s" % (cp.stdout, cp.stderr))
    if qa.get("status") != "PASS_CANDIDATE_ASSEMBLY_QA":
        raise RuntimeError("Candidate assembly QA status=%r" % qa.get("status"))

    acceptance, bad = candidate_qa_acceptance(qa)
    if bad:
        raise RuntimeError("Candidate assembly semantic acceptance failed: " + ", ".join(bad))

    if not closed:
        raise RuntimeError("SolidWorks remained open after candidate assembly QA; no authority refresh performed")
    return qa, acceptance, comp


def update_dryrun_after_pass(repo: Path, dry, report, current_hashes, qa):
    previous = dict(dry.get("frozen_actual_sha256") or {})
    dry.setdefault("history", []).append({
        "event": "ARTIFACT_HASH_REQUALIFICATION",
        "utc": report["generated_utc"],
        "previous_frozen_actual_sha256": previous,
        "evidence": str(OUT_REL).replace("\\", "/"),
        "reason": "Candidate binary SHA drift accepted only after geometry proof plus full candidate assembly QA PASS."
    })
    dry["frozen_actual_sha256"].update({
        "P003_candidate": current_hashes["P003"],
        "P016_candidate": current_hashes["P016"],
        "P017_candidate": current_hashes["P017"],
        "verification_A001": qa["verification_sha256"],
    })
    dry["status"] = "PASS_DRYRUN_MANIFEST_REQUALIFIED_READY_FOR_APPLY_PROMOTER_IMPLEMENTATION_REVIEW"
    dry["requalification_evidence"] = str(OUT_REL).replace("\\", "/")
    dry["semantic_authority_rule"] = (
        "Raw SolidWorks binary SHA is an artifact-integrity guard, not a semantic-equivalence claim. "
        "A changed artifact SHA may be admitted only by explicit geometry + assembly requalification evidence."
    )
    write_json(repo / DRYRUN_REL, dry)


def main():
    ap = argparse.ArgumentParser(description="Requalify current Baseline-02C candidates after artifact SHA drift")
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    out = repo / OUT_REL
    previous_report = load(out) if out.is_file() else {}
    report = {
        "schema": "k01.baseline_02c.candidate_requalification.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint": CHECKPOINT,
        "status": "RUNNING",
        "native_canonical_CAD_mutated": False,
        "authority_refreshed": False,
        "error": "",
    }
    try:
        step = load(repo / STEP_REL)
        if not str(step.get("status", "")).startswith("PASS_TO_BASELINE02C_PROMOTION_APPLY") or step.get("mutation_authorized") is not True:
            raise RuntimeError("Current step gate is not authorized for Baseline-02C promotion apply")
        dry = load(repo / DRYRUN_REL)
        build = load(repo / BUILD_REL)
        if dry.get("checkpoint") != CHECKPOINT:
            raise RuntimeError("Dry-run checkpoint mismatch")
        if build.get("status") != "PASS":
            raise RuntimeError("Gate04B build evidence is not PASS")

        paths = {
            "P003": Path(dry["plan"]["candidate_sources"]["P003"]),
            "P016": Path(dry["plan"]["candidate_sources"]["P016"]),
            "P017": Path(dry["plan"]["candidate_sources"]["P017"]),
        }
        for key, path in paths.items():
            if not path.is_file():
                raise RuntimeError("Missing current candidate %s: %s" % (key, path))

        old_hashes = dict(dry.get("frozen_actual_sha256") or {})
        current_hashes = {key: sha256(path) for key, path in paths.items()}
        report["artifact_hash_comparison"] = {
            key: {
                "previous": old_hashes.get(key + "_candidate"),
                "current": current_hashes[key],
                "changed": str(old_hashes.get(key + "_candidate") or "").lower() != current_hashes[key].lower(),
            } for key in ("P003", "P016", "P017")
        }

        resumed = try_resume_close_only_pass(repo, previous_report, paths, current_hashes)
        if resumed is not None:
            qa = resumed["qa"]
            acceptance = resumed["acceptance"]
            report["candidate_geometry"] = resumed["geometry"]
            report["assembly_QA"] = {
                "status": qa.get("status"),
                "verification_assembly": qa.get("verification_assembly"),
                "verification_sha256": qa.get("verification_sha256"),
                "component_count": qa.get("component_count"),
                "active_mate_errors": qa.get("active_mate_errors"),
                "unexpected_interference_total": qa.get("unexpected_interference_total"),
                "moving_group_pass": qa.get("moving_group_pass"),
                "p017_press_depth_mm": qa.get("p017_press_depth_mm"),
                "p017_protrusion_mm": qa.get("p017_protrusion_mm"),
                "acceptance": acceptance,
            }
            report["verifier_compile"] = {"status": "PASS_REUSED_FRESH_QA_EVIDENCE"}
            report["resume"] = {
                "status": "PASS_RESUMED_AFTER_VERIFIER_PROCESS_CLEANUP_HOLD",
                "reason": resumed["resume_reason"],
                "previous_error": previous_report.get("error"),
            }
            report["artifact_semantic_disposition"] = "PASS_SEMANTIC_EQUIVALENCE_REQUALIFIED"
            report["status"] = "PASS_CANDIDATES_REQUALIFIED_READY_FOR_CONTROLLED_PROMOTION"
            report["authority_refreshed"] = True
            write_json(out, report)
            update_dryrun_after_pass(repo, dry, report, current_hashes, qa)

            print("STATUS:", report["status"])
            print("RESUME: PASS_REUSED_FRESH_GEOMETRY_AND_ASSEMBLY_QA")
            print("REPORT:", out)
            print("Verification A001:", qa.get("verification_assembly"))
            print("Verification SHA:", qa.get("verification_sha256"))
            print("Canonical CAD mutated: False")
            return 0

        report["candidate_geometry"] = geometry_requalify(repo, build, paths)
        qa, acceptance, compile_info = assembly_requalify(repo)
        report["assembly_QA"] = {
            "status": qa.get("status"),
            "verification_assembly": qa.get("verification_assembly"),
            "verification_sha256": qa.get("verification_sha256"),
            "component_count": qa.get("component_count"),
            "active_mate_errors": qa.get("active_mate_errors"),
            "unexpected_interference_total": qa.get("unexpected_interference_total"),
            "moving_group_pass": qa.get("moving_group_pass"),
            "p017_press_depth_mm": qa.get("p017_press_depth_mm"),
            "p017_protrusion_mm": qa.get("p017_protrusion_mm"),
            "acceptance": acceptance,
        }
        report["verifier_compile"] = {"status": "PASS", "stdout": compile_info.get("stdout", "")}
        report["artifact_semantic_disposition"] = "PASS_SEMANTIC_EQUIVALENCE_REQUALIFIED"
        report["status"] = "PASS_CANDIDATES_REQUALIFIED_READY_FOR_CONTROLLED_PROMOTION"
        report["authority_refreshed"] = True
        write_json(out, report)
        update_dryrun_after_pass(repo, dry, report, current_hashes, qa)

        print("STATUS:", report["status"])
        print("REPORT:", out)
        for key in ("P003", "P016", "P017"):
            row = report["artifact_hash_comparison"][key]
            print("%s SHA changed=%s previous=%s current=%s" % (key, row["changed"], row["previous"], row["current"]))
        print("Verification A001:", qa.get("verification_assembly"))
        print("Verification SHA:", qa.get("verification_sha256"))
        print("Canonical CAD mutated: False")
        return 0
    except Exception as ex:
        report["status"] = "HOLD_REQUALIFICATION_FAILED"
        report["error"] = repr(ex)
        report["traceback"] = traceback.format_exc()
        write_json(out, report)
        print("STATUS:", report["status"])
        print("REPORT:", out)
        print("ERROR:", repr(ex))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
