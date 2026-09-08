from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();issues=[]
    html=(r/'K01_Command_Center_v11.html').read_text(encoding='utf-8')
    js=(r/'control/medtas/v1/center/assets/app_v11.js').read_text(encoding='utf-8')
    srv=(r/'tools/medtas/center_server_v11.py').read_text(encoding='utf-8')
    if 'innerHTML' in js:issues.append('CENTER-XSS-001: app_v11.js uses innerHTML')
    if re.search(r'\sonclick\s*=',html,re.I):issues.append('CENTER-XSS-002: inline onclick present')
    if 'eval(' in js or 'new Function' in js:issues.append('CENTER-XSS-003: dynamic JavaScript execution present')
    for token in ('Ø14.10','14.10','OD33','PCD26.5','26.5','L35'):
        if token in html or token in js:issues.append('CENTER-STATE-001: engineering literal embedded in presentation: '+token)
    if "path=u.path" not in srv:issues.append('CENTER-ROUTING-001: route parser not found')
    if "if path=='/api/dashboard'" not in srv:issues.append('CENTER-API-001: single dashboard GET missing')
    for route in ('/api/action','/api/open','/api/reveal','/api/handoff'):
        # Must occur only as POST dispatch and no explicit GET dispatch.
        if f"path=='{route}'" in srv.split('def do_GET',1)[1].split('def read_json',1)[0]:issues.append('CENTER-CSRF-GET-001: side-effect GET route present: '+route)
    for required in ('X-K01-CSRF','Origin rejected','CSRF token rejected','Unknown registered file id','BLOCKED_OPEN_EXT'):
        if required not in srv:issues.append('CENTER-SEC-001: missing security control marker '+required)
    sm=json.loads((r/'control/medtas/v1/spec/K01_STATUS_MODEL_v1_7.json').read_text(encoding='utf-8'))
    if sm.get('unknown_policy')!='MISSING':issues.append('CENTER-STATUS-001: unknown status policy is not MISSING')
    if 'medtasBucket' in js or re.search(r'function\s+cls\s*\(',js):issues.append('CENTER-STATUS-002: duplicate legacy status classifier detected')
    if "setInterval(refresh,15000)" not in js:issues.append('CENTER-POLL-001: expected 15-second cached dashboard poll not found')
    verdict='PASS' if not issues else 'HOLD';out={'schema':'k01.center_security_selftest.v1_7','verdict':verdict,'issues':issues,'checks':['POST-only side effects','same-origin Origin validation','CSRF header','registered-id file open/reveal','safe-root validation','generic executable/script open denial','DOM textContent/createElement rendering','single table-driven status model','no engineering literals in HTML/JS','single cached dashboard endpoint + ETag']}
    p=r/'reports/medtas/tests/K01_CENTER_SECURITY_SELFTEST_CURRENT.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(verdict,'Command Center v11 security/static self-test');[print(' -',x) for x in issues];return 0 if not issues else 1
if __name__=='__main__':raise SystemExit(main())
