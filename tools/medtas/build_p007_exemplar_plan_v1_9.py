from __future__ import annotations
import argparse,csv
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def find_doc(mbd,pid):
    for d in mbd.get('documents',[]) or []:
        if pid in str(d.get('document_id','')):return d
    return {}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    spec=load(r/'control/drawings/K01-D-006_P007_EXEMPLAR_v1_9.json',{}) or {};bindings=load(r/'control/drawings/K01-D-006_MBD_BINDINGS_v1_9.json',{}) or {};mbd=load(r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',{}) or {};parts=load(r/'control/product/parts.json',{}) or {};drawbind=load(r/'control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json',{}) or {}
    doc=find_doc(mbd,'K01-P-007');ann_names={str(x.get('name')) for x in doc.get('annotations',[]) or [] if x.get('name')};bmap=bindings.get('bindings',{}) or {};rows=[];block=[]
    for c in spec.get('characteristics',[]) or []:
        cid=c.get('id');binding=bmap.get(cid);present=bool(binding and binding in ann_names);status=c.get('status')
        if c.get('mbd_required'):
            state='DEFINED_IN_MBD' if present else 'MBD_BINDING_NOT_VERIFIED' if binding else 'MBD_AUTHORING_REQUIRED'
            if state!='DEFINED_IN_MBD':block.append(cid)
        else:
            state=status
            if status in ('OPEN_SPEC','OPEN_REQUIREMENT'):block.append(cid)
        rows.append({**c,'mbd_binding':binding,'mbd_present':present,'current_state':state,'balloon_id':cid,'inspection_method':'OPEN','inspection_result':'','inspection_status':'NOT_INSPECTED'})
    template=drawbind.get('template_path');template_ok=bool(template and Path(str(template)).exists())
    if not template_ok:block.append('DRAWING-TEMPLATE-BINDING')
    pmeta=(parts.get('items') or {}).get('K01-P-007',{})
    if not pmeta:block.append('PARTS-REGISTRY-P007')
    status='READY_FOR_EXEMPLAR_DRAWING' if not block else 'HOLD'
    payload={'schema':'k01.drawing_p007_exemplar_plan.current.v1_9','drawing_no':'K01-D-006','part_number':'K01-P-007','status':status,'template_path':template,'template_ready':template_ok,'part_registry':pmeta,'characteristics':rows,'blocking_items':sorted(set(block)),'next_actions':[
      'Author/verify C01-C08 and C11 in K01-P-007 native PMI/DimXpert. Do not type duplicate tolerances in the drawing.',
      'Release a draft P007 weld/containment process definition (C10).',
      'Link C12 to a quantitative leak/containment acceptance requirement when released.',
      'Generate one native K01-D-006 exemplar from the controlled template; obtain manufacturer feedback before batch drawing generation.'
    ],'policy':'P007 is the first exemplar because it combines thin wall, weld/containment, locating GD&T and hermetic inspection. Draft source values are migration candidates, not released truth.'}
    out=r/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json';dump(out,payload)
    ins=r/'reports/inspection/current/K01-D-006_P007_CHARACTERISTICS_CURRENT.csv';ins.parent.mkdir(parents=True,exist_ok=True)
    fields=['balloon_id','role','candidate_spec','current_state','mbd_binding','inspection_method','inspection_result','inspection_status']
    with ins.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    md=r/'reports/drawing/current/K01-D-006_P007_MBD_AUTHORING_CHECKLIST.md';lines=['# K01-D-006 / K01-P-007 — MBD authoring checklist','','**Rule:** dimensional/GD&T tolerance content is released from native model PMI. The drawing must not carry an independently typed duplicate tolerance.','']
    for x in rows:lines.append(f"- **{x['id']} — {x['role']}**: `{x.get('candidate_spec') or 'OPEN'}` → **{x['current_state']}**")
    lines+=['','## Current blockers']+[f'- {x}' for x in sorted(set(block))]
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    register_build(r,'K01.DRAWING.P007.EXEMPLAR.PLAN',{'tool':'build_p007_exemplar_plan_v1_9.py'});register_verify(r,'K01.DRAWING.P007.EXEMPLAR.PLAN','PASS' if status=='READY_FOR_EXEMPLAR_DRAWING' else 'HOLD',metrics={'characteristics':len(rows),'blocking_items':len(set(block))},limitations=sorted(set(block)));print('P007 exemplar plan:',out,'status=',status,'blockers=',len(set(block)));print('Inspection characteristic template:',ins);print('MBD checklist:',md);return 0
if __name__=='__main__':raise SystemExit(main())
