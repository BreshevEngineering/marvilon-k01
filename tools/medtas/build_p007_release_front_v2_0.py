from __future__ import annotations
import argparse,subprocess,sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',required=True);a=ap.parse_args();r=Path(a.repo_root).resolve();py=sys.executable
    steps=[r/'tools/medtas/build_p007_geometry_authority_v2_0.py',r/'tools/medtas/build_p007_exemplar_plan_v2_0.py']
    for p in steps:
        cp=subprocess.run([py,str(p),'--repo-root',str(r)],cwd=str(r))
        if cp.returncode:return cp.returncode
    return 0
if __name__=='__main__':raise SystemExit(main())
