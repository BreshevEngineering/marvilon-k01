from __future__ import annotations
import argparse,json,re
from pathlib import Path
from medtas_v16_common import load,dump,register_build,register_verify
FORBIDDEN=('GATE','CANDIDATE','VERIFY','VERIFICATION','SERVICE_CANDIDATE','FINAL','CURRENT','FROZEN','REFERENCE')
EXTS={'.sldprt':'PART','.sldasm':'ASSEMBLY','.slddrw':'DRAWING'}

def slug(s):
    s=re.sub(r'[^A-Za-z0-9]+','_',str(s or '').strip()).strip('_')
    return s or 'Unnamed'

def canonical(partno,desc,ext): return f'{partno}_{slug(desc)}{ext.upper()}'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    policy=load(r/'control/identity/K01_IDENTITY_POLICY_v1_9.json',{}) or {};entities=load(r/'control/identity/entities.json',{}) or {};parts=load(r/'control/product/parts.json',{}) or {};cad=load(r/'reports/medtas/cad/current/K01_CAD_SEM_A001.json',{}) or {}
    items=parts.get('items',{}) or {};rows=[];seen={}
    # Assembly identity is audited separately from part documents.
    apath=str(cad.get('source_assembly') or cad.get('assembly_path') or cad.get('assembly',{}).get('source_path') or '')
    if apath:
        ent=(entities.get('entities') or {}).get('K01-A-001',{}); name=Path(apath).name; expected=ent.get('canonical_filename')
        tokens=[t for t in FORBIDDEN if t in name.upper()];state='PASS' if expected and name.lower()==expected.lower() and not tokens else 'MIGRATION_REQUIRED'
        rows.append({'part_number':'K01-A-001','current_name':name,'current_path':apath,'expected_canonical_name':expected,'forbidden_tokens':tokens,'status':state,'note':'Assembly identity audit; no rename is performed.'})
    # Audit canonical CAD semantic documents first because this is the reference-safe project view.
    for d in cad.get('documents',[]) or []:
        docid=str(d.get('document_id') or '');partno=''
        m=re.search(r'(K01-[PBA]-\d{3})',docid,re.I)
        if m:partno=m.group(1).upper()
        meta=items.get(partno,{}) if partno else {}
        rawpath=str(d.get('source_path') or d.get('path') or d.get('document_path') or '')
        name=Path(rawpath).name if rawpath else docid
        ext=Path(name).suffix or '.SLDPRT'
        expected=canonical(partno,meta.get('description') or docid,ext) if partno else None
        tokens=[t for t in FORBIDDEN if t in name.upper()]
        state='PASS' if expected and name.lower()==expected.lower() and not tokens else 'MIGRATION_REQUIRED'
        rows.append({'part_number':partno or None,'current_name':name,'current_path':rawpath or None,'expected_canonical_name':expected,'forbidden_tokens':tokens,'status':state,'note':'No rename is performed by audit.'})
        if partno:seen.setdefault(partno,[]).append(name)
    duplicates={k:v for k,v in seen.items() if len(set(x.lower() for x in v))>1}
    migration=[x for x in rows if x['status']!='PASS']
    payload={'schema':'k01.identity_audit.v1_9','policy':policy,'status':'PASS' if rows and not migration and not duplicates else 'HOLD_MIGRATION_REQUIRED','documents_audited':len(rows),'migration_count':len(migration),'duplicate_identity_count':len(duplicates),'duplicate_identities':duplicates,'migration_plan':migration,'rules':{'bulk_rename':'PROHIBITED','execution':'Use a reference-safe SOLIDWORKS rename/replace workflow, verify A001 opens with zero missing references, then recompute CAD semantic STATE_HASH.'}}
    out=r/'reports/control/K01_IDENTITY_AUDIT_CURRENT.json';dump(out,payload);register_build(r,'K01.IDENTITY.AUDIT',{'tool':'audit_identity_v1_9.py'});register_verify(r,'K01.IDENTITY.AUDIT','PASS' if payload['status']=='PASS' else 'HOLD',metrics={'documents':len(rows),'migration':len(migration),'duplicates':len(duplicates)},limitations=[] if payload['status']=='PASS' else ['Identity migration required before immutable release baseline']);print('Identity audit:',payload['status'],'documents=',len(rows),'migration=',len(migration),'duplicates=',len(duplicates));print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
