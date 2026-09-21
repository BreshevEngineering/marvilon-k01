"""Loopback transport to canonical CLI. No engineering decision logic."""
import argparse,json,os,secrets,subprocess,sys,threading,time,webbrowser,io,zipfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from model import Model
from monitor import Monitor
from integration_package import collect

HERE=Path(__file__).resolve().parent
class Server(ThreadingHTTPServer):
 def __init__(self,root,port):
  super().__init__(('127.0.0.1',port),Handler);self.model=Model(root);self.token=secrets.token_urlsafe(32);self.lock=threading.Lock();self.jobs={};self.origin=f'http://127.0.0.1:{self.server_port}'
  self.monitor=Monitor({'project':root,'cad':self.model.cfg.get('cad_root')});self.handoff_ready=False
  threading.Thread(target=self.monitor.run,daemon=True).start()
 def server_close(self):
  self.monitor.stop.set()
  super().server_close()
class Handler(BaseHTTPRequestHandler):
 def send(self,code,body,ctype='application/json; charset=utf-8'):
  if not isinstance(body,bytes):body=json.dumps(body,ensure_ascii=False).encode()
  self.send_response(code);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-src 'self'; object-src 'none'; frame-ancestors 'none'");self.end_headers();self.wfile.write(body)
 def valid_host(self):return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
 def do_GET(self):
  if not self.valid_host():return self.send(403,{'error':'Invalid Host'})
  path=urlparse(self.path).path;s=self.server
  try:
   if path=='/api/activity':return self.send(200,s.monitor.state())
   if path=='/handoff-download':
    with s.lock:ready=s.handoff_ready
    if not ready:return self.send(404,{'error':'Build a successful handoff in this session first'})
    payload=(HERE.parent/'runtime/handoff/K01_AI_HANDOFF_WITH_REQUIREMENTS.zip').read_bytes()
    self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition','attachment; filename=K01_AI_HANDOFF_WITH_REQUIREMENTS.zip');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload);return
   if path=='/api/state':
    with s.lock:d=s.model.state()
    d['token']=s.token;d['handoff_available']=(s.model.root/'tools/medtas/ai_handoff_v2_0.py').is_file();d['handoff_ready']=s.handoff_ready;return self.send(200,d)
   if path=='/integration-package':
    with s.lock:payload=collect(s.model)
    self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition','attachment; filename=K01_P007_INTEGRATION.zip');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
   if path=='/diagnostics':
    with s.lock:d=s.model.state()
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as z:
     z.writestr('center_diagnostics.json',json.dumps(d,indent=2,ensure_ascii=False))
    payload=data.getvalue();self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition','attachment; filename=K01_CENTER_DIAGNOSTICS.zip');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
   if path=='/api/jobs':
    with s.lock:d=dict(s.jobs)
    return self.send(200,d)
   if path=='/artifact':
    key=parse_qs(urlparse(self.path).query).get('id',[''])[0]
    with s.lock:p=s.model.files.get(key)
    if not p:return self.send(404,{'error':'Unregistered artifact'})
    p=s.model.resolve(str(p));ext=p.suffix.lower()
    safe={'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.bmp':'image/bmp','.csv':'text/plain; charset=utf-8','.json':'application/json; charset=utf-8','.txt':'text/plain; charset=utf-8','.log':'text/plain; charset=utf-8'}
    if ext not in safe:
     data=p.read_bytes();self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Disposition','attachment');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
    return self.send(200,p.read_bytes(),safe[ext])
   name={'/':'index.html','/app.js':'app.js','/time.js':'time.js','/style.css':'style.css'}.get(path)
   if not name:return self.send(404,{'error':'Not found'})
   return self.send(200,(HERE/name).read_bytes(),{'index.html':'text/html; charset=utf-8','app.js':'application/javascript; charset=utf-8','time.js':'application/javascript; charset=utf-8','style.css':'text/css; charset=utf-8'}[name])
  except (ValueError,OSError) as e:self.send(400,{'error':str(e)})
 def do_POST(self):
  s=self.server
  if not self.valid_host() or self.headers.get('Origin')!=s.origin or self.headers.get('X-K01-Token')!=s.token:return self.send(403,{'error':'Invalid origin/token'})
  if self.path!='/api/run':return self.send(404,{'error':'Not found'})
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n<1 or n>4096:raise ValueError('Invalid request length')
   d=json.loads(self.rfile.read(n));name=d.get('command');args=s.model.cfg['commands'].get(name)
   root=s.model.root
   if name=='build-ai-handoff':
    if not (root/'tools/medtas/ai_handoff_v2_0.py').is_file():raise ValueError('Project handoff builder missing: tools/medtas/ai_handoff_v2_0.py')
    argv=[sys.executable,'-B',str(HERE/'build_ai_handoff.py')]
   else:
    if not isinstance(args,list) or not args or not all(isinstance(x,str) for x in args):raise ValueError('Command not allowed')
    argv=s.model.dispatcher_argv()+args
    if not (root/('run.cmd' if os.name=='nt' else 'tools/run.py')).is_file():raise ValueError('Canonical dispatcher missing')
   with s.lock:
    if any(j['state']=='RUNNING' for j in s.jobs.values()):return self.send(409,{'error':'A command is already running'})
    if name=='build-ai-handoff':s.handoff_ready=False
    key=secrets.token_hex(6);s.jobs[key]={'command':name,'state':'RUNNING','returncode':None,'output':''}
   threading.Thread(target=execute,args=(s,key,argv),daemon=True).start();return self.send(202,{'id':key})
  except (ValueError,TypeError) as e:return self.send(400,{'error':str(e)})
 def log_message(self,*args):pass

def execute(s,key,argv):
 env=os.environ.copy();env['PYTHONIOENCODING']='utf-8';env['K01_ROOT']=str(s.model.root)
 p=None
 try:
  # One local command; CAD/build/release are absent from the default allowlist.
  p=subprocess.Popen(argv,cwd=s.model.root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
  out,_=p.communicate(timeout=300);rc=p.returncode
 except subprocess.TimeoutExpired:
  p.kill();out,_=p.communicate();out+='\nTIMEOUT: launcher stopped; inspect child process state.';rc=2
 except OSError as e:out=str(e);rc=2
 logdir=HERE.parent/'runtime/commands';logdir.mkdir(parents=True,exist_ok=True);logpath=logdir/(key+'.log');logpath.write_text(out,encoding='utf-8')
 with s.lock:
  if s.jobs[key]['command']=='build-ai-handoff':s.handoff_ready=rc==0 and (HERE.parent/'runtime/handoff/K01_AI_HANDOFF_WITH_REQUIREMENTS.zip').is_file()
  s.jobs[key].update(state='FINISHED',returncode=rc,output=out[-60000:],log=str(logpath))

def main():
 a=argparse.ArgumentParser();a.add_argument('--repo-root',type=Path,default=HERE.parents[1]);a.add_argument('--port',type=int,default=8791);a.add_argument('--no-browser',action='store_true');o=a.parse_args()
 s=Server(o.repo_root,o.port);print('K01 Center:',s.origin,flush=True)
 if not o.no_browser:webbrowser.open(s.origin)
 try:s.serve_forever()
 except KeyboardInterrupt:pass
 finally:s.server_close()
if __name__=='__main__':main()
