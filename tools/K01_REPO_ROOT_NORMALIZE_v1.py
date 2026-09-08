from __future__ import annotations
import argparse,json,subprocess,shutil,os
from datetime import datetime,timezone
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
KEEP={"README_K01_CAD_CONTROL.md","SETUP_K01_GIT_HOOKS.cmd"}
def tracked(p):
    try:
        rel=str(p.relative_to(R)).replace("\\","/")
        rc=subprocess.run(["git","ls-files","--error-unmatch",rel],cwd=R,
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return rc.returncode==0
    except Exception:return False
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    files=[]
    for p in R.iterdir():
        if not p.is_file() or p.name in KEEP:continue
        if p.name.startswith(("RUN_","PATCH_")) and p.suffix.lower() in (".cmd",".py"):
            files.append(p)
        elif p.name.startswith(("README_GATE","README_PATCH")) and p.suffix.lower()==".md":
            files.append(p)
    print("K01 repo-root normalization")
    print("Legacy root files:",len(files))
    for p in sorted(files):
        print("[TRACKED]" if tracked(p) else "[UNTRACKED]",p.name)
    if not a.apply:
        print("[DRY RUN] Nothing moved.");return 0
    dest=R/".local_archive"/"legacy_root_20260903";dest.mkdir(parents=True,exist_ok=True)
    moved=[]
    for p in files:
        t=dest/p.name
        if t.exists():continue
        shutil.move(str(p),str(t));moved.append({"src":str(p),"dst":str(t),"was_tracked":tracked(p)})
    out=R/"reports"/"cad"/"current"/"K01_REPO_ROOT_NORMALIZE_20260903.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"status":"PASS","created_utc":datetime.now(timezone.utc).isoformat(),
       "moved":moved},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] Root legacy launchers archived locally.")
    print("Git status:")
    subprocess.run(["git","status","--short"],cwd=R)
    return 0
if __name__=="__main__":raise SystemExit(main())
