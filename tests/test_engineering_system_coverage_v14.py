import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "control/system/K01_ENGINEERING_DOMAIN_REGISTRY_CURRENT.json"
GRAPH = ROOT / "control/medtas/v1/graph/K01_engineering_build_graph_v2_5.json"


def load(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def test_registry_declares_core_scaling_domains():
    d = load(REG)
    ids = {x["id"] for x in d["domains"]}
    required = {
        "PRODUCT_DEFINITION", "CAD_MBD_BINDING", "DRAWING_D1_D9", "TOLERANCE_VARIATION",
        "STRUCTURAL_FEA", "MAGNETIC_FEMM", "FLOW_CFD", "THERMAL", "PRESSURE_VACUUM_CONTAINMENT",
        "EBOM", "MBOM", "INSPECTION_METROLOGY", "CONFIGURATION_RELEASE_BASELINE",
    }
    assert required <= ids


def test_no_declared_gap_is_silent():
    d = load(REG)
    for x in d["domains"]:
        if x["mode"] == "DECLARED_GAP_ALLOWED":
            assert x.get("declared_gaps")
            assert x.get("gap_action")


def test_required_graph_nodes_exist():
    reg = load(REG)
    graph = load(GRAPH)
    nodes = {n["node_id"] for n in graph["nodes"]}
    for x in reg["domains"]:
        if x["mode"] == "GRAPH_REQUIRED":
            assert set(x.get("graph_nodes", [])) <= nodes


def test_calculix_and_femm_names_are_controlled():
    text = REG.read_text(encoding="utf-8")
    assert "CalculiX" in text
    assert "FEMM" in text
    assert "Calcilux" not in text
