from __future__ import annotations
import argparse, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

C = Path(r"D:\Marvilon\K01\cad\candidates")
R = Path(r"D:\BreshevEngineering\marvilon-k01")
STAMP = "20260903"

def sw_running():
    try:
        out=subprocess.check_output(["tasklist","/FI","IMAGENAME eq SLDWORKS.exe"],
                                    text=True,errors="ignore")
        return "SLDWORKS.exe" in out
    except Exception:
        return False

def classify(p: Path):
    n=p.name
    low=n.lower()

    if n=="archive":
        return None

    # Runtime folders created beside SOLIDWORKS Simulation result files.
    if p.is_dir():
        if "k01-p-007_hermetic_magnetic_can_gate03h_native_trim_candidate" in low:
            return "simulation_workdirs"
        return "UNCLASSIFIED"

    if n.startswith("~$"):
        return "lock_temp"

    if n in ("BenchMark.txt","PerformanceLog.txt"):
        return "runtime_logs"

    if "gate04b_datumc" in low and n.lower().endswith((".sldprt",".step")):
        return "rejected_gate04b_failed"

    if "gate04a_pocket820" in low:
        return "rejected"

    if any(x in low for x in (
        "gate03b_candidate_20260902_085544",
        "gate03b_v4_candidate_20260902_090924",
        "gate03g_candidate_20260902_121828",
        "gate03h_native_trim_candidate_20260902_122840",
    )):
        return "rejected"

    if any(x in low for x in (
        "gate03e_v5_candidate_20260902_114833",
        "gate03e_collar_addon_reference_20260902_115731",
    )):
        return "superseded_reference"

    if any(x in low for x in ("gate03c_","gate03f_","gate03i_")) and n.lower().endswith(".sldasm"):
        return "verification"

    if any(x in low for x in (
        "k01_p007_static_dp_pos_020bar",
        "k01_p007_buckling_dp_neg_020bar",
    )):
        return "simulation"

    if (
        "k01-p-003_cartridge_body_gate03g_candidate_20260902_122316" in low
        or "k01-p-007_hermetic_magnetic_can_gate03h_native_trim_candidate_20260902_123200" in low
    ) and n.lower().endswith((".sldprt",".step")):
        return "accepted_history"

    return "UNCLASSIFIED"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--apply",action="store_true")
    ap.add_argument("--delete-locks",action="store_true")
    a=ap.parse_args()

    if not C.exists():
        raise FileNotFoundError(C)

    rows=[]
    unclassified=[]
    locks=[]
    for p in sorted(C.iterdir(), key=lambda x:x.name.lower()):
        g=classify(p)
        if g is None: continue
        if g=="UNCLASSIFIED":
            unclassified.append(p); continue
        if g=="lock_temp":
            locks.append(p); continue
        rows.append((g,p,C/"archive"/g/STAMP/p.name))

    print("="*80)
    print("K01 CANDIDATES TOP-LEVEL SWEEP v5")
    print("="*80)
    print("Planned archive moves:",len(rows))
    for g,s,d in rows:
        kind="DIR " if s.is_dir() else "FILE"
        print(f"[{g:24}] {kind} {s.name} -> {d}")
    print("Lock/temp:",len(locks))
    for p in locks: print("[LOCK]",p.name)
    print("UNCLASSIFIED:",len(unclassified))
    for p in unclassified: print("[KEEP/REVIEW]",p.name)

    if not a.apply:
        print("[DRY RUN] Nothing changed.")
        return 0

    if sw_running():
        raise RuntimeError("Close SOLIDWORKS before APPLY.")

    manifest=[]
    for g,s,d in rows:
        if not s.exists(): continue
        d.parent.mkdir(parents=True,exist_ok=True)
        if d.exists():
            raise RuntimeError(f"Destination exists: {d}")
        shutil.move(str(s),str(d))
        manifest.append({"group":g,"source":str(s),"destination":str(d)})

    deleted=[]
    if a.delete_locks:
        for p in locks:
            if p.exists():
                p.unlink(); deleted.append(str(p))

    out=R/"reports"/"cad"/"current"/"K01_CANDIDATES_SWEEP_V5_20260903.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({
        "schema":"k01_candidates_sweep_v5",
        "status":"PASS",
        "created_utc":datetime.now(timezone.utc).isoformat(),
        "moves":manifest,
        "deleted_locks":deleted,
        "unclassified_left":[str(p) for p in unclassified],
        "rule":"Top-level candidates should contain only archive plus current active candidates."
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("[PASS] Sweep complete.")
    print("Report:",out)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
