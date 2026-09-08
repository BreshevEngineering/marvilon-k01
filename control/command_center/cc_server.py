from __future__ import annotations
import json, os, subprocess, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = HERE / 'data'
REGISTRY = json.loads((DATA / 'K01_FILE_REGISTRY_v1.json').read_text(encoding='utf-8'))
PROFILES = json.loads((DATA / 'K01_MACHINE_PROFILES_v1.json').read_text(encoding='utf-8'))
PROFILE = PROFILES['profiles'][PROFILES['active_profile']]
CAD = Path(PROFILE['cad_root']) if PROFILE['cad_root'] != 'TBD' else None
ENTRY = {x['id']: x for x in REGISTRY['entries']}

def resolve_entry(e):
    if e['kind'] == 'repo': return REPO / Path(e['path'])
    if e['kind'] == 'cad' and CAD: return CAD / Path(e['path'])
    return None

def git(args):
    try:
        return subprocess.check_output(['git']+args,cwd=REPO,stderr=subprocess.STDOUT,text=True,timeout=5).strip()
    except Exception as ex:
        return 'ERROR: '+str(ex)

def git_state():
    st=git(['status','--porcelain=v1'])
    lines=[] if not st or st.startswith('ERROR:') else st.splitlines()
    return {'branch':git(['branch','--show-current']),'last_commit':git(['log','-1','--format=%H|%cI|%s']),
            'dirty_count':len(lines),'untracked_count':sum(1 for x in lines if x.startswith('??')),
            'status_lines':lines[:100],'origin':git(['remote','get-url','origin'])}

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self,path):
        clean=urlparse(path).path.lstrip('/')
        if not clean or clean=='index.html': return str(HERE/'K01_Command_Center_v2.html')
        return str(HERE/clean)
    def jr(self,payload,code=200):
        raw=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=='/api/files':
            rows=[]
            for e in REGISTRY['entries']:
                p=resolve_entry(e);rows.append({**e,'resolved':str(p) if p else '', 'exists':bool(p and p.exists())})
            return self.jr({'repo_root':str(REPO),'cad_root':str(CAD) if CAD else '', 'entries':rows})
        if u.path=='/api/git': return self.jr(git_state())
        if u.path in ('/api/open','/api/reveal'):
            ident=(parse_qs(u.query).get('id') or [''])[0];e=ENTRY.get(ident)
            if not e:return self.jr({'error':'unknown registry id'},404)
            p=resolve_entry(e)
            if not p or not p.exists():return self.jr({'error':'file missing','path':str(p)},404)
            target=p if u.path=='/api/open' else (p if p.is_dir() else p.parent)
            try: os.startfile(str(target));return self.jr({'ok':True,'path':str(target)})
            except Exception as ex:return self.jr({'error':str(ex),'path':str(target)},500)
        return super().do_GET()

if __name__=='__main__':
    port=8765;url=f'http://127.0.0.1:{port}/'
    print('K01 Command Center v2');print('Repo:',REPO);print('CAD:',CAD);print('URL:',url)
    webbrowser.open(url);ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
