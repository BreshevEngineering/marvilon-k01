from __future__ import annotations
import argparse,importlib.util
from pathlib import Path
from medtas_v16_common import load,dump,evaluate,tool_path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();d=evaluate(root)
    ccx=tool_path(root,'calculix_executable',['ccx.exe','ccx']);gmsh_exe=tool_path(root,'gmsh_executable',['gmsh.exe','gmsh']);gmsh_py=importlib.util.find_spec('gmsh') is not None
    paths={'structural_model':root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json','face_map':root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json','face_qualification':root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_QUAL_P006_v1_7.json','neutral_geometry':root/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_7.json','mesh_manifest':root/'reports/medtas/calculix/current/K01_STRUCTURAL_MESH_P006_v1_7.json','ccx_input_manifest':root/'reports/medtas/calculix/current/K01_CALCULIX_INPUT_P006_v1_7.json','deck':root/'reports/medtas/calculix/current/K01_CCX_P006/K01_P006.inp'}
    blocking=[]
    required_nodes=('K01.STRUCT.FACE_MAP.P006','K01.STRUCT.FACE_MAP.QUAL.P006','K01.STRUCT.BOLT_EQUIV.P006','K01.STRUCT.NEUTRAL.GEOMETRY.P006','K01.STRUCT.MESH.P006','K01.STRUCT.CCX.INPUT.P006')
    for nid in required_nodes:
        st=d.get(nid,{}).get('state')
        if st!='PASS':blocking.append(nid+':'+str(st))
    if not ccx:blocking.append('CCX-EXE-001: CalculiX executable not found/bound')
    if not gmsh_py:blocking.append('CCX-MESH-API-001: Python gmsh module not available; mesh builder requires the controlled Gmsh Python API')
    # gmsh.exe itself is optional when the Python module is present.
    for k,p in paths.items():
        if k in ('ccx_input_manifest','deck') and d.get('K01.STRUCT.CCX.INPUT.P006',{}).get('state')!='PASS':continue
        if k=='mesh_manifest' and d.get('K01.STRUCT.MESH.P006',{}).get('state')!='PASS':continue
        if not p.exists():blocking.append(k+':MISSING')
    payload={'schema':'k01.calculix_preflight.v1_7','calculix_executable':ccx,'gmsh_executable_optional':gmsh_exe,'gmsh_python_api':gmsh_py,'node_states':{nid:d.get(nid,{}).get('state') for nid in required_nodes},'artifacts':{k:str(p) for k,p in paths.items()},'ready_to_run':not blocking,'blocking':blocking,'next_sequence':'qualified face roles -> neutral STEP -> C3D10 mesh -> approved bolt/preload/contact/load-path equivalence -> deterministic .inp -> ccx -> result parser -> SW/CCX reconciliation'}
    out=root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json';dump(out,payload);print('CalculiX preflight ready_to_run=',payload['ready_to_run']);[print(' -',x) for x in blocking];print('Saved:',out);return 0
if __name__=='__main__':raise SystemExit(main())
