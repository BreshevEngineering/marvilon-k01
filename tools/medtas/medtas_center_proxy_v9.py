#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, mimetypes, os, re, subprocess, sys, threading, time, urllib.request, urllib.error, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote

class Ctx:
    root: Path
    upstream: str|None=None
    port:int=8790

def jload(p:Path, default=None):
    try: return json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception: return default

def discover_ports(root:Path):
    ports=[]
    ps=root/'cc_server_v8.ps1'
    if ps.exists():
        txt=ps.read_text(encoding='utf-8-sig', errors='ignore')
        for m in re.finditer(r'(?:localhost|127\.0\.0\.1):([0-9]{2,5})',txt,re.I):
            p=int(m.group(1))
            if p not in ports: ports.append(p)
        for m in re.finditer(r'\b(?:Port|port)\s*=\s*([0-9]{2,5})',txt):
            p=int(m.group(1))
            if p not in ports: ports.append(p)
    for p in (8787,8765,8080,8000,8090,8777):
        if p not in ports: ports.append(p)
    return ports

def probe_upstream(ports, timeout=.35):
    for p in ports:
        if p==Ctx.port: continue
        u=f'http://127.0.0.1:{p}/api/state'
        try:
            with urllib.request.urlopen(u, timeout=timeout) as r:
                if 200 <= r.status < 300:
                    body=r.read(256)
                    if body: return f'http://127.0.0.1:{p}'
        except Exception: pass
    return None

def send_json(h, obj, status=200):
    data=json.dumps(obj,ensure_ascii=False).encode('utf-8')
    h.send_response(status); h.send_header('Content-Type','application/json; charset=utf-8'); h.send_header('Content-Length',str(len(data))); h.send_header('Cache-Control','no-store'); h.end_headers(); h.wfile.write(data)

def safe_rel(rel:str):
    p=(Ctx.root/rel).resolve()
    if Ctx.root not in p.parents and p != Ctx.root: raise ValueError('Path escapes repository root')
    return p

def run_detached(cmd, cwd=None):
    flags=0
    if os.name=='nt': flags=0x00000010  # CREATE_NEW_CONSOLE
    return subprocess.Popen(cmd,cwd=str(cwd or Ctx.root),creationflags=flags)

