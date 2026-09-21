from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path


def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(description='Close non-CAD assurance-coherence defects without changing engineering values.')
    ap.add_argument('--repo-root',required=True)
    a=ap.parse_args(); root=Path(a.repo_root).resolve()

    dep_p=root/'control/project/K01_DEPENDENCY_STATE.json'
    dep=load(dep_p)
    dep['status']='LEGACY_QUARANTINED_DO_NOT_CONSUME_AS_CURRENT_AUTHORITY'
    dep['authority']=False
    dep['superseded_by']='reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'
    dep['quarantine_note']='Compatibility/history snapshot only. Current dependency authority is Authority Map -> engineering_build_graph; current materialized state is K01_MEDTAS_DERIVED_STATE_CURRENT.json.'
    dump(dep_p,dep)

    center_p=root/'control/center/K01_CENTER_INPUT_CURRENT.json'
    center=load(center_p)
    center['dependency_state']='reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'
    center['dependency_state_legacy']='control/project/K01_DEPENDENCY_STATE.json'
    center['dependency_policy']='Consume current MEDTAS derived state only. Legacy dependency snapshot is quarantined/history-only.'
    dump(center_p,center)

    gate_p=root/'reports/control/K01_P007_D3_AUTHORING_VERIFY_CURRENT.json'
    gate=load(gate_p) if gate_p.is_file() else {'schema':'k01.d3.gate.current.v17','status':'HOLD_D3_NOT_YET_RERUN'}
    gate['next']='Run D7 only after the current D3 gate status is PASS_D3_EXEMPLAR_*. L1/L2 alone never authorize D7. Release-native D3 remains HOLD until L3 is qualified.'
    gate['transition_contract']='FULL_D3_GATE_PASS_REQUIRED_FOR_D7'
    gate['transition_contract_updated_utc']=datetime.now(timezone.utc).isoformat()
    dump(gate_p,gate)

    out=root/'reports/control/K01_ASSURANCE_RECOVERY_V17_CURRENT.json'
    dump(out,{
        'schema':'k01.assurance_recovery.current.v17',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'status':'PASS_NON_CAD_RECOVERY_WRITES',
        'cad_mutated':False,
        'changes':['legacy dependency snapshot quarantined','Center dependency source redirected to MEDTAS derived state','D3->D7 transition language fail-closed'],
        'next':'Rebuild MEDTAS derived state, rebuild handoff, then rerun assurance coherence.'
    })
    print('REPORT:',out)
    print('STATUS: PASS_NON_CAD_RECOVERY_WRITES')
    return 0
if __name__=='__main__': raise SystemExit(main())
