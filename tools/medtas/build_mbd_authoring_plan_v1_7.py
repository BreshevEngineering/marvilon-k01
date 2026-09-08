from __future__ import annotations
import argparse
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();cp=r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_7.json';mp=r/'reports/medtas/mbd/current/K01_MBD_A001_v1.json';out=r/'reports/medtas/mbd/current/K01_MBD_AUTHORING_PLAN_v1_7.json'
    c=load(cp) if cp.exists() else {'rows':[]};m=load(mp) if mp.exists() else {};rows=[];blocking=[]
    action={'ALREADY_PRESENT_IN_MBD':'VERIFY_TOLERANCE_AND_DATUM_SEMANTICS','CANDIDATE_UNIQUE':'REVIEW_NATIVE_DIMENSION_THEN_AUTHOR_DIMXPERT','GEOMETRY_CANDIDATE_UNIQUE':'REVIEW_CYLINDRICAL_FACE_THEN_AUTHOR_DIMXPERT_SIZE','AMBIGUOUS':'RESOLVE_SEMANTIC_OWNERSHIP_BEFORE_WRITE','NOT_FOUND':'AUTHOR_OR_BIND_NATIVE_FEATURE_EXPLICITLY','MANUAL_SEMANTIC_BIND_REQUIRED':'BIND_ASSEMBLY_LIMIT_MATE_OR_HARD_STOP_SEMANTICS'}
    for x in c.get('rows',[]):
        y=dict(x);y['next_action']=action.get(x.get('status'),'REVIEW');y['write_authorized']=False;rows.append(y)
        if x.get('status')!='ALREADY_PRESENT_IN_MBD':blocking.append(x.get('characteristic_id'))
    payload={'schema':'k01.mbd_authoring_plan.v1_7','status':'PASS' if not blocking else 'HOLD','mbd_coverage_status':m.get('coverage_status'),'rows':rows,'blocking_characteristics':blocking,'write_policy':'No automatic MBD write in v1.7. Each characteristic must have a unique semantic owner and a reviewed tolerance/datum definition before InsertSizeDimension/InsertDatum is enabled.','next_release_step':'Author the five controlled characteristics in native model, re-extract MBD, then drawing generation may proceed.'};dump(out,payload);register_build(r,'K01.MBD.AUTHORING.PLAN',{'tool':'build_mbd_authoring_plan_v1_7.py'});register_verify(r,'K01.MBD.AUTHORING.PLAN','PASS' if not blocking else 'HOLD',metrics={'blocking_characteristics':len(blocking),'rows':len(rows)},limitations=[] if not blocking else ['MBD-AUTHORING-OPEN:'+x for x in blocking]);print('MBD authoring plan:',out,'blocking=',len(blocking));return 0
if __name__=='__main__':raise SystemExit(main())
