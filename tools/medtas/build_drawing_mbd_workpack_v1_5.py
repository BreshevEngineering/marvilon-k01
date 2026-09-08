from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p,d=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return d
def dump(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    drawing=load(root/'reports/medtas/drawing/current/K01_DRAWING_MODEL_GATE04E_v1.json',{}) or {}
    mbd=load(root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',{}) or {}
    tolmap=load(root/'control/medtas/v1/bindings/K01_TOLERANCE_MBD_MAP_v1.json',{}) or {}
    required=[]
    for chain,s in (tolmap.get('chains') or {}).items():
        for c in s.get('contributors',[]) or []:required.append({'chain_id':chain,'part_no':c.get('part_no'),'characteristic_id':c.get('characteristic_id'),'role':c.get('role'),'mapping':'DimXpert/MBD'})
        dc=s.get('direct_characteristic')
        if dc:required.append({'chain_id':chain,'part_no':'A001','characteristic_id':dc.get('characteristic_id'),'role':dc.get('role'),'mapping':'assembly MBD/controlled semantic feature'})
    existing=set()
    for d in mbd.get('documents',[]) or []:
        for x in d.get('annotations',[]) or []:existing.add(str(x.get('name') or ''))
    for r in required:r['present_in_current_mbd']=r['characteristic_id'] in existing
    payload={'schema':'k01.drawing_mbd_release_workpack.v1_5','principle':'Drawing is a derived representation of native CAD + MBD/DimXpert. AutoDimension is prohibited. Missing product definition remains OPEN; drawing generation must not invent tolerances.','definition_authority':'native CAD + MBD/DimXpert','drawing_model_status':'AVAILABLE' if drawing else 'MISSING','mbd_coverage_status':mbd.get('coverage_status','MISSING'),'required_characteristics':required,'missing_characteristics':[r['characteristic_id'] for r in required if not r['present_in_current_mbd']],'native_artifact_status':'NOT_GENERATED','next_action':'Author/confirm missing characteristics in native model, then generate SLDDRW/PDF from this workpack and verify visual + semantic parity.'}
    out=root/'reports/medtas/drawing/current/K01_DRAWING_MBD_RELEASE_WORKPACK_v1_5.json';dump(out,payload);print('Drawing MBD workpack:',out);print('missing characteristics=',len(payload['missing_characteristics']));return 0
if __name__=='__main__':raise SystemExit(main())
