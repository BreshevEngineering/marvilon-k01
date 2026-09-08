from __future__ import annotations
import argparse,subprocess
from pathlib import Path
C=Path(r"D:\Marvilon\K01\cad\candidates")
def sw_running():
    try:
        return "SLDWORKS.exe" in subprocess.check_output(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],text=True,errors="ignore")
    except Exception:return False
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    locks=sorted([p for p in C.rglob("~$*") if p.is_file()])
    print("Archived/runtime SolidWorks lock files:",len(locks))
    for p in locks:print("[LOCK]",p)
    if not a.apply:
        print("[DRY RUN] Nothing deleted.");return 0
    if sw_running():raise RuntimeError("Close SOLIDWORKS before deleting lock files.")
    for p in locks:p.unlink()
    print("[PASS] Runtime lock files removed. No engineering file deleted.");return 0
if __name__=="__main__":raise SystemExit(main())
