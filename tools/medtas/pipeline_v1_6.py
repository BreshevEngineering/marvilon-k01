from __future__ import annotations
import argparse,json,subprocess,sys,time,traceback
from pathlib import Path

def dump(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def run(root,cmd,timeout=600):
    t=time.time()
    try:
        cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True,timeout=timeout)
        return cp.returncode,cp.stdout or '',cp.stderr or '',round(time.time()-t,3)
    except subprocess.TimeoutExpired as e:return 124,e.stdout or '',e.stderr or '',round(time.time()-t,3)
    except Exception:return 125,'',traceback.format_exc(),round(time.time()-t,3)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();py=sys.executable;out=root/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json';log=root/'reports/medtas/logs/current/K01_MEDTAS_PIPELINE.log';log.parent.mkdir(parents=True,exist_ok=True);log.write_text('K01 MEDTAS pipeline v1.6\nroot='+str(root)+'\n',encoding='utf-8');stages=[]
    def stage(idx,title,cmd=None,hard=False,blocked=False,timeout=600):
        print(f'[{idx}/8] {title}',flush=True)
        if blocked:
            r={'index':idx,'title':title,'status':'BLOCKED_UPSTREAM','duration_s':0,'return_code':None};stages.append(r);print('  -> BLOCKED_UPSTREAM');return r
        rc,so,se,dur=run(root,cmd,timeout) if cmd else (0,'','',0)
        status='PASS' if rc==0 else ('HOLD' if hard else 'PASS_WITH_LIMITATIONS')
        r={'index':idx,'title':title,'status':status,'duration_s':dur,'return_code':rc,'command':[str(x) for x in cmd] if cmd else None,'message':(se.strip().splitlines()[-1] if se.strip() else so.strip().splitlines()[-1] if so.strip() else '')};stages.append(r)
        with log.open('a',encoding='utf-8') as f:
            f.write(f'\n===== STAGE {idx}/8 {title} rc={rc} status={status} =====\n');
            if so:f.write('[STDOUT]\n'+so+'\n')
            if se:f.write('[STDERR]\n'+se+'\n')
        if so:print(so,end='' if so.endswith('\n') else '\n')
        if se:print(se,end='' if se.endswith('\n') else '\n',file=sys.stderr)
        print('  ->',status,f'({dur}s)');return r
    def sub(parent,label,title,cmd,timeout=600):
        rc,so,se,dur=run(root,cmd,timeout);status='PASS' if rc==0 else 'PASS_WITH_LIMITATIONS';rec={'label':label,'title':title,'status':status,'return_code':rc,'duration_s':dur,'message':(se.strip().splitlines()[-1] if se.strip() else so.strip().splitlines()[-1] if so.strip() else '')};parent.setdefault('substeps',[]).append(rec)
        if so:print(so,end='' if so.endswith('\n') else '\n')
        if se:print(se,end='' if se.endswith('\n') else '\n',file=sys.stderr)
        if status!='PASS' and parent['status']=='PASS':parent['status']='PASS_WITH_LIMITATIONS'
        return rec
    s1=stage(1,'Canonical hashing self-test',[py,str(root/'tools/medtas/canonical_hash_selftest_v1_5.py')],hard=True);core=s1['status']=='PASS'
    s2=stage(2,'SolidWorks adapters: local interop bundle + compile',[py,str(root/'tools/medtas/compile_sw_exporters_v1_6.py'),'--repo-root',str(root)],hard=False,blocked=not core)
    s3=stage(3,'Real A001 CAD semantic extraction + canonical STATE_HASH',[py,str(root/'tools/medtas/run_cad_sem_a001.py'),'--repo-root',str(root)],hard=True,blocked=not core,timeout=420);cad=s3['status']=='PASS'
    s4=stage(4,'Native MBD / DimXpert extraction',[py,str(root/'tools/medtas/build_mbd_a001_v1_6.py'),'--repo-root',str(root)],hard=False,blocked=not cad,timeout=900)
    if cad:sub(s4,'4.1','Read-only MBD authoring candidate map',[py,str(root/'tools/medtas/build_mbd_authoring_candidates_v1_6.py'),'--repo-root',str(root)])
    s5=stage(5,'Canonical snapshot + tolerance + structural/FEMM + drawing/BOM models',[py,str(root/'tools/medtas/build_downstream_v1_6.py'),'--repo-root',str(root)],hard=True,blocked=not cad,timeout=900);down=s5['status']=='PASS'
    if down:
        sub(s5,'5.1','BOM artifact + semantic parity',[py,str(root/'tools/medtas/build_bom_artifact_v1_5.py'),'--repo-root',str(root)])
        sub(s5,'5.2','Drawing-as-MBD release workpack',[py,str(root/'tools/medtas/build_drawing_mbd_workpack_v1_6.py'),'--repo-root',str(root)])
    s6=stage(6,'Persistent structural derivation',[py,str(root/'tools/medtas/build_face_map_candidate_v1_6.py'),'--repo-root',str(root)],hard=False,blocked=not down)
    if down:
        sub(s6,'6.1','M2.5 preload equivalence scaffold',[py,str(root/'tools/medtas/build_bolt_equiv_scaffold_v1_6.py'),'--repo-root',str(root)])
        # Neutral STEP export is useful before face-role confirmation and does not write native CAD.
        sub(s6,'6.2','P003/P007 neutral STEP export',[py,str(root/'tools/medtas/export_structural_neutral_geometry_v1_6.py'),'--repo-root',str(root)],timeout=420)
    s7=stage(7,'CalculiX readiness / controlled input gate',[py,str(root/'tools/medtas/calculix_preflight_v1_6.py'),'--repo-root',str(root)],hard=False)
    s8=stage(8,'Derived-state rebuild + Center feed',[py,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)],hard=False)
    hard_fail=[x for x in stages if x['index'] in (1,3,5) and x['status']=='HOLD'];overall='HOLD' if hard_fail else ('PASS_WITH_LIMITATIONS' if any(x['status'] in ('PASS_WITH_LIMITATIONS','BLOCKED_UPSTREAM') for x in stages) else 'PASS')
    report={'schema':'k01.medtas.pipeline.v1_6','project':'K01','overall_status':overall,'stages':stages,'hard_failures':[{'index':x['index'],'title':x['title'],'message':x.get('message')} for x in hard_fail],'principles':{'cad_hash':'canonical semantic snapshot only; native SLDPRT/SLDASM SHA is diagnostic','hash_qualification':'two deterministic exports + no-change native saves','step_hash':'volatile STEP header removed; normalized STEP hash is artifact-stability only','mbd':'native CAD + MBD/DimXpert owns product definition; drawing is derived','calculix':'face roles + neutral STEP + quadratic mesh + reviewed bolt/preload equivalence + controlled input deck','stale':'confirmed face signatures persist until a causal CAD change removes them'}};dump(out,report)
    try:subprocess.run([py,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)],cwd=str(root),timeout=120)
    except Exception:pass
    print('\nK01 MEDTAS v1.6 PIPELINE',overall);print('Pipeline report:',out);print('Command Center: OPEN_K01_COMMAND_CENTER_V10.cmd');return 1 if overall=='HOLD' else 0
if __name__=='__main__':raise SystemExit(main())
