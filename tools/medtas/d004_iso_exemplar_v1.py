#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

CS = Path(r"cad_api/solidworks_2018_proven/current/K01_D004_ISO_EXEMPLAR_V1/K01D004IsoExemplarV1.cs")
SPEC = Path(r"control/drawings/spec/K01-D-004_P004_DRAWING_SPEC_v1.json")
WORK = Path(r"reports/cad/d004_iso_exemplar_v1_current")
PART = Path(r"D:\Marvilon\K01\cad\parts\K01-P-004_Front_Guide_Bushing.SLDPRT")
OUT_ROOT = Path(r"D:\Marvilon\K01\cad\drawings\candidates\K01-D-004")

def run(cmd,cwd=None,timeout=900):
    return subprocess.run(cmd,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)

def need(ok,msg):
    if not ok: raise RuntimeError(msg)

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def artifact(p:Path):
    return {'path':str(p),'exists':p.is_file(),'sha256':sha256(p) if p.is_file() else None,'size_bytes':p.stat().st_size if p.is_file() else None}

def parse_report(p:Path):
    d={}
    if not p.is_file(): return d
    for line in p.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if '=' in line:
            k,v=line.split('=',1)
            if k and k not in d: d[k]=v
    return d

def sw_running():
    cp=run(['tasklist','/FI','IMAGENAME eq SLDWORKS.exe'],timeout=30)
    return 'sldworks.exe' in ((cp.stdout or '')+(cp.stderr or '')).lower()

def cleanup_owned_sw(was_running:bool):
    if was_running or not sw_running(): return
    for _ in range(10):
        time.sleep(0.5)
        if not sw_running(): return
    run(['taskkill','/F','/T','/IM','SLDWORKS.exe'],timeout=30)

def csc():
    w=Path(os.environ.get('WINDIR',r'C:\Windows'))
    for p in (w/'Microsoft.NET/Framework64/v4.0.30319/csc.exe',w/'Microsoft.NET/Framework/v4.0.30319/csc.exe'):
        if p.exists(): return p
    raise RuntimeError('csc.exe missing')

def redist():
    for p in (Path(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist'),Path(r'C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist')):
        if (p/'SolidWorks.Interop.sldworks.dll').exists(): return p
    raise RuntimeError('SOLIDWORKS API redist missing')

def write_manifest(root:Path, report:Path):
    r=parse_report(report); cand=Path(r.get('CANDIDATE_ROOT',''))
    need(cand.is_dir(),'candidate root missing from helper report')
    manual=Path(r['MANUAL_FINISH_DIR']); generated=Path(r['GENERATED_DIR']); evidence=Path(r['EVIDENCE_DIR'])
    dwg=Path(r['OUTPUT_DRAWING']); pdf=Path(r['OUTPUT_PDF']); bmp=Path(r['OUTPUT_BMP'])
    spec=root/SPEC
    m={
      'schema':'k01.drawing_candidate.v1','candidate_id':cand.name,'drawing_id':'K01-D-004','part_id':'K01-P-004',
      'engine':'K01_D004_ISO_EXEMPLAR_V1','engine_revision':'1.0-golden-recipe','created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'state':'PRESENTATION_RECIPE_APPLIED__D8_PENDING','release':'HOLD','semantic_status':r.get('STATUS'),
      'presentation_status':'HOLD_D8_VISUAL_REVIEW','overall_status':'HOLD_PRESENTATION',
      'golden_recipe':'control/drawings/K01_DRAWING_GOLDEN_RECIPE_CURRENT.json',
      'spec':{'path':str(SPEC).replace('\\','/'),'sha256':sha256(spec)},
      'source_model':{'path':str(PART),'sha256':r.get('SOURCE_SHA256_AFTER')},
      'paths':{'candidate_root':str(cand),'generated':str(generated),'manual_finish':str(manual),'evidence':str(evidence)},
      'manual_finish':{'drawing':artifact(dwg),'pdf':artifact(pdf),'bmp':artifact(bmp)},
      'release_blockers':json.loads(spec.read_text(encoding='utf-8-sig')).get('release_blockers',[]),
      'rule':'Semantic and fixed presentation recipe are complete; D8 visual acceptance is still required before Drawing Control publication.'
    }
    (cand/'candidate_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('CANDIDATE MANIFEST:',cand/'candidate_manifest.json')
    return cand,pdf

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();was=sw_running()
    try:
        print('TZ_PRECHECK: K01-TZ-AI-OPERATING v1.0 | ACTIVE=D004 GOLDEN-RECIPE EXEMPLAR | WIP=1')
        need(not was,'Close SolidWorks before D004 exemplar build.')
        need((root/CS).is_file(),'C# helper missing: '+str(root/CS));need((root/SPEC).is_file(),'D004 spec missing');need(PART.is_file(),'P004 model missing: '+str(PART))
        rd=redist();refs=[rd/'SolidWorks.Interop.sldworks.dll',rd/'SolidWorks.Interop.swconst.dll'];build=root/WORK/'build';build.mkdir(parents=True,exist_ok=True);exe=build/'K01D004IsoExemplarV1.exe';report=root/WORK/'K01_D004_ISO_EXEMPLAR_V1_CURRENT.txt'
        cmd=[str(csc()),'/nologo','/langversion:5','/target:exe','/optimize+','/out:'+str(exe)]+['/reference:'+str(x) for x in refs]+[str(root/CS)]
        cp=run(cmd,cwd=root)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        need(cp.returncode==0,'D004 C# compile failed')
        for x in refs: shutil.copy2(x,build/x.name)
        cp=run([str(exe),'--part',str(PART),'--out-root',str(OUT_ROOT),'--report',str(report)],cwd=root,timeout=900)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        need(cp.returncode in (0,3),'D004 helper execution error')
        cand,pdf=write_manifest(root,report)
        ctl=root/'tools/medtas/drawing_control_v1.py'
        if ctl.is_file():
            c=run([sys.executable,str(ctl),'--repo-root',str(root)],cwd=root,timeout=120)
            if c.stdout: print(c.stdout,end='')
            if c.stderr: print(c.stderr,end='')
        print('STATUS: PASS_D004_GOLDEN_RECIPE_BUILD__HOLD_D8_VISUAL_REVIEW' if cp.returncode==0 else 'STATUS: PARTIAL_D004_GOLDEN_RECIPE_BUILD')
        print('PDF FOR D8:',pdf)
        print('RULE: do not publish D004 current until presentation_status becomes PASS_* after visual review.')
        return 0 if cp.returncode==0 else 3
    except Exception as e:
        print('STATUS: HOLD_D004_ISO_EXEMPLAR_V1');print('ERROR:',repr(e));return 2
    finally:
        cleanup_owned_sw(was)

if __name__=='__main__': raise SystemExit(main())
