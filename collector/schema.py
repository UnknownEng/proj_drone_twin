"""Unified dataset schema (version 1).

Every adapter returns DataFrames with these columns. Units are SI-like and
identical for every firmware, so Software 2 never needs to know the source.
"""

SCHEMA_VERSION = 1

IMU_COLUMNS = ["t_s", "gyro_x", "gyro_y", "gyro_z", "acc_x", "acc_y", "acc_z"]
MOTOR_COLUMNS = (
    ["t_s"]
    + [f"motor_{i}" for i in range(4)]
    + [f"motor_norm_{i}" for i in range(4)]
)
RC_COLUMNS = ["t_s", "rc_roll", "rc_pitch", "rc_yaw", "rc_throttle"]
ATTITUDE_COLUMNS = ["t_s", "roll_deg", "pitch_deg", "yaw_deg"]
BATTERY_COLUMNS = ["t_s", "voltage_v", "current_a"]
MODE_COLUMNS = ["t_s", "mode_raw"]

REQUIRED_FILES = ["imu", "motors", "rc_setpoints"]
OPTIONAL_FILES = ["attitude", "battery", "modes_events"]

UNITS = {
    "time": "s (starts at 0)",
    "gyro": "deg/s",
    "acc": "g",
    "motor_raw": "native firmware units (Betaflight/INAV: output counts, ArduPilot: PWM us)",
    "motor_norm": "0..1 (0 = min output, 1 = max output)",
    "rc_roll_pitch_yaw": "-1..1",
    "rc_throttle": "0..1",
    "attitude": "deg",
    "battery": "V, A",
}

DRONE_FIELDS = [
    "name", "mass_g", "frame_size_mm", "prop_size_in", "prop_pitch_in",
    "motor_model", "motor_kv", "battery_cells", "battery_mah", "notes",
]
DRONE_REQUIRED = ["mass_g", "prop_size_in", "motor_kv", "battery_cells", "battery_mah"]
