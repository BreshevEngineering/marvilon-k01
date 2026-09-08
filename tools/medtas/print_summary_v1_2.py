#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root)
    p=root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'
    if not p.exists(): raise SystemExit('Derived state missing: '+str(p))
    d=load(p)['nodes']
    ids=['K01.CAD.SEM.A001','K01.SNAPSHOT.A001','K01.TOL.A001','K01.STRUCT.MODEL.P006','K01.STRUCT.SWSIM.P006','K01.STRUCT.CCX.P006','K01.STRUCT.RECON.P006','K01.FEMM.VERIFY.CURRENT','K01.DRAWING.MODEL.GATE04E','K01.DRAWING.ARTIFACT.GATE04E','K01.BOM.MODEL.A001','K01.BOM.ARTIFACT.A001','K01.VERIFY.GATE04E']
    print('\nK01 MEDTAS CURRENT STATE')
    print('-'*72)
    for nid in ids:
        if nid in d: print(f'{nid:36s} {d[nid]["state"]}')
    print('-'*72)
    cad=d.get('K01.CAD.SEM.A001',{})
    if cad:
        print('CAD STATE_HASH   :',cad.get('state_hash'))
        print('CAD ARTIFACT_HASH:',cad.get('artifact_hash'))
if __name__=='__main__': main()
