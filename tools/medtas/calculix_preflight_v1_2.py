#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path

def dump(p,obj):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    ccx=shutil.which('ccx.exe') or shutil.which('ccx'); gmsh=shutil.which('gmsh.exe') or shutil.which('gmsh')
    structural=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json'
    face_map=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json'
    blocking=[]
    if not structural.exists(): blocking.append('CCX-MODEL-001: solver-neutral structural model missing')
    if not face_map.exists(): blocking.append('CCX-FACE-001: solver-neutral face-map candidate missing')
    else:
        try:
            fm=json.loads(face_map.read_text(encoding='utf-8-sig'))
            if fm.get('status')!='PASS': blocking.append('CCX-FACE-002: face map is '+str(fm.get('status'))+'; exact SW study face roles are not yet confirmed')
        except Exception as e: blocking.append('CCX-FACE-003: face-map JSON unreadable: '+str(e))
    blocking.append('CCX-GEO-001: controlled neutral mesh exporter is not yet generated')
    if not ccx: blocking.append('CCX-EXE-001: CalculiX executable not found on PATH')
    if not gmsh: blocking.append('CCX-MESH-001: Gmsh not found on PATH; another controlled mesher can be substituted')
    payload={'schema':'k01.calculix_preflight.v1_2','calculix_executable':ccx,'gmsh_executable':gmsh,'structural_model':str(structural),'face_map':str(face_map),'ready_to_run':len(blocking)==0,'blocking':blocking,'next_implementation':'confirm exact SW study face signatures, export controlled STEP/mesh, then generate .inp from K01.STRUCT.MODEL.P006'}
    out=root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json'; dump(out,payload)
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    print('\nSaved:',out)
if __name__=='__main__': main()
