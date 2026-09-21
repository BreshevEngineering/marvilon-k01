from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

R = Path(r"D:\BreshevEngineering\marvilon-k01")

EDR45 = Path("control/decisions/EDR-045_P004_REFERENCE_TEMPERATURE_AND_SERVICE_CLEARANCE.json")
EDR46 = Path("control/decisions/EDR-046_P004_JOINT_TOLERANCE_BUDGET_20C.json")
PD = Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ = Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
INSP = Path("reports/inspection/K01-P-004_INSPECTION_PLAN_CURRENT.json")
REC = Path("reports/engineering/K01_P004_MATING_AUTHORITY_RECOVERY_CURRENT.json")
REP = Path("reports/engineering/K01_P004_JOINT_TOLERANCE_ALLOCATION_CURRENT.json")
NEXT = Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE = Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT = Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER = Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")


def rd(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def wr(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_guard(repo: Path):
    for tool in ("k01_temporal_coherence_guard_v1.py", "k01_semantic_coherence_guard_v1.py"):
        cp = subprocess.run(
            [sys.executable, "tools/state/" + tool, "--repo-root", str(repo), "--write-report"],
            cwd=repo,
            text=True,
        )
        if cp.returncode:
            raise SystemExit("HOLD: state guard failed before EDR-046.")


def set_char(pd: dict, cid: str, updates: dict):
    chars = pd.get("characteristics")
    if not isinstance(chars, list):
        chars = []
        pd["characteristics"] = chars
    for c in chars:
        if isinstance(c, dict) and c.get("id") == cid:
            c.update(updates)
            return
    item = {"id": cid}
    item.update(updates)
    chars.append(item)


def replace_blockers(items, remove_tokens, append_items):
    out = []
    for x in items or []:
        sx = str(x)
        if any(tok.lower() in sx.lower() for tok in remove_tokens):
            continue
        out.append(x)
    for x in append_items:
        if x not in out:
            out.append(x)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(R))
    ap.add_argument("--preflight-only", action="store_true")
    a = ap.parse_args()
    repo = Path(a.repo_root).resolve()

    required = [EDR45, PD, READ, INSP, REC, NEXT, GATE, FRONT]
    missing = [str(x).replace("\\", "/") for x in required if not (repo / x).is_file()]
    if missing:
        print("HOLD_MISSING_REQUIRED_AUTHORITIES")
        for x in missing:
            print("MISSING:", x)
        return 2

    run_guard(repo)

    n = rd(repo / NEXT, {}) or {}
    f = rd(repo / FRONT, {}) or {}
    rec = rd(repo / REC, {}) or {}
    edr45 = rd(repo / EDR45, {}) or {}
    pd = rd(repo / PD, {}) or {}
    readiness = rd(repo / READ, {}) or {}
    insp = rd(repo / INSP, {}) or {}

    if n.get("next_action_id") != "K01-NA-P004-JOINT-TOLERANCE-DECISION":
        print("HOLD_WRONG_FRONTIER")
        print("EXPECTED: K01-NA-P004-JOINT-TOLERANCE-DECISION")
        print("ACTUAL:", n.get("next_action_id"))
        return 3
    if str((f.get("active_blocker") or {}).get("id")) != "P004-JOINT-TOLERANCE-ALLOCATION-DECISION":
        print("HOLD_WRONG_BLOCKER")
        print("ACTUAL:", f.get("active_blocker"))
        return 3
    if rec.get("status") != "PASS_AUTHORITY_INVENTORY__JOINT_TOLERANCE_DECISION_READY":
        print("HOLD_MATING_AUTHORITY_RECOVERY_NOT_READY")
        return 3
    if ((edr45.get("release_boundary") or {}).get("20C_dimensional_acceptance") != "CONTROLLED"):
        print("HOLD_EDR045_20C_ACCEPTANCE_NOT_CONTROLLED")
        return 3

    # Controlled top-down functional values. These are budgets, not released part tolerances.
    seat = {
        "P003_seat_nominal_ID_mm": 6.600,
        "P004_nominal_OD_mm": 6.540,
        "nominal_diametral_clearance_mm": 0.060,
        "functional_window_20C_mm": [0.040, 0.080],
        "worst_case_constraints": [
            "P003_ID_min - P004_OD_max >= 0.040 mm",
            "P003_ID_max - P004_OD_min <= 0.080 mm",
        ],
        "budget_to_low_boundary_mm": 0.020,
        "budget_to_high_boundary_mm": 0.020,
        "part_level_split": "OPEN__CAPABILITY_EVIDENCE_REQUIRED",
    }
    axial = {
        "effective_retention_space_nominal_mm": 8.050,
        "P004_nominal_length_mm": 8.000,
        "nominal_float_mm": 0.050,
        "functional_window_20C_mm": [0.040, 0.080],
        "worst_case_constraints": [
            "H_P003_P014_min - L_P004_max >= 0.040 mm",
            "H_P003_P014_max - L_P004_min <= 0.080 mm",
        ],
        "budget_toward_loss_of_float_mm": 0.010,
        "budget_toward_excessive_float_mm": 0.030,
        "part_level_split": "OPEN__CAPABILITY_EVIDENCE_REQUIRED",
        "nominal_recentering_trigger": "If demonstrated manufacturing + inspection capability cannot reliably satisfy <=0.010 mm combined adverse-side variation, reopen nominal architecture and evaluate centering toward 0.060 mm; do not change geometry solely by arithmetic.",
    }

    if a.preflight_only:
        print("PASS_PREFLIGHT_EDR046")
        print("SEAT_BUDGET_LOW/HIGH_MM: 0.020 / 0.020")
        print("AXIAL_BUDGET_LOW/HIGH_MM: 0.010 / 0.030")
        print("NO_FILES_CHANGED")
        return 0

    wr(repo / EDR46, {
        "schema": "k01.edr.v1",
        "decision_id": "EDR-046",
        "date": "2026-09-18",
        "subject": "P004 joint worst-case seat and axial tolerance budgets at 20 C",
        "status": "ACCEPTED_TOP_DOWN_TOLERANCE_BUDGET__PART_LEVEL_PRODUCTION_TOLERANCES_CAPABILITY_DEPENDENT",
        "goal": "Close the P003↔P004 seat and P003/P014↔P004 axial functional worst-case budgets at 20 C without inventing production tolerances for P003, P004 or P014.",
        "authority": [
            "EDR-045",
            "reports/engineering/K01_P004_MATING_AUTHORITY_RECOVERY_CURRENT.json",
            "control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json",
        ],
        "engineering_question": "What joint tolerance budget is available from the controlled 20 C functional windows, and what may be allocated before mating-part production capability is proven?",
        "decision": [
            "Seat nominal 6.600/6.540 is retained; nominal diametral clearance is 0.060 mm and is centered in the 0.040...0.080 mm functional window.",
            "Seat worst-case adverse contribution budget is 0.020 mm toward either functional boundary. No P003/P004 production tolerance split is released until manufacturing and metrology capability evidence supports it.",
            "Axial nominal chain H=8.050 mm and P004 L=8.000 mm is retained provisionally; nominal float is 0.050 mm in the 0.040...0.080 mm functional window.",
            "Axial worst-case budget is asymmetric: 0.010 mm toward loss of float and 0.030 mm toward excessive float.",
            "No P003/P014/P004 production tolerance split is released until manufacturing and metrology capability evidence supports it.",
            "If the <=0.010 mm adverse-side axial capability cannot be demonstrated reliably, reopen the nominal architecture and evaluate centering toward 0.060 mm or require a better process/change the functional requirement. Do not conceal insufficient capability by arbitrary tolerance splitting.",
            "20 C production dimensional acceptance remains separate from service-temperature no-binding qualification per EDR-045.",
        ],
        "seat": seat,
        "axial": axial,
        "technical_filter": {
            "function": "PASS_BUDGET_DEFINED",
            "tolerance": "PASS_JOINT_BUDGET__PART_SPLIT_OPEN",
            "manufacturing": "OPEN_CAPABILITY_EVIDENCE",
            "inspection": "OPEN_CAPABILITY_AND_UNCERTAINTY",
            "assembly": "PASS_ARCHITECTURE_RETAINED__NO_PRELOAD",
            "thermal": "20C_ACCEPTANCE_CONTROLLED__SERVICE_QUALIFICATION_SEPARATE",
        },
        "downstream_requirements": [
            "P003 seat Product Definition shall satisfy P003_ID_min - P004_OD_max >= 0.040 mm and P003_ID_max - P004_OD_min <= 0.080 mm at 20 C after capability-based allocation.",
            "P003/P014 effective installed retention-space Product Definition shall satisfy H_min - L_P004_max >= 0.040 mm and H_max - L_P004_min <= 0.080 mm at 20 C after capability-based allocation.",
            "P004 production OD/OAL tolerances remain OPEN until the shared budgets are allocated using manufacturing and metrology capability evidence.",
        ],
        "expected_closure": "PASS_P004_SEAT_AXIAL_TOLERANCE_BUDGET_DECIDED__DOWNSTREAM_PART_ALLOCATIONS_EXPLICIT",
        "impact": {"CAD": "NONE", "DimXpert": "NONE", "drawing": "NONE", "native_mutation": "NONE"},
    })

    wr(repo / REP, {
        "schema": "k01.p004.joint_tolerance_allocation.current.v1",
        "generated_utc": now(),
        "status": "PASS_P004_SEAT_AXIAL_TOLERANCE_BUDGET_DECIDED__DOWNSTREAM_PART_ALLOCATIONS_EXPLICIT",
        "part_id": "K01-P-004",
        "reference_temperature_C": 20,
        "seat": seat,
        "axial": axial,
        "released_part_tolerances": [],
        "downstream_allocation_state": {
            "P003": "REQUIREMENT_CREATED__PRODUCTION_VALUE_OPEN",
            "P014": "REQUIREMENT_CREATED__PRODUCTION_VALUE_OPEN",
            "P004": "JOINT_BUDGET_CONTROLLED__PRODUCTION_VALUE_OPEN_PENDING_CAPABILITY",
        },
        "native_mutation": "NONE",
    })

    set_char(pd, "P004-C02", {
        "name": "P003 seat OD",
        "nominal": "Ø6.54",
        "status": "JOINT_BUDGET_CONTROLLED__PRODUCTION_TOLERANCE_OPEN",
        "functional_window_20C_mm": [0.040, 0.080],
        "joint_budget_mm": {"toward_min_clearance": 0.020, "toward_max_clearance": 0.020},
        "production_tolerance": "OPEN__CAPABILITY_ALLOCATION_REQUIRED",
        "source": "EDR-046",
    })
    set_char(pd, "P004-C03", {
        "name": "OAL / axial float chain",
        "nominal": "8.00",
        "status": "JOINT_BUDGET_CONTROLLED__PRODUCTION_TOLERANCE_OPEN",
        "functional_window_20C_mm": [0.040, 0.080],
        "joint_budget_mm": {"toward_loss_of_float": 0.010, "toward_excessive_float": 0.030},
        "production_tolerance": "OPEN__CAPABILITY_ALLOCATION_REQUIRED",
        "architecture_state": "0p050_NOMINAL_RETAINED_PROVISIONALLY__RECENTER_IF_CAPABILITY_INSUFFICIENT",
        "source": "EDR-046",
    })
    pd["status"] = "PARTIAL_PRODUCT_DEFINITION__MANUFACTURING_METROLOGY_CAPABILITY_NEXT"
    pd["product_definition_ready"] = False
    pd["open_release_blockers"] = replace_blockers(
        pd.get("open_release_blockers"),
        ["temperature-aware P003/P004 tolerance allocation", "P004 axial worst-case tolerance allocation"],
        [
            "P004/P003/P014 production tolerance split — WAITING on manufacturing/metrology capability evidence",
        ],
    )
    wr(repo / PD, pd)

    readiness["generated_utc"] = now()
    readiness["joint_tolerance_allocation"] = "PASS_EDR_046"
    readiness["seat_joint_budget"] = "CONTROLLED"
    readiness["axial_joint_budget"] = "CONTROLLED"
    readiness["production_tolerance_split"] = "OPEN__MANUFACTURING_METROLOGY_CAPABILITY_REQUIRED"
    readiness["next_blocker"] = "P004-MANUFACTURING-METROLOGY-CAPABILITY-DECISION"
    readiness["next"] = "Establish controlled P004 manufacturing and metrology capability evidence at 20 C sufficient to allocate the EDR-046 seat/axial budgets. Do not assign production tolerances from generic practice."
    wr(repo / READ, readiness)

    insp["generated_utc"] = now()
    insp["reference_temperature_C"] = 20
    insp["tolerance_budget_source"] = "EDR-046"
    insp["capability_state"] = "OPEN__REQUIRES_PROCESS_AND_MEASUREMENT_CAPABILITY_EVIDENCE"
    wr(repo / INSP, insp)

    blocker = "P004-MANUFACTURING-METROLOGY-CAPABILITY-DECISION"
    nid = "K01-NA-P004-MANUFACTURING-METROLOGY-CAPABILITY"
    exp = "PASS_P004_CAPABILITY_BASIS_CONTROLLED__TOLERANCE_SPLIT_READY_OR_NOMINAL_REOPEN_TRIGGERED"
    text = (
        "Establish the controlled manufacturing + metrology capability basis for TECAPEEK PVX P004 at 20 C: "
        "OD Ø6.54, OAL 8.00, guide bore Ø5.055, conditioning/stabilization, measurement method/force and uncertainty. "
        "Use actual supplier/process/metrology evidence where available. Then determine whether EDR-046 budgets are manufacturable; "
        "if the axial <=0.010 mm adverse-side combined budget is not demonstrably capable, trigger nominal-architecture review. "
        "No CAD/DimXpert/drawing mutation."
    )
    auth = [
        str(REP).replace("\\", "/"),
        str(EDR46).replace("\\", "/"),
        str(PD).replace("\\", "/"),
        str(READ).replace("\\", "/"),
        str(INSP).replace("\\", "/"),
        "control/decisions/EDR-038_P004_MATERIAL_THERMAL_PROCESS_BASIS.json",
        "control/decisions/EDR-043_P004_TECAPEEK_PVX_PRODUCTION_MATERIAL_EVIDENCE.json",
    ]

    n.update({
        "schema": "k01.next_actions.current.v38_program_front",
        "active_blocker": blocker,
        "current_blocker": blocker + ":OPEN",
        "next_1": text,
        "next_action_id": nid,
        "expected_closure": exp,
        "execution_mode": "ENGINEERING_CAPABILITY_DECISION__NO_NATIVE_MUTATION",
        "authority_set": auth,
        "last_completed": "EDR-046 — P004 joint worst-case seat and axial tolerance budgets at 20 C",
        "latest_engineering_activity": "EDR-046 — P004 joint worst-case seat and axial tolerance budgets at 20 C [ACCEPTED_TOP_DOWN_TOLERANCE_BUDGET__PART_LEVEL_PRODUCTION_TOLERANCES_CAPABILITY_DEPENDENT]",
    })
    wr(repo / NEXT, n)

    gate = rd(repo / GATE, {}) or {}
    gate.update({
        "schema": "k01.active_step_gate.v18_program_front",
        "generated_utc": now(),
        "intent": nid,
        "intent_text": text,
        "active_blocker": blocker,
        "expected_closure": exp,
        "mutation_authorized": False,
        "mutation_scope": "ENGINEERING CAPABILITY EVIDENCE/DECISION ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING",
        "required_files": auth,
    })
    wr(repo / GATE, gate)

    front = rd(repo / FRONT, {}) or {}
    front.update({
        "generated_utc": now(),
        "active_blocker": {"id": blocker, "state": "OPEN", "timing": "ACTIVE_NOW"},
        "next_allowed_action": {
            "id": nid,
            "text": text,
            "authority_set": auth,
            "expected_closure": exp,
            "execution_mode": "ENGINEERING_CAPABILITY_DECISION__NO_NATIVE_MUTATION",
        },
    })
    timing = front.setdefault("timing", {})
    timing["ACTIVE_NOW"] = [blocker]
    waiting_dep = timing.get("WAITING_DEPENDENCY") or []
    waiting_dep = [x for x in waiting_dep if "seat production tolerance" not in str(x).lower() and "axial production tolerance" not in str(x).lower()]
    for x in [
        "P004/P003/P014 production tolerance split — manufacturing/metrology capability evidence",
        "P004 guide-clearance numeric limits — system radial/angular/optical repeatability allocation",
        "P004 GPS numeric values — after tolerance allocation",
        "P004 texture numeric values — after process capability decision",
        "P004 conditioning/final inspection acceptance — after inspection procedure/capability decision",
    ]:
        if x not in waiting_dep:
            waiting_dep.append(x)
    timing["WAITING_DEPENDENCY"] = waiting_dep
    closed = front.setdefault("closed_blocker_ids", [])
    if "P004-JOINT-TOLERANCE-ALLOCATION-DECISION" not in closed:
        closed.append("P004-JOINT-TOLERANCE-ALLOCATION-DECISION")
    wr(repo / FRONT, front)

    cm = rd(repo / CENTER, {}) or {}
    if cm:
        cm.update({
            "generated_utc": now(),
            "active_blocker": blocker,
            "next_action_id": nid,
            "p004_joint_tolerance_allocation": {"status": "PASS_EDR_046", "report": str(REP).replace("\\", "/")},
        })
        wr(repo / CENTER, cm)

    subprocess.run([sys.executable, "tools/state/k01_lifecycle_state_reducer_v2.py", "--repo-root", str(repo)], cwd=repo, check=True, text=True)
    subprocess.run([sys.executable, "tools/state/k01_temporal_coherence_guard_v1.py", "--repo-root", str(repo), "--write-report"], cwd=repo, check=True, text=True)
    subprocess.run([sys.executable, "tools/state/k01_semantic_coherence_guard_v1.py", "--repo-root", str(repo), "--write-report"], cwd=repo, check=True, text=True)

    print("PASS_P004_SEAT_AXIAL_TOLERANCE_BUDGET_DECIDED__DOWNSTREAM_PART_ALLOCATIONS_EXPLICIT")
    print("EDR: EDR-046")
    print("SEAT_BUDGET_LOW/HIGH_MM: 0.020 / 0.020")
    print("AXIAL_BUDGET_LOW/HIGH_MM: 0.010 / 0.030")
    print("PRODUCTION_TOLERANCE_SPLIT: OPEN__CAPABILITY_EVIDENCE_REQUIRED")
    print("NEXT:", blocker)
    print("NATIVE_MUTATION: NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
