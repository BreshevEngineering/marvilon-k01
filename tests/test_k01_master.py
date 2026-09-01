import json
from pathlib import Path
from params import k01_params as p

ROOT = Path(__file__).resolve().parents[1]

def test_p003_p016_nominal_pilot_match():
    assert p.P003_PILOT_D_MM == p.P016_PILOT_BORE_D_MM == 10.0

def test_pilot_bottom_clearance():
    assert abs(p.P003_P016_PILOT_BOTTOM_CLEARANCE_NOM_MM - 0.20) < 1e-12

def test_h7_g6_clearance_is_always_positive():
    assert abs(p.P003_P016_CLEARANCE_MIN_MM - 0.005) < 1e-12
    assert abs(p.P003_P016_CLEARANCE_MAX_MM - 0.029) < 1e-12
    assert p.P003_P016_CLEARANCE_MIN_MM > 0

def test_fastener_pattern_matches():
    assert p.P003_FASTENER_COUNT == p.P016_FASTENER_COUNT == 3
    assert p.P003_FASTENER_PCD_MM == p.P016_FASTENER_PCD_MM == 24.0

def test_p007_wall_consistency():
    assert abs((p.P007_THIN_OD_MM - p.P007_THIN_ID_MM)/2 - p.P007_THIN_WALL_MM) < 1e-12

def test_master_exists_and_points_to_params():
    master = json.loads((ROOT/"master"/"K01_master.json").read_text(encoding="utf-8"))
    assert master["authoring"]["parameter_source"] == "params/k01_params.py"
    assert master["current_interface"]["P003_P016"]["datum_C"].startswith("OPEN")
