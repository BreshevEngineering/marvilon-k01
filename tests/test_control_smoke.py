from params import k01_params_example as p

def test_stroke():
    assert p.STROKE == 10.0

def test_follower_clearance_positive():
    assert (p.D_CAN_I - p.D_FOLLOWER) / 2 > 0

def test_p003_p016_nominal_match():
    assert p.P016_PILOT_NOM == p.P003_PILOT_NOM
