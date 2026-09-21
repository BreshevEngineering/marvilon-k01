from __future__ import annotations
import argparse,csv,datetime as dt,json,subprocess,sys
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
EDR49=Path("control/decisions/EDR-049_P004_GUIDE_SYSTEM_ALLOCATION_AUTHORITY_RECOVERY.json")
EDR51=Path("control/decisions/EDR-051_P004_RESIDUAL_GPS_SURFACE_AUTHORITY_BOUNDARY.json")
EDR52=Path("control/decisions/EDR-052_P004_PHYSICAL_EVIDENCE_ACQUISITION_PLAN.json")
REQLEG=Path("control/requirements/requirements.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
PROC=Path("reports/inspection/K01-P-004_INSPECTION_PROCEDURE_CURRENT.json")
CAP=Path("reports/engineering/K01_P004_CAPABILITY_BOUNDARY_CURRENT.json")
GUIDE=Path("reports/engineering/K01_P004_GUIDE_SYSTEM_ALLOCATION_AUTHORITY_RECOVERY_CURRENT.json")
PLAN=Path("reports/test/K01_P004_PHYSICAL_EVIDENCE_PLAN_CURRENT.json")
CSVREL=Path("evidence/templates/K01_P004_GUIDE_REPEATABILITY_CHARACTERIZATION_TEMPLATE.csv")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")
PARTNER=Path("control/project/K01_PARTNER_REVIEW_TARGET_CURRENT.json")

def rd(p,d=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return d

def wr(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def guard(repo):
    for t in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        if subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo).returncode:raise SystemExit("HOLD: coherence guard failed before EDR-052")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));ap.add_argument("--preflight-only",action="store_true");a=ap.parse_args();repo=Path(a.repo_root).resolve()
    for rel in (EDR49,EDR51,PD,READ,PROC,CAP,GUIDE,NEXT,GATE,FRONT):
        if not (repo/rel).is_file():print("HOLD_MISSING",rel);return 2
    guard(repo)
    n=rd(repo/NEXT,{}) or {};front=rd(repo/FRONT,{}) or {};pd=rd(repo/PD,{}) or {};read=rd(repo/READ,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-PHYSICAL-EVIDENCE-PLAN":print("HOLD_WRONG_FRONTIER",n.get("next_action_id"));return 3
    if str((front.get("active_blocker") or {}).get("id"))!="P004-PHYSICAL-EVIDENCE-PLAN-DECISION":print("HOLD_WRONG_BLOCKER",front.get("active_blocker"));return 3
    stroke=10.0
    rleg=rd(repo/REQLEG,{}) or {}
    for item in rleg.get("requirements") or []:
        if isinstance(item,dict) and item.get("id")=="REQ-STROKE-001":
            try: stroke=float(item.get("value_mm",stroke))
            except Exception: pass
    campaigns=[
      {"id":"T-P004-01","name":"20 C dimensional FAI / as-built characterization","purpose":"Measure the actual P004/P001/P003/P014 geometry needed for capability allocation without assuming released mating-part production tolerances.","conditions":["20 C dimensional reference; record actual part and ambient temperature","use EDR-048 traceable measurement record fields","record material stock/lot/CoC and supplier/process/stabilization declaration where available"],"measurements":["P004 OD Ø6.54 actual size at multiple axial/angular locations sufficient to expose taper/ovality","P004 bore Ø5.055 actual size at multiple axial/angular locations sufficient to expose taper/ovality","P004 OAL 7.99 at multiple circumferential locations sufficient to expose face variation","P001 actual guide diameter/form at the P004 contact region","P003 actual P004-seat diameter","P003/P014 actual effective installed retention space H"],"acceptance":"CHARACTERIZATION/FAI INPUT. Apply released dimensional PASS/FAIL only where a production characteristic and uncertainty/decision rule already exist; otherwise report measured values without promotion.","output":"raw measurements + uncertainty/method + dimensional summary"},
      {"id":"T-P004-02","name":"P001↔P004 guide repeatability characterization","purpose":"Quantify current mechanical and, where available, optical/reference repeatability so the missing system guide-performance requirement can be allocated explicitly.","setup":["assemble P004 with P001 and P014 in the intended service architecture; no artificial P004 preload","use the controlled full stroke of %.3f mm"%stroke,"measure at OUT / MID / IN positions corresponding to 0 / %.3f / %.3f mm"%(stroke/2.0,stroke),"define and record a stable mechanical target/reference plane; if optical target/readout is available, record optical/reference result in the same cycle"],"screening_sequence":["working characterization target: 10 complete OUT→MID→IN→MID→OUT cycles; this count is for screening only and is not a statistical capability or qualification sample size","approach each position from both travel directions to expose hysteresis/backlash","do not intentionally side-load the rod; record any handling intervention","record ambient/part temperature and assembly state"],"measurements":["lateral/radial target displacement or equivalent guide-position error at each position","angular deviation if the measurement setup resolves it","optical/reference output/error at each position if available","direction of approach and cycle number","observed binding, stick-slip, shaving/scoring or abnormal contact"],"analysis":["report raw values, range/peak-to-peak and descriptive repeatability statistics","correlate result to measured P001/P004 as-built clearance","separate mechanical repeatability from optical readout repeatability"],"acceptance":"NO RELEASE PASS/FAIL THRESHOLD EXISTS YET. Result is CHARACTERIZATION ONLY until tied to a controlled stakeholder/system acceptance requirement.","output":"completed characterization CSV + setup evidence + summary"},
      {"id":"T-P004-03","name":"Seat clearance and assembled axial-float prototype screen at 20 C","purpose":"Check the currently controlled functional windows on the actual prototype while preserving the distinction between prototype screen and released production acceptance.","measurements":["actual P003 seat ID and P004 locating OD → diametral seat clearance","actual P003/P014 effective retention space H and P004 OAL → axial float","direct assembled axial float where measurable"],"screening_criteria":{"seat_diametral_clearance_mm":[0.040,0.080],"axial_float_mm":[0.040,0.080]},"acceptance":"ENGINEERING PROTOTYPE SCREEN at 20 C only. Do not promote to production release until mating-part Product Definition, process capability and metrology authority close.","output":"measured chain + calculated/direct float + screen result and limitations"},
      {"id":"T-P004-04","name":"Guide-surface functional condition","purpose":"Generate evidence for the remaining guide-bore surface/wear decision without inventing Ra/Rz.","checks":["visual/optical condition before test","complete guide cycles without intentional side load","visual/optical condition after test","record any polymer debris, shaving, scoring, stick-slip or binding","retain photos/micrographs if available with scale/reference"],"acceptance":"QUALITATIVE CHARACTERIZATION. Absence of observed damage supports the current process candidate but does not by itself qualify service life or release a numeric roughness value.","output":"before/after inspection evidence + observations"},
      {"id":"T-P004-L8-01","name":"Service-temperature no-binding qualification","purpose":"Verify no binding over qualified temperature envelope.","state":"L8_LATER__NOT_REQUIRED_FOR_20C_P004_DIMENSIONAL_ACCEPTANCE","note":"Do not use extrapolated low-temperature TECAPEEK data as physical qualification evidence."}
    ]
    if a.preflight_only:
        print("PASS_PREFLIGHT_EDR052");print("CAMPAIGNS:",len(campaigns));print("NEXT: EXTERNAL_EVIDENCE_ACQUISITION");return 0
    wr(repo/EDR52,{"schema":"k01.edr.v1","decision_id":"EDR-052","date":"2026-09-18","subject":"P004 physical evidence acquisition plan for remaining L5 external dependencies","status":"ACCEPTED_PHYSICAL_EVIDENCE_PLAN__EXTERNAL_ACQUISITION_READY","goal":"Define the minimum controlled measurements/tests needed to convert P004 external dependencies into usable engineering evidence before partner technical review, while separating characterization, prototype screens and release/qualification acceptance.","authority":[str(EDR49).replace("\\","/"),str(EDR51).replace("\\","/"),str(PROC).replace("\\","/"),str(CAP).replace("\\","/"),str(GUIDE).replace("\\","/"),str(PD).replace("\\","/"),str(REQLEG).replace("\\","/") if (repo/REQLEG).is_file() else "10 mm stroke authority in controlled K01 requirements/baseline"],"engineering_question":"What is the minimum physical evidence package needed now to close P004 external guide-performance/capability dependencies and provide defensible test/measurement results for technical review?","technical_filter":{"function":"PASS","testability":"PASS_PLAN_DEFINED","measurement":"PASS_METHOD/TRACEABILITY_FIELDS_DEFINED_EDR048","manufacturing":"PASS_FAI_DATA_REQUESTED","statistics":"SCREENING_ONLY_UNTIL_DATA_SUFFICIENT","qualification":"L8_SEPARATED","IP":"NO_DETAILED_DRAWING_OUTPUT_REQUIRED","CAD":"NONE"},"decision":["Execute T-P004-01 through T-P004-04 as the current evidence-acquisition package; T-P004-L8-01 remains later qualification.","Do not convert characterization statistics into a release requirement without a controlled system/stakeholder acceptance basis.","Do not claim Cp/Cpk/Ppk from the screening data unless the data set and process control are independently sufficient.","Use the released 0.040...0.080 mm seat and axial windows only as 20 C prototype screens where the measured chain is applicable; mating-part production release remains open.","Preserve raw data, setup/equipment traceability, temperatures, material/process identity and limitations so partner-facing summaries can trace back to evidence.","No CAD, DimXpert or drawing mutation is authorized."],"campaigns":campaigns,"expected_closure":"PASS_P004_PHYSICAL_EVIDENCE_PLAN_CONTROLLED__EXTERNAL_ACQUISITION_READY","downstream_impact":{"P004":"WAITING_EXTERNAL_MEASUREMENT_DATA_AFTER_PLAN","partner_review":"TEST_MEASUREMENT_EVIDENCE_PATH_DEFINED","L8":"LOW_T_SERVICE_QUALIFICATION_REMAINS_LATER","CAD":"NONE","DimXpert":"NONE","drawing":"NONE"}})
    wr(repo/PARTNER,{
      "schema":"k01.partner_review_target.current.v1",
      "generated_utc":now(),
      "source":"stakeholder/partner update communicated 2026-09-18",
      "review_window":{"earliest":"2026-10-02","latest":"2026-10-16","basis":"repeat meeting requested in 2-4 weeks from 2026-09-18"},
      "purpose":"Prepare defensible partner review evidence showing what is physically working, what is verified, what remains open, and the commercial cost/price structure without exposing unnecessary production-detail IP.",
      "tracks":[
        {"id":"PRT-01","name":"Physical device","status":"ACTIVE_THROUGH_ENGINEERING_LIFECYCLE","required":"bring the physical instrument/device to a reviewable working state and close known technical deficiencies","authority_rule":"engineering status only; do not overstate screen/candidate as qualification"},
        {"id":"PRT-02","name":"Tests and measurements","status":"ACTIVE_P004_EDR_052_FIRST_PACKAGE","required":"traceable test and measurement results with method, inputs, result, criterion/status and limitations","current_link":"reports/test/K01_P004_PHYSICAL_EVIDENCE_PLAN_CURRENT.json"},
        {"id":"PRT-03","name":"3D and general schemes","status":"WAITING_DEPENDENCY__PARTNER_PACKAGE","required":"3D models and main general system/functional schemes without detailed manufacturing dimensions or unnecessary proprietary detail","boundary":"presentation/review artifact only; not engineering authority"},
        {"id":"PRT-04","name":"Financial model","status":"LATER_COMMERCIAL_PACKAGE__NOT_CURRENT_ENGINEERING_WIP","required":"our cost/COGS, partner price, distributor price/margin structure and target end-customer price","dependency":"controlled BOM/cost basis and commercial margin assumptions"}
      ],
      "wip_rule":"Does not create parallel engineering WIP. Current engineering WIP remains the Completion Frontier.",
      "engineering_authority_rule":"This review-target file does not own engineering values; EDR/requirements/Product Definition/CAD/analysis/evidence remain authoritative."
    })
    wr(repo/PLAN,{"schema":"k01.p004.physical_evidence_plan.current.v1","generated_utc":now(),"status":"PASS_P004_PHYSICAL_EVIDENCE_PLAN_CONTROLLED__EXTERNAL_ACQUISITION_READY","part_id":"K01-P-004","reference_temperature_C":20,"stroke_mm":stroke,"campaigns":campaigns,"required_return_package":["completed T-P004-01 dimensional data","completed T-P004-02 characterization CSV","T-P004-02 setup/equipment description and images if available","T-P004-03 axial/seat screen data","T-P004-04 before/after guide-surface observations","material lot/CoC and manufacturing/stabilization declarations available for tested parts"],"native_mutation":"NONE","source":"EDR-052"})
    csvp=repo/CSVREL;csvp.parent.mkdir(parents=True,exist_ok=True)
    with csvp.open("w",newline="",encoding="utf-8-sig") as fh:
        w=csv.writer(fh);w.writerow(["test_id","assembly_id","cycle","position","stroke_mm","approach_direction","ambient_C","part_C","P001_diameter_mm","P004_bore_mm","derived_clearance_mm","radial_or_target_error_mm","angular_error","optical_or_reference_value","optical_or_reference_error","binding_or_stick_slip","shaving_scoring_debris","instrument_ids","uncertainty_notes","operator_notes"])
        for cyc in range(1,11):
            for pos,x,approach in (("OUT",0.0,"OUT_to_IN"),("MID",stroke/2.0,"OUT_to_IN"),("IN",stroke,"OUT_to_IN"),("MID",stroke/2.0,"IN_to_OUT"),("OUT",0.0,"IN_to_OUT")):
                w.writerow(["T-P004-02","",cyc,pos,f"{x:.3f}",approach,"","","","","","","","","","","","","",""])
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__WAITING_EXTERNAL_PHYSICAL_EVIDENCE";pd["physical_evidence_plan"]={"state":"CONTROLLED_BY_EDR_052","report":str(PLAN).replace("\\","/"),"data_state":"WAITING_EXTERNAL"};wr(repo/PD,pd)
    read["generated_utc"]=now();read["physical_evidence_plan_state"]="CONTROLLED_BY_EDR_052__WAITING_EXTERNAL_DATA";read["next_blocker"]="P004-EXTERNAL-EVIDENCE-ACQUISITION";read["next"]="Acquire and return the EDR-052 P004 physical evidence package (T-P004-01...04). Do not assign guide acceptance or production tolerance values before the measurement/stakeholder evidence is available.";wr(repo/READ,read)
    blocker="P004-EXTERNAL-EVIDENCE-ACQUISITION";nid="K01-NA-P004-ACQUIRE-PHYSICAL-EVIDENCE";exp="P004_EXTERNAL_EVIDENCE_RECEIVED__READY_FOR_GUIDE_AND_CAPABILITY_ALLOCATION"
    text="Acquire the EDR-052 P004 physical evidence package: dimensional FAI/as-built data, P001↔P004 OUT/MID/IN repeatability characterization over the 10 mm stroke, 20 C seat/axial-float prototype screen, guide-surface before/after evidence, and available material/process traceability. Return raw data and setup/equipment details. Do not invent guide pass/fail or production tolerances before evidence is reviewed."
    auth=[str(EDR52).replace("\\","/"),str(PLAN).replace("\\","/"),str(CSVREL).replace("\\","/"),str(PROC).replace("\\","/")]
    n.update({"schema":"k01.next_actions.current.v44_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"PHYSICAL_EVIDENCE_ACQUISITION__NO_NATIVE_DEFINITION_MUTATION","authority_set":auth,"last_completed":"EDR-052 — P004 physical evidence acquisition plan","latest_engineering_activity":"EDR-052 — P004 physical evidence acquisition plan [ACCEPTED_PHYSICAL_EVIDENCE_PLAN__EXTERNAL_ACQUISITION_READY]"});wr(repo/NEXT,n)
    gate=rd(repo/GATE,{}) or {};gate.update({"schema":"k01.active_step_gate.v24_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"PHYSICAL MEASUREMENT/TEST EVIDENCE ACQUISITION ONLY; NO NATIVE PRODUCT-DEFINITION MUTATION","required_files":auth});wr(repo/GATE,gate)
    front.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"PHYSICAL_EVIDENCE_ACQUISITION__NO_NATIVE_DEFINITION_MUTATION"}});timing=front.setdefault("timing",{});timing["ACTIVE_NOW"]=[blocker]
    we=timing.get("WAITING_EXTERNAL") or []
    for x in ["P004 EDR-052 physical evidence data package","controlled stakeholder/system guide-repeatability acceptance if available","P004/P001/P003/P014 manufacturing/metrology capability and material/process traceability"]:
        if x not in we:we.append(x)
    timing["WAITING_EXTERNAL"]=we
    closed=front.setdefault("closed_blocker_ids",[]);closed.append("P004-PHYSICAL-EVIDENCE-PLAN-DECISION") if "P004-PHYSICAL-EVIDENCE-PLAN-DECISION" not in closed else None;wr(repo/FRONT,front)
    cm=rd(repo/CENTER,{}) or {}
    if cm:cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"p004_physical_evidence_plan":{"status":"PASS_EDR_052__WAITING_DATA","report":str(PLAN).replace("\\","/")}});wr(repo/CENTER,cm)
    for cmd in [[sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],[sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],[sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"]]:subprocess.run(cmd,cwd=repo,check=True)
    print("PASS_P004_PHYSICAL_EVIDENCE_PLAN_CONTROLLED__EXTERNAL_ACQUISITION_READY");print("EDR: EDR-052");print("PLAN:",PLAN);print("CSV_TEMPLATE:",CSVREL);print("NEXT:",blocker);print("NATIVE_MUTATION: NONE");return 0
if __name__=="__main__":raise SystemExit(main())
