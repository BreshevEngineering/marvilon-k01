from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys
from datetime import datetime
from pathlib import Path

REPO = Path(r"D:\BreshevEngineering\marvilon-k01")
CAD = Path(r"D:\Marvilon\K01\cad")
P003_REPORT = REPO / "reports" / "cad" / "current" / "K01_P003_GATE03G_BUILD.json"
P007_REPORT = REPO / "reports" / "cad" / "current" / "K01_P007_GATE03H_BUILD.json"
P003_PROD = CAD / "parts" / "K01-P-003_Cartridge_Body.SLDPRT"
P007_PROD = CAD / "parts" / "K01-P-007_Hermetic_Magnetic_Can.SLDPRT"
ASM_PROD = CAD / "assemblies" / "K01-A-001_Calibration_Module.SLDASM"

def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def sw_running():
    try:
        out=subprocess.check_output(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],text=True,errors="ignore")
        return "SLDWORKS.exe".lower() in out.lower()
    except Exception:
        return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    if sw_running():
        print("[STOP] SOLIDWORKS.exe is running. Close SOLIDWORKS before production promotion.")
        return 2
    for p in [P003_REPORT,P007_REPORT,P003_PROD,P007_PROD,ASM_PROD]:
        if not p.exists(): raise FileNotFoundError(p)
    r3=json.loads(P003_REPORT.read_text(encoding="utf-8"))
    r7=json.loads(P007_REPORT.read_text(encoding="utf-8"))
    c3=Path(r3["native_candidate"]); c7=Path(r7["native_candidate"])
    for p in [c3,c7]:
        if not p.exists(): raise FileNotFoundError(f"Accepted native candidate missing: {p}")
    print("P003:",c3,"->",P003_PROD)
    print("P007:",c7,"->",P007_PROD)
    if not args.apply:
        print("[DRY RUN] Re-run with --apply after checking the paths.")
        return 0
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    backup=CAD/"archive"/"pre_p003_p007_promotion"/stamp
    backup.mkdir(parents=True,exist_ok=False)
    for p in [P003_PROD,P007_PROD,ASM_PROD]:
        shutil.copy2(p,backup/p.name)
    before={"P003":sha(P003_PROD),"P007":sha(P007_PROD),"assembly":sha(ASM_PROD)}
    shutil.copy2(c3,P003_PROD)
    shutil.copy2(c7,P007_PROD)
    after={"P003":sha(P003_PROD),"P007":sha(P007_PROD),"assembly":sha(ASM_PROD)}
    manifest={
      "status":"PROMOTED_PENDING_SOLIDWORKS_REOPEN_QA",
      "timestamp":stamp,
      "backup":str(backup),
      "source_candidates":{"P003":str(c3),"P007":str(c7)},
      "stable_targets":{"P003":str(P003_PROD),"P007":str(P007_PROD),"assembly":str(ASM_PROD)},
      "sha_before":before,"sha_after":after,
      "next":"Open stable K01-A-001, Force Rebuild, verify 26 mates/0 errors and run one interference detection."
    }
    mp=REPO/"reports"/"cad"/"current"/"K01_P003_P007_PRODUCTION_PROMOTION.json"
    mp.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] Stable P003/P007 files promoted. Assembly file itself was not rewritten.")
    print("Backup:",backup)
    print("Manifest:",mp)
    return 0
if __name__=="__main__":
    raise SystemExit(main())
