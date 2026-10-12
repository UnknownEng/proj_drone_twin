"""ArduPilot .bin / .BIN dataflash adapter (via pymavlink)."""
import numpy as np
import pandas as pd
from pymavlink import mavutil

from collector.common import longest_clean_segment

G = 9.80665
WANTED = ["IMU", "RCIN", "RCOU", "ATT", "BAT", "MODE", "MSG"]


def read_log(path):
    m = mavutil.mavlink_connection(path)
    rows = {k: [] for k in WANTED}
    while True:
        msg = m.recv_match(type=WANTED)
        if msg is None:
            break
        rows[msg.get_type()].append(msg.to_dict())
    return rows


def _df(rows, cols):
    return pd.DataFrame(rows)[["TimeUS"] + cols] if rows else None


def build(rows):
    notes = []
    imu_rows = [r for r in rows["IMU"] if r.get("I", 0) == 0]  # first IMU only
    if not imu_rows:
        raise SystemExit("No IMU messages in this log: cannot build a dataset.")
    imu_raw = pd.DataFrame(imu_rows)
    t_us = imu_raw["TimeUS"].to_numpy(dtype="float64") / 1e6
    s, e = longest_clean_segment(t_us)
    if len(t_us) - (e - s):
        notes.append(f"dropped {len(t_us) - (e - s)} junk/gap IMU frames")
    imu_raw = imu_raw.iloc[s:e].reset_index(drop=True)
    t0 = imu_raw["TimeUS"].iloc[0] / 1e6
    t1 = imu_raw["TimeUS"].iloc[-1] / 1e6

    def window(df, ts):
        t = df["TimeUS"] / 1e6
        df = df[(t >= t0) & (t <= t1)].copy()
        df.insert(0, "t_s", (df["TimeUS"] / 1e6 - t0).to_numpy())
        return df.drop(columns=["TimeUS"]).reset_index(drop=True)

    imu = pd.DataFrame({"t_s": imu_raw["TimeUS"] / 1e6 - t0})
    for ax in "XYZ":
        imu[f"gyro_{ax.lower()}"] = np.degrees(imu_raw[f"Gyr{ax}"])   # rad/s -> deg/s
        imu[f"acc_{ax.lower()}"] = imu_raw[f"Acc{ax}"] / G           # m/s^2 -> g

    motors = rc = attitude = battery = modes = None
    if rows["RCOU"]:
        d = window(_df(rows["RCOU"], ["C1", "C2", "C3", "C4"]), None)
        motors = pd.DataFrame({"t_s": d["t_s"]})
        for i in range(4):
            motors[f"motor_{i}"] = d[f"C{i + 1}"]
        for i in range(4):
            motors[f"motor_norm_{i}"] = ((d[f"C{i + 1}"] - 1000.0) / 1000.0).clip(0, 1)
    if rows["RCIN"]:
        d = window(_df(rows["RCIN"], ["C1", "C2", "C3", "C4"]), None)
        rc = pd.DataFrame({"t_s": d["t_s"]})
        rc["rc_roll"] = ((d["C1"] - 1500.0) / 500.0).clip(-1, 1)
        rc["rc_pitch"] = ((d["C2"] - 1500.0) / 500.0).clip(-1, 1)
        rc["rc_yaw"] = ((d["C4"] - 1500.0) / 500.0).clip(-1, 1)
        rc["rc_throttle"] = ((d["C3"] - 1000.0) / 1000.0).clip(0, 1)
    if rows["ATT"]:
        d = window(_df(rows["ATT"], ["Roll", "Pitch", "Yaw"]), None)
        attitude = d.rename(columns={"Roll": "roll_deg", "Pitch": "pitch_deg", "Yaw": "yaw_deg"})
    if rows["BAT"]:
        d = window(_df(rows["BAT"], ["Volt", "Curr"]), None)
        battery = d.rename(columns={"Volt": "voltage_v", "Curr": "current_a"})
    if rows["MODE"]:
        d = window(_df(rows["MODE"], ["ModeNum"]), None)
        modes = d.rename(columns={"ModeNum": "mode_raw"})

    vehicle, version = "unknown", ""
    for r in rows["MSG"]:
        text = str(r.get("Message", ""))
        for name in ("ArduCopter", "ArduPlane", "Rover", "ArduSub"):
            if text.startswith(name):
                vehicle, version = name, text
                break
        if vehicle != "unknown":
            break
    if vehicle != "ArduCopter":
        notes.append(f"vehicle is '{vehicle}', not ArduCopter: RCOU C1-C4 may not be motors")

    info = {
        "firmware_version": version,
        "vehicle": vehicle,
        "units_verified": True,
        "units_note": "ArduPilot logs SI units (rad/s, m/s^2); converted to deg/s and g",
        "motor_output_range": [1000.0, 2000.0],
        "adapter_notes": notes,
        "capabilities": ["gyro", "accel", "motors", "rc", "attitude_est"]
        + (["battery"] if battery is not None else [])
        + (["modes"] if modes is not None else []),
    }
    data = {"imu": imu, "motors": motors, "rc_setpoints": rc,
            "attitude": attitude, "battery": battery, "modes_events": modes}
    return data, info
