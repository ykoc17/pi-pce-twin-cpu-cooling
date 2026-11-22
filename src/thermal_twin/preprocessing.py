"""Deterministic extraction of nonoverlapping, approximately steady observations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from configs.data_config import (
    CPU_TEMPERATURE_PATTERN, DEFAULT_DATA_PATH, EXPECTED_CASE_IDS,
    EXPECTED_CPU_COLUMNS, INPUT_COLUMNS, WORKLOAD_COLUMN,
)
from configs.preprocessing_config import DEFAULT_PREPROCESSING_CONFIG, PreprocessingConfig
from thermal_twin.data import DatasetValidationError, load_dataset

CPU_COLUMNS = tuple(sorted(EXPECTED_CPU_COLUMNS))
TARGET_COLUMN = "equilibrium_max_cpu_temp_C"
OBSERVATION_COLUMNS = (
    "observation_id", "operating_period_id", "case_id", "start_time", "end_time",
    "duration_minutes", "sample_count", *INPUT_COLUMNS, *CPU_COLUMNS,
    TARGET_COLUMN, "hottest_cpu", "mean_instantaneous_cpu_max_C",
    "max_cpu_temperature_std_C", "max_cpu_temperature_range_C",
    "max_abs_cpu_temperature_drift_C_per_minute",
    *(f"{column}__std" for column in CPU_COLUMNS),
    *(f"{column}__drift_C_per_minute" for column in CPU_COLUMNS),
)
PERIOD_COLUMNS = (
    "operating_period_id", "case_id", "candidate_start_time", "candidate_end_time",
    "candidate_duration_minutes", "candidate_sample_count", "post_settling_samples",
    "incomplete_cpu_sensor_rows", "status", "reason", "accepted_start_time",
    "accepted_end_time", "accepted_sample_count", "accepted_duration_minutes",
    "cpu_power_range_W", "inlet_temperature_range_C", "fan_power_range_raw",
    "max_cpu_temperature_std_C", "max_cpu_temperature_range_C",
    "max_abs_cpu_temperature_drift_C_per_minute",
)


@dataclass
class PreprocessingResult:
    observations: pd.DataFrame
    periods: pd.DataFrame
    rows: pd.DataFrame
    case_counts: pd.DataFrame


def prepare_measurements(raw: pd.DataFrame) -> pd.DataFrame:
    """Check schema/time ordering and convert only an in-memory copy.

    Non-five-minute gaps are retained and become period boundaries. Invalid or
    duplicate/reversed timestamps are errors, because their chronology is ambiguous.
    """
    required = ("time_local", "case_id", *INPUT_COLUMNS, *CPU_COLUMNS)
    missing = sorted(set(required).difference(raw.columns))
    if missing:
        raise DatasetValidationError("Missing preprocessing columns: " + ", ".join(missing))
    actual_cpu = {column for column in raw if CPU_TEMPERATURE_PATTERN.fullmatch(column)}
    if not raw.columns.is_unique or actual_cpu != EXPECTED_CPU_COLUMNS:
        raise DatasetValidationError("Preprocessing requires unique columns and exactly the 18 expected CPUs.")
    columns = [*required, *([WORKLOAD_COLUMN] if WORKLOAD_COLUMN in raw else [])]
    data = raw[columns].copy(deep=True).reset_index(drop=True)
    data["csv_record"] = np.arange(len(data)) + 2
    data["case_id_raw"] = data["case_id"]
    try:
        data["time_local"] = pd.to_datetime(
            data["time_local"], format="%Y-%m-%d %H:%M:%S", errors="raise"
        )
    except (ValueError, TypeError) as exc:
        raise DatasetValidationError("Preprocessing requires valid time_local timestamps.") from exc
    times = data["time_local"]
    if times.isna().any() or not times.is_monotonic_increasing or times.duplicated().any():
        raise DatasetValidationError("Preprocessing requires nonmissing, strictly increasing, unique timestamps.")
    for column in columns[1:]:
        data[column] = pd.to_numeric(data[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
    data["eligible_case"] = data["case_id"].isin(EXPECTED_CASE_IDS)
    data["complete_inputs"] = data[list(INPUT_COLUMNS)].notna().all(axis=1)
    data["cpu_temp_valid_count"] = data[list(CPU_COLUMNS)].notna().sum(axis=1)
    data["complete_cpu_temperatures"] = data["cpu_temp_valid_count"].eq(len(CPU_COLUMNS))
    data["cpu_temp_observed_max_C"] = data[list(CPU_COLUMNS)].max(axis=1)
    data["cpu_temp_max_C"] = data["cpu_temp_observed_max_C"].where(data["complete_cpu_temperatures"])
    return data


def detect_operating_periods(data: pd.DataFrame, config: PreprocessingConfig) -> pd.Series:
    """Detect persistent level changes, including transitions spread over several rows.

    Segmentation uses inputs and an optional workload marker, never temperatures.
    Two approximately constant comparison windows,
    separated by a transition guard, must establish a persistent level difference.
    Nearby detections are consolidated to one strongest boundary. Isolated spikes
    do not establish new levels. Missing temperatures do not create new identities.
    """
    values = data[list(INPUT_COLUMNS)].to_numpy(dtype=float)
    workload = (data[WORKLOAD_COLUMN].to_numpy(dtype=float)
                if config.use_workload_marker and WORKLOAD_COLUMN in data else None)
    cases = data["case_id"].to_numpy(dtype=float)
    eligible = (data["eligible_case"] & data["complete_inputs"]).to_numpy()
    delta = data["time_local"].diff().dt.total_seconds().to_numpy()
    ids = np.full(len(data), np.nan)
    period_id = 0
    block_start = None
    for row in range(len(data)):
        continuous = (row > 0 and eligible[row] and eligible[row - 1]
                      and cases[row] == cases[row - 1]
                      and delta[row] == config.sample_interval_minutes * 60)
        if block_start is not None and not continuous:
            cuts = _persistent_level_boundaries(values[block_start:row], config,
                                               None if workload is None else workload[block_start:row])
            edges = [block_start, *(block_start + cut for cut in cuts), row]
            for start, end in zip(edges[:-1], edges[1:]):
                period_id += 1
                ids[start:end] = period_id
            block_start = None
        if eligible[row] and block_start is None:
            block_start = row
    if block_start is not None:
        cuts = _persistent_level_boundaries(values[block_start:], config,
                                           None if workload is None else workload[block_start:])
        edges = [block_start, *(block_start + cut for cut in cuts), len(data)]
        for start, end in zip(edges[:-1], edges[1:]):
            period_id += 1
            ids[start:end] = period_id
    return pd.Series(ids, index=data.index, name="operating_period_id").astype("Int64")


def _input_range_limits(means: np.ndarray, config: PreprocessingConfig) -> np.ndarray:
    return np.array([
        config.cpu_power_range_abs_W + config.cpu_power_range_relative * abs(means[0]),
        config.inlet_temperature_range_C,
        config.fan_power_range_abs_raw + config.fan_power_range_relative * abs(means[2]),
    ])


def _persistent_level_boundaries(values: np.ndarray, config: PreprocessingConfig,
                                 workload: np.ndarray | None = None) -> list[int]:
    """Find confirmed new levels without assuming a case has a particular load count."""
    window = math.ceil(config.level_comparison_window_minutes / config.sample_interval_minutes) + 1
    guard = math.ceil(config.transition_guard_minutes / config.sample_interval_minutes)
    separation = math.ceil(config.minimum_change_separation_minutes / config.sample_interval_minutes)
    detections = []
    for cut in range(window + guard, len(values) - window + 1):
        before = values[cut - guard - window:cut - guard]
        after = values[cut:cut + window]
        # Both sides must represent a level, rather than an outlier or an ongoing ramp.
        if (np.any(np.ptp(before, axis=0) > _input_range_limits(before.mean(axis=0), config))
                or np.any(np.ptp(after, axis=0) > _input_range_limits(after.mean(axis=0), config))):
            continue
        previous, following = np.median(before, axis=0), np.median(after, axis=0)
        limits = np.array([
            config.cpu_power_step_abs_W + config.cpu_power_step_relative
            * max(abs(previous[0]), abs(following[0])),
            config.inlet_temperature_step_C, config.fan_power_step_raw,
        ])
        differences = np.abs(following - previous)
        scores = np.divide(differences, limits, out=np.zeros_like(differences), where=limits > 0)
        scores[(limits == 0) & (differences > 0)] = np.inf
        changed = bool(np.any(differences > limits))
        score = float(scores.max())
        if workload is not None:
            previous_workload = workload[cut - guard - window:cut - guard]
            following_workload = workload[cut:cut + window]
            if (np.isfinite(previous_workload).all() and np.isfinite(following_workload).all()
                    and np.ptp(previous_workload) <= config.workload_range_pct
                    and np.ptp(following_workload) <= config.workload_range_pct):
                change = abs(np.median(following_workload) - np.median(previous_workload))
                if change > config.workload_step_pct:
                    changed = True
                    score = max(score, change / config.workload_step_pct
                                if config.workload_step_pct else np.inf)
        if changed:
            detections.append((cut, score))
    if not detections:
        return []
    clusters = [[detections[0]]]
    for detection in detections[1:]:
        if detection[0] - clusters[-1][-1][0] < separation:
            clusters[-1].append(detection)
        else:
            clusters.append([detection])
    # Highest normalized change wins; equal evidence uses earliest confirmed new level.
    return [max(cluster, key=lambda item: (item[1], -item[0]))[0] for cluster in clusters]


def stability_metrics(inputs: np.ndarray, temperatures: np.ndarray, minutes: np.ndarray,
                      config: PreprocessingConfig, *, local_window: bool = False) -> dict:
    """Check all three inputs and all 18 sensors; drift is an OLS slope in C/min."""
    result = {"input_stable": False, "temperature_stable": False,
              "cpu_power_range_W": np.nan, "inlet_temperature_range_C": np.nan,
              "fan_power_range_raw": np.nan, "max_cpu_temperature_std_C": np.nan,
              "max_cpu_temperature_range_C": np.nan,
              "max_abs_cpu_temperature_drift_C_per_minute": np.nan}
    if len(minutes) < 2 or not np.isfinite(inputs).all() or not np.isfinite(temperatures).all():
        return result
    input_ranges = np.ptp(inputs, axis=0)
    means = np.mean(inputs, axis=0)
    limits = _input_range_limits(means, config)
    centered_time = minutes - minutes.mean()
    slopes = centered_time @ temperatures / np.sum(centered_time ** 2)
    std = np.std(temperatures, axis=0, ddof=1)
    ranges = np.ptp(temperatures, axis=0)
    drift_limit = (config.cpu_temperature_window_drift_C_per_minute if local_window
                   else config.cpu_temperature_drift_C_per_minute)
    result.update({
        "input_stable": bool(np.all(input_ranges <= limits)),
        "temperature_stable": bool(
            np.max(std) <= config.cpu_temperature_std_C
            and np.max(ranges) <= config.cpu_temperature_range_C
            and np.max(np.abs(slopes)) <= drift_limit),
        "cpu_power_range_W": float(input_ranges[0]),
        "inlet_temperature_range_C": float(input_ranges[1]),
        "fan_power_range_raw": float(input_ranges[2]),
        "max_cpu_temperature_std_C": float(np.max(std)),
        "max_cpu_temperature_range_C": float(np.max(ranges)),
        "max_abs_cpu_temperature_drift_C_per_minute": float(np.max(np.abs(slopes))),
    })
    return result


def select_steady_interval(period: pd.DataFrame, config: PreprocessingConfig):
    """Return the longest admissible interval, with earliest start breaking ties.

    All samples must be complete and consecutive. Both every contained sliding
    window and the full interval must pass. At most one observation is returned
    per candidate, even if multiple disjoint stable stretches are present.
    """
    inputs = period[list(INPUT_COLUMNS)].to_numpy(dtype=float)
    temperatures = period[list(CPU_COLUMNS)].to_numpy(dtype=float)
    minutes = ((period["time_local"] - period["time_local"].iloc[0]).dt.total_seconds()
               .to_numpy() / 60)
    window_samples = math.ceil(config.stability_window_minutes / config.sample_interval_minutes) + 1
    dwell_samples = math.ceil(config.minimum_dwell_minutes / config.sample_interval_minutes) + 1
    window_records = []
    for end in range(len(period)):
        if end + 1 < window_samples:
            window_records.append(stability_metrics(inputs[:0], temperatures[:0], minutes[:0], config))
        else:
            start = end + 1 - window_samples
            window_records.append(stability_metrics(inputs[start:end + 1],
                                                    temperatures[start:end + 1],
                                                    minutes[start:end + 1], config, local_window=True))
    windows = pd.DataFrame(window_records, index=period.index)
    good = (windows["input_stable"] & windows["temperature_stable"]).to_numpy()
    bad_prefix = np.concatenate(([0], np.cumsum(~good)))
    first = int(np.searchsorted(minutes, config.initial_settling_minutes))
    if len(period) - first < dwell_samples:
        return None, windows, "insufficient_post_settling_dwell"
    for length in range(len(period) - first, dwell_samples - 1, -1):
        for start in range(first, len(period) - length + 1):
            end = start + length
            # Windows ending before start + window_samples - 1 are outside this interval.
            if bad_prefix[end] != bad_prefix[start + window_samples - 1]:
                continue
            metrics = stability_metrics(inputs[start:end], temperatures[start:end], minutes[start:end], config)
            if metrics["input_stable"] and metrics["temperature_stable"]:
                return period.iloc[start:end], windows, "accepted"
    complete = period["complete_cpu_temperatures"].to_numpy()[first:]
    longest_complete = 0
    run = 0
    for value in complete:
        run = run + 1 if value else 0
        longest_complete = max(longest_complete, run)
    if longest_complete < dwell_samples:
        reason = "no_contiguous_complete_sensor_dwell"
    elif not good[first + window_samples - 1:].any():
        reason = "no_stable_window"
    else:
        reason = "no_interval_meeting_full_stability"
    return None, windows, reason


def aggregate_observation(accepted: pd.DataFrame, period_id: int, observation_id: int,
                          config: PreprocessingConfig) -> dict:
    """Target = max over CPUs of each CPU's period mean, never mean(row maxima)."""
    means = accepted[list(CPU_COLUMNS)].mean()
    temperatures = accepted[list(CPU_COLUMNS)].to_numpy(dtype=float)
    minutes = ((accepted["time_local"] - accepted["time_local"].iloc[0]).dt.total_seconds()
               .to_numpy() / 60)
    centered = minutes - minutes.mean()
    drifts = centered @ temperatures / np.sum(centered ** 2)
    metrics = stability_metrics(accepted[list(INPUT_COLUMNS)].to_numpy(), temperatures, minutes, config)
    return {
        "observation_id": f"ss_{observation_id:04d}", "operating_period_id": period_id,
        "case_id": int(accepted["case_id"].iloc[0]),
        "start_time": accepted["time_local"].iloc[0], "end_time": accepted["time_local"].iloc[-1],
        "duration_minutes": float(minutes[-1]), "sample_count": len(accepted),
        **accepted[list(INPUT_COLUMNS)].mean().to_dict(), **means.to_dict(),
        TARGET_COLUMN: float(means.max()), "hottest_cpu": means.idxmax(),
        "mean_instantaneous_cpu_max_C": float(accepted[list(CPU_COLUMNS)].max(axis=1).mean()),
        **{key: metrics[key] for key in (
            "max_cpu_temperature_std_C", "max_cpu_temperature_range_C",
            "max_abs_cpu_temperature_drift_C_per_minute")},
        **{f"{column}__std": float(temperatures[:, index].std(ddof=1))
           for index, column in enumerate(CPU_COLUMNS)},
        **{f"{column}__drift_C_per_minute": float(drifts[index])
           for index, column in enumerate(CPU_COLUMNS)},
    }


