import argparse
import json
import os

import numpy as np

from collector.schema import META_TEMPLATE
from collector.adapters import betaflight


def import_log(firmware, input_path, output_dir):
    if firmware not in ("betaflight", "inav"):
        raise SystemExit(f"Adapter for '{firmware}' not built yet (Day 2-3).")

    df, headers = betaflight.read_log(input_path)
    imu, motors, rc = betaflight.to_unified(df)

    os.makedirs(output_dir, exist_ok=True)
    imu.to_csv(os.path.join(output_dir, "imu.csv"), index=False)
    motors.to_csv(os.path.join(output_dir, "motors.csv"), index=False)
    rc.to_csv(os.path.join(output_dir, "rc_setpoints.csv"), index=False)

    rate = 1.0 / float(np.median(np.diff(imu["t_s"].values)))
    meta = json.loads(json.dumps(META_TEMPLATE))
    meta["firmware"] = firmware
    meta["source_file"] = os.path.basename(input_path)
    meta["sample_rate_hz"] = round(rate, 1)
    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Saved dataset to {output_dir}")
    print(f"Samples: {len(imu)}   Duration: {imu['t_s'].iloc[-1]:.1f} s   Rate: {rate:.0f} Hz")
    if rate < 500:
        print("WARNING: logging rate under 500 Hz, weak for system ID.")


def main():
    p = argparse.ArgumentParser(prog="collector")
    sub = p.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="convert a flight log to the unified dataset")
    imp.add_argument("--firmware", required=True)
    imp.add_argument("--input", required=True)
    imp.add_argument("--output", required=True)
    args = p.parse_args()
    if args.cmd == "import":
        import_log(args.firmware, args.input, args.output)


if __name__ == "__main__":
    main()
