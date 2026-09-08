from __future__ import annotations
import json, os, sys
from pathlib import Path
import build_state

def main():
    repo=Path(sys.argv[1] if len(sys.argv)>1 else os.getenv('K01_REPO_ROOT',r'D:\BreshevEngineering\marvilon-k01')).resolve()
    if not (repo/'.git').exists(): print('HOLD repo missing',repo);return 2
    s=build_state.build(repo)
    checks=[]
    checks.append(('BASELINE_NAME',str(s['baseline'].get('assembly') or '').replace('\\','/').split('/')[-1]=='K01-A-001_GATE04E_P006_SERVICE_VERIFY.SLDASM'))
    checks.append(('BASELINE_SHA',s['baseline'].get('sha256')=='8059423b4fe1cb0bc384c5f7164eb92a7ad800bc0c79b2de7339f68e1d7489d4'))
    checks.append(('R01_NOT_AUTHORITY',s['baseline'].get('r01_is_authority') is False))
    checks.append(('BOM_13',s['bom']['ebom'].get('modeled_instances')==13))
    checks.append(('CHAR_REGISTRY',s['product_definition'].get('characteristic_count')==21))
    bad=[x for x in checks if not x[1]]
    for n,ok in checks: print(('PASS ' if ok else 'HOLD ')+n)
    print('baseline simulation evidence:',s['baseline'].get('simulation_evidence_count'))
    print('BOM:',s['bom']['ebom'].get('status'),'modeled=',s['bom']['ebom'].get('modeled_instances'),'rows=',s['bom']['ebom'].get('row_count'),'open=',len(s['bom']['ebom'].get('release_open_items') or []))
    print('Product definition:',s['product_definition'].get('status_counts'))
    print('Release readiness:',s['release_readiness'])
    return 3 if bad else 0
if __name__=='__main__':raise SystemExit(main())
