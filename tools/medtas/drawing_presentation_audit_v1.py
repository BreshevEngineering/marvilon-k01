#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, os, shutil, subprocess, sys, time
from pathlib import Path

CS=Path(r"cad_api/solidworks_2018_proven/current/K01_DRAWING_PRESENTATION_V1/K01DrawingPresentationAuditV1.cs")
WORK=Path(r"reports/cad/drawing_presentation_v1_current")
POLICY=Path(r"control/drawings/presentation/K01_DRAWING_PRESENTATION_POLICY_V1.json")

def run(cmd,cwd=None,timeout=600): return subprocess.run(cmd,cwd=str(cwd) if cwd else None,capture_output=True,text=True,errors="replace",timeout=timeout)
def need(ok,msg):
    if not ok: raise RuntimeError(msg)
def csc():
    w=Path(os.environ.get("WINDIR",r"C:\Windows"))
    for p in (w/"Microsoft.NET/Framework64/v4.0.30319/csc.exe",w/"Microsoft.NET/Framework/v4.0.30319/csc.exe"):
        if p.exists(): return p
    raise RuntimeError("csc.exe missing")
def redist():
    for p in (Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist"),Path(r"C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist")):
        if (p/"SolidWorks.Interop.sldworks.dll").exists(): return p
    raise RuntimeError("SOLIDWORKS API redist missing")
def sw_running():
    cp=run(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],timeout=30);return "sldworks.exe" in ((cp.stdout or "")+(cp.stderr or "")).lower()
def cleanup_owned_solidworks():
    # The audit refuses to start when SolidWorks is already running. Therefore any
    # remaining SLDWORKS.exe after the capture process is automation-owned and safe
    # to reap. Give ExitApp a short grace period first.
    for _ in range(6):
        if not sw_running(): return False
        time.sleep(0.5)
    cp=run(["taskkill","/F","/IM","SLDWORKS.exe","/T"],timeout=30)
    print("CLEANUP: terminated automation-owned SolidWorks after presentation capture")
    if cp.stdout: print(cp.stdout,end='')
    if cp.stderr: print(cp.stderr,end='',file=sys.stderr)
    return True
def latest_generated(cad_root:Path,drawing_id:str):
    root=cad_root/"drawings"/"candidates"/drawing_id
    cs=sorted([p for p in root.glob("drawing_system_v1_*") if p.is_dir()],key=lambda p:p.name,reverse=True)
    for c in cs:
        d=c/"generated"/(drawing_id+".SLDDRW")
        if d.is_file(): return d
    raise RuntimeError("no generated Drawing System candidate found for "+drawing_id)
def rect_overlap(a,b): return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
def leader_len(points):
    s=0.0
    for a,b in zip(points,points[1:]): s+=math.hypot(float(b.get('x',0))-float(a.get('x',0)),float(b.get('y',0))-float(a.get('y',0)))
    return s

