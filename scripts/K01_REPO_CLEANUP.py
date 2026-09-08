from __future__ import annotations
import argparse, shutil
from datetime import datetime
from pathlib import Path

R=Path(r"D:\BreshevEngineering\marvilon-k01")
PATTERNS=[
 "PATCH_GATE*.py","PATCH_GATE*.cmd","README_GATE*.md","README_COM_FIX.md",
 "README_GATE03A_COM_FIX.md","README_GATE03B_SELECT2_FIX.md","README_GATE03B_SW2018.md",
 "RUN_1_K01_GATE03E*.cmd","RUN_2_K01_GATE03E*.cmd","RUN_K01_GATE03*.cmd",
 "RUN_K01_GATE04A*.cmd","PATCH_K01_MASTER_P013_RETENTION.*",
]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    dest=R/".local_archive"/"20260902_gate03_dev"
    files=[]
    for pat in PATTERNS:
        files += [p for p in R.glob(pat) if p.is_file()]
    files += [p for p in (R/"tools").glob("*.pre_v*.py")] if (R/"tools").exists() else []
    files += [p for p in (R/"master").glob("*.pre_*.json")] if (R/"master").exists() else []
    files=sorted(set(files))
    print("Files to local archive:",len(files))
    for p in files: print(" ",p.relative_to(R))
    if not args.apply:
        print("[DRY RUN] No files moved.")
        return
    dest.mkdir(parents=True,exist_ok=True)
    for p in files:
        rel=p.relative_to(R)
        target=dest/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists(): shutil.move(str(p),str(target))
    for name in ["__pycache__",".pytest_cache"]:
        for p in R.rglob(name):
            if ".git" in p.parts or ".local_archive" in p.parts: continue
            shutil.rmtree(p,ignore_errors=True)
    for p in R.glob("#U*"):
        try: p.unlink()
        except Exception: pass
    gi=R/".gitignore"
    txt=gi.read_text(encoding="utf-8",errors="ignore")
    additions="""
# Local engineering-history archive
.local_archive/

# SOLIDWORKS solver / transient outputs
*.CWR
*.rsl
*.analysis.png

# Generated binary reference geometry (source/spec remains in Git)
reference/**/*.STEP
reference/**/*.step
reference/**/*.STP
reference/**/*.stp
reference/**/*.dxf
"""
    if ".local_archive/" not in txt:
        gi.write_text(txt.rstrip()+"\n"+additions,encoding="utf-8")
    print("[PASS] Repo working tree cleaned. Review `git status`; do not blindly git add -A.")
if __name__=="__main__":
    main()
