from __future__ import annotations
import argparse,json,subprocess,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone

STAGES=[
    (1,"REQUIREMENT"),
    (2,"FUNCTION_INTERFACE"),
    (3,"ARCHITECTURE_ALTERNATIVES"),
    (4,"NOMINAL_DESIGN"),
    (5,"ANALYSIS"),
    (6,"VARIATION_PROCESS_INSPECTION"),
    (7,"TPD"),
    (8,"VERIFICATION"),
    (9,"QUALIFICATION_BENCH"),
    (10,"RELEASE"),
]

P007_REQS=[
    "REQ-K01-FUNC-001","REQ-K01-SERVICE-001","REQ-K01-P007-L-001","REQ-K01-J2-LOC-001",
    "REQ-K01-MAT-P007-001","REQ-K01-ENV-DP-001","REQ-K01-ENV-TEMP-001",
    "REQ-K01-MEDIA-001","REQ-K01-SEAL-001","REQ-K01-LEAK-001","REQ-K01-SERVICE-CYCLES-001",
    "REQ-K01-TPD-001"
]

def load(p,default=None):
    try:return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:return default
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
def now():return datetime.now(timezone.utc).isoformat()

def console_print(text):
    """Print without failing on legacy Windows console code pages.
    Files remain UTF-8; only unsupported console glyphs are replaced safely.
    """
    s=str(text)
    enc=getattr(sys.stdout,"encoding",None) or "utf-8"
    try:
        sys.stdout.write(s+"\\n")
    except UnicodeEncodeError:
        safe=s.encode(enc,errors="replace").decode(enc,errors="replace")
        sys.stdout.write(safe+"\\n")
    sys.stdout.flush()
def find_current_state(repo):
    candidates=[
        repo/"handoff"/"current"/"K01_AI_HANDOFF"/"reports"/"control"/"K01_CURRENT_STATE.json",
        repo/"reports"/"control"/"K01_CURRENT_STATE.json",
        repo/"control"/"K01_CURRENT_STATE.json",
    ]
    for p in candidates:
        if p.exists():return p
    hits=list(repo.rglob("K01_CURRENT_STATE.json"))
    return hits[0] if hits else None

def req_map(state):
    rows=((state.get("requirements") or {}).get("rows") or []) if isinstance(state,dict) else []
    return {r.get("id"):r for r in rows if isinstance(r,dict) and r.get("id")}

def gate_map(state):
    rows=((state.get("gates") or {}).get("rows") or []) if isinstance(state,dict) else []
    return {r.get("gate"):r for r in rows if isinstance(r,dict) and r.get("gate")}

def stage(status,why,evidence,blockers=None,next_actions=None):
    return {
        "status":status,
        "why":why,
        "evidence":evidence,
        "blockers":blockers or [],
        "next_actions":next_actions or []
    }