def evaluate(ev,policy):
    hard=[];warn=[];sh=policy['sheet'];m=sh['margin_m'];sheet=[m,m,sh['width_m']-m,sh['height_m']-m]
    regs=policy.get('reserved_regions',[])
    for v in ev.get('views',[]):
        o=v.get('outline') or []
        if len(o)>=4:
            r=[min(o[0],o[2]),min(o[1],o[3]),max(o[0],o[2]),max(o[1],o[3])]
            if r[0]<sheet[0] or r[1]<sheet[1] or r[2]>sheet[2] or r[3]>sheet[3]: hard.append(f"VIEW_OUTSIDE_MARGIN {v['id']} {r}")
            for z in regs:
                rr=[z['xmin'],z['ymin'],z['xmax'],z['ymax']]
                if rect_overlap(r,rr): hard.append(f"VIEW_RESERVED_COLLISION {v['id']} {z['id']}")
    for a in ev.get('annotations',[]):
        p=a.get('position') or {};x=p.get('x');y=p.get('y')
        if isinstance(x,(int,float)) and isinstance(y,(int,float)) and not (0<=x<=sh['width_m'] and 0<=y<=sh['height_m']): warn.append(f"ANNOTATION_ORIGIN_OUTSIDE_SHEET {a['id']}")
        ex=a.get('note_extent') or []
        if len(ex)>=6:
            r=[min(ex[0],ex[3]),min(ex[1],ex[4]),max(ex[0],ex[3]),max(ex[1],ex[4])]
            for z in regs:
                if rect_overlap(r,[z['xmin'],z['ymin'],z['xmax'],z['ymax']]): warn.append(f"NOTE_RESERVED_COLLISION {a['id']} {z['id']}")
        for lr in a.get('leaders') or []:
            L=leader_len(lr.get('points') or [])
            if L>policy['leader_rules']['warn_length_m']: warn.append(f"LONG_LEADER {a['id']}[{lr.get('index')}] length_m={L:.4f}")
    for x in ev.get('warnings') or []: warn.append("CAPTURE_WARNING "+x)
    return hard,warn

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);ap.add_argument('--drawing-id',required=True);ap.add_argument('--spec',required=True);ap.add_argument('--drawing');a=ap.parse_args()
    root=Path(a.repo_root).resolve();spec=(root/a.spec).resolve();policy=json.loads((root/POLICY).read_text(encoding='utf-8'));sp=json.loads(spec.read_text(encoding='utf-8'));need(sp.get('drawing_id')==a.drawing_id,'drawing/spec mismatch')
    drawing=Path(a.drawing) if a.drawing else latest_generated(Path(r"D:\Marvilon\K01\cad"),a.drawing_id)
    need(drawing.is_file(),'drawing missing: '+str(drawing));need(not sw_running(),'Close SolidWorks before presentation audit (read-only audit opens its own instance).')
    rd=redist();build=root/WORK/'build';build.mkdir(parents=True,exist_ok=True);exe=build/'K01DrawingPresentationAuditV1.exe';refs=[rd/'SolidWorks.Interop.sldworks.dll',rd/'SolidWorks.Interop.swconst.dll']
    cmd=[str(csc()),'/nologo','/langversion:5','/target:exe','/optimize+','/out:'+str(exe)]+['/reference:'+str(x) for x in refs]+['/reference:System.Web.Extensions.dll',str(root/CS)]
    cp=run(cmd,cwd=root);print(cp.stdout,end='');print(cp.stderr,end='',file=sys.stderr);need(cp.returncode==0,'presentation C# compile failed')
    for x in refs: shutil.copy2(x,build/x.name)
    out=root/WORK/(a.drawing_id.replace('-','_')+'_PRESENTATION_EVIDENCE_CURRENT.json');cp=None
    try:
        cp=run([str(exe),'--drawing',str(drawing),'--spec',str(spec),'--out',str(out)],cwd=root,timeout=600)
    finally:
        cleanup_owned_solidworks()
    print(cp.stdout,end='');print(cp.stderr,end='',file=sys.stderr);need(cp.returncode==0,'presentation capture failed')
    ev=json.loads(out.read_text(encoding='utf-8'));hard,warn=evaluate(ev,policy);report=root/WORK/(a.drawing_id.replace('-','_')+'_PRESENTATION_AUDIT_CURRENT.txt');lines=[f"SCHEMA=k01.drawing_presentation_audit.v1",f"DRAWING={a.drawing_id}",f"SOURCE={drawing}",f"HARD={len(hard)}",f"WARN={len(warn)}"]+["HARD_ITEM="+x for x in hard]+["WARN_ITEM="+x for x in warn];report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    status='HOLD_DRAWING_PRESENTATION_V1' if hard else ('PASS_WITH_WARNINGS_DRAWING_PRESENTATION_V1' if warn else 'PASS_DRAWING_PRESENTATION_V1')
    print('STATUS:',status);print('HARD CHECKS:',len(hard));print('WARNINGS:',len(warn));
    for x in hard: print('  HARD:',x)
    for x in warn[:25]: print('  WARN:',x)
    print('EVIDENCE:',out);print('REPORT:',report);print('NOTE: Phase A does not claim full annotation bounding-box collision detection, leader rerouting, or D8 human approval.')
    return 2 if hard else 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as e: print('STATUS: HOLD_DRAWING_PRESENTATION_V1');print('ERROR:',repr(e));raise SystemExit(2)
