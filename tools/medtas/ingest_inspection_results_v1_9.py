from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--results',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();src=Path(a.results).resolve()
    reg=load(r/'reports/inspection/current/K01_RELEASE_CHARACTERISTICS_CURRENT.json',{}) or {};chars={x['characteristic_id']:x for x in reg.get('characteristics',[]) or []};rows=[];issues=[]
    with src.open('r',encoding='utf-8-sig',newline='') as f:
        for x in csv.DictReader(f):
            cid=str(x.get('characteristic_id') or '').strip();c=chars.get(cid)
            if not c: issues.append('INSPECTION-UNKNOWN-CHAR:'+cid);rows.append({**x,'evaluation':'HOLD_UNKNOWN_CHARACTERISTIC'});continue
            # Generic ingestion does not parse candidate_spec. Numeric auto-evaluation is allowed only when structured released bounds exist.
            bounds=c.get('released_bounds')
            if not c.get('acceptance_released') or not bounds:
                ev='HOLD_ACCEPTANCE_NOT_MACHINE_RELEASED'
            else:
                try:
                    v=float(x.get('measured_value'));lo=float(bounds['lower']);hi=float(bounds['upper']);ev='PASS' if lo<=v<=hi else 'FAIL'
                except Exception:ev='HOLD_INVALID_NUMERIC_RESULT'
            rows.append({**x,'evaluation':ev})
            if ev!='PASS':issues.append(cid+':'+ev)
    payload={'schema':'k01.inspection_results.v1_9','source_file':src.name,'rows':rows,'issues':sorted(set(issues)),'verdict':'PASS' if rows and not issues else 'HOLD','principle':'Measured data are compared only against structured released acceptance. Candidate/drawing text is never parsed into acceptance silently.'}
    out=r/'reports/inspection/current/K01_INSPECTION_RESULTS_CURRENT.json';dump(out,payload);register_build(r,'K01.INSPECTION.RESULTS',{'tool':'ingest_inspection_results_v1_9.py','source':src.name});register_verify(r,'K01.INSPECTION.RESULTS',payload['verdict'],metrics={'rows':len(rows),'issues':len(payload['issues'])},limitations=payload['issues']);print('Inspection results:',payload['verdict'],'rows=',len(rows),'issues=',len(payload['issues']));print('Report:',out);return 0 if payload['verdict']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
