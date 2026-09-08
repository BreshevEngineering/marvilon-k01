from __future__ import annotations
import argparse
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

DIMENSIONAL_AUTHORITIES=('native_datum','native_geometry','interface_parameter','tolerance_chain','functional_datum_scheme','assembly_hard_stops')
NON_DIMENSIONAL_AUTHORITIES={'material_state','canonical_bom','process_definition','service_requirement'}

def needs_mbd(c):
    a=str(c.get('authority') or '')
    return any(k in a for k in DIMENSIONAL_AUTHORITIES)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();p=r/'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json'
    if not p.exists():print('HOLD: product definition v1.8 output missing');return 2
    d=load(p);block=[];strict_ready=0;total=0
    for dr in d.get('drawings',[]) or []:
        for c in dr.get('characteristics',[]) or []:
            total+=1;mbd_req=needs_mbd(c);c['drawing_mbd_required']=mbd_req
            if mbd_req:
                c['drawing_release_authority']='READY' if c.get('definition_state')=='DEFINED_IN_MBD' else 'MBD_REQUIRED_FOR_DRAWING'
            else:
                ds=str(c.get('definition_state') or '')
                c['drawing_release_authority']='READY' if ds in ('DEFINED_IN_MBD','DERIVED_NON_DIMENSIONAL','CONTROLLED_PARAMETER_VERIFIED') else ds or 'MISSING'
            if c['drawing_release_authority']=='READY':strict_ready+=1
            else:block.append(c.get('id'))
    d['schema']='k01.product_definition.gate04e.v1_9';d['drawing_release_policy']='Dimensional/GD&T/datum tolerances must be native model PMI/MBD before release drawing generation. Verified native nominal geometry may support engineering analysis but cannot authorize a duplicate hand-typed drawing tolerance.';d['drawing_release_summary']={'characteristics':total,'strict_ready':strict_ready,'blocking':len(set(block))};d['drawing_release_blockers']=sorted(set(block))
    dump(p,d);register_build(r,'K01.PRODUCT.DEFINITION.GATE04E',{'tool':'build_product_definition_v1_8.py + harden_product_definition_v1_9.py'});register_verify(r,'K01.PRODUCT.DEFINITION.GATE04E','PASS_WITH_LIMITATIONS' if block else 'PASS',metrics=d['drawing_release_summary'],limitations=['DRAWING-MBD-REQUIRED:'+x for x in sorted(set(block))]);print('Product definition hardened for drawing release:',d['drawing_release_summary']);return 0
if __name__=='__main__':raise SystemExit(main())
