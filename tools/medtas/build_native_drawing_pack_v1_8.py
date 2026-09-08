from __future__ import annotations
import argparse,subprocess,sys
from pathlib import Path
from medtas_v16_common import load,dump,base_id,register_build,register_verify,sha256_file

def cad_binding(root):
    for n in ('K01_CAD_SEM_A001_BINDING_v1_6.json','K01_CAD_SEM_A001_BINDING_v1_5.json'):
        p=root/'control/medtas/v1/bindings'/n
        if p.exists():return load(p)
    return {}

def native_paths(root):
    b=cad_binding(root);rawp=root/b.get('raw_api_output','reports/cad/current/K01_A001_SEMANTIC_RAW_API_v1_4.json');raw=load(rawp) if rawp.exists() else {};out={}
    for d in raw.get('documents',[]) or []:
        pid=base_id(d.get('title') or d.get('native_path'));p=d.get('native_path')
        if pid and p:out[pid]=p
    cadp=root/b.get('canonical_output','reports/medtas/cad/current/K01_CAD_SEM_A001.json');cad=load(cadp) if cadp.exists() else {}
    asm=cad.get('source_assembly') or cad.get('assembly_path') or (cad.get('assembly') or {}).get('source_path')
    if asm:out['K01-A-001']=asm
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();planp=r/'reports/drawing/current/K01_DRAWING_RELEASE_PLAN_CURRENT.json';out=r/'reports/medtas/drawing/current/K01_DRAWING_ARTIFACT_GATE04E_v1_8.json';jobp=r/'reports/medtas/drawing/current/K01_DRAWING_GENERATION_JOB_v1_8.json';rawrep=r/'reports/medtas/drawing/current/K01_DRAWING_GENERATION_RAW_v1_8.json'
    if not planp.exists():print('BLOCKED: drawing release plan missing');return 2
    plan=load(planp);bind=load(r/'control/medtas/v1/bindings/K01_DRAWING_GENERATION_BINDING_v1_7.json',{}) or {};template=bind.get('template_path');block=[]
    if not template or not Path(str(template)).exists():block.append('DRAWING-TEMPLATE-001: controlled .drwdot template is not bound/found')
    exe=r/'cad_api/medtas/bin/K01DrawingPackGenerator.exe'
    if not exe.exists():block.append('DRAWING-EXEC-001: K01DrawingPackGenerator.exe not compiled')
    readyset=set(plan.get('ready_drawings',[]) or []);paths=native_paths(r);items=[];rootout=r/(bind.get('output_root') or 'drawings/release_candidate/gate04e')
    for d in plan.get('drawings',[]) or []:
        if d.get('drawing_no') not in readyset:continue
        model=d.get('model');src=paths.get(base_id(model)) or paths.get(model)
        if not src or not Path(str(src)).exists():block.append('DRAWING-MODEL-PATH-001:'+str(model));continue
        dn=d['drawing_no'];folder=rootout/dn;items.append({'drawing_no':dn,'model':model,'model_path':str(src),'slddrw_path':str((folder/(dn+'.SLDDRW')).resolve()),'pdf_path':str((folder/(dn+'.pdf')).resolve())})
    if not items:block.append('DRAWING-READY-001: no drawing currently has a complete product-definition gate')
    if block:
        payload={'schema':'k01.drawing_artifact_gate04e.v1_8','status':'BLOCKED','artifacts':[],'ready_drawings':sorted(readyset),'blocking_items':sorted(set(block)),'not_generated_drawings':[d.get('drawing_no') for d in plan.get('drawings',[]) if d.get('drawing_no') not in readyset],'policy':'Per-drawing generation. No placeholder or dimension-inventing drawing is emitted.'};dump(out,payload);print('BLOCKED native drawing pack');[print(' -',x) for x in sorted(set(block))];return 1
    job={'schema':'k01.drawing_generation_job.v1_8','template_path':str(Path(template).resolve()),'items':items,'annotation_policy':'MANUAL_PLACEMENT_FROM_NATIVE_MBD','auto_dimension':False,'blanket_model_item_import':False,'source_product_definition':'reports/medtas/product_definition/current/K01_PRODUCT_DEFINITION_GATE04E_v1_8.json'};dump(jobp,job)
    cp=subprocess.run([str(exe),'--job',str(jobp),'--out',str(rawrep)],cwd=str(r),text=True,capture_output=True,timeout=1200)
    if cp.stdout:print(cp.stdout,end='')
    if cp.stderr:print(cp.stderr,end='',file=sys.stderr)
    raw=load(rawrep) if rawrep.exists() else {'status':'ERROR','error':'generator report missing'};arts=[];issues=list(raw.get('errors',[]) or [])
    for x in raw.get('items',[]) or []:
        for k in ('slddrw_path','pdf_path'):
            p=Path(str(x.get(k) or ''))
            if p.exists():arts.append({'drawing_no':x.get('drawing_no'),'kind':'SLDDRW' if k=='slddrw_path' else 'PDF','path':p.relative_to(r).as_posix() if str(p).startswith(str(r)) else str(p),'size':p.stat().st_size,'sha256':sha256_file(p)})
            else:issues.append(str(x.get('drawing_no'))+':missing '+k)
    expected=2*len(items);status='PASS' if cp.returncode==0 and raw.get('status')=='PASS' and len(arts)==expected and not issues else 'HOLD'
    payload={'schema':'k01.drawing_artifact_gate04e.v1_8','status':status,'template_path':str(template),'generated_drawings':sorted(readyset),'not_generated_drawings':[d.get('drawing_no') for d in plan.get('drawings',[]) if d.get('drawing_no') not in readyset],'generation_job':jobp.relative_to(r).as_posix(),'raw_generation_report':rawrep.relative_to(r).as_posix(),'artifacts':arts,'issues':sorted(set(issues)),'policy':'Only drawings whose own product-definition gate is complete are generated. API creates template/views skeleton only; dimensions/PMI are intentionally placed by the engineer from native model MBD. Artifact PASS does not replace semantic/visual QA.'};dump(out,payload)
    if status=='PASS':
        register_build(r,'K01.DRAWING.ARTIFACT.GATE04E',{'tool':'K01DrawingPackGenerator.exe + build_native_drawing_pack_v1_8.py','template':str(template)});register_verify(r,'K01.DRAWING.ARTIFACT.GATE04E','PASS_WITH_LIMITATIONS' if len(readyset)<len(plan.get('drawings',[])) else 'PASS',metrics={'generated_drawings':len(readyset),'artifacts':len(arts)},notes='Per-drawing artifact generation. Remaining drawings can stay blocked without invalidating generated candidates.')
    print(status,'native drawing pack artifacts=',len(arts));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
