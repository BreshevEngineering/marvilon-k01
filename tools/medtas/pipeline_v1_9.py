from __future__ import annotations
import argparse,json,subprocess,sys,time,traceback
from pathlib import Path

def dump(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def run(root,cmd,timeout=900):
    t=time.time()
    try:
        cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True,timeout=timeout);return cp.returncode,cp.stdout or '',cp.stderr or '',round(time.time()-t,3)
    except subprocess.TimeoutExpired as e:return 124,e.stdout or '',e.stderr or '',round(time.time()-t,3)
    except Exception:return 125,'',traceback.format_exc(),round(time.time()-t,3)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();py=sys.executable;out=root/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json';log=root/'reports/medtas/logs/current/K01_MEDTAS_PIPELINE.log';log.parent.mkdir(parents=True,exist_ok=True);log.write_text('K01 MEDTAS pipeline v1.9\nroot='+str(root)+'\n',encoding='utf-8');stages=[]
    def stage(idx,title,cmd,hard=False,blocked=False,timeout=900):
        print(f'[{idx}/8] {title}',flush=True)
        if blocked:rec={'index':idx,'title':title,'status':'BLOCKED_UPSTREAM','duration_s':0,'return_code':None,'substeps':[]};stages.append(rec);print('  -> BLOCKED_UPSTREAM');return rec
        rc,so,se,d=run(root,cmd,timeout);status='PASS' if rc==0 else ('HOLD' if hard else 'PASS_WITH_LIMITATIONS');rec={'index':idx,'title':title,'status':status,'duration_s':d,'return_code':rc,'command':[str(x) for x in cmd],'substeps':[]};stages.append(rec)
        with log.open('a',encoding='utf-8') as f:f.write(f'\n===== {idx} {title} rc={rc} {status} =====\n'+('[STDOUT]\n'+so if so else '')+('\n[STDERR]\n'+se if se else '')+'\n')
        if so:print(so,end='' if so.endswith('\n') else '\n')
        if se:print(se,end='' if se.endswith('\n') else '\n',file=sys.stderr)
        print('  ->',status,f'({d}s)');return rec
    def sub(parent,label,title,cmd,required=False,timeout=900):
        print(f'[{label}/8] {title}',flush=True);rc,so,se,d=run(root,cmd,timeout);status='PASS' if rc==0 else ('HOLD' if required else 'PASS_WITH_LIMITATIONS');parent['substeps'].append({'label':label,'title':title,'status':status,'return_code':rc,'duration_s':d})
        with log.open('a',encoding='utf-8') as f:f.write(f'\n----- {label} {title} rc={rc} {status} -----\n'+('[STDOUT]\n'+so if so else '')+('\n[STDERR]\n'+se if se else '')+'\n')
        if so:print(so,end='' if so.endswith('\n') else '\n')
        if se:print(se,end='' if se.endswith('\n') else '\n',file=sys.stderr)
        if status in ('HOLD','PASS_WITH_LIMITATIONS') and parent['status']=='PASS':parent['status']='PASS_WITH_LIMITATIONS'
        return status
    s1=stage(1,'Core invariants: canonical hash + common loader + Center + project structure',[py,str(root/'tools/medtas/canonical_hash_selftest_v1_5.py')],hard=True)
    if s1['status']=='PASS':
        sub(s1,'1.0','Preserve/create mutable runtime bindings',[py,str(root/'tools/medtas/ensure_runtime_bindings_v1_9.py'),'--repo-root',str(root)],required=True)
        sub(s1,'1.1','Common JSON loader regression',[py,str(root/'tools/medtas/common_load_selftest_v1_9.py')],required=True)
        sub(s1,'1.2','Status model',[py,str(root/'tools/medtas/status_model_selftest_v1_8.py'),'--repo-root',str(root)],required=True)
        sub(s1,'1.3','Command Center security/static',[py,str(root/'tools/medtas/center_security_selftest_v1_8.py'),'--repo-root',str(root)],required=True)
        sub(s1,'1.4','Project structure zones',[py,str(root/'tools/medtas/project_structure_v1_7.py'),'--repo-root',str(root),'--ensure-dirs'])
        sub(s1,'1.5','State reducer stale/drift fixtures',[py,str(root/'tests/medtas/state_reducer_fixtures_v1_9.py')],required=True)
        sub(s1,'1.5b','Requirements/parts registry integrity',[py,str(root/'tools/medtas/registry_selftest_v1_9.py'),'--repo-root',str(root)],required=True)
        sub(s1,'1.6','Requirements coverage registry',[py,str(root/'tools/medtas/build_requirements_coverage_v1_9.py'),'--repo-root',str(root)])
    core=s1['status']!='HOLD' and all(x['status']!='HOLD' for x in s1['substeps'])
    s2=stage(2,'SolidWorks adapters compile',[py,str(root/'tools/medtas/compile_sw_exporters_v1_7.py'),'--repo-root',str(root)],blocked=not core)
    s3=stage(3,'Real A001 CAD semantic extraction + canonical STATE_HASH',[py,str(root/'tools/medtas/run_cad_sem_a001.py'),'--repo-root',str(root)],hard=True,blocked=not core,timeout=600);cad=s3['status']=='PASS'
    if cad: sub(s3,'3.1','Stable CAD identity audit',[py,str(root/'tools/medtas/audit_identity_v1_9.py'),'--repo-root',str(root)])
    s4=stage(4,'Native MBD readback + authoring candidates',[py,str(root/'tools/medtas/build_mbd_a001_v1_6.py'),'--repo-root',str(root)],blocked=not cad,timeout=1200)
    if cad:
        sub(s4,'4.1','MBD/native candidates',[py,str(root/'tools/medtas/build_mbd_authoring_candidates_v1_7.py'),'--repo-root',str(root)])
        sub(s4,'4.2','MBD authoring plan',[py,str(root/'tools/medtas/build_mbd_authoring_plan_v1_7.py'),'--repo-root',str(root)])
    s5=stage(5,'Primary engineering state: snapshot + tolerance + SW/FEMM',[py,str(root/'tools/medtas/build_downstream_v1_8.py'),'--repo-root',str(root)],hard=True,blocked=not cad,timeout=1200);down=s5['status']=='PASS'
    if down:
        sub(s5,'5.1','Computed EBOM + MBOM from CAD + parts registry',[py,str(root/'tools/medtas/build_bom_v1_9.py'),'--repo-root',str(root)])
        sub(s5,'5.2','Canonical Product Definition',[py,str(root/'tools/medtas/build_product_definition_v1_8.py'),'--repo-root',str(root)])
        sub(s5,'5.3','Strict MBD drawing-release authority',[py,str(root/'tools/medtas/harden_product_definition_v1_9.py'),'--repo-root',str(root)])
        sub(s5,'5.4','P007 first exemplar plan + inspection characteristic template',[py,str(root/'tools/medtas/build_p007_exemplar_plan_v1_9.py'),'--repo-root',str(root)])
        sub(s5,'5.5','Per-drawing release plan',[py,str(root/'tools/medtas/build_drawing_release_plan_v1_9.py'),'--repo-root',str(root)])
        sub(s5,'5.6','Release characteristic registry / inspection data contract',[py,str(root/'tools/medtas/build_inspection_characteristics_v1_9.py'),'--repo-root',str(root)])
    s6=stage(6,'Protect primary structural evidence; CalculiX remains deferred',[py,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)],blocked=not down)
    if down:sub(s6,'6.1','Keep neutral P003/P007 STEP evidence fresh',[py,str(root/'tools/medtas/export_structural_neutral_geometry_v1_7.py'),'--repo-root',str(root)],timeout=600)
    s7=stage(7,'Release priority: P007 exemplar + parts registry/EBOM first',[py,str(root/'tools/medtas/build_release_priority_view_v1_9.py'),'--repo-root',str(root)],blocked=not down)
    s8=stage(8,'Derived state + project view + Center materialization',[py,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)])
    sub(s8,'8.1','Project structure audit',[py,str(root/'tools/medtas/project_structure_v1_7.py'),'--repo-root',str(root)])
    sub(s8,'8.2','Release priority view',[py,str(root/'tools/medtas/build_release_priority_view_v1_9.py'),'--repo-root',str(root)])
    sub(s8,'8.3','Unified project view',[py,str(root/'tools/medtas/project_view_v1_9.py'),'--repo-root',str(root)])
    sub(s8,'8.4','Release program stages 0-7',[py,str(root/'tools/medtas/build_release_program_v1_9.py'),'--repo-root',str(root)])
    hard_fail=[x for x in stages if x['status']=='HOLD' and x['index'] in (1,3,5)];lim=any(x['status'] in ('PASS_WITH_LIMITATIONS','BLOCKED_UPSTREAM') or any(y['status'] in ('PASS_WITH_LIMITATIONS','HOLD') for y in x.get('substeps',[])) for x in stages);overall='HOLD' if hard_fail else 'PASS_WITH_LIMITATIONS' if lim else 'PASS';report={'schema':'k01.medtas.pipeline.v1_9','project':'K01','overall_status':overall,'stages':stages,'priority_decision':'P007 exemplar + parts registry/EBOM are current P1. CalculiX remains deferred assurance.','principles':{'identity':'stable part/drawing identity; lifecycle state excluded from canonical names','requirements':'requirements.json authoritative; coverage is explicit','parts':'CAD structure/qty + parts.json metadata','bom':'separate EBOM/MBOM; non-modeled and suppressed explicit','drawing':'MBD/PMI owns dimensions/tolerances/datums; drawing is derived; no AutoDimension','characteristics':'one stable ID links PMI, drawing balloon, inspection and acceptance','revision':'released revision immutable','structural':'current SW service PASS is protected; CCX deferred'}};dump(out,report);print('\nK01 MEDTAS v1.9 PIPELINE',overall);print('DO NOW: P007 PMI/exemplar + parts registry/EBOM.');print('Command Center: OPEN_K01_COMMAND_CENTER_V11.cmd');return 1 if overall=='HOLD' else 0
if __name__=='__main__':raise SystemExit(main())
