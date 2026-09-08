from __future__ import annotations
from pathlib import Path
import json, hashlib, subprocess, os, csv

def load(path, default=None):
    p=Path(path)
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding='utf-8-sig'))
    except Exception: return default

def save(path,obj):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding='utf-8'); return p

def sha256_file(path):
    h=hashlib.sha256();
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def latest_graph(root):
    gdir=Path(root)/'control/medtas/v1/graph'
    files=sorted(gdir.glob('K01_engineering_build_graph*.json')) if gdir.exists() else []
    return files[-1] if files else None

def run(cmd,cwd=None):
    return subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
