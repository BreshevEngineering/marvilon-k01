#!/usr/bin/env python3
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

IGNORE_NAMES={
 'README.txt','README_START_HERE.txt','K01_P004_PHYSICAL_EVIDENCE_PLAN_SNAPSHOT.json',
 'K01_P004_GUIDE_REPEATABILITY_CHARACTERIZATION_TEMPLATE.csv',
 'K01_P004_DIMENSIONAL_FAI_TEMPLATE.csv','K01_P004_SEAT_AXIAL_SCREEN_TEMPLATE.csv',
 'K01_P004_GUIDE_SURFACE_OBSERVATION_TEMPLATE.csv'
}

def load_json(p):
    with p.open('r',encoding='utf-8-sig') as f:return json.load(f)
def dump_json(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    front=root/'control/state/K01_COMPLETION_FRONTIER_CURRENT.json'
    if not front.is_file(): raise SystemExit('HOLD: missing Completion Frontier')
    f=load_json(front)
    blocker=(f.get('active_blocker') or {}).get('id') if isinstance(f.get('active_blocker'),dict) else f.get('active_blocker')
    if blocker!='P004-EXTERNAL-EVIDENCE-ACQUISITION':
        raise SystemExit('HOLD: evidence recovery is authorized only at P004-EXTERNAL-EVIDENCE-ACQUISITION')

    intake=root/'evidence/intake/K01-P-004_EXTERNAL_EVIDENCE'
    received=[]
    if intake.exists():
        for p in intake.rglob('*'):
            if p.is_file() and p.name not in IGNORE_NAMES:
                received.append(p.relative_to(root).as_posix())

    # Deliberately narrow: do not misclassify CAD/model/analysis reports as physical measurement evidence.
    legacy=[]
    for base in [root/'evidence',root/'reports/test']:
        if not base.exists(): continue
        for p in base.rglob('*'):
            if not p.is_file() or intake in p.parents: continue
            name=p.name.lower()
            if 'p004' in name and any(k in name for k in ('measurement','measured','fai','repeatability','as_built','as-built','physical')):
                if p.name not in IGNORE_NAMES and 'plan' not in name and 'template' not in name and 'intake' not in name:
                    legacy.append(p.relative_to(root).as_posix())

    found=bool(received or legacy)
    gaps=[
      'T-P004-01 dimensional FAI/as-built measurements',
      'T-P004-02 raw OUT/MID/IN repeatability data',
      'T-P004-03 actual seat clearance and axial-float data at ~20 C',
      'T-P004-04 guide-surface before/after observations/photos',
      'available material lot/CoC + manufacturing/stabilization + instrument traceability'
    ] if not found else []
    o={
      'schema':'k01.p004.existing_physical_evidence_recovery.current.v1',
      'generated_utc':datetime.now(timezone.utc).isoformat(),
      'status':'CANDIDATE_PHYSICAL_EVIDENCE_FOUND__REVIEW_REQUIRED' if found else 'PASS_RECOVERY_COMPLETE__NO_EXISTING_RAW_PHYSICAL_EVIDENCE_FOUND',
      'active_object':'K01-P-004','current_blocker':blocker,
      'received_intake_files':sorted(received),'legacy_candidate_files':sorted(set(legacy)),
      'physical_measurement_evidence_found':found,
      'remaining_external_gaps':gaps,
      'state_transition':'NONE','engineering_authority_change':'NONE','native_mutation':'NONE',
      'rule':'CAD nominal geometry, analysis output, plans/templates and inspection procedures are not physical measurement evidence.'
    }
    out=root/'reports/test/K01_P004_EXISTING_PHYSICAL_EVIDENCE_RECOVERY_CURRENT.json'; dump_json(out,o)
    print(o['status']); print('REPORT:',out); print('FOUND:',found); print('BLOCKER:',blocker); print('STATE_TRANSITION: NONE')
    return 0
if __name__=='__main__': raise SystemExit(main())
