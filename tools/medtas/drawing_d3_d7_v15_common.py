from __future__ import annotations
import json, os, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(p: Path):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')

def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True, errors='replace', timeout=timeout)

def sw_running() -> bool:
    cp = run(['tasklist','/FI','IMAGENAME eq SLDWORKS.exe'], timeout=30)
    return 'sldworks.exe' in ((cp.stdout or '')+(cp.stderr or '')).lower()

def csc() -> Path:
    w=Path(os.environ.get('WINDIR',r'C:\Windows'))
    for p in (w/'Microsoft.NET/Framework64/v4.0.30319/csc.exe',w/'Microsoft.NET/Framework/v4.0.30319/csc.exe'):
        if p.exists(): return p
    raise RuntimeError('csc.exe missing')

def redist() -> Path:
    for p in (Path(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist'),Path(r'C:\Program Files (x86)\SOLIDWORKS Corp\SOLIDWORKS\api\redist')):
        if (p/'SolidWorks.Interop.sldworks.dll').exists(): return p
    raise RuntimeError('SOLIDWORKS API redist missing')

def compile_helper(cs: Path, exe_name: str, build_dir: Path) -> Path:
    rd=redist(); refs=[rd/'SolidWorks.Interop.sldworks.dll',rd/'SolidWorks.Interop.swconst.dll',rd/'SolidWorks.Interop.swdimxpert.dll']
    for r in refs:
        if not r.exists(): raise RuntimeError(f'interop missing: {r}')
    build_dir.mkdir(parents=True,exist_ok=True); exe=build_dir/exe_name
    cmd=[str(csc()),'/nologo','/langversion:5','/target:exe','/optimize+','/out:'+str(exe)] + ['/reference:'+str(r) for r in refs] + [str(cs)]
    cp=run(cmd)
    if cp.stdout: print(cp.stdout,end='')
    if cp.stderr: print(cp.stderr,end='')
    if cp.returncode!=0: raise RuntimeError(f'compile failed: {cs.name}')
    for r in refs: shutil.copy2(r,build_dir/r.name)
    return exe

def parse_kv(p: Path):
    out={}; rec=[]
    for raw in p.read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if raw.startswith('REC='):
            rec.append(raw[4:]); continue
        if '=' in raw:
            k,v=raw.split('=',1); out[k.strip()]=v.strip()
    out['_REC']=rec
    return out

def workspace_paths():
    p=ROOT/'reports/drawing/current/K01-D-006_EXEMPLAR_WORKSPACE_CURRENT.json'
    if not p.exists(): raise RuntimeError(f'missing workspace report: {p}')
    ws=load(p)
    part=Path(ws['workspace']['part']); drawing=Path(ws['workspace']['drawing'])
    if not part.is_file() or not drawing.is_file(): raise RuntimeError('workspace part/drawing missing')
    return ws,part,drawing
