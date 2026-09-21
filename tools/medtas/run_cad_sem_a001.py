#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys, traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import medtas_state_engine_v1_1 as eng
from v22_common import authority_path
from control_authority import require_domain_authority

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def norm(x):
    if x is None: return None
    try:
        f=float(x)
        if abs(f)<1e-15: f=0.0
        return format(f,'.12g')
    except Exception: return str(x)
def stem_title(s):
    if not s: return ''
    return Path(str(s).replace('\\','/')).stem

DROP_TYPES={'CommentsFolder','FavoriteFolder','HistoryFolder','SelectionSetFolder','SensorFolder','DocsFolder','DetailCabinet','NotesAreaFtrFolder','SurfaceBodyFolder','SolidBodyFolder','EnvFolder','AmbientLight','DirectionLight','EqnFolder','MaterialFolder','OriginProfileFeature'}
STD_PLANES={'Front Plane','Top Plane','Right Plane'}

def collect_feature_semantics(doc):
    dims={}; feats=[]; materials=set(); datums=[]
    explicit_mat=str(doc.get('material_name') or '').strip()
    if explicit_mat: materials.add(explicit_mat)
    for f in doc.get('features',[]) or []:
        name=str(f.get('name','')); typ=str(f.get('type','')); path=str(f.get('path',name))
        if typ=='MaterialFolder' and name: materials.add(name)
        if typ not in DROP_TYPES and not (name in STD_PLANES and not name.startswith('K01_')):
            feats.append({'path':path,'name':name,'type':typ,'suppressed':bool(f.get('suppressed',False))})
            if typ in ('RefPlane','RefAxis') and name.startswith('K01_'):
                datums.append({'name':name,'type':typ,'suppressed':bool(f.get('suppressed',False))})
        for d in f.get('dimensions',[]) or []:
            key=str(d.get('full_name') or (path+'/'+str(d.get('name'))))
            dims[key]={'full_name':key,'system_value_SI':norm(d.get('system_value_SI'))}
    feats=sorted({(x['path'],x['type']):x for x in feats}.values(),key=lambda x:(x['path'],x['type']))
    return feats,[dims[k] for k in sorted(dims)],sorted(materials),sorted(datums,key=lambda x:x['name'])

def canonicalize(raw):
    if raw.get('status')=='ERROR':
        raise RuntimeError('SolidWorks exporter failed at %s: %s'%(raw.get('stage'),raw.get('error')))
    limitations=[]; asm=raw.get('assembly',{})
    instances=[]
    for c in raw.get('instances',[]) or []:
        tr=[norm(v) for v in (c.get('transform') or [])]
        if not c.get('suppressed') and not tr: limitations.append('CADSEM-TRANSFORM-MISSING:'+str(c.get('name')))
        instances.append({'instance':c.get('name'),'document_id':stem_title(c.get('path') or c.get('document_title')),'referenced_configuration':c.get('referenced_configuration') or '','suppressed':bool(c.get('suppressed',False)),'transform':tr})
    instances.sort(key=lambda x:(str(x['instance']),str(x['document_id'])))
    docs=[]
    for d in raw.get('documents',[]) or []:
        feats,dims,mats,datums=collect_feature_semantics(d)
        did=stem_title(d.get('title') or d.get('native_path'))
        if not feats: limitations.append('CADSEM-FEATURES-MISSING:'+did)
        if not mats: limitations.append('CADSEM-MATERIAL-MISSING:'+did)
        face_inventory=[]
        for f in d.get('faces',[]) or []:
            row={'body':f.get('body'),'surface_type':f.get('surface_type'),'area_m2':norm(f.get('area_m2')),'box_m':[norm(v) for v in (f.get('box_m') or [])],'normal':[norm(v) for v in (f.get('normal') or [])],'edge_count':f.get('edge_count')}
            for pk in ('plane_params','cylinder_params','cone_params','sphere_params','torus_params'):
                if f.get(pk): row[pk]=[norm(v) for v in (f.get(pk) or [])]
            face_inventory.append(row)
        face_inventory.sort(key=lambda x:(str(x.get('body')),str(x.get('surface_type')),str(x.get('area_m2')),str(x.get('box_m'))))
        docs.append({'document_id':did,'referenced_configuration':d.get('configuration') or '','materials':mats,'solid_body_count':d.get('solid_body_count'),'feature_states':feats,'dimensions':dims,'datums':datums,'face_inventory':face_inventory})
    docs.sort(key=lambda x:x['document_id'])
    mates=[{'name':m.get('name'),'type':m.get('type'),'suppressed':bool(m.get('suppressed',False))} for m in (raw.get('mates',[]) or [])]
    mates.sort(key=lambda x:(str(x['name']),str(x['type'])))
    if not instances: limitations.append('CADSEM-COMPONENTS-MISSING')
    if not asm.get('configuration'): limitations.append('CADSEM-ASSEMBLY-CONFIG-MISSING')
    if not mates: limitations.append('CADSEM-MATES-NOT-EXTRACTED')
    for e in raw.get('errors',[]) or []: limitations.append('CADSEM-API-WARNING:'+str(e))
    return {'schema':'medtas.k01.cad_sem_a001.v1_4','assembly':{'assembly_id':stem_title(asm.get('title') or asm.get('native_path')),'configuration':asm.get('configuration') or '','component_instance_count':len(instances)},'instances':instances,'documents':docs,'mates':mates,'completeness':{'component_instances':bool(instances),'assembly_configuration':bool(asm.get('configuration')),'component_transforms':all(x['suppressed'] or bool(x['transform']) for x in instances),'part_feature_semantics':all(bool(x['feature_states']) for x in docs) if docs else False,'material_assignments':all(bool(x['materials']) for x in docs) if docs else False,'mate_features':bool(mates)},'limitations':sorted(set(limitations))}

