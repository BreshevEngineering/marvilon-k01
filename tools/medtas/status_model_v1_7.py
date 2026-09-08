from __future__ import annotations
import json
from pathlib import Path

def load_status_model(root:Path):
    p=Path(root)/'control/medtas/v1/spec/K01_STATUS_MODEL_v1_7.json'
    return json.loads(p.read_text(encoding='utf-8-sig'))

def bucket(model,status):
    raw=str(status or '').strip().upper()
    return model.get('map',{}).get(raw,model.get('unknown_policy','MISSING'))

def selftest(model):
    errs=[]
    if model.get('unknown_policy')!='MISSING': errs.append('unknown_policy must be MISSING')
    known=model.get('map',{})
    buckets=set(model.get('buckets',{}))
    for raw,b in known.items():
        if b not in buckets: errs.append(f'{raw}: invalid bucket {b}')
    if bucket(model,'__UNRECOGNIZED_STATUS__')!='MISSING': errs.append('unknown status did not map to MISSING')
    required={'PASS','PASS_WITH_LIMITATIONS','HOLD','BLOCKED','MISSING','STALE','DRIFT','FRESH_UNVERIFIED'}
    miss=sorted(required-set(known))
    if miss: errs.append('required raw statuses missing: '+', '.join(miss))
    return errs
