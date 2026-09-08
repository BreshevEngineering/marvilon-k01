from __future__ import annotations
import argparse, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
LOCAL=R/".local_archive"/"legacy_root_20260903"
DIAG=R/"control"/"diagnostics"
SETUP=R/"control"/"setup"

# Known useful tracked root launchers are retained in the repository but moved
# under control/diagnostics. Everything else matching legacy RUN/PATCH patterns
# is archived locally; Git history already preserves tracked obsolete files.
KEEP_AS_DIAGNOSTICS={
 "RUN_SW_CAD_SNAPSHOT_v07.cmd",
 "RUN_SW_API_GATE02_WRITE_TEST_v05_FINAL.cmd",
}
KEEP_AS_SETUP={"SETUP_K01_GIT_HOOKS.cmd"}

def is_tracked(p):
    try:
        rel=str(p.relative_to(R)).replace("\\","/")
        rc=subprocess.run(["git","ls-files","--error-unmatch",rel],cwd=R,
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return rc.returncode==0
    except Exception:return False

def classify(p):
    n=p.name
    if n in KEEP_AS_DIAGNOSTICS:return ("diagnostics",DIAG/n)
    if n in KEEP_AS_SETUP:return ("setup",SETUP/n)
    if n in ("README.md",".gitignore",".gitattributes","pyproject.toml","CHANGELOG.md",
             "README_K01_CAD_CONTROL.md"):
        return None
    if n.startswith(("RUN_","PATCH_")) and p.suffix.lower() in (".cmd",".py"):
        return ("local_archive",LOCAL/n)
    if n.startswith(("README_GATE","README_PATCH","README_RUN_ORDER")) and p.suffix.lower()==".md":
        return ("local_archive",LOCAL/n)
    # obvious accidental small encoding-artifact/root scratch files
    if p.is_file() and p.stat().st_size < 4096 and "." not in n and n not in ("LICENSE",):
        return ("local_archive",LOCAL/n)
    # Old human control spreadsheet is superseded by control center v2.
    if n=="K01_PROJECT_CONTROL_v3_20260902.xlsx":
        return ("local_archive",LOCAL/n)
    return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    moves=[]
    for p in sorted(R.iterdir(),key=lambda x:x.name.lower()):
        if not p.is_file():continue
        c=classify(p)
        if c:moves.append((p,c[0],c[1],is_tracked(p)))

    print("="*90)
    print("K01 REPO ROOT NORMALIZATION v2")
    print("="*90)
    print("Planned moves:",len(moves))
    for src,group,dst,tr in moves:
        print(f"[{'TRACKED' if tr else 'UNTRACKED':9}] [{group:13}] {src.name} -> {dst.relative_to(R)}")

    if not a.apply:
        print("[DRY RUN] Nothing moved.")
        return 0

    LOCAL.mkdir(parents=True,exist_ok=True);DIAG.mkdir(parents=True,exist_ok=True);SETUP.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for src,group,dst,tr in moves:
        if not src.exists():continue
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            raise RuntimeError(f"Destination already exists: {dst}")
        shutil.move(str(src),str(dst))
        manifest.append({"source":str(src),"destination":str(dst),"group":group,"was_tracked":tr})

    # Remove Python caches anywhere outside .git/local archive.
    for name in ("__pycache__",".pytest_cache"):
        for p in R.rglob(name):
            if ".git" in p.parts or ".local_archive" in p.parts:continue
            shutil.rmtree(p,ignore_errors=True)

    gi=R/".gitignore"
    txt=gi.read_text(encoding="utf-8",errors="ignore")
    additions=[]
    for line in (".local_archive/","*.CWR","*.rsl","*.analysis.png","~$*"):
        if line not in txt:additions.append(line)
    if additions:
        gi.write_text(txt.rstrip()+"\n\n# Local generated / legacy engineering artifacts\n"+"\n".join(additions)+"\n",
                      encoding="utf-8")

    out=R/"reports"/"cad"/"current"/"K01_REPO_ROOT_NORMALIZE_V2_20260903.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({
       "schema":"k01_repo_root_normalize_v2","status":"PASS",
       "created_utc":datetime.now(timezone.utc).isoformat(),
       "moves":manifest
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] Root normalized.")
    print("Git status:")
    subprocess.run(["git","status","--short"],cwd=R)
    print("Report:",out)
    return 0
if __name__=="__main__":raise SystemExit(main())