def extract_steady_states(raw: pd.DataFrame,
                          config: PreprocessingConfig = DEFAULT_PREPROCESSING_CONFIG) -> PreprocessingResult:
    """Extract one observation per accepted continuous input period without raw writes."""
    data = prepare_measurements(raw)
    data["operating_period_id"] = detect_operating_periods(data, config)
    data["selection_status"] = "rejected_unstable_or_unselected"
    data.loc[data["case_id_raw"].isna(), "selection_status"] = "excluded_unlabeled_transition"
    data.loc[data["case_id_raw"].notna() & ~data["eligible_case"], "selection_status"] = "excluded_case"
    data.loc[data["eligible_case"] & ~data["complete_inputs"], "selection_status"] = "excluded_invalid_input"
    data["observation_id"] = ""
    data["window_input_stable"] = False
    data["window_temperature_stable"] = False
    for column in ("max_cpu_temperature_std_C", "max_cpu_temperature_range_C",
                   "max_abs_cpu_temperature_drift_C_per_minute"):
        data[f"window_{column}"] = np.nan
    observations, periods = [], []
    for period_id, period in data.dropna(subset=["operating_period_id"]).groupby("operating_period_id"):
        accepted, windows, reason = select_steady_interval(period, config)
        data.loc[period.index, "window_input_stable"] = windows["input_stable"]
        data.loc[period.index, "window_temperature_stable"] = windows["temperature_stable"]
        for column in ("max_cpu_temperature_std_C", "max_cpu_temperature_range_C",
                       "max_abs_cpu_temperature_drift_C_per_minute"):
            data.loc[period.index, f"window_{column}"] = windows[column]
        elapsed = (period["time_local"] - period["time_local"].iloc[0]).dt.total_seconds() / 60
        data.loc[period.index[elapsed.lt(config.initial_settling_minutes)], "selection_status"] = "discarded_initial_settling"
        incomplete = period.index[~period["complete_cpu_temperatures"]]
        data.loc[incomplete, "selection_status"] = "excluded_incomplete_cpu_temperatures"
        record = {
            "operating_period_id": int(period_id), "case_id": int(period["case_id"].iloc[0]),
            "candidate_start_time": period["time_local"].iloc[0],
            "candidate_end_time": period["time_local"].iloc[-1],
            "candidate_duration_minutes": float(elapsed.iloc[-1]),
            "candidate_sample_count": len(period),
            "post_settling_samples": int(elapsed.ge(config.initial_settling_minutes).sum()),
            "incomplete_cpu_sensor_rows": len(incomplete),
            "status": "accepted" if accepted is not None else "rejected", "reason": reason,
            "accepted_sample_count": 0,
        }
        if accepted is not None:
            observation = aggregate_observation(accepted, int(period_id), len(observations) + 1, config)
            observations.append(observation)
            data.loc[accepted.index, "selection_status"] = "accepted"
            data.loc[accepted.index, "observation_id"] = observation["observation_id"]
            record.update({
                "accepted_start_time": observation["start_time"],
                "accepted_end_time": observation["end_time"],
                "accepted_sample_count": observation["sample_count"],
                "accepted_duration_minutes": observation["duration_minutes"],
                **stability_metrics(accepted[list(INPUT_COLUMNS)].to_numpy(),
                                    accepted[list(CPU_COLUMNS)].to_numpy(),
                                    ((accepted["time_local"] - accepted["time_local"].iloc[0])
                                     .dt.total_seconds().to_numpy() / 60), config),
            })
        periods.append(record)
    observation_table = pd.DataFrame(observations, columns=OBSERVATION_COLUMNS)
    period_table = pd.DataFrame(periods, columns=PERIOD_COLUMNS)
    counts = []
    for case in sorted(EXPECTED_CASE_IDS):
        candidate_mask = period_table["case_id"].eq(case)
        accepted = observation_table.loc[observation_table["case_id"].eq(case)]
        counts.append({
            "case_id": case, "labeled_rows": int(data["case_id"].eq(case).sum()),
            "candidate_operating_periods": int(candidate_mask.sum()),
            "accepted_operating_periods": len(accepted),
            "rejected_operating_periods": int(candidate_mask.sum()) - len(accepted),
            "accepted_samples": int(accepted["sample_count"].sum()),
        })
    return PreprocessingResult(observation_table, period_table, data, pd.DataFrame(counts))


