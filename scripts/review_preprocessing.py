"""Independently verify saved selections; do not overwrite preprocessing outputs.

Run from the project root: .venv/Scripts/python.exe scripts/review_preprocessing.py
Candidate segmentation is rerun with the production pipeline. Interval metrics,
exhaustive longest-interval checks and threshold sensitivity are computed here
without calling the production stability or interval-selection functions.
"""

from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from configs.data_config import INPUT_COLUMNS
from configs.preprocessing_config import DEFAULT_PREPROCESSING_CONFIG as CONFIG
from thermal_twin.preprocessing import CPU_COLUMNS, TARGET_COLUMN, extract_steady_states


OUT = Path("results/preprocessing_review")


def metrics(frame):
    """Independent interval statistics, including normalized input excursions."""
    x = frame[list(INPUT_COLUMNS)].to_numpy(float)
    y = frame[list(CPU_COLUMNS)].to_numpy(float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        return np.full(4, np.inf)
    t = (frame.time_local - frame.time_local.iloc[0]).dt.total_seconds().to_numpy() / 60
    limits = np.array([
        CONFIG.cpu_power_range_abs_W + CONFIG.cpu_power_range_relative * abs(x[:, 0].mean()),
        CONFIG.inlet_temperature_range_C,
        CONFIG.fan_power_range_abs_raw + CONFIG.fan_power_range_relative * abs(x[:, 2].mean()),
    ])
    return np.array([
        (np.ptp(x, axis=0) / limits).max(), y.std(axis=0, ddof=1).max(),
        np.ptp(y, axis=0).max(), np.abs(np.polyfit(t, y, 1)[0]).max(),
    ])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = Path("data/raw/ocp_air_cooling_5min.csv")
    saved_path = Path("data/processed/steady_state.csv")
    manifest = json.loads(Path("results/preprocessing/manifest.json").read_text())
    assert asdict(CONFIG) == manifest["config"], "Saved thresholds differ from defaults"
    for path, key in [(source, "source_sha256"), (saved_path, "output_sha256")]:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest[key]
    raw = pd.read_csv(source)
    fresh = extract_steady_states(raw)
    csv = fresh.observations.to_csv(index=False, float_format="%.12g", lineterminator="\n")
    assert saved_path.read_text() == csv, "Regenerated observations differ from saved CSV"
    saved_periods = pd.read_csv("results/preprocessing/period_diagnostics.csv")
    expected = pd.read_csv(io.StringIO(fresh.periods.to_csv(index=False, float_format="%.12g")))
    pd.testing.assert_frame_equal(saved_periods, expected)
    saved_rows = pd.read_csv("results/preprocessing/row_diagnostics.csv")
    for col in ["operating_period_id", "selection_status", "observation_id"]:
        a = saved_rows[col].astype(object).where(saved_rows[col].notna(), "").astype(str)
        b = fresh.rows[col].astype(object).where(fresh.rows[col].notna(), "").astype(str)
        if col == "operating_period_id":
            pd.testing.assert_series_equal(pd.to_numeric(saved_rows[col]),
                pd.to_numeric(fresh.rows[col]).astype(float), check_names=False)
        else:
            pd.testing.assert_series_equal(a, b, check_names=False)

    # Sensitivity scenarios keep segmentation fixed and change one criterion.
    scenarios = {
        "default": {}, "std_0.75_C": {"std": 0.75},
        "global_drift_0.02_C_per_min": {"drift": 0.02},
        "local_drift_0.04_C_per_min": {"local_drift": 0.04},
        "retained_dwell_60_min": {"dwell": 60},
        "initial_discard_40_min": {"settling": 40},
    }
    selections, review, rejected = [], [], []
    windows_n = int(np.ceil(CONFIG.stability_window_minutes / CONFIG.sample_interval_minutes)) + 1
    for pid, frame in fresh.rows.dropna(subset=["operating_period_id"]).groupby("operating_period_id"):
        frame = frame.reset_index(drop=True)
        times = (frame.time_local - frame.time_local.iloc[0]).dt.total_seconds().to_numpy() / 60
        rolling = np.array([metrics(frame.iloc[i:i + windows_n])
                            for i in range(len(frame) - windows_n + 1)])
        candidates = []
        for start in np.flatnonzero(times >= CONFIG.initial_settling_minutes):
            for end in range(start + windows_n, len(frame) + 1):
                global_metrics = metrics(frame.iloc[start:end])
                local = rolling[start:end - windows_n + 1].max(axis=0)
                candidates.append((start, end, global_metrics, local))
        by_scenario = {}
        for name, overrides in scenarios.items():
            passing = []
            for start, end, g, local in candidates:
                if times[start] < overrides.get("settling", CONFIG.initial_settling_minutes):
                    continue
                if times[end - 1] - times[start] < overrides.get("dwell", CONFIG.minimum_dwell_minutes):
                    continue
                global_limits = [1, overrides.get("std", CONFIG.cpu_temperature_std_C),
                    CONFIG.cpu_temperature_range_C, overrides.get("drift", CONFIG.cpu_temperature_drift_C_per_minute)]
                local_limits = [1, global_limits[1], global_limits[2],
                    overrides.get("local_drift", CONFIG.cpu_temperature_window_drift_C_per_minute)]
                # Tiny tolerance is for independently computed floating-point slopes.
                if np.all(g <= np.array(global_limits) + 1e-12) and np.all(local <= np.array(local_limits) + 1e-12):
                    passing.append((start, end))
            best = min(passing, key=lambda bounds: (-(bounds[1] - bounds[0]), bounds[0])) if passing else None
            by_scenario[name] = best
            selections.append({"scenario": name, "case_id": int(frame.case_id.iloc[0]),
                "operating_period_id": int(pid), "accepted": best is not None})

        row = fresh.periods.set_index("operating_period_id").loc[pid]
        best = by_scenario["default"]
        assert (best is not None) == (row.status == "accepted")
        if best is None:
            after = rolling[np.flatnonzero(times[:len(rolling)] >= CONFIG.initial_settling_minutes)]
            limits = np.array([1, CONFIG.cpu_temperature_std_C, CONFIG.cpu_temperature_range_C,
                               CONFIG.cpu_temperature_window_drift_C_per_minute])
            rejected.append({"case_id": int(frame.case_id.iloc[0]), "operating_period_id": int(pid),
                "reason": row.reason, "post_discard_windows": len(after),
                **{f"windows_failing_{label}": int((after[:, i] > limits[i] + 1e-12).sum())
                   for i, label in enumerate(["inputs", "std", "range", "local_drift"])}})
            continue
        start, end = best
        chosen = frame.iloc[start:end]
        obs = fresh.observations.set_index("operating_period_id").loc[pid]
        assert chosen.time_local.iloc[0] == obs.start_time == row.accepted_start_time
        assert chosen.time_local.iloc[-1] == obs.end_time == row.accepted_end_time
        assert chosen.time_local.diff().dropna().eq(pd.Timedelta(minutes=5)).all()
        assert chosen.case_id.nunique() == 1 and chosen.case_id.isin(range(1, 6)).all()
        assert len(chosen) == obs.sample_count
        means = chosen[[*INPUT_COLUMNS, *CPU_COLUMNS]].mean()
        np.testing.assert_allclose(means, obs[means.index].astype(float), rtol=0, atol=1e-10)
        assert means[list(CPU_COLUMNS)].max() == obs[TARGET_COLUMN]
        g = metrics(chosen)
        valid_targets = []
        for a, b, whole, local in candidates:
            if b - a != windows_n:
                continue
            if np.all(whole <= [1, CONFIG.cpu_temperature_std_C, CONFIG.cpu_temperature_range_C,
                               CONFIG.cpu_temperature_drift_C_per_minute]) and np.all(local <= [
                    1, CONFIG.cpu_temperature_std_C, CONFIG.cpu_temperature_range_C,
                    CONFIG.cpu_temperature_window_drift_C_per_minute]):
                valid_targets.append(frame.iloc[a:b][list(CPU_COLUMNS)].mean().max())
        review.append({"observation_id": obs.observation_id, "case_id": int(obs.case_id),
            "operating_period_id": int(pid), "start_time": obs.start_time, "end_time": obs.end_time,
            "delay_from_candidate_min": times[start], "duration_min": obs.duration_minutes,
            "samples": len(chosen), "max_input_range_fraction_of_limit": g[0],
            "max_cpu_std_C": g[1], "max_cpu_range_C": g[2], "max_abs_drift_C_per_min": g[3],
            "target_C": obs[TARGET_COLUMN],
            "passing_30min_target_span_C": np.ptp(valid_targets) if valid_targets else np.nan})
        print(f"Verified period {int(pid)}: {len(chosen)} samples", flush=True)

    review = pd.DataFrame(review)
    review.to_csv(OUT / "accepted_interval_checks.csv", index=False, float_format="%.12g")
    pd.DataFrame(rejected).to_csv(OUT / "rejected_period_checks.csv", index=False)
    sensitivity = pd.DataFrame(selections).groupby(["scenario", "case_id"]).accepted.sum().unstack()
    sensitivity["total"] = sensitivity.sum(axis=1)
    sensitivity.to_csv(OUT / "threshold_sensitivity.csv")
    print("All saved selections, longest-interval choices, targets, hashes and row labels verified.")
    print(review.to_string(index=False))
    print(pd.DataFrame(rejected).to_string(index=False))
    print(sensitivity.to_string())


if __name__ == "__main__":
    main()
