#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, subprocess
from datetime import datetime
from pathlib import Path

REFINED=Path('reports/control/K01_D006_REFINED_EXISTING_CURRENT.json')
PROFILE=Path('control/drawings/K01_D006_BASE_DRAWING_V7_PROFILE.json')
CHARS=Path('control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json')
V6RAW=Path('reports/cad/d006_automated_native_pmi_v6_current/K01_D006_AUTOMATED_NATIVE_PMI_V6_RAW_CURRENT.txt')
OUT=Path('reports/control/K01_D006_BASE_DRAWING_V7_CURRENT.json')
CS=Path('cad_api/solidworks_2018_proven/current/K01_D006_BASE_DRAWING_V7/K01D006BaseDrawingV7.cs')
WORK=Path('reports/cad/d006_base_drawing_v7_current')

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+'.tmp'); t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.replace(str(t),str(p))
def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def run(c,cwd=None,timeout=600): return subprocess.run(c,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors='replace',timeout=timeout)
def sw_running():
    cp=run(['tasklist','/FI','IMAGENAME eq SLDWORKS.exe'],timeout=30); return 'sldworks.exe' in ((cp.stdout or '')+(cp.stderr or '')).lower()
def csc():
    w=Path(os.environ.get('WINDIR',r'C:\Windows'))
    for p in [w/'Microsoft.NET/Framework64/v4.0.30319/csc.exe',w/'Microsoft.NET/Framework/v4.0.30319/csc.exe']:
        if p.exists(): return p
    raise RuntimeError('csc.exe missing')
def redist():
    for p in [Path(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist'),Path(r'C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist')]:
        if (p/'SolidWorks.Interop.sldworks.dll').exists(): return p
    raise RuntimeError('SW interop redist missing')
def parse_kv(p):
    d={}
    if not Path(p).is_file(): return d
    for line in Path(p).read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if '=' in line:
            k,v=line.split('=',1); d[k.strip()]=v.strip()
    return d
def drawing_from_report(r):
    c=r.get('candidate') or {}; return Path(str(c.get('slddrw') or r.get('drawing') or r.get('output') or ''))
def latest_semantics_part(root:Path):
    kv=parse_kv(root/V6RAW)
    p=Path(kv.get('DRAWING_SOURCE_PART','')) if kv.get('DRAWING_SOURCE_PART') else None
    if p and p.is_file(): return p
    base=Path(r'D:\Marvilon\K01\cad\candidates\p007_drawing_authoring')
    xs=[]
    if base.exists(): xs=[x for x in base.glob('native_semantics_*/K01-P-007_Hermetic_Magnetic_Can_DRAWING_SOURCE_CANDIDATE.SLDPRT') if x.is_file()]
    return max(xs,key=lambda x:x.stat().st_mtime) if xs else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    rep={'schema':'k01.d006.base_drawing_v7.current.v1','generated_local':datetime.now().isoformat(),'status':'RUNNING'}
    try:
        need(not sw_running(),'Close SolidWorks before D006 base drawing V7 so the saved drawing on disk is the controlled source.')
        r=load(root/REFINED); drawing=drawing_from_report(r); part=latest_semantics_part(root)
        need(drawing.is_file(),'existing linked refined D006 drawing missing: '+str(drawing))
        need(part is not None and part.is_file(),'latest semantics-correct P007 drawing-source candidate missing; V6 already created this before the UI import HOLD')
        for p in [root/PROFILE,root/CHARS]: need(p.is_file(),'required control input missing: '+str(p))
        rd=redist(); refs=[rd/'SolidWorks.Interop.sldworks.dll',rd/'SolidWorks.Interop.swconst.dll']
        for x in refs: need(x.is_file(),'interop missing '+str(x))
        work=root/WORK; build=work/'build'; build.mkdir(parents=True,exist_ok=True); exe=build/'K01D006BaseDrawingV7.exe'; raw=work/'K01_D006_BASE_DRAWING_V7_RAW_CURRENT.txt'
        cmd=[str(csc()),'/nologo','/langversion:5','/target:exe','/optimize+','/out:'+str(exe)]+['/reference:'+str(x) for x in refs]+['/reference:System.Web.Extensions.dll',str(root/CS)]
        cp=run(cmd,cwd=root)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        need(cp.returncode==0,'D006 base drawing V7 compile failed')
        for x in refs: shutil.copy2(x,build/x.name)
        cp=run([str(exe),'--drawing',str(drawing),'--part',str(part),'--characteristics',str(root/CHARS),'--profile',str(root/PROFILE),'--out-root',r'D:\Marvilon\K01\cad\drawings\candidates\K01-D-006','--report',str(raw)],cwd=root,timeout=600)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        kv=parse_kv(raw); status=kv.get('STATUS') or ('HOLD_D006_BASE_DRAWING_V7_ERROR' if cp.returncode else 'HOLD_D006_BASE_DRAWING_V7_UNKNOWN')
        rep.update({'status':status,'returncode':cp.returncode,'source_drawing':str(drawing),'drawing_source_part':str(part),'profile':str(root/PROFILE),'characteristics':str(root/CHARS),'candidate':{'slddrw':kv.get('OUTPUT_DRAWING'),'pdf':kv.get('OUTPUT_PDF'),'bmp':kv.get('OUTPUT_BMP')},'created_count':int(kv.get('CREATED_COUNT','0') or 0),'critical':{'C02':kv.get('C02_CREATED')=='True','C05':kv.get('C05_CREATED')=='True'},'raw_report':str(raw),'policy':'SW2018 direct associative drawing dimensions from controlled model entities; no UI Automation dependency; native PMI remains semantic authority; OPEN tolerances remain OPEN'})
        write(root/OUT,rep); print('STATUS:',status); print('REPORT:',root/OUT)
        if status.startswith('PASS_') or status.startswith('PARTIAL_'):
            print('NEXT: inspect the saved V7 base candidate visually; keep it as the continuation source and adjust only the remaining presentation/layout manually or by the next cleanup pass.')
            return 0
        return 2
    except Exception as e:
        rep['status']='HOLD_D006_BASE_DRAWING_V7'; rep['error']=repr(e); write(root/OUT,rep); print('STATUS:',rep['status']); print('ERROR:',repr(e)); print('REPORT:',root/OUT); return 2
if __name__=='__main__': raise SystemExit(main())
