from __future__ import annotations
import argparse
from pathlib import Path
from control_authority import require_control_family
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    stp=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json'
    bp=require_control_family(root,'bolt_equiv_p006_binding')
    out=root/'reports/medtas/structural/current/K01_STRUCTURAL_BOLT_EQUIV_P006_v1_7.json'
    if not stp.exists():raise SystemExit('ERROR: structural model missing')
    st=load(stp);ref=st.get('boundary_conditions',{}).get('bolts',{})
    b=load(bp);approved=str(b.get('status','')).upper()=='APPROVED'
    lims=[] if approved else ['CCX-BOLT-001: connector/preload equivalence is not approved for '+str(ref.get('count'))+' × '+str(ref.get('thread') or ref.get('nominal_diameter_mm'))+' @ '+str(ref.get('preload_N_each'))+' N each']
    payload={'schema':'k01.structural_bolt_equiv.p006.v1_7','status':'PASS' if approved else 'HOLD','reference_solidworks':ref,'binding':b,'limitations':lims,'next_action':'Review and approve the declared bolt-equivalence binding authority only after the CalculiX load-path/pretension/contact representation is defined.'}
    dump(out,payload)
    register_build(root,'K01.STRUCT.BOLT_EQUIV.P006',{'tool':'build_bolt_equiv_scaffold_v1_7.py','binding':str(bp.relative_to(root)).replace('\\','/')},limitations=lims)
    register_verify(root,'K01.STRUCT.BOLT_EQUIV.P006','PASS' if approved else 'HOLD',metrics={'approved':approved,'bolt_count':ref.get('count'),'thread':ref.get('thread'),'preload_N_each':ref.get('preload_N_each')},limitations=lims)
    print(payload['status'],'bolt equivalence scaffold:',out);return 0
if __name__=='__main__':raise SystemExit(main())
