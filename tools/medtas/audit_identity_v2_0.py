from __future__ import annotations
import argparse,re
from pathlib import Path, PureWindowsPath
from medtas_v16_common import load,dump,register_build,register_verify,base_id

FORBIDDEN=('GATE','CANDIDATE','VERIFY','VERIFICATION','SERVICE_CANDIDATE','FINAL','CURRENT','FROZEN','REFERENCE')

def slug(s):
    s=re.sub(r'[^A-Za-z0-9]+','_',str(s or '').strip()).strip('_')
    return s or 'Unnamed'

def latest_raw(root:Path):
    for n in ('K01_A001_SEMANTIC_RAW_API_v1_4.json','K01_A001_SEMANTIC_RAW_API_v1_2.json'):
        p=root/'reports/cad/current'/n
        if p.exists(): return p
    return None

def canonical_part(partno,meta):
    return f"{partno}_{slug(meta.get('description') or partno)}.SLDPRT"

def classify(actual:str,expected:str):
    au=actual.upper(); tokens=[t for t in FORBIDDEN if t in au]
    if actual.lower()==expected.lower() and not tokens:
        return 'PASS',tokens
    if tokens:
        return 'STATEFUL_NAME_MIGRATION_REQUIRED',tokens
    return 'DESCRIPTION_NORMALIZATION_REQUIRED',tokens

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    policy=load(r/'control/identity/K01_IDENTITY_POLICY_v1_9.json',{}) or {}
    entities=load(r/'control/identity/entities.json',{}) or {}
    parts=load(r/'control/product/parts.json',{}) or {}; items=parts.get('items',{}) or {}
    rawp=latest_raw(r); raw=load(rawp,{}) if rawp else {}
    rows=[];seen={};limitations=[]
    # Audit actual native paths from the raw API snapshot. Canonical semantic JSON intentionally strips paths and must not be used to judge physical filenames.
    asm=(raw.get('assembly') or {}); apath=str(asm.get('native_path') or '')
    if apath:
        expected=((entities.get('entities') or {}).get('K01-A-001') or {}).get('canonical_filename') or 'K01-A-001_Calibration_Module.SLDASM'
        actual=PureWindowsPath(apath).name if '\\' in apath else Path(apath).name;state,tokens=classify(actual,expected)
        rows.append({'part_number':'K01-A-001','type':'ASSEMBLY','current_name':actual,'current_path':apath,'expected_canonical_name':expected,'forbidden_tokens':tokens,'status':state})
    else:
        limitations.append('IDENTITY-RAW-ASSEMBLY-PATH-MISSING')
    for d in raw.get('documents',[]) or []:
        path=str(d.get('native_path') or ''); title=str(d.get('title') or '')
        pid=base_id(title or path)
        if not pid.startswith('K01-'): continue
        meta=items.get(pid,{})
        expected=canonical_part(pid,meta)
        actual=(PureWindowsPath(path).name if '\\' in path else Path(path).name) if path else title
        if not actual:
            limitations.append('IDENTITY-DOCUMENT-NAME-MISSING:'+pid); continue
        state,tokens=classify(actual,expected)
        rows.append({'part_number':pid,'type':'PART','current_name':actual,'current_path':path or None,'expected_canonical_name':expected,'forbidden_tokens':tokens,'status':state})
        seen.setdefault(pid,[]).append(actual)
    duplicates={k:v for k,v in seen.items() if len(set(x.lower() for x in v))>1}
    stateful=[x for x in rows if x['status']=='STATEFUL_NAME_MIGRATION_REQUIRED']
    descriptive=[x for x in rows if x['status']=='DESCRIPTION_NORMALIZATION_REQUIRED']
    # Release-blocking identity migration is limited to lifecycle/state tokens or duplicate identities.
    # A stable legacy description may remain as an alias; renaming it only for wording is not worth reference churn.
    migrations=stateful
    verdict='PASS' if rows and not stateful and not duplicates else 'HOLD_MIGRATION_REQUIRED'
    payload={
      'schema':'k01.identity_audit.v2_0','policy':policy,'source_raw_snapshot':str(rawp.relative_to(r)).replace('\\','/') if rawp else None,
      'status':verdict,'documents_audited':len(rows),'migration_count':len(migrations),'stateful_name_migration_count':len(stateful),'description_normalization_note_count':len(descriptive),
      'duplicate_identity_count':len(duplicates),'duplicate_identities':duplicates,'migration_plan':migrations,'description_alias_notes':descriptive,'limitations':limitations,
      'rules':{
        'source_for_filename_audit':'raw CAD API snapshot native_path; canonical semantic state intentionally excludes filesystem paths',
        'bulk_rename':'PROHIBITED','rename_execution':'reference-safe SOLIDWORKS rename/replace only; reopen A001 with zero missing references, then recompute CAD semantic STATE_HASH and drawing/BOM dependency graph',
        'priority':'stateful lifecycle tokens first; descriptive normalization can be grouped into the same one-time migration before released drawings'
      }}
    out=r/'reports/control/K01_IDENTITY_AUDIT_CURRENT.json';dump(out,payload)
    try:register_build(r,'K01.IDENTITY.AUDIT',{'tool':'audit_identity_v2_0.py','source':'raw native paths'});register_verify(r,'K01.IDENTITY.AUDIT','PASS' if verdict=='PASS' else 'HOLD',metrics={'documents':len(rows),'migration':len(migrations),'stateful':len(stateful),'descriptive':len(descriptive),'duplicates':len(duplicates)},limitations=[] if verdict=='PASS' else ['One-time reference-safe filename migration remains before immutable release baseline'])
    except Exception as e: print('WARN identity record registration:',e)
    print('Identity audit:',verdict,'documents=',len(rows),'release-blocking migration=',len(migrations),'description aliases=',len(descriptive),'duplicates=',len(duplicates))
    for x in migrations: print(' -',x['status'],x['current_name'],'->',x['expected_canonical_name'])
    for x in descriptive: print('   NOTE stable description alias:',x['current_name'],'canonical wording=',x['expected_canonical_name'])
    print('Report:',out);return 0
if __name__=='__main__':raise SystemExit(main())
