from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

BASELINE=Path('control/repo/K01_CONTROL_NAMESPACE_BASELINE.json')
AUTHORITY=Path('control/project/K01_AUTHORITY_MAP_CURRENT.json')
REPORT=Path('reports/control/K01_CONTROL_NAMESPACE_GUARD_CURRENT.json')

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def family_key(rel):
    p=Path(rel); n=p.name
    n=re.sub(r'(?i)_V\d+(?:_\d+)*(?=_CURRENT\.)','',n)
    n=re.sub(r'(?i)_CURRENT_V\d+(?:_\d+)*(?=\.)','_CURRENT',n)
    n=re.sub(r'(?i)_V\d+(?:_\d+)*(?=\.)','',n)
    return (p.parent/n).as_posix()

def scan_files(root):
    out=[]
    for top in ('control','reports','evidence/immutable'):
        base=root/top
        if not base.exists(): continue
        for p in base.rglob('*'):
            if p.is_file(): out.append(p.relative_to(root).as_posix())
    return out

def audit(root:Path):
    root=Path(root).resolve(); violations=[]; notes=[]
    bp=root/BASELINE; ap=root/AUTHORITY
    if not bp.is_file(): return {'status':'HOLD','violations':[{'rule':'BASELINE_MISSING','path':str(BASELINE)}]}
    if not ap.is_file(): return {'status':'HOLD','violations':[{'rule':'AUTHORITY_MAP_MISSING','path':str(AUTHORITY)}]}
    baseline=load(bp); amap=load(ap); files=scan_files(root); file_set=set(files)

    # Freeze existing version-family membership: existing debt may shrink, never proliferate silently.
    groups={}
    for rel in files:
        if re.search(r'(?i)_v\d',Path(rel).name): groups.setdefault(family_key(rel),[]).append(rel)
    allowed=baseline.get('version_families') or {}
    for key,members in groups.items():
        if len(members)<=1: continue
        if key not in allowed:
            violations.append({'rule':'NEW_VERSION_FAMILY','family':key,'members':sorted(members)})
            continue
        known=set((allowed[key] or {}).get('members') or [])
        added=sorted(set(members)-known)
        if added: violations.append({'rule':'NEW_VERSION_SIBLING','family':key,'paths':added})

    # New same-format CURRENT-version conflicts are not allowed.
    cg={}
    for rel in files:
        if 'CURRENT' not in Path(rel).name.upper(): continue
        cg.setdefault((family_key(rel),Path(rel).suffix.lower()),[]).append(rel)
    known_current=baseline.get('current_conflict_families') or {}
    for (key,ext),members in cg.items():
        if len(members)<=1: continue
        known=set(known_current.get(key) or [])
        added=sorted(set(members)-known)
        if key not in known_current or added:
            violations.append({'rule':'CURRENT_CONFLICT','family':key,'extension':ext,'members':sorted(members),'new_paths':added})

    # Critical legacy siblings are frozen by content hash. Deletion is allowed; modification is not.
    for rel,expected in (baseline.get('critical_legacy_sha256') or {}).items():
        p=root/rel
        if p.is_file():
            actual=sha(p)
            if actual.lower()!=str(expected).lower():
                violations.append({'rule':'CRITICAL_LEGACY_MODIFIED','path':rel,'actual_sha256':actual,'expected_sha256':expected})

    # Critical logical families must have exactly one declared authority and only declared siblings.
    authority_rows=[]
    for ident,rec in (amap.get('control_families') or {}).items():
        authority=rec.get('authority'); glob=rec.get('glob'); legacy=set(rec.get('legacy') or [])
        row={'id':ident,'authority':authority,'authority_exists':bool(authority and authority in file_set),'legacy_present':[],'undeclared_siblings':[],'canonical_target':rec.get('canonical_target'),'migration':rec.get('migration')}
        if not row['authority_exists']:
            violations.append({'rule':'DECLARED_AUTHORITY_MISSING','family':ident,'path':authority})
        if authority in legacy:
            violations.append({'rule':'AUTHORITY_LISTED_AS_LEGACY','family':ident,'path':authority})
        if glob:
            matched={p.relative_to(root).as_posix() for p in root.glob(glob) if p.is_file()}
            row['legacy_present']=sorted(matched & legacy)
            undeclared=sorted(matched-{authority}-legacy)
            row['undeclared_siblings']=undeclared
            if undeclared: violations.append({'rule':'UNDECLARED_CRITICAL_SIBLING','family':ident,'paths':undeclared})
        authority_rows.append(row)

    debt=sum(max(0,len((x or {}).get('members') or [])-1) for x in allowed.values())
    status='PASS_WITH_DECLARED_MIGRATION_DEBT' if not violations and debt else ('PASS' if not violations else 'HOLD')
    return {
      'schema':'k01.control_namespace_guard.v1',
      'generated_utc':datetime.now(timezone.utc).isoformat(),
      'status':status,
      'violations':violations,
      'critical_authorities':authority_rows,
      'declared_version_family_count':len(allowed),
      'declared_legacy_sibling_debt':debt,
      'rule':'No implicit newest-file authority. Critical authority is explicit; existing version debt may shrink; new sibling ambiguity is blocked.'
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',default='.');ap.add_argument('--write-report',action='store_true');ap.add_argument('--ci',action='store_true');a=ap.parse_args()
    root=Path(a.repo_root).resolve(); rep=audit(root)
    if a.write_report:
        p=root/REPORT;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('REPORT:',p)
    print('control_namespace_guard:',rep['status'],'violations=',len(rep.get('violations') or []),'legacy_debt=',rep.get('declared_legacy_sibling_debt'))
    for e in rep.get('violations') or []: print('HOLD:',json.dumps(e,ensure_ascii=False))
    return 0 if str(rep.get('status','')).startswith('PASS') else 2
if __name__=='__main__': raise SystemExit(main())
