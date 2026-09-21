#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

CHECKPOINT=Path('control/project/K01_CHECKPOINT_CURRENT.json')
BASELINE=Path('control/baseline/K01_ENGINEERING_BASELINE.json')
STEP=Path('reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json')
GEOM=Path('reports/drawing/current/K01-D-006_P007_LIVE_GEOMETRY_CURRENT.json')
PLAN=Path('reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json')
PC=Path('control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json')
PMI_SCOPE=Path('control/product_definition/K01_P007_PMI_AUTHORING_SCOPE.json')
EXEMPLAR=Path('control/drawings/K01-D-006_P007_EXEMPLAR_v1_9.json')
AUTHORING=Path('control/drawings/K01_D006_AUTHORING_INPUT.json')
NEXT=Path('control/project/K01_NEXT_ACTIONS_CURRENT.json')
DECISION=Path('control/decisions/EDR-024_P007_C02_LOCATOR_DEPTH_BASELINE.json')
OUT=Path('reports/control/K01_P007_PROFESSIONAL_START_CURRENT.json')
P007=Path(r'D:\Marvilon\K01\cad\parts\K01-P-007_Hermetic_Magnetic_Can.SLDPRT')
C02_SPEC='Ø14.10 H7; female locator bore depth 2.00 mm nominal; depth tolerance OPEN'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.replace(str(t),str(p))
def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def near(a,b,t=0.002):
    try:return abs(float(a)-float(b))<=t
    except:return False
def run(cmd,root):
    cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True,errors='replace')
    if cp.stdout: print(cp.stdout,end='')
    if cp.stderr: print(cp.stderr,end='',file=sys.stderr)
    need(cp.returncode==0,'command failed rc=%d: %s'%(cp.returncode,' '.join(str(x) for x in cmd)))

