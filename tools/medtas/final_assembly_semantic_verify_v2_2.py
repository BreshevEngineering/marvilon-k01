"""Fail closed: inventory parity alone is not semantic equivalence."""
from pathlib import Path
import argparse
from v22_common import load,save
from build_bom_v2_2 import components
from final_assembly_promotion_v2_2 import paths,verify_target,BASE

def evaluate(r,base,raw):
    checks=[]
    def check(key,ok,detail): checks.append({'id':key,'status':'PASS' if ok else 'HOLD','detail':detail})
    src,target=paths(r,base)
    check('EXPORT',raw.get('status') in ('OK','PASS'),raw.get('status'))
    actual=str((raw.get('assembly') or {}).get('native_path','')).replace('\\','/').lower()
    check('TARGET_BINDING',actual==str(target).replace('\\','/').lower(),actual)
    receipt_errors=verify_target(r,base,target)
    check('TARGET_RECEIPT',not receipt_errors,receipt_errors)
    cc=components(raw); mates=raw.get('mates') or []
    check('COMPONENT_COUNT',len(cc)==base.get('expected_component_count'),len(cc))
    check('MATE_COUNT',len(mates)==base.get('expected_mate_count'),len(mates))
    bad=[c.get('path') or c.get('name') for c in cc if any(x in str(c.get('path') or c.get('native_path') or c.get('name')).upper() for x in ['GATE','CANDIDATE','VERIFY','REFERENCE'])]
    check('IDENTITY',not bad,bad)
    # Existing raw snapshots lack source/target hash-bound comparison of transforms,
    # configurations, mates, materials, features and face geometry. Never infer it.
    check('SEMANTIC_EQUIVALENCE',False,'OPEN: qualified before/after comparison and fresh target native hashes required; counts alone insufficient')
    return {'schema':'k01.final_assembly_semantic_verify.v2_2_repair1','status':'HOLD','checks':checks}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    binding=load(r/'control/medtas/v1/bindings/K01_CAD_SEM_A001_BINDING_v1_6.json',{}) or {}
    raw=load(r/binding.get('raw_api_output','reports/cad/current/K01_A001_SEMANTIC_RAW_API_v1_4.json'),{}) or {}
    result=evaluate(r,load(r/BASE,{}) or {},raw)
    save(r/'reports/control/K01_FINAL_ASSEMBLY_SEMANTIC_VERIFY_CURRENT.json',result)
    print(result['status']);[print(c) for c in result['checks'] if c['status']!='PASS'];return 2
if __name__=='__main__': raise SystemExit(main())
