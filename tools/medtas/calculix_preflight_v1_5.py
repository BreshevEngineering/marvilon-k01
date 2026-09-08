#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path

def load(p,d=None):
    try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
    except Exception:return d
def dump(p,obj):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve()
    ccx=shutil.which('ccx.exe') or shutil.which('ccx');gmsh=shutil.which('gmsh.exe') or shutil.which('gmsh')
    structural=root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json';face_map=root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json';scaf=root/'reports/medtas/calculix/current/K01_CALCULIX_CASE_SCAFFOLD_P006_v1_5.json'
    blocking=[];fm=load(face_map);sf=load(scaf)
    if not structural.exists():blocking.append('CCX-MODEL-001: solver-neutral structural model missing')
    if not fm:blocking.append('CCX-FACE-001: face-map candidate missing')
    elif fm.get('status')!='PASS':blocking.append('CCX-FACE-002: face map is '+str(fm.get('status'))+'; exact SW study face roles are not yet confirmed')
    if not sf:blocking.append('CCX-SCAFFOLD-001: case scaffold missing')
    elif sf.get('status')!='READY_FOR_NEUTRAL_MESH_EXPORT':blocking.append('CCX-SCAFFOLD-002: '+str(sf.get('status'))+'; missing '+', '.join(sf.get('missing_face_roles') or []))
    # These are intentionally separate from face binding: even after role confirmation,
    # a controlled neutral geometry/mesh export must exist before .inp generation.
    neutral=root/'reports/medtas/calculix/current/K01_P006_NEUTRAL_MESH.msh'
    if not neutral.exists():blocking.append('CCX-GEO-001: controlled neutral mesh artifact not yet generated')
    if not ccx:blocking.append('CCX-EXE-001: CalculiX executable not found on PATH')
    if not gmsh:blocking.append('CCX-MESH-001: Gmsh not found on PATH; another controlled mesher can be substituted')
    payload={'schema':'k01.calculix_preflight.v1_5','calculix_executable':ccx,'gmsh_executable':gmsh,'structural_model':str(structural),'face_map':str(face_map),'case_scaffold':str(scaf),'neutral_mesh':str(neutral),'ready_to_run':len(blocking)==0,'blocking':blocking,'next_implementation':'confirm exact SW study face signatures -> export P003/P007 neutral geometry/mesh with named groups -> generate .inp -> ccx -> reconciliation'}
    out=root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json';dump(out,payload);print(json.dumps(payload,ensure_ascii=False,indent=2));print('\nSaved:',out);return 0
if __name__=='__main__':raise SystemExit(main())
