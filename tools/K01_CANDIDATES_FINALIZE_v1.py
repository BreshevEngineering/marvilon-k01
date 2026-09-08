from __future__ import annotations
import argparse, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

C=Path(r"D:\Marvilon\K01\cad\candidates")
R=Path(r"D:\BreshevEngineering\marvilon-k01")

def sw_running():
    try:
        out=subprocess.check_output(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],
                                    text=True,errors="ignore")
        return "SLDWORKS.exe" in out
    except Exception:
        return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()

    if not C.exists(): raise FileNotFoundError(C)

    locks=sorted([p for p in C.iterdir() if p.is_file() and p.name.startswith("~$")])
    remaining=[]
    for p in sorted(C.iterdir(),key=lambda x:x.name.lower()):
        if p.name=="archive" or p.name.startswith("~$"): continue
        remaining.append(p)

    print("="*78)
    print("K01 CANDIDATES FINALIZE")
    print("="*78)
    print("Stale lock files:",len(locks))
    for p in locks: print("[DELETE LOCK]",p.name)
    print("Non-archive top-level items:",len(remaining))
    for p in remaining:
        print("[REVIEW]", "DIR" if p.is_dir() else "FILE", p.name)

    if not a.apply:
        print("[DRY RUN] Nothing changed.")
        return 0

    if sw_running():
        raise RuntimeError("SOLIDWORKS is running. Close it before APPLY.")

    for p in locks:
        if p.exists(): p.unlink()

    # Do not silently move unknown active candidates. The previous v5 sweep
    # should already have archived all known history.
    remaining_after=[p for p in C.iterdir()
                     if p.name!="archive" and not p.name.startswith("~$")]
    if remaining_after:
        raise RuntimeError(
            "Top-level candidates still contains non-archive items. "
            "Review before any forced move: " +
            ", ".join(p.name for p in remaining_after)
        )

    out=R/"reports"/"cad"/"current"/"K01_CANDIDATES_FINALIZE_20260903.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({
      "schema":"k01_candidates_finalize_v1","status":"PASS",
      "created_utc":datetime.now(timezone.utc).isoformat(),
      "deleted_stale_locks":[str(p) for p in locks],
      "top_level_state":["archive"],
      "rule":"Top-level candidates is empty of history; new active candidates may be created only by current gates."
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] candidates top level normalized.")
    print("Report:",out)
    return 0
if __name__=="__main__": raise SystemExit(main())
