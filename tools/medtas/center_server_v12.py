from __future__ import annotations
import argparse, hashlib, json, os, secrets, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from ai_handoff_v2_0 import build_handoff

BLOCKED_OPEN_EXT={'.exe','.cmd','.bat','.ps1','.py','.pyw','.js','.vbs','.msi','.scr','.com','.lnk','.reg'}
MAX_BODY=64*1024

class CenterState:
    def __init__(self, root:Path, port:int):
        self.root=root.resolve(); self.port=port; self.csrf=secrets.token_urlsafe(32)
        self.lock=threading.RLock(); self.handoff_lock=threading.Lock(); self._fingerprint=None; self._etag=None; self._dashboard=None; self.actions=self._actions()
    def _actions(self):
        return {
            'RUN_MEDTAS_PIPELINE':'03_RUN_MEDTAS_PIPELINE.cmd',
            'RUN_IDENTITY_AUDIT':'00_AUDIT_IDENTITY.cmd',
            'RUN_REQ_COVERAGE':'01_BUILD_REQUIREMENTS_COVERAGE.cmd',
            'RUN_ASSURANCE':'02_RUN_MEDTAS_ASSURANCE_TESTS.cmd',
            'RUN_INSPECTION_CHARACTERISTICS':'29_BUILD_INSPECTION_CHARACTERISTICS.cmd',
            'RUN_RELEASE_PROGRAM':'31_BUILD_RELEASE_PROGRAM.cmd',
            'RUN_HASH_INVARIANCE':'06_TEST_CAD_HASH_INVARIANCE.cmd',
            'RUN_BOM_ARTIFACT':'08_BUILD_BOM_ARTIFACT.cmd',
            'RUN_EBOM_MBOM':'23_BUILD_EBOM_MBOM.cmd',
            'RUN_PARTS_PROPS_DRY':'24_SYNC_PARTS_REGISTRY_TO_CAD_PROPS.cmd',
            'RUN_P007_EXEMPLAR_PLAN':'25_BUILD_P007_EXEMPLAR_PLAN.cmd',
            'RUN_DRAWING_QA':'26_VERIFY_DRAWING_QA.cmd',
            'RUN_P007_EXEMPLAR_SKELETON':'28_BUILD_P007_EXEMPLAR_SKELETON.cmd',
            'RUN_MBD_CANDIDATES':'09_BUILD_MBD_AUTHORING_CANDIDATES.cmd',
            'RUN_MBD_PLAN':'09B_BUILD_MBD_AUTHORING_PLAN.cmd',
            'RUN_FACE_BIND_AUTO':'10_BIND_STRUCTURAL_FACE_ROLES.cmd',
            'RUN_FACE_QUAL':'10B_QUALIFY_STRUCTURAL_FACE_MAP.cmd',
            'RUN_NEUTRAL_GEOMETRY':'11_EXPORT_STRUCTURAL_NEUTRAL_GEOMETRY.cmd',
            'RUN_STRUCT_MESH':'12_BUILD_STRUCTURAL_MESH.cmd',
            'RUN_BOLT_EQUIV':'12_BUILD_BOLT_EQUIV_SCAFFOLD.cmd',
            'RUN_CALCULIX_INPUT':'13_BUILD_CALCULIX_INPUT.cmd',
            'RUN_PROJECT_STRUCTURE':'14_AUDIT_PROJECT_STRUCTURE.cmd',
            'RUN_DRAWING_PLAN':'15_BUILD_DRAWING_RELEASE_PLAN.cmd',
            'RUN_DRAWING_PACK':'16_BUILD_NATIVE_DRAWING_PACK.cmd',
            'DISCOVER_DRAWING_TEMPLATE':'20_DISCOVER_DRAWING_TEMPLATE.cmd',
            'RECORD_DRAWING_VISUAL_APPROVAL':'21_RECORD_DRAWING_VISUAL_APPROVAL.cmd',
            'RUN_CALCULIX_PREFLIGHT':'05_CALCULIX_PREFLIGHT.cmd',
            'DISCOVER_ANALYSIS_TOOLCHAIN':'17_DISCOVER_ANALYSIS_TOOLCHAIN.cmd',
            'RUN_CALCULIX_P006':'18_RUN_CALCULIX_P006.cmd',
            'REBUILD_MEDTAS_STATE':'04_REBUILD_MEDTAS_CENTER.cmd',
        }
    def load(self, rel, default=None):
        p=self.root/rel
        try:return json.loads(p.read_text(encoding='utf-8-sig'))
        except Exception:return default
    def input_paths(self):
        rels=[
            'reports/control/K01_PROJECT_VIEW_CURRENT.json','reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json',
            'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json','reports/control/K01_CURRENT_STATE.json','control/state/K01_CURRENT_STATE.json',
            'control/requirements/requirements.json','reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json','control/identity/K01_IDENTITY_POLICY_v1_9.json','control/identity/entities.json','reports/control/K01_IDENTITY_AUDIT_CURRENT.json','reports/control/K01_RELEASE_PROGRAM_CURRENT.json','control/inspection/K01_CHARACTERISTIC_POLICY_v1_9.json','reports/inspection/current/K01_RELEASE_CHARACTERISTICS_CURRENT.json','reports/inspection/current/K01_INSPECTION_RESULTS_CURRENT.json',
            'control/medtas/v1/spec/K01_STATUS_MODEL_v1_9.json','control/parameters/K01_J2_INTERFACE_PARAMETERS_v1_7.json',
            'reports/control/K01_PROJECT_STRUCTURE_CURRENT.json','reports/control/K01_RELEASE_PRIORITY_CURRENT.json','reports/control/K01_AI_HANDOFF_CURRENT.zip','reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json',
            'reports/medtas/mbd/current/K01_MBD_A001_v1.json','reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_7.json','reports/drawing/current/K01-D-006_P007_LIVE_GEOMETRY_CURRENT.json',
            'reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_6.json','reports/medtas/mbd/current/K01_MBD_AUTHORING_PLAN_v1_7.json',
            'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json','reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json','reports/drawing/current/K01-D-006_P007_EXEMPLAR_ARTIFACT_CURRENT.json','reports/inspection/current/K01-D-006_P007_CHARACTERISTICS_CURRENT.csv','reports/medtas/drawing/current/K01_DRAWING_VERIFY_GATE04E_v1.json','control/drawings/K01_DRAWING_QA_POLICY_v1_9.json','reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json','reports/drawing/current/K01_DRAWING_TEMPLATE_DISCOVERY_CURRENT.json','reports/medtas/drawing/current/K01_DRAWING_MBD_RELEASE_WORKPACK_v1_6.json',
            'control/product/parts.json','control/product/K01_BOM_POLICY_v1_9.json','reports/medtas/bom/current/K01_BOM_MODEL_A001_v1.json','reports/medtas/bom/current/K01_BOM_VERIFY_A001_v1.json','reports/medtas/bom/current/K01_EBOM_MODEL_A001_v1_9.json','reports/medtas/bom/current/K01_EBOM_VERIFY_A001_v1_9.json','reports/medtas/bom/current/K01_MBOM_MODEL_A001_v1_9.json','reports/medtas/bom/current/K01_MBOM_VERIFY_A001_v1_9.json','reports/bom/current/K01_PARTS_PROPERTY_PROJECTION_CURRENT.json',
            'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json','reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_QUAL_P006_v1_7.json',
            'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json','reports/medtas/calculix/current/K01_ANALYSIS_TOOLCHAIN_DISCOVERY_CURRENT.json','control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1_2.json',
            'control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1.json','reports/bom/current/K01_BOM_A001_CURRENT.csv'
        ]
        return [self.root/r for r in rels]
    def fingerprint(self):
        rows=[]
        for p in self.input_paths():
            try:
                st=p.stat(); rows.append((str(p.relative_to(self.root)).replace('\\','/'),st.st_size,st.st_mtime_ns))
            except Exception: rows.append((str(p.relative_to(self.root)).replace('\\','/'),None,None))
        raw=json.dumps(rows,separators=(',',':')).encode(); return hashlib.sha256(raw).hexdigest()
    def project_view(self): return self.load('reports/control/K01_PROJECT_VIEW_CURRENT.json',{}) or {}
    def approved_roots(self):
        roots=[self.root]
        ps=self.load('reports/control/K01_PROJECT_STRUCTURE_CURRENT.json',{}) or {}
        ext=ps.get('external_cad_root')
        if ext:
            try: roots.append(Path(ext).resolve())
            except Exception: pass
        return roots
    @staticmethod
    def within(path:Path, roots):
        try:
            rp=path.resolve()
            for r in roots:
                try:
                    if os.path.commonpath([str(rp),str(r.resolve())])==str(r.resolve()): return True
                except (ValueError,OSError): continue
        except Exception: pass
        return False
    def file_registry(self):
        reg={}
        def add(fid,name,path,domain='Evidence'):
            if not fid or not path:return
            p=Path(path)
            if not p.is_absolute():p=self.root/p
            try:rp=p.resolve()
            except Exception:return
            if not self.within(rp,self.approved_roots()):return
            reg[str(fid)]={'id':str(fid),'name':str(name),'domain':domain,'path':str(rp),'exists':rp.exists()}
        ev=self.load('control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1_2.json') or self.load('control/medtas/v1/registry/K01_EVIDENCE_REGISTRY_v1.json',{}) or {}
        entries=ev.get('evidence',ev.get('items',[])) if isinstance(ev,dict) else []
        for e in entries or []:
            eid=e.get('evidence_id') or e.get('id')
            for i,f in enumerate(e.get('files',[]) or []):
                path=f.get('path') if isinstance(f,dict) else f
                add(f'EVIDENCE::{eid}::{i}', e.get('title') or eid, path, e.get('category') or 'Evidence')
        known=[
          ('BOM-CSV','Compatibility EBOM CSV','reports/bom/current/K01_BOM_A001_CURRENT.csv','BOM'),
          ('EBOM-CSV','Current EBOM CSV','reports/bom/current/K01_EBOM_A001_CURRENT.csv','BOM'),
          ('EBOM-JSON','Current EBOM JSON','reports/bom/current/K01_EBOM_A001_CURRENT.json','BOM'),
          ('MBOM-CSV','Current MBOM CSV','reports/bom/current/K01_MBOM_A001_CURRENT.csv','BOM'),
          ('MBOM-JSON','Current MBOM JSON','reports/bom/current/K01_MBOM_A001_CURRENT.json','BOM'),
          ('PARTS-REGISTRY','Canonical parts registry','control/product/parts.json','Product Data'),
          ('PARTS-PROPS-PROJECTION','Registry-to-CAD property projection','reports/bom/current/K01_PARTS_PROPERTY_PROJECTION_CURRENT.json','Product Data'),
          ('BOM-MODEL','Canonical BOM model','reports/medtas/bom/current/K01_BOM_MODEL_A001_v1.json','BOM'),
          ('BOM-VERIFY','BOM parity verification','reports/medtas/bom/current/K01_BOM_VERIFY_A001_v1.json','BOM'),
          ('MBD-CURRENT','Current MBD semantic state','reports/medtas/mbd/current/K01_MBD_A001_v1.json','MBD'),
          ('MBD-PLAN','MBD authoring plan','reports/medtas/mbd/current/K01_MBD_AUTHORING_PLAN_v1_7.json','MBD'),
          ('DRAWING-PLAN','Drawing release plan','reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json','Drawing'),
          ('P007-EXEMPLAR-PLAN','P007 exemplar drawing plan','reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json','Drawing'),
          ('P007-LIVE-GEOMETRY','P007 live CAD geometry authority','reports/drawing/current/K01-D-006_P007_LIVE_GEOMETRY_CURRENT.json','Drawing'),
          ('P007-EXEMPLAR-DRAFT','P007 exemplar draft artifact manifest','reports/drawing/current/K01-D-006_P007_EXEMPLAR_ARTIFACT_CURRENT.json','Drawing'),
          ('P007-MBD-CHECKLIST','P007 MBD authoring checklist','reports/drawing/current/K01-D-006_P007_MBD_AUTHORING_CHECKLIST.md','Drawing'),
          ('P007-INSPECTION-CHAR','P007 inspection characteristic template','reports/inspection/current/K01-D-006_P007_CHARACTERISTICS_CURRENT.csv','Inspection'),
          ('P007-MFG-REVIEW','P007 manufacturer review template','control/drawings/K01-D-006_MANUFACTURER_REVIEW_TEMPLATE_v1_9.csv','Drawing'),
          ('DRAWING-QA-POLICY','Drawing QA policy','control/drawings/K01_DRAWING_QA_POLICY_v1_9.json','Drawing'),
          ('DRAWING-TEMPLATE-DISCOVERY','Drawing template discovery','reports/drawing/current/K01_DRAWING_TEMPLATE_DISCOVERY_CURRENT.json','Drawing'),
          ('DRAWING-ARTIFACT','Native drawing artifact manifest','reports/medtas/drawing/current/K01_DRAWING_ARTIFACT_GATE04E_v1_8.json','Drawing'),
          ('DRAWING-VERIFY','Drawing verification','reports/medtas/drawing/current/K01_DRAWING_VERIFY_GATE04E_v1_7.json','Drawing'),
          ('PROJECT-STRUCTURE','Project structure audit','reports/control/K01_PROJECT_STRUCTURE_CURRENT.json','Control'),
          ('MEDTAS-DERIVED','MEDTAS derived state','reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json','Control'),
          ('PIPELINE','Current pipeline report','reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json','Control'),
          ('FACE-MAP','Structural face map','reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json','Structural'),
          ('FACE-QUAL','Face-map qualification','reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_QUAL_P006_v1_7.json','Structural'),
          ('CCX-PREFLIGHT','CalculiX preflight','reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json','Structural'),
          ('CCX-TOOLCHAIN','Analysis toolchain discovery','reports/medtas/calculix/current/K01_ANALYSIS_TOOLCHAIN_DISCOVERY_CURRENT.json','Structural'),
          ('PRODUCT-DEFINITION','Canonical Product Definition','reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json','Product Definition'),
          ('RELEASE-PRIORITY','Current release priority','reports/control/K01_RELEASE_PRIORITY_CURRENT.json','Control'),
          ('AI-HANDOFF-CURRENT','Current AI handoff ZIP','reports/control/K01_AI_HANDOFF_CURRENT.zip','AI Handoff'),
          ('REPO-MAP','Repository structure & authority','docs/architecture/K01_REPOSITORY_STRUCTURE_AND_AUTHORITY_v1_8.md','Architecture'),
          ('PROJECT-MIGRATION','Project migration review plan','reports/control/K01_PROJECT_MIGRATION_PLAN_CURRENT.json','Control'),
          ('REQUIREMENTS-REGISTRY','Requirements registry','control/requirements/requirements.json','Requirements'),
          ('REQUIREMENTS-COVERAGE','Requirement-to-evidence coverage','reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json','Requirements'),
          ('IDENTITY-POLICY','Stable identity policy','control/identity/K01_IDENTITY_POLICY_v1_9.json','Identity'),
          ('IDENTITY-REGISTRY','Stable identity registry','control/identity/entities.json','Identity'),
          ('IDENTITY-AUDIT','Native CAD identity audit','reports/control/K01_IDENTITY_AUDIT_CURRENT.json','Identity'),
          ('RELEASE-PROGRAM','Release program stages 0-7','reports/control/K01_RELEASE_PROGRAM_CURRENT.json','Control'),
          ('CHAR-REGISTRY','Release characteristic registry','reports/inspection/current/K01_RELEASE_CHARACTERISTICS_CURRENT.json','Inspection'),
          ('INSPECTION-RESULTS','Current inspection result evaluation','reports/inspection/current/K01_INSPECTION_RESULTS_CURRENT.json','Inspection'),
        ]
        for x in known:add(*x)
        # Current native CAD assembly is registered server-side from the materialized semantic state; browser never supplies this path.
        cad=self.load('reports/medtas/cad/current/K01_CAD_SEM_A001.json',{}) or {}
        native=cad.get('source_assembly') or cad.get('assembly_path')
        if native:add('CAD-A001-CURRENT','Current A001 native assembly',native,'Native CAD')
        return reg
    def build_dashboard(self):
        fp=self.fingerprint()
        with self.lock:
            if self._fingerprint==fp and self._dashboard is not None:return self._dashboard,self._etag
            current=self.load('reports/control/K01_CURRENT_STATE.json') or self.load('control/state/K01_CURRENT_STATE.json',{}) or {}
            status=self.load('control/medtas/v1/spec/K01_STATUS_MODEL_v1_9.json',{}) or {}
            pv=self.project_view(); feed=self.load('reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json',{}) or {}
            files=list(self.file_registry().values())
            payload={
              'schema':'k01.center.dashboard.v2_0','server_build':'2.0','csrf_token':self.csrf,'status_model':status,'project_view':pv,'medtas_feed':feed,'current_state':current,
              'requirements_registry':self.load('control/requirements/requirements.json',{}) or {},
              'requirements_coverage':self.load('reports/control/K01_REQUIREMENTS_COVERAGE_CURRENT.json',{}) or {},
              'identity_audit':self.load('reports/control/K01_IDENTITY_AUDIT_CURRENT.json',{}) or {},
              'release_program':self.load('reports/control/K01_RELEASE_PROGRAM_CURRENT.json',{}) or {},
              'release_characteristics':self.load('reports/inspection/current/K01_RELEASE_CHARACTERISTICS_CURRENT.json',{}) or {},
              'inspection_results':self.load('reports/inspection/current/K01_INSPECTION_RESULTS_CURRENT.json',{}) or {},
              'release_priority':self.load('reports/control/K01_RELEASE_PRIORITY_CURRENT.json',{}) or {},
              'product_definition':self.load('reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json',{}) or {},
              'mbd_candidates':self.load('reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_7.json') or self.load('reports/medtas/mbd/current/K01_MBD_AUTHORING_CANDIDATES_v1_6.json',{}) or {},
              'mbd_plan':self.load('reports/medtas/mbd/current/K01_MBD_AUTHORING_PLAN_v1_7.json',{}) or {},
              'drawing_plan':self.load('reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json',{}) or {},
              'p007_exemplar':self.load('reports/drawing/current/K01-D-006_P007_EXEMPLAR_PLAN_CURRENT.json',{}) or {},
              'p007_live_geometry':self.load('reports/drawing/current/K01-D-006_P007_LIVE_GEOMETRY_CURRENT.json',{}) or {},
              'drawing_template_discovery':self.load('reports/drawing/current/K01_DRAWING_TEMPLATE_DISCOVERY_CURRENT.json',{}) or {},
              'drawing_workpack':self.load('reports/medtas/drawing/current/K01_DRAWING_MBD_RELEASE_WORKPACK_v1_6.json',{}) or {},
              'parts_registry':self.load('control/product/parts.json',{}) or {},
              'bom_model':self.load('reports/medtas/bom/current/K01_BOM_MODEL_A001_v1.json',{}) or {},
              'bom_verify':self.load('reports/medtas/bom/current/K01_BOM_VERIFY_A001_v1.json',{}) or {},
              'ebom_model':self.load('reports/medtas/bom/current/K01_EBOM_MODEL_A001_v1_9.json',{}) or {},
              'ebom_verify':self.load('reports/medtas/bom/current/K01_EBOM_VERIFY_A001_v1_9.json',{}) or {},
              'mbom_model':self.load('reports/medtas/bom/current/K01_MBOM_MODEL_A001_v1_9.json',{}) or {},
              'mbom_verify':self.load('reports/medtas/bom/current/K01_MBOM_VERIFY_A001_v1_9.json',{}) or {},
              'parts_property_projection':self.load('reports/bom/current/K01_PARTS_PROPERTY_PROJECTION_CURRENT.json',{}) or {},
              'face_map':self.load('reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json',{}) or {},
              'face_qualification':self.load('reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_QUAL_P006_v1_7.json',{}) or {},
              'files':files,
            }
            raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'); et='"'+hashlib.sha256(raw).hexdigest()+'"'
            self._fingerprint=fp;self._dashboard=payload;self._etag=et;return payload,et
    def start_action(self, action_id):
        name=self.actions.get(action_id)
        if not name: raise ValueError('Unknown controlled action id')
        # High-priority actions are launched directly as Python argv, avoiding fragile nested cmd.exe quoting.
        direct={
          'RUN_MEDTAS_PIPELINE':['tools/medtas/pipeline_v2_0.py'],
          'RUN_IDENTITY_AUDIT':['tools/medtas/audit_identity_v2_0.py'],
          'RUN_REQ_COVERAGE':['tools/medtas/build_requirements_coverage_v1_9.py'],
          'RUN_EBOM_MBOM':['tools/medtas/build_bom_v1_9.py'],
          'RUN_PARTS_PROPS_DRY':['tools/medtas/sync_parts_registry_to_cad_props_v2_0.py'],
          'RUN_P007_EXEMPLAR_PLAN':['tools/medtas/build_p007_release_front_v2_0.py'],
          'RUN_DRAWING_QA':['tools/medtas/drawing_qa_gate_v1_9.py'],
          'RUN_MBD_CANDIDATES':['tools/medtas/build_mbd_authoring_candidates_v1_7.py'],
          'RUN_MBD_PLAN':['tools/medtas/build_mbd_authoring_plan_v1_7.py'],
          'RUN_PROJECT_STRUCTURE':['tools/medtas/project_structure_v1_7.py'],
          'RUN_DRAWING_PLAN':['tools/medtas/build_drawing_release_plan_v1_9.py'],
          'REBUILD_MEDTAS_STATE':['tools/medtas/rebuild_medtas_state.py'],
          'RUN_RELEASE_PROGRAM':['tools/medtas/build_release_program_v1_9.py'],
          'RUN_INSPECTION_CHARACTERISTICS':['tools/medtas/build_inspection_characteristics_v1_9.py'],
        }
        log=self.root/'reports/medtas/logs/current/K01_CENTER_ACTIONS.log';log.parent.mkdir(parents=True,exist_ok=True)
        flags=getattr(subprocess,'CREATE_NEW_CONSOLE',0) if os.name=='nt' else 0
        if action_id in direct:
            script=(self.root/direct[action_id][0]).resolve()
            if not script.exists(): raise FileNotFoundError(str(script.relative_to(self.root)))
            if not self.within(script,[self.root]): raise PermissionError('Controlled action path escaped repository root')
            cmd=[sys.executable,str(script),'--repo-root',str(self.root)]
        else:
            p=(self.root/name).resolve()
            if not p.exists(): raise FileNotFoundError(name)
            if not self.within(p,[self.root]): raise PermissionError('Controlled action path escaped repository root')
            if os.name!='nt': raise RuntimeError('This controlled CMD action requires Windows')
            comspec=os.environ.get('COMSPEC') or 'cmd.exe'
            cmd=[comspec,'/d','/c',str(p)]
        try:
            cp=subprocess.Popen(cmd,cwd=str(self.root),creationflags=flags,close_fds=False)
            with log.open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' START '+action_id+' pid='+str(cp.pid)+' argv='+repr(cmd)+'\n')
        except Exception as e:
            with log.open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' ERROR '+action_id+' '+repr(e)+'\n')
            raise RuntimeError('Controlled action launch failed; see '+str(log)+': '+str(e))
        return {'ok':True,'action':action_id,'started':True,'pid':cp.pid,'launcher':'DIRECT_PYTHON' if action_id in direct else 'CONTROLLED_CMD'}
    def open_registered(self,fid,reveal=False):
        rec=self.file_registry().get(str(fid))
        if not rec: raise ValueError('Unknown registered file id')
        p=Path(rec['path']).resolve()
        if not self.within(p,self.approved_roots()): raise PermissionError('Registered path is outside approved engineering roots')
        if not p.exists(): raise FileNotFoundError(rec['name'])
        if not reveal and p.suffix.lower() in BLOCKED_OPEN_EXT: raise PermissionError('Executable/script artifacts cannot be opened by the generic file endpoint')
        if os.name!='nt': raise RuntimeError('Open/reveal actions require Windows')
        if reveal: subprocess.Popen(['explorer.exe','/select,',str(p)],close_fds=True)
        else: os.startfile(str(p))
        return {'ok':True,'id':fid,'mode':'reveal' if reveal else 'open'}
    def handoff(self):
        log=self.root/'reports/medtas/logs/current/K01_CENTER_HANDOFF.log';log.parent.mkdir(parents=True,exist_ok=True)
        if not self.handoff_lock.acquire(blocking=False):
            raise RuntimeError('AI handoff build is already running')
        try:
            with log.open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' START\n')
            res=build_handoff(self.root)
            with log.open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' PASS files='+str(res.get('files'))+' sha256='+str(res.get('sha256'))+'\n')
            self._fingerprint=None
            return res
        except Exception as e:
            with log.open('a',encoding='utf-8') as f:f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' ERROR '+repr(e)+'\n')
            raise
        finally:
            self.handoff_lock.release()

