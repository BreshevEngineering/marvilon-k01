from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p,d=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return d

def dump(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    derived=load(r/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',{}) or {};nodes=derived.get('nodes',{})
    interface=load(r/'control/parameters/K01_J2_INTERFACE_PARAMETERS_v1_7.json',{}) or {}
    state=load(r/'reports/control/K01_CURRENT_STATE.json',{}) or load(r/'control/state/K01_CURRENT_STATE.json',{}) or {}
    mbd=load(r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',{}) or {}
    candidates=load(r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_7.json',{}) or load(r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_6.json',{}) or {}
    mbdplan=load(r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_PLAN_v1_7.json',{}) or {}
    drawplan=load(r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json',{}) or {}
    drawing=load(r/'reports/medtas/drawing/current/K01_DRAWING_MBD_RELEASE_WORKPACK_v1_6.json',{}) or load(r/'reports/medtas/drawing/current/K01_DRAWING_MBD_RELEASE_WORKPACK_v1_5.json',{}) or {}
    bom=load(r/'reports/medtas/bom/current/K01_BOM_MODEL_A001_v1.json',{}) or {};bomv=load(r/'reports/medtas/bom/current/K01_BOM_VERIFY_A001_v1.json',{}) or {}
    struct=load(r/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json',{}) or {};fm=load(r/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json',{}) or {};fq=load(r/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_QUAL_P006_v1_7.json',{}) or {}
    bolt=load(r/'reports/medtas/structural/current/K01_STRUCTURAL_BOLT_EQUIV_P006_v1_7.json',{}) or load(r/'reports/medtas/structural/current/K01_STRUCTURAL_BOLT_EQUIV_P006_v1_6.json',{}) or {}
    neutral=load(r/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_7.json',{}) or {}
    mesh=load(r/'reports/medtas/calculix/current/K01_STRUCTURAL_MESH_P006_v1_7.json',{}) or {}
    ccxin=load(r/'reports/medtas/calculix/current/K01_CALCULIX_INPUT_P006_v1_7.json',{}) or {}
    ccxrun=load(r/'reports/medtas/calculix/current/K01_CALCULIX_RUN_P006_v1_7.json',{}) or {}
    drawart=load(r/'reports/medtas/drawing/current/K01_DRAWING_ARTIFACT_GATE04E_v1_7.json',{}) or {};drawverify=load(r/'reports/medtas/drawing/current/K01_DRAWING_VERIFY_GATE04E_v1_7.json',{}) or {}
    ccx=load(r/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json',{}) or {};tool=load(r/'reports/medtas/calculix/current/K01_ANALYSIS_TOOLCHAIN_DISCOVERY_CURRENT.json',{}) or {};pipe=load(r/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json',{}) or {};ps=load(r/'reports/control/K01_PROJECT_STRUCTURE_CURRENT.json',{}) or {}
    req=state.get('requirements') or {};gates=state.get('gates') or {};counts={}
    for _,x in nodes.items():counts[x.get('state','MISSING')]=counts.get(x.get('state','MISSING'),0)+1
    frontier=[]
    for nid,x in nodes.items():
        if x.get('state') in ('MISSING','FRESH_UNVERIFIED','HOLD','BLOCKED','STALE','DRIFT'):
            frontier.append({'node_id':nid,'title':x.get('title'),'state':x.get('state'),'reasons':x.get('reasons',[])})
    payload={'schema':'k01.project_view.current.v1_7','project':'K01','interface_parameters':interface,
      'build_summary':{'node_count':len(nodes),'counts':counts,'frontier':frontier},
      'product_state':{'requirements':{'total':req.get('total',0),'released':req.get('released',0),'blockers':req.get('blockers',0)},'gates':{'total':gates.get('total',0),'blockers':gates.get('blockers',0)},'current_action':state.get('current_action')},
      'mbd':{'coverage_status':mbd.get('coverage_status'),'summary':mbd.get('summary',{}),'candidate_summary':candidates.get('summary',{}),'authoring_plan_status':mbdplan.get('status'),'blocking_characteristics':mbdplan.get('blocking_characteristics',[])},
      'drawings':{'generation_gate':drawplan.get('verdict') or drawing.get('generation_gate'),'blocking_items':drawplan.get('blocking_items',[]),'missing_characteristics':drawing.get('missing_characteristics',[]),'required_characteristics':drawing.get('required_characteristics',[]),'artifact':drawart,'verification':drawverify},
      'bom':{'item_count':bom.get('item_count',len(bom.get('items',[]) or [])),'limitations':bom.get('limitations',[]),'verify_verdict':bomv.get('verdict'),'verify_issues':bomv.get('issues',[])},
      'structural':{'model':struct,'face_map_status':fm.get('status'),'face_map_limitations':fm.get('limitations',[]),'face_qualification':fq,'bolt_equivalence':bolt,'neutral_geometry':neutral,'mesh':mesh,'ccx_input':ccxin,'ccx_run':ccxrun,'calculix':ccx,'toolchain':tool},
      'project_structure':ps,'pipeline':{'overall_status':pipe.get('overall_status'),'stages':pipe.get('stages',[])}}
    out=r/'reports/control/K01_PROJECT_VIEW_CURRENT.json';dump(out,payload);print('Project view:',out);return 0
if __name__=='__main__':raise SystemExit(main())
