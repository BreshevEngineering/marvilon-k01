from __future__ import annotations
import argparse, json, shutil, subprocess
from pathlib import Path
R=Path(r"D:\BreshevEngineering\marvilon-k01")
PATTERNS=["PATCH_GATE*.py","PATCH_GATE*.cmd","README_GATE*.md","README_COM_FIX.md",
          "RUN_1_K01_GATE03E*.cmd","RUN_2_K01_GATE03E*.cmd","RUN_K01_GATE03*.cmd",
          "RUN_K01_GATE04A*.cmd","PATCH_K01_MASTER_P013_RETENTION.*"]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); a=ap.parse_args()
    dest=R/".local_archive"/"20260902_gate03_dev"; files=[]
    for pat in PATTERNS: files += [p for p in R.glob(pat) if p.is_file()]
    if (R/"tools").exists(): files += list((R/"tools").glob("*.pre_v*.py"))
    if (R/"master").exists(): files += list((R/"master").glob("*.pre_*.json"))
    files=sorted(set(files))
    print("Files to local archive:",len(files))
    for p in files: print(" ",p.relative_to(R))
    if not a.apply:
        print("[DRY RUN] No files moved."); return 0
    manifest=[]
    for p in files:
        if not p.exists(): continue
        t=dest/p.relative_to(R); t.parent.mkdir(parents=True,exist_ok=True)
        if not t.exists(): shutil.move(str(p),str(t)); manifest.append({"src":str(p),"dst":str(t)})
    for name in ["__pycache__",".pytest_cache"]:
        for p in R.rglob(name):
            if ".git" not in p.parts and ".local_archive" not in p.parts: shutil.rmtree(p,ignore_errors=True)
    gi=R/".gitignore"; txt=gi.read_text(encoding="utf-8",errors="ignore")
    add="\n# Local engineering-history archive\n.local_archive/\n*.CWR\n*.rsl\n*.analysis.png\n"
    if ".local_archive/" not in txt: gi.write_text(txt.rstrip()+"\n"+add,encoding="utf-8")
    mp=R/"reports"/"cad"/"current"/"K01_REPO_CLEANUP_20260902.json"
    mp.write_text(json.dumps({"status":"PASS","moves":manifest},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] repo debug files archived locally.")
    try:
        print(subprocess.check_output(["git","status","--short"],cwd=R,text=True,errors="ignore"))
    except Exception: pass
    return 0
if __name__=="__main__": raise SystemExit(main())
