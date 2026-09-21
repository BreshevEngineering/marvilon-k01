from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
from medtas_v16_common import register_build, register_verify
from drawing_d3_d7_v15_common import ROOT, load, dump, run, sw_running, compile_helper, parse_kv, workspace_paths

CS=ROOT/'cad_api/solidworks_2018_proven/current/K01_D3_D7_V15/K01P007D3VerifyV15.cs'
RAW=ROOT/'reports/cad/d3_d7_v15_current/K01_P007_D3_RAW_CURRENT.txt'
OUT=ROOT/'reports/drawing/current/K01-P-007_D3_AUTHORING_VERIFY_CURRENT.json'
CTRL=ROOT/'reports/control/K01_P007_D3_AUTHORING_VERIFY_CURRENT.json'
POL=ROOT/'control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json'
D1=ROOT/'reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json'


def b(kv,k): return kv.get(k)=='True'
def i(kv,k):
    try:return int(kv.get(k,'0') or 0)
    except:return 0

def main():
    status='HOLD_D3_V15'
    try:
        if sw_running(): raise RuntimeError('Close SolidWorks before D3 so rebuild/readback is performed against saved workspace files.')
        for p in (CS,POL,D1):
            if not p.exists(): raise RuntimeError(f'missing input: {p.relative_to(ROOT)}')
        ws,part,drawing=workspace_paths(); d1=load(D1)
        exe=compile_helper(CS,'K01P007D3VerifyV15.exe',RAW.parent/'build_d3')
        RAW.parent.mkdir(parents=True,exist_ok=True)
        cp=run([str(exe),'--part',str(part),'--report',str(RAW)],timeout=600)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        if not RAW.exists(): raise RuntimeError('D3 raw report missing')
        kv=parse_kv(RAW)
        l1=b(kv,'L1_SAVE_REOPEN');l2=b(kv,'L2_FORCE_REBUILD');src=b(kv,'SOURCE_SHA_INVARIANT')
        c01=b(kv,'C01_PASS');c02=b(kv,'C02_PASS');c09=b(kv,'C09_MATERIAL_PASS')
        c01v=kv.get('S2_C01_VIEW','');c02v=kv.get('S2_C02_VIEW','')
        c01geom=b(kv,'S2_C01_GEOM');c02geom=b(kv,'S2_C02_GEOM')
        authorized=set(d1.get('d2_authorizable_claim_ids') or [])
        checks={
          'D3-001_C01_DATUM_IDENTITY_AND_GEOMETRY':c01 and c01geom,
          'D3-002_C02_DIMXPERT_IDENTITY_H7_AND_GEOMETRY':c02 and c02geom,
          'D3-003_C09_NATIVE_MATERIAL':c09,
          'D3-004_ANNOTATION_VIEW_IDENTITY_C01':bool(c01v),
          'D3-005_ANNOTATION_VIEW_IDENTITY_C02':bool(c02v),
          'D3-006_L1_SAVE_CLOSE_REOPEN':l1,
          'D3-007_L2_FORCE_REBUILD':l2,
          'D3-008_SOURCE_FILE_SHA_INVARIANT':src,
          'D3-009_AUTHORIZED_SCOPE_CONTAINS_C01_C02_C09':{'C01.DATUM_A','C02.DIAMETER_FIT','C09.MATERIAL'}.issubset(authorized),
        }
        blocking=[k for k,v in checks.items() if not v]
        l3='PENDING_NO_QUALIFIED_PERTURBATION_RECIPE'
        if blocking: status='HOLD_D3_EXEMPLAR'
        else: status='PASS_D3_EXEMPLAR_L1_L2__L3_REQUIRED_FOR_RELEASE'
        warnings=['D3 L3 perturb/restore is intentionally not auto-run until a controlled benign-perturbation recipe names a real P007 parameter and allowed delta. Release-native D3 remains HOLD on L3.']
        payload={
          'schema':'k01.d3.authoring_verify.current.v15','generated_utc':datetime.now(timezone.utc).isoformat(),'status':status,
          'part':'K01-P-007','drawing':'K01-D-006','workspace_part':str(part),'workspace_drawing':str(drawing),
          'checks':checks,'blocking_checks':blocking,'warnings':warnings,'l3':l3,
          'annotation_view_evidence':{'C01.DATUM_A':c01v,'C02.DIAMETER_FIT':c02v},
          'geometry_evidence':{
            'C01.DATUM_A':{'face_signature':kv.get('S2_C01_FACE_SIG'),'face_count':i(kv,'S2_C01_FACE_COUNT'),'expected_geometry':c01geom},
            'C02.DIAMETER_FIT':{'feature':kv.get('S2_C02_FEATURE'),'annotation':kv.get('S2_C02_ANNOTATION'),'face_signature':kv.get('S2_C02_FACE_SIG'),'face_count':i(kv,'S2_C02_FACE_COUNT'),'nominal_mm':kv.get('S2_C02_MM'),'tol_type':kv.get('S2_C02_TOLTYPE'),'hole_fit':kv.get('S2_C02_HOLE'),'shaft_fit':kv.get('S2_C02_SHAFT'),'expected_geometry':c02geom},
          },
          'rebuild_invariance':{'L1_save_reopen':l1,'L2_force_rebuild':l2,'L3_perturb_restore':l3,'source_sha_invariant':src,'geometry_fingerprint_before':kv.get('S0_GEOM_FP'),'geometry_fingerprint_reopen':kv.get('S1_GEOM_FP'),'geometry_fingerprint_rebuild':kv.get('S2_GEOM_FP')},
          'material_readback':kv.get('S2_MATERIAL'),'raw_report':str(RAW.relative_to(ROOT)),
          'release_boundary':'D3 exemplar can pass L1/L2 while release-native D3 remains HOLD until L3 controlled perturb/restore passes.'
        }
        dump(OUT,payload);dump(CTRL,{'schema':'k01.d3.gate.current.v15','status':status,'blocking_checks':blocking,'l3':l3,'report':str(OUT.relative_to(ROOT)),'next':'Run D7 exemplar QA if D3 L1/L2 passes. Define and authorize a real L3 perturbation recipe before release-native D3.'})
        br=register_build(ROOT,'K01.DRAWING.D006.D3.AUTHORING_VERIFY','tools/medtas/drawing_d3_verify_v15.py + K01P007D3VerifyV15.cs',limitations=warnings,extra={'workspace_part':str(part),'annotation_views':payload['annotation_view_evidence']})
        register_verify(ROOT,'K01.DRAWING.D006.D3.AUTHORING_VERIFY','PASS_WITH_LIMITATIONS' if not blocking else 'HOLD',metrics={'C01':c01,'C02':c02,'C09_material':c09,'L1':l1,'L2':l2,'L3':'PENDING'},limitations=warnings)
        print('STATUS:',status);print('BLOCKING_CHECKS:',','.join(blocking) if blocking else 'NONE');print('C01 ANNOTATION VIEW:',c01v or 'MISSING');print('C02 ANNOTATION VIEW:',c02v or 'MISSING');print('L1:',l1,'L2:',l2,'L3:',l3);print('MATERIAL:',c09,kv.get('S2_MATERIAL',''));print('REPORT:',OUT);print('MEDTAS_STATE_HASH:',br['built_state_hash'])
        return 0 if not blocking else 3
    except Exception as e:
        dump(CTRL,{'schema':'k01.d3.gate.current.v15','status':status,'error':repr(e)});print('STATUS:',status);print('ERROR:',repr(e));print('REPORT:',CTRL);return 2
if __name__=='__main__': raise SystemExit(main())
