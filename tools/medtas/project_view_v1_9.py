from __future__ import annotations
import argparse,json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from v22_common import authority_path

def load(p,d=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return d

def dump(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();derived=load(r/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',{}) or {};nodes=derived.get('nodes',{});gp=authority_path(r,'engineering_build_graph'); graph=load(gp,{}) if gp else {};criticality={n.get('node_id'):(n.get('lifecycle') or {}).get('criticality') for n in graph.get('nodes',[]) or []};state=load(r/'reports/control/K01_CURRENT_STATE.json',{}) or load(r/'control/state/K01_CURRENT_STATE.json',{}) or {};priority=load(r/'reports/control/K01_RELEASE_PRIORITY_CURRENT.json',{}) or {};counts={};frontier=[]
    deferred_prefixes=('K01.STRUCT.FACE_MAP','K01.STRUCT.BOLT_EQUIV','K01.STRUCT.NEUTRAL','K01.STRUCT.MESH','K01.STRUCT.CCX','K01.STRUCT.RECON')
    for nid,x in nodes.items():
        st=x.get('state','MISSING');counts[st]=counts.get(st,0)+1
        if st in ('MISSING','FRESH_UNVERIFIED','HOLD','BLOCKED','STALE','DRIFT') and not nid.startswith(deferred_prefixes):frontier.append({'node_id':nid,'title':x.get('title'),'state':st,'reasons':x.get('reasons',[])})
    payload={
      'schema':'k01.project_view.current.v1_9','project':'K01','release_priority':priority,'build_summary':{'node_count':len(nodes),'counts':counts,'frontier':frontier},
      'product_state':{'requirements':state.get('requirements',{}),'gates':state.get('gates',{}),'current_action':state.get('current_action')},
      'parts_registry':load(r/'control/product/parts.json',{}) or {},
      'product_definition':load(r/'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json',{}) or {},
      'mbd':load(r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',{}) or {},
      'mbd_candidates':load(r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_7.json',{}) or {},
      'mbd_plan':load(r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_PLAN_v1_7.json',{}) or {},
      'drawings':{'system':load(r/'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json',{}) or {},'registry':load(r/'control/drawings/K01_DRAWING_REGISTRY_CURRENT.json',{}) or {},'control':load(r/'reports/control/K01_DRAWING_CONTROL_CURRENT.json',{}) or {},'plan':load(r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json',{}) or {},'p007_exemplar':load(r/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json',{}) or {},'artifact':load(r/'reports/medtas/drawing/current/K01_DRAWING_ARTIFACT_GATE04E_v1_8.json',{}) or {},'verification':load(r/'reports/medtas/drawing/current/K01_DRAWING_VERIFY_GATE04E_v1.json',{}) or {}},
      'bom':{'ebom_model':load(r/'reports/medtas/bom/current/K01_EBOM_MODEL_A001_v1_9.json',{}) or {},'ebom_verify':load(r/'reports/medtas/bom/current/K01_EBOM_VERIFY_A001_v1_9.json',{}) or {},'mbom_model':load(r/'reports/medtas/bom/current/K01_MBOM_MODEL_A001_v1_9.json',{}) or {},'mbom_verify':load(r/'reports/medtas/bom/current/K01_MBOM_VERIFY_A001_v1_9.json',{}) or {},'property_projection':load(r/'reports/bom/current/K01_PARTS_PROPERTY_PROJECTION_CURRENT.json',{}) or {}},
      'structural':{'model':load(r/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json',{}) or {},'current_role':'DEFERRED_ASSURANCE','neutral_geometry':load(r/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_7.json',{}) or {},'calculix':load(r/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json',{}) or {}},
      'project_structure':load(r/'reports/control/K01_PROJECT_STRUCTURE_CURRENT.json',{}) or {},'pipeline':load(r/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json',{}) or {}
    };out=r/'reports/control/K01_PROJECT_VIEW_CURRENT.json';dump(out,payload);print('Project view:',out);return 0
if __name__=='__main__':raise SystemExit(main())
