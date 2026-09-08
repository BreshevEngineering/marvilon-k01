from __future__ import annotations
import argparse
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify,base_id

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();reg=load(r/'control/drawings/K01_DRAWING_CHARACTERISTICS_v1_7.json');mbd=load(r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json') if (r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json').exists() else {'documents':[]};bind=load(r/'control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json');cad=load(r/'reports/medtas/cad/current/K01_CAD_SEM_A001.json') if (r/'reports/medtas/cad/current/K01_CAD_SEM_A001.json').exists() else {'documents':[]}
    ann={(base_id(d.get('document_id')),str(a.get('name'))):a for d in mbd.get('documents',[]) for a in d.get('annotations',[])};docs={base_id(d.get('document_id')):d for d in cad.get('documents',[])};rows=[];blockers=[]
    for d in reg['drawings']:
        dr={'drawing_no':d['drawing_no'],'model':d['model'],'title':d['title'],'model_present':base_id(d['model']) in docs or d['model']=='K01-A-001','characteristics':[]}
        for c in d['characteristics']:
            x=dict(c);key=(base_id(d['model']),c['id']);present=key in ann;x['mbd_present']=present
            if present:x['release_state']='DEFINED_IN_MBD'
            elif c['status']=='DEFINED_IN_CONTROL' and c['authority'] in ('material_state','canonical_bom'):x['release_state']='DERIVED_NON_DIMENSIONAL'
            elif c['status']=='OPEN_SPEC':x['release_state']='OPEN_SPEC';blockers.append(c['id'])
            else:x['release_state']='MBD_BIND_REQUIRED';blockers.append(c['id'])
            dr['characteristics'].append(x)
        dr['status']='READY_FOR_NATIVE_GENERATION' if dr['model_present'] and all(x['release_state'] in ('DEFINED_IN_MBD','DERIVED_NON_DIMENSIONAL') for x in dr['characteristics']) else 'BLOCKED_MBD_DEFINITION';rows.append(dr)
    if not bind.get('template_path'):blockers.append('DRAWING-TEMPLATE-BINDING')
    verdict='PASS' if not blockers else 'HOLD';payload={'schema':'k01.drawing_release_plan.gate04e.v1_7','verdict':verdict,'drawings':rows,'generation_binding':bind,'blocking_items':sorted(set(blockers)),'native_artifact_status':'NOT_GENERATED' if blockers else 'READY','policy':'No released SLDDRW/PDF is generated while a required MBD/spec characteristic or template binding is open. Drawing never invents a tolerance.'};out=r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json';dump(out,payload);register_build(r,'K01.DRAWING.RELEASE.PLAN.GATE04E',{'tool':'build_drawing_release_plan_v1_7.py'});register_verify(r,'K01.DRAWING.RELEASE.PLAN.GATE04E',verdict,metrics={'drawings':len(rows),'blocking_items':len(set(blockers))},limitations=[] if verdict=='PASS' else sorted(set(blockers)));print('Drawing release plan:',out,'verdict=',verdict,'blockers=',len(set(blockers)));return 0
if __name__=='__main__':raise SystemExit(main())
