from __future__ import annotations
import argparse,json,socket,subprocess,sys,time,urllib.error,urllib.request
from pathlib import Path

def free_port():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p

def req(url,method='GET',data=None,headers=None):
    body=None if data is None else json.dumps(data).encode('utf-8');h=headers or {}
    if body is not None:h={'Content-Type':'application/json',**h}
    r=urllib.request.Request(url,data=body,method=method,headers=h)
    try:
        with urllib.request.urlopen(r,timeout=4) as x:return x.status,dict(x.headers),x.read()
    except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();port=free_port();url=f'http://127.0.0.1:{port}';cmd=[sys.executable,str(root/'tools/medtas/center_server_v11.py'),'--repo-root',str(root),'--port',str(port),'--no-browser'];p=subprocess.Popen(cmd,cwd=str(root),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    issues=[];checks=[]
    try:
        for _ in range(40):
            try:
                st,_,_=req(url+'/api/health');
                if st==200:break
            except Exception:pass
            time.sleep(.1)
        else:raise RuntimeError('server did not become ready')
        st,_,b=req(url+'/api/health');checks.append(['health',st]);
        if st!=200:issues.append('CENTER-RUNTIME-001: health not 200')
        st,h,b=req(url+'/api/dashboard');checks.append(['dashboard',st]);
        if st!=200:issues.append('CENTER-RUNTIME-002: dashboard not 200');dash={}
        else:dash=json.loads(b.decode('utf-8'))
        et=h.get('ETag');st2,_,_=req(url+'/api/dashboard',headers={'If-None-Match':et} if et else {});checks.append(['etag',st2]);
        if et and st2!=304:issues.append('CENTER-CACHE-001: If-None-Match did not return 304')
        st,_,_=req(url+'/api/open?path=C:/Windows/System32/calc.exe');checks.append(['get_open',st]);
        if st!=404:issues.append('CENTER-GET-001: GET /api/open route is reachable')
        st,_,_=req(url+'/api/action',method='POST',data={'id':'REBUILD_MEDTAS_STATE'});checks.append(['post_no_origin',st]);
        if st!=403:issues.append('CENTER-CSRF-001: POST without Origin/CSRF was not rejected')
        token=dash.get('csrf_token','')
        headers={'Origin':url,'X-K01-CSRF':token}
        st,_,_=req(url+'/api/open',method='POST',data={'id':'DOES-NOT-EXIST','path':'C:/Windows/System32/calc.exe'},headers=headers);checks.append(['registered_id_only',st]);
        if st!=400:issues.append('CENTER-REGISTRY-001: unknown registered file id did not fail closed')
        st,_,_=req(url+'/api/action',method='POST',data={'id':'DOES-NOT-EXIST'},headers=headers);checks.append(['action_allowlist',st]);
        if st!=400:issues.append('CENTER-ACTION-001: unknown action id did not fail closed')
    except Exception as e:issues.append('CENTER-RUNTIME-EXCEPTION:'+repr(e))
    finally:
        try:p.terminate();p.wait(timeout=3)
        except Exception:
            try:p.kill()
            except Exception:pass
    verdict='PASS' if not issues else 'HOLD';out={'schema':'k01.center_server_regression.v1_7','verdict':verdict,'checks':checks,'issues':issues,'test_scope':['single-process server boots','health/dashboard','ETag 304','no side-effect GET routes','Origin+CSRF required','registered file IDs only','controlled action allowlist']};rp=root/'reports/medtas/tests/K01_CENTER_SERVER_REGRESSION_CURRENT.json';rp.parent.mkdir(parents=True,exist_ok=True);rp.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(verdict,'Command Center v11 runtime regression');[print(' -',x) for x in issues];return 0 if not issues else 1
if __name__=='__main__':raise SystemExit(main())
