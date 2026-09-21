from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
EDR44=Path("control/decisions/EDR-044_P004_DATUM_FUNCTION_CORRECTION.json")
EDR46=Path("control/decisions/EDR-046_P004_JOINT_TOLERANCE_BUDGET_20C.json")
EDR47=Path("control/decisions/EDR-047_P004_AXIAL_RECENTER.json")
EDR48=Path("control/decisions/EDR-048_P004_INSPECTION_CONDITIONING_PROCEDURE.json")
EDR50=Path("control/decisions/EDR-050_P004_FUNCTIONAL_EDGE_TREATMENT.json")
EDR51=Path("control/decisions/EDR-051_P004_RESIDUAL_GPS_SURFACE_AUTHORITY_BOUNDARY.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
REP=Path("reports/engineering/K01_P004_RESIDUAL_GPS_SURFACE_BOUNDARY_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")

def rd(p,d=None):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return d

def wr(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def guard(repo):
    for t in ("k01_temporal_coherence_guard_v1.py","k01_semantic_coherence_guard_v1.py"):
        if subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo).returncode:raise SystemExit("HOLD: coherence guard failed before EDR-051")
def set_char(pd,cid,updates):
    for c in pd.get("characteristics") or []:
        if isinstance(c,dict) and c.get("id")==cid:c.update(updates);return
    pd.setdefault("characteristics",[]).append(dict({"id":cid},**updates))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));ap.add_argument("--preflight-only",action="store_true");a=ap.parse_args();repo=Path(a.repo_root).resolve()
    for rel in (EDR44,EDR46,EDR47,EDR48,EDR50,PD,READ,NEXT,GATE,FRONT):
        if not (repo/rel).is_file():print("HOLD_MISSING",rel);return 2
    guard(repo)
    n=rd(repo/NEXT,{}) or {};front=rd(repo/FRONT,{}) or {};pd=rd(repo/PD,{}) or {};read=rd(repo/READ,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-RESIDUAL-GPS-SURFACE-BOUNDARY":print("HOLD_WRONG_FRONTIER",n.get("next_action_id"));return 3
    if str((front.get("active_blocker") or {}).get("id"))!="P004-RESIDUAL-GPS-SURFACE-AUTHORITY-BOUNDARY":print("HOLD_WRONG_BLOCKER",front.get("active_blocker"));return 3

    controls={
      "bore_to_OD":{"functional_need":"REQUIRED__OD_AXIS_LOCATES_BUSHING_WHILE_BORE_GUIDES_P001","control_family":"TOTAL_RUNOUT_OR_EQUIVALENT_ISO_GPS_TO_DATUM_A_AXIS","numeric_state":"WAITING_EXTERNAL_GUIDE_SYSTEM_ALLOCATION_AND_CAPABILITY"},
      "end_faces":{"functional_need":"NO_DETERMINISTIC_AXIAL_DATUM__AXIAL_FLOAT_INTENTIONAL","control_family":"NO_STANDALONE_NUMERIC_PERPENDICULARITY_RELEASED_NOW","acceptance_logic":"face form/orientation contribution shall be contained by effective installed axial-float requirement; if future allocation shows a separate orientation limit is needed, allocate it from the axial budget","numeric_state":"N/A_UNLESS_FUTURE_STACK_ALLOCATION_REQUIRES"},
      "guide_bore_texture":{"functional_need":"SLIDING_GUIDE__WEAR_SHAVING_FRICTION_SENSITIVE","control_family":"FUNCTIONAL_SURFACE_CLASS_RETAINED","qualitative_requirement":"clean continuous machined surface; no burr/raised material or damage that causes shaving/scoring/binding","numeric_state":"WAITING_EXTERNAL_PROCESS_WEAR_CAPABILITY_EVIDENCE"},
      "seat_OD_texture":{"functional_need":"STATIC_LOCATING_SLIP_INTERFACE","control_family":"NO_INDEPENDENT_NUMERIC_TEXTURE_RELEASED","qualitative_requirement":"clean/damage-free surface compatible with insertion/removal and dimensional inspection","numeric_state":"N/A_CURRENT_FUNCTION_UNLESS_ASSEMBLY_EVIDENCE_CREATES_STALE_TRIGGER"},
      "axial_face_texture":{"functional_need":"RETENTION_BOUNDARY_WITH_INTENTIONAL_FLOAT__NO_SEAL_NO_PRELOAD","control_family":"NO_INDEPENDENT_NUMERIC_TEXTURE_RELEASED","qualitative_requirement":"clean/burr-free/damage-free; no raised feature causing false seating or loss of axial float","numeric_state":"N/A_CURRENT_FUNCTION_UNLESS_FUTURE_EVIDENCE_CREATES_STALE_TRIGGER"}
    }
    if a.preflight_only:
        print("PASS_PREFLIGHT_EDR051");print("BORE_TO_OD_NUMERIC: WAITING_EXTERNAL");print("GUIDE_TEXTURE_NUMERIC: WAITING_EXTERNAL");return 0
    wr(repo/EDR51,{"schema":"k01.edr.v1","decision_id":"EDR-051","date":"2026-09-18","subject":"P004 residual GPS, face-orientation and surface-texture authority boundary","status":"ACCEPTED_FUNCTIONAL_CONTROL_BOUNDARY__ONLY_REQUIRED_NUMERIC_EXTERNALS_REMAIN","goal":"Remove unjustified generic GPS/texture requirements while preserving every control needed by P004 function and explicitly exposing the numeric controls that still need external evidence.","authority":[str(EDR44).replace("\\","/"),str(EDR46).replace("\\","/"),str(EDR47).replace("\\","/"),str(EDR48).replace("\\","/"),str(EDR50).replace("\\","/"),str(PD).replace("\\","/")],"engineering_question":"Which residual GPS and surface controls are independently required by function, which may be accepted qualitatively, and which numeric values still lack authority?","options":[{"id":"A","description":"Assign generic perpendicularity/runout/Ra values to make the drawing look complete.","disposition":"REJECTED_NO_TOP_DOWN_FUNCTIONAL_ALLOCATION"},{"id":"B","description":"Retain the bore-to-OD control family and sliding-bore surface class, keep their numeric values external until guide/process evidence exists, and avoid standalone numeric face/seat texture controls not demanded by function.","disposition":"ACCEPTED"},{"id":"C","description":"Remove all GPS/surface requirements.","disposition":"REJECTED_BORE_GUIDE_RELATION_AND_SLIDING_SURFACE_ARE_FUNCTIONAL"}],"technical_filter":{"function":"PASS","tolerance":"PASS_NO_DUPLICATE_BUDGET","manufacturing":"PASS_AVOIDS_UNJUSTIFIED_TIGHT_CONTROLS","inspection":"PASS_METHODS_ALREADY_DEFINED_EDR048","assembly":"PASS_AXIAL_FLOAT_AND_SLIP_FUNCTION_PRESERVED","wear_tribology":"GUIDE_BORE_NUMERIC_TEXTURE_WAITING_EXTERNAL","CAD":"NONE"},"decision":["The P004 guide bore shall remain geometrically related to datum A (Ø6.54 locating-OD axis) using total runout or an equivalent ISO-GPS control family; its numeric value is not released until the system guide-performance allocation and manufacturing/metrology capability are controlled.","No independent numeric end-face perpendicularity is released now because P004 has no deterministic axial datum and axial float is intentional. End-face form/orientation effects must remain inside the effective installed axial-float requirement; a separate numeric orientation value is created only if the final stack allocation proves it necessary.","Guide-bore surface texture remains a functional sliding/wear characteristic. Its numeric Ra/Rz is not released from generic practice; process/wear/capability evidence is required. Qualitatively the surface shall be clean, continuous and free from burrs/raised material/damage causing shaving, scoring or binding.","P004 locating-OD and axial-face surfaces do not receive independent numeric roughness requirements from current function. Their acceptance is clean/damage-free plus released dimensional/GPS and assembly requirements. Reopen only on a stale trigger from assembly, wear, supplier process or inspection evidence.","No CAD, DimXpert or drawing mutation is authorized."],"controls":controls,"expected_closure":"PASS_P004_RESIDUAL_GPS_SURFACE_BOUNDARY_CONTROLLED__NUMERIC_EXTERNALS_EXPLICIT","downstream_impact":{"bore_to_OD_numeric":"WAITING_EXTERNAL","guide_bore_texture_numeric":"WAITING_EXTERNAL","end_face_perpendicularity_numeric":"N/A_UNLESS_STACK_ALLOCATION_REQUIRES","seat_OD_texture_numeric":"N/A_CURRENT_FUNCTION","axial_face_texture_numeric":"N/A_CURRENT_FUNCTION","CAD":"NONE","DimXpert":"NONE","drawing":"NONE"}})
    wr(repo/REP,{"schema":"k01.p004.residual_gps_surface_boundary.current.v1","generated_utc":now(),"status":"PASS_P004_RESIDUAL_GPS_SURFACE_BOUNDARY_CONTROLLED__NUMERIC_EXTERNALS_EXPLICIT","part_id":"K01-P-004","controls":controls,"remaining_numeric_external":["bore-to-OD GPS value after guide-system allocation + capability","guide-bore numeric texture after process/wear/capability evidence"],"native_mutation":"NONE","source":"EDR-051"})
    set_char(pd,"P004-C04",{"name":"Guide-bore to locating-OD relationship","status":"CONTROL_FAMILY_RELEASED__NUMERIC_WAITING_EXTERNAL","architecture":"TOTAL RUNOUT or equivalent ISO GPS relative to datum A axis","numeric_tolerance":"OPEN__GUIDE_SYSTEM_ALLOCATION_PLUS_CAPABILITY","source":"EDR-044 + EDR-051"})
    set_char(pd,"P004-C05",{"name":"End-face orientation","status":"NO_STANDALONE_NUMERIC_CONTROL_REQUIRED_CURRENTLY","architecture":"effects contained by effective axial-float requirement; allocate separate orientation only if final stack proves necessary","numeric_tolerance":"N/A_CURRENT_FUNCTION","source":"EDR-051"})
    set_char(pd,"P004-C06",{"name":"guide bore texture","status":"FUNCTIONAL_SURFACE_CLASS_CONTROLLED__NUMERIC_WAITING_EXTERNAL","surface_class":"GUIDE/SLIDING","qualitative_requirement":"clean continuous machined surface; no burr/raised material/damage causing shaving/scoring/binding","numeric_texture":"OPEN__PROCESS_WEAR_CAPABILITY_EVIDENCE_REQUIRED","source":"EDR-051"})
    set_char(pd,"P004-C07",{"name":"seat OD texture","status":"QUALITATIVE_FUNCTIONAL_REQUIREMENT_CONTROLLED","surface_class":"LOCATING/SLIP","qualitative_requirement":"clean/damage-free; compatible with insertion/removal and dimensional inspection","numeric_texture":"N/A_CURRENT_FUNCTION","source":"EDR-051"})
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__INTERNAL_ARCHITECTURE_CLOSED__PHYSICAL_EVIDENCE_PLAN_NEXT"
    obs=[]
    for x in pd.get("open_release_blockers") or []:
        sx=str(x).lower()
        if "functional datum/gps" in sx:obs.append("bore-to-OD GPS numeric value — WAITING_EXTERNAL guide-system allocation + capability")
        elif "surface texture" in sx:obs.append("guide-bore numeric texture — WAITING_EXTERNAL process/wear/capability evidence")
        else:obs.append(x)
    pd["open_release_blockers"]=list(dict.fromkeys(obs));wr(repo/PD,pd)
    read["generated_utc"]=now();read["gps_state"]="FUNCTIONAL_FAMILY_CONTROLLED__BORE_TO_OD_NUMERIC_WAITING_EXTERNAL";read["surface_state"]="SEAT_FACE_QUALITATIVE_CLOSED__GUIDE_BORE_NUMERIC_WAITING_EXTERNAL";read["face_orientation_state"]="NO_STANDALONE_NUMERIC_CURRENTLY__CONTAIN_IN_AXIAL_FLOAT_STACK";read["next_blocker"]="P004-PHYSICAL-EVIDENCE-PLAN-DECISION";read["next"]="Define the minimal controlled P004 physical evidence acquisition plan needed to close external guide-performance and manufacturing/metrology dependencies before partner review, separating characterization from release acceptance. No CAD/DimXpert/drawing mutation."
    for item in read.get("remaining_dependencies") or []:
        if isinstance(item,dict) and item.get("id")=="GPS_NUMERIC":item.update({"state":"WAITING_EXTERNAL","dependency":"guide-system allocation + manufacturing/metrology capability"})
        if isinstance(item,dict) and item.get("id")=="TEXTURE_NUMERIC":item.update({"state":"WAITING_EXTERNAL","dependency":"guide-bore process/wear/capability evidence; seat/face numeric texture N/A current function"})
    wr(repo/READ,read)
    blocker="P004-PHYSICAL-EVIDENCE-PLAN-DECISION";nid="K01-NA-P004-PHYSICAL-EVIDENCE-PLAN";exp="PASS_P004_PHYSICAL_EVIDENCE_PLAN_CONTROLLED__EXTERNAL_ACQUISITION_READY"
    text="Define the minimal controlled P004 physical evidence acquisition plan for the remaining external dependencies: guide-system/repeatability characterization or stakeholder acceptance, P004/P001/P003/P014 dimensional FAI/capability evidence, material lot/process traceability, and guide-surface functional evidence. Separate characterization from release acceptance and do not invent pass/fail thresholds. No CAD/DimXpert/drawing mutation."
    auth=[str(EDR51).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/"),"reports/inspection/K01-P-004_INSPECTION_PROCEDURE_CURRENT.json","reports/engineering/K01_P004_GUIDE_SYSTEM_ALLOCATION_AUTHORITY_RECOVERY_CURRENT.json","reports/engineering/K01_P004_CAPABILITY_BOUNDARY_CURRENT.json"]
    n.update({"schema":"k01.next_actions.current.v43_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"ENGINEERING_PHYSICAL_EVIDENCE_PLAN__NO_NATIVE_MUTATION","authority_set":auth,"last_completed":"EDR-051 — P004 residual GPS/surface authority boundary","latest_engineering_activity":"EDR-051 — P004 residual GPS/surface authority boundary [ACCEPTED_FUNCTIONAL_CONTROL_BOUNDARY__ONLY_REQUIRED_NUMERIC_EXTERNALS_REMAIN]"});wr(repo/NEXT,n)
    gate=rd(repo/GATE,{}) or {};gate.update({"schema":"k01.active_step_gate.v23_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"ENGINEERING PHYSICAL-EVIDENCE PLAN ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING","required_files":auth});wr(repo/GATE,gate)
    front.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"ENGINEERING_PHYSICAL_EVIDENCE_PLAN__NO_NATIVE_MUTATION"}});front.setdefault("timing",{})["ACTIVE_NOW"]=[blocker];closed=front.setdefault("closed_blocker_ids",[]);closed.append("P004-RESIDUAL-GPS-SURFACE-AUTHORITY-BOUNDARY") if "P004-RESIDUAL-GPS-SURFACE-AUTHORITY-BOUNDARY" not in closed else None;wr(repo/FRONT,front)
    cm=rd(repo/CENTER,{}) or {}
    if cm:cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"p004_gps_surface_boundary":{"status":"PASS_EDR_051","report":str(REP).replace("\\","/")}});wr(repo/CENTER,cm)
    for cmd in [[sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],[sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],[sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"]]:subprocess.run(cmd,cwd=repo,check=True)
    print("PASS_P004_RESIDUAL_GPS_SURFACE_BOUNDARY_CONTROLLED__NUMERIC_EXTERNALS_EXPLICIT");print("EDR: EDR-051");print("NEXT:",blocker);print("NATIVE_MUTATION: NONE");return 0
if __name__=="__main__":raise SystemExit(main())
