from __future__ import annotations
import argparse, json
from pathlib import Path

CONTROL_REL='reports/control/K01_DRAWING_CONTROL_CURRENT.json'
REGISTRY_REL='control/drawings/K01_DRAWING_REGISTRY_CURRENT.json'


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',default='.')
    a=ap.parse_args()
    root=Path(a.repo_root).resolve()
    p=root/'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json'
    if not p.is_file():
        print('STATUS: HOLD_DRAWING_SYSTEM_V1_DISCOVERY')
        print('ERROR: canonical pointer missing:',p)
        return 2
    d=load_json(p)
    required=[]
    for rel in d.get('canonical_read_order',[]):
        if '<drawing_id>' not in rel: required.append(rel)
    for rel in (d.get('implementation') or {}).values():
        if isinstance(rel,str): required.append(rel)
    required.extend([REGISTRY_REL,CONTROL_REL])
    missing=[r for r in dict.fromkeys(required) if not (root/r).exists()]

    print('SYSTEM CAPABILITY STATUS:',d.get('status'))
    print('POINTER:',p)
    print('ENGINE:',(d.get('implementation') or {}).get('solidworks_engine'))
    print('ORCHESTRATOR:',(d.get('implementation') or {}).get('orchestrator'))
    print('LIFECYCLE:',(d.get('implementation') or {}).get('candidate_lifecycle'))
    print('PLACEMENT CAPTURE:',(d.get('implementation') or {}).get('placement_capture'))
    print('PRESENTATION AUDIT:',(d.get('implementation') or {}).get('presentation_audit'))
    print('D003 ENGINE VALIDATION:',((d.get('validation') or {}).get('D003') or {}).get('generic_engine_semantic_build'))
    print('D006 ENGINE VALIDATION:',((d.get('validation') or {}).get('D006') or {}).get('generic_engine'))
    lc=(d.get('validation') or {}).get('candidate_lifecycle') or {}
    print('PLACEMENT ROUNDTRIP:',lc.get('placement_capture_runtime'),'/',lc.get('placement_replay_runtime'))
    status=d.get('status') or ''
    if 'MANUAL_VISUAL_FINISH_DEFAULT' in status:
        presentation_phase='EXPERIMENTAL_DEFERRED__MANUAL_FINISH_DEFAULT'
    elif 'PRESENTATION_ENGINE_PHASE_A' in status:
        presentation_phase='PHASE_A_RUNTIME_PENDING'
    else:
        presentation_phase='NOT_ACTIVE'
    print('PRESENTATION PHASE:',presentation_phase)

    ctl_path=root/CONTROL_REL
    if ctl_path.is_file():
        try:
            c=load_json(ctl_path); sm=c.get('summary') or {}
            print('DRAWING CONTROL:',c.get('status'),'| drawings=',sm.get('drawing_count'),'| candidates=',sm.get('candidate_count'),'| holds=',sm.get('hold_count'))
            print('CURRENT ROOT:',sm.get('navigation_root'))
            for did,row in sorted((c.get('drawings') or {}).items()):
                bits=[f"runtime={row.get('status','OPEN')}"]
                if row.get('semantic_status'): bits.append(f"semantic={row.get('semantic_status')}")
                if row.get('latest_candidate'): bits.append(f"candidate={row.get('latest_candidate')}")
                print(f"  {did}: "+' | '.join(bits))
        except Exception as e:
            print('DRAWING CONTROL: HOLD_READ',repr(e))
            return 2
    else:
        print('DRAWING CONTROL: MISSING — run RUN_K01_DRAWING_CONTROL_REFRESH_V1.cmd')
        return 2

    if missing:
        print('DISCOVERY FILES: HOLD')
        for r in missing: print('  MISSING:',r)
        return 2
    print('DISCOVERY FILES: PASS')
    if (c.get('summary') or {}).get('hold_count'):
        print('NEXT VALIDATION: close upstream Product Definition/readiness for held drawings; do not rebuild them and do not expand Drawing System features.')
    else:
        print('NEXT VALIDATION:',d.get('next_validation','Use validated semantic engine; manual visual finish default.'))
    print('NEW CHAT: run `run.cmd handoff`, upload K01_AI_HANDOFF_CURRENT.zip, then read K01_START_HERE -> K01_DRAWING_SYSTEM_CURRENT.json -> K01_DRAWING_REGISTRY_CURRENT.json -> K01_DRAWING_CONTROL_CURRENT.json. Live drawing state comes from Drawing Control.')
    return 0

if __name__=='__main__': raise SystemExit(main())
