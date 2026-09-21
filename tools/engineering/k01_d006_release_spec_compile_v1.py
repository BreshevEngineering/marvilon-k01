from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
import sys

REPO_DEFAULT = Path(r"D:\BreshevEngineering\marvilon-k01")
LOCAL_DEFAULT = Path(r"D:\BreshevEngineering\K01_local")

PD = Path("control/product_definition/K01_P007_PRODUCT_DEFINITION_RELEASE_CURRENT.json")
SPEC_CANDIDATES = [
    Path("control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_v1.json"),
    Path("control/drawings/K01-D-006_RELEASE_DEFINITION.json"),
]
OUT = Path("control/drawings/spec/K01-D-006_P007_DRAWING_SPEC_RELEASE_CANDIDATE.json")


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(REPO_DEFAULT))
    ap.add_argument("--local-root", default=str(LOCAL_DEFAULT))
    args = ap.parse_args()
    repo = Path(args.repo_root)
    local = Path(args.local_root)

    pdp = repo / PD
    if not pdp.exists():
        raise SystemExit("HOLD: P007 release-ready Product Definition record is missing.")
    pd = read_json(pdp)
    if pd.get("product_definition_ready") is not True or pd.get("status") != "READY_FOR_D006_RELEASE_PIPELINE":
        raise SystemExit("HOLD: P007 Product Definition is not READY.")

    source = None
    for rel in SPEC_CANDIDATES:
        if (repo / rel).exists():
            source = rel
            break
    if source is None:
        raise SystemExit("HOLD: no existing D006 controlled spec source found. Do not invent a new drawing spec from scratch.")

    src = read_json(repo / source)

    # Preserve existing spec as the engineering source; add a release overlay.
    rc = {
        "schema": "k01.drawing_spec.release_candidate.v1",
        "generated_utc": now(),
        "drawing_id": "K01-D-006",
        "part": "K01-P-007",
        "status": "RELEASE_CANDIDATE_SPEC_READY__DRAWING_QA_PENDING",
        "source_spec": str(source).replace("\\", "/"),
        "source_spec_snapshot": src,
        "product_definition_authority": str(PD).replace("\\", "/"),
        "release_basis": [
            "EDR-025", "EDR-027", "EDR-028", "EDR-029", "EDR-030",
            "EDR-032", "EDR-033", "EDR-035", "EDR-036", "EDR-037"
        ],
        "mandatory_release_additions": {
            "SURFACE_J2": {
                "surface": "J2 Datum-A seal-contact face",
                "requirement": "Ra <= 0.8 µm",
                "inspection": "profilometer",
                "authority": "EDR-037"
            },
            "C12": {
                "requirement": "q_He <= 1.0e-5 mbar·L/s at |Δp| = 0.20 bar",
                "temperature": "20 ±5 °C",
                "method": "calibrated helium tracer-gas test",
                "authority": "EDR-035"
            },
            "fastener_note": {
                "text": "J2: 3x ISO 4762 M2.5x6 A4-70; assembly/preload/locking per EDR-036.",
                "authority": "EDR-036"
            },
            "inspection_reference": "control/inspection/K01_P007_INSPECTION_PLAN_CURRENT.json",
            "material": "EN 1.4404 / AISI 316L"
        },
        "presentation_policy": {
            "do_not_regenerate_from_scratch": True,
            "use_existing_linked_current_drawing": True,
            "semantic_QA_required": True,
            "D8_visual_QA_required": True,
            "Drawing_Control_publication_required": True
        },
        "release_boundary": "This file is the final controlled Drawing Spec input. It is not itself a released SLDDRW/PDF."
    }

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = local / "backups" / f"D006_SPEC_{stamp}"
    if (repo / OUT).exists():
        (bdir / OUT).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / OUT, bdir / OUT)

    write_json(repo / OUT, rc)
    print("PASS:", repo / OUT)
    print("NEXT: semantic/native QA on existing linked D006 -> controlled visual D8 -> Drawing Control release-candidate publication.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
