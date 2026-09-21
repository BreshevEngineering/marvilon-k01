from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")

def run(repo:Path, rel:str, *args, allow_nonzero=False):
    p=repo/rel
    if not p.is_file():
        print("HOLD: required tool missing:",p); return 2
    cp=subprocess.run([sys.executable,str(p),*args],cwd=repo,text=True)
    if cp.returncode!=0 and not allow_nonzero:
        print("HOLD:",rel,"rc=",cp.returncode)
    return cp.returncode

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=str(R));a=ap.parse_args();repo=Path(a.repo_root).resolve()
    print("============================================================")
    print("K01 GLOBAL PROJECT STATE SYNC V3")
    print("Projections -> Authority State Epoch -> Temporal/Semantic/Project Guards")
    print("NO NATIVE CAD/DRAWING MUTATION")
    print("============================================================")

    # Refresh cross-domain projections first. The lifecycle reducer records their semantic digests as
    # projection observations, but they MUST NOT feed back into State Epoch identity.
    rc=run(repo,"tools/medtas/engineering_system_guard_v14.py","--repo-root",str(repo))
    if rc!=0:return rc
    rc=run(repo,"tools/control/k01_project_control_spine_v1.py","--repo-root",str(repo))
    if rc!=0:return rc
    # Git/GitHub status is read-only. HOLD on behind/diverged; source dirty alone is visible but not an automatic stop.
    rc=run(repo,"tools/control/k01_git_github_status_v1.py","--repo-root",str(repo))
    if rc!=0:return rc

    rc=run(repo,"tools/state/k01_decision_identity_guard_v1.py","--repo-root",str(repo))
    if rc!=0:return rc
    rc=run(repo,"tools/state/k01_engineering_value_coherence_guard_v1.py","--repo-root",str(repo))
    if rc!=0:return rc

    # Single canonical lifecycle reducer. Do NOT invoke the legacy current_state_reducer_v1 here.
    rc=run(repo,"tools/state/k01_lifecycle_state_reducer_v2.py","--repo-root",str(repo))
    if rc!=0:return rc

    # Guards run only after the reducer has rebound all navigation artifacts to one State Epoch.
    rc=run(repo,"tools/state/k01_temporal_coherence_guard_v1.py","--repo-root",str(repo),"--write-report")
    if rc!=0:return rc
    rc=run(repo,"tools/state/k01_semantic_coherence_guard_v1.py","--repo-root",str(repo),"--write-report")
    if rc!=0:return rc
    rc=run(repo,"tools/state/k01_project_control_guard_v1.py","--repo-root",str(repo))
    if rc!=0:return rc

    print("PASS_GLOBAL_PROJECT_STATE_SYNC_V3")
    return 0

if __name__=="__main__":raise SystemExit(main())
