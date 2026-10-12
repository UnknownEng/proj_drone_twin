import os

import numpy as np
import pandas as pd
import pytest

from collector import quality
from collector.common import longest_clean_segment, bits_to_float

BF_LOG = "data/raw/flight1.bbl"
AP_LOG = "data/raw/test_ardupilot.bin"


def test_clean_segment_drops_junk_start():
    t = np.array([0.0, -0.1, -0.2, 200.0, 200.001, 200.002, 200.003])
    s, e = longest_clean_segment(t)
    assert (s, e) == (3, 7)


def test_clean_segment_splits_on_big_gap():
    t = np.concatenate([np.arange(0, 1, 0.01), np.arange(5, 5.2, 0.01)])
    s, e = longest_clean_segment(t)
    assert e - s == 100


def test_bits_to_float_one():
    assert bits_to_float(1065353216) == 1.0


def _fake(rate=1000.0, seconds=60.0, wiggle=300.0):
    t = np.arange(0, seconds, 1 / rate)
    g = wiggle * np.sin(2 * np.pi * 0.5 * t)
    imu = pd.DataFrame({"t_s": t, "gyro_x": g, "gyro_y": g * 0.5, "gyro_z": g * 0.2,
                        "acc_x": 0.0, "acc_y": 0.0, "acc_z": 1.0})
    mot = pd.DataFrame({"t_s": t, **{f"motor_norm_{i}": 0.4 for i in range(4)}})
    rc = pd.DataFrame({"t_s": t, "rc_roll": 0.0, "rc_pitch": 0.0, "rc_yaw": 0.0, "rc_throttle": 0.4})
    return {"imu": imu, "motors": mot, "rc_setpoints": rc}


def test_quality_accepts_good_log():
    rep = quality.analyze(_fake(), {"units_verified": True})
    assert rep["suitable_for_system_id"] is True


def test_quality_rejects_low_rate():
    rep = quality.analyze(_fake(rate=50.0), {"units_verified": True})
    assert rep["suitable_for_system_id"] is False
    assert any("rate" in p for p in rep["problems"])


def test_quality_rejects_short_log():
    rep = quality.analyze(_fake(seconds=5.0), {"units_verified": True})
    assert rep["suitable_for_system_id"] is False


@pytest.mark.skipif(not os.path.exists(BF_LOG), reason="betaflight sample log missing")
def test_betaflight_real_log():
    from collector.adapters import betaflight
    df, headers = betaflight.read_log(BF_LOG)
    data, info = betaflight.build(df, headers)
    assert info["units_verified"] is True
    assert (np.diff(data["imu"]["t_s"]) > 0).all()
    rc = data["rc_setpoints"]
    assert rc["rc_throttle"].between(0, 1).all()
    assert rc["rc_throttle"].mean() < 0.9          # not stuck at max
    assert data["motors"]["motor_norm_0"].between(0, 1).all()
    assert 0.5 < data["imu"]["acc_z"].median() < 1.5   # about 1 g at rest-ish


@pytest.mark.skipif(not os.path.exists(AP_LOG), reason="ardupilot sample log missing")
def test_ardupilot_real_log():
    from collector.adapters import ardupilot
    data, info = ardupilot.build(ardupilot.read_log(AP_LOG))
    assert info["units_verified"] is True
    assert len(data["imu"]) > 10
    assert (np.diff(data["imu"]["t_s"]) > 0).all()
    assert abs(data["imu"]["acc_z"].median()) > 0.5   # gravity shows up in g
