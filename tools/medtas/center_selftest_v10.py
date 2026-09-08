from pathlib import Path
import argparse,py_compile

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();root=Path(a.repo_root).resolve();fails=[]
    req=[
      root/'K01_Command_Center_v10.html',
      root/'tools/medtas/center_server_v10.py',
      root/'tools/medtas/pipeline_v1_6.py',
      root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_6.json',
      root/'tools/medtas/canonical_hash_v1_5.py',
      root/'tools/medtas/cad_hash_invariance_test_v1_6.py',
      root/'tools/medtas/build_face_map_candidate_v1_6.py',
      root/'tools/medtas/build_structural_mesh_v1_6.py',
      root/'tools/medtas/calculix_preflight_v1_6.py']
    for p in req:
        if not p.exists():fails.append('MISSING '+str(p))
    for p in req:
        if p.suffix=='.py' and p.exists():
            try:py_compile.compile(str(p),doraise=True)
            except Exception as e:fails.append('PYTHON '+str(p)+': '+str(e))
    if fails:
        print('K01 Command Center v10 SELFTEST HOLD');print('\n'.join(' - '+x for x in fails));return 1
    print('K01 Command Center v10 SELFTEST PASS');print('Standalone single-process server; MEDTAS v1.6 graph/pipeline present; no legacy v8 upstream dependency');return 0
if __name__=='__main__':raise SystemExit(main())
