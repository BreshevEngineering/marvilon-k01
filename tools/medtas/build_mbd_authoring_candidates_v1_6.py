from __future__ import annotations
import argparse
from pathlib import Path
from medtas_v16_common import load,dump,base_id

def mbd_names(mbd):
    out=set()
    for d in mbd.get('documents',[]) or []:
        pid=base_id(d.get('document_id'))
        for a in d.get('annotations',[]) or []:
            if a.get('name'):out.add((pid,str(a['name'])))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    cadp=root/'reports/medtas/cad/current/K01_CAD_SEM_A001.json';tar=root/'control/medtas/v1/bindings/K01_MBD_AUTHORING_TARGETS_v1_6.json';mbdp=root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json'
    if not cadp.exists():raise SystemExit('ERROR: canonical CAD semantic state missing')
    cad=load(cadp);targets=load(tar);mbd=load(mbdp) if mbdp.exists() else {'documents':[]};present=mbd_names(mbd)
    docs={base_id(d.get('document_id')):d for d in cad.get('documents',[]) or []};rows=[]
    for t in targets['characteristics']:
        cid=t['characteristic_id'];pid=t.get('part_no')
        if not pid:
            rows.append({**t,'status':'MANUAL_SEMANTIC_BIND_REQUIRED','candidates':[]});continue
        if (base_id(pid),cid) in present:
            rows.append({**t,'status':'ALREADY_PRESENT_IN_MBD','candidates':[]});continue
        doc=docs.get(base_id(pid));cand=[]
        if doc:
            target_m=float(t['nominal_mm'])/1000.0;tol_m=float(t.get('search_tolerance_mm',0.0005))/1000.0
            for d in doc.get('dimensions',[]) or []:
                try:v=float(d.get('system_value_SI'))
                except Exception:continue
                if abs(abs(v)-abs(target_m))<=tol_m:
                    cand.append({'full_name':d.get('full_name'),'system_value_SI':d.get('system_value_SI'),'value_mm':round(v*1000.0,9),'delta_mm':round((v-target_m)*1000.0,9)})
        status='CANDIDATE_UNIQUE' if len(cand)==1 else ('AMBIGUOUS' if len(cand)>1 else 'NOT_FOUND')
        rows.append({**t,'status':status,'candidates':cand})
    out=root/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_6.json'
    payload={'schema':'k01.mbd_authoring_candidates.v1_6','policy':'READ_ONLY. Candidate discovery never writes SOLIDWORKS and never infers a tolerance from nominal equality alone. Characteristic ownership must be reviewed before any MBD write.','rows':rows,'summary':{s:sum(1 for r in rows if r['status']==s) for s in sorted(set(r['status'] for r in rows))}}
    dump(out,payload);print('MBD authoring candidates:',out);print(payload['summary']);return 0
if __name__=='__main__':raise SystemExit(main())