def update_c02_characteristic(rows):
    found=False
    for c in rows or []:
        if c.get('id')=='C02':
            found=True
            old=c.get('candidate_spec')
            c['superseded_candidate_spec']=old if old!=C02_SPEC else c.get('superseded_candidate_spec')
            c['candidate_spec']=C02_SPEC
            c['female_locator_bore_depth_nominal_mm']=2.0
            c['depth_tolerance_status']='OPEN'
            c['nominal_p003_pilot_engagement_mm']=1.5
            c['nominal_bottom_clearance_mm']=0.5
            c['decision']='EDR-024_P007_C02_LOCATOR_DEPTH_BASELINE'
            if c.get('solidworks_binding'):
                c['historical_pre_cp_p_binding']=c.get('solidworks_binding')
                c['solidworks_binding']=None
                c['binding_status']='CANONICAL_REBIND_REQUIRED'
    need(found,'C02 characteristic missing')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    rep={'schema':'k01.p007.professional_start.v1','generated_utc':datetime.now(timezone.utc).isoformat(),'status':'RUNNING','native_CAD_mutated':False,'control_files_mutated':False}
    try:
        cp=load(root/CHECKPOINT); bl=load(root/BASELINE); st=load(root/STEP)
        need(cp.get('checkpoint_id')=='K01-CP-20260910-BASELINE-02C-PROMOTED','current checkpoint is not CP-P')
        need(str(st.get('status') or '').startswith('PASS_TO_P007_PROFESSIONAL_DIMXPERT_CANDIDATE_AUTHORING'),'P007 authoring step gate is not PASS')
        need((bl.get('cad') or {}).get('component_count')==14,'engineering baseline does not declare 14 components')
        need(P007.is_file(),'canonical P007 missing: '+str(P007))
        p007_sha=sha(P007)
        run([sys.executable,str(root/'tools/medtas/build_p007_release_front_v2_0.py'),'--repo-root',str(root)],root)
        g=load(root/GEOM); live=g.get('live_geometry') or {}
        expected={'flange_od_mm':33.0,'flange_thickness_mm':3.0,'locator_od_mm':14.1,'locator_length_mm':2.0,'clearance_hole_count':3,'clearance_hole_diameter_mm':2.9,'fastener_pcd_mm':26.5,'thin_can_od_mm':10.0,'thin_can_id_mm':9.4,'overall_length_mm':35.0}
        for k,v in expected.items():
            if k=='clearance_hole_count': need(int(live.get(k,-1))==3,'P007 live '+k+' mismatch')
            else: need(near(live.get(k),v),'P007 live %s mismatch actual=%r expected=%r'%(k,live.get(k),v))

        # Decision: canonical live female bore depth is 2.00 mm; legacy 1.70 nominal-depth candidate is superseded, but release depth tolerance remains OPEN.
        decision={
          'schema':'k01.engineering_decision.v1','id':'EDR-024_P007_C02_LOCATOR_DEPTH_BASELINE','generated_utc':datetime.now(timezone.utc).isoformat(),
          'status':'PASS_DECISION','scope':'K01-P-007 / K01-D-006 C02 female locator bore depth and Datum-B size semantics','decision':'Use the canonical native P007 female Ø14.10 H7 locator-bore depth 2.00 mm as the nominal geometry for the current engineering baseline. Supersede the legacy 1.70 mm nominal depth candidate. P003 male pilot length remains 1.50 mm, giving 0.50 mm nominal bottom clearance. The P007 bore-depth tolerance remains OPEN and shall not be invented.',
          'basis':['CP-P canonical Baseline-02C','fresh canonical CAD semantic geometry: P007 Ø14.10 cylindrical bore span 2.00 mm','controlled J2 design history: EDR-002 legacy candidate 1.70 mm / P003 male pilot 1.50 mm','REQ-K01-J2-LOC-001 requires Ø14.10 H7/g6 locating architecture and metal-face axial location but does not prescribe locator-bore depth'],
          'technical_filter':{'function':'P003 Ø14.10 g6 male pilot remains the radial locator; P007 Ø14.10 H7 female bore remains Datum-B feature','geometry':'canonical P007 contains a 2.00 mm cylindrical bore depth; P003 pilot nominal length remains 1.50 mm','fit_clearance':'nominal bottom clearance becomes 0.50 mm; positive clearance is preserved and axial location remains metal mating faces','requirements':'released J2 locating requirement controls H7/g6 pair and metal-face axial location, not the old 1.70 mm bore-depth candidate','tolerance':'bore-depth tolerance is still OPEN; worst-case non-bottoming must be proven later in the J2 tolerance stack','strength_analysis':'no native geometry is changed by this decision; current P007 structural/buckling refresh remains required on the canonical geometry','manufacturing':'2.00 mm nominal is simpler to retain than changing verified canonical CAD solely to match a legacy draft; capability and released tolerance remain OPEN','assembly_service':'larger nominal bottom clearance reduces pilot-bottoming sensitivity without changing 1.50 mm locating engagement','traceability':'EDR-024 supersedes only the 1.70 mm nominal-depth draft; it does not release the depth tolerance or drawing'},
          'material':'P007 AISI 316L / EN 1.4404 CONTROLLED; no material change',
          'native_CAD_change':False,'rejected_alternative':{'value_mm':1.70,'prior_nominal_bottom_clearance_mm':0.20,'reason':'The 1.70 mm value is a verified-candidate/design-history value but is not a released requirement; current canonical CAD is 2.00 mm. Re-machining/re-authoring native geometry solely to recover 0.20 mm nominal bottom clearance adds change/stale impact without a demonstrated functional benefit. Release tolerance/non-bottoming proof remains a separate P3 task.'}
        }
        write(root/DECISION,decision)

        pc=load(root/PC); old_pc=deepcopy(pc)
        pc['generated_utc']=datetime.now(timezone.utc).isoformat(); pc['engineering_baseline']={'assembly':str((bl.get('cad') or {}).get('assembly')),'assembly_sha256':str((bl.get('cad') or {}).get('sha256'))}
        pc['native_part']={'path':str(P007),'sha256':p007_sha,'document_title':P007.name,'semantic_document':'K01-P-007_Hermetic_Magnetic_Can'}
        pc['geometry_authority']='CANONICAL_NATIVE_SOLIDWORKS_PART_REFERENCED_BY_BASELINE_02C'
        pc['persistent_reference_state']='PRE_CP_P_BINDINGS_STALE_REBIND_REQUIRED_BEFORE_NEW_PMI_WRITE'
        if pc.get('datum_A'):
            pc['historical_pre_cp_p_datum_A']=deepcopy(pc.get('datum_A'))
            pc['datum_A']={'binding_mode':'COMPOSITE_COPLANAR_FACE_SET','binding_status':'CANONICAL_REBIND_REQUIRED','entities':[]}
        for c in pc.get('characteristics') or []:
            if c.get('id')!='C02' and c.get('solidworks_binding'):
                c['historical_pre_cp_p_binding']=c.get('solidworks_binding')
                c['solidworks_binding']=None
                c['binding_status']='CANONICAL_REBIND_REQUIRED'
        update_c02_characteristic(pc.get('characteristics'))
        pc.setdefault('authoring_policy',{})['persistent_refs_bound_to_part_sha256']=old_pc.get('native_part',{}).get('sha256')
        pc['authoring_policy']['canonical_part_sha256']=p007_sha
        pc['authoring_policy']['persistent_ref_rebind_required']=True
        write(root/PC,pc)

        ex=load(root/EXEMPLAR); update_c02_characteristic(ex.get('characteristics')); ex['updated_utc']=datetime.now(timezone.utc).isoformat(); ex['C02_decision']='EDR-024_P007_C02_LOCATOR_DEPTH_BASELINE'; write(root/EXEMPLAR,ex)

        scope=load(root/PMI_SCOPE); old_native=deepcopy(scope.get('native_part'))
        scope['generated_utc']=datetime.now(timezone.utc).isoformat(); scope['status']='HOLD_CANONICAL_PERSISTENT_REF_REBIND_REQUIRED'
        scope['native_part']={'path':str(P007),'sha256_before_write':p007_sha}
        scope['historical_pre_cp_p_native_part']=old_native
        for item in scope.get('safe_authoring_scope') or []:
            if item.get('id')=='C02': item['candidate_spec']=C02_SPEC
            if item.get('solidworks_binding'):
                item['historical_pre_cp_p_binding']=item['solidworks_binding']; item['solidworks_binding']=None; item['binding_status']='CANONICAL_REBIND_REQUIRED'
        scope['next_step']='REGENERATE_CANONICAL_PERSISTENT_REFERENCES_THEN_AUTHOR_PMI_ON_TIMESTAMPED_CANDIDATE_COPY'
        scope.setdefault('write_rules',{})['do_not_use_historical_pre_cp_p_persistent_refs']=True
        write(root/PMI_SCOPE,scope)

        au=load(root/AUTHORING); au['generated_utc']=datetime.now(timezone.utc).isoformat(); au['canonical_reconciliation_status']='PASS_C02_2P00_NOMINAL'; au['canonical_p007']={'path':str(P007),'sha256':p007_sha}; au['C02_decision']='EDR-024_P007_C02_LOCATOR_DEPTH_BASELINE'; au['persistent_reference_status']='REBIND_REQUIRED_BEFORE_NEW_PMI_WRITE'; write(root/AUTHORING,au)

        # Rebuild the derived live geometry/plan after the controlled C02 adjudication.
        run([sys.executable,str(root/'tools/medtas/build_p007_release_front_v2_0.py'),'--repo-root',str(root)],root)
        plan=load(root/PLAN)
        conflicts=[x for x in (load(root/GEOM).get('issues') or []) if 'LEGACY-DRAFT-CONFLICT:C02' in str(x)]
        need(not conflicts,'C02 conflict still present after adjudication')

        nxt=load(root/NEXT)
        nxt['current_stage']='P007_CANONICAL_GEOMETRY_RECONCILED_PERSISTENT_REF_REBIND_REQUIRED'
        nxt['last_completed']='CP-P canonical baseline is PASS. P007 C02 nominal geometry is reconciled: canonical female Ø14.10 H7 bore depth 2.00 mm, P003 male pilot 1.50 mm, nominal bottom clearance 0.50 mm. Legacy 1.70 mm depth candidate is superseded; released depth tolerance remains OPEN.'
        nxt['last_evidence']=[str(OUT).replace('\\','/'),str(DECISION).replace('\\','/'),str(GEOM).replace('\\','/'),str(PLAN).replace('\\','/')]
        nxt['current_blocker']='Pre-CP-P persistent references are bound to the old candidate path/SHA. Regenerate canonical P007 persistent references before any new PMI write.'
        nxt['next_1']='Regenerate persistent-reference bindings on canonical stable K01-P-007 for C01/C02/C04/C05 and bind C06 overall length without changing geometry.'
        nxt['next_2']='Create a timestamped candidate copy from canonical P007 and author C01/C02/C03/C04/C05/C06/C09 through native DimXpert/PMI; prove save-close-reopen persistence and geometry invariance.'
        nxt['then']='Derive a new K01-D-006 candidate from native PMI, run semantic drawing lint + visual QA, then bind inspection characteristics. C07/C08/C10/C11/C12/blind-end release items remain OPEN.'
        write(root/NEXT,nxt)

        rep.update({'status':'PASS_P007_CANONICAL_GEOMETRY_RECONCILED_READY_FOR_ENTITY_REBIND','control_files_mutated':True,'canonical_p007':{'path':str(P007),'sha256':p007_sha},'live_geometry':live,'C02':{'nominal_diameter_mm':14.1,'P007_fit':'H7','P003_fit':'g6','female_bore_depth_nominal_mm':2.0,'male_pilot_length_nominal_mm':1.5,'nominal_bottom_clearance_mm':0.5,'depth_tolerance':'OPEN','decision':str(DECISION).replace('\\','/')},'next':'CANONICAL_PERSISTENT_REFERENCE_REBIND'})
        write(root/OUT,rep)
        print('STATUS:',rep['status']); print('P007:',P007); print('P007 SHA256:',p007_sha); print('C02: P007 Ø14.10 H7 bore depth 2.00 nominal; P003 pilot 1.50; nominal bottom clearance 0.50; depth tolerance OPEN'); print('NEXT: canonical persistent-reference rebind'); print('REPORT:',root/OUT); return 0
    except Exception as e:
        rep['status']='HOLD_P007_PROFESSIONAL_START'; rep['error']=repr(e); write(root/OUT,rep); print('STATUS:',rep['status']); print('ERROR:',repr(e)); print('REPORT:',root/OUT); return 2
if __name__=='__main__': raise SystemExit(main())
