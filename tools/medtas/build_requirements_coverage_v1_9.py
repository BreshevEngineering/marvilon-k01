from __future__ import annotations
import argparse, json
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify
from control_authority import require_control_family, require_domain_authority

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    reqp=require_domain_authority(r,'requirements')
    evp=require_control_family(r,'evidence_registry')
    reg=load(reqp,{}) or {}; ev=load(evp,{}) or {}
    evidence_items=ev.get('items',ev.get('evidence',[])) if isinstance(ev,dict) else []
    ev_by_id={str(x.get('evidence_id') or x.get('id')):x for x in evidence_items or []}
    file_to_ev={Path(str(f.get('path') if isinstance(f,dict) else f)).name:eid for eid,x in ev_by_id.items() for f in (x.get('files') or [])}
    rows=[];hard=[]
    for q in reg.get('requirements',[]) or []:
        qid=q['id'];refs=[];missing=[]
        for ref in q.get('evidence_ids',[]) or []:
            if ref in ev_by_id: refs.append(ref)
            elif Path(str(ref)).name in file_to_ev: refs.append(file_to_ev[Path(str(ref)).name])
            else: missing.append(ref)
        # Gate state is derived elsewhere and deliberately not inferred from a legacy state projection here.
        gate_covered=False
        lifecycle=str(q.get('lifecycle_status') or 'OPEN').upper()
        linked=bool(refs) and not missing
        definition_open=lifecycle in ('OPEN','PARTIAL','CANDIDATE')
        if definition_open and linked: coverage='OPEN_REQUIREMENT_WITH_REGISTERED_EVIDENCE'
        elif definition_open: coverage='OPEN_REQUIREMENT'
        elif linked: coverage='REGISTERED_EVIDENCE_LINKED'
        elif gate_covered: coverage='GATE_ONLY_NO_REGISTERED_EVIDENCE'
        else: coverage='UNCOVERED'
        row={**q,'coverage_status':coverage,'resolved_evidence_ids':sorted(set(refs)),'unresolved_evidence_refs':missing,'gate_covered':gate_covered,'gate_coverage_source':'NOT_EVALUATED_IN_EVIDENCE_LINKAGE_REPORT','registered_evidence_linked':linked,'definition_open':definition_open,'qualification_state':'NOT_INFERRED_FROM_LINK_ONLY'}
        rows.append(row)
        if q.get('release_blocker') and (definition_open or not linked): hard.append(qid)
    summary={'total':len(rows),'registered_evidence_linked':sum(bool(x.get('registered_evidence_linked')) for x in rows),'gate_only':sum(x['coverage_status']=='GATE_ONLY_NO_REGISTERED_EVIDENCE' for x in rows),'open':sum(bool(x.get('definition_open')) for x in rows),'uncovered':sum(x['coverage_status']=='UNCOVERED' for x in rows),'release_blockers_open_or_without_registered_evidence':len(hard),'release_blockers_without_registered_evidence':sum(1 for x in rows if x.get('release_blocker') and not x.get('registered_evidence_linked'))}
    payload={'schema':'k01.requirements.coverage.v1_9','status':'PASS' if not hard else 'HOLD','requirements':rows,'summary':summary,'release_blockers':sorted(set(hard)),'verdict':'PASS' if not hard else 'HOLD','principle':'Coverage is explicit. Registered evidence linkage is not qualification. OPEN/PARTIAL/CANDIDATE release blockers remain blockers even when supporting evidence is linked.','evidence_role_policy':'Until requirements migrate to explicit supporting_evidence_ids vs qualifying_evidence_ids, evidence_ids means registered linkage only and must not by itself clear a release blocker.'}
    out=r/'reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json';dump(out,payload);register_build(r,'K01.REQ.COVERAGE',{'tool':'build_requirements_coverage_v1_9.py'});register_verify(r,'K01.REQ.COVERAGE',payload['verdict'],metrics=payload['summary'],limitations=hard);print('Requirements coverage:',payload['verdict'],payload['summary']);print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
