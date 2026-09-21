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


def test_family_rules_are_semantic_neutral_and_section_first_for_p007_family():
    r = load_json("control/drawings/K01_DRAWING_FAMILY_RULES_CURRENT.json")
    fam = r["families"]["ROTATIONAL_FLANGED_HOLLOW"]
    assert "never creates engineering requirements" in r["purpose"]
    roles = [x["role"] for x in fam["view_rules"]]
    assert roles[:2] == ["AXIAL_FULL_SECTION", "FLANGE_END"]
    assert any(x["role"] == "AXIAL_EXTERNAL" and x["disposition"] == "OMIT_AS_REDUNDANT" for x in fam["suppression_rules"])
    order = [x["class"] for x in r["authoring_order"]]
    assert order[:4] == ["DATUM_DRF", "SIZE_FIT", "LOCATION_PATTERN", "GDT"]


def test_p007_family_binding_captures_manual_exemplar_lessons():
    b = load_json("control/drawings/K01_P007_DRAWING_FAMILY_BINDING_CURRENT.json")
    assert b["family"] == "ROTATIONAL_FLANGED_HOLLOW"
    assert b["view_plan"]["primary"]["role"] == "AXIAL_FULL_SECTION"
    assert b["view_plan"]["secondary"]["role"] == "FLANGE_END"
    assert b["view_plan"]["auxiliary"]["role"] == "ISOMETRIC"
    assert b["claim_role_overrides"]["C02.DIAMETER_FIT"] == "LOCATING_INTERNAL_DIAMETER"
    assert b["claim_role_overrides"]["C04.HOLE_PATTERN"] == "HOLE_PATTERN"
    assert b["current_exemplar_evidence"]["environment"]["length_unit"] == "MMGS"


def test_family_plan_routes_all_current_claims_without_inventing_semantics():
    pd = load_module("tools/medtas/product_definition_guard_v11.py", "pd_v13_family")
    assert pd.main() == 0
    fp = load_module("tools/medtas/drawing_family_plan_v13.py", "family_v13")
    assert fp.main() == 0
    plan = load_json("reports/drawing/current/K01-D-006_FAMILY_PLAN_CURRENT.json")
    assert plan["status"] == "PASS_DRAWING_FAMILY_PLAN_V13"
    assert plan["claim_route_count"] == 16
    assert plan["issues"] == []
    by = {x["claim_id"]: x for x in plan["claim_routes"]}
    assert by["C01.DATUM_A"]["authoring_order_class"] == "DATUM_DRF"
    assert by["C02.DIAMETER_FIT"]["family_view_role"] == "AXIAL_FULL_SECTION"
    assert by["C04.HOLE_PATTERN"]["family_view_role"] == "FLANGE_END"
    assert by["C09.MATERIAL"]["family_view_role"] == "TITLE_BLOCK"
    assert by["C11.COAXIALITY"]["authoring_order_class"] == "GDT"


def test_d1_consumes_family_plan_and_authoring_order():
    pd = load_module("tools/medtas/product_definition_guard_v11.py", "pd_v13_d1")
    assert pd.main() == 0
    fp = load_module("tools/medtas/drawing_family_plan_v13.py", "family_v13_d1")
    assert fp.main() == 0
    d1 = load_module("tools/medtas/drawing_d1_authoring_plan_v11.py", "d1_v13_family")
    assert d1.main() == 0
    plan = load_json("reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json")
    assert plan["drawing_family"] == "ROTATIONAL_FLANGED_HOLLOW"
    assert plan["drawing_family_plan_sha256"]
    tasks = plan["tasks"]
    assert tasks == sorted(tasks, key=lambda x: (int(x.get("authoring_order", 999)), str(x.get("family_view_role") or ""), str(x.get("claim_id") or "")))
    assert tasks[0]["authoring_order_class"] == "DATUM_DRF"


def test_graph_v23_family_plan_is_preserved_and_current_authority_is_v24_or_newer():
    g = load_json("control/medtas/v1/graph/K01_engineering_build_graph_v2_3.json")
    nodes = {x["node_id"]: x for x in g["nodes"]}
    for nid in ("K01.DRAWING.FAMILY.RULES", "K01.DRAWING.P007.FAMILY.BINDING", "K01.DRAWING.D006.FAMILY.PLAN", "K01.DRAWING.D006.D1.AUTHORING_PLAN"):
        assert nid in nodes
    d1_inputs = {x["node_id"] for x in nodes["K01.DRAWING.D006.D1.AUTHORING_PLAN"]["contract"]["inputs"]}
    assert "K01.DRAWING.D006.FAMILY.PLAN" in d1_inputs
    a = load_json("control/project/K01_AUTHORITY_MAP_CURRENT.json")
    assert a["control_families"]["engineering_build_graph"]["authority"].endswith("K01_engineering_build_graph_v2_5.json")


def test_d7_environment_checks_are_controlled():
    p = load_json("control/drawings/K01_DRAWING_PIPELINE_POLICY_CURRENT.json")
    d7 = {x["code"]: x for x in p["d7_checks"]}
    for code in ("DQA-017", "DQA-018", "DQA-019", "DQA-020"):
        assert d7[code]["level"] == "BLOCK"
