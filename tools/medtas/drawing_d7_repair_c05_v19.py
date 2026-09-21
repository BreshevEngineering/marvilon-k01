from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import shutil
import time

from drawing_d3_d7_v15_common import (
    ROOT, dump, run, sw_running, compile_helper, parse_kv, workspace_paths
)

CS = ROOT / "cad_api/solidworks_2018_proven/current/K01_D7_REPAIR_C05_V19/K01D006RemoveC05V19.cs"
OUT = ROOT / "reports/drawing/current/K01-D-006_D7_REPAIR_C05_V19_CURRENT.json"
RAW = ROOT / "reports/cad/d7_repair_c05_v19_current/K01_D006_D7_REPAIR_C05_V19_RAW_CURRENT.txt"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wait_sw_exit(seconds: float = 20.0) -> bool:
    end = time.time() + seconds
    while time.time() < end:
        if not sw_running():
            return True
        time.sleep(0.5)
    return not sw_running()


def main() -> int:
    backup = None
    try:
        if sw_running():
            raise RuntimeError("Close SolidWorks before V19 drawing repair.")

        _, part_s, drawing_s = workspace_paths()
        part = Path(part_s)
        drawing = Path(drawing_s)
        if not part.exists():
            raise RuntimeError(f"workspace part missing: {part}")
        if not drawing.exists():
            raise RuntimeError(f"workspace drawing missing: {drawing}")
        if not CS.exists():
            raise RuntimeError(f"V19 helper source missing: {CS.relative_to(ROOT)}")

        part_before = sha256(part)
        drawing_before = sha256(drawing)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = ROOT / "reports/cad/d7_repair_c05_v19_history" / stamp
        backup_dir.mkdir(parents=True, exist_ok=False)
        backup = backup_dir / drawing.name
        shutil.copy2(drawing, backup)
        (backup_dir / "README.txt").write_text(
            "Controlled V19 pre-mutation backup of SAME K01-D-006 exemplar drawing.\n"
            f"source={drawing}\nsha256={drawing_before}\n"
            "Scope: remove exactly one visible unauthorized C05 / Ø33 display dimension only.\n",
            encoding="utf-8",
        )

        exe = compile_helper(CS, "K01D006RemoveC05V19.exe", RAW.parent / "build")
        RAW.parent.mkdir(parents=True, exist_ok=True)

        cp = run(
            [
                str(exe),
                "--drawing", str(drawing),
                "--part", str(part),
                "--report", str(RAW),
            ],
            timeout=600,
        )
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")

        if not RAW.exists():
            raise RuntimeError("V19 raw report missing")
        kv = parse_kv(RAW)
        if kv.get("STATUS") != "PASS_D7_REPAIR_C05_V19_APPLY":
            if backup.exists():
                shutil.copy2(backup, drawing)
            raise RuntimeError(
                "V19 helper did not pass; drawing restored from backup. "
                f"helper_status={kv.get('STATUS','')}"
            )

        if not wait_sw_exit():
            raise RuntimeError(
                "V19 repair passed but SLDWORKS.exe did not exit within 20 s. "
                "Drawing is saved; close/kill SolidWorks and rerun D7 only."
            )

        part_after = sha256(part)
        drawing_after = sha256(drawing)
        if part_after != part_before:
            if backup.exists():
                shutil.copy2(backup, drawing)
            raise RuntimeError("V19 changed workspace PART SHA; drawing restored and gate held.")
        if drawing_after == drawing_before:
            raise RuntimeError("V19 reported PASS but drawing SHA did not change.")

        payload = {
            "schema": "k01.d006.d7_repair_c05.v19",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS_D7_REPAIR_C05_V19_APPLY__D7_REVERIFY_REQUIRED",
            "scope": {
                "same_v12_exemplar": True,
                "drawing": str(drawing),
                "part": str(part),
                "mutation": "DELETE_EXACTLY_ONE_VISIBLE_UNAUTHORIZED_C05_DRAWING_ANNOTATION",
                "model_pmi_mutated": False,
                "canonical_cad_mutated": False,
            },
            "sha": {
                "part_before": part_before,
                "part_after": part_after,
                "part_invariant": part_before == part_after,
                "drawing_before": drawing_before,
                "drawing_after": drawing_after,
                "drawing_changed": drawing_before != drawing_after,
            },
            "backup": str(backup),
            "raw_report": str(RAW.relative_to(ROOT)),
            "next": "Run D7 semantic QA immediately. Do not make any other drawing edits before D7.",
        }
        dump(OUT, payload)
        print("STATUS:", payload["status"])
        print("PART SHA INVARIANT:", payload["sha"]["part_invariant"])
        print("DRAWING CHANGED:", payload["sha"]["drawing_changed"])
        print("BACKUP:", backup)
        print("REPORT:", OUT)
        return 0

    except Exception as e:
        dump(
            OUT,
            {
                "schema": "k01.d006.d7_repair_c05.v19",
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "status": "HOLD_D7_REPAIR_C05_V19",
                "error": repr(e),
                "backup": str(backup) if backup else None,
            },
        )
        print("STATUS: HOLD_D7_REPAIR_C05_V19")
        print("ERROR:", repr(e))
        if backup:
            print("BACKUP:", backup)
        print("REPORT:", OUT)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
