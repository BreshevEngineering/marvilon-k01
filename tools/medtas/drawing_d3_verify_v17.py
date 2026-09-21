from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, math
from medtas_v16_common import register_build, register_verify
from drawing_d3_d7_v15_common import ROOT, load, dump, run, sw_running, compile_helper, parse_kv, workspace_paths

CS=ROOT/'cad_api/solidworks_2018_proven/current/K01_D3_D7_V15/K01P007D3VerifyV15.cs'  # sensor only; acceptance is V17 contract-driven below
RAW=ROOT/'reports/cad/d3_d7_v15_current/K01_P007_D3_RAW_CURRENT.txt'
OUT=ROOT/'reports/drawing/current/K01-P-007_D3_AUTHORING_VERIFY_CURRENT.json'
CTRL=ROOT/'reports/control/K01_P007_D3_AUTHORING_VERIFY_CURRENT.json'
D1=ROOT/'reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json'
PD=ROOT/'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json'
EXEC=ROOT/'control/drawings/K01_P007_D3_EXECUTION_CONTRACT_CURRENT.json'
REQUAL=ROOT/'reports/drawing/current/K01-D-006_EXEMPLAR_REQUALIFICATION_CURRENT.json'
PARTS=ROOT/'control/product/parts.json'

AUTHORITY_BINDING_CONTRACT_VERSION='K01-D3-AUTHORITY-CONTRACT-v17'
AUTHORITY_BINDING_CONTRACT_ENFORCED=True
VIEW_ROLE_CONTRACT_ENFORCED=True


def b(kv,k): return kv.get(k)=='True'
def i(kv,k):
    try:return int(kv.get(k,'0') or 0)
    except:return 0

def parse_face_sig(txt):
    out={}
    for idx,p in enumerate((txt or '').split('|')):
        if idx==0: out['surface']=p.strip()
        elif '=' in p:
            k,v=p.split('=',1)
            try: out[k]=float(v) if v else None
            except: out[k]=v
    return out

def near(a,b,tol):
    try:return a is not None and b is not None and abs(float(a)-float(b))<=tol
    except:return False

def c01_authority_member(face_sig, pd):
    face=parse_face_sig(face_sig)
    c01=next((x for x in pd.get('characteristics',[]) if isinstance(x,dict) and x.get('id')=='C01'),{})
    bind=c01.get('solidworks_binding') or pd.get('datum_A') or {}
    entities=bind.get('entities') or []
    if bind.get('binding_type')!='COMPOSITE_COPLANAR_FACE_SET' or len(entities)!=2: return False,bind
    if face.get('surface')!='plane': return False,bind
    for e in entities:
        if e.get('surface_type')!='plane': continue
        if near(face.get('PXmm'),e.get('plane_x_mm'),0.002) and near(face.get('A'),e.get('area_m2'),2e-9):
            return True,bind
    return False,bind

def material_ok(raw, contract):
    allowed=((contract.get('material_projection') or {}).get('accepted_native_library_names') or [])
    return any((raw or '').strip().lower()==str(x).strip().lower() for x in allowed)

def view_role_ok(actual, role, contract):
    rec=((contract.get('annotation_view_roles') or {}).get(role) or {})
    allowed=rec.get('allowed_standard_view_names') or []
    return rec.get('status')=='CONTROLLED_FOR_STANDARD_SW_VIEWS' and actual in allowed