class Handler(BaseHTTPRequestHandler):
    server_version='K01-MEDTAS-v12'
    def log_message(self,fmt,*args): print(time.strftime('%H:%M:%S'),fmt%args)
    @property
    def S(self): return self.server.state
    def security_headers(self,ctype='text/plain; charset=utf-8'):
        self.send_header('Content-Type',ctype);self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY');self.send_header('Cache-Control','no-store');self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
    def send_bytes(self,status,data,ctype,etag=None):
        self.send_response(status);self.security_headers(ctype)
        if etag:self.send_header('ETag',etag)
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def send_json(self,status,obj,etag=None):self.send_bytes(status,json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode(), 'application/json; charset=utf-8',etag)
    def valid_host(self):
        h=(self.headers.get('Host') or '').split(':')[0].lower();return h in {'127.0.0.1','localhost','[::1]','::1'}
    def valid_origin(self):
        origin=(self.headers.get('Origin') or '').rstrip('/').lower();allowed={f'http://127.0.0.1:{self.S.port}',f'http://localhost:{self.S.port}'};return origin in allowed
    def do_GET(self):
        if not self.valid_host(): return self.send_json(403,{'ok':False,'error':'Invalid Host'})
        u=urlparse(self.path);path=u.path
        if path=='/':
            p=self.S.root/'K01_Command_Center_v11.html';return self.send_bytes(200,p.read_bytes(),'text/html; charset=utf-8')
        if path=='/assets/app_v11.js':return self.send_bytes(200,(self.S.root/'control/medtas/v1/center/assets/app_v11.js').read_bytes(),'application/javascript; charset=utf-8')
        if path=='/assets/styles_v11.css':return self.send_bytes(200,(self.S.root/'control/medtas/v1/center/assets/styles_v11.css').read_bytes(),'text/css; charset=utf-8')
        if path=='/api/health':return self.send_json(200,{'ok':True,'schema':'k01.center.health.v2_0','server_build':'2.0','legacy_backend_required':False})
        if path=='/api/dashboard':
            d,etag=self.S.build_dashboard()
            if self.headers.get('If-None-Match')==etag:
                self.send_response(304);self.security_headers('application/json; charset=utf-8');self.send_header('ETag',etag);self.end_headers();return
            return self.send_json(200,d,etag)
        # Deliberately no GET routes for actions/open/reveal/handoff.
        return self.send_json(404,{'ok':False,'error':'Not Found'})
    def read_json(self):
        try:n=int(self.headers.get('Content-Length','0'))
        except Exception:n=0
        if n<=0 or n>MAX_BODY:raise ValueError('Invalid request body length')
        return json.loads(self.rfile.read(n).decode('utf-8'))
    def authorize_post(self):
        if not self.valid_host():raise PermissionError('Invalid Host')
        if not self.valid_origin():raise PermissionError('Origin rejected')
        if not secrets.compare_digest(self.headers.get('X-K01-CSRF') or '',self.S.csrf):raise PermissionError('CSRF token rejected')
    def do_POST(self):
        u=urlparse(self.path);path=u.path
        try:
            self.authorize_post();body=self.read_json()
            if path=='/api/action':res=self.S.start_action(body.get('id'))
            elif path=='/api/open':res=self.S.open_registered(body.get('id'),False)
            elif path=='/api/reveal':res=self.S.open_registered(body.get('id'),True)
            elif path=='/api/handoff':res=self.S.handoff()
            else:return self.send_json(404,{'ok':False,'error':'Not Found'})
            return self.send_json(200,res)
        except PermissionError as e:return self.send_json(403,{'ok':False,'error':str(e)})
        except (ValueError,FileNotFoundError) as e:return self.send_json(400,{'ok':False,'error':str(e)})
        except Exception as e:return self.send_json(500,{'ok':False,'error':str(e)})

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,addr,handler,state):super().__init__(addr,handler);self.state=state

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--port',type=int,default=8790);ap.add_argument('--no-browser',action='store_true');a=ap.parse_args();root=Path(a.repo_root).resolve()
    port=a.port
    while True:
        state=CenterState(root,port)
        try:srv=Server(('127.0.0.1',port),Handler,state);break
        except OSError:
            port+=1
            if port>a.port+20:raise
    srv.state.port=port;url=f'http://127.0.0.1:{port}/'
    print('K01 MEDTAS Command Center v12 runtime - secure single-process server');print('root  =',root);print('center=',url);print('GET dashboard is cached/materialized; side effects require same-origin POST + CSRF + registered IDs.')
    if not a.no_browser:
        try:
            import webbrowser; threading.Timer(.5,lambda:webbrowser.open(url)).start()
        except Exception:pass
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
    return 0
if __name__=='__main__':raise SystemExit(main())
