from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone


def load(p: Path): return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def find_char(rows, cid):
    for r in rows:
        if r.get('id') == cid: return r
    raise RuntimeError(f'missing characteristic {cid}')

def update_pds_source(path: Path):
    txt=path.read_text(encoding='utf-8')
    old='["C07/C08/C11 radial stack + C01/C05/C06/blind-end tolerance closure","thin-wall/blind-end manufacturing capability","seal/media/leak definition","fastener/process qualification","inspection plan"]'
    new='["C01/C05/C06/blind-end tolerance closure","thin-wall/blind-end manufacturing capability","seal/media/leak definition","fastener/process qualification","inspection plan"]'
    if old in txt: txt=txt.replace(old,new,1)
    old='["Close C07/C08/C11 coupled radial stack and remaining C01/C05/C06/blind-end tolerances","Qualify 0.30 mm wall / integral blind-end manufacturing and inspection capability",'
    new='["Close C01/C05/C06/blind-end tolerances via T05/process evidence","Qualify 0.30 mm nominal wall / integral blind-end manufacturing and inspection capability",'
    if old in txt: txt=txt.replace(old,new,1)
    old='{"priority":4,"lane":"VARIATION","task":"Close C07/C08/C11 coupled radial envelope and remaining functional tolerances",\n         "type":"ENGINEERING_DECISION_EXECUTABLE_NOW","upstream":["REQ-K01-J2-LOC-001 RELEASED","nominal J2 geometry frozen"]},'
    new='{"priority":4,"lane":"VARIATION","task":"Close C01/C05/C06/blind-end tolerances using T05 and current process evidence",\n         "type":"ENGINEERING_DECISION_EXECUTABLE_NOW","upstream":["EDR-029 C07/C08/C11 released","T07A PASS"]},'
    if old in txt: txt=txt.replace(old,new,1)
    path.write_text(txt,encoding='utf-8')

