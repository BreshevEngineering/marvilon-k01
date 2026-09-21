#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,sys,subprocess
from datetime import datetime,timezone
from pathlib import Path

ARCH=Path("control/drawings/K01_DRAWING_ARCHITECTURE_CURRENT.json")
WORK=Path("control/drawings/K01_D006_MANUAL_FINISH_WORKPACK_CURRENT.md")
SESSION=Path("control/project/K01_AI_SESSION_RULES_CURRENT.json")
HANDOFF=Path("control/project/K01_HANDOFF_REQUIRED_SOURCES_CURRENT.json")
NEXT=Path("control/project/K01_NEXT_ACTIONS_CURRENT.json")
ACTIVE=Path("control/project/K01_ACTIVE_STEP_GATE.json")

def load(p,default=None):
    try:return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except:return default
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+".tmp")
    t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");os.replace(str(t),str(p))
def run_backend(root,rel,timeout=180):
    p=root/rel
    if not p.is_file():return
    cp=subprocess.run([sys.executable,str(p),"--repo-root",str(root)],cwd=str(root),capture_output=True,text=True,errors="replace",timeout=timeout)
    if cp.stdout:print(cp.stdout,end="")
    if cp.stderr:print(cp.stderr,end="",file=sys.stderr)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    stamp=datetime.now(timezone.utc).isoformat()

    s=load(root/SESSION,{}) or {}
    rules=s.get("permanent_rules",[]) or []
    additions=[
      ("R19","2D drawing is a derivative presentation of controlled product definition; do not create a second independent dimensional authority."),
      ("R20","Released drawing dimensions/GD&T should originate in native DimXpert/PMI or another controlled model annotation. Manual layout is allowed; manual retyping of released semantic values is not."),
      ("R21","On SOLIDWORKS 2018 use annotation-view drawing import for DimXpert transfer. Do not spend critical-path time recreating this UI path with unproven COM automation."),
      ("R22","Professional drawing quality has two gates: automated semantic QA and human visual QA. File creation alone is not a professional-drawing PASS."),
      ("R23","Project/debug/open-item tables belong in workpacks/inspection evidence, not on the final manufacturing sheet unless the controlled drawing standard explicitly requires them."),
      ("R24","Use one controlled title block and property-linked document metadata. Never use a full native filename as visible drawing title/number."),
    ]
    have={x.get("id") for x in rules if isinstance(x,dict)}
    for rid,rule in additions:
        if rid not in have:rules.append({"id":rid,"rule":rule})
    s["permanent_rules"]=rules
    order=s.get("first_read_order",[]) or []
    for x in [str(ARCH).replace("\\","/"),str(WORK).replace("\\","/")]:
        if x not in order:order.insert(1,x)
    s["first_read_order"]=order
    write(root/SESSION,s)

    h=load(root/HANDOFF,{}) or {};req=h.get("required",[]) or []
    for x in [
      "docs/architecture/K01_DRAWING_PRODUCT_DEFINITION_WORKFLOW_v1.md",
      str(ARCH).replace("\\","/"),
      str(WORK).replace("\\","/"),
      "tools/medtas/drawing_workflow_transition_v1.py",
      "cad_api/solidworks_2018_proven/RUN_DRAWING_WORKFLOW_TRANSITION.cmd"
    ]:
        if x not in req:req.append(x)
    h["required"]=req
    h["note"]="Drawing workflow is hybrid MBD + 2D derivative. New chats must read drawing architecture/workpack before generating or modifying drawings."
    write(root/HANDOFF,h)

    n=load(root/NEXT,{}) or {}
    n["current_stage"]="K01_D006_MANUAL_NATIVE_PMI_TRANSFER_AND_PROFESSIONAL_LAYOUT"
    n["last_completed"]="Automation proved linked SLDDRW/PDF generation, section command, four P007 references and source-hash invariance. Visual review reclassified that artifact as a linked drawing seed, not a professional drawing."
    n["current_blocker"]="Manual native DimXpert transfer + professional view/layout cleanup is required in SOLIDWORKS; C02/C05 must be imported from model PMI, not retyped."
    n["next_1"]="Create a clean K01-D-006 drawing candidate; longitudinal section primary, flange end view secondary, optional J2 detail, small isometric."
    n["next_2"]="Import DimXpert annotations from model/annotation views in SOLIDWORKS 2018 and perform human layout/detailing."
    n["then"]="Run automated semantic QA + human visual QA, then inspection linkage and P007 structural/buckling refresh."
    n["drawing_architecture"]=str(ARCH).replace("\\","/")
    n["manual_finish_workpack"]=str(WORK).replace("\\","/")
    write(root/NEXT,n)

    active={
      "schema":"k01.active_step_gate.v1",
      "step_id":"K01-STEP-P4-D006-MANUAL-PMI-TRANSFER-PROFESSIONAL-LAYOUT",
      "active_line":"K01-P007-PROFESSIONAL-PRODUCT-DEFINITION",
      "checkpoint_id":"K01-CP-20260910-BASELINE-02C-PROMOTED",
      "intent":"MANUALLY_IMPORT_CURRENT_NATIVE_DIMXPERT_INTO_CLEAN_D006_DRAWING_AND_FINISH_PROFESSIONAL_LAYOUT_WITHOUT_RETYPING_CONTROLLED_VALUES",
      "mutation_authorized":True,
      "result_on_pass":"PASS_TO_D006_SEMANTIC_AND_VISUAL_QA",
      "required_files":[str(ARCH).replace("\\","/"),str(WORK).replace("\\","/"),"reports/control/K01_P007_PMI_PROVEN_CURRENT.json","reports/control/K01_NODE_TECHNICAL_FILTER_CURRENT.json"],
      "impact_declarations":{
        "requirements":"No OPEN release tolerance/process/leak value may be invented or converted to released status during drawing layout.",
        "materials":"P007 material remains AISI 316L / EN 1.4404 and must be shown from controlled product data.",
        "bom":"Drawing layout does not alter geometry, quantity or BOM authority.",
        "dimxpert_drawings":"C02/C05 must transfer from current native DimXpert PMI using SW2018 annotation-view import; controlled semantic values must not be retyped.",
        "inspection":"Drawing callouts will later map back to the same Cxx/PMI authority; inspection criteria are not inferred from free drawing text.",
        "dependencies":"Any solid-geometry or PMI-semantic change invalidates the drawing seed and triggers stale propagation; layout-only changes do not alter product geometry.",
        "technical_filter":"Manufacturing, tolerancing, inspection, service, material and release categories remain explicit; unresolved release characteristics remain OPEN.",
        "rollback":"Manual drawing work is performed on a new timestamped drawing candidate; existing proven P007 PMI candidate/canonical CAD remain unchanged.",
        "evidence":"Source part/hash, imported PMI readback, drawing-view references, semantic lint, PDF/BMP render, and human visual-QA record are required."
      }
    }
    write(root/ACTIVE,active)

    for rel,to in [
      ("tools/medtas/rebuild_medtas_state.py",300),
      ("tools/medtas/technical_filter_map_v2_2.py",180),
      ("tools/assurance/engineering_step_gate.py",180),
      ("tools/assurance/build_engineering_dashboard.py",180),
    ]:run_backend(root,rel,to)

    print("STATUS: PASS_DRAWING_WORKFLOW_TRANSITION")
    print("ARCHITECTURE:",root/ARCH)
    print("WORKPACK:",root/WORK)
    print("NEXT: manual native PMI transfer + professional SOLIDWORKS layout")
    return 0

if __name__=="__main__":raise SystemExit(main())
