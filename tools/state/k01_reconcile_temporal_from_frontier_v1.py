from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
ALLOWED={
 "STATE_SOURCE_DRIFT","NEW_DECISION_NOT_REDUCED","DELIVERABLE_MISMATCH_MANIFEST_GOAL",
 "DELIVERABLE_MISMATCH_NEXT_GOAL","ACTIVE_DEPENDENCY_MISMATCH","STATE_EPOCH_MISMATCH",
 "TEXT_STATE_EPOCH_MISSING","DRAWING_IDENTITY_MISMATCH","VISUAL_QA_OLD_WORKSPACE",
 "AI_FIRST_READ_TEMPORAL_PRECEDENCE_BROKEN","LEGACY_STAGE3_README_STILL_CURRENT"}

def rd(p):
    try:return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:return {}

def run(c,repo):
    print(">"," ".join(map(str,c)))
    return subprocess.run(c,cwd=repo,check=True,text=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=str(R))
    a=ap.parse_args()
    repo=Path(a.repo_root)

    old=rd(repo/"reports/control/K01_TEMPORAL_COHERENCE_CURRENT.json")
    issues=old.get("issues") or []
    unknown=[x for x in issues if x.get("rule") not in ALLOWED]
    if unknown:
        print("HOLD: temporal state contains non-navigation/source-drift issues not safe for automatic reconciliation:")
        for x in unknown:print(json.dumps(x,ensure_ascii=False))
        return 2

    run([sys.executable,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo)],repo)
    run([sys.executable,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],repo)
    run([sys.executable,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report"],repo)
    print("PASS: temporal + semantic state reconciled from Goal Lock / Completion Frontier / current engineering authorities.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