def medtas_payload():
    feed=jload(Ctx.root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json',{}) or {}
    der=jload(Ctx.root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',{}) or {}
    fail=jload(Ctx.root/'reports/control/K01_MEDTAS_LAST_FAILURE.json',None)
    ccx=jload(Ctx.root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json',None)
    face=jload(Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json',None)
    mbd=jload(Ctx.root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',None)
    hinv=jload(Ctx.root/'reports/medtas/tests/K01_CAD_CANONICAL_HASH_INVARIANCE_CURRENT.json',None)
    return {'ok':True,'feed':feed,'derived':der,'last_failure':fail,'calculix_preflight':ccx,'face_map':face,'mbd':mbd,'hash_invariance':hinv,'upstream':Ctx.upstream}

ACTIONS={
 'RUN_MEDTAS_PIPELINE':'03_RUN_MEDTAS_PIPELINE.cmd',
 'REBUILD_MEDTAS_STATE':'04_REBUILD_MEDTAS_CENTER.cmd',
 'RUN_CALCULIX_PREFLIGHT':'05_CALCULIX_PREFLIGHT.cmd',
 'RUN_CAD_SEM':'03_RUN_MEDTAS_CAD_SEM_A001.cmd',
 'RUN_HASH_INVARIANCE':'06_TEST_CAD_HASH_INVARIANCE.cmd',
}

class Handler(BaseHTTPRequestHandler):
    server_version='K01MEDTASProxy/9.0'
    def log_message(self,fmt,*args):
        print(time.strftime('%H:%M:%S'),fmt%args)
    def do_GET(self): self.route(False)
    def do_POST(self): self.route(True)
    def route(self, is_post):
        u=urlparse(self.path); path=u.path; q=parse_qs(u.query)
        if path in ('/','/K01_Command_Center_v9.html'):
            return self.serve_file(Ctx.root/'K01_Command_Center_v9.html','text/html; charset=utf-8')
        if path=='/api/medtas': return send_json(self,medtas_payload())
        if path=='/api/medtas/action':
            aid=(q.get('id') or [''])[0]
            if aid not in ACTIONS: return send_json(self,{'ok':False,'error':'Unknown MEDTAS action '+aid},400)
            p=Ctx.root/ACTIONS[aid]
            if not p.exists(): return send_json(self,{'ok':False,'error':'Missing command '+str(p)},404)
            try:
                run_detached(['cmd.exe','/c',str(p)],Ctx.root)
                return send_json(self,{'ok':True,'started':aid,'command':str(p)})
            except Exception as e: return send_json(self,{'ok':False,'error':str(e)},500)
        if path=='/api/medtas/open':
            rel=(q.get('path') or [''])[0]
            try:
                p=safe_rel(rel)
                if not p.exists(): return send_json(self,{'ok':False,'error':'Missing '+rel},404)
                if os.name=='nt': os.startfile(str(p))
                else: subprocess.Popen(['xdg-open',str(p)])
                return send_json(self,{'ok':True,'path':rel})
            except Exception as e: return send_json(self,{'ok':False,'error':str(e)},500)
        if path.startswith('/medtas/files/'):
            rel=path[len('/medtas/files/'):]
            try: return self.serve_file(safe_rel(rel))
            except Exception as e: return send_json(self,{'ok':False,'error':str(e)},404)
        if path.startswith('/api/'):
            if not Ctx.upstream:
                Ctx.upstream=probe_upstream(discover_ports(Ctx.root))
            if not Ctx.upstream:
                return send_json(self,{'ok':False,'error':'Legacy v8 API upstream is not reachable. Build Graph remains available.'},503)
            return self.proxy(Ctx.upstream+self.path,is_post)
        # allow harmless local repository reads only under reports/control for debugging
        if path.startswith('/reports/control/'):
            try:return self.serve_file(safe_rel(path.lstrip('/')))
            except Exception as e:return send_json(self,{'ok':False,'error':str(e)},404)
        self.send_error(404)
    def proxy(self,url,is_post):
        try:
            body=None
            if is_post:
                n=int(self.headers.get('Content-Length','0') or '0'); body=self.rfile.read(n) if n else b''
            req=urllib.request.Request(url,data=body,method='POST' if is_post else 'GET')
            if self.headers.get('Content-Type'): req.add_header('Content-Type',self.headers['Content-Type'])
            with urllib.request.urlopen(req,timeout=20) as r:
                data=r.read(); self.send_response(r.status)
                self.send_header('Content-Type',r.headers.get('Content-Type','application/json'))
                self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data=e.read(); self.send_response(e.code); self.send_header('Content-Type',e.headers.get('Content-Type','text/plain')); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
        except Exception as e: send_json(self,{'ok':False,'error':'Upstream proxy error: '+str(e)},502)
    def serve_file(self,p:Path,ctype=None):
        if not p.exists() or not p.is_file(): return self.send_error(404)
        data=p.read_bytes(); ct=ctype or mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
        self.send_response(200); self.send_header('Content-Type',ct); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(data)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); ap.add_argument('--port',type=int,default=8790); ap.add_argument('--no-browser',action='store_true'); a=ap.parse_args()
    Ctx.root=Path(a.repo_root).resolve(); Ctx.port=a.port
    Ctx.upstream=probe_upstream(discover_ports(Ctx.root))
    print('K01 MEDTAS unified center proxy')
    print('root    =',Ctx.root)
    print('upstream=',Ctx.upstream or 'NOT DETECTED (legacy tabs will show degraded until v8 server is available)')
    print('center  =',f'http://127.0.0.1:{Ctx.port}/')
    srv=ThreadingHTTPServer(('127.0.0.1',Ctx.port),Handler)
    if not a.no_browser:
        threading.Timer(.8,lambda:webbrowser.open(f'http://127.0.0.1:{Ctx.port}/')).start()
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
if __name__=='__main__': raise SystemExit(main())
