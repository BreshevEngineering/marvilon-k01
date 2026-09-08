from __future__ import annotations
import argparse,json,subprocess,sys,time,traceback
from pathlib import Path

def dump(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def run(root,cmd,timeout=600):
    t=time.time()
    try:
        cp=subprocess.run(cmd,cwd=str(root),text=True,capture_output=True,timeout=timeout)
        return cp.returncode,cp.stdout or '',cp.stderr or '',round(time.time()-t,3),None
    except subprocess.TimeoutExpired as e:return 124,e.stdout or '',e.stderr or '',round(time.time()-t,3),'timeout'
    except Exception as e:return 125,'',traceback.format_exc(),round(time.time()-t,3),str(e)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    out=root/'reports/medtas/pipeline/K01_PIPELINE_RUN_CURRENT.json';log=root/'reports/medtas/logs/current/K01_MEDTAS_PIPELINE.log';log.parent.mkdir(parents=True,exist_ok=True)
    stages=[];cad_ok=False
    def stage(index,title,cmd=None,hard=False,blocked=False,message=None,timeout=600):
        nonlocal cad_ok
        print(f'[{index}/8] {title}',flush=True)
        if blocked:
            rec={'index':index,'title':title,'status':'BLOCKED_UPSTREAM','message':message or 'blocked by previous hard stage','duration_s':0.0,'return_code':None}
            stages.append(rec);print('  BLOCKED_UPSTREAM:',rec['message']);return rec
        rc,so,se,dur,exc=run(root,cmd,timeout) if cmd else (0,'','',0,None)
        status='PASS' if rc==0 else ('HOLD' if hard else 'PASS_WITH_LIMITATIONS')
        rec={'index':index,'title':title,'status':status,'message':message or (se.strip().splitlines()[-1] if se.strip() else so.strip().splitlines()[-1] if so.strip() else ''),'duration_s':dur,'return_code':rc,'command':[str(x) for x in cmd] if cmd else None}
        stages.append(rec)
        with log.open('a',encoding='utf-8') as f:
            f.write(f'\n===== STAGE {index}/8 {title} rc={rc} status={status} =====\n')
            if so:f.write('[STDOUT]\n'+so+'\n')
            if se:f.write('[STDERR]\n'+se+'\n')
        if so:print(so,end='' if so.endswith('\n') else '\n')
        if se:print(se,end='' if se.endswith('\n') else '\n',file=sys.stderr)
        print('  ->',status,f'({dur}s)')
        return rec

    log.write_text('K01 MEDTAS pipeline v1.5\nroot='+str(root)+'\n',encoding='utf-8')
    py=sys.executable
    s1=stage(1,'Canonical hashing self-test',[py,str(root/'tools/medtas/canonical_hash_selftest_v1_5.py')],hard=True)
    hard_block=s1['status']=='HOLD'
    # Compile is deliberately soft: CAD stage has a pywin32 fallback.
    s2=stage(2,'SolidWorks adapters: local interop bundle + compile',[py,str(root/'tools/medtas/compile_sw_exporters_v1_5.py'),'--repo-root',str(root)],hard=False,blocked=hard_block,message='canonical hash core failed' if hard_block else None)
    s3=stage(3,'Real A001 CAD semantic extraction + canonical STATE_HASH',[py,str(root/'tools/medtas/run_cad_sem_a001.py'),'--repo-root',str(root)],hard=True,blocked=hard_block,message='canonical hash core failed' if hard_block else None,timeout=420)
    cad_ok=s3['status']=='PASS'
    s4=stage(4,'Native MBD / DimXpert extraction',[py,str(root/'tools/medtas/build_mbd_a001_v1_4.py'),'--repo-root',str(root)],hard=False,blocked=not cad_ok,message='CAD semantic state unavailable' if not cad_ok else None,timeout=600)
    s5=stage(5,'Canonical snapshot + tolerance + structural/FEMM + drawing/BOM models',[py,str(root/'tools/medtas/build_downstream_v1_2.py'),'--repo-root',str(root)],hard=True,blocked=not cad_ok,message='CAD semantic state unavailable' if not cad_ok else None,timeout=900)
    downstream_ok=s5['status']=='PASS'
    if downstream_ok:
        # Derived artifacts that can be created without inventing engineering data.
        br=stage(5.1,'BOM artifact + semantic parity verification',[py,str(root/'tools/medtas/build_bom_artifact_v1_5.py'),'--repo-root',str(root)],hard=False)
        dr=stage(5.2,'Drawing-as-MBD release workpack',[py,str(root/'tools/medtas/build_drawing_mbd_workpack_v1_5.py'),'--repo-root',str(root)],hard=False)
        # Hide substage numbering from the canonical eight-stage summary but retain detail.
        stages.remove(br);stages.remove(dr)
        s5['substeps']=[br,dr]
        if br['status']!='PASS' or dr['status']!='PASS':s5['status']='PASS_WITH_LIMITATIONS'
    s6=stage(6,'Persistent structural face-map candidate',[py,str(root/'tools/medtas/build_face_map_candidate_v1_3.py'),'--repo-root',str(root)],hard=False,blocked=not downstream_ok,message='solver-neutral structural model unavailable' if not downstream_ok else None)
    s7a=stage(7.1,'CalculiX solver-neutral case scaffold',[py,str(root/'tools/medtas/build_calculix_scaffold_v1_5.py'),'--repo-root',str(root)],hard=False,blocked=not downstream_ok,message='solver-neutral structural model unavailable' if not downstream_ok else None)
    s7=stage(7,'CalculiX preflight / neutral-model readiness',[py,str(root/'tools/medtas/calculix_preflight_v1_5.py'),'--repo-root',str(root)],hard=False)
    stages.remove(s7a);s7['substeps']=[s7a]
    if s7a['status']!='PASS':s7['status']='PASS_WITH_LIMITATIONS'
    s8=stage(8,'Derived-state rebuild + Center feed',[py,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)],hard=False)
    # Determine overall state from hard stages, not from expected engineering OPEN/HOLD frontiers.
    hard_fail=[x for x in stages if x['index'] in (1,3,5) and x['status']=='HOLD']
    overall='HOLD' if hard_fail else ('PASS_WITH_LIMITATIONS' if any(x['status'] in ('PASS_WITH_LIMITATIONS','BLOCKED_UPSTREAM') for x in stages) else 'PASS')
    report={'schema':'k01.medtas.pipeline.v1_5','project':'K01','overall_status':overall,'stages':stages,'hard_failures':[{'index':x['index'],'title':x['title'],'message':x['message']} for x in hard_fail],'principles':{'cad_hash':'canonical semantic snapshot only; native SLDPRT/SLDASM binary SHA is diagnostic','step_hash':'volatile STEP header removed; normalized STEP hash is artifact-stability only','drawing':'native CAD + MBD/DimXpert owns product definition; drawing is derived presentation','stale':'downstream state is recomputed from causal STATE_HASH/ARTIFACT_HASH inputs'}}
    dump(out,report)
    # One final state rebuild lets the center discover the pipeline report without relying on any upstream server.
    try:subprocess.run([py,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)],cwd=str(root),timeout=120)
    except Exception:pass
    print('\nK01 MEDTAS v1.5 PIPELINE',overall);print('Pipeline report:',out);print('Command Center: OPEN_K01_COMMAND_CENTER_V10.cmd')
    return 1 if overall=='HOLD' else 0
if __name__=='__main__':raise SystemExit(main())
