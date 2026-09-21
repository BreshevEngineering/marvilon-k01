from __future__ import annotations
import argparse, datetime as dt, json, shutil, subprocess, sys
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01");L=Path(r"D:\BreshevEngineering\K01_local")
PREF=Path("reports/engineering/K01_P004_PRODUCT_DEFINITION_PREFLIGHT_CURRENT.json")
SPINE=Path("reports/control/K01_PROJECT_CONTROL_SPINE_CURRENT.json")
DRAW=Path("reports/control/K01_DRAWING_LANE_STATUS_CURRENT.json")
GOAL=Path("control/project/K01_GOAL_LOCK_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
GATE=Path("control/project/K01_ACTIVE_STEP_GATE.json")
FRONT=Path("control/state/K01_COMPLETION_FRONTIER_CURRENT.json")
CENTER=Path("control/center/K01_CENTER_MASTER_FEED_CURRENT.json")
def rd(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def wr(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def backup(repo,local,rels):
 out=local/"backups"/("TRANSITION_MAIN_FRONT_TO_P004_"+dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
 for r in rels:
  p=repo/r
  if p.exists():
   d=out/r;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));ap.add_argument("--local-root",default=str(L));a=ap.parse_args()
 repo=Path(a.repo_root);local=Path(a.local_root)
 for r in (PREF,SPINE,DRAW,GOAL,NEXT,GATE,FRONT):
  if not (repo/r).exists():raise SystemExit("HOLD: missing "+str(r))
 pref=rd(repo/PREF);draw=rd(repo/DRAW)
 if pref.get("status")!="PASS_PREP_COMPLETE__HOLD_ENGINEERING_DECISIONS":raise SystemExit("HOLD: P004 preflight not ready.")
 if draw.get("status")!="DRAWING_AUTHORING_SEPARATED_FROM_MAIN_ENGINEERING_LANE":raise SystemExit("HOLD: drawing lane is not explicitly separated.")
 b=backup(repo,local,[GOAL,NEXT,GATE,FRONT,CENTER]);print("BACKUP:",b)

 oldg=rd(repo/GOAL);oldn=rd(repo/NEXT);oldgate=rd(repo/GATE);oldf=rd(repo/FRONT)
 epoch=oldn.get("state_epoch") or oldf.get("state_epoch")
 deliver="K01-P-004 PRODUCT DEFINITION"
 level="L5"
 active="K01-P-004"
 blocker="P004-REQ-TOL-MAT-PROCESS-CLOSURE"
 nid="K01-NA-P004-PD-ENGINEERING-CLOSURE"
 exp="PASS_P004_ENGINEERING_BASIS_NARROWED__NEXT_BLOCKER_IDENTIFIED"
 text="Close P004 requirements/interfaces through Technical Filter: service-temperature applicability, guide-clearance requirement, worst-case tolerance allocation, production material/process and inspection basis. No CAD/DimXpert/drawing mutation."

 g=dict(oldg)
 g.update({"schema":"k01.goal_lock.current.v2_program_front","generated_utc":now(),"current_lifecycle_level":level,
  "current_deliverable":deliver,"deliverable_class":"PRODUCT DEFINITION CLOSURE","primary_objective":"Bring K01-P-004 to manufacturable and inspectable Product Definition readiness before any D004/PMI authoring.",
  "active_dependency":"P004 REQUIREMENTS / TOLERANCE / MATERIAL / PROCESS CLOSURE","active_engineering_object":active,
  "current_execution_mode":"ENGINEERING_DECISION_READ_ONLY_OVER_NATIVE_CAD","wip_limit":1})
 g["drawing_branch_waiting"]={"K01-D-006":"WAITING_EXTERNAL_USER_CONTROLLED_MARVILON_DRAWING_BRANCH","rule":"Native drawing authoring is not main engineering WIP."}
 wr(repo/GOAL,g)

 n={"schema":"k01.next_actions.current.v30_program_front","state_epoch":epoch,"generated_utc":now(),
    "current_lifecycle_level":level,"current_deliverable":deliver,"deliverable_class":"PRODUCT DEFINITION CLOSURE","wip_limit":1,
    "active_engineering_object":active,"active_dependency":"P004 REQUIREMENTS / TOLERANCE / MATERIAL / PROCESS CLOSURE",
    "active_line":"K01-P004-PRODUCT-DEFINITION-CLOSURE","active_blocker":blocker,"current_blocker":blocker+":OPEN",
    "next_1":text,"next_action_id":nid,"expected_closure":exp,"execution_mode":"ENGINEERING_DECISION__NO_NATIVE_MUTATION",
    "authority_set":[str(PREF).replace("\\","/"),"control/product_definition/K01_P004_PRODUCT_DEFINITION_WORKPACK_CURRENT.json",
                     "reports/engineering/K01_P004_TECHNICAL_FILTER_CURRENT.json","reports/engineering/K01_P004_CALCULATION_REGISTER_CURRENT.json",
                     "reports/control/K01_PROJECT_CONTROL_SPINE_CURRENT.json"],
    "waiting_external":[{"id":"K01-D-006","state":"WAITING_EXTERNAL","owner":"Marvilon drawing branch / user controlled","note":"Do not run drawing API in main engineering lane."}],
    "do_not_do":["Do not generate/refine D006/D004 here.","Do not write DimXpert/PMI before Product Definition READY.","Do not mutate native P004/P003/P001/P014 CAD during this decision step.","Do not hand-edit EBOM/MBOM authority.","Do not restart FEMM or closed P007 EDRs."]}
 wr(repo/NEXT,n)

 gate={"schema":"k01.active_step_gate.v10_program_front","state_epoch":epoch,"generated_utc":now(),
       "step_id":"K01-STEP-P004-L5-PD-CLOSURE","current_lifecycle_level":level,"active_line":"K01-P004-PRODUCT-DEFINITION-CLOSURE",
       "checkpoint_id":oldgate.get("checkpoint_id"),"intent":nid,"intent_text":text,"active_blocker":blocker,"expected_closure":exp,
       "mutation_authorized":False,"mutation_scope":"READ_ONLY_ENGINEERING_DECISION; NO NATIVE CAD; NO DIMXPERT; NO DRAWING; NO BOM AUTHORITY MUTATION",
       "result_on_pass":exp,"required_files":n["authority_set"]}
 wr(repo/GATE,gate)

 f={"schema":"k01.completion_frontier.current.v3_program","state_epoch":epoch,"generated_utc":now(),
    "current_lifecycle_level":level,"lifecycle_name":"Product Definition","current_deliverable":deliver,"wip_limit":1,
    "active_engineering_object":active,"active_dependency":n["active_dependency"],
    "active_blocker":{"id":blocker,"state":"OPEN","timing":"ACTIVE_NOW"},
    "next_allowed_action":{"id":nid,"text":text,"authority_set":n["authority_set"],"expected_closure":exp,"execution_mode":"ENGINEERING_DECISION__NO_NATIVE_MUTATION"},
    "maturity":{"K01-P-004":"L5_PRODUCT_DEFINITION_ACTIVE","K01-P-007":"PRODUCT_DEFINITION_READY","K01-D-006":"L6_CANDIDATE_TPD__WAITING_EXTERNAL_USER_DRAWING","physical_qualification":"OPEN_L8","release":"HOLD"},
    "timing":{"ACTIVE_NOW":[blocker],
              "WAITING_EXTERNAL":["K01-D-006 USER-CONTROLLED DRAWING FINALIZATION"],
              "WAITING_DEPENDENCY":["D004/PMI until P004 Product Definition READY","P004 BOM release row until material/process authority closes"],
              "LATER":["remaining Product Definitions","magnetic physical qualification","EBOM/MBOM release","remaining drawings","manufacturing/inspection capability","verification/qualification","Git/configuration release checkpoint","SW2026 migration + chamber integration"],
              "DEBT":["Drawing System fresh-section defect","broad repository cleanup","Center UI refinements"]},
    "closed_blocker_ids":["K01-NA-C12-MEDIA-SEAL-LEAK","EDR-035","EDR-036","EDR-037"]}
 wr(repo/FRONT,f)

 c=rd(repo/CENTER) if (repo/CENTER).exists() else {}
 c.update({"generated_utc":now(),"current_lifecycle_level":level,"current_deliverable":deliver,"active_engineering_object":active,
           "active_blocker":blocker,"next_action_id":nid,"drawing_waiting_external":"K01-D-006"})
 wr(repo/CENTER,c)

 subprocess.run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
 subprocess.run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],cwd=repo,check=True,text=True)
 print("PASS: main engineering completion frontier transitioned to P004 Product Definition.")
 print("D006: WAITING_EXTERNAL / user-controlled drawing branch.")
 return 0
if __name__=="__main__":raise SystemExit(main())
