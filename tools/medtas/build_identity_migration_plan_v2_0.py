from __future__ import annotations
import argparse
from pathlib import Path,PureWindowsPath
from medtas_v16_common import load,dump,register_build,register_verify

def target_path(cur,expected):
    if not cur:return None
    if '\\' in cur:
        p=PureWindowsPath(cur);return str(p.parent/expected)
    p=Path(cur);return str(p.parent/expected)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();audit=load(r/'reports/control/K01_IDENTITY_AUDIT_CURRENT.json',{}) or {};ops=[]
    for i,x in enumerate(audit.get('migration_plan',[]) or [],1):
        ops.append({'order':i,'part_number':x.get('part_number'),'current_path':x.get('current_path'),'target_path':target_path(str(x.get('current_path') or ''),x.get('expected_canonical_name')),'reason':x.get('status'),'execution_status':'NOT_EXECUTED'})
    payload={'schema':'k01.identity_migration_plan.v2_0','status':'READY_FOR_CONTROLLED_EXECUTION' if ops else 'NO_MIGRATION_REQUIRED','write_performed':False,'operations':ops,'preconditions':['Close released drawing generation until migration completes.','Use SOLIDWORKS reference-safe rename/replace, never Explorer rename.','Preserve one backup/checkpoint before migration.'],'postconditions':['A001 opens with zero missing references.','13 expected components resolve.','Mate count/state unchanged.','Recompute K01.CAD.SEM.A001 STATE_HASH.','Rerun tolerance/BOM/drawing dependency graph.','Run canonical hash qualification after no-change saves.'],'policy':'This file is a migration work order only. It never renames native CAD.'}
    out=r/'reports/control/K01_IDENTITY_MIGRATION_PLAN_CURRENT.json';dump(out,payload)
    try:
        register_build(r,'K01.IDENTITY.MIGRATION.PLAN',{'tool':'build_identity_migration_plan_v2_0.py','write_performed':False})
        register_verify(r,'K01.IDENTITY.MIGRATION.PLAN','PASS',metrics={'operations':len(ops),'status':payload['status']},limitations=[] if not ops else ['Migration plan exists; identity audit remains the release gate until operations are executed and reverified.'])
    except Exception as e: print('WARN migration plan record registration:',e)
    print('Identity migration plan:',payload['status'],'operations=',len(ops));[print(' -',x['part_number'],x['current_path'],'->',x['target_path']) for x in ops];print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
