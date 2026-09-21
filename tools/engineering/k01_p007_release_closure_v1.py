from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

Q_HE_LIMIT = 1.0e-5  # mbar L/s
REPO_DEFAULT = Path(r"D:\BreshevEngineering\marvilon-k01")
LOCAL_DEFAULT = Path(r"D:\BreshevEngineering\K01_local")

REQ_PATH = Path("control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json")
NONMODELED_PATH = Path("control/product/K01_J2_NONMODELED_ITEMS.json")
MFG_PATH = Path("control/manufacturing/K01_P007_MANUFACTURING_FEASIBILITY_CURRENT.json")
EDR032_PATH = Path("control/decisions/EDR-032_P007_C02_LOCATOR_DEPTH_RELEASE.json")
DRAWING_CONTROL_PATH = Path("reports/control/K01_DRAWING_CONTROL_CURRENT.json")
TEMPORAL_PATH = Path("reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json")

EDR035_PATH = Path("control/decisions/EDR-035_J2_MEDIA_SEAL_LEAK_RELEASE.json")
EDR036_PATH = Path("control/decisions/EDR-036_J2_FASTENER_SERVICE_RELEASE.json")
EDR037_PATH = Path("control/decisions/EDR-037_P007_RELEASE_COMPLETION.json")
INSPECTION_PATH = Path("control/inspection/K01_P007_INSPECTION_PLAN_CURRENT.json")
PD_RELEASE_PATH = Path("control/product_definition/K01_P007_PRODUCT_DEFINITION_RELEASE_CURRENT.json")
REPORT_PATH = Path("reports/product_definition/current/K01_P007_RELEASE_CLOSURE_CURRENT.json")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    print(">", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, text=True, check=check)


