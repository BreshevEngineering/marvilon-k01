from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
EDR47=Path("control/decisions/EDR-047_P004_AXIAL_RECENTER.json")
EDR48=Path("control/decisions/EDR-048_P004_INSPECTION_CONDITIONING_PROCEDURE.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
INSP=Path("reports/inspection/K01-P-004_INSPECTION_PLAN_CURRENT.json")
PROC=Path("reports/inspection/K01-P-004_INSPECTION_PROCEDURE_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")

def rd(p,default=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return default

def wr(p,o):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def run_guard(repo):
    for t in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        cp=subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo,text=True)
        if cp.returncode: raise SystemExit("HOLD: state guard failed before EDR-048.")

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));ap.add_argument("--preflight-only",action="store_true");a=ap.parse_args()
    repo=Path(a.repo_root).resolve()
    for rel in (EDR47,PD,READ,INSP,NEXT,GATE,FRONT):
        if not (repo/rel).is_file(): print("HOLD_MISSING:",rel); return 2
    run_guard(repo)
    n=rd(repo/NEXT,{}) or {}; f=rd(repo/FRONT,{}) or {}; edr47=rd(repo/EDR47,{}) or {}; pd=rd(repo/PD,{}) or {}; readiness=rd(repo/READ,{}) or {}; insp=rd(repo/INSP,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-INSPECTION-CONDITIONING-PROCEDURE":
        print("HOLD_WRONG_FRONTIER",n.get("next_action_id")); return 3
    if str((f.get("active_blocker") or {}).get("id"))!="P004-INSPECTION-CONDITIONING-PROCEDURE-DECISION":
        print("HOLD_WRONG_BLOCKER",f.get("active_blocker")); return 3
    if not str(edr47.get("status","" )).startswith("ACCEPTED_CAPABILITY_BOUNDARY"):
        print("HOLD_EDR047_NOT_ACCEPTED"); return 3

    if a.preflight_only:
        print("PASS_PREFLIGHT_EDR048"); print("NO_NATIVE_MUTATION"); return 0

    procedure={
      "reference_temperature_C":20,
      "temperature_control":[
        "Dimensional acceptance is referenced to 20 C per the controlled K01 requirement architecture.",
        "Part, contact standards/masters and measurement setup shall be thermally equilibrated in the measurement environment before critical acceptance.",
        "Record actual part temperature and ambient temperature for every critical FAI/acceptance record.",
        "Do not apply an unvalidated thermal correction to rescue an out-of-condition measurement."
      ],
      "material_conditioning":[
        "No generic humidity-conditioning-to-weight acceptance step is released for TECAPEEK PVX from current evidence.",
        "Keep parts clean and protected from uncontrolled environmental exposure before inspection.",
        "Supplier/manufacturing record shall declare stock lot/form and whether stress-relief/intermediate anneal was used.",
        "If an intermediate anneal/stabilization step is used, final critical machining/finishing shall occur after that stabilization step; the actual cycle is supplier/process-specific and remains controlled process evidence rather than a generic project value."
      ],
      "measurement_methods":{
        "P004_OD_6p54":"Calibrated low-force micrometer/comparator or equivalent method that does not measurably deform the polymer; record instrument identity and measurement setup.",
        "P004_OAL_8p00":"Calibrated low-force comparator/height measurement with stable flat contacts/support; record setup and instrument identity.",
        "P004_bore_5p055":"Small-bore method suitable for PEEK (e.g. controlled-contact internal metrology, air/optical/CMM where validated); final method is selected only when the guide tolerance is released.",
        "OD_to_bore":"Functional runout fixture/CMM/optical method reproducing datum A locating-OD axis; numeric acceptance remains open.",
        "faces":"Comparator/CMM orientation check to datum A only if the final axial-chain definition requires it.",
        "functional_checks":"Free sliding/no shaving/no binding and assembled axial-float measurement may be recorded as engineering/FAI evidence; they do not replace dimensional acceptance where dimensions are specified."
      },
      "metrology_record_fields":[
        "part serial or FAI identifier","material stock lot and CoC reference","supplier/process revision/effectivity",
        "machining route and stabilization/anneal declaration","measurement date/time","ambient temperature","part temperature",
        "instrument ID/calibration status","measurement method/setup","contact-force setting where applicable",
        "measured result(s)","measurement uncertainty or validated method uncertainty","decision rule/guard band once numeric tolerance exists",
        "operator/reviewer","nonconformance disposition if applicable"
      ],
      "uncertainty_rule":"A numeric PASS/FAIL decision is not released until the characteristic tolerance and a documented measurement uncertainty/decision rule exist. Gage uncertainty must be demonstrated adequate for the released tolerance; no arbitrary 10:1 ratio is imposed by this EDR.",
      "statistical_boundary":"Repeated FAI measurements may screen feasibility and short-term repeatability. Do not claim Cp/Cpk/Ppk from an inadequately sized or uncontrolled data set.",
      "numeric_acceptance":"OPEN__WAITS_FOR_GUIDE_REQUIREMENT_AND_CAPABILITY_BASED_TOLERANCE_ALLOCATION"
    }

    wr(repo/EDR48,{
      "schema":"k01.edr.v1","decision_id":"EDR-048","date":"2026-09-18",
      "subject":"P004 inspection conditioning and measurement procedure architecture",
      "status":"ACCEPTED_INSPECTION_CONDITIONING_PROCEDURE__NUMERIC_ACCEPTANCE_WAITING",
      "goal":"Control how P004 first-article/production dimensions are conditioned, measured and recorded without inventing unreleased tolerances or metrology capability.",
      "authority":["EDR-038","EDR-043","EDR-045","EDR-047",str(INSP).replace("\\","/")],
      "external_manufacturer_basis":[
        "Ensinger PEEK machining guidance: narrow-tolerance/filled-plastic machining may require stress-relief/intermediate annealing and final machining after stabilization.",
        "Ensinger TECAPEEK PVX data: low moisture absorption and suitability for machined sliding/bearing applications."
      ],
      "decision":[
        "Release the 20 C inspection/conditioning procedure architecture defined in this EDR.",
        "Do not release a generic humidity soak time, annealing cycle, measurement force or gage type without the selected supplier/process/metrology method.",
        "Require traceable temperature, material lot/process effectivity, instrument identity/calibration and measurement uncertainty fields in FAI records.",
        "Keep final numeric acceptance limits OPEN until guide-functional allocation and capability-based production tolerance allocation are controlled.",
        "Functional sliding/axial checks are supplementary engineering/FAI evidence and do not silently replace dimensional acceptance."
      ],
      "procedure":procedure,
      "technical_filter":{"function":"PASS","inspection":"PASS_PROCEDURE_ARCHITECTURE","manufacturing":"PASS_PROCESS_DECLARATION_REQUIRED","metrology":"PASS_FIELDS_DEFINED__NUMERIC_CAPABILITY_OPEN","thermal":"PASS_20C_REFERENCE","CAD":"NONE"},
      "expected_closure":"PASS_P004_INSPECTION_CONDITIONING_PROCEDURE_CONTROLLED__NUMERIC_ACCEPTANCE_WAITING",
      "impact":{"CAD":"NONE","DimXpert":"NONE","drawing":"NONE","native_mutation":"NONE"}
    })
    wr(repo/PROC,{"schema":"k01.p004.inspection_procedure.current.v1","generated_utc":now(),"status":"PASS_P004_INSPECTION_CONDITIONING_PROCEDURE_CONTROLLED__NUMERIC_ACCEPTANCE_WAITING","part_id":"K01-P-004","procedure":procedure,"source":"EDR-048","native_mutation":"NONE"})

    insp.update({"generated_utc":now(),"status":"PROCEDURE_ARCHITECTURE_CONTROLLED__NUMERIC_ACCEPTANCE_OPEN","conditioning":"CONTROLLED_BY_EDR_048__THERMAL_EQUILIBRATION_AND_PROCESS_DECLARATION","procedure_authority":"EDR-048","procedure_report":str(PROC).replace("\\","/"),"numeric_acceptance":"OPEN"})
    wr(repo/INSP,insp)

    readiness.update({"generated_utc":now(),"conditioning_state":"PROCEDURE_CONTROLLED_BY_EDR_048","inspection_state":"PROCEDURE_CONTROLLED__NUMERIC_ACCEPTANCE_OPEN","next_blocker":"P004-GUIDE-SYSTEM-ALLOCATION-AUTHORITY-RECOVERY","next":"Recover the system-level numeric radial/angular/optical repeatability requirement that must bound P001↔P004 guide clearance. If no controlled numeric authority exists, classify GUIDE_NUMERIC as WAITING_EXTERNAL/STAKEHOLDER_REQUIREMENT_OR_TEST instead of inventing a clearance band. No CAD/DimXpert/drawing mutation."})
    # update remaining dependency entry if present
    for item in readiness.get("remaining_dependencies") or []:
        if isinstance(item,dict) and item.get("id")=="CONDITIONING": item.update({"state":"CLOSED_BY_EDR_048","dependency":"inspection procedure controlled; numeric acceptance remains downstream"})
    wr(repo/READ,readiness)

    pd["status"]="PARTIAL_PRODUCT_DEFINITION__GUIDE_REQUIREMENT_AUTHORITY_NEXT"
    pd["product_definition_ready"]=False
    # Remove active inspection blocker if present; leave numeric inspection blocker implicit in tolerance dependencies.
    obs=[]
    for x in pd.get("open_release_blockers") or []:
        if "inspection conditioning/measurement procedure" in str(x).lower(): continue
        obs.append(x)
    pd["open_release_blockers"]=obs
    pd["inspection_procedure"]={"state":"CONTROLLED_BY_EDR_048","report":str(PROC).replace("\\","/"),"numeric_acceptance":"OPEN"}
    wr(repo/PD,pd)

    blocker="P004-GUIDE-SYSTEM-ALLOCATION-AUTHORITY-RECOVERY"
    nid="K01-NA-P004-GUIDE-SYSTEM-ALLOCATION-RECOVERY"
    exp="PASS_P004_GUIDE_REQUIREMENT_AUTHORITY_RECOVERED_OR_EXPLICIT_EXTERNAL_DEPENDENCY"
    text=("Recover the controlled system-level radial/angular/optical repeatability allocation that must bound P001↔P004 guide clearance. "
          "Use requirements/EDR/Product Definition/test evidence only. If no numeric authority exists, do not invent a clearance band; record an explicit external stakeholder/test requirement. "
          "No CAD/DimXpert/drawing mutation.")
    auth=[str(EDR48).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/"),"control/decisions/EDR-040_P004_GUIDE_CLEARANCE_AUTHORITY_BOUNDARY.json","control/requirements/K01_RELEASE_REQUIREMENTS_CURRENT.json"]
    n=rd(repo/NEXT,{}) or {}; n.update({"schema":"k01.next_actions.current.v40_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"ENGINEERING_REQUIREMENT_AUTHORITY_RECOVERY__NO_NATIVE_MUTATION","authority_set":auth,"last_completed":"EDR-048 — P004 inspection conditioning and measurement procedure architecture","latest_engineering_activity":"EDR-048 — P004 inspection conditioning and measurement procedure architecture [ACCEPTED_INSPECTION_CONDITIONING_PROCEDURE__NUMERIC_ACCEPTANCE_WAITING]"}); wr(repo/NEXT,n)
    gate=rd(repo/GATE,{}) or {}; gate.update({"schema":"k01.active_step_gate.v20_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"ENGINEERING REQUIREMENT AUTHORITY RECOVERY ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING","required_files":auth}); wr(repo/GATE,gate)
    front=rd(repo/FRONT,{}) or {}; front.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"ENGINEERING_REQUIREMENT_AUTHORITY_RECOVERY__NO_NATIVE_MUTATION"}})
    timing=front.setdefault("timing",{}); timing["ACTIVE_NOW"]=[blocker]
    wd=timing.get("WAITING_DEPENDENCY") or []
    wd=[x for x in wd if "conditioning" not in str(x).lower()]
    timing["WAITING_DEPENDENCY"]=wd
    closed=front.setdefault("closed_blocker_ids",[])
    if "P004-INSPECTION-CONDITIONING-PROCEDURE-DECISION" not in closed: closed.append("P004-INSPECTION-CONDITIONING-PROCEDURE-DECISION")
    wr(repo/FRONT,front)
    cm=rd(repo/CENTER,{}) or {}
    if cm: cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"p004_inspection_procedure":{"status":"PASS_EDR_048","report":str(PROC).replace("\\","/")}}); wr(repo/CENTER,cm)

    for cmd in [
        [sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],
        [sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],
        [sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"]]:
        subprocess.run(cmd,cwd=repo,check=True,text=True)
    print("PASS_P004_INSPECTION_CONDITIONING_PROCEDURE_CONTROLLED__NUMERIC_ACCEPTANCE_WAITING")
    print("EDR: EDR-048")
    print("NEXT:",blocker)
    print("NATIVE_MUTATION: NONE")
    return 0

if __name__=="__main__": raise SystemExit(main())
