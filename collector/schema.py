"""Unified dataset schema. Every adapter must output these files/columns."""

IMU_COLUMNS = ["t_s", "gyro_x", "gyro_y", "gyro_z"]
MOTOR_COLUMNS = ["t_s", "motor_0", "motor_1", "motor_2", "motor_3"]
RC_COLUMNS = ["t_s", "rc_roll", "rc_pitch", "rc_yaw", "rc_throttle"]

META_TEMPLATE = {
    "firmware": None,
    "firmware_version": None,
    "source_file": None,
    "sample_rate_hz": None,
    "units_verified": False,
    "drone": {
        "mass_g": None,
        "prop_size_in": None,
        "motor_kv": None,
        "battery_cells": None,
        "battery_mah": None,
    },
}
