from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
INSP=Path("reports/inspection/K01-P-004_INSPECTION_PLAN_CURRENT.json")
THERM=Path("reports/engineering/K01_P004_THERMAL_TOLERANCE_SCREEN_CURRENT.json")
GUIDE=Path("reports/engineering/K01_P004_GUIDE_CLEARANCE_AUTHORITY_BOUNDARY_CURRENT.json")
SEAT=Path("reports/engineering/K01_P004_SEAT_AXIAL_TOLERANCE_ARCHITECTURE_CURRENT.json")
MAT=Path("reports/engineering/K01_P004_TECAPEEK_PVX_MATERIAL_EVIDENCE_CURRENT.json")
EDR42=Path("control/decisions/EDR-042_P004_DATUM_GPS_SURFACE_INSPECTION_ARCHITECTURE.json")
EDR43=Path("control/decisions/EDR-043_P004_TECAPEEK_PVX_PRODUCTION_MATERIAL_EVIDENCE.json")
EDR44=Path("control/decisions/EDR-044_P004_DATUM_FUNCTION_CORRECTION.json")
EDR45=Path("control/decisions/EDR-045_P004_REFERENCE_TEMPERATURE_AND_SERVICE_CLEARANCE.json")
REP=Path("reports/engineering/K01_P004_DEPENDENCY_CLOSURE_PLAN_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")
BOM=Path("reports/control/K01_BOM_RELEASE_STATUS_CURRENT.json")

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def now():return dt.datetime.now(dt.timezone.utc).isoformat()

def guard(repo):
    for t in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        cp=subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo,text=True)
        if cp.returncode:raise SystemExit("HOLD: state guard failed before P004 dependency closure.")

