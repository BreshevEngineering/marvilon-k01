from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "tools/medtas").resolve()))


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def load_module(rel, name):
    p = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_pipeline_has_two_lanes_and_release_native_provenance_rules():
    p = load_json("control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json")
    assert p["lanes"]["DESIGN_REVIEW_BASE"]["release_eligible"] is False
    assert p["lanes"]["RELEASE_NATIVE_D1_D9"]["release_eligible"] is True
    assert "InsertModelAnnotations3" in p["solidworks_2018_transport"]["release_native_rule"]
    d7 = {x["code"]: x for x in p["d7_checks"]}
    assert "provenance" in d7["DQA-010"]["rule"].lower()
    assert "general_tolerance_policy_ref" in d7["DQA-005"]["rule"]


def test_characteristic_context_is_claim_level_and_c05_spans_multiple_views():
    ctx = load_json("control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json")
    c05 = ctx["characteristics"]["C05"]["drawing_authoring"]["targets"]
    assert {x["claim_id"] for x in c05} == {"C05.FLANGE_OD", "C05.FLANGE_THICKNESS"}
    assert len({x["annotation_view_role"] for x in c05}) == 2
    assert all("claim_paths" in x and x["claim_paths"] for x in c05)


def test_product_definition_drawing_slice_carries_authoring_targets():
    mod = load_module("tools/medtas/product_definition_guard_v11.py", "pd_v11_draw")
    assert mod.main() == 0
    drawing = load_json("reports/product_definition/current/K01_P007_PD_SLICE_DRAWING.json")
    by_id = {x["id"]: x for x in drawing["characteristics"]}
    assert "drawing_authoring" in by_id["C02"]
    assert any(x["claim_id"] == "C02.DIAMETER_FIT" for x in by_id["C02"]["drawing_authoring"]["targets"])


def test_d1_plan_is_generated_claim_level_and_does_not_mutate_cad():
    pd = load_module("tools/medtas/product_definition_guard_v11.py", "pd_v11_for_d1")
    assert pd.main() == 0
    fp = load_module("tools/medtas/drawing_family_plan_v13.py", "family_v13_for_old_d1")
    assert fp.main() == 0
    d1 = load_module("tools/medtas/drawing_d1_authoring_plan_v11.py", "d1_v11")
    assert d1.main() == 0
    plan = load_json("reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json")
    assert plan["status"] == "PASS_D1_AUTHORING_PLAN"
    assert plan["d2_release_native_mutation_gate"] == "PASS_D2_ROUTE_INDEPENDENT_SCOPE_AUTHORIZABLE"
    assert not any(x.get("blocks_stage") == "D2" for x in plan["release_native_blockers"])
    assert any(x.get("blocks_stage") == "RELEASE" for x in plan["release_native_blockers"])
    assert any(x.get("blocks_stage") == "D9" for x in plan["release_native_blockers"])
    assert set(plan["d2_authorizable_claim_ids"]) == {"C01.DATUM_A", "C02.DIAMETER_FIT", "C09.MATERIAL"}
    assert plan["d2_mutation_blockers"] == []
    ids = [x["claim_id"] for x in plan["tasks"]]
    assert len(ids) == len(set(ids))
    assert "C02.DIAMETER_FIT" in ids and "C05.FLANGE_OD" in ids
    c02 = next(x for x in plan["tasks"] if x["claim_id"] == "C02.DIAMETER_FIT")
    assert c02["binding_anchor"]["kind"] == "EXISTING_PMI_IDENTITY"
    assert c02["annotation_view_role"] == "AV_J2_LONGITUDINAL"


def test_graph_v23_contains_d1_and_authority_map_points_to_it():
    g = load_json("control/medtas/v1/graph/K01_engineering_build_graph_v2_3.json")
    nodes = {x["node_id"]: x for x in g["nodes"]}
    assert "K01.DRAWING.PIPELINE.POLICY" in nodes
    assert "K01.DRAWING.D006.D1.AUTHORING_PLAN" in nodes
    ins = {x["node_id"] for x in nodes["K01.DRAWING.D006.D1.AUTHORING_PLAN"]["contract"]["inputs"]}
    assert "K01.PD.P007.DRAWING_SLICE" in ins
    assert "K01.PARTS.REGISTRY" in ins
    a = load_json("control/project/K01_AUTHORITY_MAP_CURRENT.json")
    assert a["control_families"]["engineering_build_graph"]["authority"].endswith("K01_engineering_build_graph_v2_3.json")


def test_d8_d9_no_cycle_and_exports_conditional():
    p = load_json("control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json")
    by = {x["id"]: x for x in p["nodes"]}
    assert "temporary preview" in by["D8"]["input"].lower()
    assert "D7 PASS + D8 PASS" in by["D9"]["input"]
    delivery = load_json("control/drawings/K01_DRAWING_DELIVERY_CAPABILITY_CURRENT.json")
    assert delivery["manufacturer_or_supplier"]["step_ap242_pmi_acceptance"] == "OPEN"
    assert "CONDITIONAL" in delivery["local_capability"]["dxf_export"]
