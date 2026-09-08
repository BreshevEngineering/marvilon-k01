from __future__ import annotations
import argparse, shutil
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    stp=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json'
    bp=root/'control/medtas/v1/bindings/K01_BOLT_EQUIV_P006_BINDING_v1_7.json'
    legacy=root/'control/medtas/v1/bindings/K01_BOLT_EQUIV_P006_BINDING_v1_6.json'
    out=root/'reports/medtas/structural/current/K01_STRUCTURAL_BOLT_EQUIV_P006_v1_7.json'
    if not stp.exists():raise SystemExit('ERROR: structural model missing')
    st=load(stp);ref=st.get('boundary_conditions',{}).get('bolts',{})
    if not bp.exists() and legacy.exists():
        old=load(legacy); old['schema']='k01.bolt_equiv_binding.v1_7'; old['migrated_from']='control/medtas/v1/bindings/K01_BOLT_EQUIV_P006_BINDING_v1_6.json'; dump(bp,old)
    if not bp.exists():
        scaffold={'schema':'k01.bolt_equiv_binding.v1_7','status':'OPEN','reference_solidworks':ref,'calculix_representation':{'method':'OPEN','pretension_N_each':ref.get('preload_N_each'),'count':ref.get('count'),'thread':ref.get('thread'),'nominal_diameter_mm':ref.get('nominal_diameter_mm'),'load_path_entities':'OPEN','pretension_section_definition':'OPEN','contact_interaction_with_flange':'OPEN','approved_ccx_tail_fragment':''},'acceptance':{'same_count':True,'same_nominal_diameter':True,'same_pretension':True,'load_path_review_required':True},'approval':{'reviewed_by':'','decision_id':'','notes':''},'note':'Do not mark APPROVED until the CalculiX connector/pretension representation preserves the SolidWorks clamp/load path sufficiently for the intended cross-solver comparison.'}
        dump(bp,scaffold)
    b=load(bp);approved=str(b.get('status','')).upper()=='APPROVED'
    lims=[] if approved else ['CCX-BOLT-001: connector/preload equivalence is not approved for '+str(ref.get('count'))+' × '+str(ref.get('thread') or ref.get('nominal_diameter_mm'))+' @ '+str(ref.get('preload_N_each'))+' N each']
    payload={'schema':'k01.structural_bolt_equiv.p006.v1_7','status':'PASS' if approved else 'HOLD','reference_solidworks':ref,'binding':b,'limitations':lims,'next_action':'Review and approve control/medtas/v1/bindings/K01_BOLT_EQUIV_P006_BINDING_v1_7.json only after the CalculiX load-path/pretension/contact representation is defined.'}
    dump(out,payload)
    register_build(root,'K01.STRUCT.BOLT_EQUIV.P006',{'tool':'build_bolt_equiv_scaffold_v1_7.py','binding':'control/medtas/v1/bindings/K01_BOLT_EQUIV_P006_BINDING_v1_7.json'},limitations=lims)
    register_verify(root,'K01.STRUCT.BOLT_EQUIV.P006','PASS' if approved else 'HOLD',metrics={'approved':approved,'bolt_count':ref.get('count'),'thread':ref.get('thread'),'preload_N_each':ref.get('preload_N_each')},limitations=lims)
    print(payload['status'],'bolt equivalence scaffold:',out);return 0
if __name__=='__main__':raise SystemExit(main())
