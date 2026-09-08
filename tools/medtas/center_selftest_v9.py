from pathlib import Path
import argparse, json, py_compile, subprocess, sys

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',required=True); a=ap.parse_args(); root=Path(a.repo_root).resolve()
    required=[
        root/'K01_Command_Center_v9.html',
        root/'tools/medtas/medtas_center_proxy_v9.py',
        root/'tools/medtas/rebuild_medtas_state.py',
        root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_4.json',
        root/'tools/medtas/canonical_hash_v1_4.py',
        root/'tools/medtas/canonical_hash_selftest_v1_4.py',
    ]
    fail=[]
    for p in required:
        if not p.exists(): fail.append('MISSING '+str(p))
    for p in [root/'control/medtas/v1/graph/K01_engineering_build_graph_v1_4.json',root/'reports/control/K01_MEDTAS_CENTER_FEED_CURRENT.json']:
        if p.exists():
            try: json.loads(p.read_text(encoding='utf-8-sig'))
            except Exception as e: fail.append('BAD JSON '+str(p)+': '+str(e))
    for p in [
        root/'tools/medtas/medtas_center_proxy_v9.py',
        root/'tools/medtas/run_cad_sem_a001.py',
        root/'tools/medtas/build_face_map_candidate_v1_3.py',
        root/'tools/medtas/build_mbd_a001_v1_4.py',
        root/'tools/medtas/canonical_hash_selftest_v1_4.py',
        root/'tools/medtas/build_downstream_v1_2.py',
    ]:
        if p.exists():
            try: py_compile.compile(str(p),doraise=True)
            except Exception as e: fail.append('PYTHON SYNTAX '+str(p)+': '+str(e))
    if not fail:
        cp=subprocess.run([sys.executable,str(root/'tools/medtas/canonical_hash_selftest_v1_4.py')],cwd=str(root),text=True,capture_output=True)
        if cp.returncode: fail.append('CANONICAL HASH SELFTEST FAILED: '+(cp.stdout+cp.stderr).strip())
    if fail:
        print('K01 Command Center v9 SELFTEST HOLD')
        print('Resolved repo root:',root)
        print('\n'.join(' - '+x for x in fail)); return 1
    print('K01 Command Center v9 SELFTEST PASS')
    print('Resolved repo root:',root)
    print('Canonical hash core: PASS')
    print('Legacy backend:', 'FOUND' if (root/'cc_server_v8.ps1').exists() else 'NOT IN OVERLAY / expected in existing repo')
    return 0
if __name__=='__main__': raise SystemExit(main())
