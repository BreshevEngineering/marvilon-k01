from __future__ import annotations
import argparse,json
from pathlib import Path
from medtas_v16_common import load,dump

def safe(p,d=None):
    try:return load(p)
    except Exception:return d

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    drawing=safe(root/'reports/medtas/drawing/current/K01_DRAWING_MODEL_GATE04E_v1.json',{}) or {}
    mbd=safe(root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',{}) or {}
    tolmap=safe(root/'control/medtas/v1/bindings/K01_TOLERANCE_MBD_MAP_v1.json',{}) or {}
    candidates=safe(root/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_6.json',{}) or {}
    cidx={r.get('characteristic_id'):r for r in candidates.get('rows',[]) or []}
    required=[]
    for chain,s in (tolmap.get('chains') or {}).items():
        for c in s.get('contributors',[]) or []:
            required.append({'chain_id':chain,'part_no':c.get('part_no'),'characteristic_id':c.get('characteristic_id'),'role':c.get('role'),'mapping':'DimXpert/MBD'})
        dc=s.get('direct_characteristic')
        if dc:required.append({'chain_id':chain,'part_no':'A001','characteristic_id':dc.get('characteristic_id'),'role':dc.get('role'),'mapping':'assembly MBD / controlled semantic feature'})
    existing=set()
    for d in mbd.get('documents',[]) or []:
        for x in d.get('annotations',[]) or []:
            if x.get('name'):existing.add(str(x['name']))
    for r in required:
        cid=r['characteristic_id'];r['present_in_current_mbd']=cid in existing
        if cid in cidx:r['native_dimension_candidate']=cidx[cid]
    missing=[r['characteristic_id'] for r in required if not r['present_in_current_mbd']]
    payload={'schema':'k01.drawing_mbd_release_workpack.v1_6','principle':'Drawing is a derived release presentation of native CAD + MBD/DimXpert. AutoDimension is prohibited. Missing model definition remains OPEN; drawing generation must not introduce an independent tolerance.','definition_authority':'native SOLIDWORKS CAD + reviewed MBD/DimXpert','drawing_model_status':'AVAILABLE' if drawing else 'MISSING','mbd_coverage_status':mbd.get('coverage_status','MISSING'),'required_characteristics':required,'missing_characteristics':missing,'native_artifact_status':'NOT_GENERATED','generation_gate':'READY_FOR_DRAWING_ARTIFACT' if not missing else 'BLOCKED_MBD_DEFINITION','next_action':'Review/author missing MBD characteristics, then generate controlled SLDDRW/PDF and verify semantic + visual parity.'}
    out=root/'reports/medtas/drawing/current/K01_DRAWING_MBD_RELEASE_WORKPACK_v1_6.json';dump(out,payload);print('Drawing MBD workpack:',out);print('generation_gate=',payload['generation_gate'],'missing=',len(missing));return 0
if __name__=='__main__':raise SystemExit(main())