def assess(repo):
    sp=find_current_state(repo)
    state=load(sp,{}) if sp else {}
    rm=req_map(state);gm=gate_map(state)
    reqs={rid:rm.get(rid) for rid in P007_REQS if rm.get(rid)}
    open_req=[rid for rid,r in reqs.items() if r.get("requirement_status") in ("OPEN","PARTIAL","CANDIDATE")]
    release_block_req=[rid for rid,r in reqs.items() if r.get("release_blocker")]

    visual=load(repo/"control"/"drawings"/"K01_D006_VISUAL_QA_CURRENT.json",{}) or {}
    d006=load(repo/"control"/"drawings"/"K01_D006_RELEASE_DEFINITION.json",{}) or {}
    femm=load(repo/"control"/"analysis"/"K01_FIXED_COIL_FEMM_BENCHMARK.json",{}) or {}
    bom=load(repo/"control"/"bom"/"K01_BOM_RELEASE_WORKLIST.json",{}) or {}

    stages={}
    stages["1_REQUIREMENT"]=stage(
        "HOLD_OPEN_REQUIREMENTS" if open_req else "PASS",
        "P007/J2 release cannot advance while media/seal/leak/service requirements are not released.",
        [str(sp.relative_to(repo)).replace("\\","/") if sp else None],
        open_req,
        ["Define media/cleaning envelope","Define quantitative leak acceptance","Release required service-cycle target",
         "Complete static-seal requirement after media envelope is frozen"] if open_req else []
    )
    stages["2_FUNCTION_INTERFACE"]=stage(
        "PASS",
        "Current-state gates report functional requirement, architecture integrity and interfaces/datums as PASS for the removable J2 interface.",
        [str(sp.relative_to(repo)).replace("\\","/") if sp else None],
        [],
        []
    )
    edr025=repo/"control/decisions/EDR-025_P007_MONOLITHIC_REMOVABLE_J2_BASELINE.json"
    arch_pass=edr025.is_file()
    stages["3_ARCHITECTURE_ALTERNATIVES"]=stage(
        "PASS" if arch_pass else "HOLD_ARCHITECTURE_DECISION",
        "EDR-025 controls active C2R1 architecture: P007 is monolithic machined 316L with integral blind end; P003↔P007 J2 is removable metal-face + static O-ring + 3×M2.5; permanent P003↔P007 weld is rejected.",
        [str(sp.relative_to(repo)).replace("\\","/") if sp else None,
         "control/decisions/EDR-025_P007_MONOLITHIC_REMOVABLE_J2_BASELINE.json",
         "docs/K01_P007_J2_MANUFACTURING_BASELINE_CURRENT.md"],
        [] if arch_pass else ["EDR-025 architecture decision missing"],
        [] if arch_pass else ["Restore/review EDR-025 before downstream manufacturing decisions"]
    )
    stages["4_NOMINAL_DESIGN"]=stage(
        "PASS",
        "Native P007/J2 geometry is controlled: L35, locator Ø14.10, OD33, 3×Ø2.90 on PCD26.5, OD10/ID9.4 and 316L.",
        ["control/snapshot/K01_GATE04E_CURRENT_SNAPSHOT.json",
         "control/drawings/K01_D006_RELEASE_DEFINITION.json"],
        [],
        []
    )
    t07a_edr=repo/"control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json"
    t07a_pass=t07a_edr.is_file()
    pressure_hold=(gm.get("pressure_vacuum_sealing") or {}).get("status","").startswith("HOLD")
    analysis_block=[]
    if (not t07a_pass) and (gm.get("buckling_stability") or {}).get("status")=="STALE": analysis_block.append("buckling_stability STALE")
    if pressure_hold: analysis_block.append("pressure_vacuum_sealing HOLD")
    if t07a_pass and pressure_hold:
        analysis_status="HOLD_PRESSURE_VACUUM_SEALING__T07A_PASS"
        analysis_why="EDR-027 closes current P007 global +0.20 bar static and -0.20 bar linear buckling. Analysis remains HOLD only for pressure/vacuum/sealing closure outside T07A."
        analysis_next=["Close seal/media/leak pressure-vacuum requirements; do not rerun T07A unless an EDR-027 stale trigger fires."]
    elif analysis_block:
        analysis_status="HOLD_ANALYSIS_REFRESH"
        analysis_why="Required P007 analysis evidence is incomplete."
        analysis_next=["Close the listed analysis blockers."]
    else:
        analysis_status="PASS_WITH_LIMIT"
        analysis_why="Current required P007 analysis screens are controlled for this lifecycle stage."
        analysis_next=[]
    stages["5_ANALYSIS"]=stage(
        analysis_status,analysis_why,
        [str(sp.relative_to(repo)).replace("\\","/") if sp else None,
         "control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json",
         "control/project/K01_PROJECT_CLOSURE_MATRIX.json"],
        analysis_block,analysis_next)
    stages["6_VARIATION_PROCESS_INSPECTION"]=stage(
        "HOLD",
        "Architecture/process route is selected by EDR-025, but functional tolerances, monolithic thin-wall/blind-end capability, seal/fastener qualification, quantitative leak acceptance and inspection plan are not yet released.",
        ["control/drawings/K01_P007_FUNCTIONAL_TOLERANCE_PLAN.json",
         "control/product_definition/K01_J2_CONTAINMENT_CLOSURE_PLAN.json",
         "control/manufacturing/K01_P007_MANUFACTURING_FEASIBILITY_CURRENT.json"],
        ["thin-wall/blind-end manufacturing capability","seal/media/leak definition","fastener/process qualification","inspection plan"],
        ["Qualify 0.30 mm nominal wall / integral blind-end manufacturing and inspection capability","Close surface texture/inspection/measurement conditions",
         "Close T04/T05/T06 seal/fastener/service inputs","Define C12 quantitative leak acceptance and inspection methods"]
    )
    tpd_status="HOLD"
    tpd_reason="Current D006 is a view sheet with controlled notes, not a manufacturing TPD drawing."
    if visual.get("status")=="FAIL_NOT_A_MANUFACTURING_DRAWING":
        tpd_status="HOLD_REAUTHOR_D006"
    stages["7_TPD"]=stage(
        tpd_status,
        tpd_reason,
        ["control/drawings/K01_D006_VISUAL_QA_CURRENT.json",
         "control/drawings/K01_D006_RELEASE_DEFINITION.json",
         "control/bom/K01_BOM_RELEASE_WORKLIST.json"],
        ["real K01-D-006 drawing","EBOM/MBOM release blockers"],
        ["Do not author release D006 until Stages 1,5,6 relevant blockers close",
         "Retain current PDF/SLDDRW only as API/view-layout evidence"]
    )
    stages["8_VERIFICATION"]=stage(
        "HOLD",
        "Drawing semantic QA, inspection cross-check, leak verification and affected-node re-verification are incomplete.",
        ["control/change/K01_CHANGE_CURRENT.json"],
        ["drawing semantic QA","inspection cross-check","leak verification"],
        []
    )
    stages["9_QUALIFICATION_BENCH"]=stage(
        "HOLD",
        "P007/J2 leak/service qualification is incomplete. Magnetic bench belongs to the actuator lane and is tracked separately.",
        [str(sp.relative_to(repo)).replace("\\","/") if sp else None],
        ["leak test","service-cycle qualification"],
        []
    )
    stages["10_RELEASE"]=stage(
        "DEFERRED",
        "Release is impossible while earlier mandatory stages are HOLD.",
        ["control/project/K01_PROJECT_CLOSURE_MATRIX.json"],
        ["upstream lifecycle holds"],
        []
    )

    # Strict release sequence = first non-pass mandatory stage.
    order=list(stages.keys())
    first_hold=next((k for k in order if not stages[k]["status"].startswith("PASS")),None)

    # Productive execution queue: tasks may run only when their own upstream inputs are already released.
    queue=[
        {"priority":1,"lane":"REQUIREMENT","task":"Freeze REQ-K01-MEDIA-001 media/cleaning envelope",
         "type":"EXTERNAL_INPUT_REQUIRED","unblocks":["REQ-K01-SEAL-001","Stage 6 seal process","Stage 9 leak qualification"]},
        {"priority":2,"lane":"REQUIREMENT","task":"Define REQ-K01-LEAK-001 quantitative leak-test acceptance",
         "type":"ENGINEERING_REQUIREMENT_DECISION","unblocks":["Stage 6 inspection","Stage 9 qualification","D006 release notes"]},
        {"priority":3,"lane":"ANALYSIS","task":"Run T07A current P007 pressure-shell refresh: +0.20 bar static and -0.20 bar linear buckling",
         "type":"MANUAL_CONTROLLED_EXECUTABLE_NOW","upstream":["REQ-K01-ENV-DP-001 RELEASED","current P007 geometry frozen","EDR-026 scope split"],
         "boundary":"Does not close local J2 contact/seal/preload/leak requirements"},
        {"priority":4,"lane":"VARIATION","task":"C01/C05/C06/blind-end released by EDR-030; close remaining surface/inspection/process semantics",
         "type":"ENGINEERING_CLOSURE","upstream":["EDR-030 primary dimensions released"]},
        {"priority":5,"lane":"PROCESS_INSPECTION","task":"Close monolithic P007 capability plus seal/fastener/leak/inspection requirements",
         "type":"ENGINEERING_CLOSURE","upstream":["EDR-025 architecture controlled"]},
        {"priority":6,"lane":"TPD","task":"Author full K01-D-006 manufacturing drawing once from released Product Definition",
         "type":"BLOCKED","blocked_by":["Stage 5 pressure/vacuum/sealing release hold","Stage 6 release blockers","Product Definition DRAWING_RELEASE_READY"]}
    ]

    if t07a_pass:
        queue=[q for q in queue if "Run T07A current P007 pressure-shell refresh" not in str(q.get("task",""))]
    for i,q in enumerate(queue,1): q["priority"]=i

    return {
        "schema":"k01.product_development_state.v1",
        "generated_utc":now(),
        "scope":"P007_J2",
        "lifecycle_stages":stages,
        "first_release_gate_hold":first_hold,
        "requirements_open":open_req,
        "release_blocking_requirements":release_block_req,
        "execution_queue":queue,
        "policy":{
            "release_gates_are_sequential":True,
            "independent_execution_may_run_in_parallel_only_when_its_own_upstream_inputs_are_released":True,
            "center_is_not_authority":True,
            "drawing_is_not_allowed_to_define_missing_engineering_requirements":True
        }
    }

