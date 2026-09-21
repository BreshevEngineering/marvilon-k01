from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

STEP_REL = Path("reports/control/K01_ENGINEERING_STEP_GATE_CURRENT.json")
PREFLIGHT_REL = Path("reports/control/K01_BASELINE_02C_PROMOTION_PREFLIGHT_CURRENT.json")
TOOL_REVIEW_REL = Path("reports/control/K01_PROMOTION_TOOLCHAIN_REVIEW_CURRENT.json")
ASSET_REL = Path("reports/control/K01_ASSET_INDEX_CURRENT.json")
PARTS_REL = Path("control/product/parts.json")
TX_REL = Path("control/project/K01_BASELINE_02C_PROMOTION_TRANSACTION_CURRENT.json")
OUT_REL = Path("reports/control/K01_BASELINE_02C_PROMOTION_DRYRUN_CURRENT.json")

CHECKPOINT = "K01-CP-20260910-BASELINE-02C-DATUM-C-VERIFIED"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def add(rows, name, ok, actual=None, expected=None):
    rows.append({
        "check": name,
        "status": "PASS" if ok else "FAIL",
        "actual": actual,
        "expected": expected,
    })
    return ok

def sw_running():
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq SLDWORKS.exe"],
            text=True,
            errors="ignore",
        )
        return "sldworks.exe" in out.lower()
    except Exception:
        return None

def stable_from_index(asset, identity):
    row = (asset.get("stable_by_identity") or {}).get(identity)
    return Path(row["path"]) if isinstance(row, dict) and row.get("path") else None

def resolve_new_p017_target(p017_candidate: Path, stable_parts_dir: Path):
    # Deterministic stable identity derivation from the already accepted candidate identity.
    # Example:
    # K01-P-017_Datum_C_Relieved_Locator_GATE04B_V7_20260909_231939.SLDPRT
    # -> K01-P-017_Datum_C_Relieved_Locator.SLDPRT
    stem = p017_candidate.stem
    base = re.sub(r"_GATE.*$", "", stem, flags=re.IGNORECASE)
    if base == stem or not base.startswith("K01-P-017_"):
        raise RuntimeError(f"Cannot derive controlled P017 stable stem from candidate: {p017_candidate.name}")
    return stable_parts_dir / f"{base}{p017_candidate.suffix.upper()}"

