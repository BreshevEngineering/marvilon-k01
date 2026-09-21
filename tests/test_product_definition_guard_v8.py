from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/medtas/product_definition_guard_v8.py"


def load_module():
    spec = importlib.util.spec_from_file_location("k01_product_definition_guard_v8", MODULE)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_open_tolerance_conflict_is_fail_closed():
    mod = load_module()
    decision = {"variation_semantics": {"diameter_tolerance": "OPEN", "thickness_tolerance": "OPEN"}}
    reasons = mod.stale_legacy_reason("C05", "Ø33.00 ±0.05 × 3.00 ±0.05", decision)
    assert reasons


def test_compiled_product_definition_readiness():
    mod = load_module()
    rc = mod.main()
    assert rc == 0
    report = json.loads((ROOT / "reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json").read_text(encoding="utf-8"))
    compiled = json.loads((ROOT / report["compiled_definition"]).read_text(encoding="utf-8"))

    assert report["gates"]["DRAWING_CANDIDATE_READY"] == "PASS"
    assert report["gates"]["DRAWING_RELEASE_READY"] == "HOLD"
    assert report["stale_legacy_spec_count"] >= 5

    by_id = {x["id"]: x for x in compiled["characteristics"]}
    assert by_id["C02"]["variation_semantics"]["diameter_fit"] == "H7"
    assert by_id["C05"]["variation_semantics"]["diameter_tolerance"] == "OPEN"
    assert by_id["C05"]["legacy_spec_disposition"] == "STALE_IGNORED"
    assert any(x["id"] == "PDG-SURFACE-TEXTURE" for x in compiled["coverage_gaps"])
    assert compiled["drawing_compiler_contract"]["must_not_read_as_authority"]
