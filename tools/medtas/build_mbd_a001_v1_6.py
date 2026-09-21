from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
from control_authority import require_control_family
from medtas_v16_common import load,dump,graph_path,register_build

def norm_num(v):
    try:
        x=float(v); x=0.0 if abs(x)<1e-15 else x; return format(x,'.12g')
    except Exception:return None

def canonical_doc(raw,document_id):
    anns=[]
    for a in raw.get('annotations',[]) or []:
        x={'name':str(a.get('name') or ''),'annotation_type':str(a.get('annotation_type') or ''),'suppressed':bool(a.get('suppressed',False)),'to_be_inspected':bool(a.get('to_be_inspected',False)),'statistical':bool(a.get('statistical',False)),'free_state':bool(a.get('free_state',False)),'model_feature_name':str(a.get('model_feature_name') or ''),'model_feature_type':str(a.get('model_feature_type') or '')}
        for k in ('nominal_SI','upper_limit_SI','lower_limit_SI'):
            if k in a:x[k]=norm_num(a.get(k))
        for k in ('dimension_type','datum_identifier'):
            if a.get(k) not in (None,''):x[k]=str(a.get(k))
        if 'limit_available' in a:x['limit_available']=bool(a.get('limit_available'))
        anns.append(x)
    anns.sort(key=lambda x:(x['name'],x['annotation_type'],x.get('model_feature_name','')))
    feats=[]
    for f in raw.get('features',[]) or []:
        feats.append({'name':str(f.get('name') or ''),'feature_type':str(f.get('feature_type') or ''),'suppressed':bool(f.get('suppressed',False)),'face_count':f.get('face_count'),'model_feature_name':str(f.get('model_feature_name') or ''),'model_feature_type':str(f.get('model_feature_type') or '')})
    feats.sort(key=lambda x:(x['name'],x['feature_type']))
    return {'document_id':document_id,'configuration':str(raw.get('configuration') or ''),'annotations':anns,'features':feats,'annotation_count':len(anns),'feature_count':len(feats)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    bindp=require_control_family(root,'cad_sem_a001_binding')
    binding=load(bindp)
    rawp=root/binding['raw_api_output'];out=root/'reports/medtas/mbd/current/K01_MBD_A001_v1.json';exe=root/'cad_api/medtas/bin/K01MbdDimXpertPart.exe';log=root/'reports/medtas/logs/current/K01_MBD_DIMXPERT_EXPORT.log'
    limitations=[];docs=[]
    if not rawp.exists():print('ERROR: raw CAD semantic snapshot missing:',rawp,file=sys.stderr);return 51
    raw=load(rawp)
    if raw.get('status')!='OK':print('ERROR: raw CAD semantic snapshot is not OK',file=sys.stderr);return 52
    if not exe.exists(): limitations.append('MBD-API-001: DimXpert exporter unavailable; compile/runtime binding not complete')
    else:
        tmp=root/'reports/medtas/mbd/raw';tmp.mkdir(parents=True,exist_ok=True);log.parent.mkdir(parents=True,exist_ok=True)
        for i,d in enumerate(raw.get('documents',[]) or []):
            path=d.get('native_path');cfg=d.get('configuration') or '';did=Path(str(d.get('title') or path or f'DOC_{i}')).stem
            if not path or not Path(path).exists(): limitations.append('MBD-PATH-MISSING:'+did);continue
            rp=tmp/(did+'.dimxpert.raw.json')
            cp=subprocess.run([str(exe),'--part',str(path),'--config',str(cfg),'--out',str(rp),'--log',str(log)],cwd=str(exe.parent),text=True,capture_output=True,timeout=180)
            with log.open('a',encoding='utf-8') as f:
                if cp.stdout:f.write('\n[STDOUT '+did+']\n'+cp.stdout)
                if cp.stderr:f.write('\n[STDERR '+did+']\n'+cp.stderr)
            if cp.returncode or not rp.exists():limitations.append('MBD-EXTRACT-FAILED:'+did+':rc='+str(cp.returncode));continue
            r=load(rp)
            if r.get('status')!='OK': limitations.append('MBD-EXTRACT-ERROR:'+did+':'+str(r.get('error')));continue
            docs.append(canonical_doc(r,did))
    docs.sort(key=lambda x:x['document_id'])
    ann_count=sum(x['annotation_count'] for x in docs);datum_count=sum(1 for x in docs for y in x['annotations'] if y.get('datum_identifier'));dim_count=sum(1 for x in docs for y in x['annotations'] if 'nominal_SI' in y)
    if ann_count==0:limitations.append('MBD-COVERAGE-001: no DimXpert annotations extracted; current tolerance chain remains controlled-seed-backed until model PMI is authored')
    payload={'schema':'k01.mbd_a001.v1_6','authority':'machine-readable MBD/DimXpert extracted from native part models; paths/timestamps/native binary hashes excluded','documents':docs,'summary':{'documents_extracted':len(docs),'annotations':ann_count,'dimension_tolerances':dim_count,'datums':datum_count},'coverage_status':'MBD_ACTIVE' if ann_count else 'MBD_NOT_YET_AUTHORED','limitations':sorted(set(limitations))}
    dump(out,payload);register_build(root,'K01.MBD.A001',{'tool':'build_mbd_a001_v1_6.py','mode':'SolidWorks DimXpert extraction'},limitations=payload['limitations'])
    subprocess.call([sys.executable,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)])
    print('K01.MBD.A001 built:',payload['coverage_status'],'annotations=',ann_count,'limitations=',len(payload['limitations']))
    return 0
if __name__=='__main__':raise SystemExit(main())
