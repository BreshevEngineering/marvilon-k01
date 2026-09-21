from __future__ import annotations
import argparse, datetime as dt, json, re, subprocess, sys
from pathlib import Path

R = Path(r"D:\BreshevEngineering\marvilon-k01")
EDR46 = Path("control/decisions/EDR-046_P004_JOINT_TOLERANCE_BUDGET_20C.json")
EDR47 = Path("control/decisions/EDR-047_P004_CAPABILITY_BOUNDARY_AND_AXIAL_NOMINAL_RECENTER.json")
PD = Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ = Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
INSP = Path("reports/inspection/K01-P-004_INSPECTION_PLAN_CURRENT.json")
REP46 = Path("reports/engineering/K01_P004_JOINT_TOLERANCE_ALLOCATION_CURRENT.json")
REP47 = Path("reports/engineering/K01_P004_CAPABILITY_BOUNDARY_CURRENT.json")
NEXT = Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE = Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT = Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER = Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")
# EDR-047 was subsequently resolved by a canonical native CAD promotion to P004 L=7.990 mm.
# This legacy generator is retained for provenance only and is prohibited from recreating the
# superseded retain-L=8.000 / H=8.060 branch.
SUPERSEDED_BY_CANONICAL_EDR047 = Path("control/decisions/EDR-047_P004_AXIAL_RECENTER.json")



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
            cwd=repo, text=True
        )
        if cp.returncode:
            raise SystemExit("HOLD: state guard failed before EDR-047.")


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
    out=[]
    for x in items or []:
        sx=str(x)
        if any(tok.lower() in sx.lower() for tok in remove_tokens):
            continue
        out.append(x)
    for x in append_items:
        if x not in out:
            out.append(x)
    return out


