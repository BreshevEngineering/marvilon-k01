from __future__ import annotations
import argparse,json,subprocess,sys,time,traceback
from pathlib import Path


def dump(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')

def run(root,cmd,timeout=900):
    t=time.time()
    try:
        cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True,timeout=timeout)
        return cp.returncode,cp.stdout or '',cp.stderr or '',round(time.time()-t,3)
    except subprocess.TimeoutExpired as e:
        return 124,(e.stdout or ''),(e.stderr or ''),round(time.time()-t,3)
    except Exception:
        return 125,'',traceback.format_exc(),round(time.time()-t,3)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();py=sys.executable
    out=root/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json';log=root/'reports/medtas/logs/current/K01_MEDTAS_PIPELINE.log';log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text('K01 MEDTAS pipeline v1.7\nroot='+str(root)+'\n',encoding='utf-8');stages=[]

    def stage(idx,title,cmd=None,hard=False,blocked=False,timeout=900):
        print(f'[{idx}/8] {title}',flush=True)
        if blocked:
            rec={'index':idx,'title':title,'status':'BLOCKED_UPSTREAM','duration_s':0,'return_code':None,'substeps':[]};stages.append(rec);print('  -> BLOCKED_UPSTREAM');return rec
        rc,so,se,dur=run(root,cmd,timeout) if cmd else (0,'','',0)
        status='PASS' if rc==0 else ('HOLD' if hard else 'PASS_WITH_LIMITATIONS')
        rec={'index':idx,'title':title,'status':status,'duration_s':dur,'return_code':rc,'command':[str(x) for x in cmd] if cmd else None,'message':(se.strip().splitlines()[-1] if se.strip() else so.strip().splitlines()[-1] if so.strip() else ''),'substeps':[]};stages.append(rec)
        with log.open('a',encoding='utf-8') as f:
            f.write(f'\n===== STAGE {idx}/8 {title} rc={rc} status={status} =====\n')
            if so:f.write('[STDOUT]\n'+so+'\n')
            if se:f.write('[STDERR]\n'+se+'\n')
        if so:print(so,end='' if so.endswith('\n') else '\n')
        if se:print(se,end='' if se.endswith('\n') else '\n',file=sys.stderr)
        print('  ->',status,f'({dur}s)');return rec

    def sub(parent,label,title,cmd,timeout=900,required=False):
        print(f'[{label}/8] {title}',flush=True)
        rc,so,se,dur=run(root,cmd,timeout)
        status='PASS' if rc==0 else ('HOLD' if required else 'PASS_WITH_LIMITATIONS')
        rec={'label':label,'title':title,'status':status,'return_code':rc,'duration_s':dur,'command':[str(x) for x in cmd],'message':(se.strip().splitlines()[-1] if se.strip() else so.strip().splitlines()[-1] if so.strip() else '')};parent.setdefault('substeps',[]).append(rec)
        with log.open('a',encoding='utf-8') as f:
            f.write(f'\n----- SUBSTEP {label} {title} rc={rc} status={status} -----\n')
            if so:f.write('[STDOUT]\n'+so+'\n')
            if se:f.write('[STDERR]\n'+se+'\n')
        if so:print(so,end='' if so.endswith('\n') else '\n')
        if se:print(se,end='' if se.endswith('\n') else '\n',file=sys.stderr)
        if status in ('HOLD','PASS_WITH_LIMITATIONS') and parent['status']=='PASS':parent['status']='PASS_WITH_LIMITATIONS'
        return rec

    # 1. Core invariants and project structure. No CAD writes.
    s1=stage(1,'Core invariants: canonical hash + status model + Center security',[py,str(root/'tools/medtas/canonical_hash_selftest_v1_5.py')],hard=True)
    if s1['status']=='PASS':
        sub(s1,'1.1','Single controlled status-model self-test',[py,str(root/'tools/medtas/status_model_selftest_v1_7.py'),'--repo-root',str(root)],required=True)
        sub(s1,'1.2','Command Center v11 static/security self-test',[py,str(root/'tools/medtas/center_security_selftest_v1_7.py'),'--repo-root',str(root)],required=True)
        sub(s1,'1.2b','Command Center v11 localhost runtime regression',[py,str(root/'tools/medtas/center_server_regression_v1_7.py'),'--repo-root',str(root)],required=True,timeout=120)
        sub(s1,'1.3','Project structure audit / ensure canonical zones',[py,str(root/'tools/medtas/project_structure_v1_7.py'),'--repo-root',str(root),'--ensure-dirs'])
    core=s1['status'] not in ('HOLD','BLOCKED_UPSTREAM') and all(x['status']!='HOLD' for x in s1.get('substeps',[]))

    # 2. SolidWorks adapters. Compile failures in MBD/Simulation remain limitations; CAD semantic exporter is mandatory later.
    s2=stage(2,'SolidWorks adapters: deterministic interop bundle + CAD/MBD/Simulation exporters',[py,str(root/'tools/medtas/compile_sw_exporters_v1_7.py'),'--repo-root',str(root)],hard=False,blocked=not core)

    # 3. Live semantic extraction and first-class state hash.
    s3=stage(3,'Real A001 CAD semantic extraction + canonical STATE_HASH',[py,str(root/'tools/medtas/run_cad_sem_a001.py'),'--repo-root',str(root)],hard=True,blocked=not core,timeout=600)
    cad=s3['status']=='PASS'

    # 4. MBD extraction, candidate discovery and authoring plan. Read-only.
    s4=stage(4,'Native MBD / DimXpert extraction',[py,str(root/'tools/medtas/build_mbd_a001_v1_6.py'),'--repo-root',str(root)],hard=False,blocked=not cad,timeout=1200)
    if cad:
        sub(s4,'4.1','Semantic MBD authoring candidates (dimension + geometry)',[py,str(root/'tools/medtas/build_mbd_authoring_candidates_v1_7.py'),'--repo-root',str(root)])
        sub(s4,'4.2','Controlled MBD authoring plan',[py,str(root/'tools/medtas/build_mbd_authoring_plan_v1_7.py'),'--repo-root',str(root)])

    # 5. Solver/drawing/BOM-neutral derived engineering models.
    s5=stage(5,'Canonical snapshot + tolerance + structural/FEMM + drawing/BOM semantic models',[py,str(root/'tools/medtas/build_downstream_v1_7.py'),'--repo-root',str(root)],hard=True,blocked=not cad,timeout=1200)
    down=s5['status']=='PASS'
    if down:
        sub(s5,'5.1','BOM artifact + semantic parity',[py,str(root/'tools/medtas/build_bom_artifact_v1_5.py'),'--repo-root',str(root)])
        sub(s5,'5.2','Drawing release plan from MBD-backed characteristics',[py,str(root/'tools/medtas/build_drawing_release_plan_v1_7.py'),'--repo-root',str(root)])

    # 6. Structural identity chain. Automatic Simulation binding is attempted; ambiguity is fail-closed.
    s6=stage(6,'Persistent structural face identities',[py,str(root/'tools/medtas/build_face_map_candidate_v1_7.py'),'--repo-root',str(root)],hard=False,blocked=not down)
    if down:
        sub(s6,'6.1','Automatic exact SolidWorks Simulation load/entity binding',[py,str(root/'tools/medtas/auto_bind_structural_face_roles_v1_7.py'),'--repo-root',str(root)],timeout=420)
        # qualification can only pass if automatic binding passes; still run to leave explicit evidence.
        sub(s6,'6.2','Face-map no-op rebuild qualification',[py,str(root/'tools/medtas/qualify_structural_face_map_v1_7.py'),'--repo-root',str(root)],timeout=600)
        sub(s6,'6.3','M2.5 preload/load-path equivalence scaffold',[py,str(root/'tools/medtas/build_bolt_equiv_scaffold_v1_7.py'),'--repo-root',str(root)])
        sub(s6,'6.4','P003/P007 neutral STEP export',[py,str(root/'tools/medtas/export_structural_neutral_geometry_v1_7.py'),'--repo-root',str(root)],timeout=600)

    # 7. Mesh + CalculiX execution readiness. Missing external tools are engineering/toolchain limitations, not pipeline crashes.
    s7=stage(7,'CalculiX solver-neutral execution chain',[py,str(root/'tools/medtas/calculix_preflight_v1_7.py'),'--repo-root',str(root)],hard=False)
    if down:
        sub(s7,'7.1','Quadratic C3D10-compatible mesh build',[py,str(root/'tools/medtas/build_structural_mesh_v1_7.py'),'--repo-root',str(root)],timeout=1200)
        sub(s7,'7.2','Controlled CalculiX input gate',[py,str(root/'tools/medtas/build_calculix_input_v1_7.py'),'--repo-root',str(root)])
        sub(s7,'7.3','Final CalculiX preflight',[py,str(root/'tools/medtas/calculix_preflight_v1_7.py'),'--repo-root',str(root)])

    # 8. Materialized views only; no graph recomputation during browser polling.
    s8=stage(8,'Derived state + project view + secure Center materialization',[py,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)],hard=False)
    sub(s8,'8.1','Project structure materialized audit',[py,str(root/'tools/medtas/project_structure_v1_7.py'),'--repo-root',str(root)])
    sub(s8,'8.2','Unified project view for Command Center v11',[py,str(root/'tools/medtas/project_view_v1_7.py'),'--repo-root',str(root)])

    hard_fail=[]
    for x in stages:
        if x['status']=='HOLD' and x['index'] in (1,3,5): hard_fail.append(x)
        hard_fail.extend({'index':x['index'],'title':s['title'],'message':s.get('message')} for s in x.get('substeps',[]) if s['status']=='HOLD' and x['index']==1)
    limitation=any(x['status'] in ('PASS_WITH_LIMITATIONS','BLOCKED_UPSTREAM') or any(s['status'] in ('PASS_WITH_LIMITATIONS','HOLD') for s in x.get('substeps',[])) for x in stages)
    overall='HOLD' if hard_fail else ('PASS_WITH_LIMITATIONS' if limitation else 'PASS')
    report={'schema':'k01.medtas.pipeline.v1_7','project':'K01','overall_status':overall,'stages':stages,'hard_failures':hard_fail,'principles':{
        'build_graph':'MEDTAS computes derived state from causal dependencies; materialized Center files are rebuildable views',
        'cad_hash':'STATE_HASH uses canonical semantic JSON only; native SLDPRT/SLDASM SHA is diagnostic provenance',
        'hash_qualification':'two deterministic exports + no-change save(s); unchanged engineering state must preserve hash',
        'step_hash':'volatile STEP header removed; normalized STEP hash is artifact-stability only, not geometric-equivalence proof',
        'mbd':'native CAD + reviewed MBD/DimXpert owns product definition; drawing is derived presentation',
        'face_identity':'automatic Simulation entity extraction + unique semantic face signature + no-op rebuild qualification; ambiguity is HOLD',
        'calculix':'qualified face roles + neutral STEP + C3D10-compatible mesh + reviewed bolt/contact/preload equivalence + controlled deck',
        'center_security':'single dashboard GET; same-origin POST+CSRF actions; registered IDs only for open/reveal; DOM text rendering; one status model',
        'project_structure':'canonical zones are created/audited without automatically moving existing engineering evidence'
    }}
    dump(out,report)
    # Update views once more so Center sees the pipeline report itself.
    for script in ('rebuild_medtas_state.py','project_structure_v1_7.py','project_view_v1_7.py'):
        try:subprocess.run([py,str(root/'tools/medtas'/script),'--repo-root',str(root)],cwd=str(root),timeout=180,capture_output=True,text=True)
        except Exception:pass
    print('\nK01 MEDTAS v1.7 PIPELINE',overall);print('Pipeline report:',out);print('Command Center: OPEN_K01_COMMAND_CENTER_V11.cmd')
    return 1 if overall=='HOLD' else 0

if __name__=='__main__':raise SystemExit(main())
