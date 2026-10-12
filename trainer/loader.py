import json
import os
import sys

import pandas as pd

from collector.schema import OPTIONAL_FILES, REQUIRED_FILES


def load_dataset(path):
    with open(os.path.join(path, "meta.json")) as f:
        meta = json.load(f)
    data = {}
    for name in REQUIRED_FILES:
        data[name] = pd.read_csv(os.path.join(path, f"{name}.csv"))
    for name in OPTIONAL_FILES:
        fp = os.path.join(path, f"{name}.csv")
        data[name] = pd.read_csv(fp) if os.path.exists(fp) else None
    return meta, data


if __name__ == "__main__":
    meta, data = load_dataset(sys.argv[1])
    print("Firmware:", meta["firmware"], "| Vehicle:", meta["vehicle"],
          "| Rate:", meta["sample_rate_hz"], "Hz | units verified:", meta["units_verified"])
    for name, df in data.items():
        if df is not None:
            print(f"{name}: {len(df)} rows, columns = {list(df.columns)}")
