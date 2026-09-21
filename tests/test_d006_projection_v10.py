import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "tools/medtas").resolve()))
MOD_PATH = ROOT / "tools/medtas/d006_projection_compiler_v10.py"
spec = importlib.util.spec_from_file_location("d006v10", MOD_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)



def ensure_v11_outputs():
    p = ROOT / "tools/medtas/product_definition_guard_v11.py"
    sp = importlib.util.spec_from_file_location("pd_v11_for_projection", p)
    m = importlib.util.module_from_spec(sp)
    assert sp.loader is not None
    sp.loader.exec_module(m)
    assert m.main() == 0


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def test_projection_plan_covers_only_safe_drawing_slice_ids_and_avoids_stale_specs():
    ensure_v11_outputs()
    drawing = load("reports/product_definition/current/K01_P007_PD_SLICE_DRAWING.json")
    profile = load("control/drawings/K01_D006_PROJECTION_PROFILE_v10.json")
    plan = mod.build_projection_plan(drawing, profile)
    safe = set(drawing["safe_projection_ids"])
    projected = {x["characteristic_id"] for x in plan["projection_evidence"]}
    assert projected == safe
    assert plan["source_projection_fingerprint"] == drawing["slice_sha256"]
    all_text = "\n".join(x["text"] for x in plan["notes"])
    for stale in ("FLATNESS 0.03", "PERP Ø0.03", "POS Ø0.15", "±0.05"):
        assert stale not in all_text
    assert "Ø14.10 H7" in all_text
    assert "Ø33.00 NOM" in all_text
    assert "OAL 35.00 NOM" in all_text


def test_projection_is_drawing_slice_driven_not_hardcoded_nominal():
    ensure_v11_outputs()
    drawing = load("reports/product_definition/current/K01_P007_PD_SLICE_DRAWING.json")
    profile = load("control/drawings/K01_D006_PROJECTION_PROFILE_v10.json")
    altered = deepcopy(drawing)
    for c in altered["characteristics"]:
        if c["id"] == "C06":
            c["nominal_or_requirement"]["overall_length_mm"] = 35.25
    plan = mod.build_projection_plan(altered, profile)
    c06 = next(x for x in plan["notes"] if x["characteristic_id"] == "C06")
    assert "35.25" in c06["text"]


def test_graph_binds_v10_projection_to_narrow_drawing_slice():
    ensure_v11_outputs()
    graph = load("control/medtas/v1/graph/K01_engineering_build_graph_v2_2.json")
    node = next(x for x in graph["nodes"] if x["node_id"] == "K01.DRAWING.D006.PROJECTION")
    assert node["producer"]["implementation"] == "tools/medtas/d006_projection_compiler_v10.py"
    inputs = {x["node_id"]: x for x in node["contract"]["inputs"]}
    assert inputs["K01.PD.P007.DRAWING_SLICE"]["required"] is True
    assert inputs["K01.PD.P007.DRAWING_SLICE"]["consume"] == "both"
    assert "K01.PD.P007.COMPILED" not in inputs


def test_layout_profile_contains_no_engineering_characteristic_values():
    profile = load("control/drawings/K01_D006_PROJECTION_PROFILE_v10.json")
    text = json.dumps(profile, ensure_ascii=False).lower()
    for forbidden in ("diameter_mm", "tolerance", "h7/g6", "aisi 316l", "35.00", "14.10", "33.00"):
        assert forbidden not in text
