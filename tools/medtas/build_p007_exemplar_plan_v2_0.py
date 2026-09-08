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
    spec=load(r/'control/drawings/K01-D-006_P007_EXEMPLAR_v1_9.json',{}) or {};bindings=load(r/'control/drawings/K01-D-006_MBD_BINDINGS_v1_9.json',{}) or {};mbd=load(r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',{}) or {};parts=load(r/'control/product/parts.json',{}) or {};drawbind=load(r/'control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json',{}) or {};geom=load(r/'reports/drawing/current/K01-D-006_P007_LIVE_GEOMETRY_CURRENT.json',{}) or {}
    doc=find_doc(mbd,'K01-P-007');ann_names={str(x.get('name')) for x in doc.get('annotations',[]) or [] if x.get('name')};bmap=bindings.get('bindings',{}) or {};rows=[];block=[]
    live_recon={x.get('characteristic_id'):x for x in geom.get('legacy_draft_reconciliation',[]) or []}
    for c in spec.get('characteristics',[]) or []:
        cid=c.get('id');binding=bmap.get(cid);present=bool(binding and binding in ann_names);status=c.get('status');lr=live_recon.get(cid,{})
        if c.get('mbd_required'):
            state='DEFINED_IN_MBD' if present else 'LIVE_CAD_CONFLICT_REVIEW' if lr.get('status')=='CONFLICT' else 'MBD_BINDING_NOT_VERIFIED' if binding else 'MBD_AUTHORING_REQUIRED'
            if state!='DEFINED_IN_MBD':block.append(cid)
        else:
            state=status
            if status in ('OPEN_SPEC','OPEN_REQUIREMENT'):block.append(cid)
        rows.append({**c,'mbd_binding':binding,'mbd_present':present,'current_state':state,'live_geometry_reconciliation':lr or None,'balloon_id':cid,'inspection_method':'OPEN','inspection_result':'','inspection_status':'NOT_INSPECTED'})
    template=drawbind.get('template_path');template_ok=bool(template and Path(str(template)).exists())
    if not template_ok:block.append('DRAWING-TEMPLATE-BINDING')
    pmeta=(parts.get('items') or {}).get('K01-P-007',{})
    if not pmeta:block.append('PARTS-REGISTRY-P007')
    status='READY_FOR_EXEMPLAR_DRAWING' if not block else 'HOLD'
    decisions=[]
    if any(x.startswith('P007-LEGACY-DRAFT-CONFLICT:C02') for x in geom.get('issues',[]) or []):
        decisions.append({'id':'P007-DRAWING-DRIFT-C02','status':'REVIEW_REQUIRED','finding':'Live CAD locator is Ø14.10 × 2.00 mm while the legacy draft candidate says Ø14.10 H7 × 1.70.','recommended_action':'Protect the verified frozen CAD geometry and supersede the 1.70-mm legacy draft candidate unless contrary functional evidence is produced. Do not resize P007 merely to make the draft match.'})
    payload={'schema':'k01.drawing_p007_exemplar_plan.current.v2_0','drawing_no':'K01-D-006','part_number':'K01-P-007','status':status,'template_path':template,'template_ready':template_ok,'part_registry':pmeta,'live_geometry_status':geom.get('status'),'live_geometry':geom.get('live_geometry',{}),'engineering_decisions':decisions,'characteristics':rows,'blocking_items':sorted(set(block)),'next_actions':[
      'Resolve P007-DRAWING-DRIFT-C02 first: current verified CAD is 2.00 mm locator length; legacy 1.70-mm draft is not authority.',
      'Author/verify C01-C08 and C11 in K01-P-007 native PMI/DimXpert. Do not type duplicate tolerances in the drawing.',
      'Release a draft P007 weld/containment process definition (C10).',
      'Link C12 to a quantitative leak/containment acceptance requirement when released.',
      'Generate one native K01-D-006 exemplar from the controlled ISO template; obtain manufacturer feedback before batch drawing generation.'
    ],'policy':'P007 is the first exemplar. Live canonical CAD is the nominal-geometry authority; legacy drawing values are candidates only. Dimensional/GD&T tolerances are released from native model PMI/MBD.'}
    out=r/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json';dump(out,payload)
    ins=r/'reports/inspection/current/K01-D-006_P007_CHARACTERISTICS_CURRENT.csv';ins.parent.mkdir(parents=True,exist_ok=True)
    fields=['balloon_id','role','candidate_spec','current_state','mbd_binding','inspection_method','inspection_result','inspection_status']
    with ins.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    md=r/'reports/drawing/current/K01-D-006_P007_MBD_AUTHORING_CHECKLIST.md';lines=['# K01-D-006 / K01-P-007 — MBD authoring checklist','','**Rule:** live CAD owns nominal geometry. Tolerance/GD&T content must be authored in native PMI/MBD before drawing release. Legacy draft values are comparison candidates only.','']
    if decisions:
        lines+=['## Engineering drift requiring resolution']+[f"- **{x['id']}** — {x['finding']} **Recommended:** {x['recommended_action']}" for x in decisions]+['']
    for x in rows:lines.append(f"- **{x['id']} — {x['role']}**: `{x.get('candidate_spec') or 'OPEN'}` → **{x['current_state']}**")
    lines+=['','## Current blockers']+[f'- {x}' for x in sorted(set(block))]
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    try:register_build(r,'K01.DRAWING.P007.EXEMPLAR.PLAN',{'tool':'build_p007_exemplar_plan_v2_0.py','live_geometry_authority':True});register_verify(r,'K01.DRAWING.P007.EXEMPLAR.PLAN','PASS' if status=='READY_FOR_EXEMPLAR_DRAWING' else 'HOLD',metrics={'characteristics':len(rows),'blocking_items':len(set(block)),'live_geometry_conflicts':len(decisions)},limitations=sorted(set(block)))
    except Exception as e:print('WARN P007 record registration:',e)
    print('P007 exemplar plan:',out,'status=',status,'blockers=',len(set(block)),'live conflicts=',len(decisions));print('Inspection characteristic template:',ins);print('MBD checklist:',md);return 0
if __name__=='__main__':raise SystemExit(main())