def choose_assembly(root,binding):
    src=binding.get('source_selection') or {}
    if src.get('mode')!='ENGINEERING_BASELINE_AUTHORITY':
        raise RuntimeError('CAD semantic binding source mode must be ENGINEERING_BASELINE_AUTHORITY')
    bp=require_domain_authority(root,src.get('authority_key') or 'engineering_baseline')
    baseline=load(bp); value=baseline
    for key in src.get('authority_field') or ['cad','assembly']:
        if not isinstance(value,dict) or key not in value:
            raise RuntimeError(f'Engineering baseline field missing: {src.get("authority_field")}')
        value=value[key]
    assembly=str(value or '').strip()
    if not assembly: raise RuntimeError('Engineering baseline assembly path is empty')
    p=Path(assembly)
    if not p.exists(): raise FileNotFoundError('Engineering baseline assembly missing: '+assembly)
    return assembly,'engineering_baseline_authority'

def write_failure(root,stage,exc,extra=None):
    out=root/'reports/control/K01_MEDTAS_LAST_FAILURE.json'
    payload={'schema':'k01.medtas.failure.v1','stage':stage,'error':str(exc),'traceback':traceback.format_exc(),'extra':extra or {}}
    dump(out,payload)
    try:
        subprocess.call([sys.executable,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)])
    except Exception: pass
    print('MEDTAS FAILURE:',stage,str(exc),file=sys.stderr)
    print('Failure report:',out,file=sys.stderr)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    binding_path=authority_path(root,'cad_sem_a001_binding')
    if binding_path is None: raise RuntimeError('Declared CAD semantic binding authority missing')
    try:
        binding=load(binding_path); assembly,source=choose_assembly(root,binding)
        raw=root/binding['raw_api_output']; canonical=root/binding['canonical_output']; record=root/binding['build_record']
        exe=root/'cad_api/medtas/bin/K01CadSemanticA001.exe'; log=root/'reports/medtas/logs/current/K01_CAD_SEM_A001_EXPORT.log'
        raw.parent.mkdir(parents=True,exist_ok=True); canonical.parent.mkdir(parents=True,exist_ok=True); record.parent.mkdir(parents=True,exist_ok=True); log.parent.mkdir(parents=True,exist_ok=True)
        print('Selected assembly:',assembly,'source=',source,flush=True)
        # Prefer early-bound C# for rich typed API access. If runtime binding or a
        # machine-specific interop issue blocks it, fall back to the pywin32 route
        # that already proved stable in earlier K01 Gate01 probes. Both adapters feed
        # the same canonicalizer, so there is still one semantic truth model.
        adapter='csharp'
        cp=None
        if exe.exists():
            cmd=[str(exe),'--assembly',assembly,'--out',str(raw),'--log',str(log)]
            cp=subprocess.run(cmd,cwd=str(exe.parent),text=True,capture_output=True,timeout=300)
            if cp.stdout: print(cp.stdout,end='')
            if cp.stderr: print(cp.stderr,end='',file=sys.stderr)
            with log.open('a',encoding='utf-8') as f:
                if cp.stdout: f.write('\n[C# STDOUT]\n'+cp.stdout)
                if cp.stderr: f.write('\n[C# STDERR]\n'+cp.stderr)
                f.write('\n[C# RETURN CODE] %d\n'%cp.returncode)
        if cp is None or cp.returncode!=0:
            adapter='pywin32'
            print('C# adapter unavailable/failed; trying pywin32 fallback...',flush=True)
            py=root/'tools/medtas/sw_semantic_pywin32_v1_5.py'
            cp2=subprocess.run([sys.executable,str(py),'--assembly',assembly,'--out',str(raw),'--log',str(log)],cwd=str(root),text=True,capture_output=True,timeout=300)
            if cp2.stdout: print(cp2.stdout,end='')
            if cp2.stderr: print(cp2.stderr,end='',file=sys.stderr)
            with log.open('a',encoding='utf-8') as f:
                if cp2.stdout: f.write('\n[PYWIN32 STDOUT]\n'+cp2.stdout)
                if cp2.stderr: f.write('\n[PYWIN32 STDERR]\n'+cp2.stderr)
                f.write('\n[PYWIN32 RETURN CODE] %d\n'%cp2.returncode)
            if cp2.returncode!=0:
                csrc='not run' if cp is None else ('rc='+str(cp.returncode))
                raise RuntimeError('Both CAD semantic adapters failed (C# '+csrc+', pywin32 rc='+str(cp2.returncode)+'). See '+str(log))
        if not raw.exists(): raise RuntimeError('Exporter returned success but raw JSON is missing: '+str(raw))
        rawj=load(raw); canon=canonicalize(rawj); dump(canonical,canon)
        # Rebuild once to compute the current hash before writing its build record.
        graph_path=authority_path(root,'engineering_build_graph')
        if graph_path is None: raise RuntimeError('Declared engineering build graph authority missing')
        graph=load(graph_path); records=eng.load_record_store(record.parent); verifs=eng.load_record_store(root/'reports/medtas/verifications/current')
        derived=eng.evaluate_graph(graph,root,records,verifs); c=derived['K01.CAD.SEM.A001']
        br={'schema':'medtas.build_record.v1','node_id':'K01.CAD.SEM.A001','built_state_hash':c['state_hash'],'artifact_hash':c['artifact_hash'],'producer':{'raw_api_adapter':adapter,'csharp_exporter':'cad_api/medtas/bin/K01CadSemanticA001.exe','pywin32_fallback':'tools/medtas/sw_semantic_pywin32_v1_5.py','canonicalizer':'tools/medtas/run_cad_sem_a001.py'},'source_assembly':{'selection':source,'display_name':Path(assembly).name},'raw_snapshot':binding['raw_api_output'],'canonical_snapshot':binding['canonical_output'],'completeness':canon.get('completeness',{}),'limitations':canon.get('limitations',[])}
        dump(record,br)
        fail=root/'reports/control/K01_MEDTAS_LAST_FAILURE.json'
        if fail.exists(): fail.unlink()
        subprocess.check_call([sys.executable,str(root/'tools/medtas/rebuild_medtas_state.py'),'--repo-root',str(root)])
        final=load(root/'reports/control/K01_MEDTAS_DERIVED_STATE_CURRENT.json')['nodes']['K01.CAD.SEM.A001']
        print('K01.CAD.SEM.A001 STATE =',final['state'])
        print('STATE_HASH    =',final['state_hash'])
        print('ARTIFACT_HASH =',final['artifact_hash'])
        if canon.get('limitations'):
            print('LIMITATIONS:')
            for x in canon['limitations']: print(' -',x)
        return 0
    except subprocess.TimeoutExpired as e:
        write_failure(root,'CAD_SEM_EXPORT_TIMEOUT',e,{'timeout_s':300}); return 41
    except Exception as e:
        write_failure(root,'CAD_SEM_A001',e); return 42
if __name__=='__main__': raise SystemExit(main())
