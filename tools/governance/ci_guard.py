from __future__ import annotations
import argparse,fnmatch,os,subprocess,sys
from pathlib import Path

THIS=Path(__file__).resolve()
REPO=THIS.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0,str(REPO))

from tools.governance.change_control import DEFAULT_RULES,classify_path,max_class,norm,load

def run(cmd,cwd=None):
    return subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,errors="replace")

def changed_paths(repo,base):
    cp=run(["git","-C",str(repo),"diff","--name-only",base+"...HEAD"])
    if cp.returncode!=0:
        cp=run(["git","-C",str(repo),"diff","--name-only","HEAD^","HEAD"])
    return [norm(x) for x in cp.stdout.splitlines() if x.strip()]

def covered(paths,planned):
    missing=[]
    for p in paths:
        if p.startswith("control/change/"):
            continue
        if not any(fnmatch.fnmatch(p,q) or p.startswith(q.rstrip("*")) for q in planned):
            missing.append(p)
    return missing

def main(repo,base):
    paths=changed_paths(repo,base)
    if not paths:
        print("ci_guard: PASS no changed paths")
        return 0

    policy=load(repo/"control"/"governance"/"K01_CHANGE_POLICY.json",{}) or {}
    rules=policy.get("classification_rules") or DEFAULT_RULES
    classified=[classify_path(p,rules) for p in paths]
    cls=max_class([x["class"] for x in classified])
    print("ci_change_class:",cls)

    if cls=="C":
        print("ci_guard: PASS Class C")
        return 0

    rec=load(repo/"control"/"change"/"K01_CHANGE_CURRENT.json",{}) or {}
    if rec.get("impact_status")!="PASS_PRECHANGE":
        print("HOLD: A/B change without PASS_PRECHANGE")
        return 2

    missing=covered(paths,rec.get("planned_paths") or [])
    missing=[p for p in missing if not (
        p.startswith("tools/") or p.startswith("tests/") or p.startswith(".github/") or
        p.startswith("control/governance/") or p.startswith("control/git/") or
        p.startswith("control/center/") or p=="run.cmd"
    )]
    if missing:
        print("HOLD: changed A/B paths not covered by current change record:",missing)
        return 2

    print("ci_guard: PASS",rec.get("id"))
    return 0

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(REPO))
    ap.add_argument("--base",default=os.environ.get("K01_DIFF_BASE","HEAD^"))
    args=ap.parse_args()
    raise SystemExit(main(Path(args.repo_root).resolve(),args.base))
