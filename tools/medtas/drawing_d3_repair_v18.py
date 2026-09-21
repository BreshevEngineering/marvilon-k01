from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

from drawing_d3_d7_v15_common import (
    ROOT, load, dump, run, sw_running, compile_helper, parse_kv, workspace_paths
)

CS = ROOT / "cad_api/solidworks_2018_proven/current/K01_D3_REPAIR_V18/K01P007D3RepairV18.cs"
D3 = ROOT / "reports/drawing/current/K01-P-007_D3_AUTHORING_VERIFY_CURRENT.json"
COH = ROOT / "reports/control/K01_ASSURANCE_COHERENCE_CURRENT.json"
PD = ROOT / "control/product_definition/K01_P007_PRODUCT_CHARACTERISTICS.json"
EXEC = ROOT / "control/drawings/K01_P007_D3_EXECUTION_CONTRACT_CURRENT.json"
OUT = ROOT / "reports/drawing/current/K01-P-007_D3_REPAIR_V18_CURRENT.json"
RAW = ROOT / "reports/cad/d3_repair_v18_current/K01_P007_D3_REPAIR_V18_RAW_CURRENT.txt"

EXPECTED_BLOCKERS = {
    "D3-001_C01_DATUM_IDENTITY_FROM_CONTROLLED_COMPOSITE_AUTHORITY",
    "D3-004_ANNOTATION_VIEW_ROLE_C01",
    "D3-005_ANNOTATION_VIEW_ROLE_C02",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def authority_member(pd: dict) -> dict:
    c01 = next(
        (x for x in pd.get("characteristics", [])
         if isinstance(x, dict) and x.get("id") == "C01"),
        {},
    )
    binding = c01.get("solidworks_binding") or pd.get("datum_A") or {}
    entities = binding.get("entities") or []
    if binding.get("binding_type") != "COMPOSITE_COPLANAR_FACE_SET":
        raise RuntimeError("C01 authority is not COMPOSITE_COPLANAR_FACE_SET")
    if len(entities) != 2:
        raise RuntimeError(f"C01 authority expected 2 member faces, got {len(entities)}")

    candidates = []
    for index, e in enumerate(entities):
        if not isinstance(e, dict) or e.get("surface_type") != "plane":
            continue
        if e.get("plane_x_mm") is None or e.get("area_m2") is None:
            continue
        candidates.append((index, e))
    if len(candidates) != 2:
        raise RuntimeError("C01 authority does not expose two complete plane signatures")

    # Contract v17 explicitly allows the native datum symbol to attach to any one
    # member of the controlled composite datum feature.  Choose authority order
    # deterministically; this is representation selection, not geometry inference.
    index, entity = candidates[0]
    return {
        "authority_index": index,
        "plane_x_mm": float(entity["plane_x_mm"]),
        "area_m2": float(entity["area_m2"]),
        "raw": entity,
    }


def require_current_gate() -> tuple[dict, dict, dict, Path, Path]:
    if sw_running():
        raise RuntimeError("Close SolidWorks before V18 repair/preflight.")

    for p in (CS, D3, COH, PD, EXEC):
        if not p.exists():
            raise RuntimeError(f"missing required input: {p.relative_to(ROOT)}")

    d3 = load(D3)
    coh = load(COH)
    pd = load(PD)
    contract = load(EXEC)

    if coh.get("status") != "PASS_ASSURANCE_COHERENCE":
        raise RuntimeError("assurance coherence is not PASS; do not mutate CAD")

    blockers = set(d3.get("blocking_checks") or [])
    if d3.get("status") != "HOLD_D3_EXEMPLAR":
        raise RuntimeError(f"expected HOLD_D3_EXEMPLAR, got {d3.get('status')}")
    if blockers != EXPECTED_BLOCKERS:
        raise RuntimeError(
            "V18 scope mismatch; expected exactly current three D3 blockers, got: "
            + ",".join(sorted(blockers))
        )

    av = (contract.get("annotation_view_roles") or {}).get("AV_J2_LONGITUDINAL") or {}
    allowed = av.get("allowed_standard_view_names") or []
    if "*Front" not in allowed:
        raise RuntimeError("V18 requires *Front to remain an allowed AV_J2_LONGITUDINAL mapping")

    c01 = (contract.get("C01.DATUM_A") or {})
    if c01.get("sw2018_symbol_attachment_semantics") != "SINGLE_MEMBER_OF_CONTROLLED_COMPOSITE_DATUM_FEATURE":
        raise RuntimeError("V18 C01 native-symbol representation is not authorized by execution contract")

    _, part, drawing = workspace_paths()
    part = Path(part)
    drawing = Path(drawing)
    if not part.exists():
        raise RuntimeError(f"workspace part missing: {part}")
    if not drawing.exists():
        raise RuntimeError(f"workspace drawing missing: {drawing}")

    return d3, pd, contract, part, drawing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("preflight", "apply"), required=True)
    ns = ap.parse_args()

    status = "HOLD_D3_REPAIR_V18"
    backup = None

    try:
        d3, pd, contract, part, drawing = require_current_gate()
        member = authority_member(pd)

        exe = compile_helper(CS, "K01P007D3RepairV18.exe", RAW.parent / "build")
        RAW.parent.mkdir(parents=True, exist_ok=True)

        before_sha = sha256(part)
        args = [
            str(exe),
            "--mode", ns.mode,
            "--part", str(part),
            "--report", str(RAW),
            "--plane-x-mm", format(member["plane_x_mm"], ".17g"),
            "--area-m2", format(member["area_m2"], ".17g"),
            "--view", "*Front",
        ]

        if ns.mode == "apply":
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = ROOT / "reports/cad/d3_repair_v18_history" / stamp
            backup_dir.mkdir(parents=True, exist_ok=False)
            backup = backup_dir / part.name
            shutil.copy2(part, backup)
            (backup_dir / "README.txt").write_text(
                "Controlled V18 pre-mutation backup of SAME V12 exemplar P007.\n"
                f"source={part}\nsha256={before_sha}\n",
                encoding="utf-8",
            )

        cp = run(args, timeout=600)
        if cp.stdout:
            print(cp.stdout, end="")
        if cp.stderr:
            print(cp.stderr, end="")

        if not RAW.exists():
            raise RuntimeError("V18 raw report missing")
        kv = parse_kv(RAW)

        helper_status = kv.get("STATUS", "")
        preflight_pass = helper_status == "PASS_D3_REPAIR_V18_PREFLIGHT"
        apply_pass = helper_status == "PASS_D3_REPAIR_V18_APPLY"

        if ns.mode == "preflight" and not preflight_pass:
            raise RuntimeError(f"V18 helper preflight did not pass: {helper_status}")
        if ns.mode == "apply" and not apply_pass:
            # A failed mutation attempt must not leave the exemplar in an unknown state.
            if backup and backup.exists():
                shutil.copy2(backup, part)
            raise RuntimeError(
                f"V18 helper apply did not pass: {helper_status}; "
                + ("workspace part restored from backup" if backup else "no backup available")
            )

        after_sha = sha256(part)
        if ns.mode == "preflight" and after_sha != before_sha:
            raise RuntimeError("read-only V18 preflight changed workspace part SHA")

        payload = {
            "schema": "k01.p007.d3_repair.v18",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "mode": ns.mode,
            "status": (
                "PASS_D3_REPAIR_V18_PREFLIGHT"
                if ns.mode == "preflight"
                else "PASS_D3_REPAIR_V18_APPLY__D3_REVERIFY_REQUIRED"
            ),
            "scope": {
                "same_v12_exemplar": True,
                "workspace_part": str(part),
                "workspace_drawing": str(drawing),
                "allowed_repairs": sorted(EXPECTED_BLOCKERS),
                "drawing_mutated": False,
                "canonical_cad_mutated": False,
            },
            "authority": {
                "c01_binding_type": "COMPOSITE_COPLANAR_FACE_SET",
                "selected_native_symbol_member": member,
                "annotation_view_role": "AV_J2_LONGITUDINAL",
                "target_standard_annotation_view": "*Front",
                "selection_rule": (
                    "First member in controlled authority order; contract permits any one "
                    "controlled member for native SW datum-symbol attachment."
                ),
            },
            "sha": {
                "workspace_part_before": before_sha,
                "workspace_part_after": after_sha,
                "changed_by_apply": after_sha != before_sha,
            },
            "backup": str(backup) if backup else None,
            "raw_report": str(RAW.relative_to(ROOT)),
            "next": (
                "If PASS, run tools/commands/workflows_20260916/RUN_K01_D3_REPAIR_P007_V18_APPLY.cmd."
                if ns.mode == "preflight"
                else "Run contract-driven D3 V17 immediately; do not run D7 unless D3 exemplar PASS."
            ),
        }
        dump(OUT, payload)
        print("STATUS:", payload["status"])
        print("PART:", part)
        print("TARGET C01 MEMBER:", "plane_x_mm=", member["plane_x_mm"], "area_m2=", member["area_m2"])
        print("TARGET ANNOTATION VIEW: *Front")
        if backup:
            print("BACKUP:", backup)
        print("REPORT:", OUT)
        return 0

    except Exception as e:
        dump(
            OUT,
            {
                "schema": "k01.p007.d3_repair.v18",
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "mode": ns.mode,
                "status": status,
                "error": repr(e),
                "backup": str(backup) if backup else None,
            },
        )
        print("STATUS:", status)
        print("ERROR:", repr(e))
        if backup:
            print("BACKUP:", backup)
        print("REPORT:", OUT)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
