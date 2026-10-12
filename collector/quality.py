"""Quality report: decides whether a dataset is usable and says why not."""
import json
import os

import numpy as np

# Heuristic thresholds (tune later against real results)
MIN_RATE_HZ = 500.0
MIN_DURATION_S = 30.0
GAP_FACTOR = 5.0
HOVER_DEG_S = 10.0
AGGRESSIVE_DEG_S = 200.0


def _rate(df):
    if df is None or len(df) < 3:
        return None
    return float(1.0 / np.median(np.diff(df["t_s"].to_numpy())))


def analyze(data, meta):
    imu = data["imu"]
    t = imu["t_s"].to_numpy()
    dt = np.diff(t)
    med = float(np.median(dt))
    rate = 1.0 / med
    gaps = int((dt > GAP_FACTOR * med).sum())
    duration = float(t[-1] - t[0])
    gyro = imu[["gyro_x", "gyro_y", "gyro_z"]].abs()
    p95 = {c: round(float(np.percentile(gyro[c], 95)), 1) for c in gyro}
    hover_frac = float((gyro < HOVER_DEG_S).all(axis=1).mean())
    aggr_frac = float((gyro > AGGRESSIVE_DEG_S).any(axis=1).mean())
    nan_frac = float(imu[["gyro_x", "gyro_y", "gyro_z"]].isna().mean().mean())

    problems, warnings = [], []
    if rate < MIN_RATE_HZ:
        problems.append(f"IMU rate {rate:.0f} Hz is below {MIN_RATE_HZ:.0f} Hz")
    if duration < MIN_DURATION_S:
        problems.append(f"duration {duration:.1f} s is below {MIN_DURATION_S:.0f} s")
    if gaps:
        problems.append(f"{gaps} time gaps larger than {GAP_FACTOR:g}x the sample period")
    if nan_frac > 0:
        problems.append("gyro contains missing values")
    if float(gyro.std().min()) < 1e-6:
        problems.append("a gyro axis is flat (sensor not logged?)")

    motors = data.get("motors")
    sat = None
    if motors is None:
        problems.append("no motor outputs logged")
    else:
        norm = motors[[f"motor_norm_{i}" for i in range(4)]]
        sat = float((norm >= 0.98).any(axis=1).mean())
        if sat > 0.05:
            warnings.append(f"motors at max {sat * 100:.0f}% of the time (saturation hides dynamics)")
    if data.get("rc_setpoints") is None:
        problems.append("no RC/command data logged")

    if hover_frac < 0.05:
        warnings.append("almost no calm/hover segments: add a slow, steady flight")
    if aggr_frac < 0.02:
        warnings.append("almost no aggressive segments: add fast maneuvers for excitation")
    if not meta.get("units_verified"):
        warnings.append("units not verified")
    warnings += meta.get("adapter_notes", [])

    return {
        "imu_rate_hz": round(rate, 1),
        "motor_rate_hz": _rate(motors),
        "rc_rate_hz": _rate(data.get("rc_setpoints")),
        "duration_s": round(duration, 1),
        "time_gaps": gaps,
        "gyro_p95_deg_s": p95,
        "calm_fraction": round(hover_frac, 3),
        "aggressive_fraction": round(aggr_frac, 3),
        "motor_saturation_fraction": None if sat is None else round(sat, 3),
        "problems": problems,
        "warnings": warnings,
        "suitable_for_system_id": len(problems) == 0,
    }


def print_report(rep, profile_missing):
    ok = "YES" if rep["suitable_for_system_id"] else "NO"
    print("\n=== Quality report ===")
    print(f"IMU rate: {rep['imu_rate_hz']} Hz | duration: {rep['duration_s']} s | gaps: {rep['time_gaps']}")
    print(f"Gyro 95th percentile (deg/s): {rep['gyro_p95_deg_s']}")
    print(f"Calm: {rep['calm_fraction'] * 100:.0f}% | aggressive: {rep['aggressive_fraction'] * 100:.0f}%")
    for p in rep["problems"]:
        print("  PROBLEM:", p)
    for w in rep["warnings"]:
        print("  warning:", w)
    print(f"Suitable for system ID: {ok}")
    if profile_missing:
        print(f"Drone profile incomplete, missing: {', '.join(profile_missing)}")
        print("  -> relative behaviour can be fitted, absolute parameters cannot.")


def save(rep, out_dir):
    with open(os.path.join(out_dir, "quality.json"), "w") as f:
        json.dump(rep, f, indent=2)