def main():
    status='HOLD_D3_V17'
    try:
        if sw_running(): raise RuntimeError('Close SolidWorks before D3 so rebuild/readback is performed against saved workspace files.')
        for p in (CS,D1,PD,EXEC,REQUAL,PARTS):
            if not p.exists(): raise RuntimeError(f'missing input: {p.relative_to(ROOT)}')
        ws,part,drawing=workspace_paths(); d1=load(D1); pd=load(PD); contract=load(EXEC); rq=load(REQUAL)
        if rq.get('status')!='PASS_EXEMPLAR_REQUALIFIED_TO_CURRENT_D1_FROZEN_SCOPE' or rq.get('current_d1_pin')!=d1.get('authoring_plan_sha256'):
            raise RuntimeError('current exemplar is not explicitly requalified to current D1')
        exe=compile_helper(CS,'K01P007D3VerifyV15_SENSOR.exe',RAW.parent/'build_d3_v17')
        RAW.parent.mkdir(parents=True,exist_ok=True)
        cp=run([str(exe),'--part',str(part),'--report',str(RAW)],timeout=600)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        if not RAW.exists(): raise RuntimeError('D3 raw report missing')
        kv=parse_kv(RAW)
        l1=b(kv,'L1_SAVE_REOPEN');l2=b(kv,'L2_FORCE_REBUILD');src=b(kv,'SOURCE_SHA_INVARIANT')
        c01_present=b(kv,'S2_C01'); c02_sensor=b(kv,'S2_C02')
        c01_member,c01_bind=c01_authority_member(kv.get('S2_C01_FACE_SIG',''),pd)
        c01_face_count=i(kv,'S2_C01_FACE_COUNT')
        c01=c01_present and c01_face_count==1 and c01_member
        c02=c02_sensor and b(kv,'S2_C02_H7') and b(kv,'S2_C02_GEOM')
        material_raw=kv.get('S2_MATERIAL',''); c09=material_ok(material_raw,contract)
        tm={x.get('claim_id'):x for x in d1.get('tasks',[]) if isinstance(x,dict)}
        role1=(tm.get('C01.DATUM_A') or {}).get('annotation_view_role'); role2=(tm.get('C02.DIAMETER_FIT') or {}).get('annotation_view_role')
        c01v=kv.get('S2_C01_VIEW','');c02v=kv.get('S2_C02_VIEW','')
        c01_view_ok=view_role_ok(c01v,role1,contract); c02_view_ok=view_role_ok(c02v,role2,contract)
        authorized=set(d1.get('d2_authorizable_claim_ids') or [])
        checks={
          'D3-000_EXEMPLAR_REQUALIFIED_TO_CURRENT_D1':True,
          'D3-001_C01_DATUM_IDENTITY_FROM_CONTROLLED_COMPOSITE_AUTHORITY':c01,
          'D3-002_C02_DIMXPERT_IDENTITY_H7_AND_GEOMETRY':c02,
          'D3-003_C09_NATIVE_MATERIAL_ALIAS_TO_CONTROLLED_AUTHORITY':c09,
          'D3-004_ANNOTATION_VIEW_ROLE_C01':c01_view_ok,
          'D3-005_ANNOTATION_VIEW_ROLE_C02':c02_view_ok,
          'D3-006_L1_SAVE_CLOSE_REOPEN':l1,
          'D3-007_L2_FORCE_REBUILD':l2,
          'D3-008_SOURCE_FILE_SHA_INVARIANT':src,
          'D3-009_AUTHORIZED_SCOPE_EXACT_C01_C02_C09':authorized=={'C01.DATUM_A','C02.DIAMETER_FIT','C09.MATERIAL'},
          'D3-010_AUTHORITY_BINDING_CONTRACT_ENFORCED':AUTHORITY_BINDING_CONTRACT_ENFORCED and c01_bind.get('binding_type')=='COMPOSITE_COPLANAR_FACE_SET',
          'D3-011_VIEW_ROLE_CONTRACT_ENFORCED':VIEW_ROLE_CONTRACT_ENFORCED and role1=='AV_J2_LONGITUDINAL' and role2=='AV_J2_LONGITUDINAL',
        }
        exemplar_nonblocking={
          'D3-004_ANNOTATION_VIEW_ROLE_C01',
          'D3-005_ANNOTATION_VIEW_ROLE_C02',
        }
        blocking=[k for k,v in checks.items() if (not v) and k not in exemplar_nonblocking]
        release_limitations=[k for k,v in checks.items() if (not v) and k in exemplar_nonblocking]
        l3='PENDING_NO_QUALIFIED_PERTURBATION_RECIPE'
        status=('HOLD_D3_EXEMPLAR' if blocking else
                'PASS_D3_EXEMPLAR_L1_L2__VIEW_ROLE_LIMITATION__L3_REQUIRED_FOR_RELEASE'
                if release_limitations else
                'PASS_D3_EXEMPLAR_L1_L2__L3_REQUIRED_FOR_RELEASE')
        warnings=[
          'D3 L3 perturb/restore is intentionally not auto-run until a controlled benign-perturbation recipe names a real P007 parameter and allowed delta. Release-native D3 remains HOLD on L3.',
          'For the first P007 drawing exemplar only, C01/C02 3D annotation-view role mismatches are evidence/release limitations, not blockers to D7 drawing semantic QA. The dimensional/geometry identity and Datum A binding remain mandatory blockers.'
        ]
        payload={
          'schema':'k01.d3.authoring_verify.current.v17','generated_utc':datetime.now(timezone.utc).isoformat(),'status':status,
          'part':'K01-P-007','drawing':'K01-D-006','workspace_part':str(part),'workspace_drawing':str(drawing),
          'authority_contract':str(EXEC.relative_to(ROOT)),'authority_contract_version':AUTHORITY_BINDING_CONTRACT_VERSION,
          'requalification':str(REQUAL.relative_to(ROOT)),'checks':checks,'blocking_checks':blocking,'release_limitations':release_limitations,'warnings':warnings,'l3':l3,
          'annotation_view_evidence':{
            'C01.DATUM_A':{'actual':c01v,'required_role':role1,'role_pass':c01_view_ok},
            'C02.DIAMETER_FIT':{'actual':c02v,'required_role':role2,'role_pass':c02_view_ok}},
          'geometry_evidence':{
            'C01.DATUM_A':{'attached_face_signature':kv.get('S2_C01_FACE_SIG'),'attached_face_count':c01_face_count,'matches_controlled_composite_member':c01_member,'authority_binding_type':c01_bind.get('binding_type'),'authority_entity_count':len(c01_bind.get('entities') or [])},
            'C02.DIAMETER_FIT':{'feature':kv.get('S2_C02_FEATURE'),'annotation':kv.get('S2_C02_ANNOTATION'),'face_signature':kv.get('S2_C02_FACE_SIG'),'face_count':i(kv,'S2_C02_FACE_COUNT'),'nominal_mm':kv.get('S2_C02_MM'),'tol_type':kv.get('S2_C02_TOLTYPE'),'hole_fit':kv.get('S2_C02_HOLE'),'shaft_fit':kv.get('S2_C02_SHAFT'),'expected_geometry':b(kv,'S2_C02_GEOM')}},
          'rebuild_invariance':{'L1_save_reopen':l1,'L2_force_rebuild':l2,'L3_perturb_restore':l3,'source_sha_invariant':src,'geometry_fingerprint_before':kv.get('S0_GEOM_FP'),'geometry_fingerprint_reopen':kv.get('S1_GEOM_FP'),'geometry_fingerprint_rebuild':kv.get('S2_GEOM_FP')},
          'material_readback':material_raw,'raw_report':str(RAW.relative_to(ROOT)),
          'sensor_note':'The V15 C# helper is retained as a read-only SW2018 sensor. V17 acceptance deliberately ignores its legacy C01 MinAxialPlaneX acceptance flag and evaluates C01 against controlled Product Definition entities in Python.',
          'release_boundary':'D3 exemplar may proceed to D7 when C01/C02/C09 identity, geometry, material, L1/L2 and source invariance pass. 3D annotation-view role mismatches remain explicit release limitations; release-native D3 also remains HOLD until L3 controlled perturb/restore passes.'}
        dump(OUT,payload);dump(CTRL,{'schema':'k01.d3.gate.current.v17','status':status,'blocking_checks':blocking,'release_limitations':release_limitations,'l3':l3,'report':str(OUT.relative_to(ROOT)),'transition_contract':'FULL_D3_GATE_PASS_REQUIRED_FOR_D7','next':'Run D7 only after the current D3 gate status is PASS_D3_EXEMPLAR_*. For this first drawing exemplar, 3D annotation-view role mismatches may remain release limitations; C01/C02/C09 identity/geometry/material plus L1/L2/source invariance remain mandatory. L1/L2 alone never authorize D7.'})
        br=register_build(ROOT,'K01.DRAWING.D006.D3.AUTHORING_VERIFY','tools/medtas/drawing_d3_verify_v17.py + V15 SW2018 sensor + controlled D3 execution contract',limitations=warnings,extra={'workspace_part':str(part),'annotation_views':payload['annotation_view_evidence'],'authority_contract':str(EXEC.relative_to(ROOT))})
        register_verify(ROOT,'K01.DRAWING.D006.D3.AUTHORING_VERIFY','PASS_WITH_LIMITATIONS' if not blocking else 'HOLD',metrics={'C01':c01,'C02':c02,'C09_material':c09,'C01_view_role':c01_view_ok,'C02_view_role':c02_view_ok,'L1':l1,'L2':l2,'L3':'PENDING'},limitations=warnings)
        print('STATUS:',status);print('BLOCKING_CHECKS:',','.join(blocking) if blocking else 'NONE');print('C01 AUTHORITY MEMBER:',c01_member,'face='+kv.get('S2_C01_FACE_SIG',''));print('C01 VIEW:',c01v or 'MISSING','required='+str(role1),'pass='+str(c01_view_ok));print('C02 VIEW:',c02v or 'MISSING','required='+str(role2),'pass='+str(c02_view_ok));print('L1:',l1,'L2:',l2,'L3:',l3);print('MATERIAL:',c09,material_raw);print('REPORT:',OUT);print('MEDTAS_STATE_HASH:',br['built_state_hash'])
        return 0 if not blocking else 3
    except Exception as e:
        dump(CTRL,{'schema':'k01.d3.gate.current.v17','status':status,'error':repr(e),'transition_contract':'FULL_D3_GATE_PASS_REQUIRED_FOR_D7'});print('STATUS:',status);print('ERROR:',repr(e));print('REPORT:',CTRL);return 2
if __name__=='__main__': raise SystemExit(main())
