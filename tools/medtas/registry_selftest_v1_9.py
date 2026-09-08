from __future__ import annotations
import argparse,re
from pathlib import Path
from medtas_v16_common import load
REQ=re.compile(r'^REQ-K01-[A-Z0-9-]+$')
PART=re.compile(r'^K01-[PB]-\d{3}$')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();errs=[]
    rr=load(r/'control/requirements/requirements.json',{}) or {};rows=rr.get('requirements',[]) or [];ids=[]
    for x in rows:
        q=x.get('id');ids.append(q)
        if not q or not REQ.match(str(q)):errs.append('REQ-ID:'+str(q))
        for k in ('title','statement','lifecycle_status','verification_method'):
            if x.get(k) in (None,''):errs.append(f'REQ-{q}-MISSING-{k}')
    if len(ids)!=len(set(ids)):errs.append('REQ-DUPLICATE-ID')
    pr=load(r/'control/product/parts.json',{}) or {};items=pr.get('items',{}) or []
    for key,x in items.items():
        if key!=x.get('part_number'):errs.append('PART-KEY-MISMATCH:'+key)
        if not PART.match(key):errs.append('PART-ID:'+key)
        for k in ('description','item_type','make_buy','material_authority','material_status','unit'):
            if x.get(k) in (None,''):errs.append(f'PART-{key}-MISSING-{k}')
    print('K01 registry selftest', 'PASS' if not errs else 'HOLD', 'requirements=',len(rows),'parts=',len(items),'errors=',len(errs))
    for e in errs: print(' -',e)
    return 0 if not errs else 1
if __name__=='__main__':raise SystemExit(main())
