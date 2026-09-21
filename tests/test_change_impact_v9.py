from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDTAS = ROOT / "tools" / "medtas"
if str(MEDTAS) not in sys.path:
    sys.path.insert(0, str(MEDTAS))

import medtas_state_engine_v1_1 as eng
from change_impact_v9 import build_plan


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def test_current_graph_v23_is_authoritative_and_acyclic():
    amap = load("control/project/K01_AUTHORITY_MAP_CURRENT.json")
    gp = amap["control_families"]["engineering_build_graph"]["authority"]
    assert gp.endswith("K01_engineering_build_graph_v2_3.json")
    graph = load(gp)
    order = eng.topological({n["node_id"]: n for n in graph["nodes"]})
    assert len(order) == len(graph["nodes"])
    assert "K01.PD.P007.COMPILED" in order
    assert "K01.PD.P007.DRAWING_SLICE" in order
    assert "K01.PD.P007.VARIATION_SLICE" in order
    assert "K01.DRAWING.D006.PROJECTION" in order


def test_p007_geometry_reaches_cad_and_drawing_without_rewriting_semantic_authority():
    r = build_plan(ROOT, ["K01-P-007"], "geometry")
    ids = [x["node_id"] for x in r["rebuild_order"]]
    assert "K01.CAD.SEM.A001" in ids
    assert "K01.DRAWING.D006.PROJECTION" in ids
    # Pure geometry change does not silently rewrite Product Definition semantics.
    # Conformance/drawing consumers must reconcile against the existing compiled contract.
    assert "K01.PD.P007.COMPILED" not in ids
    assert r["release_path_affected"] is True


def test_shared_j2_change_requires_counterpart_review():
    r = build_plan(ROOT, ["K01-P-007"], "interface_geometry")
    reviews = {(x["interface"], x["entity"], x["status"]) for x in r["counterpart_reviews"]}
    assert ("K01-IF-J2", "K01-P-003", "COUNTERPART_REVIEW_REQUIRED") in reviews
    assert ("K01-IF-J2", "K01-P-007", "COUNTERPART_REVIEW_REQUIRED") in reviews
    assert "K01.PARAM.INTERFACE.J2" in r["seed_nodes"]


def test_visual_drawing_change_does_not_invalidate_product_definition_or_cad():
    r = build_plan(ROOT, ["K01-D-006"], "drawing_visual")
    ids = {x["node_id"] for x in r["rebuild_order"]}
    assert "K01.DRAWING.D006.PROJECTION" in ids
    assert "K01.PD.P007.COMPILED" not in ids
    assert "K01.CAD.SEM.A001" not in ids


def test_legacy_dependency_files_are_explicit_non_authorities():
    amap = load("control/project/K01_AUTHORITY_MAP_CURRENT.json")
    text = "\n".join(amap.get("explicit_non_authorities", []))
    assert "K01_DEPENDENCY_STATE.json" in text
    assert "K01_DEPENDENCY_GRAPH_v2.json" in text


def test_measurement_condition_change_does_not_invalidate_physics_without_declared_consumption():
    r = build_plan(ROOT, ["K01-P-007"], "measurement_condition")
    ids = {x["node_id"] for x in r["rebuild_order"]}
    assert "K01.PD.P007.CONTEXT.MEASUREMENT" in ids
    assert "K01.PD.P007.VARIATION_SLICE" in ids
    assert "K01.PD.P007.INSPECTION_SLICE" in ids
    assert "K01.DRAWING.D006.PROJECTION" in ids
    assert "K01.PD.P007.PHYSICS_SLICE" not in ids


def test_inspection_strategy_change_does_not_churn_drawing_or_physics():
    r = build_plan(ROOT, ["K01-P-007"], "inspection_strategy")
    ids = {x["node_id"] for x in r["rebuild_order"]}
    assert "K01.PD.P007.CONTEXT.INSPECTION" in ids
    assert "K01.PD.P007.INSPECTION_SLICE" in ids
    assert "K01.PD.P007.VARIATION_SLICE" in ids
    assert "K01.DRAWING.D006.PROJECTION" not in ids
    assert "K01.PD.P007.PHYSICS_SLICE" not in ids
