from __future__ import annotations
import argparse, hashlib, json, shutil
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_HASHES=Path('SHA256.json')
REPORT=Path('reports/control/K01_ROOT_PACKAGE_QUARANTINE_CURRENT.json')
KNOWN_TOP=['README_RU.md','TEST_RESULTS.txt','install.py','SHA256.json']
KNOWN_PREFIX='integration/'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description='Safely quarantine the legacy Center-panel install package from repository root.')
    ap.add_argument('--repo-root',default='.');ap.add_argument('--apply',action='store_true');a=ap.parse_args();root=Path(a.repo_root).resolve()
    hp=root/PACKAGE_HASHES
    if not hp.is_file():
        print('PASS: no SHA256.json package manifest at repository root; nothing to quarantine')
        return 0
    expected=json.loads(hp.read_text(encoding='utf-8-sig'))
    candidates=[];errors=[]
    for rel,exp in expected.items():
        if rel.startswith('center/panel/') or rel.startswith('tests/'):
            continue  # installed canonical/allowed trees stay in place
        if not (rel in KNOWN_TOP or rel.startswith(KNOWN_PREFIX)):
            errors.append('UNEXPECTED_MANIFEST_PATH:'+rel);continue
        p=root/rel
        if p.is_file():
            actual=sha(p)
            if actual.lower()!=str(exp).lower():errors.append('HASH_MISMATCH:'+rel)
            else:candidates.append(rel)
    integration=root/'integration'
    if integration.exists():
        listed={x for x in expected if x.startswith('integration/')}
        actual={p.relative_to(root).as_posix() for p in integration.rglob('*') if p.is_file()}
        extra=sorted(actual-listed)
        if extra: errors += ['UNLISTED_INTEGRATION_FILE:'+x for x in extra]
    if errors:
        print('HOLD: package quarantine refused');[print(' ',x) for x in errors];return 2
    # The package manifest itself is a transport/install artefact and must leave
    # repository root together with the files it authenticates. Its content was
    # already used above as the acceptance authority for the move.
    if hp.is_file():
        candidates.append(PACKAGE_HASHES.as_posix())
    candidates=list(dict.fromkeys(candidates))
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    dest=root/'reports'/'migration'/'quarantine'/('center_panel_package_'+stamp)
    rep={'schema':'k01.root_package_quarantine.v1','generated_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS_DRYRUN' if not a.apply else 'PASS_APPLIED','source_manifest':'SHA256.json','destination':str(dest),'files':[],'rule':'No bytes are deleted; manifest-verified legacy package files are relocated under non-authoritative reports/migration/quarantine.'}
    for rel in candidates:
        p=root/rel;rep['files'].append({'path':rel,'sha256':sha(p),'size':p.stat().st_size})
    if a.apply:
        for rel in candidates:
            src=root/rel;dst=dest/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(src),str(dst))
        # remove empty integration tree
        if integration.exists():
            for d in sorted([x for x in integration.rglob('*') if x.is_dir()],reverse=True):
                try:d.rmdir()
                except OSError:pass
            try:integration.rmdir()
            except OSError:pass
    out=root/REPORT;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(rep['status']);print('DEST:',dest);print('REPORT:',out);print('FILES:',len(candidates));return 0
if __name__=='__main__':raise SystemExit(main())
