import argparse
import json
import os

from collector import profile as prof
from collector import quality
from collector.schema import (
    ATTITUDE_COLUMNS, BATTERY_COLUMNS, IMU_COLUMNS, MODE_COLUMNS, MOTOR_COLUMNS,
    OPTIONAL_FILES, RC_COLUMNS, REQUIRED_FILES, SCHEMA_VERSION, UNITS,
)

COLUMNS = {
    "imu": IMU_COLUMNS, "motors": MOTOR_COLUMNS, "rc_setpoints": RC_COLUMNS,
    "attitude": ATTITUDE_COLUMNS, "battery": BATTERY_COLUMNS, "modes_events": MODE_COLUMNS,
}


def _convert(firmware, input_path):
    if firmware in ("betaflight", "inav"):
        from collector.adapters import betaflight as a
        df, headers = a.read_log(input_path)
        return a.build(df, headers)
    if firmware == "ardupilot":
        from collector.adapters import ardupilot as a
        return a.build(a.read_log(input_path))
    raise SystemExit(f"No adapter for '{firmware}' yet (PX4 comes on Day 3).")


def import_log(firmware, input_path, output_dir, profile_path=None):
    data, info = _convert(firmware, input_path)
    os.makedirs(output_dir, exist_ok=True)

    written = []
    for name in REQUIRED_FILES + OPTIONAL_FILES:
        df = data.get(name)
        if df is not None and len(df):
            df = df[COLUMNS[name]]
            data[name] = df
            df.to_csv(os.path.join(output_dir, f"{name}.csv"), index=False)
            written.append(name)

    drone = prof.load(profile_path) if profile_path else prof.template("unknown")
    missing = prof.missing(drone)

    meta = {
        "schema_version": SCHEMA_VERSION,
        "firmware": firmware,
        "firmware_version": info["firmware_version"],
        "vehicle": info["vehicle"],
        "source_file": os.path.basename(input_path),
        "files": written,
        "capabilities": info["capabilities"],
        "units": UNITS,
        "units_verified": info["units_verified"],
        "units_note": info["units_note"],
        "frame_convention_verified": False,
        "motor_output_range": info["motor_output_range"],
        "adapter_notes": info["adapter_notes"],
        "drone": drone,
        "drone_profile_missing": missing,
    }
    rep = quality.analyze(data, meta)
    meta["sample_rate_hz"] = rep["imu_rate_hz"]
    meta["suitable_for_system_id"] = rep["suitable_for_system_id"]

    with open(os.path.join(output_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    quality.save(rep, output_dir)

    print(f"Saved dataset to {output_dir}  (files: {', '.join(written)})")
    quality.print_report(rep, missing)


def report_only(dataset_dir):
    from trainer.loader import load_dataset
    meta, data = load_dataset(dataset_dir)
    rep = quality.analyze(data, meta)
    quality.print_report(rep, meta.get("drone_profile_missing", []))


def main():
    p = argparse.ArgumentParser(prog="collector")
    sub = p.add_subparsers(dest="cmd", required=True)

    imp = sub.add_parser("import", help="convert a flight log to the unified dataset")
    imp.add_argument("--firmware", required=True, choices=["betaflight", "inav", "ardupilot"])
    imp.add_argument("--input", required=True)
    imp.add_argument("--output", required=True)
    imp.add_argument("--profile", help="drone profile .yaml (mass, props, battery)")

    rep = sub.add_parser("report", help="print the quality report of a dataset")
    rep.add_argument("--dataset", required=True)

    new = sub.add_parser("new-profile", help="create an empty drone profile")
    new.add_argument("--name", required=True)
    new.add_argument("--output", required=True)

    a = p.parse_args()
    if a.cmd == "import":
        import_log(a.firmware, a.input, a.output, a.profile)
    elif a.cmd == "report":
        report_only(a.dataset)
    elif a.cmd == "new-profile":
        prof.save(prof.template(a.name), a.output)
        print(f"Created {a.output}. Open it and fill in the values.")


if __name__ == "__main__":
    main()
