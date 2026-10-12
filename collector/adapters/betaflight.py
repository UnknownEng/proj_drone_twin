import numpy as np
import pandas as pd
from orangebox import Parser


def read_log(path, log_index=1):
    parser = Parser.load(path, log_index=log_index)
    rows = [frame.data for frame in parser.frames()]
    df = pd.DataFrame(rows, columns=parser.field_names)
    return df, parser.headers


def clean_time(df, max_gap_s=0.5):
    """Keep the longest run of frames with increasing time and no big gaps.

    Some logs start with a few junk frames (time near zero, then a jump).
    """
    t = df["time"].to_numpy(dtype="float64") / 1e6
    dt = np.diff(t)
    bad = (dt <= 0) | (dt > max_gap_s)
    cuts = np.concatenate(([0], np.where(bad)[0] + 1, [len(t)]))
    best = max(zip(cuts[:-1], cuts[1:]), key=lambda se: se[1] - se[0])
    kept = df.iloc[best[0]:best[1]].reset_index(drop=True)
    return kept, len(df) - len(kept)


def to_unified(df):
    df, dropped = clean_time(df)
    if dropped:
        print(f"Cleaned log: dropped {dropped} junk/gap frames")
    t = (df["time"] - df["time"].iloc[0]) / 1e6  # microseconds -> seconds

    imu = pd.DataFrame({"t_s": t})
    for i, ax in enumerate(["x", "y", "z"]):
        imu[f"gyro_{ax}"] = df[f"gyroADC[{i}]"]

    motors = pd.DataFrame({"t_s": t})
    for i in range(4):
        motors[f"motor_{i}"] = df[f"motor[{i}]"]

    rc = pd.DataFrame({"t_s": t})
    for i, name in enumerate(["roll", "pitch", "yaw", "throttle"]):
        rc[f"rc_{name}"] = df[f"rcCommand[{i}]"]

    return imu, motors, rc
