from __future__ import annotations
import argparse
from pathlib import Path
from medtas_v16_common import load,dump,evaluate,tool_path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();d=evaluate(root);ccx=tool_path(root,'calculix_executable',['ccx.exe','ccx']);gmsh=tool_path(root,'gmsh_executable',['gmsh.exe','gmsh'])
    paths={'structural_model':root/'reports/medtas/structural/current/K01_STRUCTURAL_MODEL_P006_v1.json','face_map':root/'reports/medtas/structural/current/K01_STRUCTURAL_FACE_MAP_P006_v1.json','neutral_geometry':root/'reports/medtas/structural/current/K01_STRUCTURAL_NEUTRAL_GEOMETRY_P006_v1_6.json','mesh_manifest':root/'reports/medtas/calculix/current/K01_STRUCTURAL_MESH_P006_v1_6.json','ccx_input_manifest':root/'reports/medtas/calculix/current/K01_CALCULIX_INPUT_P006_v1_6.json','deck':root/'reports/medtas/calculix/current/K01_CCX_P006/K01_P006.inp'}
    blocking=[]
    for nid in ('K01.STRUCT.FACE_MAP.P006','K01.STRUCT.BOLT_EQUIV.P006','K01.STRUCT.NEUTRAL.GEOMETRY.P006','K01.STRUCT.MESH.P006','K01.STRUCT.CCX.INPUT.P006'):
        st=d.get(nid,{}).get('state')
        if st!='PASS':blocking.append(nid+':'+str(st))
    if not ccx:blocking.append('CCX-EXE-001: CalculiX executable not found/bound')
    if not gmsh:blocking.append('CCX-MESH-001: Gmsh executable not found/bound (Python gmsh API is also required by mesh builder)')
    for k,p in paths.items():
        if k in ('ccx_input_manifest','deck') and d.get('K01.STRUCT.CCX.INPUT.P006',{}).get('state')!='PASS':continue
        if not p.exists():blocking.append(k+':MISSING')
    payload={'schema':'k01.calculix_preflight.v1_6','calculix_executable':ccx,'gmsh_executable':gmsh,'node_states':{nid:d.get(nid,{}).get('state') for nid in ('K01.STRUCT.FACE_MAP.P006','K01.STRUCT.BOLT_EQUIV.P006','K01.STRUCT.NEUTRAL.GEOMETRY.P006','K01.STRUCT.MESH.P006','K01.STRUCT.CCX.INPUT.P006')},'artifacts':{k:str(p) for k,p in paths.items()},'ready_to_run':not blocking,'blocking':blocking,'next_sequence':'face roles -> neutral STEP -> quadratic mesh -> approved bolt/preload/contact/load-path equivalence -> deterministic .inp -> ccx -> results parser -> SW/CCX reconciliation'}
    out=root/'reports/medtas/calculix/current/K01_CALCULIX_PREFLIGHT_CURRENT.json';dump(out,payload);print('CalculiX preflight ready_to_run=',payload['ready_to_run']);
    for x in blocking:print(' -',x)
    print('Saved:',out);return 0
if __name__=='__main__':raise SystemExit(main())