def strengthen_source_hygiene(path: Path):
    txt=path.read_text(encoding='utf-8')
    marker='K01-D006-WELD_ACTIVE_REGISTRY'
    if marker in txt: return
    anchor='    fam=load(root/"control/drawings/K01_P007_DRAWING_FAMILY_BINDING_CURRENT.json")\n'
    if anchor not in txt: raise RuntimeError('source_hygiene anchor not found')
    ins='''    drawreg=load(root/"control/drawings/K01_DRAWING_CHARACTERISTICS_v1_7.json")\n    d006=next((x for x in drawreg.get("drawings",[]) if x.get("drawing_no")=="K01-D-006"),{})\n    for ch in d006.get("characteristics",[]):\n        if ch.get("id")=="K01-D006-WELD": issues.append({"rule":"K01-D006-WELD_ACTIVE_REGISTRY","value":ch})\n    edr029=root/"control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json"\n    if edr029.is_file():\n        defs=load(root/"control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json")\n        for cid in ("C07","C08","C11"):\n            c=next((x for x in defs.get("characteristics",[]) if x.get("id")==cid),{})\n            if c.get("definition_state")!="CONTROLLED" or c.get("release_blocking") is not False:\n                issues.append({"rule":"EDR029_NOT_PROPAGATED_TO_ACTIVE_DEFINITION","characteristic":cid,"state":c.get("definition_state"),"release_blocking":c.get("release_blocking")})\n'''
    txt=txt.replace(anchor,ins+anchor,1)
    path.write_text(txt,encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',default='.'); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    for rel in [
        'control/decisions/EDR-025_P007_MONOLITHIC_REMOVABLE_J2_BASELINE.json',
        'control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json',
        'control/decisions/EDR-028_P007_C03_C04_RELEASE.json',
        'control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json']:
        if not (root/rel).is_file(): raise RuntimeError(f'MISSING authority: {rel}')

    # Product Definition: close the P007-side radial envelope without pretending counterpart parts are released.
    p=root/'control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json'; d=load(p); chars=d.get('characteristics',[])
    c=find_char(chars,'C07'); c.update({
        'definition_state':'CONTROLLED',
        'nominal_or_requirement':{'diameter_mm':10.0,'limits_mm':[9.964,10.0]},
        'variation_semantics':{'diameter_tolerance':'h9 (0/-0.036 mm at Ø10.00)','radial_envelope_relation':'C11 TOTAL RUNOUT 0.02 | B'},
        'authority_sources':['canonical native geometry','EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE','SRC-FIT-ISO286-2-001'],
        'cad_binding':'CANONICAL_REBIND_REQUIRED',
        'mbd_carrier':'DimXpert size Ø10 h9 + C11 total-runout control',
        'drawing_projection':'PROJECT Ø10 h9; apply C11 TOTAL RUNOUT 0.02 | B to thin-can OD',
        'inspection':'Low-force supported OD measurement/CMM plus total-runout verification to datum B; first-article capability confirmation',
        'release_blocking':False})
    c=find_char(chars,'C08'); c.update({
        'definition_state':'CONTROLLED',
        'nominal_or_requirement':{'id_mm':9.4,'limits_mm':[9.4,9.436],'radial_wall_nominal_mm':0.3,'size_only_wall_range_mm':[0.264,0.3]},
        'variation_semantics':{'id_tolerance':'H9 (0/+0.036 mm at Ø9.40)','wall':'0.30 REF derived from C07/C08 sizes; not independently toleranced','radial_envelope_relation':'C11 TOTAL RUNOUT 0.02 | B'},
        'authority_sources':['canonical native geometry','EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE','SRC-FIT-ISO286-2-001','EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE'],
        'cad_binding':'CANONICAL_REBIND_REQUIRED',
        'mbd_carrier':'DimXpert size Ø9.40 H9; wall 0.30 REF only',
        'drawing_projection':'PROJECT Ø9.40 H9; show 0.30 wall as REF only if useful; apply C11 TOTAL RUNOUT 0.02 | B to thin-can ID',
        'inspection':'Supported bore/CMM measurement plus total-runout verification to datum B; first-article thin-wall capability confirmation',
        'release_blocking':False})
    c=find_char(chars,'C11'); c.update({
        'definition_state':'CONTROLLED',
        'nominal_or_requirement':{'relationship':'thin-can OD and ID radial envelope to datum B axis','P007_side_allocation_mm':0.02},
        'variation_semantics':{'gdt':'TOTAL RUNOUT 0.02 | B on both thin-can OD and ID surfaces'},
        'authority_sources':['EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE','K01_P007_FUNCTIONAL_TOLERANCE_PLAN FT-04','EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE','SRC-GPS-ISO1101-001'],
        'cad_binding':'DERIVED_BINDING_READY_C07_C08_SURFACES_TO_DATUM_B_AXIS',
        'mbd_carrier':'DimXpert total-runout FCF on OD and ID surfaces to datum B',
        'drawing_projection':'PROJECT TOTAL RUNOUT 0.02 | B on thin-can OD and ID',
        'inspection':'CMM/qualified low-force rotary runout setup referenced to datum B; supported thin-wall condition; first-article capability confirmation',
        'release_blocking':False})
    dump(p,d)

    # Historical candidate registry becomes explicit current-reference semantics, not an OPEN authority source.
    p=root/'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json'; d=load(p)
    for r in d.get('characteristics',[]):
        if r.get('id')=='C07':
            r.update({'status':'CONTROLLED_BY_EDR_029','current_state':'CONTROLLED_RELEASE_DEFINITION','candidate_spec':'Ø10 h9 (9.964..10.000); TOTAL RUNOUT 0.02 | B','authority_class':'CURRENT_NATIVE_GEOMETRY_PLUS_EDR_029'})
        elif r.get('id')=='C08':
            r.update({'status':'CONTROLLED_BY_EDR_029','current_state':'CONTROLLED_RELEASE_DEFINITION','candidate_spec':'Ø9.40 H9 (9.400..9.436); wall 0.30 REF; TOTAL RUNOUT 0.02 | B','authority_class':'CURRENT_NATIVE_GEOMETRY_PLUS_EDR_029'})
        elif r.get('id')=='C11':
            r.update({'status':'CONTROLLED_BY_EDR_029','current_state':'CONTROLLED_RELEASE_DEFINITION','candidate_spec':'TOTAL RUNOUT 0.02 | B on thin-can OD and ID','authority_class':'EDR_029_CONTROLLED_REQUIREMENT'})
    dump(p,d)

    # Characteristic context and inspection carrier.
    p=root/'control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json'; d=load(p); ctx=d.get('characteristics',{})
    ctx['C07']['inspection_strategy']={'method':'SUPPORTED_LOW_FORCE_OD_OR_CMM_PLUS_RUNOUT','capability':'FIRST_ARTICLE_CONFIRMATION_REQUIRED'}
    ctx['C07']['drawing_authoring']['targets'][0].update({'authoring_class':'CONTROLLED_SIZE','action':'AUTHOR_RELEASE_SIZE_AFTER_BINDING_SIGNATURE','release_eligible':True})
    ctx['C08']['inspection_strategy']={'method':'SUPPORTED_BORE_OR_CMM_PLUS_RUNOUT','capability':'FIRST_ARTICLE_CONFIRMATION_REQUIRED'}
    for t in ctx['C08']['drawing_authoring']['targets']:
        if t.get('claim_id')=='C08.CAN_ID': t.update({'authoring_class':'CONTROLLED_SIZE','action':'AUTHOR_RELEASE_SIZE_AFTER_BINDING_SIGNATURE','release_eligible':True})
        elif t.get('claim_id')=='C08.WALL': t.update({'authoring_class':'DERIVED_REFERENCE_ONLY','action':'PROJECT_REFERENCE_WALL_ONLY__NO_INDEPENDENT_TOLERANCE','release_eligible':True})
    ctx['C11']['datum_reference_system']={'defines':[],'references':['B'],'controlled_feature':'thin-can OD and ID surfaces','system_id':'DRS-K01-J2-AB','status':'CONTROLLED_B_AXIS'}
    ctx['C11']['inspection_strategy']={'method':'CMM_OR_LOW_FORCE_TOTAL_RUNOUT_TO_B','capability':'FIRST_ARTICLE_CONFIRMATION_REQUIRED'}
    ctx['C11']['drawing_authoring']['targets'][0].update({'claim_id':'C11.TOTAL_RUNOUT','authoring_class':'CONTROLLED_GDT','action':'AUTHOR_TOTAL_RUNOUT_0P02_TO_B_AFTER_BINDING_SIGNATURE','release_eligible':True})
    dump(p,d)

    # Functional tolerance plan.
    p=root/'control/drawings/K01_P007_FUNCTIONAL_TOLERANCE_PLAN.json'; d=load(p)
    for ft in d.get('functional_chain',[]):
        if ft.get('id')=='FT-04':
            ft['method']='P007-side radial envelope: unilateral H9/h9 size limits preserve nominal clearances; TOTAL RUNOUT 0.02 to datum B allocates P007 alignment error. Counterpart P008/P015 production/alignment remain separate interface-release items.'
            ft['numeric_status']='CONTROLLED_P007_SIDE_EDR_029__COUNTERPART_INTERFACE_RELEASE_SEPARATE'
            ft['release_definition']={'C07':'Ø10 h9 = 9.964..10.000 mm','C08':'Ø9.40 H9 = 9.400..9.436 mm; wall 0.30 REF','C11':'TOTAL RUNOUT 0.02 | B on OD and ID'}
    dump(p,d)

    # Manufacturing route carries the requirement but capability evidence remains a real process gap.
    p=root/'control/manufacturing/K01_P007_MANUFACTURING_FEASIBILITY_CURRENT.json'; d=load(p)
    d['released_product_requirements_from_EDR_029']={'C07':'Ø10 h9','C08':'Ø9.40 H9; wall 0.30 REF','C11':'TOTAL RUNOUT 0.02 | B on OD and ID'}
    d['capability_boundary']='EDR-029 defines product requirements. Supplier/first-article proof that the selected monolithic route can repeatedly meet H9/h9 and 0.02 total runout remains open and is not silently converted to PASS.'
    dump(p,d)

    # Drawing intent. Do not author CAD yet.
    p=root/'control/drawings/spec/K01-D-006_P007_DRAWING_INTENT_v1.json'; d=load(p); rows=d.get('characteristics',[])
    for r in rows:
        if r.get('id')=='P007-C07': r.update({'spec':'Ø10 h9 (9.964..10.000)','source':'EDR-029','inspection':'supported low-force OD/CMM + total runout'})
        elif r.get('id')=='P007-C08': r.update({'spec':'Ø9.40 H9 (9.400..9.436); wall 0.30 REF','source':'EDR-029','inspection':'supported bore/CMM + total runout'})
    if not any(r.get('id')=='P007-C11' for r in rows):
        rows.append({'id':'P007-C11','feature':'thin-can OD and ID relative to locator datum B axis','type':'GD&T','spec':'TOTAL RUNOUT 0.02 | B on OD and ID','source':'EDR-029','view':'SECTION_AA','inspection':'CMM / low-force total-runout setup to datum B'})
    dump(p,d)

    # Active drawing registry: remove stale weld carrier and control thin-wall/runout semantics.
    p=root/'control/drawings/K01_DRAWING_CHARACTERISTICS_v1_7.json'; d=load(p)
    d006=next(x for x in d.get('drawings',[]) if x.get('drawing_no')=='K01-D-006')
    cleaned=[]
    for ch in d006.get('characteristics',[]):
        if ch.get('id')=='K01-D006-WELD': continue
        if ch.get('id')=='K01-D006-THIN-WALL': ch.update({'authority':'native_geometry+EDR-029','status':'CONTROLLED_DEFINITION_NEEDS_MBD_BIND'})
        if ch.get('id')=='K01-D006-CONCENTRICITY': ch.update({'role':'thin-can total runout to locator axis B','authority':'EDR-029','status':'CONTROLLED_DEFINITION_NEEDS_MBD_BIND'})
        cleaned.append(ch)
    if not any(ch.get('id')=='K01-D006-J2-PROCESS-ARCH' for ch in cleaned):
        cleaned.append({'id':'K01-D006-J2-PROCESS-ARCH','role':'removable J2 process architecture / no permanent P003-P007 weld','authority':'EDR-025','status':'CONTROLLED'})
    d006['characteristics']=cleaned; dump(p,d)

    # Drawing release source and authoring input: remove C07/C08/C11 definition gaps, preserve real blockers.
    p=root/'control/drawings/K01_D006_RELEASE_DEFINITION.json'; d=load(p)
    d['next_authoring_scope']=list(dict.fromkeys(d.get('next_authoring_scope',[])+['C07 released thin-can OD size','C08 released thin-can ID size / wall reference','C11 released total-runout semantics']))
    d['release_blockers']=[x for x in d.get('release_blockers',[]) if not ('C07/C08' in x or 'C11 ' in x)]
    for x in ['C01/C05/C06/blind-end remaining tolerance/form closure','thin-wall/blind-end manufacturing capability','C12 quantitative leak/containment acceptance','inspection/release measurement conditions']:
        if x not in d['release_blockers']: d['release_blockers'].append(x)
    leg=d.get('legacy_drawing_plan_entry',{})
    for ch in leg.get('characteristics',[]):
        if ch.get('id')=='K01-D006-THIN-WALL': ch.update({'authority':'EDR-029','definition_state':'CONTROLLED_REQUIREMENT','drawing_release_authority':'MBD_BIND_REQUIRED','source':'control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json'})
        elif ch.get('id')=='K01-D006-CONCENTRICITY': ch.update({'authority':'EDR-029','definition_state':'CONTROLLED_REQUIREMENT','drawing_release_authority':'MBD_BIND_REQUIRED','source':'control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json'})
    d['C07_C08_C11_radial_envelope']={'status':'CONTROLLED','decision':'EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE','C07':'Ø10 h9','C08':'Ø9.40 H9; wall 0.30 REF','C11':'TOTAL RUNOUT 0.02 | B on OD and ID','counterpart_boundary':'P008/P015 production/alignment remain separate interface release items'}
    dump(p,d)

    p=root/'control/drawings/K01_D006_AUTHORING_INPUT.json'; d=load(p)
    d['next_authoring_scope']=list(dict.fromkeys(d.get('next_authoring_scope',[])+['C07','C08','C11']))
    d['release_blockers']=[x for x in d.get('release_blockers',[]) if not ('C07/C08' in x or 'C11 ' in x)]
    for x in ['C01/C05/C06/blind-end remaining tolerance/form closure','thin-wall/blind-end manufacturing capability','C12 quantitative leak/containment acceptance','inspection/release measurement conditions']:
        if x not in d['release_blockers']: d['release_blockers'].append(x)
    d['radial_envelope_decision']='CONTROLLED_BY_EDR_029'; d['next_action']='Close C01/C05/C06/blind-end tolerance/form requirements and process/inspection gaps before full drawing authoring.'
    dump(p,d)

    # Workpack / release gaps.
    p=root/'control/workpacks/K01_P007_PRODUCT_DEFINITION_CLOSURE_v1.json'; d=load(p)
    d['status']='IN_PROGRESS__T07A_C03_C04_C07_C08_C11_CLOSED__LOCAL_FLANGE_PROCESS_ACTIVE'
    for r in d.get('technical_filter',[]):
        if r.get('id')=='C07': r.update({'candidate':'Ø10 nominal / tolerance OPEN','disposition':'ACCEPT_Ø10_h9_EDR_029','next':'Definition closed; route capability first article remains process evidence.'})
        elif r.get('id')=='C08': r.update({'candidate':'Ø9.40 / wall0.30 nominal / tolerance OPEN','disposition':'ACCEPT_Ø9P40_H9__WALL_0P30_REF_EDR_029','next':'Definition closed; thin-wall capability remains process evidence.'})
        elif r.get('id')=='C11': r.update({'candidate':'coaxiality/concentricity OPEN','disposition':'ACCEPT_TOTAL_RUNOUT_0P02_TO_B_EDR_029','next':'Definition closed; first-article capability and counterpart interface alignment remain separate.'})
    q=[x for x in d.get('immediate_execution_queue',[]) if 'C07/C08/C11' not in str(x.get('action',''))]
    q.insert(0,{'priority':1,'action':'Close C01/C05/C06/blind-end tolerances using T05 local flange/contact evidence plus current manufacturing capability.','mode':'ENGINEERING_CALCULATION'})
    for i,x in enumerate(q,1): x['priority']=i
    d['immediate_execution_queue']=q; dump(p,d)

    p=root/'control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json'; d=load(p); d['generated_utc']=datetime.now(timezone.utc).isoformat()
    d['active_engineering_gaps']=[x for x in d.get('active_engineering_gaps',[]) if x.get('id')!='C07_C08_C11']
    for x in [
        {'id':'IF_RADIAL_INNER_COUNTERPART','status':'OPEN_INTERFACE_QUALIFICATION','topic':'P008/moving-group OD, guide alignment/runout and dynamic no-rub allocation relative to P007 datum B; not a P007 size-definition blocker'},
        {'id':'IF_RADIAL_OUTER_P015','status':'OPEN_INTERFACE_QUALIFICATION','topic':'P015 production ID/material/tolerance/alignment relative to P007 OD; not a P007 size-definition blocker'}]:
        if not any(y.get('id')==x['id'] for y in d.get('active_engineering_gaps',[])): d.setdefault('active_engineering_gaps',[]).append(x)
    closed=d.setdefault('closed_do_not_restart',[])
    s='C07/C08/C11 P007-side radial envelope via EDR-029: Ø10 h9 / Ø9.40 H9 / TOTAL RUNOUT 0.02 | B'
    if s not in closed: closed.append(s)
    dump(p,d)

    # Next-actions semantic update.
    p=root/'control/project/K01_NEXT_ACTIONS_CURRENT.json'; d=load(p); d['generated_utc']=datetime.now(timezone.utc).isoformat()
    d['current_stage']='P007 Product Definition Closure — C07/C08/C11 released; local flange/remaining tolerances active'
    d['last_completed']='EDR-029 C07/C08/C11 P007-side radial envelope release definition'
    d['current_blocker']='Full K01-D-006 remains blocked by C01/C05/C06/blind-end tolerance/form closure, thin-wall capability, seal/leak/process/inspection and BOM gaps.'
    d['next_1']='Close C01/C05/C06/blind-end tolerances using T05 and current process evidence; do not return to drawing authoring yet.'
    d['execution_mode']='ENGINEERING_DECISION'
    seq=[x for x in d.get('engineering_sequence',[]) if 'C07/C08/C11' not in x]
    if not seq or 'C01/C05/C06/blind-end' not in seq[0]: seq.insert(0,'C01/C05/C06/blind-end tolerance/form closure via T05/process evidence')
    d['engineering_sequence']=seq
    a=d.setdefault('authority',[]); rel='control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json'
    if rel not in a: a.append(rel)
    dump(p,d)

    update_pds_source(root/'tools/pds/k01_pds.py')
    strengthen_source_hygiene(root/'tools/repo/source_hygiene_guard.py')

    print('STEP4_SOURCE_UPDATE: PASS')
    print('C07: RELEASE Ø10 h9 = 9.964..10.000 mm')
    print('C08: RELEASE Ø9.40 H9 = 9.400..9.436 mm; wall 0.30 REF')
    print('C11: RELEASE TOTAL RUNOUT 0.02 | B on thin-can OD and ID')
    print('P007-side radial definition: CLOSED / EDR-029')
    print('COUNTERPART P008/P015 interface qualification: preserved OPEN separately')
    print('NEXT: C01/C05/C06/blind-end tolerance/form closure via T05/process evidence')
    return 0

if __name__=='__main__': raise SystemExit(main())
