from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import sys


def load(p: Path):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def task_map(d1):
    return {x.get('claim_id'): x for x in d1.get('tasks', []) if isinstance(x, dict) and x.get('claim_id')}


def main():
    ap = argparse.ArgumentParser(description='Explicitly requalify the SAME V12 exemplar to the current D1 plan without CAD mutation.')
    ap.add_argument('--repo-root', required=True)
    a = ap.parse_args()
    root = Path(a.repo_root).resolve()
    ws_p = root/'reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json'
    d1_p = root/'reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json'
    pol_p = root/'control/drawings/K01_D006_EXEMPLAR_POLICY_CURRENT.json'
    pd_p = root/'control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json'
    for p in (ws_p,d1_p,pol_p,pd_p):
        if not p.is_file():
            raise RuntimeError(f'missing input: {p.relative_to(root)}')
    ws,d1,pol,pd = map(load,(ws_p,d1_p,pol_p,pd_p))
    old_pin = ws.get('d1_plan_sha256')
    new_pin = d1.get('authoring_plan_sha256')
    frozen = list(ws.get('d2_authorizable_claim_ids') or [])
    current = list(d1.get('d2_authorizable_claim_ids') or [])
    expected = list((pol.get('d2_authoring_scope') or {}).get('expected_now') or [])
    tm = task_map(d1)
    checks = {
        'RQ-001_SAME_WORKSPACE_IDENTITY': ws.get('part')=='K01-P-007' and ws.get('drawing')=='K01-D-006',
        'RQ-002_ORIGINAL_PIN_PRESERVED': bool(old_pin),
        'RQ-003_CURRENT_D1_PIN_PRESENT': bool(new_pin),
        'RQ-004_FROZEN_SCOPE_EQUALS_CURRENT_SCOPE': set(frozen)==set(current),
        'RQ-005_SCOPE_EQUALS_EXEMPLAR_POLICY': set(current)==set(expected)=={'C01.DATUM_A','C02.DIAMETER_FIT','C09.MATERIAL'},
        'RQ-006_C01_STILL_CONTROLLED_DATUM': (tm.get('C01.DATUM_A') or {}).get('resolved_claim_values',{}).get('nominal_or_requirement.datum')=='A',
        'RQ-007_C01_ROLE_STILL_LONGITUDINAL': (tm.get('C01.DATUM_A') or {}).get('annotation_view_role')=='AV_J2_LONGITUDINAL',
        'RQ-008_C02_STILL_14P10_H7': (tm.get('C02.DIAMETER_FIT') or {}).get('resolved_claim_values',{}).get('nominal_or_requirement.diameter_mm')==14.1 and (tm.get('C02.DIAMETER_FIT') or {}).get('resolved_claim_values',{}).get('variation_semantics.diameter_fit')=='H7',
        'RQ-009_C09_STILL_316L_14404': (tm.get('C09.MATERIAL') or {}).get('resolved_claim_values',{}).get('nominal_or_requirement.material')=='AISI 316L / EN 1.4404',
        'RQ-010_NO_SCOPE_EXPANSION': set(current).issubset(set(frozen)),
    }
    blockers=[k for k,v in checks.items() if not v]
    status='PASS_EXEMPLAR_REQUALIFIED_TO_CURRENT_D1_FROZEN_SCOPE' if not blockers else 'HOLD_EXEMPLAR_REQUALIFICATION'
    out=root/'reports/drawing/current/K01-D-006_EXEMPLAR_REQUALIFICATION_CURRENT.json'
    payload={
        'schema':'k01.d006.exemplar_requalification.current.v17',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'status':status,
        'cad_mutated':False,
        'workspace':str(ws_p.relative_to(root)),
        'original_workspace_d1_pin':old_pin,
        'current_d1_pin':new_pin,
        'frozen_authorized_claims':frozen,
        'current_authorized_claims':current,
        'checks':checks,
        'blocking_checks':blockers,
        'historical_full_d1_body_available':False,
        'requalification_basis':'The original full D1 body is not reconstructed. Requalification is explicit, not an equivalence claim: the same V12 workspace is accepted for interpretation by the current D1 only because the frozen D2 claim scope is unchanged and C01/C02/C09 controlled semantics are rechecked against current authorities.',
        'release_boundary':'Design-review exemplar requalification only. No manufacturing-release claim and no CAD write.'
    }
    dump(out,payload)
    # Register this deterministic requalification in the current MEDTAS graph when available.
    try:
        sys.path.insert(0,str(root/'tools/medtas'))
        from medtas_v16_common import register_build
        register_build(root,'K01.DRAWING.D006.EXEMPLAR.REQUALIFICATION','tools/assurance/d006_exemplar_requalify_v17.py',extra={'original_workspace_d1_pin':old_pin,'current_d1_pin':new_pin,'cad_mutated':False})
    except Exception as e:
        payload['medtas_registration_warning']=repr(e)
        dump(out,payload)
    print('REPORT:',out)
    print('STATUS:',status)
    print('ORIGINAL_D1_PIN:',old_pin)
    print('CURRENT_D1_PIN:',new_pin)
    print('BLOCKING_CHECKS:',','.join(blockers) if blockers else 'NONE')
    return 0 if not blockers else 3

if __name__=='__main__':
    raise SystemExit(main())
