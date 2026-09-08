from __future__ import annotations
import argparse, json, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

C=Path(r"D:\Marvilon\K01\cad\candidates")
R=Path(r"D:\BreshevEngineering\marvilon-k01")
DEST=C/"archive"/"rejected_gate04b_failed"/"20260903"

def sw_running():
    try:
        out=subprocess.check_output(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],
                                    text=True,errors="ignore")
        return "SLDWORKS.exe" in out
    except Exception:return False

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    gate_files=[]
    for p in C.iterdir():
        if not p.is_file():continue
        n=p.name.lower()
        if "gate04b_datumc_v3_" in n or "gate04b_datumc_v4_" in n or "gate04b_datumc_20260903_" in n:
            gate_files.append(p)
    locks=[p for p in C.iterdir() if p.is_file() and p.name.startswith("~$")]
    others=[p for p in C.iterdir()
            if p.name!="archive" and p not in gate_files and p not in locks]

    print("="*80);print("K01 FAILED-GATE04B CANDIDATE CLEANUP");print("="*80)
    print("Failed Gate04B files:",len(gate_files))
    for p in sorted(gate_files):print("[ARCHIVE]",p.name)
    print("Stale locks:",len(locks))
    for p in sorted(locks):print("[DELETE]",p.name)
    print("Other top-level items:",len(others))
    for p in sorted(others):print("[REVIEW]",p.name)

    if not a.apply:
        print("[DRY RUN] Nothing changed.");return 0
    if sw_running():raise RuntimeError("Close SOLIDWORKS before APPLY.")
    DEST.mkdir(parents=True,exist_ok=True)
    moved=[]
    for p in gate_files:
        d=DEST/p.name
        if d.exists():raise RuntimeError(f"Destination exists: {d}")
        shutil.move(str(p),str(d));moved.append({"src":str(p),"dst":str(d)})
    for p in locks:
        if p.exists():p.unlink()
    others_after=[p for p in C.iterdir() if p.name!="archive"]
    if others_after:
        raise RuntimeError("Unexpected top-level candidates remain: "+", ".join(p.name for p in others_after))
    out=R/"reports"/"cad"/"current"/"K01_GATE04B_FAILED_CLEANUP_20260903.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"status":"PASS","created_utc":datetime.now(timezone.utc).isoformat(),
      "moved":moved,"deleted_locks":[str(p) for p in locks]},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] candidates top-level clean.")
    print("Report:",out);return 0
if __name__=="__main__":raise SystemExit(main())
