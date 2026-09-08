#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, mimetypes, os, subprocess, sys, threading, time, webbrowser, zipfile, shutil
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

class Ctx:
    root:Path; port:int=8790

def jload(p,default=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return default

def send_json(h,obj,status=200):
    b=json.dumps(obj,ensure_ascii=False).encode('utf-8')
    h.send_response(status);h.send_header('Content-Type','application/json; charset=utf-8');h.send_header('Content-Length',str(len(b)));h.send_header('Cache-Control','no-store');h.end_headers();h.wfile.write(b)

def open_os(p:Path):
    if os.name=='nt': os.startfile(str(p))
    elif sys.platform=='darwin': subprocess.Popen(['open',str(p)])
    else: subprocess.Popen(['xdg-open',str(p)])

def state_path():
    for p in [Ctx.root/'reports/control/K01_CURRENT_STATE.json',Ctx.root/'control/state/K01_CURRENT_STATE.json',Ctx.root/'K01_CURRENT_STATE.json']:
        if p.exists(): return p
    return None

def minimal_state():
    return {'schema':'k01.center.degraded_state.v10','tasks':[],'technical_filter':{'gates':[]},'drawing_specs':[],'workpacks':{},'ready_now':[],'next_task':None,'evidence':{},'current_action':'BUILD_GRAPH'}

def load_state():
    p=state_path(); st=jload(p) if p else None
    if not isinstance(st,dict): st=minimal_state()
    # Adapt reducer-oriented K01_CURRENT_STATE into the UI contract directly.
    # This removes the legacy v8 server as a required translation layer.
    ev=st.setdefault('evidence',{})
    if st.get('bom') and not ev.get('bom'): ev['bom']=st['bom']
    if st.get('github') and not ev.get('github_remote'): ev['github_remote']=st['github']
    if 'technical_filter' not in st:
        tfp=Ctx.root/'control/technical_filter/K01_J2_C2R1_TECHNICAL_FILTER_v1.json';tf=jload(tfp,None)
        if isinstance(tf,dict) and isinstance(tf.get('gates'),list): st['technical_filter']=tf
        else:
            rows=((st.get('gates') or {}).get('rows') or [])
            st['technical_filter']={'gates':[{'gate':r.get('gate'),'status':r.get('status'),'basis':r.get('reason',''),'question':'Close '+str(r.get('gate',''))+' release evidence','verification_method':'See controlled requirement/gate evidence','evidence_ids':[],'source_ids':[],'open_actions':r.get('requirement_ids',[]) or []} for r in rows]}
    if not st.get('tasks'):
        tasks=[];wps={}
        wpdir=Ctx.root/'control/workpacks'
        if wpdir.exists():
            for fp in sorted(wpdir.glob('K01_T*.json')):
                j=jload(fp,{}) or {};tid=str(j.get('task_id') or j.get('id') or fp.stem.split('_')[1] if '_' in fp.stem else fp.stem)
                title=str(j.get('title') or j.get('name') or fp.stem);status=str(j.get('status') or 'OPEN');why=str(j.get('why') or j.get('reason') or j.get('next_action') or '')
                t={'id':tid,'name':title,'status':status,'why':why,'action':None};tasks.append(t);wps[tid]=j
        st['tasks']=tasks;st.setdefault('workpacks',wps)
    if not st.get('next_task'):
        def ispass(x):return str(x.get('status','')).upper().startswith('PASS')
        st['next_task']=next((x for x in st.get('tasks',[]) if not ispass(x)),None)
    st.setdefault('ready_now',[]);st.setdefault('drawing_specs',[]);st.setdefault('workpacks',{});st.setdefault('digital_thread',{})
    return st,p

def git_payload():
    def run(*args):
        cp=subprocess.run(['git',*args],cwd=str(Ctx.root),text=True,capture_output=True,timeout=8)
        return cp.returncode,(cp.stdout or '').strip(),(cp.stderr or '').strip()
    if not (Ctx.root/'.git').exists(): return {'ok':True,'git':{'status':'NO_REPO','branch':'—','dirty':'—','untracked':'—','last':'—','origin':'—'}}
    rc,branch,_=run('branch','--show-current'); rc2,por,_=run('status','--porcelain'); rc3,last,_=run('log','-1','--pretty=%h %ad %s','--date=iso'); rc4,origin,_=run('remote','get-url','origin')
    lines=[x for x in por.splitlines() if x]; untracked=sum(1 for x in lines if x.startswith('??'))
    return {'ok':True,'git':{'status':'PASS' if not lines else 'DIRTY','branch':branch or '—','dirty':len(lines),'untracked':untracked,'last':last or '—','origin':origin or '—','classification':None}}

def choose_assembly():
    # Reuse MEDTAS binding rather than hard-coding a path.
    bind=None
    for n in ('K01_CAD_SEM_A001_BINDING_v1_6.json','K01_CAD_SEM_A001_BINDING_v1_5.json','K01_CAD_SEM_A001_BINDING_v1_4.json'):
        p=Ctx.root/'control/medtas/v1/bindings'/n
        if p.exists(): bind=jload(p); break
    if not bind:return None
    try:
        s=bind['source_selection']; rp=Ctx.root/s['preferred_gate_verify']; j=jload(rp,{}) or {}; cand=j.get(s['preferred_gate_verify_field'])
        if cand and Path(cand).exists(): return Path(cand)
        fb=Ctx.root/s['fallback_assembly']; return fb if fb.exists() else None
    except Exception:return None

def file_entries():
    rows=[]; seen=set()
    def add(fid,domain,name,p):
        if not p:return
        p=Path(p); key=str(p).lower()
        if key in seen:return
        seen.add(key); ex=p.exists(); mt=''
        if ex:
            try:mt=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(p.stat().st_mtime))
            except Exception:pass
        rows.append({'id':fid,'domain':domain,'name':name,'exists':ex,'modified':mt,'path':str(p)})
    add('CAD-R1-ASM','CAD','Current Gate04E verification assembly',choose_assembly())
    basics=[
      ('STATE-CURRENT','Control','K01 Current State',state_path()),
      ('MEDTAS-DERIVED','MEDTAS','Derived Build Graph state',Ctx.root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json'),
      ('MEDTAS-FEED','MEDTAS','Center feed',Ctx.root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json'),
      ('MEDTAS-PIPELINE','MEDTAS','8-stage pipeline run',Ctx.root/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json'),
      ('FILTER','Control','Technical Filter',Ctx.root/'control/technical_filter/K01_J2_C2R1_TECHNICAL_FILTER_v1.json'),
      ('MBD-A001','MBD','A001 MBD / DimXpert semantic state',Ctx.root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json'),
      ('TOL-A001','Tolerance','A001 tolerance analysis',Ctx.root/'reports/medtas/tolerance/current/K01_TOLERANCE_A001_v1.json'),
      ('STRUCT-P006','Structural','P006 solver-neutral structural model',Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json'),
      ('CCX-PREFLIGHT','CalculiX','CalculiX preflight',Ctx.root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json'),
      ('CCX-MESH','CalculiX','P006 controlled quadratic mesh manifest',Ctx.root/'reports/medtas/calculix/current/K01_STRUCTURAL_MESH_P006_v1_6.json'),
      ('CCX-INPUT','CalculiX','P006 controlled CalculiX input manifest',Ctx.root/'reports/medtas/calculix/current/K01_CALCULIX_INPUT_P006_v1_6.json'),
      ('DRAW-MBD-WP','Drawing','Drawing-as-MBD release workpack',Ctx.root/'reports/medtas/drawing/current/K01_DRAWING_MBD_RELEASE_WORKPACK_v1_6.json'),
      ('MBD-CANDIDATES','MBD','MBD native dimension authoring candidates',Ctx.root/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_6.json'),
      ('FACE-MAP','Structural','Persistent structural face-role map',Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json'),
      ('NEUTRAL-GEO','Structural','P003/P007 neutral geometry manifest',Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_6.json'),
      ('BOLT-EQUIV','Structural','M2.5 preload equivalence',Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_BOLT_EQUIV_P006_v1_6.json'),
      ('BOM-CSV','BOM','Canonical BOM CSV artifact',Ctx.root/'reports/bom/current/K01_BOM_A001_CURRENT.csv'),
    ]
    for x in basics:add(*x)
    feed=jload(Ctx.root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json',{}) or {}
    for ei,e in enumerate(feed.get('evidence',[]) or []):
        for fi,f in enumerate(e.get('files',[]) or []):
            rel=f.get('path'); p=Ctx.root/rel if rel else None; add(f'EV-{ei}-{fi}','Evidence',e.get('title') or rel,p)
    return rows

def files_payload():
    return {'ok':True,'files':{'repo_root':str(Ctx.root),'cad_root':str(choose_assembly().parent if choose_assembly() else ''),'entries':file_entries()}}

def resolve_file_id(fid):
    for r in file_entries():
        if r['id']==fid:return Path(r['path'])
    return None

def medtas_payload():
    return {'ok':True,'feed':jload(Ctx.root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json',{}) or {},'derived':jload(Ctx.root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',{}) or {},'last_failure':jload(Ctx.root/'reports/control/K01_MEDTAS_LAST_FAILURE.json',None),'calculix_preflight':jload(Ctx.root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json',None),'face_map':jload(Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json',None),'mbd':jload(Ctx.root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json',None),'hash_invariance':jload(Ctx.root/'reports/medtas/tests/K01_CAD_CANONICAL_HASH_INVARIANCE_CURRENT.json',None),'pipeline_report':jload(Ctx.root/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json',None),'bolt_equiv':jload(Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_BOLT_EQUIV_P006_v1_6.json',None),'neutral_geometry':jload(Ctx.root/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_6.json',None),'mesh':jload(Ctx.root/'reports/medtas/calculix/current/K01_STRUCTURAL_MESH_P006_v1_6.json',None),'ccx_input':jload(Ctx.root/'reports/medtas/calculix/current/K01_CALCULIX_INPUT_P006_v1_6.json',None),'mbd_candidates':jload(Ctx.root/'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_6.json',None),'server_mode':'STANDALONE_V10_V16'}

MEDTAS_ACTIONS={'RUN_MEDTAS_PIPELINE':'03_RUN_MEDTAS_PIPELINE.cmd','REBUILD_MEDTAS_STATE':'04_REBUILD_MEDTAS_CENTER.cmd','RUN_CALCULIX_PREFLIGHT':'05_CALCULIX_PREFLIGHT.cmd','RUN_CAD_SEM':'03_RUN_MEDTAS_CAD_SEM_A001.cmd','RUN_HASH_INVARIANCE':'06_TEST_CAD_HASH_INVARIANCE.cmd','RUN_MBD_CANDIDATES':'09_BUILD_MBD_AUTHORING_CANDIDATES.cmd','RUN_FACE_BIND':'10_BIND_STRUCTURAL_FACE_ROLES.cmd','RUN_NEUTRAL_GEOMETRY':'11_EXPORT_STRUCTURAL_NEUTRAL_GEOMETRY.cmd','RUN_STRUCT_MESH':'12_BUILD_STRUCTURAL_MESH.cmd','RUN_BOLT_EQUIV':'12_BUILD_BOLT_EQUIV_SCAFFOLD.cmd','RUN_CCX_INPUT':'13_BUILD_CALCULIX_INPUT.cmd'}
LEGACY_ACTION_FILES={
 'RUN_CC_SELFTEST':['RUN_K01_COMMAND_CENTER_SELFTEST.ps1'],
 'CHECK_FEMM_INSTALL':['CHECK_FEMM_INSTALL.cmd','control/CHECK_FEMM_INSTALL.cmd'],
 'START_SW_BRIDGE':['START_K01_SW_BRIDGE.cmd','cad_api/START_K01_SW_BRIDGE.cmd'],
 'RUN_DRAW_V3':['RUN_K01_DRAWING_V3.cmd','drawings/RUN_K01_DRAWING_V3.cmd'],
 'RUN_DRAW_LINT':['RUN_K01_DRAWING_LINT.cmd'],
 'RUN_DRAW_VISUAL':['RUN_K01_DRAWING_VISUAL.cmd'],
 'RUN_GIT_V2':['RUN_K01_GIT_V2.cmd'],
}

def detached(path:Path):
    flags=0x00000010 if os.name=='nt' else 0
    if path.suffix.lower()=='.ps1': cmd=['powershell.exe','-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',str(path)]
    elif path.suffix.lower() in ('.cmd','.bat'): cmd=['cmd.exe','/c',str(path)]
    else: cmd=[str(path)]
    subprocess.Popen(cmd,cwd=str(Ctx.root),creationflags=flags)

def build_handoff():
    outdir=Ctx.root/'reports/ai';outdir.mkdir(parents=True,exist_ok=True); out=outdir/'K01_AI_HANDOFF_CURRENT.zip'
    candidates=[state_path(),Ctx.root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json',Ctx.root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json',Ctx.root/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json',Ctx.root/'reports/control/K01_MEDTAS_LAST_FAILURE.json']
    feed=jload(Ctx.root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json',{}) or {}
    for e in feed.get('evidence',[]) or []:
        for f in e.get('files',[]) or []:
            if f.get('path'):candidates.append(Ctx.root/f['path'])
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p in candidates:
            if p and Path(p).exists() and Path(p).is_file():
                try: arc=str(Path(p).resolve().relative_to(Ctx.root))
                except Exception: arc=Path(p).name
                z.write(p,arc)
    return out

class H(BaseHTTPRequestHandler):
    server_version='K01MEDTASStandalone/10.0'
    def log_message(self,fmt,*args):print(time.strftime('%H:%M:%S'),fmt%args)
    def do_GET(self):self.route(False)
    def do_POST(self):self.route(True)
    def route(self,post):
        u=urlparse(self.path);path=u.path;q=parse_qs(u.query)
        if path in ('/','/K01_Command_Center_v10.html'):return self.file(Ctx.root/'K01_Command_Center_v10.html','text/html; charset=utf-8')
        if path=='/api/health':return send_json(self,{'ok':True,'mode':'standalone_v10','root':str(Ctx.root)})
        if path=='/api/state':
            st,p=load_state();return send_json(self,{'ok':True,'state':st,'source':str(p) if p else 'degraded_synthetic'})
        if path=='/api/git':return send_json(self,git_payload())
        if path=='/api/files':return send_json(self,files_payload())
        if path=='/api/medtas':return send_json(self,medtas_payload())
        if path=='/api/handoff':
            try:return send_json(self,{'ok':True,'path':str(build_handoff())})
            except Exception as e:return send_json(self,{'ok':False,'error':str(e)},500)
        if path in ('/api/open','/api/reveal'):
            fid=(q.get('id') or [''])[0];p=resolve_file_id(fid)
            if not p or not p.exists():return send_json(self,{'ok':False,'error':'Unknown/missing file id '+fid},404)
            try:open_os(p.parent if path.endswith('reveal') else p);return send_json(self,{'ok':True,'path':str(p)})
            except Exception as e:return send_json(self,{'ok':False,'error':str(e)},500)
        if path=='/api/medtas/open':
            rel=(q.get('path') or [''])[0];p=(Ctx.root/rel).resolve()
            try:
                if not p.exists():return send_json(self,{'ok':False,'error':'Missing '+rel},404)
                open_os(p);return send_json(self,{'ok':True,'path':str(p)})
            except Exception as e:return send_json(self,{'ok':False,'error':str(e)},500)
        if path=='/api/medtas/action':
            aid=(q.get('id') or [''])[0];fn=MEDTAS_ACTIONS.get(aid)
            if not fn:return send_json(self,{'ok':False,'error':'Unknown MEDTAS action '+aid},400)
            p=Ctx.root/fn
            if not p.exists():return send_json(self,{'ok':False,'error':'Missing command '+str(p)},404)
            try:detached(p);return send_json(self,{'ok':True,'started':aid})
            except Exception as e:return send_json(self,{'ok':False,'error':str(e)},500)
        if path=='/api/action':
            aid=(q.get('id') or [''])[0]
            if aid=='OPEN_FILTER':
                p=Ctx.root/'control/technical_filter/K01_J2_C2R1_TECHNICAL_FILTER_v1.json'
                if p.exists():open_os(p);return send_json(self,{'ok':True})
            if aid=='CHECK_GITHUB_REMOTE':return send_json(self,git_payload())
            for rel in LEGACY_ACTION_FILES.get(aid,[]):
                p=Ctx.root/rel
                if p.exists():detached(p);return send_json(self,{'ok':True,'started':aid,'command':str(p)})
            return send_json(self,{'ok':False,'error':'Action '+aid+' is not mapped in standalone v10. State remains readable; add a controlled command mapping before enabling this write/action.'},409)
        if path.startswith('/reports/') or path.startswith('/control/'):
            p=(Ctx.root/path.lstrip('/')).resolve()
            if Ctx.root not in p.parents and p!=Ctx.root:return self.send_error(403)
            return self.file(p)
        return self.send_error(404)
    def file(self,p,ct=None):
        if not p.exists() or not p.is_file():return self.send_error(404)
        b=p.read_bytes();typ=ct or mimetypes.guess_type(str(p))[0] or 'application/octet-stream'
        self.send_response(200);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--port',type=int,default=8790);ap.add_argument('--no-browser',action='store_true');a=ap.parse_args();Ctx.root=Path(a.repo_root).resolve();Ctx.port=a.port
    print('K01 MEDTAS Command Center v10 - standalone single-process server');print('root  =',Ctx.root);print('legacy v8 upstream: NOT REQUIRED')
    srv=None;requested=Ctx.port
    for p in range(requested,requested+10):
        try:
            srv=ThreadingHTTPServer(('127.0.0.1',p),H);Ctx.port=p;break
        except OSError as e:
            if p==requested: print('Port',requested,'is busy; trying fallback ports...')
    if srv is None: raise RuntimeError('No free localhost port in range %d..%d'%(requested,requested+9))
    print('center=',f'http://127.0.0.1:{Ctx.port}/')
    if not a.no_browser:threading.Timer(.7,lambda:webbrowser.open(f'http://127.0.0.1:{Ctx.port}/')).start()
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
if __name__=='__main__':raise SystemExit(main())
