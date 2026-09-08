from __future__ import annotations
import argparse
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

ACCEPTED={'DEFINED_IN_MBD','VERIFIED_NATIVE_DATUM','VERIFIED_NATIVE_DIMENSION','VERIFIED_NATIVE_GEOMETRY','CONTROLLED_PARAMETER_VERIFIED','DERIVED_NON_DIMENSIONAL'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    pdp=r/'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json';out=r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json'
    pd=load(pdp) if pdp.exists() else {'drawings':[],'blocking_characteristics':['PRODUCT-DEFINITION-MISSING']}
    bind=load(r/'control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json',{}) or {}
    template=bind.get('template_path');global_blockers=[]
    if not template:global_blockers.append('DRAWING-TEMPLATE-BINDING')
    rows=[];pack_blockers=list(global_blockers);ready=[]
    for d in pd.get('drawings',[]) or []:
        dr={'drawing_no':d.get('drawing_no'),'model':d.get('model'),'title':d.get('title'),'characteristics':[],'blocking_items':[]}
        for c in d.get('characteristics',[]) or []:
            x={'id':c.get('id'),'role':c.get('role'),'authority':c.get('authority'),'definition_state':c.get('definition_state'),'source':c.get('source'),'evidence':c.get('evidence',{}),'tolerance_release_state':c.get('tolerance_release_state')}
            x['release_state']='READY_FROM_PRODUCT_DEFINITION' if c.get('definition_state') in ACCEPTED else c.get('definition_state','MISSING')
            if x['release_state']!='READY_FROM_PRODUCT_DEFINITION':dr['blocking_items'].append(c.get('id'))
            dr['characteristics'].append(x)
        if not template:dr['blocking_items'].append('DRAWING-TEMPLATE-BINDING')
        dr['status']='READY_FOR_NATIVE_GENERATION' if not dr['blocking_items'] else 'BLOCKED_PRODUCT_DEFINITION'
        if dr['status']=='READY_FOR_NATIVE_GENERATION':ready.append(dr['drawing_no'])
        else:pack_blockers.extend(dr['blocking_items'])
        rows.append(dr)
    verdict='PASS' if rows and all(d['status']=='READY_FOR_NATIVE_GENERATION' for d in rows) else 'PASS_WITH_LIMITATIONS' if ready else 'HOLD'
    payload={'schema':'k01.drawing_release_plan.gate04e.v1_8','verdict':verdict,'drawings':rows,'generation_binding':bind,'ready_drawings':ready,'blocking_items':sorted(set(pack_blockers)),'native_artifact_status':'READY_PARTIAL' if ready and verdict!='PASS' else 'READY' if verdict=='PASS' else 'NOT_GENERATED','policy':'Drawing generation is per drawing. Each characteristic must be resolved in canonical Product Definition; native MBD is preferred but reviewed native semantic bindings are accepted transitional authority. OPEN tolerance/process/datum specs remain blockers. AutoDimension prohibited.'}
    dump(out,payload);register_build(r,'K01.DRAWING.RELEASE.PLAN.GATE04E',{'tool':'build_drawing_release_plan_v1_8.py'});register_verify(r,'K01.DRAWING.RELEASE.PLAN.GATE04E',verdict,metrics={'drawings':len(rows),'ready_drawings':len(ready),'blocking_items':len(set(pack_blockers))},limitations=[] if verdict=='PASS' else sorted(set(pack_blockers)))
    print('Drawing release plan:',out,'verdict=',verdict,'ready=',ready,'blockers=',len(set(pack_blockers)));return 0
if __name__=='__main__':raise SystemExit(main())
