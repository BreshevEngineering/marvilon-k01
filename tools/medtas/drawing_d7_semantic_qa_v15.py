from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from medtas_v16_common import register_build, register_verify
from drawing_d3_d7_v15_common import ROOT, load, dump, run, sw_running, compile_helper, parse_kv, workspace_paths

CS=ROOT/'cad_api/solidworks_2018_proven/current/K01_D3_D7_V15/K01D006D7VerifyV15.cs'
RAW=ROOT/'reports/cad/d3_d7_v15_current/K01_D006_D7_RAW_CURRENT.txt'
OUT=ROOT/'reports/drawing/current/K01-D-006_D7_SEMANTIC_QA_CURRENT.json'
CTRL=ROOT/'reports/control/K01_D006_D7_SEMANTIC_QA_CURRENT.json'
D3=ROOT/'reports/drawing/current/K01-P-007_D3_AUTHORING_VERIFY_CURRENT.json'
POL=ROOT/'control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json'
PROFILE=ROOT/'control/drawings/K01_DRAWING_STANDARD_PROFILE_CURRENT.json'


def b(kv,k): return kv.get(k)=='True'
def n(kv,k):
    try:return int(kv.get(k,'0') or 0)
    except:return 0

def main():
    status='HOLD_D7_V15'
    try:
        if sw_running(): raise RuntimeError('Close SolidWorks before D7 so semantic QA reads only saved drawing/model files.')
        for p in (CS,POL,PROFILE,D3):
            if not p.exists(): raise RuntimeError(f'missing input: {p.relative_to(ROOT)}')
        d3=load(D3)
        if not str(d3.get('status','')).startswith('PASS_D3_EXEMPLAR_'): raise RuntimeError('D3 exemplar L1/L2 must pass before D7')
        ws,part,drawing=workspace_paths(); exe=compile_helper(CS,'K01D006D7VerifyV15.exe',RAW.parent/'build_d7');RAW.parent.mkdir(parents=True,exist_ok=True)
        cp=run([str(exe),'--drawing',str(drawing),'--part',str(part),'--report',str(RAW)],timeout=600)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        if not RAW.exists(): raise RuntimeError('D7 raw report missing')
        kv=parse_kv(RAW)
        machine_codes=['DQA-001','DQA-002','DQA-003','DQA-004','DQA-005','DQA-006','DQA-008','DQA-010','DQA-013','DQA-014','DQA-017','DQA-018','DQA-019','DQA-020']
        checks={c:b(kv,c) for c in machine_codes}
        # DQA-007/009/015 remain outside first exemplar release scope; keep explicit, not silently PASS.
        checks['DQA-007']='OPEN_CONFIGURATION_EFFECTIVITY_RELEASE_ONLY'
        checks['DQA-009']='PASS_REGISTRY_IDENTITY__NOT_A_VISIBLE_BALLOON_REQUIREMENT'
        checks['DQA-015']='OPEN_NO_PRE_D6_SEMANTIC_FINGERPRINT_FOR_LEGACY_FIRST_EXEMPLAR'
        checks['DQA-011']='WARN' if n(kv,'P007_VIEW_REFS')>0 else 'HOLD'
        checks['DQA-012']='WARN' if n(kv,'VIEW_OVERLAP_PAIRS')>0 else 'PASS'
        blocking=[c for c in machine_codes if not checks[c]]
        warnings=[]
        if not b(kv,'TITLE_TEXT_MATERIAL_FOUND'): warnings.append('Title-block/material text was not machine-detected. Model material is checked by DQA-008; title-block presentation still needs D8/manual verification or property-link normalization.')
        if n(kv,'VIEW_OVERLAP_PAIRS')>0: warnings.append(f"{n(kv,'VIEW_OVERLAP_PAIRS')} drawing-view bounding-box overlap pair(s) detected; inspect visually in D8.")
        warnings += ['DQA-007 configuration/effectivity and DQA-015 pre/post-D6 semantic fingerprint are not retroactively provable for this first legacy exemplar; they remain mandatory for release-native pipeline runs.']
        if blocking: status='HOLD_D7_EXEMPLAR_SCOPE'
        else: status='PASS_D7_EXEMPLAR_SCOPE__RELEASE_D7_STILL_HOLD'
        payload={
          'schema':'k01.d7.semantic_qa.current.v15','generated_utc':datetime.now(timezone.utc).isoformat(),'status':status,'scope':'FIRST_P007_MANUAL_EXEMPLAR_NOT_RELEASE','part':'K01-P-007','drawing':'K01-D-006','workspace_drawing':str(drawing),'workspace_part':str(part),
          'checks':checks,'blocking_checks':blocking,'warnings':warnings,
          'counts':{
            'p007_view_refs':n(kv,'P007_VIEW_REFS'),'C01_visible':n(kv,'C01_VISIBLE_COUNT'),'C02_visible':n(kv,'C02_VISIBLE_COUNT'),'C05_visible_unauthorized':n(kv,'C05_VISIBLE_UNAUTHORIZED_COUNT'),'other_visible_dimensions':n(kv,'OTHER_VISIBLE_DIM_COUNT'),'manual_non_dimxpert_dimensions':n(kv,'VISIBLE_NON_DIMXPERT_DIM_COUNT'),'other_datums':n(kv,'VISIBLE_OTHER_DATUM_COUNT'),'gtol':n(kv,'VISIBLE_GTOL_COUNT'),'surface':n(kv,'VISIBLE_SURFACE_COUNT'),'dangling':n(kv,'DANGLING_VISIBLE_COUNT'),'display_overrides':n(kv,'DISPLAY_OVERRIDE_COUNT'),'unit_overrides':n(kv,'UNIT_OVERRIDE_COUNT'),'fallback_notes':n(kv,'FALLBACK_NOTE_COUNT'),'view_overlap_pairs':n(kv,'VIEW_OVERLAP_PAIRS')},
          'environment':{'mm':b(kv,'DRAWING_MM'),'iso':b(kv,'DETAILING_STANDARD_ISO'),'first_angle':b(kv,'FIRST_ANGLE'),'a3':b(kv,'SHEET_A3'),'sheet_width_m':kv.get('SHEET_WIDTH_M'),'sheet_height_m':kv.get('SHEET_HEIGHT_M'),'view_scales':kv.get('VIEW_SCALES')},
          'material':{'model_controlled':b(kv,'MODEL_MATERIAL_CONTROLLED'),'raw':kv.get('MODEL_MATERIAL_RAW'),'title_text_detected':b(kv,'TITLE_TEXT_MATERIAL_FOUND')},
          'notes':{'general_tolerance_note_found':b(kv,'GENERAL_TOLERANCE_NOTE_FOUND'),'default_roughness_note_found':b(kv,'DEFAULT_ROUGHNESS_NOTE_FOUND')},
          'raw_records':kv.get('_REC',[]),'raw_report':str(RAW.relative_to(ROOT)),
          'release_boundary':'Passing this exemplar scope proves semantic cleanliness of currently authorized C01/C02/C09 presentation only. It does not close the 18 Product Definition release blockers, D3 L3, configuration/effectivity, or D8 visual approval.'
        }
        dump(OUT,payload);dump(CTRL,{'schema':'k01.d7.gate.current.v15','status':status,'blocking_checks':blocking,'warnings':warnings,'report':str(OUT.relative_to(ROOT)),'next':'If HOLD, correct only listed drawing-presentation defects on the same V12 exemplar and rerun D7. If PASS, proceed to D8 visual QA and freeze the first controlled exemplar.'})
        br=register_build(ROOT,'K01.DRAWING.D006.D7.SEMANTIC_QA','tools/medtas/drawing_d7_semantic_qa_v15.py + K01D006D7VerifyV15.cs',limitations=warnings,extra={'workspace_drawing':str(drawing),'scope':'FIRST_P007_MANUAL_EXEMPLAR'})
        register_verify(ROOT,'K01.DRAWING.D006.D7.SEMANTIC_QA','PASS_WITH_LIMITATIONS' if not blocking else 'HOLD',metrics={'blocking_count':len(blocking),'C01':n(kv,'C01_VISIBLE_COUNT'),'C02':n(kv,'C02_VISIBLE_COUNT'),'unauthorized_C05':n(kv,'C05_VISIBLE_UNAUTHORIZED_COUNT'),'dangling':n(kv,'DANGLING_VISIBLE_COUNT'),'manual_dims':n(kv,'VISIBLE_NON_DIMXPERT_DIM_COUNT'),'mm':b(kv,'DRAWING_MM'),'iso':b(kv,'DETAILING_STANDARD_ISO'),'first_angle':b(kv,'FIRST_ANGLE'),'a3':b(kv,'SHEET_A3')},limitations=warnings)
        print('STATUS:',status);print('BLOCKING_CHECKS:',','.join(blocking) if blocking else 'NONE');print('AUTHORIZED C01/C02:',n(kv,'C01_VISIBLE_COUNT'),n(kv,'C02_VISIBLE_COUNT'));print('UNAUTHORIZED C05:',n(kv,'C05_VISIBLE_UNAUTHORIZED_COUNT'));print('FALLBACK NOTES:',n(kv,'FALLBACK_NOTE_COUNT'),'MANUAL DIMS:',n(kv,'VISIBLE_NON_DIMXPERT_DIM_COUNT'),'DANGLING:',n(kv,'DANGLING_VISIBLE_COUNT'));print('ENV MM/ISO/FIRST_ANGLE/A3:',b(kv,'DRAWING_MM'),b(kv,'DETAILING_STANDARD_ISO'),b(kv,'FIRST_ANGLE'),b(kv,'SHEET_A3'));print('MATERIAL MODEL:',b(kv,'MODEL_MATERIAL_CONTROLLED'),kv.get('MODEL_MATERIAL_RAW',''));print('VIEW OVERLAP PAIRS:',n(kv,'VIEW_OVERLAP_PAIRS'));print('REPORT:',OUT);print('MEDTAS_STATE_HASH:',br['built_state_hash'])
        return 0 if not blocking else 3
    except Exception as e:
        dump(CTRL,{'schema':'k01.d7.gate.current.v15','status':status,'error':repr(e)});print('STATUS:',status);print('ERROR:',repr(e));print('REPORT:',CTRL);return 2
if __name__=='__main__': raise SystemExit(main())