def run_preprocess(data_path: str | Path = DEFAULT_DATA_PATH, *,
                   output: str | Path = "data/processed/steady_state.csv",
                   diagnostics: str | Path = "results/preprocessing",
                   config: PreprocessingConfig = DEFAULT_PREPROCESSING_CONFIG) -> PreprocessingResult:
    """Write the extracted dataset, effective settings, selection diagnostics, and figures."""
    data_path, output, diagnostics = Path(data_path), Path(output), Path(diagnostics)
    raw_directory = data_path.resolve().parent
    if output.resolve().is_relative_to(raw_directory) or diagnostics.resolve().is_relative_to(raw_directory):
        raise DatasetValidationError("Preprocessing outputs must be outside the raw input directory.")
    if output.resolve() == diagnostics.resolve() or diagnostics.resolve().is_relative_to(output.resolve()):
        raise DatasetValidationError("The output CSV and diagnostics directory must have separate paths.")
    raw = load_dataset(data_path)
    result = extract_steady_states(raw, config)
    output.parent.mkdir(parents=True, exist_ok=True)
    diagnostics.mkdir(parents=True, exist_ok=True)
    result.observations.to_csv(output, index=False, float_format="%.12g")
    result.periods.to_csv(diagnostics / "period_diagnostics.csv", index=False, float_format="%.12g")
    result.rows.to_csv(diagnostics / "row_diagnostics.csv", index=False, float_format="%.12g")
    result.case_counts.to_csv(diagnostics / "case_counts.csv", index=False)
    manifest = {
        "source": str(data_path), "source_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "output": str(output), "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "config": asdict(config), "python_version": platform.python_version(),
        "versions": {name: version(name) for name in ("thermal-twin", "numpy", "pandas", "matplotlib")},
        "target": "max over 18 CPUs of their interval-average temperatures",
        "incomplete_sensor_policy": "exclude; never bridge missing readings",
        "candidate_policy": "one longest admissible interval per input period; earliest-start tie break",
        "segmentation": "persistent input/workload level changes; no target period count",
        "auxiliary_workload_column": (WORKLOAD_COLUMN if config.use_workload_marker
                                      and WORKLOAD_COLUMN in raw else None),
        "pce_input_columns": list(INPUT_COLUMNS),
        "duration_convention": (f"end minus start; N regularly spaced samples span "
                                f"(N-1)*{config.sample_interval_minutes:g} minutes"),
        "fan_power_unit": "unverified; no conversion", "dp_used": False,
    }
    (diagnostics / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_diagnostics_report(result, config, output, diagnostics)
    from thermal_twin.preprocessing_plots import plot_selection
    plot_selection(result, diagnostics / "figures")
    return result


def write_diagnostics_report(result, config, output, diagnostics):
    counts = result.case_counts
    count_lines = ["| Case | Candidate periods | Accepted observations | Rejected periods | Accepted samples |",
                   "| --- | --- | --- | --- | --- |"]
    for row in counts.itertuples():
        count_lines.append(f"| {row.case_id} | {row.candidate_operating_periods} | "
                           f"{row.accepted_operating_periods} | {row.rejected_operating_periods} | "
                           f"{row.accepted_samples} |")
    reasons = result.periods.loc[result.periods["status"].eq("rejected"), "reason"].value_counts()
    exclusions = result.rows["selection_status"].value_counts()
    report = f"""# Steady-state preprocessing diagnostics

Output: `{output}`. Accepted operating observations: **{len(result.observations)}**.

{chr(10).join(count_lines)}

## Selection algorithm

1. Retain only case IDs 1-5 with finite values for all three inputs. Unlabeled rows,
   invalid labels, and missing/invalid inputs are excluded and break continuity.
2. Break continuity on case changes, excluded rows, or any interval other than
   {config.sample_interval_minutes:g} minutes. Within each continuous block, compare
   median input levels in two {config.level_comparison_window_minutes:g}-minute windows,
   separated by a {config.transition_guard_minutes:g}-minute transition guard. Both
   comparison windows must have approximately constant inputs. Sustained level
   differences define new candidates, including ramps whose individual steps are small.
   Nearby detections less than {config.minimum_change_separation_minutes:g} minutes
   apart are consolidated to the strongest change, with earliest-start tie breaking.
   Isolated spikes do not establish new operating levels. No required number of
   periods or workload percentages is hardcoded.
   If enabled and present, `{WORKLOAD_COLUMN}` supplies additional workload-change
   evidence. It is a segmentation marker only, never a PCE input or a temperature
   target. Missing marker values fall back to input-level evidence. Values above
   100 are retained without clipping or claiming calibrated workload percentages.
   No time sorting, interpolation, resampling, or missing-sensor imputation is performed.
   DP is not used; segmentation never examines CPU temperatures.
3. Discard the first {config.initial_settling_minutes:g} minutes after each candidate starts.
4. Require at least {config.minimum_dwell_minutes:g} minutes of retained consecutive,
   sensor-complete data AFTER that discard. Duration is end minus start, so seven
   five-minute samples span 30 minutes, rather than 35.
5. Check every CPU's sample standard deviation, peak-to-peak range, and absolute
   linear drift, plus peak-to-peak ranges of every input. These checks must pass
   both in every contained {config.stability_window_minutes:g}-minute sliding window
   and over the entire retained interval. Gradual drift cannot pass by chaining
   individually similar neighboring observations. Missing sensors break valid windows.
6. Select the longest passing interval per candidate period; equal lengths select
   the earliest start. Other stable fragments of that same period are not emitted
   as additional training rows. Overlapping stability windows are diagnostic only.

## Effective thresholds

All defaults and validation rules live in `configs/preprocessing_config.py`.
The exact effective values, including CLI overrides, are saved in `manifest.json`.

```json
{json.dumps(asdict(config), indent=2)}
```

Differences between CPU median levels use absolute + relative *
max(abs(previous level), abs(following level)).
Input range limits use absolute + relative * abs(interval mean). Inlet and fan
step limits are absolute. Fan power remains an **unverified-unit raw signal**;
these tolerances do not imply watts or kilowatts. All 18 CPU sensors must be finite.
Temperature checks are per sensor, not just checks of the hottest CPU.
The rolling drift limit ({config.cpu_temperature_window_drift_C_per_minute:g} C/min)
allows short-window apparent slopes from one-degree sensor steps. The full-interval
limit remains stricter ({config.cpu_temperature_drift_C_per_minute:g} C/min).
Local jitter tolerance never substitutes for the full-interval drift check.
The default 30-minute thermal window reduces sensitivity to short-window sensor
quantization; the default per-CPU standard-deviation limit is 1 C, rather than
requiring an almost constant quantized reading. The 3 C temperature-range limit,
0.03 C/min full-period drift limit, 20-minute initial discard, 30-minute retained
dwell, and complete-18-sensor requirement remain in force. Defaults describe
stationary measured fluctuations and must still be reviewed as heuristics, not
as a calibrated proof of physical equilibrium or a way to obtain a desired count.

## Aggregation and target

Each output row averages the three inputs and each of the 18 CPU temperatures over
the SAME retained timestamps. Original input and CPU column names contain these
period means. `{TARGET_COLUMN}` is the **maximum of the 18 CPU means**.
It is not the time average of instantaneous system maxima; the latter is retained
only as a diagnostic column. Per-CPU standard deviations and drifts, maximum sensor
variability, timestamps, sample count, case, and candidate identity are recorded.

## Sample accounting

{chr(10).join(f'- {name}: {count} rows' for name, count in exclusions.items())}

Rejected candidate reasons:

{chr(10).join(f'- {name}: {count} periods' for name, count in reasons.items()) or '- None'}

`row_diagnostics.csv` accounts for every original CSV row, including source record
number, raw case label, complete-sensor flags, rolling checks, and final selection.
`period_diagnostics.csv` records every candidate, acceptance or rejection reason,
candidate and retained bounds, and full-interval stability metrics for accepted data.
`figures/` contains an overview and a figure for each present case in PNG and PDF,
showing accepted, rejected, discarded-settling, and excluded measurements on the
original time series. Gray crosses flag available-only temperature maxima when
some CPU readings are missing; they never contribute to accepted observations.

## Interpretation and limits

These are nonoverlapping operating-period observations, NOT a proof of statistical
independence. Successive periods can share thermal history, hardware, controls,
and measurement bias; later validation must still respect case/time grouping.
The counts above must not be read as independent random experimental replicates.
Missing inputs can fragment a physical run; candidate IDs and rejected fragments
are retained for review. Short physical plateaus may not provide enough evidence
for two-sided change detection or the required settling and dwell intervals.
Repeated operating conditions are
not merged across interruptions or cases.

The defaults are reproducible heuristics, not externally calibrated equilibrium
thresholds. They establish observed stability at five-minute resolution, not a
physical proof of equilibrium. The source does not specify whether five-minute
values were sampled or averaged. In particular, slow drift below configured
limits and sensor quantization can remain. No predictive models were fitted.
"""
    (diagnostics / "report.md").write_text(report, encoding="utf-8")
