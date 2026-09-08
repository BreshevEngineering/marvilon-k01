from __future__ import annotations
import argparse, json, mimetypes, os, threading, webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import build_state

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): print(fmt%args)
    @property
    def root(self): return self.server.repo_root
    @property
    def web(self): return self.server.web_root
    def headers_common(self,ctype):
        self.send_header('Content-Type',ctype);self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer');self.send_header('Cache-Control','no-store');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    def send_bytes(self,status,data,ctype):
        self.send_response(status); self.headers_common(ctype); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def valid_host(self):
        h=(self.headers.get('Host') or '').split(':')[0].lower(); return h in {'127.0.0.1','localhost','[::1]','::1'}
    def do_GET(self):
        if not self.valid_host(): return self.send_bytes(403,b'forbidden','text/plain; charset=utf-8')
        p=urlparse(self.path).path
        if p=='/api/state':
            s=build_state.build(self.root)
            out=self.root/'reports/center/K01_CENTER_STATE_CURRENT.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(s,indent=2,ensure_ascii=False),encoding='utf-8')
            return self.send_bytes(200,json.dumps(s,ensure_ascii=False).encode('utf-8'),'application/json; charset=utf-8')
        if p=='/api/health': return self.send_bytes(200,b'{"ok":true,"mode":"READ_ONLY","version":"1.0"}','application/json; charset=utf-8')
        rel='index.html' if p=='/' else p.lstrip('/')
        target=(self.web/rel).resolve()
        try:
            if os.path.commonpath([str(target),str(self.web.resolve())])!=str(self.web.resolve()): raise ValueError()
        except Exception: return self.send_bytes(403,b'forbidden','text/plain; charset=utf-8')
        if not target.exists() or not target.is_file(): return self.send_bytes(404,b'not found','text/plain; charset=utf-8')
        ctype=mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript','application/json'): ctype+='; charset=utf-8'
        return self.send_bytes(200,target.read_bytes(),ctype)
    def do_POST(self): return self.send_bytes(405,b'read-only center','text/plain; charset=utf-8')

class Server(ThreadingHTTPServer):
    daemon_threads=True

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--port',type=int,default=8790);ap.add_argument('--no-browser',action='store_true');a=ap.parse_args()
    repo=Path(a.repo_root).resolve(); web=Path(__file__).resolve().parent/'web'
    if not (repo/'.git').exists(): raise SystemExit('HOLD: invalid repo root '+str(repo))
    port=a.port
    while True:
        try: srv=Server(('127.0.0.1',port),Handler);break
        except OSError:
            port+=1
            if port>a.port+20: raise
    srv.repo_root=repo;srv.web_root=web
    url=f'http://127.0.0.1:{port}/'
    print('K01 Command Center 1.0 — READ ONLY')
    print('repo  =',repo);print('center=',url);print('No CAD, Git, BOM, drawing, or source writes are exposed by this server.')
    if not a.no_browser: threading.Timer(.4,lambda:webbrowser.open(url)).start()
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
if __name__=='__main__':main()
