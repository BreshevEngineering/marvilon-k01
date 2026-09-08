from __future__ import annotations
import argparse, json, shutil
from datetime import datetime
from pathlib import Path
C=Path(r"D:\Marvilon\K01\cad\candidates")
CAD=Path(r"D:\Marvilon\K01\cad")
R=Path(r"D:\BreshevEngineering\marvilon-k01")
GROUPS={
 "rejected":[
   "K01-P-007_Hermetic_Magnetic_Can_GATE03B*","K01-P-007_Hermetic_Magnetic_Can_GATE03E*",
   "K01-P-003_GATE03E_COLLAR*","K01-P-003_Cartridge_Body_GATE03G_CANDIDATE_20260902_121828*",
   "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE_20260902_122840*",
   "K01-P-008_Internal_Magnetic_Follower_GATE04A*"],
 "verification":["K01-A-001_GATE03C*","K01-A-001_GATE03F*","K01-A-001_GATE03I*"],
 "simulation":["*K01_P007_STATIC_DP_POS_020bar*","*K01_P007_BUCKLING_DP_NEG_020bar*"],
 "accepted_history":[
   "K01-P-003_Cartridge_Body_GATE03G_CANDIDATE_20260902_122316*",
   "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE_20260902_123200*"]
}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); a=ap.parse_args()
    stamp="20260902"; moves=[]
    for group,pats in GROUPS.items():
        for pat in pats:
            for p in C.glob(pat):
                if p.is_file() and "archive" not in p.parts and not p.name.startswith("~$"):
                    moves.append((group,p,C/"archive"/group/stamp/p.name))
    locks=[p for p in C.glob("~$*") if p.is_file()]
    print("Planned moves:",len(moves))
    for g,s,d in moves: print(f"[{g}] {s.name} -> {d}")
    print("Lock/temp files:",len(locks))
    if not a.apply:
        print("[DRY RUN] No files moved."); return 0
    manifest=[]
    for g,s,d in moves:
        if not s.exists(): continue
        d.parent.mkdir(parents=True,exist_ok=True)
        if d.exists():
            print("[SKIP exists]",d); continue
        shutil.move(str(s),str(d)); manifest.append({"group":g,"src":str(s),"dst":str(d)})
    for p in locks:
        try:p.unlink()
        except Exception:pass
    mp=R/"reports"/"cad"/"current"/"K01_CANDIDATES_ARCHIVE_20260902.json"
    mp.parent.mkdir(parents=True,exist_ok=True)
    mp.write_text(json.dumps({"status":"PASS","moves":manifest},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] candidates organized; no engineering evidence deleted.")
    print("Manifest:",mp); return 0
if __name__=="__main__": raise SystemExit(main())