def inventory(repo: Path):
    # Targeted evidence inventory only. Architecture/planning records do not count as measured capability.
    candidates=[]
    roots=[repo/"reports", repo/"control"]
    name_re=re.compile(r"p004", re.I)
    capability_re=re.compile(r"(fai|first.?article|inspection.?result|measurement.?result|process.?capab|metrolog.*capab|cpk|ppk|gage.?r|msa)", re.I)
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".json",".csv",".md",".txt"}:
                continue
            rel=p.relative_to(repo).as_posix()
            if name_re.search(rel) and capability_re.search(rel):
                candidates.append(rel)
    # Known architecture records are not physical measurements/capability proof.
    excluded_tokens=("DATUM_GPS_SURFACE_INSPECTION","INSPECTION_PLAN","CAPABILITY_BOUNDARY")
    physical=[x for x in sorted(set(candidates)) if not any(t.lower() in x.lower() for t in excluded_tokens)]
    return {"candidate_records": sorted(set(candidates)), "physical_or_statistical_capability_records": physical}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(R))
    ap.add_argument("--preflight-only", action="store_true")
    a=ap.parse_args()
    repo=Path(a.repo_root).resolve()

    if (repo/SUPERSEDED_BY_CANONICAL_EDR047).is_file():
        print("HOLD_SUPERSEDED_TOOL__EDR047_CANONICAL_NATIVE_PROMOTION_ALREADY_EXISTS")
        print("CANONICAL:",SUPERSEDED_BY_CANONICAL_EDR047)
        print("RULE: Do not recreate EDR-047 retain-L=8.000 / H=8.060 branch.")
        return 4

    required=[EDR46, PD, READ, INSP, REP46, NEXT, GATE, FRONT]
    missing=[str(x).replace("\\","/") for x in required if not (repo/x).is_file()]
    if missing:
        print("HOLD_MISSING_REQUIRED_AUTHORITIES")
        for x in missing: print("MISSING:",x)
        return 2

    run_guard(repo)
    n=rd(repo/NEXT,{}) or {}
    f=rd(repo/FRONT,{}) or {}
    edr46=rd(repo/EDR46,{}) or {}
    rep46=rd(repo/REP46,{}) or {}
    pd=rd(repo/PD,{}) or {}
    readiness=rd(repo/READ,{}) or {}
    insp=rd(repo/INSP,{}) or {}

    if n.get("next_action_id") != "K01-NA-P004-MANUFACTURING-METROLOGY-CAPABILITY":
        print("HOLD_WRONG_FRONTIER")
        print("EXPECTED: K01-NA-P004-MANUFACTURING-METROLOGY-CAPABILITY")
        print("ACTUAL:",n.get("next_action_id")); return 3
    if str((f.get("active_blocker") or {}).get("id")) != "P004-MANUFACTURING-METROLOGY-CAPABILITY-DECISION":
        print("HOLD_WRONG_BLOCKER"); print("ACTUAL:",f.get("active_blocker")); return 3
    if edr46.get("status") != "ACCEPTED_TOP_DOWN_TOLERANCE_BUDGET__PART_LEVEL_PRODUCTION_TOLERANCES_CAPABILITY_DEPENDENT":
        print("HOLD_EDR046_NOT_ACCEPTED"); return 3
    if rep46.get("status") != "PASS_P004_SEAT_AXIAL_TOLERANCE_BUDGET_DECIDED__DOWNSTREAM_PART_ALLOCATIONS_EXPLICIT":
        print("HOLD_EDR046_REPORT_NOT_PASS"); return 3

    inv=inventory(repo)
    physical=inv["physical_or_statistical_capability_records"]

    # Architecture math. Production tolerances remain deliberately unallocated.
    old_H=8.050; L=8.000; old_float=0.050
    target_float=0.060; target_H=L+target_float
    window=[0.040,0.080]
    centered_half_budget=min(target_float-window[0],window[1]-target_float)
    hot_shift=-0.003892
    cold_shift=+0.006672
    screen={
        "F20_target_mm": target_float,
        "F55_screen_mm": round(target_float+hot_shift,6),
        "Fminus40_extrapolated_screen_mm": round(target_float+cold_shift,6),
        "qualification_boundary": "55C engineering screen only; -40C remains L8 qualification/open because low-temperature material property is not directly controlled."
    }

    evidence_boundary={
        "route_feasibility": "SUPPORTED__CNC_MACHINING_OF_TECAPEEK_PVX/PEEK",
        "material_dimensional_stability": "SUPPORTED_QUALITATIVELY",
        "stress_relief_anneal_relevance": "SUPPORTED_QUALITATIVELY_FOR_NARROW_TOLERANCE_PEEK_MACHINING",
        "numeric_process_capability": "NOT_PROVEN_IN_CURRENT_REPO",
        "numeric_metrology_uncertainty": "NOT_PROVEN_IN_CURRENT_REPO",
        "supplier_lot_stock_CoC": "OPEN",
        "statistical_capability_or_FAI_measurements": "FOUND" if physical else "NOT_FOUND_IN_CURRENT_REPO",
        "records": physical,
    }

    if a.preflight_only:
        print("PASS_PREFLIGHT_EDR047")
        print("CAPABILITY_RECORDS:",len(physical))
        print("AXIAL_CURRENT_FLOAT_MM:",old_float)
        print("AXIAL_TARGET_FLOAT_MM:",target_float)
        print("DOWNSTREAM_H_NOMINAL_MM:",target_H)
        print("CENTERED_COMBINED_HALF_BUDGET_MM:",centered_half_budget)
        print("NO_FILES_CHANGED_EXCEPT_GUARD_REPORT_REFRESH")
        return 0

    external_sources=[
        {
            "authority":"Ensinger official",
            "url":"https://www.ensingerplastics.com/en/shapes/peek-tecapeek-pvx-black",
            "claim":"TECAPEEK PVX black is a bearing/sliding PEEK grade; official product data supports dimensional-stability/sliding application but does not publish project-specific machining Cp/Cpk or gage uncertainty."
        },
        {
            "authority":"Ensinger official",
            "url":"https://www.ensingerplastics.com/en/thermoplastic-materials/peek-plastic/peek-machining",
            "claim":"PEEK including filled grades is suitable for precision CNC machining; actual tight-tolerance capability depends on optimized machining practice rather than a generic project tolerance value."
        },
        {
            "authority":"Ensinger official",
            "url":"https://www.ensingerplastics.com/en/faq",
            "claim":"For narrow tolerances and filled plastics, intermediate annealing/stress relief may be beneficial; final dimensions are produced after the stabilization step."
        }
    ]

    decision=[
        "Current evidence supports the selected TECAPEEK PVX machining route, but it does not contain quantitative project/supplier process-capability data or measurement-uncertainty evidence sufficient to release numeric P003/P004/P014 production tolerance splits.",
        "Do not invent ± values, ISO fit classes, Cpk/Ppk or gage capability from generic machining practice.",
        "Retain the P003/P004 seat nominal architecture: 6.600/6.540 gives 0.060 mm nominal diametral clearance, already centered in the 0.040...0.080 mm 20 C functional window.",
        "Reopen and recenter only the axial nominal architecture at the requirement level: retain P004 L_nom=8.000 mm and require P003/P014 effective installed retention-space nominal H_nom=8.060 mm, giving F_nom=0.060 mm at 20 C.",
        "This axial recentering doubles the symmetric combined worst-case half-budget from 0.010 mm to 0.020 mm without assigning any part-level production tolerance.",
        "The exact P003/P014 feature that realizes H_nom=8.060 mm remains a downstream Product Definition decision; no P003/P014 CAD, DimXpert or drawing mutation is authorized by this decision.",
        "Supplier/FAI/metrology evidence remains required before numeric part-level tolerance allocation. The evidence package shall include stock/lot traceability, actual machining/stabilization route, dimensional results, measurement temperature, calibrated method and measurement uncertainty/decision rule.",
        "A small first-article set may screen feasibility, but no statistical process-capability claim is released unless the data set and method are sufficient for that claim.",
        "20 C dimensional acceptance remains separate from service-temperature no-binding qualification."
    ]

    wr(repo/EDR47,{
        "schema":"k01.edr.v1","decision_id":"EDR-047","date":"2026-09-18",
        "subject":"P004 manufacturing/metrology capability boundary and axial nominal robustness allocation",
        "status":"ACCEPTED_CAPABILITY_BOUNDARY__AXIAL_NOMINAL_RECENTER_REQUIREMENT__NUMERIC_PRODUCTION_CAPABILITY_EXTERNAL",
        "goal":"Determine whether existing evidence can support EDR-046 part-level tolerance allocation and, if not, remove avoidable axial nominal asymmetry without inventing production capability.",
        "authority":[str(EDR46).replace("\\","/"),str(REP46).replace("\\","/"),str(PD).replace("\\","/"),str(INSP).replace("\\","/"),"EDR-038","EDR-043","EDR-045"],
        "external_manufacturer_evidence":external_sources,
        "capability_inventory":inv,
        "engineering_question":"Can current manufacturing/metrology evidence justify numeric tolerance splits, and should the 0.050 mm axial nominal be retained when only 0.010 mm adverse-side combined budget is available?",
        "options":[
            {"id":"A","description":"Retain 0.050 mm axial nominal and wait for supplier capability evidence.","disposition":"REJECTED_AS_UNNECESSARILY_ASYMMETRIC_FOR_20C_FUNCTION"},
            {"id":"B","description":"Recenter functional axial nominal to 0.060 mm through downstream P003/P014 effective retention-space requirement while retaining P004 L=8.000 mm.","disposition":"ACCEPTED"},
            {"id":"C","description":"Assign typical ±0.01/H7/etc. production values from generic practice.","disposition":"REJECTED_NO_AUTHORITY"},
            {"id":"D","description":"Change the 0.040...0.080 mm functional window.","disposition":"NOT_JUSTIFIED"}
        ],
        "decision":decision,
        "axial_nominal_allocation":{
            "P004_length_nominal_mm":L,
            "previous_effective_retention_space_nominal_mm":old_H,
            "previous_float_nominal_mm":old_float,
            "required_effective_retention_space_nominal_mm":target_H,
            "required_float_nominal_20C_mm":target_float,
            "functional_window_20C_mm":window,
            "centered_combined_half_budget_mm":centered_half_budget,
            "part_level_tolerance_split":"OPEN__WAITING_EXTERNAL_CAPABILITY_EVIDENCE",
            "implementation_owner":"P003/P014 downstream Product Definition; exact feature allocation not selected here"
        },
        "service_screen":screen,
        "technical_filter":{
            "function":"PASS__TARGET_REMAINS_INSIDE_20C_WINDOW",
            "tolerance":"PASS_NOMINAL_RECENTER__NUMERIC_PART_SPLIT_OPEN",
            "manufacturing":"ROUTE_FEASIBLE__NUMERIC_CAPABILITY_UNPROVEN",
            "inspection":"METHOD_ARCHITECTURE_EXISTS__UNCERTAINTY_UNPROVEN",
            "assembly":"PASS__AXIAL_FLOAT_RETENTION_NO_PRELOAD_PRESERVED",
            "thermal":"PASS_SCREEN_WITH_LIMITATIONS__L8_LOW_T_OPEN",
            "serviceability":"PASS__NO_SELECTIVE_ASSEMBLY_BASELINE_INTRODUCED"
        },
        "required_external_evidence":[
            "TECAPEEK PVX stock form/lot/CoC and machining supplier identity/effectivity",
            "declared rough/finish/stress-relief or anneal sequence used for P004",
            "FAI dimensional measurements for P004 OD, OAL and bore at controlled/recorded temperature",
            "measurement equipment traceability, method, contact force where relevant, and uncertainty/decision rule",
            "supplier historical or pilot-run process capability evidence before any Cp/Cpk/Ppk claim",
            "mating-part P003/P014 capability evidence before final shared tolerance split"
        ],
        "expected_closure":"PASS_P004_CAPABILITY_BASIS_CONTROLLED__NOMINAL_REOPEN_TRIGGERED__NUMERIC_SPLIT_EXTERNAL",
        "impact":{"CAD":"NONE","DimXpert":"NONE","drawing":"NONE","P003/P014":"DOWNSTREAM_NOMINAL_REQUIREMENT_ONLY","native_mutation":"NONE"}
    })

    wr(repo/REP47,{
        "schema":"k01.p004.capability_boundary.current.v1","generated_utc":now(),
        "status":"PASS_P004_CAPABILITY_BASIS_CONTROLLED__NOMINAL_REOPEN_TRIGGERED__NUMERIC_SPLIT_EXTERNAL",
        "part_id":"K01-P-004","reference_temperature_C":20,
        "capability_evidence_boundary":evidence_boundary,
        "seat":{"nominal_clearance_mm":0.060,"decision":"RETAIN","production_tolerance_split":"WAITING_EXTERNAL_CAPABILITY_EVIDENCE"},
        "axial":{"previous_nominal_float_mm":old_float,"target_nominal_float_mm":target_float,"required_effective_retention_space_nominal_mm":target_H,"combined_half_budget_mm":centered_half_budget,"production_tolerance_split":"WAITING_EXTERNAL_CAPABILITY_EVIDENCE"},
        "service_screen":screen,
        "external_evidence_required":True,
        "native_mutation":"NONE"
    })

    set_char(pd,"P004-C03",{
        "name":"OAL / axial float chain","nominal":"8.00",
        "status":"NOMINAL_ARCHITECTURE_RECENTERED_REQUIREMENT__PRODUCTION_TOLERANCE_OPEN",
        "functional_window_20C_mm":window,
        "axial_float_nominal_target_20C_mm":target_float,
        "downstream_effective_retention_space_nominal_mm":target_H,
        "joint_budget_mm":{"toward_loss_of_float":centered_half_budget,"toward_excessive_float":centered_half_budget},
        "production_tolerance":"OPEN__WAITING_EXTERNAL_CAPABILITY_EVIDENCE",
        "architecture_state":"RECENTERED_AT_REQUIREMENT_LEVEL__NO_NATIVE_MUTATION",
        "source":"EDR-047"
    })
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__CAPABILITY_EXTERNAL__INSPECTION_PROCEDURE_NEXT"
    pd["product_definition_ready"]=False
    pd["open_release_blockers"]=replace_blockers(pd.get("open_release_blockers"),[
        "production tolerance split","P004/P003/P014 production tolerance split"
    ],[
        "P004/P003/P014 numeric production tolerance split — WAITING_EXTERNAL on supplier/FAI/metrology capability evidence",
        "P004 inspection conditioning/measurement procedure — ACTIVE_NEXT",
    ])
    pd["downstream_allocation_requirements"]=pd.get("downstream_allocation_requirements") or []
    req="P003/P014 effective installed retention-space nominal H_nom = 8.060 mm at 20 C relative to P004 L_nom = 8.000 mm; exact feature allocation and production tolerances remain downstream/open."
    if req not in pd["downstream_allocation_requirements"]: pd["downstream_allocation_requirements"].append(req)
    wr(repo/PD,pd)

    readiness.update({
        "generated_utc":now(),
        "manufacturing_metrology_capability_decision":"PASS_BOUNDARY_CONTROLLED__NUMERIC_CAPABILITY_EXTERNAL",
        "axial_nominal_architecture":"RECENTERED_REQUIREMENT_0P060__P004_LENGTH_UNCHANGED",
        "production_tolerance_split":"WAITING_EXTERNAL__SUPPLIER_FAI_METROLOGY_CAPABILITY",
        "capability_external_evidence": "REQUIRED",
        "next_blocker":"P004-INSPECTION-CONDITIONING-PROCEDURE-DECISION",
        "next":"Define the controlled P004 inspection/conditioning procedure at 20 C: equilibration/temperature recording, low-force measurement setup, traceability, uncertainty/decision-rule fields and FAI record structure. Do not invent final acceptance limits while numeric production tolerances remain external. No CAD/DimXpert/drawing mutation."
    })
    wr(repo/READ,readiness)

    insp.update({
        "generated_utc":now(),
        "capability_state":"ROUTE_FEASIBLE__NUMERIC_CAPABILITY_WAITING_EXTERNAL",
        "axial_nominal_target_20C_mm":target_float,
        "external_capability_evidence_required":True,
        "next_procedure_closure":"P004-INSPECTION-CONDITIONING-PROCEDURE-DECISION"
    })
    wr(repo/INSP,insp)

    blocker="P004-INSPECTION-CONDITIONING-PROCEDURE-DECISION"
    nid="K01-NA-P004-INSPECTION-CONDITIONING-PROCEDURE"
    exp="PASS_P004_INSPECTION_CONDITIONING_PROCEDURE_CONTROLLED__NUMERIC_ACCEPTANCE_WAITING"
    text=("Define the controlled P004 inspection/conditioning procedure at 20 C: part/gage temperature equilibration and recording, "
          "low-force measurement setup for polymer features, equipment traceability, uncertainty/decision-rule fields, FAI record structure, "
          "and supplier stabilization/anneal declaration. Do not invent final numeric acceptance limits while production tolerance split is WAITING_EXTERNAL. "
          "No CAD/DimXpert/drawing mutation.")
    auth=[str(REP47).replace("\\","/"),str(EDR47).replace("\\","/"),str(PD).replace("\\","/"),str(INSP).replace("\\","/"),"control/decisions/EDR-043_P004_TECAPEEK_PVX_PRODUCTION_MATERIAL_EVIDENCE.json"]

    n.update({
        "schema":"k01.next_actions.current.v39_program_front",
        "active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,
        "expected_closure":exp,"execution_mode":"ENGINEERING_INSPECTION_PROCEDURE_DECISION__NO_NATIVE_MUTATION",
        "authority_set":auth,"last_completed":"EDR-047 — P004 capability boundary and axial nominal robustness allocation",
        "latest_engineering_activity":"EDR-047 — P004 manufacturing/metrology capability boundary and axial nominal robustness allocation [ACCEPTED_CAPABILITY_BOUNDARY__AXIAL_NOMINAL_RECENTER_REQUIREMENT__NUMERIC_PRODUCTION_CAPABILITY_EXTERNAL]"
    })
    wr(repo/NEXT,n)

    gate=rd(repo/GATE,{}) or {}
    gate.update({
        "schema":"k01.active_step_gate.v19_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,
        "expected_closure":exp,"mutation_authorized":False,
        "mutation_scope":"ENGINEERING INSPECTION/CONDITIONING PROCEDURE ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING",
        "required_files":auth
    })
    wr(repo/GATE,gate)

    front=rd(repo/FRONT,{}) or {}
    front.update({
        "generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},
        "next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"ENGINEERING_INSPECTION_PROCEDURE_DECISION__NO_NATIVE_MUTATION"}
    })
    timing=front.setdefault("timing",{})
    timing["ACTIVE_NOW"]=[blocker]
    wd=[x for x in (timing.get("WAITING_DEPENDENCY") or []) if "production tolerance split" not in str(x).lower()]
    for x in [
        "P004 guide-clearance numeric limits — system radial/angular/optical repeatability allocation",
        "P004 GPS numeric values — after guide/tolerance allocation",
        "P004 texture numeric values — after process capability evidence"
    ]:
        if x not in wd: wd.append(x)
    timing["WAITING_DEPENDENCY"]=wd
    we=timing.get("WAITING_EXTERNAL") or []
    for x in [
        "P004/P003/P014 numeric production tolerance split — supplier/FAI/metrology capability evidence",
        "P004 production lot/stock CoC and supplier process effectivity",
    ]:
        if x not in we: we.append(x)
    timing["WAITING_EXTERNAL"]=we
    closed=front.setdefault("closed_blocker_ids",[])
    for x in ["P004-JOINT-TOLERANCE-ALLOCATION-DECISION","P004-MANUFACTURING-METROLOGY-CAPABILITY-DECISION"]:
        if x not in closed: closed.append(x)
    wr(repo/FRONT,front)

    cm=rd(repo/CENTER,{}) or {}
    if cm:
        cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,
                   "p004_capability_boundary":{"status":"PASS_EDR_047","report":str(REP47).replace("\\","/")}})
        wr(repo/CENTER,cm)

    subprocess.run([sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)

    print("PASS_P004_CAPABILITY_BASIS_CONTROLLED__NOMINAL_REOPEN_TRIGGERED__NUMERIC_SPLIT_EXTERNAL")
    print("EDR: EDR-047")
    print("P004_LENGTH_NOMINAL_MM: 8.000")
    print("DOWNSTREAM_EFFECTIVE_RETENTION_SPACE_NOMINAL_MM: 8.060")
    print("AXIAL_FLOAT_TARGET_20C_MM: 0.060")
    print("CENTERED_COMBINED_HALF_BUDGET_MM: 0.020")
    print("NUMERIC_PRODUCTION_TOLERANCE_SPLIT: WAITING_EXTERNAL_CAPABILITY_EVIDENCE")
    print("NEXT:",blocker)
    print("NATIVE_MUTATION: NONE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
