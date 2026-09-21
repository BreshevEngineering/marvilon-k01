#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,shutil,subprocess
from datetime import datetime
from pathlib import Path

REFINED=Path('reports/control/K01_D006_REFINED_EXISTING_CURRENT.json')
PMI=Path('reports/control/K01_P007_PMI_PROVEN_CURRENT.json')
OUT=Path('reports/control/K01_D006_AUTOMATED_NATIVE_PMI_V6_CURRENT.json')
CS=Path('cad_api/solidworks_2018_proven/current/K01_D006_AUTOMATED_NATIVE_PMI_V6/K01D006AutomatedNativePmi_v1.cs')
WORK=Path('reports/cad/d006_automated_native_pmi_v6_current')

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(str(t),str(p))
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

def framework_assembly(name):
    w=Path(os.environ.get('WINDIR',r'C:\Windows'))
    pf86=Path(os.environ.get('ProgramFiles(x86)',r'C:\Program Files (x86)'))
    candidates=[
        w/'Microsoft.NET/Framework64/v4.0.30319/WPF'/name,
        w/'Microsoft.NET/Framework/v4.0.30319/WPF'/name,
        w/'Microsoft.NET/Framework64/v4.0.30319'/name,
        w/'Microsoft.NET/Framework/v4.0.30319'/name,
    ]
    refroot=pf86/'Reference Assemblies/Microsoft/Framework/.NETFramework'
    if refroot.exists():
        for d in sorted(refroot.glob('v*'),reverse=True):
            candidates.extend([d/name,d/'Profile/Client'/name])
    for p in candidates:
        if p.is_file(): return p
    raise RuntimeError('framework assembly missing: '+name+'; checked '+ '; '.join(str(x) for x in candidates))
def parse_kv(p):
    d={}
    for line in Path(p).read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if '=' in line:
            k,v=line.split('=',1);d[k.strip()]=v.strip()
    return d

def drawing_from_report(r):
    c=r.get('candidate') or {}
    return Path(str(c.get('slddrw') or r.get('drawing') or r.get('output') or ''))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    rep={'schema':'k01.d006.automated_native_pmi.v6','generated_local':datetime.now().isoformat(),'status':'RUNNING'}
    try:
        need(not sw_running(),'Close SolidWorks before the controlled automation-first D006 PMI run.')
        r=load(root/REFINED);p=load(root/PMI);drawing=drawing_from_report(r);part=Path(str(((p.get('candidate') or {}).get('path') or '')))
        need(drawing.is_file(),'refined linked D006 drawing candidate missing: '+str(drawing));need(part.is_file(),'proven P007 PMI source missing: '+str(part))
        rd=redist();refs=[rd/'SolidWorks.Interop.sldworks.dll',rd/'SolidWorks.Interop.swconst.dll',rd/'SolidWorks.Interop.swdimxpert.dll']
        for x in refs: need(x.is_file(),'interop missing '+str(x))
        ui_refs=[framework_assembly('UIAutomationClient.dll'),framework_assembly('UIAutomationTypes.dll')]
        work=root/WORK;build=work/'build';build.mkdir(parents=True,exist_ok=True);exe=build/'K01D006AutomatedNativePmi_v1.exe';raw=work/'K01_D006_AUTOMATED_NATIVE_PMI_V6_RAW_CURRENT.txt'
        cmd=[str(csc()),'/nologo','/langversion:5','/target:exe','/optimize+','/out:'+str(exe)]+['/reference:'+str(x) for x in refs+ui_refs]+['/reference:System.Windows.Forms.dll',str(root/CS)]
        cp=run(cmd,cwd=root)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        need(cp.returncode==0,'D006 automated native PMI V6 compile failed')
        for x in refs+ui_refs: shutil.copy2(x,build/x.name)
        cp=run([str(exe),'--drawing',str(drawing),'--part',str(part),'--drawing-out-root',r'D:\Marvilon\K01\cad\drawings\candidates\K01-D-006','--part-out-root',r'D:\Marvilon\K01\cad\candidates\p007_drawing_authoring','--report',str(raw)],cwd=root,timeout=600)
        if cp.stdout: print(cp.stdout,end='')
        if cp.stderr: print(cp.stderr,end='')
        kv=parse_kv(raw) if raw.exists() else {};status=kv.get('STATUS') or ('HOLD_D006_AUTOMATED_NATIVE_PMI_ERROR' if cp.returncode else 'HOLD_D006_AUTOMATED_NATIVE_PMI_UNKNOWN')
        rep.update({'status':status,'returncode':cp.returncode,'source_drawing':str(drawing),'proven_pmi_source':str(part),'ui_automation_refs':[str(x) for x in ui_refs],'drawing_source_part':kv.get('DRAWING_SOURCE_PART'),'candidate':{'slddrw':kv.get('OUTPUT_DRAWING'),'pdf':kv.get('OUTPUT_PDF'),'bmp':kv.get('OUTPUT_BMP')},'dimxpert':{'count':int(kv.get('DIMXPERT_COUNT','0') or 0),'C02':kv.get('C02')=='True','C02_H7':kv.get('C02_SEMANTICS_H7')=='True','C05':kv.get('C05')=='True','C05_NONE':kv.get('C05_SEMANTICS_NONE')=='True'},'raw_report':str(raw),'policy':'automation-first existing linked drawing; separate PMI drawing-source copy; C02 H7; C05 tolerance NONE/OPEN; native SW2018 DimXpert import bridge; exact semantic verification; source invariance'})
        write(root/OUT,rep);print('STATUS:',status);print('REPORT:',root/OUT)
        if cp.returncode==0 and status.startswith('PASS_'):
            print('NEXT: use this saved candidate as the only D006 continuation source; proceed to API cleanup/layout, then final 10-20% human visual QA.')
            return 0
        print('NEXT: return this console output + raw report; do not rebuild the drawing and do not edit C02/C05 manually.')
        return 3 if cp.returncode==3 else 2
    except Exception as e:
        rep['status']='HOLD_D006_AUTOMATED_NATIVE_PMI_V6';rep['error']=repr(e);write(root/OUT,rep);print('STATUS:',rep['status']);print('ERROR:',repr(e));print('REPORT:',root/OUT);return 2
if __name__=='__main__': raise SystemExit(main())
