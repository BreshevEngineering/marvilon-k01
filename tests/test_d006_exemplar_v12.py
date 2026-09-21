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


def ensure_d1():
    pd = load_module("tools/medtas/product_definition_guard_v11.py", "pd_v11_v12_scope")
    assert pd.main() == 0
    fp = load_module("tools/medtas/drawing_family_plan_v13.py", "family_v13_for_v12")
    assert fp.main() == 0
    d1 = load_module("tools/medtas/drawing_d1_authoring_plan_v11.py", "d1_v12_scope")
    assert d1.main() == 0
    return load_json("reports/drawing/current/K01-D-006_D1_AUTHORING_PLAN_CURRENT.json")


def test_route_open_does_not_blanket_block_route_independent_controlled_claims():
    plan = ensure_d1()
    assert plan["status"] == "PASS_D1_AUTHORING_PLAN"
    assert plan["d2_release_native_mutation_gate"] == "PASS_D2_ROUTE_INDEPENDENT_SCOPE_AUTHORIZABLE"
    assert set(plan["d2_authorizable_claim_ids"]) == {"C01.DATUM_A", "C02.DIAMETER_FIT", "C09.MATERIAL"}
    assert plan["d2_blocked_controlled_claim_ids"] == []
    assert any(x["code"] == "D1-BLK-MFG-ROUTE" and x["blocks_stage"] == "RELEASE" for x in plan["release_native_blockers"])
    assert not any(x.get("blocks_stage") == "D2" for x in plan["release_native_blockers"])


def test_authoring_context_declares_manufacturing_route_dependency_per_claim():
    ctx = load_json("control/product_definition/K01_CHARACTERISTIC_CONTEXT_CURRENT.json")
    targets = {}
    for cid, ch in ctx["characteristics"].items():
        for t in ch.get("drawing_authoring", {}).get("targets", []):
            targets[t["claim_id"]] = t
    for claim in ("C01.DATUM_A", "C02.DIAMETER_FIT", "C09.MATERIAL"):
        assert targets[claim]["manufacturing_route_dependency"] == "NONE"
        assert targets[claim]["exemplar_scope"] == "AUTHOR_IF_D1_CONTROLLED"
    assert targets["C06.OAL"]["manufacturing_route_dependency"] == "ROUTE_DEPENDENT"
    assert targets["C10.JOINING_PROCESS"]["manufacturing_route_dependency"] == "PROCESS_DEFINING"


def test_exemplar_policy_is_nonrelease_and_bounded_to_d1_authorized_scope():
    p = load_json("control/drawings/K01_D006_EXEMPLAR_POLICY_CURRENT.json")
    assert p["lane"] == "DESIGN_REVIEW_EXEMPLAR_NOT_RELEASE"
    assert p["release_eligible"] is False
    assert set(p["expected_d2_authorizable_claims"]) == {"C01.DATUM_A", "C02.DIAMETER_FIT", "C09.MATERIAL"}
    text = json.dumps(p, ensure_ascii=False).lower()
    assert "canonical" in text or "source" in text
    assert "release" in text


def test_graph_tracks_exemplar_workspace_and_capture_as_nonrelease_derived_nodes():
    g = load_json("control/medtas/v1/graph/K01_engineering_build_graph_v2_3.json")
    nodes = {x["node_id"]: x for x in g["nodes"]}
    for nid in ("K01.DRAWING.D006.EXEMPLAR.POLICY", "K01.DRAWING.D006.EXEMPLAR.WORKSPACE", "K01.DRAWING.D006.EXEMPLAR.CAPTURE"):
        assert nid in nodes
    ws_inputs = {x["node_id"] for x in nodes["K01.DRAWING.D006.EXEMPLAR.WORKSPACE"]["contract"]["inputs"]}
    assert {"K01.DRAWING.D006.D1.AUTHORING_PLAN", "K01.DRAWING.D006.PROJECTION", "K01.DRAWING.D006.EXEMPLAR.POLICY", "K01.PD.P007.DRAWING_SLICE"}.issubset(ws_inputs)
    cap_inputs = {x["node_id"] for x in nodes["K01.DRAWING.D006.EXEMPLAR.CAPTURE"]["contract"]["inputs"]}
    assert "K01.DRAWING.D006.EXEMPLAR.WORKSPACE" in cap_inputs
    assert "K01.PD.P007.DRAWING_SLICE" in cap_inputs


def test_capture_implementation_cannot_claim_full_d3_d7_or_release():
    text = (ROOT / "tools/medtas/d006_exemplar_capture_v12.py").read_text(encoding="utf-8")
    assert '"d3_release_native_status":"PARTIAL__' in text
    assert '"d7_release_native_status":"NOT_RUN' in text
    assert '"release":"HOLD"' in text
    assert "PASS_D006_EXEMPLAR_NATIVE_TRANSPORT__D6_CLEANUP_REQUIRED" in text


def test_manual_exemplar_precedes_d5_automation_in_method_registry_and_session_rules():
    methods = load_json("control/project/K01_EXECUTION_METHOD_REGISTRY_CURRENT.json")
    by = {x["id"]: x for x in methods["methods"]}
    assert by["D006_MANUAL_EXEMPLAR_V12"]["status"] == "NATIVE_TRANSPORT_PROVEN__D6_VISUAL_BASE_ACTIVE"
    assert by["DRAWING_D5_RELEASE_NATIVE_GENERATOR"]["status"] == "DEFER_UNTIL_EXEMPLAR_D3_D7_EVIDENCE"
    rules = load_json("control/project/K01_AI_SESSION_RULES_CURRENT.json")
    text = "\n".join(x["rule"] for x in rules["permanent_rules"])
    assert "MANUAL EXEMPLAR BEFORE D5" in text
    assert "D2 AUTHORIZATION IS CLAIM-SCOPED" in text
