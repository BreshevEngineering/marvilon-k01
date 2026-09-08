from __future__ import annotations
import argparse,csv
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    ex=load(r/'control/drawings/K01-D-006_P007_EXEMPLAR_v1_9.json',{}) or {};req=load(r/'control/requirements/requirements.json',{}) or {};reqs={x['id']:x for x in req.get('requirements',[]) or []}
    rows=[]
    for c in ex.get('characteristics',[]) or []:
        cid=f"K01-D006-{c.get('id')}";source='MBD_REQUIRED' if c.get('mbd_required') else 'CONTROLLED_NON_DIMENSIONAL'
        reqids=[]
        if c.get('id')=='C12':reqids=['REQ-K01-LEAK-001']
        if c.get('id')=='C09':reqids=['REQ-K01-MAT-P007-001']
        rows.append({'characteristic_id':cid,'balloon':c.get('id'),'drawing_no':'K01-D-006','part_number':'K01-P-007','role':c.get('role'),'type':c.get('type'),'definition_source':source,'definition_status':c.get('status'),'candidate_spec':c.get('candidate_spec'),'requirement_ids':reqids,'acceptance_released':False if c.get('status') not in ('CONTROLLED_PRODUCT_DATA',) else True,'inspection_method':'OPEN' if c.get('id') not in ('C09',) else 'material_certificate_and_registry_reconciliation'})
    payload={'schema':'k01.release_characteristics.registry.v1_9','policy':load(r/'control/inspection/K01_CHARACTERISTIC_POLICY_v1_9.json',{}) or {},'characteristics':rows,'summary':{'count':len(rows),'acceptance_released':sum(bool(x['acceptance_released']) for x in rows),'open_acceptance':sum(not bool(x['acceptance_released']) for x in rows)},'note':'candidate_spec is not release authority. Dimensional/GD&T acceptance becomes released only after current model PMI/MBD readback confirms it.'}
    out=r/'reports/inspection/current/K01_RELEASE_CHARACTERISTICS_CURRENT.json';dump(out,payload)
    csvp=r/'reports/inspection/current/K01_AS9102_STYLE_CHARACTERISTICS_CURRENT.csv';csvp.parent.mkdir(parents=True,exist_ok=True)
    fields=['characteristic_id','balloon','drawing_no','part_number','role','type','definition_source','definition_status','acceptance_released','inspection_method']
    with csvp.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:x.get(k) for k in fields} for x in rows)
    register_build(r,'K01.CHARACTERISTICS.REGISTRY',{'tool':'build_inspection_characteristics_v1_9.py'});register_verify(r,'K01.CHARACTERISTICS.REGISTRY','PASS' if payload['summary']['open_acceptance']==0 else 'PASS_WITH_LIMITATIONS',metrics=payload['summary'],limitations=[] if payload['summary']['open_acceptance']==0 else ['Some release characteristics do not yet have structured released acceptance']);print('Inspection characteristics:',len(rows),'open acceptance=',payload['summary']['open_acceptance']);print('JSON:',out);print('CSV:',csvp);return 0
if __name__=='__main__':raise SystemExit(main())
