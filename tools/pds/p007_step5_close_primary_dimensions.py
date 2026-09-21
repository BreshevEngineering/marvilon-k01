from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone


def load(p: Path):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def find_char(rows, cid):
    for r in rows:
        if r.get('id') == cid:
            return r
    raise RuntimeError(f'missing characteristic {cid}')

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        if new in text:
            return text
        raise RuntimeError(f'cannot update {label}: anchor not found')
    return text.replace(old, new, 1)

def run(root: Path, args: list[str]):
    print('RUN:', ' '.join(args))
    cp = subprocess.run(args, cwd=root)
    if cp.returncode:
        raise RuntimeError(f'command failed rc={cp.returncode}: {args}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root', default='.')
    ap.add_argument('--rebuild', action='store_true')
    a=ap.parse_args()
    root=Path(a.repo_root).resolve()

    # Mandatory upstream decisions/evidence.
    required = [
        'control/decisions/EDR-025_P007_MONOLITHIC_REMOVABLE_J2_BASELINE.json',
        'control/decisions/EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE.json',
        'control/decisions/EDR-028_P007_C03_C04_RELEASE.json',
        'control/decisions/EDR-029_P007_C07_C08_C11_RADIAL_ENVELOPE_RELEASE.json',
        'control/workpacks/K01_T05_J2_CLAMP_STRENGTH_WORKPACKAGE_v1.json',
        'control/drawings/K01_D006_RELEASE_DEFINITION.json',
    ]
    for rel in required:
        if not (root/rel).is_file():
            raise RuntimeError(f'MISSING authority/evidence: {rel}')

    # 1) Current Product Definition decisions.
    p=root/'control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json'
    d=load(p); chars=d.get('characteristics',[])

    c=find_char(chars,'C01')
    c.update({
        'definition_state':'CONTROLLED',
        'nominal_or_requirement':{
            'datum':'A',
            'datum_identity':'CONTROLLED_COMPOSITE_COPLANAR_FACE_SET',
            'controlled_contact_patches':2,
        },
        'variation_semantics':{
            'flatness':'0.03 mm COMMON/COMBINED ZONE (CZ) across the two controlled Datum-A mating-face patches',
            'orientation':'NOT_APPLICABLE_TO_SELF_DATUM_FORM_CONTROL',
        },
        'authority_sources':['functional datum architecture','canonical persistent-ref binding','EDR-030_P007_C01_C05_C06_BLIND_END_RELEASE','SRC-TORNINCASA-GPS-DATUMS-FORM'],
        'cad_binding':'PASS_CANONICAL_PERSISTENT_REF_COMPOSITE_FACE_SET',
        'mbd_carrier':'Native Datum A + flatness 0.03 CZ on the controlled composite mating-face set',
        'drawing_projection':'PROJECT DATUM A and FLATNESS 0.03 CZ on the controlled two-patch mating-face set',
        'inspection':'CMM/common-zone plane evaluation of both controlled contact patches; clean free-state part; no clamp distortion',
        'release_blocking':False,
    })

    c=find_char(chars,'C05')
    c.update({
        'definition_state':'CONTROLLED',
        'nominal_or_requirement':{'diameter_mm':33.0,'thickness_mm':3.0},
        'variation_semantics':{
            'diameter_tolerance':'±0.05 mm',
            'diameter_limits_mm':[32.95,33.05],
            'thickness_tolerance':'±0.05 mm',
            'thickness_limits_mm':[2.95,3.05],
        },
        'authority_sources':['canonical native geometry','proven P007 PMI nominal evidence','WP-T05','EDR-030_P007_C01_C05_C06_BLIND_END_RELEASE'],
        'cad_binding':'PASS_CANONICAL_PERSISTENT_REF',
        'mbd_carrier':'DimXpert/native PMI Ø33.00 ±0.05 plus flange thickness 3.00 ±0.05',
        'drawing_projection':'PROJECT Ø33.00 ±0.05 and flange thickness 3.00 ±0.05',
        'inspection':'OD micrometer/CMM; flange thickness by CMM or qualified thickness/depth measurement',
        'release_blocking':False,
    })

    c=find_char(chars,'C06')
    c.update({
        'definition_state':'CONTROLLED',
        'nominal_or_requirement':{'overall_length_mm':35.0,'measurement_origin':'Datum A functional mating plane','measurement_terminus':'external blind-end face'},
        'variation_semantics':{'length_tolerance':'±0.05 mm','length_limits_mm':[34.95,35.05]},
        'authority_sources':['REQ-K01-P007-L-001','canonical native geometry','C2R1 mechanical baseline','EDR-030_P007_C01_C05_C06_BLIND_END_RELEASE'],
        'cad_binding':'PASS_CANONICAL_PERSISTENT_REF',
        'mbd_carrier':'native model dimension / controlled size annotation 35.00 ±0.05',
        'drawing_projection':'PROJECT OAL 35.00 ±0.05 from Datum-A side to external blind-end face',
        'inspection':'CMM or qualified length measurement from the functional Datum-A setup',
        'release_blocking':False,
    })

    c=find_char(chars,'K01-D006-BLIND-END')
    c.update({
        'definition_state':'CONTROLLED',
        'nominal_or_requirement':{'thickness_mm':1.0,'limits_mm':[0.9,1.1]},
        'variation_semantics':{'thickness_tolerance':'±0.10 mm'},
        'authority_sources':['canonical native geometry','K01_P007_FUNCTIONAL_TOLERANCE_PLAN FT-05','EDR-027_T07A_PRESSURE_SHELL_SCREEN_ACCEPTANCE','EDR-030_P007_C01_C05_C06_BLIND_END_RELEASE'],
        'cad_binding':'PENDING_DETERMINISTIC_BINDING',
        'mbd_carrier':'native size annotation 1.00 ±0.10 after deterministic blind-end face-pair binding',
        'drawing_projection':'PROJECT BLIND-END THICKNESS 1.00 ±0.10',
        'inspection':'CMM/depth comparison between external end face and internal blind-bottom face, or equivalent qualified thickness method',
        'release_blocking':False,
    })

    # Edge condition is now controlled. Surface texture remains deliberately open.
    for g in d.get('coverage_gaps',[]):
        if g.get('id')=='PDG-EDGE-CONDITION':
            g.update({
                'state':'CONTROLLED',
                'requirement':'DEBURR. Break non-functional sharp edges 0.1–0.2 mm. Do not break/abrade Datum A, Ø14.10 H7 locator, seal-contact, or other explicitly controlled functional edges unless specifically dimensioned.',
                'release_blocking':False,
                'authority':'EDR-030_P007_C01_C05_C06_BLIND_END_RELEASE',
            })
    rej=d.get('explicitly_rejected_legacy_semantics',[])
    rej=[x for x in rej if not (x.startswith('C01 FLATNESS 0.03') or x.startswith('C05 Ø33.00') or x.startswith('C06 35.00'))]
    for x in [
        'C01/C05/C06 legacy values are no longer release-rejected after explicit revalidation and promotion by EDR-030; only pre-EDR-030 uncontrolled use remains superseded.',
        'Permanent P003↔P007 containment weld as active C2R1 baseline'
    ]:
        if x not in rej: rej.append(x)
    d['explicitly_rejected_legacy_semantics']=rej
    dump(p,d)

    # 2) Product characteristic source status.
    p=root/'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json'
    d=load(p)
    for r in d.get('characteristics',[]):
        cid=r.get('id')
        if cid=='C01':
            r.update({'candidate_spec':'DATUM A; FLATNESS 0.03 CZ across controlled two-patch mating-face set','status':'CONTROLLED_BY_EDR_030','current_state':'CONTROLLED_RELEASE_DEFINITION','authority_class':'EDR_030_CONTROLLED_REQUIREMENT'})
        elif cid=='C05':
            r.update({'candidate_spec':'Ø33.00 ±0.05 × 3.00 ±0.05','status':'CONTROLLED_BY_EDR_030','current_state':'CONTROLLED_RELEASE_DEFINITION','authority_class':'CURRENT_NATIVE_GEOMETRY_PLUS_EDR_030'})
        elif cid=='C06':
            r.update({'candidate_spec':'35.00 ±0.05','status':'CONTROLLED_BY_EDR_030','current_state':'CONTROLLED_RELEASE_DEFINITION','authority_class':'CURRENT_NATIVE_GEOMETRY_PLUS_EDR_030'})
        elif cid=='K01-D006-BLIND-END':
            r.update({'candidate_spec':'1.00 ±0.10','status':'CONTROLLED_BY_EDR_030','current_state':'CONTROLLED_RELEASE_DEFINITION','authority_class':'CURRENT_NATIVE_GEOMETRY_PLUS_EDR_027_EDR_030'})
    be=d.get('blind_end',{})
    if be:
        be['tolerance_status']='CONTROLLED_EDR_030'
        be['release_tolerance']='1.00 ±0.10 mm'
    d['open_items']=[x for x in d.get('open_items',[]) if x not in {'K01-D006-BLIND-END-TOLERANCE'}]
    dump(p,d)

    # 3) Context: close practical measurement / inspection method for this block only.
    p=root/'control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json'
    d=load(p); ctx=d.get('characteristics',{})
    ctx['C01']['measurement_condition']={'temperature':'20±2 °C metrology condition','part_state':'CLEAN_FREE_STATE','fixture':'DATUM_SIMULATOR_WITHOUT_DISTORTING_CLAMP','measurement_force':'LOW_FORCE_AS_NEEDED','status':'CONTROLLED'}
    ctx['C01']['inspection_strategy']={'method':'CMM_COMMON_ZONE_FLATNESS_CZ_ON_TWO_DATUM_A_PATCHES','capability':'FIRST_ARTICLE_CONFIRMATION_REQUIRED'}
    ctx['C05']['measurement_condition']={'temperature':'20±2 °C metrology condition','part_state':'FREE_STATE','fixture':'NON_DISTORTING_SUPPORT','measurement_force':'NORMAL_SIZE_METROLOGY','status':'CONTROLLED'}
    ctx['C05']['inspection_strategy']={'method':'OD_MICROMETER_OR_CMM_PLUS_FLANGE_THICKNESS_MEASUREMENT','capability':'STANDARD_PRECISION_CAPABILITY'}
    for t in ctx['C05']['drawing_authoring']['targets']:
        t.update({'authoring_class':'CONTROLLED_SIZE','release_eligible':True})
        if t.get('claim_id')=='C05.FLANGE_OD': t['action']='VERIFY_EXISTING_AND_APPLY_RELEASE_TOLERANCE'
        elif t.get('claim_id')=='C05.FLANGE_THICKNESS': t['action']='AUTHOR_RELEASE_THICKNESS_AFTER_BINDING_SIGNATURE'
    ctx['C06']['measurement_condition']={'temperature':'20±2 °C metrology condition','part_state':'FREE_STATE','fixture':'DATUM_A_FUNCTIONAL_SETUP','measurement_force':'NORMAL_CMM_OR_LENGTH_METROLOGY','status':'CONTROLLED'}
    ctx['C06']['inspection_strategy']={'method':'CMM_OR_LENGTH_MEASUREMENT_FROM_DATUM_A_TO_EXTERNAL_BLIND_END_FACE','capability':'STANDARD_PRECISION_CAPABILITY'}
    ctx['C06']['drawing_authoring']['targets'][0].update({'authoring_class':'CONTROLLED_SIZE','action':'AUTHOR_OAL_35P00_PM0P05_AFTER_BINDING_SIGNATURE','release_eligible':True})
    bectx=ctx['K01-D006-BLIND-END']
    bectx['datum_reference_system']={'defines':[],'references':[],'status':'NOT_REQUIRED_FOR_SIZE_IDENTITY'}
    bectx['measurement_condition']={'temperature':'20±2 °C metrology condition','part_state':'THIN_WALL_SUPPORTED_NON_DISTORTING_STATE','fixture':'SUPPORTED_LOW_FORCE','measurement_force':'LOW_FORCE','status':'CONTROLLED'}
    bectx['inspection_strategy']={'method':'CMM_OR_DEPTH_DIFFERENCE_EXTERNAL_END_TO_INTERNAL_BLIND_BOTTOM','capability':'FIRST_ARTICLE_CONFIRMATION_REQUIRED'}
    bectx['drawing_authoring']['targets'][0].update({'authoring_class':'CONTROLLED_SIZE','action':'AUTHOR_BLIND_END_1P00_PM0P10_AFTER_BINDING_SIGNATURE','release_eligible':True})
    dump(p,d)

    # 4) Drawing intent becomes the controlled design-review target; no CAD mutation here.
    p=root/'control/drawings/spec/K01-D-006_P007_DRAWING_INTENT_v1.json'
    d=load(p); rows=d.get('characteristics',[])
    for r in rows:
        if r.get('id')=='P007-C01': r.update({'spec':'DATUM A; FLATNESS 0.03 CZ across controlled two-patch mating-face set','source':'EDR-030 + canonical Datum-A binding','inspection':'CMM common-zone flatness / functional datum setup'})
        elif r.get('id')=='P007-C05': r.update({'spec':'Ø33.00 ±0.05 × 3.00 ±0.05 within OAL','source':'EDR-030 + WP-T05','inspection':'OD micrometer/CMM + flange thickness'})
        elif r.get('id')=='P007-C06': r.update({'spec':'35.00 ±0.05','source':'EDR-030 + REQ-K01-P007-L-001','inspection':'CMM from functional Datum-A setup'})
    if not any(r.get('id')=='P007-BLIND-END' for r in rows):
        rows.append({'id':'P007-BLIND-END','feature':'integral blind-end thickness','type':'SIZE_CONTAINMENT','spec':'1.00 ±0.10','source':'EDR-030 + EDR-027','view':'SECTION_AA','inspection':'CMM/depth-difference or qualified thickness method'})
    notes=d.setdefault('general_notes',[])
    edge='DEBURR; BREAK NON-FUNCTIONAL SHARP EDGES 0.1–0.2. DO NOT BREAK OR ABRADE DATUM A, Ø14.10 H7 LOCATOR, SEAL-CONTACT, OR OTHER EXPLICITLY CONTROLLED FUNCTIONAL EDGES.'
    notes=[x for x in notes if not x.startswith('DEBURR; BREAK SHARP EDGES')]
    notes.append(edge); d['general_notes']=notes
    dump(p,d)

    # 5) Release definition / authoring input.
    p=root/'control/drawings/K01_D006_RELEASE_DEFINITION.json'
    d=load(p)
    d['release_blockers']=[x for x in d.get('release_blockers',[]) if 'C01/C05/C06/blind-end remaining' not in x and 'blind-end released tolerance' not in x]
    d['EDR_030_primary_dimensions']={'status':'CONTROLLED','C01':'FLATNESS 0.03 CZ on Datum-A two-patch set','C05':'Ø33.00 ±0.05; thickness 3.00 ±0.05','C06':'35.00 ±0.05','blind_end':'1.00 ±0.10','edge_condition':'CONTROLLED_NONFUNCTIONAL_0P1_TO_0P2_WITH_FUNCTIONAL_EXCLUSIONS'}
    for x in ['surface texture on functionally required surfaces','thin-wall/blind-end manufacturing capability','C12 quantitative leak/containment acceptance','inspection/release measurement conditions','configuration/effectivity + final binding-invariance qualification']:
        if x not in d['release_blockers']: d['release_blockers'].append(x)
    dump(p,d)

    aip=root/'control/drawings/K01_D006_AUTHORING_INPUT.json'
    if aip.is_file():
        d=load(aip)
        d['release_blockers']=[x for x in d.get('release_blockers',[]) if 'C01/C05/C06/blind-end remaining' not in x and 'blind-end released tolerance' not in x]
        d['primary_dimension_decision']='CONTROLLED_BY_EDR_030'
        d['next_action']='Author/refresh the full-geometry K01-D-006 engineering-review candidate from the current controlled Product Definition while keeping remaining process/release holds explicit.'
        dump(aip,d)

    # 6) Workpack and next-actions.
    p=root/'control/workpacks/K01_P007_PRODUCT_DEFINITION_CLOSURE_v1.json'
    d=load(p); d['status']='IN_PROGRESS__PRIMARY_DIMENSIONS_CLOSED__SEAL_LEAK_INSPECTION_ACTIVE'
    for r in d.get('technical_filter',[]):
        if r.get('id')=='C01': r.update({'disposition':'ACCEPT_FLATNESS_0P03_CZ_EDR_030','next':'Definition closed; final PMI binding/invariance after full characteristic freeze.'})
        elif r.get('id')=='C05': r.update({'disposition':'ACCEPT_OD33_PM0P05__T3_PM0P05_EDR_030','next':'Definition closed; T05 local contact FEA remains a post-seal/process stale trigger, not current geometry blocker.'})
        elif r.get('id')=='C06': r.update({'disposition':'ACCEPT_35_PM0P05_EDR_030','next':'Definition closed.'})
        elif r.get('id')=='K01-D006-BLIND-END': r.update({'disposition':'ACCEPT_1P00_PM0P10_EDR_030','next':'Definition closed; first-article/process capability remains manufacturing evidence.'})
        elif r.get('id')=='EDGE_CONDITION': r.update({'disposition':'ACCEPT_CONTROLLED_DEBURR_NONFUNCTIONAL_0P1_0P2','next':'Definition closed; functional edges excluded.'})
    d['immediate_execution_queue']=[
        {'priority':1,'action':'Freeze media/cleaning envelope + exact seal product/compound + C12 quantitative leak acceptance.','mode':'ENGINEERING_REQUIREMENT_DECISION'},
        {'priority':2,'action':'Freeze exact M2.5 screw/finish/lubrication/torque-preload process and remaining service requirement.','mode':'ENGINEERING_PROCESS_DECISION'},
        {'priority':3,'action':'Close surface texture only on functionally required surfaces + inspection/measurement conditions; freeze final characteristic table.','mode':'ENGINEERING_CLOSURE'},
        {'priority':4,'action':'Author/refresh full K01-D-006 engineering-review candidate from controlled Product Definition; keep release holds explicit.','mode':'MANUAL_CONTROLLED_DRAWING'},
        {'priority':5,'action':'After full PMI freeze run one binding-invariance qualification, configuration/effectivity, D7/D8/D9, BOM/P6.','mode':'RELEASE_VERIFICATION'},
    ]
    dump(p,d)

    p=root/'control/project/K01_NEXT_ACTIONS_CURRENT.json'
    d=load(p); d['generated_utc']=datetime.now(timezone.utc).isoformat()
    d['current_stage']='P007 Product Definition Closure — primary geometric/tolerance block released by EDR-030; seal/leak/inspection/process active'
    d['last_completed']='EDR-030 C01/C05/C06/blind-end + edge-condition release definition'
    d['current_blocker']='Full release remains blocked by seal/media/C12, surface texture where functionally required, manufacturing capability, inspection/measurement, configuration/effectivity, binding invariance and BOM gaps.'
    d['next_1']='Freeze media/seal/C12 and inspection/process requirements in parallel; K01-D-006 full-geometry engineering-review candidate may now be authored/refreshed from controlled Product Definition without inventing release values.'
    d['execution_mode']='ENGINEERING_DECISION_PLUS_MANUAL_CONTROLLED_DRAWING'
    d['engineering_sequence']=[
        'media/seal/C12 + exact fastener/process closure',
        'surface texture + inspection/measurement closure',
        'final P007 characteristic table',
        'native PMI/DimXpert with stable characteristic names',
        'full K01-D-006 engineering-review candidate / then release candidate',
        'one full binding-invariance qualification + configuration/effectivity',
        'D7/D8/D9 + EBOM/MBOM verify + P6',
    ]
    authlist=d.setdefault('authority',[]); rel='control/decisions/EDR-030_P007_C01_C05_C06_BLIND_END_RELEASE.json'
    if rel not in authlist: authlist.append(rel)
    dump(p,d)

    # 7) Release gap register.
    p=root/'control/project/K01_P007_RELEASE_GAP_REGISTER_CURRENT.json'
    if p.is_file():
        d=load(p); d['generated_utc']=datetime.now(timezone.utc).isoformat()
        d['active_engineering_gaps']=[x for x in d.get('active_engineering_gaps',[]) if x.get('id')!='C01_C05_C06_BLIND_END']
        closed=d.setdefault('closed_do_not_restart',[])
        s='C01/C05/C06/blind-end + edge condition via EDR-030'
        if s not in closed: closed.append(s)
        dump(p,d)

    # 8) Update lifecycle source text, without creating a new orchestration layer.
    p=root/'tools/pds/k01_pds.py'; txt=p.read_text(encoding='utf-8')
    txt=replace_once(txt,
        '["C01/C05/C06/blind-end tolerance closure","thin-wall/blind-end manufacturing capability","seal/media/leak definition","fastener/process qualification","inspection plan"]',
        '["thin-wall/blind-end manufacturing capability","seal/media/leak definition","fastener/process qualification","inspection plan"]',
        'PDS Stage6 blockers')
    txt=replace_once(txt,
        '["Close C01/C05/C06/blind-end tolerances via T05/process evidence","Qualify 0.30 mm nominal wall / integral blind-end manufacturing and inspection capability",',
        '["Qualify 0.30 mm nominal wall / integral blind-end manufacturing and inspection capability","Close surface texture/inspection/measurement conditions",',
        'PDS Stage6 next')
    txt=replace_once(txt,
        '{"priority":4,"lane":"VARIATION","task":"Close C01/C05/C06/blind-end tolerances using T05 and current process evidence",\n         "type":"ENGINEERING_DECISION_EXECUTABLE_NOW","upstream":["EDR-029 C07/C08/C11 released","T07A PASS"]},',
        '{"priority":4,"lane":"VARIATION","task":"C01/C05/C06/blind-end released by EDR-030; close remaining surface/inspection/process semantics",\n         "type":"ENGINEERING_CLOSURE","upstream":["EDR-030 primary dimensions released"]},',
        'PDS queue')
    p.write_text(txt,encoding='utf-8')

    # 9) Write a small decision-application report.
    rpt=root/'reports/engineering/K01_P007_PRIMARY_DIMENSIONS_RELEASE_DECISION_CURRENT.md'
    rpt.write_text('''# K01-P-007 primary dimensions/form release — EDR-030\n\n'
**C01** — Datum A composite mating-face set; `FLATNESS 0.03 CZ`.\n\n'
**C05** — `Ø33.00 ±0.05`; flange thickness `3.00 ±0.05`.\n\n'
**C06** — OAL `35.00 ±0.05` from functional Datum-A side to external blind-end face.\n\n'
**Blind end** — `1.00 ±0.10`.\n\n'
**Edge condition** — deburr; break non-functional sharp edges 0.1–0.2 mm; protect functional datum/fit/seal edges.\n\n'
No new FEA is required for this Product Definition decision. Existing T05 analytical evidence remains the architecture/local-contact basis; one final local verification is deferred until seal/process inputs are frozen if still required.\n'''.replace("'\n",'\n'), encoding='utf-8')

    print('STEP5_SOURCE_UPDATE: PASS')
    print('C01: RELEASE DATUM A + FLATNESS 0.03 CZ')
    print('C05: RELEASE Ø33.00 ±0.05; t=3.00 ±0.05')
    print('C06: RELEASE OAL 35.00 ±0.05')
    print('BLIND END: RELEASE 1.00 ±0.10')
    print('EDGE CONDITION: CONTROLLED')
    print('NEXT: media/seal/C12 + inspection/process; full-geometry K01-D-006 engineering-review candidate may proceed in parallel')

    if a.rebuild:
        run(root,[sys.executable,'tools/pds/k01_pds.py','--repo-root',str(root),'status'])
        run(root,[sys.executable,'tools/medtas/product_definition_guard_v11.py'])
        run(root,[sys.executable,'tools/medtas/build_bom_v1_9.py','--repo-root',str(root)])
        run(root,[sys.executable,'tools/medtas/rebuild_medtas_state.py','--repo-root',str(root)])
        run(root,[sys.executable,'tools/medtas/ai_handoff_v2_0.py','--repo-root',str(root),'--cad-root',r'D:\Marvilon\K01\cad'])
    return 0

if __name__=='__main__':
    raise SystemExit(main())