def iter_dicts(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from iter_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_dicts(v)


def find_by_key_value(obj: Any, key: str, value: str) -> dict | None:
    for d in iter_dicts(obj):
        if d.get(key) == value:
            return d
    return None


def status_is_pass(obj: Any) -> bool:
    if isinstance(obj, dict):
        for key in ("status", "temporal_coherence", "verdict"):
            v = obj.get(key)
            if isinstance(v, str) and "PASS" in v.upper() and "HOLD" not in v.upper():
                return True
    return False


def add_unique_evidence(req: dict, path: str) -> None:
    ev = req.setdefault("evidence", [])
    if isinstance(ev, list) and path not in ev:
        ev.append(path)


def verify_c02(repo: Path) -> dict:
    p = repo / EDR032_PATH
    if not p.exists():
        raise RuntimeError("EDR-032 missing: C02 may not be re-invented.")
    data = read_json(p)
    txt = json.dumps(data, ensure_ascii=False)
    required_tokens = ["2.00", "0.05", "1.50", "0.40", "0.60"]
    if not all(t in txt for t in required_tokens):
        raise RuntimeError("EDR-032 exists but released C02/non-bottoming values cannot be verified.")
    status = str(data.get("status", ""))
    if "ACCEPTED" not in status.upper() and "RELEASE" not in status.upper():
        raise RuntimeError(f"EDR-032 is not release/accepted: {status}")
    return {
        "authority": str(EDR032_PATH).replace("\\", "/"),
        "status": status,
        "P007_locator_depth_mm": "2.00 ±0.05",
        "P003_pilot_length_mm": "1.50 ±0.05",
        "worst_case_bottom_clearance_mm": "0.40...0.60",
        "action": "NO_NEW_DESIGN_DECISION__PROPAGATE_EXISTING_RELEASE"
    }


def backup_files(repo: Path, local_root: Path, paths: list[Path]) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = local_root / "backups" / f"P007_CLOSURE_{stamp}"
    for rel in paths:
        src = repo / rel
        if src.exists():
            dst = bdir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return bdir


def reconcile_and_guard(repo: Path) -> None:
    run([sys.executable, "tools/state/k01_current_state_reducer_v1.py", "--repo-root", str(repo)], repo)
    run([sys.executable, "tools/state/k01_temporal_coherence_guard_v1.py",
         "--repo-root", str(repo), "--write-report"], repo)
    tr = repo / TEMPORAL_PATH
    if not tr.exists() or not status_is_pass(read_json(tr)):
        raise RuntimeError("Temporal coherence did not reach PASS.")


def make_edr035() -> dict:
    return {
        "schema": "k01.edr.v1",
        "id": "EDR-035",
        "title": "J2 service media, static seal and C12 leak acceptance release",
        "generated_utc": now_utc(),
        "status": "ACCEPTED_RELEASE_DEFINITION",
        "scope": "K01-P-003 ↔ K01-P-007 J2 removable containment interface",
        "request": "Close REQ-K01-MEDIA-001, REQ-K01-SEAL-001 and REQ-K01-LEAK-001 using the documented MARV application and an explicit K01 quantitative containment acceptance.",
        "decision": {
            "service_media": {
                "applicability": [
                    "documented MARV BOF/BF-type process-gas service",
                    "CO-bearing process gas",
                    "water vapour / high humidity / possible condensate",
                    "dust / process particulates",
                    "dry N2 purge"
                ],
                "local_temperature_max_C": 55.0,
                "differential_pressure_bar": [-0.20, 0.20],
                "cleaning": "No intentionally applied liquid cleaning chemical at J2 in the released internal-service baseline.",
                "high_pressure_purge_exclusion": "6 bar probe/filter purge is excluded from the optical-module/J2 load path by system valve routing.",
                "requalification_triggers": [
                    "new corrosive/acidic/solvent species not covered by current MARV service",
                    "intentional liquid cleaner contact at J2",
                    "temperature > 55 C",
                    "|differential pressure| > 0.20 bar",
                    "seal material family or gland geometry change"
                ]
            },
            "seal": {
                "architecture": "static face O-ring",
                "size_mm": "16 x 1.5",
                "gland": "existing controlled J2 gland retained",
                "material_requirement": "FKM, 75 ±5 Shore A, post-cured production grade",
                "supplier_lot_boundary": "Exact supplier compound/lot and CoC are incoming/procurement qualification, not geometry-definition blockers.",
                "fallback": "FFKM only if later compatibility evidence invalidates FKM for the released media envelope."
            },
            "C12": {
                "characteristic": "integral J2 leak / containment acceptance",
                "acceptance_qHe_mbar_L_s_max": Q_HE_LIMIT,
                "test_differential_pressure_bar_abs": 0.20,
                "pressure_directions": "both directions unless equivalence is explicitly justified",
                "measurement_temperature_C": "20 ±5",
                "method": "calibrated helium tracer-gas integral/local method with stated tracer concentration, reference leak, background, test pressure and result",
                "production_screening": "pressure-decay/gross-leak method allowed only after correlation to this quantitative acceptance",
                "physical_verification_state": "OPEN_L8_QUALIFICATION"
            }
        },
        "rationale": {
            "containment_function": "The MARV protection concept requires no normal release, only abnormal limited release.",
            "containment_inlet_limit": "200 mbar documented maximum inlet pressure to containment system",
            "system_flow_context": "40 L/min documented maximum containment-system flow",
            "q_limit_origin": "K01 engineering acceptance decision. It is NOT claimed to be supplied by IEC or a vacuum handbook.",
            "q_limit_scale": "1e-5 mbar L/s corresponds to about 0.864 mL/day referenced to ~1 bar, approximately 1.5e-8 of 40 L/min on a daily-volume basis.",
            "methodology_note": "Vacuum literature is used for leak-test method principles, not to invent the product acceptance number."
        },
        "requirements_closed": ["REQ-K01-MEDIA-001", "REQ-K01-SEAL-001", "REQ-K01-LEAK-001"],
        "downstream": ["P007 Product Definition", "D006", "EBOM/MBOM", "J2 physical leak qualification"]
    }


def make_edr036() -> dict:
    return {
        "schema": "k01.edr.v1",
        "id": "EDR-036",
        "title": "J2 M2.5 clamp fastener, preload, locking and service definition",
        "generated_utc": now_utc(),
        "status": "ACCEPTED_RELEASE_DEFINITION",
        "scope": "Three-screw P003↔P007 J2 clamp",
        "decision": {
            "fastener": {
                "quantity": 3,
                "standard": "ISO 4762",
                "thread": "M2.5 x 0.45",
                "length_mm": 6.0,
                "material_grade": "A4-70 stainless steel",
                "P007_clearance_hole": "Ø2.90 H10 released pattern",
                "P003_thread": "M2.5 x 0.45-6H DEEP 5.00",
                "nominal_thread_engagement_mm": 3.0,
                "nominal_bottom_clearance_mm": 2.0,
                "minimum_required_effective_engagement_mm": 2.5,
                "minimum_required_bottom_clearance_mm": 1.0
            },
            "preload": {
                "acceptance_N_per_screw": [200.0, 300.0],
                "target_N_per_screw": 250.0,
                "basis": "Existing J2 local thread/proof/contact screening passes the 200–300 N/screw architecture."
            },
            "assembly_process": {
                "locking": "low-strength anaerobic threadlocker for small fasteners; released baseline product LOCTITE 222 or procurement-controlled direct equivalent",
                "screw_reuse": "single-use screw after a J2 opening",
                "seal_reuse": "replace O-ring after each J2 opening",
                "torque_policy": "No generic handbook torque is released. Production torque shall be calibrated with the released screw/thread/locking condition to achieve 200–300 N/screw, target 250 N/screw.",
                "witness": "external torque/witness mark after final tightening",
                "galling_control": "clean undamaged stainless threads; locking-process/torque qualification shall include galling inspection"
            },
            "service": {
                "requirement_cycles_min": 50,
                "cycle_definition": "complete J2 disassembly and reassembly",
                "qualification": "P003/P007 threads, locating features and mating/seal surfaces shall survive 50 cycles with replacement seal and single-use clamp screws; C12 shall pass after qualification.",
                "physical_verification_state": "OPEN_L8_QUALIFICATION"
            }
        },
        "requirements_closed": ["REQ-K01-SERVICE-CYCLES-001"],
        "downstream": ["J2 clamp process", "EBOM/MBOM", "service qualification"]
    }


def inspection_plan() -> dict:
    common = {
        "reference_temperature_C": 20.0,
        "allowed_lab_temperature_C": "20 ±2",
        "stabilization": "part and measuring equipment thermally stabilized before acceptance measurement",
        "FAI": "required for first released manufacturing route and after process/source change affecting characteristic"
    }
    chars = [
        ["C01", "Datum-A flatness / common zone", "CMM or validated surface-mapping setup", "EDR-030"],
        ["C02", "Ø14.10 H7 locator + 2.00 ±0.05 depth", "calibrated bore gauge/CMM + depth measurement", "EDR-032"],
        ["C03", "locator-axis orientation to Datum A", "CMM", "EDR-028"],
        ["C04", "3x Ø2.90 H10 / PCD26.50 / 120° / position", "CMM", "EDR-033"],
        ["C05", "Ø33.00 ±0.05 / flange thickness 3.00 ±0.05", "micrometer/CMM", "EDR-030"],
        ["C06", "overall length 35.00 ±0.05", "micrometer/CMM", "EDR-030"],
        ["C07", "thin-can OD Ø10 h9", "low-force micrometer or roundness/CMM setup avoiding collapse", "EDR-029"],
        ["C08", "thin-can ID Ø9.40 H9 / wall reference", "air/bore gauge or CMM/roundness method qualified for thin wall", "EDR-029"],
        ["C09", "can internal functional length", "CMM/depth method", "controlled Product Definition"],
        ["C10", "containment construction/process", "route/visual/process-record verification", "EDR-025 + EDR-037"],
        ["C11", "total runout 0.02 to datum axis B", "roundness tester or validated CMM/mandrel setup", "EDR-029"],
        ["C12", "J2 leak acceptance qHe <= 1e-5 mbar L/s", "calibrated helium tracer-gas leak test", "EDR-035"],
        ["K01-D006-BLIND-END", "blind-end thickness 1.00 ±0.10", "CMM/depth or qualified ultrasonic/section-equivalent method", "EDR-030"],
        ["SURFACE-J2", "J2 seal-contact surface Ra <= 0.8 µm", "profilometer", "EDR-037"]
    ]
    return {
        "schema": "k01.inspection_plan.p007.v1",
        "generated_utc": now_utc(),
        "status": "DEFINED_FOR_PRODUCT_DEFINITION__FAI_PHYSICAL_EXECUTION_OPEN",
        "part": "K01-P-007",
        "measurement_conditions": common,
        "characteristics": [
            {"id": c[0], "role": c[1], "method": c[2], "authority": c[3], "result_state": "NOT_YET_MEASURED_PHYSICAL_QUALIFICATION"}
            for c in chars
        ]
    }


def make_edr037(repo: Path) -> dict:
    dc = repo / DRAWING_CONTROL_PATH
    dc_sha = sha256(dc) if dc.exists() else None
    return {
        "schema": "k01.edr.v1",
        "id": "EDR-037",
        "title": "P007 release completion: surface, manufacturing, inspection, measurement and effectivity",
        "generated_utc": now_utc(),
        "status": "ACCEPTED_RELEASE_DEFINITION",
        "scope": "K01-P-007 Product Definition completion before D006 release pipeline",
        "decision": {
            "surface_texture": {
                "surface": "J2 Datum-A seal-contact face only",
                "requirement": "Ra <= 0.8 µm",
                "inspection": "profilometer",
                "basis": "EDR-031 engineering-review candidate promoted after EDR-035 media/seal/leak definition."
            },
            "edge_condition": {
                "status": "ALREADY_RELEASED_EDR030",
                "rule": "deburr; break non-functional sharp edges 0.1–0.2 mm; do not break/abrade Datum A, locator, seal or controlled functional edges"
            },
            "C02": verify_c02(repo),
            "manufacturing_route": {
                "status": "ACCEPTED_DESIGN_ROUTE__PHYSICAL_FAI_CAPABILITY_OPEN",
                "route": [
                    "certified EN 1.4404 / AISI 316L stock",
                    "deep-bore ID 9.40 leaving integral blind end",
                    "finish Ø14.10 H7 locator and controlled depth",
                    "supported finish of Ø10 thin wall",
                    "machine Ø33 x 3 flange and overall length",
                    "drill 3x Ø2.90 H10 pattern on PCD26.50",
                    "deburr with protected functional edges",
                    "clean/passivate using released stainless route",
                    "dimensional/geometry/surface inspection",
                    "J2 leak qualification at assembly level"
                ],
                "physical_qualification_open": [
                    "0.30 mm wall ovality/collapse capability",
                    "runout capability",
                    "fixture/support method",
                    "blind-end capability",
                    "FAI evidence"
                ],
                "important": "Physical process capability remains L8 evidence; it does not make the design definition OPEN."
            },
            "measurement_conditions": inspection_plan()["measurement_conditions"],
            "inspection_plan": str(INSPECTION_PATH).replace("\\", "/"),
            "configuration_effectivity": {
                "baseline": "K01-CP-20260910-BASELINE-02C-PROMOTED",
                "P007_definition": "EDR-025 through EDR-037",
                "drawing_control_sha256_at_decision": dc_sha,
                "binding_mode": "PINNED_CONTROLLED_CONFIGURATION",
                "invalidation_rule": "Any P007 native geometry hash/revision change or released characteristic change invalidates D006/PMI binding and requires re-verification."
            },
            "stale_projection_resolution": {
                "C01_C05_C06_blind_end": "Released by EDR-030; any PARTIAL readiness projection is stale and shall be rebuilt, not re-engineered.",
                "C02": "Released by EDR-032; do not reopen.",
                "C03_C04": "Released by EDR-028/033.",
                "C07_C08_C11": "Released by EDR-029.",
                "weld_process": "N/A / superseded by monolithic P007 baseline EDR-025."
            }
        },
        "downstream": ["P007 Product Definition READY record", "D006 final Drawing Spec", "semantic QA", "D8"]
    }


def update_requirements(reqdoc: Any) -> None:
    changes = {
        "REQ-K01-MEDIA-001": {
            "requirement_status": "RELEASED",
            "statement": "For the current MARV application, J2 contact media are bounded to documented BOF/BF-type CO-bearing process gas, water vapour/high humidity/possible condensate, dust/particulates and dry N2 purge. No intentional liquid cleaner contact at J2 is included. Any new aggressive/solvent species or envelope change requires requalification.",
            "verification_method": "EDR-035 applicability + released seal material basis + J2 leak qualification",
            "release_blocker": False,
            "verification_state": "DESIGN_DEFINITION_RELEASED__PHYSICAL_QUALIFICATION_OPEN"
        },
        "REQ-K01-SEAL-001": {
            "requirement_status": "RELEASED",
            "statement": "J2 shall use the released 16 x 1.5 mm static face O-ring architecture with FKM 75 ±5 Shore A post-cured production grade over the released media, 55 C and ±0.20 bar envelope.",
            "verification_method": "EDR-035 + gland/tolerance definition + C12 physical leak qualification",
            "release_blocker": False,
            "verification_state": "DESIGN_DEFINITION_RELEASED__SUPPLIER_LOT_AND_PHYSICAL_QUALIFICATION_OPEN"
        },
        "REQ-K01-LEAK-001": {
            "requirement_status": "RELEASED",
            "statement": "Assembled J2 shall demonstrate helium-equivalent integral leakage q_He <= 1.0e-5 mbar·L/s at |Δp| = 0.20 bar under the released test conditions.",
            "verification_method": "Calibrated helium tracer-gas leak test per EDR-035; both pressure directions unless equivalence is justified",
            "release_blocker": False,
            "verification_state": "REQUIREMENT_RELEASED__PHYSICAL_TEST_OPEN"
        },
        "REQ-K01-SERVICE-CYCLES-001": {
            "requirement_status": "RELEASED",
            "statement": "The J2/P006 service architecture shall withstand at least 50 complete service cycles under EDR-036. J2 O-ring and clamp screws are replaced after each J2 opening in the released service baseline.",
            "verification_method": "50-cycle physical service qualification with thread/galling/locator/seal-face inspection and post-qualification C12 leak test",
            "release_blocker": False,
            "verification_state": "REQUIREMENT_RELEASED__PHYSICAL_50_CYCLE_QUALIFICATION_OPEN"
        }
    }
    for rid, vals in changes.items():
        r = find_by_key_value(reqdoc, "id", rid)
        if r is None:
            raise RuntimeError(f"Requirement not found: {rid}")
        for k, v in vals.items():
            r[k] = v
        edr = "control/decisions/EDR-035_J2_MEDIA_SEAL_LEAK_RELEASE.json" if rid != "REQ-K01-SERVICE-CYCLES-001" else "control/decisions/EDR-036_J2_FASTENER_SERVICE_RELEASE.json"
        add_unique_evidence(r, edr)


def update_nonmodeled(doc: Any) -> None:
    seal = find_by_key_value(doc, "registry_key", "NM-J2-SEAL")
    screw = find_by_key_value(doc, "registry_key", "NM-J2-CLAMP-SCREW")
    proc = find_by_key_value(doc, "registry_key", "NM-J2-FASTENER-PROCESS")
    weld = find_by_key_value(doc, "registry_key", "NM-P007-WELD-PROCESS")
    if seal:
        seal.update({
            "description": "J2 static face O-ring 16 x 1.5 FKM 75A",
            "material_authority": "EDR-035: FKM 75 ±5 Shore A, post-cured production grade",
            "material_status": "CONTROLLED_DESIGN_SPEC__SUPPLIER_LOT_QUALIFICATION_OPEN",
            "standard_or_specification": "EDR-035 / 16 x 1.5 mm static face O-ring",
            "release_state": "PASS_DESIGN_DEFINITION",
            "note": "Exact supplier compound/lot and CoC are procurement/incoming qualification. FFKM only by controlled requalification."
        })
    if screw:
        screw.update({
            "description": "J2 clamp screw ISO 4762 M2.5x6 A4-70",
            "part_number": "ISO 4762 M2.5x6 A4-70",
            "material_authority": "A4-70 stainless steel",
            "material_status": "CONTROLLED_DESIGN_SPEC",
            "standard_or_specification": "ISO 4762; M2.5x0.45; L=6 mm; A4-70; EDR-036",
            "release_state": "PASS_DESIGN_DEFINITION",
            "note": "3 pcs. Single-use after J2 opening. Production torque calibrated to released 200–300 N/screw preload."
        })
    if proc:
        proc.update({
            "description": "J2 fastener preload / locking / service process",
            "material_authority": "EDR-036",
            "material_status": "CONTROLLED_PROCESS_DEFINITION__PHYSICAL_CALIBRATION_OPEN",
            "standard_or_specification": "EDR-036: 200–300 N/screw, target 250 N; LOCTITE 222 baseline; torque by calibration",
            "release_state": "PASS_DESIGN_DEFINITION",
            "note": "No handbook torque is released. Same screw/thread/locking condition must be used in torque-preload calibration."
        })
    if weld:
        weld.update({
            "description": "P007 weld process — NOT APPLICABLE to released monolithic P007",
            "material_authority": "EDR-025 / EDR-037",
            "material_status": "N/A_SUPERSEDED_MONOLITHIC",
            "standard_or_specification": "N/A",
            "release_state": "N/A",
            "note": "Historical welded-construction residue. Released P007 baseline is monolithic."
        })
    for d in iter_dicts(doc):
        if d.get("id") == "MBOM-P007-WELDED-CONSTRUCTION":
            d.update({
                "status": "N/A_SUPERSEDED_MONOLITHIC",
                "mbom_representation": "MONOLITHIC_P007",
                "note": "Superseded by EDR-025 monolithic P007 baseline; no sleeve/flange weld decomposition in released design."
            })


def update_mfg(doc: Any) -> None:
    if not isinstance(doc, dict):
        return
    doc["release_decision"] = {
        "authority": "EDR-037",
        "status": "ACCEPTED_DESIGN_ROUTE__PHYSICAL_FAI_CAPABILITY_OPEN",
        "interpretation": "Manufacturing route is sufficiently defined for Product Definition. Physical capability/FAI remains L8 qualification.",
        "generated_utc": now_utc()
    }


def make_pd_release(repo: Path, c02: dict) -> dict:
    dc = repo / DRAWING_CONTROL_PATH
    return {
        "schema": "k01.product_definition.release.current.v1",
        "generated_utc": now_utc(),
        "part": "K01-P-007",
        "status": "READY_FOR_D006_RELEASE_PIPELINE",
        "product_definition_ready": True,
        "qualification_complete": False,
        "lifecycle_state": "L5_COMPLETE_FOR_DESIGN__L6_TPD_PIPELINE_ALLOWED",
        "authorities": [
            "EDR-025", "EDR-027", "EDR-028", "EDR-029", "EDR-030",
            "EDR-032", "EDR-033", "EDR-035", "EDR-036", "EDR-037"
        ],
        "C02_closeout": c02,
        "requirements": {
            "REQ-K01-MEDIA-001": "RELEASED",
            "REQ-K01-SEAL-001": "RELEASED",
            "REQ-K01-LEAK-001": "RELEASED",
            "REQ-K01-SERVICE-CYCLES-001": "RELEASED"
        },
        "surface_texture": "J2 seal-contact face Ra <= 0.8 µm",
        "manufacturing": "DESIGN_ROUTE_ACCEPTED__PHYSICAL_CAPABILITY_OPEN",
        "inspection": str(INSPECTION_PATH).replace("\\", "/"),
        "measurement_reference": "20 C; lab acceptance 20 ±2 C",
        "configuration": {
            "baseline": "K01-CP-20260910-BASELINE-02C-PROMOTED",
            "drawing_control_sha256": sha256(dc) if dc.exists() else None,
            "binding_mode": "PINNED_CONTROLLED_CONFIGURATION"
        },
        "downstream_allowed": [
            "compile final K01-D-006 Drawing Spec",
            "semantic QA",
            "D8 visual QA",
            "release-candidate publication"
        ],
        "physical_qualification_open": [
            "C12 physical leak test",
            "50-cycle service qualification",
            "manufacturing FAI/capability",
            "actual purchased seal/screw incoming qualification"
        ],
        "release_boundary": "READY means Product Definition is complete enough to author/release candidate TPD. It does not mean L8 physical qualification or L9 product release is complete."
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(REPO_DEFAULT))
    ap.add_argument("--local-root", default=str(LOCAL_DEFAULT))
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo_root)
    local_root = Path(args.local_root)
    if not repo.exists():
        raise SystemExit(f"Repo not found: {repo}")

    print("K01 P007 RELEASE CLOSURE v1")
    print("repo:", repo)
    print("mode:", "APPLY" if args.apply else "DRY-RUN")

    # Fail-closed current-state reconciliation before engineering mutation.
    reconcile_and_guard(repo)

    c02 = verify_c02(repo)
    print("C02:", c02["action"], c02["worst_case_bottom_clearance_mm"])

    reqp = repo / REQ_PATH
    if not reqp.exists():
        raise RuntimeError(f"Requirements authority missing: {reqp}")
    reqdoc = read_json(reqp)

    # Preflight required IDs.
    for rid in ("REQ-K01-MEDIA-001", "REQ-K01-SEAL-001", "REQ-K01-LEAK-001", "REQ-K01-SERVICE-CYCLES-001"):
        r = find_by_key_value(reqdoc, "id", rid)
        if r is None:
            raise RuntimeError(f"Missing requirement: {rid}")
        print(rid, "current=", r.get("requirement_status"))

    edr035 = make_edr035()
    edr036 = make_edr036()
    edr037 = make_edr037(repo)
    insp = inspection_plan()

    proposed_req = copy.deepcopy(reqdoc)
    update_requirements(proposed_req)

    nonmodeled = None
    if (repo / NONMODELED_PATH).exists():
        nonmodeled = read_json(repo / NONMODELED_PATH)
        update_nonmodeled(nonmodeled)

    mfg = None
    if (repo / MFG_PATH).exists():
        mfg = read_json(repo / MFG_PATH)
        update_mfg(mfg)

    pd_release = make_pd_release(repo, c02)

    print()
    print("PROPOSED:")
    print(" EDR-035 -> media/seal/C12")
    print(" EDR-036 -> fastener/preload/service")
    print(" EDR-037 -> Ra/manufacturing/inspection/effectivity")
    print(" P007 Product Definition -> READY_FOR_D006_RELEASE_PIPELINE")
    print(" C12 =", Q_HE_LIMIT, "mbar L/s @ |dP|=0.20 bar")
    print()

    if not args.apply:
        return 0

    backup_list = [REQ_PATH, NONMODELED_PATH, MFG_PATH, EDR035_PATH, EDR036_PATH, EDR037_PATH, INSPECTION_PATH, PD_RELEASE_PATH]
    bdir = backup_files(repo, local_root, backup_list)
    print("BACKUP:", bdir)

    write_json(repo / EDR035_PATH, edr035)
    write_json(repo / EDR036_PATH, edr036)
    write_json(repo / EDR037_PATH, edr037)
    write_json(repo / INSPECTION_PATH, insp)
    write_json(repo / REQ_PATH, proposed_req)
    if nonmodeled is not None:
        write_json(repo / NONMODELED_PATH, nonmodeled)
    if mfg is not None:
        write_json(repo / MFG_PATH, mfg)
    write_json(repo / PD_RELEASE_PATH, pd_release)

    report = {
        "schema": "k01.p007.release_closure.execution.v1",
        "generated_utc": now_utc(),
        "status": "PASS_PRODUCT_DEFINITION_READY__PHYSICAL_QUALIFICATION_OPEN",
        "part": "K01-P-007",
        "C02": c02,
        "decisions": [str(EDR035_PATH), str(EDR036_PATH), str(EDR037_PATH)],
        "product_definition_release": str(PD_RELEASE_PATH),
        "backup": str(bdir),
        "next": "Compile final D006 release spec from Product Definition; then semantic QA + D8."
    }
    write_json(repo / REPORT_PATH, report)

    # Recompute state after engineering decisions.
    reconcile_and_guard(repo)

    print()
    print("PASS: P007 PRODUCT DEFINITION = READY_FOR_D006_RELEASE_PIPELINE")
    print("PHYSICAL QUALIFICATION remains explicitly OPEN.")
    print("NEXT: compile final D006 release spec.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
