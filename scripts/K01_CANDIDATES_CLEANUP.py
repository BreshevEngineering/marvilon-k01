from __future__ import annotations
import argparse, shutil
from datetime import datetime
from pathlib import Path

C=Path(r"D:\Marvilon\K01\cad\candidates")

GROUPS={
 "rejected":[
   "K01-P-007_Hermetic_Magnetic_Can_GATE03B*",
   "K01-P-007_Hermetic_Magnetic_Can_GATE03E*",
   "K01-P-003_GATE03E_COLLAR*",
   "K01-P-003_Cartridge_Body_GATE03G_CANDIDATE_20260902_121828*",
   "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE_20260902_122840*",
   "K01-P-008_Internal_Magnetic_Follower_GATE04A*",
 ],
 "verification":[
   "K01-A-001_GATE03C*","K01-A-001_GATE03F*","K01-A-001_GATE03I*"
 ],
 "simulation":[
   "*K01_P007_STATIC_DP_POS_020bar*","*K01_P007_BUCKLING_DP_NEG_020bar*",
   "K01_P007_STATIC_DP_POS_020bar-*.csv","K01_P007_BUCKLING_DP_NEG_020bar-*.csv"
 ],
 "accepted_history":[
   "K01-P-003_Cartridge_Body_GATE03G_CANDIDATE_20260902_122316*",
   "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE_20260902_123200*",
 ]
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    stamp="20260902"
    moves=[]
    for group,pats in GROUPS.items():
        dest=C/"archive"/group/stamp
        for pat in pats:
            for p in C.glob(pat):
                if "~$" in p.name: continue
                if "archive" in p.parts: continue
                moves.append((p,dest/p.name))
    # lock/temp files separately
    locks=list(C.glob("~$*"))
    for src,dst in moves:
        print(group if False else "",src,"->",dst)
    print(f"Planned moves: {len(moves)}; temp lock files: {len(locks)}")
    if not args.apply:
        print("[DRY RUN] Close SOLIDWORKS, verify production promotion first, then run --apply.")
        return
    for src,dst in moves:
        if not src.exists(): continue
        dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists(): continue
        shutil.move(str(src),str(dst))
    for p in locks:
        try: p.unlink()
        except Exception: pass
    print("[PASS] candidates organized without deleting engineering evidence.")
if __name__=="__main__":
    main()
