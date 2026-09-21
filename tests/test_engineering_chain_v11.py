from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str((ROOT / "tools/medtas").resolve()))


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def load_module(rel: str, name: str):
    p = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_requirement_allocation_and_equal_300n_inputs_are_explicitly_distinct():
    alloc = load_json("control/requirements/K01_REQUIREMENT_ALLOCATION_REGISTRY_v1.json")
    by_req = {x["requirement_id"]: x for x in alloc["allocations"]}
    assert by_req["REQ-K01-J2-LOC-001"]["allocation_type"] == "SHARED_COMPLEMENTARY"
    assert {x["entity_id"] for x in by_req["REQ-K01-J2-LOC-001"]["targets"]} == {"K01-P-003", "K01-P-007"}

    der = load_json("control/engineering/K01_DERIVED_ENGINEERING_INPUTS_v1.json")
    by_id = {x["id"]: x for x in der["inputs"]}
    normal = by_id["DER-K01-P006-SERVICE-NORMAL-FORCE-001"]
    preload = by_id["DER-K01-J2-BOLT-PRELOAD-SCREEN-001"]
    assert normal["value"] == 300.0
    assert preload["value"] == 300.0
    assert normal["quantity_kind"] != preload["quantity_kind"]
    assert normal["unit"] != preload["unit"]
    assert normal["release_authority"] is False
    assert preload["release_authority"] is False


def test_execution_contract_contains_feedback_split_and_configuration_release():
    c = load_json("control/project/K01_ENGINEERING_EXECUTION_CONTRACT_CURRENT.json")
    stage_ids = {x["id"] for x in c["stages"]}
    required = {
        "S0A_REQUIREMENT_ALLOCATION",
        "S1A_DERIVED_INPUTS",
        "S1B_MANUFACTURING_SUPPLY_STRATEGY",
        "S2_PRODUCT_DEFINITION",
        "S3_CAD_BINDING_MBD",
        "S4A_PHYSICS_ANALYSIS",
        "S4B_VARIATION_CAPABILITY",
        "S4C_COMPILED_PRODUCT_DEFINITION",
        "S5_DRAWING_PROJECTION_QA",
        "S6_INSPECTION_REALIZATION",
        "S7_CONFIGURATION_RELEASE_EFFECTIVITY",
    }
    assert required.issubset(stage_ids)
    assert len(c["feedback_loops"]) >= 6
    assert any(x["from"] == "S4B_VARIATION_CAPABILITY" and x["to"] == "S1_ENGINEERING_DECISION" for x in c["feedback_loops"])


def test_product_characteristic_context_covers_decisions_and_thin_wall_measurement_is_not_silently_defaulted():
    decisions = load_json("control/product_definition/K01_P007_DEFINITION_DECISIONS_CURRENT.json")
    ctx = load_json("control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json")
    decision_ids = {x["id"] for x in decisions["characteristics"]}
    assert decision_ids.issubset(set(ctx["characteristics"]))
    for cid in ("C07", "C08", "C11", "K01-D006-BLIND-END"):
        mc = ctx["characteristics"][cid]["measurement_condition"]
        assert "status" in mc
        # Release must not quietly assume the fixture/temperature/measurement-force condition.
        assert "OPEN" in json.dumps(mc, ensure_ascii=False).upper() or mc["status"].upper() != "CONTROLLED"


def test_binding_invariance_is_separate_from_pmi_persistence():
    p = load_json("control/verification/K01_CAD_BINDING_INVARIANCE_POLICY_v1.json")
    levels = {x["id"]: x for x in p["levels"]}
    assert {"L1_SAVE_REOPEN", "L2_FORCE_REBUILD", "L3_PERTURB_RESTORE"}.issubset(levels)
    assert p["current_p007_status"] != "PASS"
    text = json.dumps(p, ensure_ascii=False).lower()
    assert "forcerebuild3" in text
    assert "runtime face" in text or "face index" in text


def test_domain_slice_graph_separates_drawing_variation_physics_and_inspection():
    graph = load_json("control/medtas/v1/graph/K01_engineering_build_graph_v2_2.json")
    nodes = {x["node_id"]: x for x in graph["nodes"]}
    for nid in (
        "K01.PD.P007.DRAWING_SLICE",
        "K01.PD.P007.VARIATION_SLICE",
        "K01.PD.P007.PHYSICS_SLICE",
        "K01.PD.P007.INSPECTION_SLICE",
        "K01.PD.P007.MANUFACTURING_SLICE",
        "K01.PD.P007.CONFIGURATION_SLICE",
        "K01.DRAWING.D006.D1.AUTHORING_PLAN",
    ):
        assert nid in nodes
    drawing_inputs = {x["node_id"] for x in nodes["K01.DRAWING.D006.PROJECTION"]["contract"]["inputs"]}
    assert "K01.PD.P007.DRAWING_SLICE" in drawing_inputs
    assert "K01.PD.P007.COMPILED" not in drawing_inputs


def test_v11_guards_produce_controlled_chain_with_release_hold_and_domain_fingerprints():
    chain_mod = load_module("tools/medtas/engineering_chain_guard_v11.py", "chain_v11")
    assert chain_mod.main() == 0
    chain = load_json("reports/control/K01_ENGINEERING_CHAIN_READINESS_CURRENT.json")
    assert chain["status"] == "PASS_CHAIN_CONTROLLED__HOLD_RELEASE"
    assert chain["known_300N_identity_check"]["status"] == "PASS"

    pd_mod = load_module("tools/medtas/product_definition_guard_v11.py", "pd_v11")
    assert pd_mod.main() == 0
    readiness = load_json("reports/control/K01_P007_PRODUCT_DEFINITION_READINESS_CURRENT.json")
    compiled = load_json("reports/product_definition/current/K01_P007_PRODUCT_DEFINITION_COMPILED.json")
    drawing = load_json("reports/product_definition/current/K01_P007_PD_SLICE_DRAWING.json")
    assert readiness["gates"]["DRAWING_CANDIDATE_READY"] == "PASS"
    assert readiness["gates"]["DRAWING_RELEASE_READY"] == "HOLD"
    assert compiled["drawing_projection_sha256"] == drawing["slice_sha256"]
    assert drawing["safe_projection_ids"] == compiled["safe_projection_ids"]
    assert compiled["drawing_projection_sha256"] != compiled["variation_sha256"]


def test_medtas_json_projection_supports_context_subdomain_hashing():
    eng = load_module("tools/medtas/medtas_state_engine_v1_1.py", "medtas_engine_projection")
    sample = {
        "configuration_scope": {"effectivity_status": "OPEN"},
        "characteristics": {
            "C01": {"measurement_condition": {"status": "OPEN"}, "inspection_strategy": {"method": "A"}},
            "C02": {"measurement_condition": {"status": "CONTROLLED"}, "inspection_strategy": {"method": "B"}},
        },
    }
    payload, errors = eng.json_projection(sample, ["characteristics.*.measurement_condition"])
    assert errors == []
    assert set(payload["characteristics.*.measurement_condition"]) == {"C01", "C02"}
    assert "inspection_strategy" not in json.dumps(payload)
