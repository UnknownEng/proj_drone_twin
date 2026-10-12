"""Betaflight / INAV blackbox adapter (via orangebox)."""
import numpy as np
import pandas as pd
from orangebox import Parser

from collector.common import bits_to_float, longest_clean_segment


def read_log(path, log_index=1):
    parser = Parser.load(path, log_index=log_index)
    rows = [frame.data for frame in parser.frames()]
    df = pd.DataFrame(rows, columns=parser.field_names)
    return df, dict(parser.headers)


def build(df, headers):
    notes = []
    start, end = longest_clean_segment(df["time"].to_numpy(dtype="float64") / 1e6)
    dropped = len(df) - (end - start)
    df = df.iloc[start:end].reset_index(drop=True)
    if dropped:
        notes.append(f"dropped {dropped} junk/gap frames")
    t = (df["time"] - df["time"].iloc[0]) / 1e6

    # --- gyro: header scale decides units
    fw = str(headers.get("Firmware revision", ""))
    scale = bits_to_float(headers["gyro_scale"]) if "gyro_scale" in headers else None
    units_verified = scale is not None and abs(scale - 1.0) < 1e-6 and fw.startswith("Betaflight")
    if scale is None:
        scale = 1.0
        notes.append("gyro_scale header missing, assumed deg/s")
    elif not units_verified:
        notes.append(f"gyro_scale={scale:g} / firmware '{fw}': gyro units NOT verified")

    imu = pd.DataFrame({"t_s": t})
    for i, ax in enumerate("xyz"):
        imu[f"gyro_{ax}"] = df[f"gyroADC[{i}]"] * scale

    acc_1g = float(headers.get("acc_1G", 0)) or None
    for i, ax in enumerate("xyz"):
        col = f"accSmooth[{i}]"
        if acc_1g and col in df:
            imu[f"acc_{ax}"] = df[col] / acc_1g
        else:
            imu[f"acc_{ax}"] = np.nan
    if not acc_1g:
        notes.append("acc_1G header missing: accelerometer not scaled")

    # --- motors: normalise with the log's own output range
    lo, hi = headers.get("motorOutput", [None, None])[:2] if "motorOutput" in headers else (None, None)
    if lo is None or hi is None or hi <= lo:
        lo, hi = float(df["motor[0]"].min()), float(df["motor[0]"].max())
        notes.append("motorOutput header missing: range estimated from data")
    motors = pd.DataFrame({"t_s": t})
    for i in range(4):
        motors[f"motor_{i}"] = df[f"motor[{i}]"]
    for i in range(4):
        motors[f"motor_norm_{i}"] = ((df[f"motor[{i}]"] - lo) / (hi - lo)).clip(0, 1)

    # --- rc: roll/pitch/yaw -500..500 -> -1..1, throttle 1000..2000 -> 0..1
    rc = pd.DataFrame({"t_s": t})
    for i, name in enumerate(["roll", "pitch", "yaw"]):
        rc[f"rc_{name}"] = (df[f"rcCommand[{i}]"] / 500.0).clip(-1, 1)
    thr_raw = df["rcCommand[3]"].astype("float64")
    wrapped = int((thr_raw >= 2**31).sum())
    if wrapped:
        notes.append(f"fixed {wrapped} throttle values with a 32-bit wrap error")
    thr_raw = thr_raw % 2**32
    rc["rc_throttle"] = ((thr_raw - 1000.0) / 1000.0).clip(0, 1)

    # --- flight mode flags: store change events (decoded in a later day)
    modes = None
    if "flightModeFlags" in df:
        flags = df["flightModeFlags"].astype(str)
        changed = flags != flags.shift()
        modes = pd.DataFrame({"t_s": t[changed].to_numpy(), "mode_raw": flags[changed].to_numpy()})

    info = {
        "firmware_version": fw,
        "vehicle": str(headers.get("Craft name", "")),
        "units_verified": bool(units_verified),
        "units_note": "gyro scale from log header" if units_verified else "see notes",
        "motor_output_range": [float(lo), float(hi)],
        "adapter_notes": notes,
        "capabilities": ["gyro", "accel", "motors", "rc", "mode_flags"],
    }
    data = {"imu": imu, "motors": motors, "rc_setpoints": rc,
            "attitude": None, "battery": None, "modes_events": modes}
    return data, info
