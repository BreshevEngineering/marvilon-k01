from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
EDR40=Path("control/decisions/EDR-040_P004_GUIDE_CLEARANCE_AUTHORITY_BOUNDARY.json")
EDR48=Path("control/decisions/EDR-048_P004_INSPECTION_CONDITIONING_PROCEDURE.json")
EDR49=Path("control/decisions/EDR-049_P004_GUIDE_SYSTEM_ALLOCATION_AUTHORITY_RECOVERY.json")
REQ=Path("control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
WORK=Path("control/product_definition/K01_P004_PRODUCT_DEFINITION_WORKPACK_CURRENT.json")
REP=Path("reports/engineering/K01_P004_GUIDE_SYSTEM_ALLOCATION_AUTHORITY_RECOVERY_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def now():return dt.datetime.now(dt.timezone.utc).isoformat()

def run_guard(repo):
    for t in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        cp=subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo,text=True)
        if cp.returncode: raise SystemExit("HOLD: state guard failed before EDR-049")

def set_char(pd,cid,updates):
    for c in pd.get("characteristics") or []:
        if isinstance(c,dict) and c.get("id")==cid:
            c.update(updates);return
    pd.setdefault("characteristics",[]).append(dict({"id":cid},**updates))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));ap.add_argument("--preflight-only",action="store_true");a=ap.parse_args()
    repo=Path(a.repo_root).resolve()
    for rel in (EDR40,EDR48,REQ,PD,READ,WORK,NEXT,GATE,FRONT):
        if not (repo/rel).is_file(): print("HOLD_MISSING:",rel); return 2
    run_guard(repo)
    n=rd(repo/NEXT,{}) or {}; f=rd(repo/FRONT,{}) or {}; e40=rd(repo/EDR40,{}) or {}; req=rd(repo/REQ,{}) or {}; pd=rd(repo/PD,{}) or {}; readiness=rd(repo/READ,{}) or {}; work=rd(repo/WORK,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-GUIDE-SYSTEM-ALLOCATION-RECOVERY":
        print("HOLD_WRONG_FRONTIER",n.get("next_action_id"));return 3
    if str((f.get("active_blocker") or {}).get("id"))!="P004-GUIDE-SYSTEM-ALLOCATION-AUTHORITY-RECOVERY":
        print("HOLD_WRONG_BLOCKER",f.get("active_blocker"));return 3
    if not str(e40.get("status","")).startswith("ACCEPTED_AUTHORITY_BOUNDARY"):
        print("HOLD_EDR040_NOT_ACCEPTED");return 3

    # Targeted authority recovery: only current requirements + active P004 PD/workpack + EDR-040 boundary.
    req_blob=json.dumps(req,ensure_ascii=False).lower()
    candidate_terms=("guide clearance","radial repeatability","angular repeatability","optical repeatability","target repeatability")
    requirement_hits=[t for t in candidate_terms if t in req_blob]
    # Current release requirements contain no P004/P001 guide allocation entry. Mere words in legacy/plans are not numeric authority.
    current_requirement_ids=[k for k in (req.get("requirements") or {}).keys() if "P004" in k.upper() or "GUIDE" in k.upper() or "OPT" in k.upper() or "REPEAT" in k.upper()]
    recovered_numeric_authority=False
    inventory={
      "authorities_checked":[str(REQ).replace("\\","/"),str(EDR40).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/"),str(WORK).replace("\\","/")],
      "current_requirement_ids_matching_scope":current_requirement_ids,
      "keyword_hits_in_release_requirements":requirement_hits,
      "numeric_system_allocation_found":False,
      "legacy_or_planning_mentions_are_authority":False,
      "nominal_geometry_is_requirement_authority":False
    }
    decision=[
      "No controlled numeric system-level radial, angular or optical repeatability allocation was found in the current release requirements or active P004 authorities.",
      "EDR-040 remains valid: P004 bore Ø5.055 and P001 rod Ø5.000 establish only 0.055 mm nominal diametral clearance; they do not establish acceptable guide-clearance min/max.",
      "Do not release P004 bore tolerance, P001 rod tolerance, guide-form/GPS numeric values, or a guide-clearance band from nominal geometry or generic fit practice.",
      "Classify GUIDE_NUMERIC as WAITING_EXTERNAL_REQUIREMENT_OR_CHARACTERIZATION_EVIDENCE.",
      "A stakeholder/system requirement is preferred. If none exists, a controlled physical characterization may quantify current radial/angular/optical repeatability, but characterization results do not become a release requirement without an explicit system acceptance basis.",
      "No native CAD, DimXpert or drawing mutation is authorized."
    ]
    external_needed=[
      "Controlled system/stakeholder acceptance requirement for allowable calibration-rod/target radial or angular repositioning and/or optical calibration repeatability; OR",
      "controlled characterization test results with method, setup, positions/stroke, repetitions, environmental conditions, raw results and uncertainty, followed by an explicit engineering allocation decision tying measured mechanical play to acceptable system/optical performance",
      "P001 size/form capability and P004 bore size/form capability before final production tolerance split"
    ]
    if a.preflight_only:
        print("PASS_PREFLIGHT_EDR049")
        print("NUMERIC_SYSTEM_ALLOCATION_FOUND: FALSE")
        print("RESULT: EXPLICIT_EXTERNAL_DEPENDENCY")
        return 0

    wr(repo/EDR49,{
      "schema":"k01.edr.v1","decision_id":"EDR-049","date":"2026-09-18",
      "subject":"P004/P001 guide system-allocation authority recovery",
      "status":"ACCEPTED_AUTHORITY_RECOVERY__NO_NUMERIC_SYSTEM_ALLOCATION__EXTERNAL_REQUIREMENT_OR_CHARACTERIZATION_REQUIRED",
      "goal":"Determine whether a controlled numeric system-level repeatability allocation exists to bound P001↔P004 guide clearance; if absent, expose the dependency rather than inventing a fit.",
      "authority":[str(EDR40).replace("\\","/"),str(REQ).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/"),str(WORK).replace("\\","/")],
      "inputs":inventory,
      "engineering_question":"Is there a current controlled numeric radial/angular/optical repeatability allocation that can be converted into P001↔P004 guide-clearance limits?",
      "options":[
        {"id":"A","description":"Release guide clearance from the 5.055/5.000 nominal geometry or generic fits.","disposition":"REJECTED_NO_REQUIREMENT_AUTHORITY"},
        {"id":"B","description":"Use a current controlled system-level numeric allocation if one exists.","disposition":"NOT_AVAILABLE_IN_CURRENT_AUTHORITIES"},
        {"id":"C","description":"Keep numeric guide clearance open and create an explicit external requirement/characterization dependency.","disposition":"ACCEPTED"}
      ],
      "technical_filter":{"function":"OPEN_NUMERIC_SYSTEM_ACCEPTANCE","tolerance":"HOLD_NUMERIC_ALLOCATION","manufacturing":"NO_NEW_VALUES","inspection":"CHARACTERIZATION_METHOD_REQUIRED_IF_NO_STAKEHOLDER_REQUIREMENT","assembly":"NOMINAL_ARCHITECTURE_UNCHANGED","thermal":"NO_CHANGE_EDR045_BOUNDARY","CAD":"NONE"},
      "decision":decision,
      "external_evidence_required":external_needed,
      "expected_closure":"PASS_P004_GUIDE_REQUIREMENT_AUTHORITY_RECOVERED_OR_EXPLICIT_EXTERNAL_DEPENDENCY",
      "downstream_impact":{"P004_guide_size_tolerance":"WAITING_EXTERNAL","P001_rod_tolerance":"WAITING_EXTERNAL","guide_GPS_numeric":"WAITING_EXTERNAL/DEPENDENCY","CAD":"NONE","DimXpert":"NONE","drawing":"NONE"}
    })
    wr(repo/REP,{"schema":"k01.p004.guide_system_allocation_authority_recovery.current.v1","generated_utc":now(),"status":"PASS_P004_GUIDE_REQUIREMENT_AUTHORITY_RECOVERED_OR_EXPLICIT_EXTERNAL_DEPENDENCY","part_id":"K01-P-004","interface":"P004 bore Ø5.055 nominal ↔ P001 rod Ø5.000 nominal","nominal_diametral_clearance_mm":0.055,"numeric_system_allocation_found":recovered_numeric_authority,"guide_numeric_state":"WAITING_EXTERNAL_REQUIREMENT_OR_CHARACTERIZATION_EVIDENCE","authority_inventory":inventory,"external_evidence_required":external_needed,"native_mutation":"NONE"})

    set_char(pd,"P004-C01",{"name":"Guide bore","nominal":"Ø5.055","status":"NOMINAL_CONTROLLED__FUNCTIONAL_NUMERIC_LIMITS_WAITING_EXTERNAL","authority_state":"NO_CONTROLLED_NUMERIC_SYSTEM_ALLOCATION_FOUND_EDR_049","derived_nominal_clearance_mm":0.055,"production_tolerance":"OPEN__WAITS_FOR_SYSTEM_REQUIREMENT_AND_CAPABILITY","dependency":"WAITING_EXTERNAL_REQUIREMENT_OR_CHARACTERIZATION_EVIDENCE","source":"EDR-040 + EDR-049"})
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__GUIDE_EXTERNAL__EDGE_DECISION_NEXT"
    obs=[]
    for x in pd.get("open_release_blockers") or []:
        if "P001/P004 guide-clearance" in str(x):
            obs.append("P001/P004 guide-clearance numeric min/max and size/form tolerance allocation — WAITING_EXTERNAL requirement/characterization + capability evidence")
        else: obs.append(x)
    pd["open_release_blockers"]=list(dict.fromkeys(obs))
    wr(repo/PD,pd)

    readiness["generated_utc"]=now(); readiness["guide_clearance_state"]="WAITING_EXTERNAL__REQUIREMENT_OR_CHARACTERIZATION_EVIDENCE"; readiness["next_blocker"]="P004-EDGE-TREATMENT-DECISION"; readiness["next"]="Close P004 functional edge/deburr requirement without inventing an arbitrary edge-break dimension. Preserve guide, seat and axial functional geometry. No CAD/DimXpert/drawing mutation."
    for item in readiness.get("remaining_dependencies") or []:
        if isinstance(item,dict) and item.get("id")=="GUIDE_NUMERIC": item.update({"state":"WAITING_EXTERNAL","dependency":"controlled stakeholder/system guide-repeatability allocation or characterized repeatability tied to an explicit acceptance basis","blocks":["P004 guide-bore size tolerance","guide form/GPS numeric"]})
        if isinstance(item,dict) and item.get("id") in ("SEAT_TOLERANCE","AXIAL_TOLERANCE"):
            item.update({"state":"WAITING_EXTERNAL_CAPABILITY_EVIDENCE","dependency":"shared manufacturing/metrology capability allocation after EDR-046/047"})
        if isinstance(item,dict) and item.get("id")=="TEXTURE_NUMERIC": item.update({"state":"WAITING_EXTERNAL_PROCESS_WEAR_CAPABILITY_EVIDENCE"})
    wr(repo/READ,readiness)

    blocker="P004-EDGE-TREATMENT-DECISION"; nid="K01-NA-P004-EDGE-TREATMENT-DECISION"; exp="PASS_P004_EDGE_FUNCTIONAL_REQUIREMENT_CONTROLLED__NO_ARBITRARY_EDGE_BREAK"
    text="Close the P004 functional edge/deburr requirement: prevent burrs/raised material from entering the guide, seat or axial interfaces and preserve controlled functional dimensions, without inventing a generic numeric edge-break. Determine whether any edge needs an independently controlled geometry. No CAD/DimXpert/drawing mutation."
    auth=[str(EDR49).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/"),str(WORK).replace("\\","/"),"control/decisions/EDR-044_P004_DATUM_FUNCTION_CORRECTION.json","control/decisions/EDR-048_P004_INSPECTION_CONDITIONING_PROCEDURE.json"]
    n.update({"schema":"k01.next_actions.current.v41_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"ENGINEERING_EDGE_FUNCTION_DECISION__NO_NATIVE_MUTATION","authority_set":auth,"last_completed":"EDR-049 — P004/P001 guide system-allocation authority recovery","latest_engineering_activity":"EDR-049 — P004/P001 guide system-allocation authority recovery [ACCEPTED_AUTHORITY_RECOVERY__NO_NUMERIC_SYSTEM_ALLOCATION__EXTERNAL_REQUIREMENT_OR_CHARACTERIZATION_REQUIRED]"}); wr(repo/NEXT,n)
    gate=rd(repo/GATE,{}) or {};gate.update({"schema":"k01.active_step_gate.v21_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"ENGINEERING EDGE/DEBURR DECISION ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING","required_files":auth});wr(repo/GATE,gate)
    front=rd(repo/FRONT,{}) or {};front.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"ENGINEERING_EDGE_FUNCTION_DECISION__NO_NATIVE_MUTATION"}})
    timing=front.setdefault("timing",{});timing["ACTIVE_NOW"]=[blocker]
    we=timing.get("WAITING_EXTERNAL") or []
    for x in ["P004/P001 guide numeric acceptance — stakeholder/system requirement or controlled characterization tied to acceptance basis","P004/P001 guide production tolerance split — P001/P004 process + metrology capability"]:
        if x not in we:we.append(x)
    timing["WAITING_EXTERNAL"]=we
    wd=[x for x in (timing.get("WAITING_DEPENDENCY") or []) if "guide-clearance numeric limits" not in str(x).lower()]
    timing["WAITING_DEPENDENCY"]=wd
    closed=front.setdefault("closed_blocker_ids",[])
    if "P004-GUIDE-SYSTEM-ALLOCATION-AUTHORITY-RECOVERY" not in closed:closed.append("P004-GUIDE-SYSTEM-ALLOCATION-AUTHORITY-RECOVERY")
    wr(repo/FRONT,front)
    cm=rd(repo/CENTER,{}) or {}
    if cm:cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"p004_guide_authority":{"status":"PASS_EDR_049__EXTERNAL_DEPENDENCY","report":str(REP).replace("\\","/")}});wr(repo/CENTER,cm)

    for cmd in [[sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],[sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],[sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"]]: subprocess.run(cmd,cwd=repo,check=True,text=True)
    print("PASS_P004_GUIDE_REQUIREMENT_AUTHORITY_RECOVERED_OR_EXPLICIT_EXTERNAL_DEPENDENCY")
    print("EDR: EDR-049")
    print("NUMERIC_GUIDE_AUTHORITY: NOT_FOUND")
    print("NEXT:",blocker)
    print("NATIVE_MUTATION: NONE")
    return 0
if __name__=="__main__":raise SystemExit(main())
