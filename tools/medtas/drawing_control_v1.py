#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, shutil
from pathlib import Path

REGISTRY = Path('control/drawings/K01_DRAWING_REGISTRY_CURRENT.json')
REPORT = Path('reports/control/K01_DRAWING_CONTROL_CURRENT.json')
RETENTION = Path('control/drawings/K01_DRAWING_CANDIDATE_RETENTION_POLICY_CURRENT.json')


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception:
        return default


def sha256(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()


def artifact(p: Path):
    return {'path':str(p),'exists':p.is_file(),'sha256':sha256(p) if p.is_file() else None,'size_bytes':p.stat().st_size if p.is_file() else None}


def atomic_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_name(dst.name+'.tmp')
    if tmp.exists(): tmp.unlink()
    shutil.copy2(src,tmp)
    os.replace(tmp,dst)


def latest_candidates(output_root: Path):
    if not output_root.is_dir(): return []
    q=[]
    for p in output_root.iterdir():
        if not p.is_dir(): continue
        m=p/'candidate_manifest.json'
        if not m.is_file(): continue
        d=load_json(m,{}) or {}
        q.append((p,d,m))
    q.sort(key=lambda x:x[0].stat().st_mtime,reverse=True)
    return q




def semantic_status(candidate: Path):
    rp=candidate/'evidence'/'semantic_report.txt'
    if not rp.is_file(): return None
    try:
        for line in rp.read_text(encoding='utf-8-sig',errors='replace').splitlines():
            if line.startswith('STATUS='):
                return line.split('=',1)[1].strip()
    except Exception:
        return None
    return None


def invalidate_current_marker(spec: dict, drawing_id: str, candidate: Path, semantic):
    output_root=Path(spec['output_root']); drawings_root=output_root.parent.parent; current_dir=drawings_root/'current'/drawing_id
    current_dir.mkdir(parents=True,exist_ok=True)
    marker=current_dir/'DO_NOT_USE__INCOMPLETE_CANDIDATE.txt'
    marker.write_text('K01 DRAWING CONTROL HOLD\nDrawing: '+drawing_id+'\nCandidate: '+candidate.name+'\nSemantic status: '+str(semantic)+'\nThis candidate is evidence only and is not a routine/manufacturing current drawing.\n',encoding='utf-8')
    pointer={'schema':'k01.drawing_current_projection.v1','drawing_id':drawing_id,'status':'HOLD_INCOMPLETE_CANDIDATE','use_for_routine_work':False,'candidate_id':candidate.name,'semantic_status':semantic,'updated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'rule':'Do not use. Close Product Definition / semantic coverage, rebuild, then publish a PASS candidate.'}
    (current_dir/'CURRENT.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return str(marker)

def preferred_artifacts(candidate: Path, manifest: dict, drawing_id: str):
    manual=Path((manifest.get('paths') or {}).get('manual_finish') or (candidate/'manual_finish'))
    generated=Path((manifest.get('paths') or {}).get('generated') or (candidate/'generated'))
    md=manual/(drawing_id+'_ISO_FINISH.SLDDRW'); mp=manual/(drawing_id+'_ISO_FINISH.PDF')
    gd=generated/(drawing_id+'.SLDDRW'); gp=generated/(drawing_id+'.PDF'); gb=generated/(drawing_id+'.BMP')
    if md.is_file():
        return 'MANUAL_FINISH',md,mp if mp.is_file() else None,gb if gb.is_file() else None
    return 'GENERATED',gd,gp if gp.is_file() else None,gb if gb.is_file() else None


def publish_current(drawing_id: str, spec: dict, candidate: Path, manifest: dict):
    output_root=Path(spec['output_root'])
    drawings_root=output_root.parent.parent
    current_dir=drawings_root/'current'/drawing_id
    stage,dwg,pdf,bmp=preferred_artifacts(candidate,manifest,drawing_id)
    if not dwg.is_file():
        return {'status':'HOLD_CURRENT_ARTIFACT_MISSING','current_dir':str(current_dir),'source_candidate':str(candidate),'preferred_stage':stage}
    current_dir.mkdir(parents=True,exist_ok=True)
    dst_d=current_dir/(drawing_id+'.SLDDRW'); atomic_copy(dwg,dst_d)
    dst_p=current_dir/(drawing_id+'.PDF')
    if pdf and pdf.is_file(): atomic_copy(pdf,dst_p)
    dst_b=current_dir/(drawing_id+'.BMP')
    if bmp and bmp.is_file(): atomic_copy(bmp,dst_b)
    src_manifest=candidate/'candidate_manifest.json'
    dst_m=current_dir/'candidate_manifest.json'
    if src_manifest.is_file(): atomic_copy(src_manifest,dst_m)
    pointer={
      'schema':'k01.drawing_current_projection.v1','drawing_id':drawing_id,'part_id':spec.get('part_id'),'title':spec.get('title'),
      'preferred_stage':stage,'candidate_id':candidate.name,'candidate_root':str(candidate),'updated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'source_model':{'path':spec.get('model_path'),'sha256':(manifest.get('source_model') or {}).get('sha256')},
      'spec':manifest.get('spec') or {},'release':'HOLD' if spec.get('release_blockers') else 'CANDIDATE_READY',
      'artifacts':{'drawing':artifact(dst_d),'pdf':artifact(dst_p),'bmp':artifact(dst_b)},
      'rule':'Stable current projection only. Candidate history remains under candidates/<drawing_id>; engineering authority remains upstream Product Definition/requirements/CAD.'
    }
    (current_dir/'CURRENT.json').write_text(json.dumps(pointer,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'status':'PASS_CURRENT_PUBLISHED','current_dir':str(current_dir),'preferred_stage':stage,'pointer':str(current_dir/'CURRENT.json'),'artifacts':pointer['artifacts']}


def refresh(root: Path, publish: bool=True):
    reg=load_json(root/REGISTRY,{}) or {}
    retention=load_json(root/RETENTION,{}) or {}
    out={'schema':'k01.drawing_control.current.v1','project':'K01','generated_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'system_pointer':'control/drawings/K01_DRAWING_SYSTEM_CURRENT.json','registry':str(REGISTRY).replace('\\','/'),'retention_policy':str(RETENTION).replace('\\','/'),'status':'PASS','drawings':{},'summary':{}}
    total_candidates=0; holds=[]
    for drawing_id,entry in (reg.get('drawings') or {}).items():
        sp=root/entry.get('spec','')
        spec=load_json(sp,{}) or {}
        row={'drawing_id':drawing_id,'part_id':entry.get('part_id'),'title':entry.get('title'),'registry_status':entry.get('status'),'spec':entry.get('spec'),'trace':entry.get('trace'),'runner':entry.get('runner'),'native_model':spec.get('model_path'),'assembly':r'D:\Marvilon\K01\cad\assemblies\K01-A-001_Calibration_Module.SLDASM','release_blockers':spec.get('release_blockers',[])}
        if not sp.is_file() or not spec.get('output_root'):
            row['status']='HOLD_SPEC_MISSING'; holds.append(drawing_id);out['drawings'][drawing_id]=row;continue
        q=latest_candidates(Path(spec['output_root'])); row['candidate_count']=len(q);total_candidates+=len(q)
        if not q:
            row['status']='READY_NO_RUNTIME_CANDIDATE';out['drawings'][drawing_id]=row;continue
        candidate,manifest,mp=q[0];row['latest_candidate']=candidate.name;row['candidate_root']=str(candidate);row['candidate_state']=manifest.get('state');row['source_model_hash']=(manifest.get('source_model') or {}).get('sha256');row['spec_hash']=(manifest.get('spec') or {}).get('sha256')
        sem=manifest.get('semantic_status') or semantic_status(candidate);row['semantic_status']=sem
        semantic_pass=bool(sem and sem.startswith('PASS_'))
        presentation=manifest.get('presentation_status')
        if presentation is not None: row['presentation_status']=presentation
        if not semantic_pass:
            row['status']='HOLD_INCOMPLETE_CANDIDATE';holds.append(drawing_id)
            if publish: row['current_invalid_marker']=invalidate_current_marker(spec,drawing_id,candidate,sem)
            out['drawings'][drawing_id]=row;continue
        if presentation is not None and not str(presentation).startswith('PASS_'):
            row['status']='HOLD_PRESENTATION';holds.append(drawing_id)
            out['drawings'][drawing_id]=row;continue
        if publish:
            pub=publish_current(drawing_id,spec,candidate,manifest);row['current']=pub
            row['status']='PASS' if pub.get('status')=='PASS_CURRENT_PUBLISHED' else pub.get('status')
            if row['status']!='PASS': holds.append(drawing_id)
        else: row['status']='PASS_CANDIDATE_DISCOVERED'
        out['drawings'][drawing_id]=row
    out['summary']={'drawing_count':len(out['drawings']),'candidate_count':total_candidates,'hold_count':len(holds),'holds':holds,'navigation_root':r'D:\Marvilon\K01\cad\drawings\current','candidate_history_root':r'D:\Marvilon\K01\cad\drawings\candidates','manual_visual_finish_default':True,'auto_delete_candidates':False}
    if holds: out['status']='HOLD_PARTIAL_DRAWING_CONTROL'
    rp=root/REPORT;rp.parent.mkdir(parents=True,exist_ok=True);rp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return out


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--audit-only',action='store_true');a=ap.parse_args();root=Path(a.repo_root).resolve()
    try:
        o=refresh(root,publish=not a.audit_only)
        print('STATUS: '+o['status'])
        print('DRAWINGS: '+str(o['summary']['drawing_count']))
        print('CANDIDATES: '+str(o['summary']['candidate_count']))
        print('CURRENT ROOT: '+o['summary']['navigation_root'])
        for did,row in o['drawings'].items():
            print(f"  {did}: {row.get('status')} | candidates={row.get('candidate_count',0)} | latest={row.get('latest_candidate','NONE')}")
        print('REPORT: '+str(root/REPORT))
        print('RULE: use current/<drawing_id> for routine work; candidates/ is history only; no automatic deletion.')
        return 0 if o['status'].startswith('PASS') else 3
    except Exception as e:
        print('STATUS: HOLD_DRAWING_CONTROL_V1');print('ERROR:',repr(e));return 2

if __name__=='__main__': raise SystemExit(main())
