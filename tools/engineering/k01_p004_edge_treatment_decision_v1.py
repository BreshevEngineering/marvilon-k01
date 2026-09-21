from __future__ import annotations
import argparse, datetime as dt, json, subprocess, sys
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
EDR49=Path("control/decisions/EDR-049_P004_GUIDE_SYSTEM_ALLOCATION_AUTHORITY_RECOVERY.json")
EDR50=Path("control/decisions/EDR-050_P004_FUNCTIONAL_EDGE_TREATMENT.json")
PD=Path("control/product_definition/K01-P-004_PRODUCT_DEFINITION_CURRENT.json")
READ=Path("reports/product_definition/K01-P-004_READINESS_CURRENT.json")
WORK=Path("control/product_definition/K01_P004_PRODUCT_DEFINITION_WORKPACK_CURRENT.json")
PROC=Path("reports/inspection/K01-P-004_INSPECTION_PROCEDURE_CURRENT.json")
REP=Path("reports/engineering/K01_P004_EDGE_TREATMENT_CURRENT.json")
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
        if subprocess.run([sys.executable,"tools/state/"+t,"--repo-root",str(repo),"--write-report"],cwd=repo).returncode:raise SystemExit("HOLD: coherence guard failed before EDR-050")
def set_char(pd,cid,updates):
    for c in pd.get("characteristics") or []:
        if isinstance(c,dict) and c.get("id")==cid:c.update(updates);return
    pd.setdefault("characteristics",[]).append(dict({"id":cid},**updates))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));ap.add_argument("--preflight-only",action="store_true");a=ap.parse_args();repo=Path(a.repo_root).resolve()
    for rel in (EDR49,PD,READ,WORK,PROC,NEXT,GATE,FRONT):
        if not (repo/rel).is_file():print("HOLD_MISSING",rel);return 2
    guard(repo)
    n=rd(repo/NEXT,{}) or {};front=rd(repo/FRONT,{}) or {};pd=rd(repo/PD,{}) or {};read=rd(repo/READ,{}) or {};work=rd(repo/WORK,{}) or {}
    if n.get("next_action_id")!="K01-NA-P004-EDGE-TREATMENT-DECISION":print("HOLD_WRONG_FRONTIER",n.get("next_action_id"));return 3
    if str((front.get("active_blocker") or {}).get("id"))!="P004-EDGE-TREATMENT-DECISION":print("HOLD_WRONG_BLOCKER",front.get("active_blocker"));return 3
    funcs={x.get("id"):x.get("text") for x in work.get("functions") or [] if isinstance(x,dict)}
    if not all(k in funcs for k in ("F01","F02","F03","F04","F06")):print("HOLD_P004_FUNCTION_SET_INCOMPLETE");return 3
    requirements=[
      "All P004 edges created by machining/deburring shall be free of burrs, raised material and loose particles that could enter the P001 guide interface, P003 locating seat or P003/P014 axial-retention interface.",
      "Edge treatment shall not reduce or locally distort the controlled guide-bore, locating-OD or axial-face functional geometry outside its released size/GPS acceptance.",
      "Guide-bore entry/exit edges shall not shave, score or visibly damage P001 during controlled assembly/sliding checks.",
      "Locating-OD and axial-face edges shall not prevent free insertion/removal or create a false seating condition.",
      "No independent chamfer/radius/edge-break dimension is released by this EDR because no function currently requires a specific lead-in geometry. Any future intentional chamfer/radius that changes functional length/contact/clearance requires its own controlled Product Definition characteristic."
    ]
    if a.preflight_only:
        print("PASS_PREFLIGHT_EDR050");print("NUMERIC_EDGE_BREAK: NOT_REQUIRED_BY_CURRENT_FUNCTION");return 0
    wr(repo/EDR50,{"schema":"k01.edr.v1","decision_id":"EDR-050","date":"2026-09-18","subject":"P004 functional edge/deburr requirement","status":"ACCEPTED_FUNCTIONAL_EDGE_REQUIREMENT__NO_INDEPENDENT_NUMERIC_EDGE_BREAK_RELEASED","goal":"Close P004 edge/deburr Product Definition using function and inspection needs without assigning an arbitrary generic chamfer or radius.","authority":[str(WORK).replace("\\","/"),str(PD).replace("\\","/"),"control/decisions/EDR-044_P004_DATUM_FUNCTION_CORRECTION.json",str(PROC).replace("\\","/")],"inputs":{"functions":funcs,"material":"TECAPEEK PVX black","interfaces":["P001 sliding guide","P003 locating/slip seat","P003/P014 axial retention with intentional float"]},"engineering_question":"Which edge condition is functionally required, and does any edge need an independently controlled numeric chamfer/radius now?","options":[{"id":"A","description":"Assign a generic numeric edge break/chamfer from drafting habit.","disposition":"REJECTED_NO_FUNCTIONAL_AUTHORITY"},{"id":"B","description":"Release functional burr-free/no-raised-material requirements and preserve controlled interface geometry, with no independent numeric edge break until function demands one.","disposition":"ACCEPTED"},{"id":"C","description":"Leave all edge requirements undefined.","disposition":"REJECTED_ASSEMBLY_AND_INSPECTION_RISK"}],"technical_filter":{"function":"PASS","tolerance":"PASS_NO_NEW_NUMERIC_VALUE","manufacturing":"PASS_CONTROLLED_DEBURR_ALLOWED","inspection":"PASS_VISUAL_OPTICAL_PLUS_FUNCTIONAL_CHECK","assembly":"PASS_PROTECTS_SLIDING_AND_SEATING","thermal":"NO_CHANGE","material":"PASS_NO_SHAVING_OR_LOOSE_PARTICLES","CAD":"NONE"},"decision":requirements,"inspection":{"method":"visual/optical examination under suitable inspection conditions plus controlled assembly/sliding evidence where applicable","acceptance":"no burr/raised material/loose particle; no shaving/scoring attributable to edge; controlled functional dimensions remain conforming","numeric_chamfer_radius":"NOT_RELEASED_NOT_CURRENTLY_REQUIRED"},"expected_closure":"PASS_P004_EDGE_FUNCTIONAL_REQUIREMENT_CONTROLLED__NO_ARBITRARY_EDGE_BREAK","impact":{"CAD":"NONE","DimXpert":"NONE","drawing":"FUTURE_PRODUCT_DEFINITION_NOTE/ANNOTATION_ONLY_AFTER_P004_READY","native_mutation":"NONE"}})
    wr(repo/REP,{"schema":"k01.p004.edge_treatment.current.v1","generated_utc":now(),"status":"PASS_P004_EDGE_FUNCTIONAL_REQUIREMENT_CONTROLLED__NO_ARBITRARY_EDGE_BREAK","part_id":"K01-P-004","requirements":requirements,"numeric_edge_break":"NOT_REQUIRED_BY_CURRENT_FUNCTION","inspection":"VISUAL_OPTICAL_PLUS_FUNCTIONAL_ASSEMBLY_EVIDENCE","source":"EDR-050","native_mutation":"NONE"})
    set_char(pd,"P004-C11",{"name":"Edge/deburr","status":"RELEASED_FUNCTIONAL_REQUIREMENT","requirement":"BURR_FREE_NO_RAISED_MATERIAL_NO_LOOSE_PARTICLES__PRESERVE_FUNCTIONAL_GEOMETRY","numeric_chamfer_radius":"N/A_CURRENT_FUNCTION__SEPARATE_DECISION_IF_INTENTIONAL_LEAD_IN_ADDED","source":"EDR-050"})
    pd["status"]="PARTIAL_PRODUCT_DEFINITION__RESIDUAL_GPS_SURFACE_BOUNDARY_NEXT";pd["open_release_blockers"]=[x for x in (pd.get("open_release_blockers") or []) if "edge treatment" not in str(x).lower()];wr(repo/PD,pd)
    read["generated_utc"]=now();read["edge_state"]="CLOSED_BY_EDR_050__FUNCTIONAL_QUALITATIVE";read["next_blocker"]="P004-RESIDUAL-GPS-SURFACE-AUTHORITY-BOUNDARY";read["next"]="Resolve the remaining P004 GPS/face-orientation/surface-texture authority boundary: release only functionally justified control families and explicitly classify numeric values that still depend on guide requirement, process/wear or capability evidence. No CAD/DimXpert/drawing mutation.";wr(repo/READ,read)
    blocker="P004-RESIDUAL-GPS-SURFACE-AUTHORITY-BOUNDARY";nid="K01-NA-P004-RESIDUAL-GPS-SURFACE-BOUNDARY";exp="PASS_P004_RESIDUAL_GPS_SURFACE_BOUNDARY_CONTROLLED__NUMERIC_EXTERNALS_EXPLICIT"
    text="Resolve the remaining P004 GPS/face-orientation/surface-texture authority boundary. Use P004 function, EDR-044 datum A, EDR-046/047 functional budgets and EDR-048 inspection architecture. Release only controls required by function; keep any numeric GPS/texture values dependent on missing guide/process/wear/capability evidence explicitly external. No CAD/DimXpert/drawing mutation."
    auth=[str(EDR50).replace("\\","/"),str(PD).replace("\\","/"),str(READ).replace("\\","/"),"control/decisions/EDR-044_P004_DATUM_FUNCTION_CORRECTION.json","control/decisions/EDR-046_P004_JOINT_TOLERANCE_BUDGET_20C.json","control/decisions/EDR-047_P004_AXIAL_RECENTER.json","control/decisions/EDR-048_P004_INSPECTION_CONDITIONING_PROCEDURE.json"]
    n.update({"schema":"k01.next_actions.current.v42_program_front","active_blocker":blocker,"current_blocker":blocker+":OPEN","next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"ENGINEERING_GPS_SURFACE_BOUNDARY_DECISION__NO_NATIVE_MUTATION","authority_set":auth,"last_completed":"EDR-050 — P004 functional edge/deburr requirement","latest_engineering_activity":"EDR-050 — P004 functional edge/deburr requirement [ACCEPTED_FUNCTIONAL_EDGE_REQUIREMENT__NO_INDEPENDENT_NUMERIC_EDGE_BREAK_RELEASED]"});wr(repo/NEXT,n)
    gate=rd(repo/GATE,{}) or {};gate.update({"schema":"k01.active_step_gate.v22_program_front","generated_utc":now(),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,"mutation_authorized":False,"mutation_scope":"ENGINEERING GPS/SURFACE AUTHORITY BOUNDARY ONLY; NO NATIVE CAD; NO DIMXPERT; NO DRAWING","required_files":auth});wr(repo/GATE,gate)
    front.update({"generated_utc":now(),"active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},"next_allowed_action":{"id":nid,"text":text,"authority_set":auth,"expected_closure":exp,"execution_mode":"ENGINEERING_GPS_SURFACE_BOUNDARY_DECISION__NO_NATIVE_MUTATION"}});front.setdefault("timing",{})["ACTIVE_NOW"]=[blocker];closed=front.setdefault("closed_blocker_ids",[]);closed.append("P004-EDGE-TREATMENT-DECISION") if "P004-EDGE-TREATMENT-DECISION" not in closed else None;wr(repo/FRONT,front)
    cm=rd(repo/CENTER,{}) or {}
    if cm:cm.update({"generated_utc":now(),"active_blocker":blocker,"next_action_id":nid,"p004_edge_requirement":{"status":"PASS_EDR_050","report":str(REP).replace("\\","/")}});wr(repo/CENTER,cm)
    for cmd in [[sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],[sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],[sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"]]:subprocess.run(cmd,cwd=repo,check=True)
    print("PASS_P004_EDGE_FUNCTIONAL_REQUIREMENT_CONTROLLED__NO_ARBITRARY_EDGE_BREAK");print("EDR: EDR-050");print("NEXT:",blocker);print("NATIVE_MUTATION: NONE");return 0
if __name__=="__main__":raise SystemExit(main())
