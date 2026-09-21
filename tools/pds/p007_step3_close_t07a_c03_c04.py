from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


def load(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def dump(p: Path, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_char(rows, cid):
    for r in rows:
        if r.get("id") == cid:
            return r
    raise RuntimeError(f"missing characteristic {cid}")


def replace_once(text: str, old: str, new: str) -> str:
    return text.replace(old, new, 1) if old in text else text


def modernize_pds_source(path: Path):
    """Make PDS regeneration aware of EDR-027 and closed C03/C04.

    Uses structural line anchors, not volatile generated JSON content.
    Idempotent: if the EDR-027 marker is already present, only wording cleanup runs.
    """
    txt = path.read_text(encoding="utf-8")
    marker = "EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE"

    if marker not in txt:
        lines = txt.splitlines(keepends=True)
        i0 = next((i for i, line in enumerate(lines) if line == "    analysis_block=[]\n"), None)
        i1 = next((i for i, line in enumerate(lines) if i0 is not None and i > i0 and line.startswith('    stages["6_VARIATION_PROCESS_INSPECTION"]=stage(')), None)
        if i0 is None or i1 is None:
            raise RuntimeError("PDS Stage-5 anchors not found; refusing ambiguous source mutation")

        new_stage = '''    t07a_edr=repo/"control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json"\n    t07a_pass=t07a_edr.is_file()\n    pressure_hold=(gm.get("pressure_vacuum_sealing") or {}).get("status","").startswith("HOLD")\n    analysis_block=[]\n    if (not t07a_pass) and (gm.get("buckling_stability") or {}).get("status")=="STALE": analysis_block.append("buckling_stability STALE")\n    if pressure_hold: analysis_block.append("pressure_vacuum_sealing HOLD")\n    if t07a_pass and pressure_hold:\n        analysis_status="HOLD_PRESSURE_VACUUM_SEALING__T07A_PASS"\n        analysis_why="EDR-027 closes current P007 global +0.20 bar static and -0.20 bar linear buckling. Analysis remains HOLD only for pressure/vacuum/sealing closure outside T07A."\n        analysis_next=["Close seal/media/leak pressure-vacuum requirements; do not rerun T07A unless an EDR-027 stale trigger fires."]\n    elif analysis_block:\n        analysis_status="HOLD_ANALYSIS_REFRESH"\n        analysis_why="Required P007 analysis evidence is incomplete."\n        analysis_next=["Close the listed analysis blockers."]\n    else:\n        analysis_status="PASS_WITH_LIMIT"\n        analysis_why="Current required P007 analysis screens are controlled for this lifecycle stage."\n        analysis_next=[]\n    stages["5_ANALYSIS"]=stage(\n        analysis_status,analysis_why,\n        [str(sp.relative_to(repo)).replace("\\\\","/") if sp else None,\n         "control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json",\n         "control/project/K01_PROJECT_CLOSURE_MATRIX.json"],\n        analysis_block,analysis_next)\n'''.splitlines(keepends=True)
        lines[i0:i1] = new_stage

        # Insert a dynamic queue filter immediately before assess() returns its state.
        qidx = next((i for i, line in enumerate(lines) if '"task":"Run T07A current P007 pressure-shell refresh:' in line), None)
        if qidx is None:
            raise RuntimeError("PDS T07A queue entry anchor not found")
        ridx = next((i for i, line in enumerate(lines) if i > qidx and line == "    return {\n"), None)
        if ridx is None:
            raise RuntimeError("PDS assess-return anchor not found")
        queue_filter = '''    if t07a_pass:\n        queue=[q for q in queue if "Run T07A current P007 pressure-shell refresh" not in str(q.get("task",""))]\n    for i,q in enumerate(queue,1): q["priority"]=i\n\n'''.splitlines(keepends=True)
        lines[ridx:ridx] = queue_filter
        txt = "".join(lines)

    txt = replace_once(
        txt,
        '"Close C03/C04/C07/C08/C11 functional stacks"',
        '"Close C07/C08/C11 coupled radial stack and remaining C01/C05/C06/blind-end tolerances"',
    )
    txt = replace_once(
        txt,
        '"Close C03/C04/C07/C08/C11 functional tolerance stacks"',
        '"Close C07/C08/C11 coupled radial envelope and remaining functional tolerances"',
    )
    txt = replace_once(
        txt,
        '["functional tolerance stack","thin-wall/blind-end manufacturing capability","seal/media/leak definition","fastener/process qualification","inspection plan"]',
        '["C07/C08/C11 radial stack + C01/C05/C06/blind-end tolerance closure","thin-wall/blind-end manufacturing capability","seal/media/leak definition","fastener/process qualification","inspection plan"]',
    )
    txt = replace_once(
        txt,
        '"blocked_by":["Stage 5 required T07A evidence","Stage 6 release blockers","Product Definition DRAWING_RELEASE_READY"]',
        '"blocked_by":["Stage 5 pressure/vacuum/sealing release hold","Stage 6 release blockers","Product Definition DRAWING_RELEASE_READY"]',
    )
    path.write_text(txt, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    a = ap.parse_args()
    root = Path(a.repo_root).resolve()

    for rel in [
        "control/decisions/EDR-025_P007_MONOLITHIC_REMOVABLE_J2_BASELINE.json",
        "control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json",
        "control/decisions/EDR-028_P007_C03_C04_RELEASE.json",
    ]:
        if not (root / rel).is_file():
            raise RuntimeError(f"MISSING authority: {rel}")

    # 1. T07A source state: close only the global pressure-shell lane.
    p = root / "control/analysis/K01_T07_P007_STRUCTURAL_REFRESH.json"
    d = load(p)
    d["status"] = "T07A_PASS_ENGINEERING_SCREEN__T07B_LOCAL_J2_DEPENDENT"
    d["decision"] = "EDR-026_T07_PRESSURE_ONLY_SCOPE + EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE"
    d["T07A_current_result"] = {
        "decision": "EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE",
        "status": "PASS_ENGINEERING_SCREEN",
        "static": {
            "sigma_vm_max_MPa": 0.6147,
            "displacement_max_mm": 6.257e-05,
            "reaction_N": 3.1229,
            "FoS_screen_170MPa": 276.56,
        },
        "buckling": {"lambda1": 1918.67, "equivalent_critical_pressure_bar": 383.734},
        "mesh_convergence": "WAIVED_BY_ENGINEERING_JUDGMENT_PER_EDR-027",
        "stale_triggers": [
            "P007 geometry/material/wall change",
            "fixture/load boundary change",
            "released differential-pressure change",
        ],
    }
    dump(p, d)

    p = root / "control/technical_filter/K01_J2_C2R1_TECHNICAL_FILTER_v1.json"
    d = load(p)
    for g in d.get("gates", []):
        if g.get("gate") == "buckling_stability":
            g["status"] = "PASS"
            g["basis"] = "Current C2R1 P007 T07A: lambda1=1918.67 at -0.20 bar reference pressure; project screen floor lambda1>=10. Accepted by EDR-027."
            g["evidence_ids"] = ["EDR-027", "T07A-20260914"]
            g["open_actions"] = []
    dump(p, d)

    # 2. Standards/source registry used by EDR-028.
    p = root / "control/evidence/K01_SOURCE_REGISTRY_v2.json"
    d = load(p)
    rows = d.setdefault("sources", [])
    additions = [
        {
            "source_id": "SRC-GPS-ISO2692-001",
            "type": "standard",
            "title": "ISO 2692:2021 — GPS — Maximum material requirement (MMR), least material requirement (LMR) and reciprocity requirement (RPR)",
            "publisher": "ISO",
            "location": "https://www.iso.org/standard/74592.html",
            "relevance": "MMR/virtual-condition control where size and geometry are interdependent for assembly",
            "status": "PUBLISHED_CURRENT_EDITION_UNDER_SYSTEMATIC_REVIEW_2026",
        },
        {
            "source_id": "SRC-FIT-ISO286-2-001",
            "type": "standard",
            "title": "ISO 286-2 — ISO system of limits and fits — tolerance classes and limit deviations",
            "publisher": "ISO",
            "location": "controlled standard / ISO 286-2",
            "relevance": "Ø14.10 H7/g6 fit limits and Ø2.90 H10 hole tolerance",
            "status": "STANDARD_REFERENCE",
        },
        {
            "source_id": "SRC-FASTENER-ISO273-001",
            "type": "standard",
            "title": "ISO 273:1979 — Fasteners — Clearance holes for bolts and screws",
            "publisher": "ISO",
            "location": "https://www.iso.org/standard/4183.html",
            "relevance": "M2.5 medium-series clearance-hole nominal Ø2.90; project H10 tolerance is tighter by design",
            "status": "CURRENT_CONFIRMED_2024",
        },
    ]
    have = {x.get("source_id") for x in rows}
    rows.extend(x for x in additions if x["source_id"] not in have)
    dump(p, d)

    # 3. Product Definition: release C03 and C04 as controlled requirements.
    p = root / "control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json"
    d = load(p)
    chars = d.get("characteristics", [])

    c = find_char(chars, "C03")
    c.update(
        {
            "definition_state": "CONTROLLED",
            "nominal_or_requirement": {
                "relationship": "locator axis to Datum A",
                "P007_fit": "Ø14.10 H7",
                "P003_counterpart_fit": "Ø14.10 g6",
                "common_virtual_condition_mm": 14.097,
            },
            "variation_semantics": {
                "perpendicularity": "Ø0.003(M) to A at MMC",
                "P003_counterpart_perpendicularity": "Ø0.003(M) to A at MMC",
            },
            "authority_sources": [
                "REQ-K01-J2-LOC-001",
                "EDR-028_P007_C03_C04_RELEASE",
                "SRC-FIT-ISO286-2-001",
                "SRC-GPS-ISO2692-001",
                "SRC-GPS-ISO1101-001",
            ],
            "cad_binding": "DERIVED_BINDING_READY_C02_AXIS_TO_DATUM_A",
            "mbd_carrier": "DimXpert/GD&T perpendicularity on C02 bore axis with MMR",
            "drawing_projection": "PROJECT PERP Ø0.003(M) | A on C02 locator-bore axis",
            "inspection": "CMM with MMR evaluation or qualified functional-gage equivalent; first-article capability confirmation before P6",
            "release_blocking": False,
        }
    )

    c = find_char(chars, "C04")
    c.update(
        {
            "definition_state": "CONTROLLED",
            "nominal_or_requirement": {
                "count": 3,
                "hole_diameter_mm": 2.9,
                "hole_limits_mm": [2.9, 2.94],
                "through": True,
                "pcd_mm": 26.5,
                "equal_spacing_deg": 120.0,
            },
            "variation_semantics": {
                "hole_size_tolerance": "H10 (0/+0.040 mm at Ø2.90)",
                "pcd": "BASIC",
                "equal_spacing": "BASIC",
                "position_tolerance": "Ø0.15 | A | B",
            },
            "authority_sources": [
                "canonical native geometry",
                "WP-T03",
                "EDR-028_P007_C03_C04_RELEASE",
                "SRC-FIT-ISO286-2-001",
                "SRC-FASTENER-ISO273-001",
            ],
            "cad_binding": "PASS_CANONICAL_PERSISTENT_REF",
            "mbd_carrier": "DimXpert hole pattern + position FCF",
            "drawing_projection": "PROJECT 3×Ø2.90 H10 THRU; PCD Ø26.50 BASIC; 120° BASIC; POSITION Ø0.15 | A | B",
            "inspection": "2.900 GO / 2.940 NO-GO limit-gage (or equivalent bore measurement) + CMM pattern position to A|B",
            "release_blocking": False,
        }
    )

    rej = d.get("explicitly_rejected_legacy_semantics", [])
    d["explicitly_rejected_legacy_semantics"] = [x for x in rej if not x.startswith("C04 POS Ø0.15")]
    if "C03 PERP Ø0.03 TO A as released value" not in d["explicitly_rejected_legacy_semantics"]:
        d["explicitly_rejected_legacy_semantics"].append("C03 PERP Ø0.03 TO A as released value")
    dump(p, d)

    # Keep the legacy candidate registry explicitly historical so it cannot masquerade as current authority.
    p = root / "control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json"
    d = load(p)
    for r in d.get("characteristics", []):
        if r.get("id") == "C03":
            r["status"] = "SUPERSEDED_BY_EDR_028"
            r["current_state"] = "SUPERSEDED_LEGACY_CANDIDATE"
            r["authority_class"] = "HISTORICAL_CANDIDATE_ONLY"
        elif r.get("id") == "C04":
            r["status"] = "SUPERSEDED_BY_EDR_028_RELEASE_DEFINITION"
            r["current_state"] = "CONTROLLED_BY_EDR_028"
            r["authority_class"] = "NATIVE_GEOMETRY_PLUS_EDR_028_RELEASE_SEMANTICS"
    dump(p, d)

    # 4. Characteristic context / inspection route.
    p = root / "control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json"
    d = load(p)
    ctx = d.get("characteristics", {})
    c = ctx["C03"]
    c["datum_reference_system"]["status"] = "CONTROLLED_MMR_RELATIONSHIP"
    c["inspection_strategy"] = {"method": "CMM_MMR_OR_FUNCTIONAL_GAGE", "capability": "FIRST_ARTICLE_CONFIRMATION_REQUIRED"}
    c["drawing_authoring"]["targets"][0].update(
        {"authoring_class": "CONTROLLED_GDT", "action": "AUTHOR_RELEASE_GDT_AFTER_BINDING_SIGNATURE", "release_eligible": True}
    )
    c = ctx["C04"]
    c["datum_reference_system"].update({"references": ["A", "B"], "status": "CONTROLLED_AB"})
    c["inspection_strategy"] = {"method": "LIMIT_GAGE_PLUS_CMM_PATTERN", "capability": "STANDARD_INSPECTION"}
    c["drawing_authoring"]["targets"][0].update(
        {"authoring_class": "CONTROLLED_HOLE_PATTERN_GDT", "action": "AUTHOR_RELEASE_PATTERN_AFTER_BINDING_SIGNATURE", "release_eligible": True}
    )
    dump(p, d)

    # 5. Drawing intents: current values only. No CAD mutation here.
    p = root / "control/drawings/spec/K01-D-006_P007_DRAWING_INTENT_v1.json"
    d = load(p)
    for r in d.get("characteristics", []):
        if r.get("id") == "P007-C02":
            r["spec"] = "Ø14.10 H7 ×2.00; datum feature B = bore axis"
            r["source"] = "EDR-024 + C2R1"
        elif r.get("id") == "P007-C03":
            r["spec"] = "perpendicularity Ø0.003(M) to A"
            r["source"] = "EDR-028"
            r["inspection"] = "CMM MMR / functional gage"
        elif r.get("id") == "P007-C04":
            r["spec"] = "3× Ø2.90 H10 THRU; PCD Ø26.50 BASIC, 120° BASIC; position Ø0.15 | A | B"
            r["source"] = "EDR-028 + WP-T03"
            r["inspection"] = "2.900 GO / 2.940 NO-GO limit gage + CMM"
    dump(p, d)

    p = root / "control/drawings/spec/K01-D-003_P003_DRAWING_INTENT_v1.json"
    d = load(p)
    for r in d.get("characteristics", []):
        if r.get("id") == "P003-C03":
            r["spec"] = "perpendicularity Ø0.003(M) to A; datum feature B = pilot axis"
            r["source"] = "EDR-028"
            r["inspection"] = "CMM MMR / functional gage"
    dump(p, d)

    # 6. Closure workpack: remove completed tasks by semantic identity, not volatile priority numbers.
    p = root / "control/workpacks/K01_P007_PRODUCT_DEFINITION_CLOSURE_v1.json"
    d = load(p)
    d["status"] = "IN_PROGRESS__T07A_C03_C04_CLOSED__RADIAL_FILTER_ACTIVE"
    for r in d.get("technical_filter", []):
        if r.get("id") == "C03":
            r.update(
                {
                    "candidate": "legacy perpendicularity Ø0.03 to A",
                    "disposition": "REJECT_0P03__ACCEPT_PERP_0P003_MMR_EDR_028",
                    "next": "Closed. Reopen only if H7/g6, pilot engagement, face architecture or manufacturing capability changes.",
                }
            )
        elif r.get("id") == "C04":
            r.update(
                {
                    "candidate": "position Ø0.15 |A|B + Ø2.90 hole",
                    "disposition": "ACCEPT_RELEASE_EDR_028__HOLE_2P90_H10__POS_0P15_AB",
                    "next": "Closed definition. T05 local flange/contact verification remains a stale trigger, not a current C04 definition blocker.",
                }
            )

    q = []
    for x in d.get("immediate_execution_queue", []):
        atext = str(x.get("action", ""))
        if "Regenerate Product Definition and EBOM/MBOM after EDR-025" in atext:
            continue
        if "Run T07" in atext:
            continue
        if "C03 orientation stack" in atext or "freeze C04" in atext:
            continue
        if "C07/C08/C11 coupled radial envelope" in atext:
            continue
        q.append(x)
    q.insert(
        0,
        {
            "priority": 1,
            "action": "Close C07/C08/C11 coupled radial envelope and allocate the 0.050 mm inner radial budget.",
            "mode": "ENGINEERING_CALCULATION",
        },
    )
    for i, x in enumerate(q, 1):
        x["priority"] = i
    d["immediate_execution_queue"] = q
    dump(p, d)

    # 7. Persistent release-gap register; create if Step 2 baseline did not have one.
    p = root / "control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json"
    if p.is_file():
        d = load(p)
    else:
        d = {
            "schema": "k01_p007_release_gap_register_v1",
            "part": "K01-P-007",
            "status": "OPEN_RELEASE_GAPS",
            "closed_do_not_restart": [],
            "active_engineering_gaps": [
                {"id": "C03", "status": "OPEN", "topic": "locator-axis orientation/perpendicularity"},
                {"id": "C04", "status": "OPEN", "topic": "clamp-hole pattern size/position release"},
                {"id": "C07_C08_C11", "status": "OPEN", "topic": "coupled radial envelope"},
                {"id": "C01_C05_C06_BLIND_END", "status": "OPEN", "topic": "remaining dimensional/form tolerance closure"},
                {"id": "SEAL_LEAK_PROCESS_INSPECTION", "status": "OPEN", "topic": "seal/media/leak/process/inspection closure"},
            ],
        }
    d["generated_utc"] = datetime.now(timezone.utc).isoformat()
    closed = d.setdefault("closed_do_not_restart", [])
    for x in [
        "T07A global +0.20 bar static and -0.20 bar buckling via EDR-027",
        "C03 J2 locator-axis orientation via EDR-028 MMR virtual-condition control",
        "C04 P007 clamp-hole size/position release via EDR-028 + T03",
    ]:
        if x not in closed:
            closed.append(x)
    d["active_engineering_gaps"] = [x for x in d.get("active_engineering_gaps", []) if x.get("id") not in ("C03", "C04")]
    dump(p, d)

    # 8. PDS source itself must no longer resurrect closed tasks.
    modernize_pds_source(root / "tools/pds/k01_pds.py")

    # 9. Current next action: mutate semantically at runtime; do not ship generated JSON diffs in the patch.
    p = root / "control/project/K01_NEXT_ACTIONS_CURRENT.json"
    d = load(p)
    d["generated_utc"] = datetime.now(timezone.utc).isoformat()
    d["active_line"] = "K01-P007-PRODUCT-DEFINITION-CLOSURE"
    d["current_stage"] = "P007 Product Definition Closure — T07A/C03/C04 closed; coupled radial tolerance closure active"
    d["last_completed"] = "EDR-027 T07A global pressure-shell screen + EDR-028 C03/C04 release definition"
    d["current_blocker"] = "Full K01-D-006 remains blocked by C07/C08/C11 radial stack, C01/C05/C06/blind-end tolerances, seal/leak/process/inspection and BOM release gaps."
    d["next_1"] = "Close C07/C08/C11 coupled radial envelope using the existing 0.050 mm inner radial budget. Do not return to drawing authoring yet."
    d["execution_mode"] = "ENGINEERING_DECISION"
    seq = [x for x in d.get("engineering_sequence", []) if "T07A" not in x and "C03/C04" not in x]
    if not seq or "C07/C08/C11 coupled radial envelope" not in seq[0]:
        seq.insert(0, "C07/C08/C11 coupled radial envelope")
    d["engineering_sequence"] = seq
    auth = d.setdefault("authority", [])
    for x in [
        "control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json",
        "control/decisions/EDR-028_P007_C03_C04_RELEASE.json",
    ]:
        if x not in auth:
            auth.append(x)
    dump(p, d)

    print("STEP3_SOURCE_UPDATE: PASS")
    print("T07A: PASS_ENGINEERING_SCREEN / EDR-027")
    print("C03: RELEASE PERP Ø0.003(M) | A on H7 bore and g6 pilot; common VC=14.097 mm")
    print("C04: RELEASE 3x Ø2.90 H10 THRU; PCD26.50 BASIC; 120 BASIC; POS Ø0.15 | A | B")
    print("NEXT: C07/C08/C11 coupled radial envelope")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