def main():
    ap = argparse.ArgumentParser(
        description="K01 Baseline-02C READ-ONLY stable-promotion dry-run manifest"
    )
    ap.add_argument("--repo-root", required=True)
    args = ap.parse_args()
    root = Path(args.repo_root).resolve()

    rows = []
    step = load(root / STEP_REL)
    pre = load(root / PREFLIGHT_REL)
    review = load(root / TOOL_REVIEW_REL)
    asset = load(root / ASSET_REL)
    parts = load(root / PARTS_REL)
    tx = load(root / TX_REL)

    add(
        rows, "step gate permits dry-run only",
        str(step.get("status", "")).startswith("PASS_TO_PROMOTION_DRYRUN")
        and step.get("mutation_authorized") is False,
        {"status": step.get("status"), "mutation_authorized": step.get("mutation_authorized")},
        "PASS_TO_PROMOTION_DRYRUN* and mutation_authorized=false",
    )
    add(
        rows, "promotion preflight",
        str(pre.get("status", "")).startswith("PASS_READY"),
        pre.get("status"), "PASS_READY*"
    )
    add(
        rows, "toolchain review",
        str(review.get("status", "")).startswith("PASS_PRECEDENT_REVIEWED"),
        review.get("status"), "PASS_PRECEDENT_REVIEWED*"
    )
    add(
        rows, "transaction remains non-mutating",
        tx.get("mutation_allowed") is False,
        tx.get("mutation_allowed"), False
    )
    add(
        rows, "checkpoint",
        tx.get("checkpoint") == CHECKPOINT,
        tx.get("checkpoint"), CHECKPOINT
    )

    frozen = pre.get("frozen_inputs") or {}
    required_frozen = [
        "canonical_A001", "verification_A001",
        "P003_candidate", "P016_candidate", "P017_candidate"
    ]
    for key in required_frozen:
        add(rows, f"frozen input {key}", isinstance(frozen.get(key), dict), bool(frozen.get(key)), True)

    p003_cand = Path(frozen["P003_candidate"]["path"])
    p016_cand = Path(frozen["P016_candidate"]["path"])
    p017_cand = Path(frozen["P017_candidate"]["path"])
    a001_canon = Path(frozen["canonical_A001"]["path"])
    a001_verify = Path(frozen["verification_A001"]["path"])

    p003_stable = stable_from_index(asset, "K01-P-003")
    p016_stable = stable_from_index(asset, "K01-P-016")
    p017_indexed = stable_from_index(asset, "K01-P-017")

    add(rows, "P003 stable identity resolves", p003_stable is not None, str(p003_stable) if p003_stable else None, "stable_by_identity")
    add(rows, "P016 stable identity resolves", p016_stable is not None, str(p016_stable) if p016_stable else None, "stable_by_identity")
    add(rows, "P017 has no pre-existing stable identity", p017_indexed is None, str(p017_indexed) if p017_indexed else None, None)

    if p003_stable is None or p016_stable is None:
        raise RuntimeError("Cannot resolve existing stable P003/P016 identities from asset index")

    stable_parts_dir = p003_stable.parent
    add(rows, "P003/P016 share stable parts directory", p016_stable.parent == stable_parts_dir, str(p016_stable.parent), str(stable_parts_dir))

    p017_stable = resolve_new_p017_target(p017_cand, stable_parts_dir)
    add(
        rows, "P017 proposed stable filename",
        p017_stable.name == "K01-P-017_Datum_C_Relieved_Locator.SLDPRT",
        p017_stable.name, "K01-P-017_Datum_C_Relieved_Locator.SLDPRT"
    )

    # Product registry must agree with the identity being materialized.
    p17reg = (parts.get("items") or {}).get("K01-P-017")
    add(rows, "P017 product registry identity", isinstance(p17reg, dict) and p17reg.get("cad_identity_key") == "K01-P-017",
        p17reg.get("cad_identity_key") if isinstance(p17reg, dict) else None, "K01-P-017")
    add(rows, "P017 release remains HOLD", isinstance(p17reg, dict) and p17reg.get("release_state") == "HOLD",
        p17reg.get("release_state") if isinstance(p17reg, dict) else None, "HOLD")
    add(rows, "P017 native material assignment remains OPEN",
        isinstance(p17reg, dict) and "OPEN" in str(p17reg.get("material_status", "")).upper(),
        p17reg.get("material_status") if isinstance(p17reg, dict) else None, "OPEN")

    # Re-prove every frozen binary on the live workstation.
    actual_hashes = {}
    for key, path in [
        ("canonical_A001", a001_canon),
        ("verification_A001", a001_verify),
        ("P003_candidate", p003_cand),
        ("P016_candidate", p016_cand),
        ("P017_candidate", p017_cand),
    ]:
        exists = path.is_file()
        add(rows, f"{key} exists", exists, str(path), True)
        if exists:
            h = sha256(path)
            actual_hashes[key] = h
            expected = str(frozen[key].get("sha256", "")).lower()
            add(rows, f"{key} frozen SHA", bool(expected) and h.lower() == expected, h, expected)

    # Existing stable targets are pre-state authority; P017 must be a genuinely new stable file.
    prestate = {}
    for key, path in [("P003", p003_stable), ("P016", p016_stable), ("A001", a001_canon)]:
        exists = path.is_file()
        add(rows, f"stable {key} exists", exists, str(path), True)
        if exists:
            prestate[key] = {"path": str(path), "sha256": sha256(path), "size": path.stat().st_size}

    add(rows, "stable P017 target absent", not p017_stable.exists(), str(p017_stable), "must not exist before first materialization")

    # Exact source candidates must not alias stable paths.
    for key, cand, stable in [
        ("P003", p003_cand, p003_stable),
        ("P016", p016_cand, p016_stable),
        ("P017", p017_cand, p017_stable),
    ]:
        add(rows, f"{key} candidate != stable path",
            os.path.normcase(os.path.normpath(str(cand))) != os.path.normcase(os.path.normpath(str(stable))),
            str(cand), f"not {stable}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cad_root = a001_canon.parent.parent
    backup_root = cad_root / "archive" / "pre_baseline_02c_promotion" / stamp
    staging_root = cad_root / "promotion_staging" / "baseline_02c" / stamp

    plan = {
        "stable_targets": {
            "P003": str(p003_stable),
            "P016": str(p016_stable),
            "P017": str(p017_stable),
            "A001": str(a001_canon),
        },
        "candidate_sources": {
            "P003": str(p003_cand),
            "P016": str(p016_cand),
            "P017": str(p017_cand),
            "verification_A001": str(a001_verify),
        },
        "backup_root_proposed": str(backup_root),
        "staging_root_proposed": str(staging_root),
        "rollback_map": {
            "restore": [str(p003_stable), str(p016_stable), str(a001_canon)],
            "delete_if_created": [str(p017_stable)],
            "source_of_restore": str(backup_root),
        },
        "apply_sequence_required": [
            "A0: require a fresh prewrite/step-gate PASS and recheck all frozen SHA values.",
            "A1: close SOLIDWORKS; create immutable backup of canonical A001/P003/P016 plus manifest.",
            "A2: materialize exact candidate binaries to stable P003/P016 and NEW stable P017.",
            "A3: build a STAGING A001 from the verified Datum-C assembly; replace candidate references with stable P003/P016/P017 using SOLIDWORKS reference-safe API. Do not overwrite canonical A001 yet.",
            "A4: staging QA: 14 modeled occurrences; one stable P003/P016/P017 each; no candidate-path references; zero active mate errors; Datum-C center/orientation/depth/protrusion preserved; moving group PASS; unexpected IN/MID/OUT interference=0.",
            "A5: only after staging QA PASS, close SOLIDWORKS and atomically replace canonical A001 from the verified staging assembly.",
            "A6: reopen canonical A001 and run post-promotion semantic + assembly QA. On any failure restore P003/P016/A001 from backup and delete newly created P017 stable target.",
            "A7: generate new canonical semantic snapshot and recompute dependency/freshness state.",
            "A8: rebuild EBOM/MBOM from fresh canonical occurrences; prove 14 modeled occurrences and K01-P-017 qty=1.",
            "A9: create CP-P checkpoint, Git checkpoint and fresh AI handoff.",
        ],
        "explicitly_forbidden": [
            "copy verification A001 directly over canonical A001",
            "leave canonical A001 referencing any \\\\candidates\\\\ path",
            "run superseded radial-slot closer",
            "use final/R01 PackAndGo promoter for this Baseline-02C transition",
            "hand-edit generated EBOM/MBOM",
            "convert P017 material OPEN or any release-only OPEN requirement to PASS",
        ],
        "product_data_impact": {
            "EBOM": "+ K01-P-017 x1; expected modeled occurrence count 13 -> 14",
            "MBOM": "refresh required after fresh canonical semantic export",
            "P017_material": "AISI 316L / EN 1.4404 baseline; native material-card assignment remains OPEN",
        },
        "dimxpert_drawing_inspection_impact": {
            "P003_D003": "STALE/REFRESH after promoted Datum-C hole; functional characteristic must bind through native feature -> DimXpert/PMI -> drawing -> inspection.",
            "A001_D012": "STALE/REFRESH because product structure changes 13 -> 14.",
            "P017": "new manufactured product item; detail-drawing identity/release definition remains OPEN, do not invent drawing number in this transition.",
            "P007_D006": "not invalidated solely by Datum-C; remains first professional DimXpert-driven drawing exemplar after applicable P1-P3 inputs.",
        },
        "analysis_impact": {
            "FEMM_method": "remains PASS_METHOD_ONLY unless its declared method dependencies change",
            "physics_results": "freshness must be recomputed from graph after canonical promotion; do not blanket-invalidate or preserve manually",
        },
        "technical_filter_rule": "Promotion is an engineering-baseline authority transition only; it does not grant structural/thermal/magnetic/manufacturing/release PASS.",
    }

    ok = all(r["status"] == "PASS" for r in rows)
    report = {
        "schema": "k01.baseline_02c.promotion_dryrun.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_DRYRUN_MANIFEST_READY_FOR_APPLY_PROMOTER_IMPLEMENTATION_REVIEW" if ok else "HOLD_DRYRUN",
        "checkpoint": CHECKPOINT,
        "native_CAD_mutated": False,
        "mutation_authorized": False,
        "solidworks_running_observation": sw_running(),
        "checks": rows,
        "frozen_actual_sha256": actual_hashes,
        "prestate_stable": prestate,
        "stable_identity_resolution": {
            "P003": "asset_index.stable_by_identity",
            "P016": "asset_index.stable_by_identity",
            "P017": "derived deterministically from accepted candidate identity + existing stable parts directory; target must be absent before promotion",
        },
        "plan": plan,
        "next": (
            "Implement/adapt the APPLY promoter from the reviewed K01_PROMOTE_P003_P007 precedent "
            "against this exact manifest. APPLY remains blocked until its rollback, staging A001, "
            "reference-rewrite and post-promotion QA paths are code-reviewed and dry-tested."
        ),
    }

    out = root / OUT_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("STATUS:", report["status"])
    print("REPORT:", out)
    print("P003:", p003_cand, "->", p003_stable)
    print("P016:", p016_cand, "->", p016_stable)
    print("P017:", p017_cand, "->", p017_stable)
    print("A001 verification:", a001_verify)
    print("A001 canonical:", a001_canon)
    print("Native CAD mutated: False")
    for r in rows:
        if r["status"] != "PASS":
            print("HOLD:", r["check"], "actual=", r["actual"], "expected=", r["expected"])
    return 0 if ok else 2

if __name__ == "__main__":
    raise SystemExit(main())
