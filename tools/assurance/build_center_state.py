from __future__ import annotations
import argparse,sys
from pathlib import Path

THIS=Path(__file__).resolve()
REPO=THIS.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0,str(REPO))

from tools.assurance.evidence_reducer import build

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(REPO))
    args=ap.parse_args()
    repo=Path(str(args.repo_root).strip().strip('"')).resolve()
    ep,vp,view=build(repo)
    print("evidence_index:",ep)
    print("center_view:",vp)
    print("verdict:",view["verdict"],"blockers:",len(view["blockers"]),"screens:",view["screens"])