def setc(pd,cid,u):
    xs=pd.get("characteristics")
    if not isinstance(xs,list):xs=[];pd["characteristics"]=xs
    for c in xs:
        if isinstance(c,dict) and c.get("id")==cid:c.update(u);return
    x={"id":cid};x.update(u);xs.append(x)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root);guard(repo)
    for rel in (PD,READ,INSP,THERM,GUIDE,SEAT,MAT,EDR42,EDR43,NEXT,GATE,FRONT):
        if not (repo/rel).is_file():raise SystemExit("HOLD: missing "+str(rel))
    n=rd(repo/NEXT,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-OPEN-DEPENDENCY-CLOSURE":raise SystemExit("HOLD: frontier not at P004 remaining-dependency closure.")

    pd=rd(repo/PD,{}) or {};ready=rd(repo/READ,{}) or {};insp=rd(repo/INSP,{}) or {};therm=rd(repo/THERM,{}) or {}
    res=therm.get("results") or {};srow=res.get("seat_clearance_nominal_mm") or {};arow=res.get("axial_float_nominal_mm") or {}
    if any(srow.get(k) is None for k in ("Tref","Tmax")) or any(arow.get(k) is None for k in ("Tref","Tmax")):raise SystemExit("HOLD: thermal screen incomplete.")

    # EDR-044: assembly-function correction to EDR-042 datum hierarchy.
    wr(repo/EDR44,{"schema":"k01.edr.v1","decision_id":"EDR-044","date":"2026-09-17",
      "subject":"P004 datum architecture correction from assembly constraint hierarchy",
      "status":"ACCEPTED_CORRECTION__DATUM_ARCHITECTURE",
      "stale_trigger":"EDR-042 used an axial face as primary datum, while accepted assembly architecture radially locates P004 by Ø6.54 OD and intentionally retains axial float with P014 and no preload.",
      "supersedes":{"decision":"EDR-042","scope":"datum hierarchy and datum-dependent GPS references only"},
      "decision":[
        "Datum A = P004 external locating cylinder Ø6.54; its derived axis is the primary functional datum axis because P003 seat provides radial location.",
        "No secondary axial datum is released: P004 axial position intentionally floats and neither end face is a deterministic assembly locator.",
        "Datum C = N/A because P004 is rotationally symmetric.",
        "Guide-bore relation uses total runout or equivalent ISO GPS relation to datum A; numeric value remains OPEN.",
        "End-face orientation uses perpendicularity/equivalent orientation to datum A only if required by axial-stack function; numeric value remains OPEN.",
        "Inspection datum simulation shall reproduce the locating OD with controlled low-force support suitable for a polymer part; fixture uncertainty remains OPEN."],
      "basis":["P004 OD Ø6.54 is the P003 locating/slip-fit interface.","P004 is retained by P014 without adhesive or axial preload.","P004 axial float is intentional."],
      "impact":{"CAD":"NONE","DimXpert":"NONE","drawing":"NONE","BOM":"NONE","EDR-042":"datum scope superseded; surface/edge/inspection method architecture retained"}})

    # EDR-045: ISO 1 reference-temperature semantics versus service function.
    seat_shift=float(srow["Tmax"])-float(srow["Tref"]);axial_shift=float(arow["Tmax"])-float(arow["Tref"]);band_lo=0.04;band_hi=0.08
    seat_hot=band_lo+seat_shift;axial_hot=band_lo+axial_shift
    wr(repo/EDR45,{"schema":"k01.edr.v1","decision_id":"EDR-045","date":"2026-09-17",
      "subject":"P004 reference-temperature dimensional acceptance versus service-temperature anti-binding function",
      "status":"ACCEPTED_REQUIREMENT_APPLICABILITY__SERVICE_QUALIFICATION_PARTIAL",
      "decision":[
        "Treat controlled 0.04...0.08 mm dimensional clearance/float bands as dimensional acceptance at the ISO 1:2022 standard reference temperature 20 C unless an explicit higher-level K01 requirement states the identical numerical band must hold at every service temperature.",
        "Keep service-temperature acceptance separate: no interference/binding and preserved required motion over the qualified K01 temperature envelope.",
        "EDR-041 narrowed 20 C windows from an all-temperature-band assumption remain a conservative sensitivity case, not the governing production acceptance basis.",
        "No axial nominal shift toward 0.0586...0.060 mm is justified solely by that former all-temperature-band assumption.",
        "At +55 C, manufacturer-supported 23...100 C TECAPEEK PVX CLTE gives positive screened gaps even from the 20 C minimum 0.040 mm; this is engineering screening, not qualification.",
        "The -40...23 C portion remains qualification OPEN because captured TECAPEEK PVX CLTE evidence does not directly cover that range."],
      "standard_basis":{"reference":"ISO 1:2022","reference_temperature_C":20,"source":"https://www.iso.org/standard/80702.html"},
      "screening":{"20C_band_mm":[band_lo,band_hi],"seat_20_to_55_shift_mm":seat_shift,"seat_55C_gap_from_20C_min_mm":seat_hot,"axial_20_to_55_shift_mm":axial_shift,"axial_55C_gap_from_20C_min_mm":axial_hot},
      "release_boundary":{"20C_dimensional_acceptance":"CONTROLLED","55C_no_binding":"ENGINEERING_SCREEN_PASS_WITH_LIMITATIONS","minus40C_no_binding":"QUALIFICATION_OPEN","production_tolerance_allocation":"OPEN"},
      "impact":{"CAD":"NONE","DimXpert":"NONE","drawing":"NONE","EDR-041":"all-temperature-band case retained as sensitivity only","physical_qualification":"OPEN_L8"}})

    deps=[
      {"id":"GUIDE_NUMERIC","state":"WAITING_DEPENDENCY","dependency":"system radial/angular/optical repeatability allocation","blocks":["P004 guide-bore size tolerance","guide form/GPS numeric"]},
      {"id":"SEAT_TOLERANCE","state":"EXECUTABLE_AFTER_MATING_AUTHORITY_RECOVERY","dependency":"P003 Ø6.60 seat production authority","blocks":["P003/P004 worst-case split"]},
      {"id":"AXIAL_TOLERANCE","state":"EXECUTABLE_AFTER_MATING_AUTHORITY_RECOVERY","dependency":"P003/P014 axial-stack production authorities","blocks":["P004 OAL tolerance","axial stack worst-case"]},
      {"id":"LOW_T_PROPERTY","state":"L8_QUALIFICATION_DEPENDENCY","dependency":"low-temperature correlation or physical no-binding test","does_not_block":["20 C dimensional acceptance"]},
      {"id":"DATUM_HIERARCHY","state":"CLOSED_BY_EDR_044"},
      {"id":"GPS_NUMERIC","state":"WAITING_TOLERANCE_ALLOCATION"},
      {"id":"TEXTURE_NUMERIC","state":"WAITING_PROCESS_CAPABILITY_DECISION"},
      {"id":"CONDITIONING","state":"WAITING_INSPECTION_PROCEDURE"}]
    wr(repo/REP,{"schema":"k01.p004.dependency_closure_plan.current.v1","generated_utc":now(),"status":"PASS_REMAINING_DEPENDENCIES_CLASSIFIED__MATING_AUTHORITY_RECOVERY_NEXT","part_id":"K01-P-004","corrections":{"datum":"EDR-044","temperature_applicability":"EDR-045"},"dependencies":deps,"closed_now":["datum hierarchy contradiction","20 C versus service-temperature acceptance ambiguity"],"active_next":"P004-MATING-AUTHORITY-RECOVERY","native_mutation":"NONE"})

    pd["datum_system"]={"A":"Ø6.54 external locating cylinder / derived axis — RELEASED ARCHITECTURE","B":"N/A — axial direction intentionally floats","C":"N/A — rotational symmetry"}
    setc(pd,"P004-C04",{"name":"Guide-bore to locating-OD relationship","status":"OPEN","architecture":"TOTAL RUNOUT or equivalent ISO GPS relative to datum A axis","numeric_tolerance":"OPEN","source":"EDR-044"})
    setc(pd,"P004-C05",{"name":"End-face orientation","status":"OPEN","architecture":"PERPENDICULARITY/equivalent to datum A if axial-stack function requires","numeric_tolerance":"OPEN","source":"EDR-044"})
    pd["reference_temperature"]={"value_C":20,"standard":"ISO 1:2022","source":"EDR-045"}
    pd["service_temperature_function"]={"criterion":"no interference/binding over qualified service envelope","hot_side_55C":"ENGINEERING_SCREEN_PASS_WITH_LIMITATIONS","cold_side_minus40C":"QUALIFICATION_OPEN"}
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__MATING_TOLERANCE_AUTHORITIES_NEXT";pd["product_definition_ready"]=False;wr(repo/PD,pd)

    insp["generated_utc"]=now();insp["datum_simulation"]={"A":"Ø6.54 locating OD with controlled low-force simulator suitable for PEEK","B":"N/A","C":"N/A"};insp["reference_temperature_C"]=20;insp["reference_temperature_standard"]="ISO 1:2022";insp["material_cold_qualification"]="OPEN_L8";wr(repo/INSP,insp)

    ready.update({"generated_utc":now(),"status":"PARTIAL__DEPENDENCIES_CLASSIFIED__MATING_AUTHORITIES_NEXT","product_definition_ready":False,"datum_state":"ARCHITECTURE_RELEASED__OD_AXIS_PRIMARY","temperature_applicability_state":"20C_DIMENSIONAL_ACCEPTANCE_CONTROLLED__SERVICE_NO_BINDING_SEPARATE","low_temperature_state":"L8_QUALIFICATION_OPEN","open_blocker_count":6,"remaining_dependencies":deps,"next_blocker":"P004-MATING-AUTHORITY-RECOVERY","next":"Recover current P003 Ø6.60 seat and P014/P003 axial-stack production authorities, then decide joint worst-case tolerance allocation. Read-only; no CAD/DimXpert/drawing mutation."});wr(repo/READ,ready)

    if (repo/BOM).is_file():
        b=rd(repo/BOM,{}) or {};b["generated_utc"]=now();b["P004_dependency_projection"]={"material":"Ensinger TECAPEEK PVX black — design identity controlled","datum":"Ø6.54 locating-OD axis by EDR-044","release":"HOLD until numeric tolerances/inspection/conditioning close","source":["EDR-043","EDR-044","EDR-045"]};wr(repo/BOM,b)

    f=rd(repo/FRONT,{}) or {};g=rd(repo/GATE,{}) or {};n=rd(repo/NEXT,{}) or {};blocker="P004-MATING-AUTHORITY-RECOVERY";nid="K01-NA-P004-MATING-AUTHORITY-RECOVERY";exp="PASS_P004_MATING_AUTHORITIES_INVENTORIED__JOINT_TOLERANCE_DECISION_READY";text="Recover current P003 Ø6.60 seat and P014/P003 axial-stack production authorities from controlled repo state; classify RELEASED/OPEN without inventing values. Then prepare joint P003/P004/P014 worst-case tolerance decision. No native CAD/DimXpert/drawing mutation.";auth=[str(REP).replace("\\","/"),str(EDR44).replace("\\","/"),str(EDR45).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/")]
    n.update({"schema":"k01.next_actions.current.v36_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"READ_ONLY_MATING_AUTHORITY_RECOVERY","authority_set":auth});wr(repo/NEXT,n)
    g.update({"schema":"k01.active_step_gate.v16_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"READ_ONLY AUTHORITY RECOVERY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING; NO ENGINEERING VALUE MUTATION","required_files":auth});wr(repo/GATE,g)
    f.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"READ_ONLY_MATING_AUTHORITY_RECOVERY"}});f.setdefault("timing",{})["ACTIVE_NOW"]=[blocker];wr(repo/FRONT,f)
    cm=rd(repo/CENTER,{}) or {}
    if cm:cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"p004_dependency_closure":{"datum":"CLOSED_BY_EDR_044","dimensional_reference_temperature":"20 C / ISO 1:2022","service_temperature":"NO_BINDING; cold qualification OPEN","guide_numeric":"WAITING_DEPENDENCY","seat_axial":"MATING_AUTHORITY_RECOVERY_NEXT"}});wr(repo/CENTER,cm)

    subprocess.run([sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
    subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
    print("PASS: P004 dependency closure plan controlled.");print("EDR-044: datum A corrected to Ø6.54 locating-OD axis.");print("EDR-045: dimensional bands at 20 C; service no-binding separate.");print("NEXT: P004 mating-authority recovery.")
    return 0

if __name__=="__main__":raise SystemExit(main())