def render_md(state):
    lines=["# K01 Product Development System - P007/J2","",
           f"Generated: {state['generated_utc']}","",
           "## Release lifecycle"]
    for key,val in state["lifecycle_stages"].items():
        lines.append(f"- **{key}** — `{val['status']}` — {val['why']}")
        if val["blockers"]:
            lines.append("  - blockers: "+", ".join(str(x) for x in val["blockers"]))
    lines+=["","## First mandatory release hold",f"`{state['first_release_gate_hold']}`","","## Productive execution queue"]
    for q in state["execution_queue"]:
        lines.append(f"{q['priority']}. **{q['lane']}** — {q['task']} — `{q['type']}`")
    return "\n".join(lines)+"\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=r"D:\BreshevEngineering\marvilon-k01")
    sub=ap.add_subparsers(dest="cmd",required=True)
    sub.add_parser("status");sub.add_parser("next");sub.add_parser("report")
    a=ap.parse_args();repo=Path(str(a.repo_root).strip().strip('"')).resolve()
    state=assess(repo)
    write(repo/"control"/"pds"/"K01_P007_J2_LIFECYCLE.json",state)
    write(repo/"control"/"pds"/"K01_WORK_QUEUE.json",{
        "schema":"k01.work_queue.v1","generated_utc":state["generated_utc"],
        "scope":"P007_J2","queue":state["execution_queue"]
    })
    rp=repo/"reports"/"pds"/"K01_P007_J2_READINESS_CURRENT.md"
    rp.parent.mkdir(parents=True,exist_ok=True);rp.write_text(render_md(state),encoding="utf-8")
    if a.cmd=="next":
        console_print(json.dumps(state["execution_queue"][0],indent=2,ensure_ascii=False))
    elif a.cmd=="report":
        console_print(rp)
    else:
        console_print(render_md(state))
    return 0
if __name__=="__main__":raise SystemExit(main())
