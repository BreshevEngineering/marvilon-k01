from __future__ import annotations
import argparse, json
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    reg=load(r/'control/requirements/requirements.json',{}) or {};ev=load(r/'control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1_2.json',{}) or load(r/'control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1.json',{}) or {};cur=load(r/'reports/control/K01_CURRENT_STATE.json',{}) or load(r/'control/state/K01_CURRENT_STATE.json',{}) or {}
    evidence_items=ev.get('items',ev.get('evidence',[])) if isinstance(ev,dict) else []
    ev_by_id={str(x.get('evidence_id') or x.get('id')):x for x in evidence_items or []}
    file_to_ev={Path(str(f.get('path') if isinstance(f,dict) else f)).name:eid for eid,x in ev_by_id.items() for f in (x.get('files') or [])}
    cur_rows={x.get('id'):x for x in ((cur.get('requirements') or {}).get('rows') or [])}
    rows=[];hard=[]
    for q in reg.get('requirements',[]) or []:
        qid=q['id'];refs=[];missing=[]
        for ref in q.get('evidence_ids',[]) or []:
            if ref in ev_by_id: refs.append(ref)
            elif Path(str(ref)).name in file_to_ev: refs.append(file_to_ev[Path(str(ref)).name])
            else: missing.append(ref)
        c=cur_rows.get(qid,{})
        gate_covered=bool(c.get('covered_by_gate'))
        lifecycle=str(q.get('lifecycle_status') or 'OPEN').upper()
        if refs and not missing: coverage='EVIDENCE_LINKED'
        elif lifecycle in ('OPEN','PARTIAL','CANDIDATE'): coverage='OPEN_REQUIREMENT'
        elif gate_covered: coverage='GATE_ONLY_NO_REGISTERED_EVIDENCE'
        else: coverage='UNCOVERED'
        row={**q,'coverage_status':coverage,'resolved_evidence_ids':sorted(set(refs)),'unresolved_evidence_refs':missing,'gate_covered':gate_covered}
        rows.append(row)
        if q.get('release_blocker') and coverage!='EVIDENCE_LINKED':hard.append(qid)
    payload={'schema':'k01.requirements.coverage.v1_9','requirements':rows,'summary':{'total':len(rows),'evidence_linked':sum(x['coverage_status']=='EVIDENCE_LINKED' for x in rows),'gate_only':sum(x['coverage_status']=='GATE_ONLY_NO_REGISTERED_EVIDENCE' for x in rows),'open':sum(x['coverage_status']=='OPEN_REQUIREMENT' for x in rows),'uncovered':sum(x['coverage_status']=='UNCOVERED' for x in rows),'release_blockers_without_registered_evidence':len(hard)},'release_blockers':hard,'verdict':'PASS' if not hard else 'HOLD','principle':'Coverage is explicit. A released/gate-covered requirement is not silently treated as evidence-backed when no registered evidence is linked.'}
    out=r/'reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json';dump(out,payload);register_build(r,'K01.REQ.COVERAGE',{'tool':'build_requirements_coverage_v1_9.py'});register_verify(r,'K01.REQ.COVERAGE',payload['verdict'],metrics=payload['summary'],limitations=hard);print('Requirements coverage:',payload['verdict'],payload['summary']);print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
