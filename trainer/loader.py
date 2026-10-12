import json
import os
import sys

import pandas as pd


def load_dataset(path):
    with open(os.path.join(path, "meta.json")) as f:
        meta = json.load(f)
    data = {
        name: pd.read_csv(os.path.join(path, f"{name}.csv"))
        for name in ("imu", "motors", "rc_setpoints")
    }
    return meta, data


if __name__ == "__main__":
    meta, data = load_dataset(sys.argv[1])
    print("Firmware:", meta["firmware"], "| Rate:", meta["sample_rate_hz"], "Hz")
    for name, df in data.items():
        print(f"{name}: {len(df)} rows, columns = {list(df.columns)}")
