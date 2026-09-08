from __future__ import annotations
import argparse, json, os, shutil, subprocess
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

C = Path(r"D:\Marvilon\K01\cad\candidates")
R = Path(r"D:\BreshevEngineering\marvilon-k01")
STAMP = "20260902"

# IMPORTANT:
# First matching rule owns the file. No duplicate source entries are allowed.
RULES = [
    ("rejected", [
        "K01-P-007_Hermetic_Magnetic_Can_GATE03B_CANDIDATE_20260902_085544.*",
        "K01-P-007_Hermetic_Magnetic_Can_GATE03B_V4_CANDIDATE_20260902_090924.*",
        "K01-P-003_Cartridge_Body_GATE03G_CANDIDATE_20260902_121828.*",
        "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE_20260902_122840.*",
        "K01-P-008_Internal_Magnetic_Follower_GATE04A_POCKET820_CANDIDATE_20260902_222131.*",
    ]),
    ("superseded_reference", [
        "K01-P-007_Hermetic_Magnetic_Can_GATE03E_V5_CANDIDATE_20260902_114833.SLDPRT",
        "K01-P-007_Hermetic_Magnetic_Can_GATE03E_V5_CANDIDATE_20260902_114833.STEP",
        "K01-P-003_GATE03E_COLLAR_ADDON_REFERENCE_20260902_115731.SLDPRT",
        "K01-P-003_GATE03E_COLLAR_ADDON_REFERENCE_20260902_115731.STEP",
    ]),
    ("verification", [
        "K01-A-001_GATE03C_*.SLDASM",
        "K01-A-001_GATE03F_*.SLDASM",
        "K01-A-001_GATE03I_*.SLDASM",
    ]),
    ("simulation", [
        "*K01_P007_STATIC_DP_POS_020bar*.analysis.png",
        "*K01_P007_STATIC_DP_POS_020bar*.CWR",
        "*K01_P007_STATIC_DP_POS_020bar*.LOG",
        "K01_P007_STATIC_DP_POS_020bar*.csv",
        "*K01_P007_BUCKLING_DP_NEG_020bar*.analysis.png",
        "*K01_P007_BUCKLING_DP_NEG_020bar*.CWR",
        "*K01_P007_BUCKLING_DP_NEG_020bar*.LOG",
        "*K01_P007_BUCKLING_DP_NEG_020bar*.rsl",
        "K01_P007_BUCKLING_DP_NEG_020bar*.csv",
    ]),
    ("accepted_history", [
        "K01-P-003_Cartridge_Body_GATE03G_CANDIDATE_20260902_122316.SLDPRT",
        "K01-P-003_Cartridge_Body_GATE03G_CANDIDATE_20260902_122316.STEP",
        "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE_20260902_123200.SLDPRT",
        "K01-P-007_Hermetic_Magnetic_Can_GATE03H_NATIVE_TRIM_CANDIDATE_20260902_123200.STEP",
    ]),
]

def solidworks_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
            text=True, errors="ignore"
        )
        return "SLDWORKS.exe" in out
    except Exception:
        return False

def plan_moves():
    ownership = OrderedDict()
    for group, patterns in RULES:
        for pat in patterns:
            for p in sorted(C.glob(pat)):
                if not p.is_file():
                    continue
                if "archive" in [x.lower() for x in p.parts]:
                    continue
                key = os.path.normcase(os.path.normpath(str(p)))
                if key in ownership:
                    continue
                ownership[key] = (group, p, C/"archive"/group/STAMP/p.name)
    return list(ownership.values())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--delete-locks", action="store_true")
    args=ap.parse_args()

    moves = plan_moves()
    locks = sorted([p for p in C.glob("~$*") if p.is_file()])

    print("K01 candidates cleanup v3")
    print("="*72)
    print("Unique planned moves:", len(moves))
    by_group={}
    for g,s,d in moves:
        by_group[g]=by_group.get(g,0)+1
        print(f"[{g}] {s.name} -> {d}")
    print("-"*72)
    print("By group:", by_group)
    print("Lock/temp files:", len(locks))
    for p in locks:
        print("  [LOCK]", p.name)

    if not args.apply:
        print("[DRY RUN] No files moved.")
        return 0

    if solidworks_running():
        raise RuntimeError(
            "SOLIDWORKS is running. Close it before candidate cleanup APPLY."
        )

    manifest=[]
    for g,s,d in moves:
        if not s.exists():
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        if d.exists():
            raise RuntimeError(f"Destination already exists: {d}")
        shutil.move(str(s), str(d))
        manifest.append({"group":g,"src":str(s),"dst":str(d)})

    deleted_locks=[]
    if args.delete_locks:
        for p in locks:
            if p.exists():
                p.unlink()
                deleted_locks.append(str(p))

    report = {
        "schema":"k01_candidates_cleanup_v3",
        "status":"PASS",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "moves":manifest,
        "deleted_lock_files":deleted_locks,
        "lock_files_left_in_place":[str(p) for p in locks if p.exists()],
        "note":"No engineering evidence deleted. Accepted, rejected, superseded-reference, verification and simulation evidence are separated."
    }
    out=R/"reports"/"cad"/"current"/"K01_CANDIDATES_ARCHIVE_V3_20260903.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] Candidates cleanup v3 complete.")
    print("Manifest:",out)
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("[FAIL]", type(exc).__name__, exc)
        raise
