from __future__ import annotations
import argparse,subprocess,sys
from pathlib import Path
from medtas_v16_common import load,dump,base_id,sha256_file

def cad_binding(root):
    for n in ('K01_CAD_SEM_A001_BINDING_v1_6.json','K01_CAD_SEM_A001_BINDING_v1_5.json'):
        p=root/'control/medtas/v1/bindings'/n
        if p.exists(): return load(p,{}) or {}
    return {}

def p007_native(root):
    b=cad_binding(root);rawp=root/b.get('raw_api_output','reports/cad/current/K01_A001_SEMANTIC_RAW_API_v1_4.json')
    raw=load(rawp,{}) or {}
    for d in raw.get('documents',[]) or []:
        pid=base_id(d.get('title') or d.get('native_path'))
        if pid=='K01-P-007' and d.get('native_path'): return Path(str(d['native_path']))
    return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve()
    bind=load(r/'control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json',{}) or {};template=Path(str(bind.get('template_path') or ''));src=p007_native(r);exe=r/'cad_api/medtas/bin/K01DrawingPackGenerator.exe';issues=[]
    if not template.is_file():issues.append('P007-DRAFT-TEMPLATE-001: controlled drawing template is not bound/found')
    if src is None or not src.is_file():issues.append('P007-DRAFT-MODEL-001: current native K01-P-007 model path not resolved')
    if not exe.is_file():issues.append('P007-DRAFT-EXEC-001: drawing generator is not compiled; run pipeline compile stage')
    outdir=r/'drawings/work/K01-D-006';sld=outdir/'K01-D-006_P007_EXEMPLAR_DRAFT.SLDDRW';pdf=outdir/'K01-D-006_P007_EXEMPLAR_DRAFT.pdf';jobp=r/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_GENERATION_JOB_CURRENT.json';rawp=r/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_GENERATION_RAW_CURRENT.json';manifest=r/'reports/drawing/current/K01-D-006_P007_EXEMPLAR_ARTIFACT_CURRENT.json'
    if issues:
        dump(manifest,{'schema':'k01.drawing_p007_exemplar_artifact.v1_9','status':'BLOCKED','issues':issues,'policy':'Draft skeleton only; not a release artifact.'});print('BLOCKED P007 exemplar skeleton');[print(' -',x) for x in issues];return 1
    outdir.mkdir(parents=True,exist_ok=True)
    job={'schema':'k01.p007_exemplar_generation_job.v1_9','template_path':str(template.resolve()),'items':[{'drawing_no':'K01-D-006','model':'K01-P-007','model_path':str(src.resolve()),'slddrw_path':str(sld.resolve()),'pdf_path':str(pdf.resolve())}],'annotation_policy':'MANUAL_PLACEMENT_FROM_NATIVE_MBD','auto_dimension':False,'blanket_model_item_import':False,'release_state':'DRAFT_FOR_MANUFACTURER_REVIEW'};dump(jobp,job)
    cp=subprocess.run([str(exe),'--job',str(jobp),'--out',str(rawp)],cwd=str(r),capture_output=True,text=True,timeout=1200)
    if cp.stdout:print(cp.stdout,end='' if cp.stdout.endswith('\n') else '\n')
    if cp.stderr:print(cp.stderr,end='' if cp.stderr.endswith('\n') else '\n',file=sys.stderr)
    raw=load(rawp,{}) or {};arts=[]
    for kind,p in [('SLDDRW',sld),('PDF',pdf)]:
        if p.exists():arts.append({'kind':kind,'path':p.relative_to(r).as_posix(),'size':p.stat().st_size,'sha256':sha256_file(p)})
        else:issues.append('P007-DRAFT-MISSING-'+kind)
    status='PASS_DRAFT' if cp.returncode==0 and len(arts)==2 and not issues else 'HOLD'
    payload={'schema':'k01.drawing_p007_exemplar_artifact.v1_9','status':status,'drawing_no':'K01-D-006','part_number':'K01-P-007','template_path':str(template.resolve()),'model_path':str(src.resolve()),'artifacts':arts,'issues':issues,'policy':'This is a non-released exemplar skeleton. API creates standard views only. Engineer intentionally places dimensions/PMI from the native model; no AutoDimension and no independent duplicate tolerance authoring.'};dump(manifest,payload);print(status,'P007 exemplar skeleton:',manifest);return 0 if status=='PASS_DRAFT' else 1
if __name__=='__main__':raise SystemExit(main())
