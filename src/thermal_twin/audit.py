"""Descriptive, read-only analysis of HEATWISE air-cooling experiments."""

from __future__ import annotations

import hashlib
import json
import platform
from importlib.metadata import version
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pandas as pd

from configs.data_config import (
    DEFAULT_DATA_PATH, EXPECTED_CPU_COLUMNS, EXPECTED_SHAPE, INPUT_COLUMNS,
)
from thermal_twin.data import DatasetValidationError, load_dataset

AIR_FILE = DEFAULT_DATA_PATH.name
AIRFLOW = "tunnel_airflow_m3_h"
MAX_TEMP = "cpu_temp_max_C"
DOMAIN_COLUMNS = (INPUT_COLUMNS[1], INPUT_COLUMNS[2], INPUT_COLUMNS[0])
CPU_COLUMNS = tuple(sorted(EXPECTED_CPU_COLUMNS))
FAN_UNIT_NOTE = (
    "The unit of tunnel_fan_power_raw is unverified. DATA_DICTIONARY.csv lists "
    "unit='unverified' and low confidence. Values are retained on their raw scale; "
    "they are not converted to W or kW and cannot support calibrated fan-energy costs."
)


def read_metadata(path: str | Path, required: tuple[str, ...]) -> pd.DataFrame:
    """Read a metadata table with actionable file and schema errors."""
    path = Path(path)
    if not path.is_file():
        raise DatasetValidationError(f"Metadata file not found: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DatasetValidationError(f"Cannot read metadata {path}: {exc}") from exc
    missing = sorted(set(required).difference(frame.columns))
    if missing:
        raise DatasetValidationError(f"Missing columns in {path}: {', '.join(missing)}")
    return frame


def prepare_audit_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Create a numeric analysis copy; keep missing sensors and invalid times visible.

    Strict maxima require all 18 finite readings. An available-sensor maximum is
    also retained, explicitly named, and must not be mistaken for that strict maximum.
    """
    required = ("time_local", "case_id", *INPUT_COLUMNS, AIRFLOW, *CPU_COLUMNS)
    missing = sorted(set(required).difference(raw.columns))
    if missing:
        raise DatasetValidationError("Missing audit columns: " + ", ".join(missing))
    data = raw.copy(deep=True)
    data["is_transition"] = raw["case_id"].isna()
    data["time_local"] = pd.to_datetime(
        raw["time_local"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
    )
    for column in required[1:]:
        data[column] = pd.to_numeric(raw[column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
    temperatures = data[list(CPU_COLUMNS)]
    data["cpu_temp_valid_count"] = temperatures.notna().sum(axis=1)
    data["cpu_temp_observed_max_C"] = temperatures.max(axis=1)
    data[MAX_TEMP] = data["cpu_temp_observed_max_C"].where(
        data["cpu_temp_valid_count"].eq(18)
    )
    return data


def column_audit(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audit missingness and numerical ranges without imputing or dropping records."""
    missing_records, range_records = [], []
    for column in raw:
        original = raw[column]
        numeric = pd.to_numeric(original, errors="coerce")
        # All original HEATWISE columns except time_local have numerical semantics.
        is_numeric = column != "time_local"
        invalid = int((original.notna() & numeric.isna()).sum()) if is_numeric else 0
        nonfinite = int(np.isinf(numeric.to_numpy(dtype=float)).sum()) if is_numeric else 0
        missing_records.append({
            "column": column, "dtype": str(original.dtype),
            "missing_count": int(original.isna().sum()),
            "missing_fraction": float(original.isna().mean()),
            "invalid_numeric_count": invalid, "infinite_count": nonfinite,
            "unique_nonmissing": int(original.nunique()),
        })
        if is_numeric:
            finite = numeric.replace([np.inf, -np.inf], np.nan)
            record = {"column": column, **finite.describe(
                percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]
            ).to_dict()}
            record["unique_finite"] = int(finite.nunique())
            range_records.append(record)
    return pd.DataFrame(missing_records), pd.DataFrame(range_records)


def timestamp_audit(raw: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Report invalid, duplicate, reversed, and irregular intervals in source order."""
    times = pd.to_datetime(
        raw["time_local"], format="%Y-%m-%d %H:%M:%S", errors="coerce"
    )
    seconds = times.diff().dt.total_seconds()
    anomalies = pd.DataFrame({
        "csv_record": np.arange(len(raw)) + 2,
        "time_local_raw": raw["time_local"].to_numpy(),
        "previous_time_local_raw": raw["time_local"].shift().to_numpy(),
        "delta_seconds": seconds.to_numpy(),
    })
    bad_interval = seconds.ne(300)
    if len(bad_interval):
        bad_interval.iloc[0] = False
    anomalies = anomalies.loc[(times.isna() | bad_interval).to_numpy()]
    summary = {
        "min_timestamp": str(times.min()) if times.notna().any() else None,
        "max_timestamp": str(times.max()) if times.notna().any() else None,
        "missing_timestamps": int(raw["time_local"].isna().sum()),
        "invalid_nonmissing_timestamps": int((raw["time_local"].notna() & times.isna()).sum()),
        "duplicate_timestamps_after_first": int(times[times.notna()].duplicated().sum()),
        "nonpositive_intervals": int(seconds.le(0).sum()),
        "intervals_not_five_minutes": int(bad_interval.sum()),
        "strictly_increasing": bool(times.notna().all() and times.is_monotonic_increasing
                                    and not times.duplicated().any()),
        "all_intervals_five_minutes": bool(times.notna().all() and not bad_interval.any()),
    }
    return summary, anomalies


def summarize_cases(data: pd.DataFrame, definitions: pd.DataFrame) -> pd.DataFrame:
    """Cross-check curated case IDs against inclusive CASES.csv windows and counts."""
    cases = definitions.loc[
        definitions["file"].eq(AIR_FILE) & definitions["cooling_mode"].eq("air")
    ].copy()
    ids = pd.to_numeric(cases["case_id"], errors="coerce")
    if len(cases) != 5 or set(ids) != set(range(1, 6)):
        raise DatasetValidationError("CASES.csv must define exactly air-cooling cases 1-5.")
    for column in ("inlet_setpoint_C", "dp_setpoint_kPa", "n_samples"):
        cases[column] = pd.to_numeric(cases[column], errors="coerce")
    for column in ("start", "end"):
        cases[column] = pd.to_datetime(cases[column], errors="coerce")
    if cases[["start", "end", "inlet_setpoint_C", "dp_setpoint_kPa", "n_samples"]].isna().any().any():
        raise DatasetValidationError("CASES.csv has invalid air-cooling windows or numerical values.")
    if (cases["end"] < cases["start"]).any():
        raise DatasetValidationError("CASES.csv has a case end before its start.")
    records = []
    for _, row in cases.sort_values("case_id").iterrows():
        case_id = int(row["case_id"])
        labeled = data["case_id"].eq(case_id)
        window = data["time_local"].between(row["start"], row["end"], inclusive="both")
        record = row.to_dict()
        record.update({
            "case_id": case_id, "observed_samples": int(labeled.sum()),
            "sample_count_matches": bool(labeled.sum() == row["n_samples"]),
            "labeled_outside_window": int((labeled & ~window).sum()),
            "window_rows_with_wrong_or_missing_label": int((window & ~labeled).sum()),
            "incomplete_cpu_temperature_rows": int((labeled & data["cpu_temp_valid_count"].lt(18)).sum()),
        })
        for column in (*DOMAIN_COLUMNS, AIRFLOW, MAX_TEMP):
            values = data.loc[labeled, column]
            for name in ("min", "median", "max"):
                record[f"{column}__{name}"] = float(getattr(values, name)())
        records.append(record)
    return pd.DataFrame(records)


def grouped_statistics(data: pd.DataFrame) -> pd.DataFrame:
    """Summarize each input, airflow, all sensors, and strict maximum by case."""
    records = []
    for scope, subset in analysis_groups(data):
        for column in (*INPUT_COLUMNS, AIRFLOW, *CPU_COLUMNS, MAX_TEMP):
            values = subset[column]
            records.append({
                "scope": scope, "column": column, "rows": len(subset),
                "missing_count": int(values.isna().sum()),
                **values.describe(percentiles=[0.05, 0.5, 0.95]).to_dict(),
            })
    return pd.DataFrame(records)


def analysis_groups(data: pd.DataFrame):
    """Keep transitions separate and expose pooled versus within-case structure."""
    yield "all_rows", data
    yield "labeled_cases", data.loc[data["case_id"].isin(range(1, 6))]
    yield "transitions", data.loc[data["is_transition"]]
    for case in range(1, 6):
        yield f"case_{case}", data.loc[data["case_id"].eq(case)]


def dependency_statistics(data: pd.DataFrame) -> pd.DataFrame:
    """Pairwise-complete Pearson/Spearman summaries; no fitted relationships or p-values."""
    records = []
    pairs = [*combinations(INPUT_COLUMNS, 2), (INPUT_COLUMNS[2], AIRFLOW)]
    for scope, subset in analysis_groups(data):
        for first, second in pairs:
            complete = subset[[first, second]].dropna()
            adequate = len(complete) >= 3 and complete.nunique().min() > 1
            records.append({
                "scope": scope, "first": first, "second": second,
                "pairwise_complete_rows": len(complete),
                "excluded_rows": len(subset) - len(complete),
                "pearson_r": float(complete[first].corr(complete[second])) if adequate else np.nan,
                "spearman_rho": float(complete[first].corr(complete[second], method="spearman"))
                if adequate else np.nan,
            })
    return pd.DataFrame(records)


def coverage_grid(data: pd.DataFrame, bins: int = 5) -> pd.DataFrame:
    """Count observed labeled tuples in a fixed equal-width 3-D grid, including empty cells.

    Occupancy is resolution-dependent and does not establish interpolation safety.
    Axis order is inlet temperature, raw fan signal, then total CPU power.
    """
    if not isinstance(bins, int) or bins < 1:
        raise ValueError("Coverage bins must be a positive integer.")
    selected = data.loc[data["case_id"].isin(range(1, 6))]
    selected = selected.dropna(subset=list(DOMAIN_COLUMNS))
    if selected.empty:
        raise DatasetValidationError("No complete labeled input tuples available for coverage.")
    edges = [np.histogram_bin_edges(selected[column].to_numpy(), bins=bins)
             for column in DOMAIN_COLUMNS]
    counts, _ = np.histogramdd(selected[list(DOMAIN_COLUMNS)].to_numpy(), bins=edges)
    case_counts = {
        case: np.histogramdd(selected.loc[selected["case_id"].eq(case), list(DOMAIN_COLUMNS)]
                            .to_numpy(), bins=edges)[0]
        for case in range(1, 6)
    }
    records = []
    for indices in product(range(bins), repeat=3):
        record = {"observations": int(counts[indices])}
        for axis, column in enumerate(DOMAIN_COLUMNS):
            record[f"{column}__lower"] = float(edges[axis][indices[axis]])
            record[f"{column}__upper"] = float(edges[axis][indices[axis] + 1])
        record.update({f"case_{case}_rows": int(values[indices])
                       for case, values in case_counts.items()})
        records.append(record)
    return pd.DataFrame(records)


def _markdown_table(frame: pd.DataFrame) -> str:
    """Render a small report table without an optional tabulate dependency."""
    def cell(value):
        if isinstance(value, (float, np.floating)):
            return f"{value:.6g}"
        return str(value).replace("|", "\\|")
    rows = ["| " + " | ".join(map(str, frame.columns)) + " |",
            "| " + " | ".join("---" for _ in frame.columns) + " |"]
    rows += ["| " + " | ".join(map(cell, row)) + " |"
             for row in frame.itertuples(index=False, name=None)]
    return "\n".join(rows)


def write_report(output: Path, quality: dict, cases: pd.DataFrame, missing: pd.DataFrame,
                 statistics: pd.DataFrame, dependencies: pd.DataFrame, coverage: pd.DataFrame,
                 dictionary: pd.DataFrame) -> None:
    """Write an interpretation tied directly to saved descriptive statistics."""
    case_display = cases[["case_id", "inlet_setpoint_C", "dp_setpoint_kPa", "observed_samples",
                          "tunnel_fan_power_raw__min", "tunnel_fan_power_raw__max",
                          "total_cpu_power_W__min", "total_cpu_power_W__max"]]
    case_display = case_display.rename(columns={
        "inlet_setpoint_C": "Inlet setpoint (C)", "dp_setpoint_kPa": "DP setpoint (kPa)",
        "observed_samples": "Rows", "tunnel_fan_power_raw__min": "Fan raw min",
        "tunnel_fan_power_raw__max": "Fan raw max", "total_cpu_power_W__min": "CPU W min",
        "total_cpu_power_W__max": "CPU W max",
    })
    pooled = dependencies.loc[dependencies["scope"].eq("labeled_cases")]
    within_cpu_fan = dependencies.loc[
        dependencies["scope"].str.startswith("case_")
        & dependencies["first"].eq(INPUT_COLUMNS[0])
        & dependencies["second"].eq(INPUT_COLUMNS[2]), "pearson_r"
    ]
    fan_entry = dictionary.loc[dictionary["column"].eq(INPUT_COLUMNS[2])].iloc[0]
    global_stats = statistics.loc[statistics["scope"].eq("all_rows")]
    sensors = global_stats.loc[global_stats["column"].isin(CPU_COLUMNS)]
    max_row = global_stats.loc[global_stats["column"].eq(MAX_TEMP)].iloc[0]
    occupied = int(coverage["observations"].gt(0).sum())
    text = f"""# HEATWISE air-cooling exploratory audit

This is descriptive analysis of the original five-minute measurements. No predictive
models, surrogate fits, steady-state selection, or parameter optimization were performed.
See `manifest.json` for source SHA-256 hashes, package versions, and analysis settings.

## Data quality

- Original dimensions: {quality['rows']} rows by {quality['columns']} columns.
- Dimensions match the expected 1333 by 219 original CSV: {quality['original_shape_matches']}.
- Missing cells: {quality['missing_cells']}; unlabeled transitions: {quality['transition_rows']}.
- Exact duplicate rows after the first: {quality['exact_duplicate_rows_after_first']}.
- Repeated measurement vectors excluding time and case labels: {quality['repeated_measurement_vectors_after_first']}.
  Repeated measurements are descriptive counts, not automatically erroneous duplicates.
- Duplicate timestamps: {quality['duplicate_timestamps_after_first']}; invalid nonmissing
  timestamps: {quality['invalid_nonmissing_timestamps']}; missing timestamps: {quality['missing_timestamps']}.
- Strictly increasing timestamps: {quality['strictly_increasing']}; all intervals exactly
  five minutes: {quality['all_intervals_five_minutes']}. Source order is retained.
- Observed time span: {quality['min_timestamp']} to {quality['max_timestamp']}.
  Timestamps are source local time; the timezone is unspecified.
- Invalid case labels: {quality['invalid_case_label_rows']}; case labels disagreeing with
  CASES.csv windows: {quality['case_window_mismatch_rows']}; case sample counts match: {quality['case_counts_match']}.
- Nonfinite numerical values: {quality['infinite_values']}; invalid numerical cells:
  {quality['invalid_numeric_cells']}. Only the analysis copy treats these as missing.

Columns with missing source values:

{_markdown_table(missing.loc[missing['missing_count'].gt(0), ['column', 'missing_count']])}

`tables/missing_values.csv` covers every original column; `numerical_ranges.csv`
contains finite-value distributions, quantiles, and unique counts. Timestamp anomalies
and exact duplicate source records have separate tables, even when empty.

## Inputs and measured airflow

Finite-value ranges over all original rows, including transitions:

{_markdown_table(global_stats.loc[global_stats['column'].isin((*INPUT_COLUMNS, AIRFLOW)),
                                ['column', 'count', 'min', '50%', 'max']]
                .rename(columns={'50%': 'median'}))}

CPU power is the sum reported across the 18 CPUs, inlet temperature is the wind-tunnel
measurement before the servers, and airflow is the measured venturi-meter signal
in m3/h. Fan signal is on its original, unverified-unit scale. Tables retain
within-case distributions rather than treating these marginal ranges as a tested box.

## CPU temperatures

All 18 individual sensors are analyzed in `grouped_statistics.csv` and displayed in
`figures/all_cpu_temperatures.*`. Their overall observed range is
{sensors['min'].min():.3g}–{sensors['max'].max():.3g} C.
There are {quality['incomplete_cpu_temperature_rows']} timestamps with fewer than 18
finite CPU readings. `cpu_temp_max_C` is missing for those timestamps; it is the
confirmed maximum across all 18 CPUs only when all readings are available.
The strict maximum ranges from {max_row['min']:.3g} to {max_row['max']:.3g} C.
`cpu_temp_observed_max_C` separately records the maximum of available sensors,
which can understate the true system maximum. Neither missing readings nor maximum
temperatures are imputed. `tables/audit_timeseries.csv` retains every timestamp,
all CPU sensors, both maxima, input values, airflow, and the valid-sensor count.

## Five experimental cases and actual coverage

Only air-cooling entries for `ocp_air_cooling_5min.csv` are selected from CASES.csv;
hybrid cases 6–8 are excluded. Windows are inclusive and checked against existing labels.

{_markdown_table(case_display)}

The designed regimes are (inlet setpoint C, differential-pressure setpoint kPa):
(25, 2), (35, 4), (45, 6), (45, 8), and (45, 10). **Differential pressure is not
fan power.** Each case has a narrow observed raw fan-signal band and a broad CPU
load range. Dataset notes describe 100%, 75%, 50%, 25%, and idle stress-ng steps;
the audit does not infer exact load plateaus or equate CPU watts to those percentages.
Measured inlet temperatures vary within cases, including adjustment transients.
Case labels describe curated setpoint stretches and do not certify thermal equilibrium
after every load or setpoint change. Full measured ranges per case are in `case_summary.csv`.

The three PCE inputs were **not varied independently over a full factorial design**.
For example, the high-fan bands in cases 4–5 were tested around the 45 C inlet
setpoint, not at 25 or 35 C. Combining their fan values with a 25 C inlet creates
an untested operating regime even if every coordinate is inside its individual range.
CPU power was swept within the five case trajectories; a min/max box for a case
does not mean every continuous triple inside it was measured.

The five-bin-per-axis, equal-width measured-domain grid has {occupied} occupied
cells out of {len(coverage)}. Bin occupancy is resolution-dependent and is only a
coverage diagnostic, not a safety boundary or a measure of physical feasibility.
`observed_input_combinations.csv` lists actual complete labeled triples with counts;
`coverage_grid.csv` includes empty cells. Transition rows appear in time-series and
scatter plots, but are excluded from case-domain occupancy and the input correlation matrix.

## Input dependencies and measured airflow

Pairwise-complete correlations on labeled cases:

{_markdown_table(pooled[['first', 'second', 'pairwise_complete_rows', 'pearson_r', 'spearman_rho']])}

Pearson and Spearman correlations are also reported for all rows, transitions, and
each individual case in `input_dependencies.csv`. Sample counts accompany every
pair; undefined correlations for constant or insufficient data remain missing.
Pooled relationships mix setpoint changes with within-case behavior. Near-zero
correlation does not establish independence, and strong pooled correlation does
not establish causality. Time samples are serially dependent, so this report does
not attach independent-sample p-values to them.

Within-case CPU-power versus raw-fan Pearson correlations range from
{within_cpu_fan.min():.3f} to {within_cpu_fan.max():.3f}; compare these with the
pooled value in the table. For this dataset the pooled near-zero correlation
conceals strong negative dependencies within cases. The experiment's operating
sequence and controlled setpoints must be considered before assigning independent
input distributions. No causal interpretation or fitted fan law is claimed.

Fan signal versus measured venturi airflow is shown using observed points, by case,
with no fitted curve. It describes this experiment and does not calibrate fan energy.
Classical independent-input PCE and Sobol assumptions must be examined before
later analysis: drawing the three marginal distributions independently would
generate combinations absent from this experiment.

## Unverified fan-power unit

{FAN_UNIT_NOTE}

The selected dictionary entry gives unit `{fan_entry['unit']}`, confidence
`{fan_entry['confidence']}`, and description: {fan_entry['description']}
The original source-column name is retained in `tables/variable_metadata.csv`;
an original label containing W does not verify the curated signal's unit.
Every figure labels this axis as a raw fan signal with unverified unit.

## Why extrapolation is dangerous

The observed data support only the measured case trajectories and their sampled
load steps. Neither separate marginal limits, occupied coarse bins, nor even an
enclosing convex hull establish support for arbitrary joint operating points.
Gaps between inlet/fan regimes remain untested. An eventual surrogate could give
smooth, precise-looking predictions there without experimental validation;
temperature-limit and energy-optimization decisions would then be unsupported.
Further experiments or independently validated physics are needed to assess those
combinations. The five-minute acquisition/averaging convention is unspecified,
steady-state intervals still require a separate selection step, and all observed
temperature extrema are measurements rather than validated operating limits.

## Reproduction and outputs

Run `thermal-twin audit` from the repository root after installation. Tables are
CSV files, figures are 300-dpi PNG and PDF, and all outputs are under this directory.
No raw input is overwritten. Analysis uses numeric coercion only in memory,
pairwise-complete correlations, and complete labeled input tuples for coverage.
Figure colors consistently identify cases; gray points/background identify transitions
or missing sensor values as described in each figure. No random sampling is used.
"""
    (output / "report.md").write_text(text, encoding="utf-8")


def run_audit(data_path: str | Path = DEFAULT_DATA_PATH, *, cases_path: str | Path | None = None,
              dictionary_path: str | Path | None = None,
              output: str | Path = "results/audit") -> dict:
    """Create reproducible tables, publication figures, provenance, and interpretation."""
    data_path = Path(data_path)
    cases_path = Path(cases_path) if cases_path is not None else data_path.with_name("CASES.csv")
    dictionary_path = (Path(dictionary_path) if dictionary_path is not None
                       else data_path.with_name("DATA_DICTIONARY.csv"))
    output = Path(output)
    inputs = (data_path, cases_path, dictionary_path)
    # Avoid placing any generated artifacts in the directory containing raw inputs.
    if any(output.resolve().is_relative_to(path.resolve().parent) for path in inputs):
        raise DatasetValidationError("Audit output must be outside the raw input directories.")
    raw = load_dataset(data_path)
    data = prepare_audit_data(raw)
    definitions = read_metadata(cases_path, (
        "case_id", "cooling_mode", "file", "start", "end", "n_samples",
        "inlet_setpoint_C", "dp_setpoint_kPa",
    ))
    dictionary = read_metadata(dictionary_path, (
        "file", "column", "description", "unit", "confidence", "source_column_name",
    ))
    dictionary = dictionary.loc[dictionary["file"].eq(AIR_FILE)].copy()
    required_metadata = {*INPUT_COLUMNS, AIRFLOW, *CPU_COLUMNS}
    if not required_metadata.issubset(set(dictionary["column"])):
        raise DatasetValidationError("DATA_DICTIONARY.csv is missing audited variable entries.")
    if dictionary["column"].duplicated().any():
        raise DatasetValidationError("DATA_DICTIONARY.csv has duplicate air-cooling column entries.")
    cases = summarize_cases(data, definitions)
    missing, ranges = column_audit(raw)
    timestamp_quality, anomalies = timestamp_audit(raw)
    statistics = grouped_statistics(data)
    dependencies = dependency_statistics(data)
    coverage = coverage_grid(data)
    window_mismatch = pd.Series(False, index=data.index)
    for _, case in cases.iterrows():
        in_window = data["time_local"].between(case["start"], case["end"], inclusive="both")
        window_mismatch |= in_window.ne(data["case_id"].eq(case["case_id"]))
    quality = {
        "rows": len(raw), "columns": len(raw.columns),
        "original_shape_matches": raw.shape == EXPECTED_SHAPE,
        "missing_cells": int(raw.isna().sum().sum()),
        "transition_rows": int(raw["case_id"].isna().sum()),
        "invalid_case_label_rows": int((raw["case_id"].notna()
                                         & ~data["case_id"].isin(range(1, 6))).sum()),
        "exact_duplicate_rows_after_first": int(raw.duplicated().sum()),
        "repeated_measurement_vectors_after_first": int(raw.drop(columns=["time_local", "case_id"])
                                                        .duplicated().sum()),
        "incomplete_cpu_temperature_rows": int(data["cpu_temp_valid_count"].lt(18).sum()),
        "infinite_values": int(missing["infinite_count"].sum()),
        "invalid_numeric_cells": int(missing["invalid_numeric_count"].sum()),
        "case_counts_match": bool(cases["sample_count_matches"].all()),
        "case_window_mismatch_rows": int(window_mismatch.sum()),
        **timestamp_quality,
    }
    tables = output / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    frames = {
        "missing_values": missing, "numerical_ranges": ranges, "case_summary": cases,
        "timestamp_anomalies": anomalies,
        "timestamp_intervals": pd.DataFrame({"delta_seconds": data["time_local"].diff()
                                             .iloc[1:].dt.total_seconds()})
        .value_counts(dropna=False).rename("count").reset_index(),
        "duplicate_rows": raw.loc[raw.duplicated(keep=False)].copy(deep=True).assign(
            csv_record=lambda frame: frame.index + 2),
        "grouped_statistics": statistics, "input_dependencies": dependencies,
        "coverage_grid": coverage, "variable_metadata": dictionary,
        "audit_timeseries": data[["time_local", "case_id", "is_transition", *INPUT_COLUMNS, AIRFLOW,
                                  *CPU_COLUMNS, "cpu_temp_valid_count",
                                  "cpu_temp_observed_max_C", MAX_TEMP]],
        "observed_input_combinations": data.loc[data["case_id"].isin(range(1, 6))]
        .groupby(["case_id", *DOMAIN_COLUMNS], dropna=True).size().rename("observations").reset_index(),
    }
    for name, frame in frames.items():
        frame.to_csv(tables / f"{name}.csv", index=False, float_format="%.10g")
    labeled = data.loc[data["case_id"].isin(range(1, 6)), list(INPUT_COLUMNS)]
    for method in ("pearson", "spearman"):
        labeled.corr(method=method).to_csv(tables / f"input_correlation_{method}.csv",
                                           index_label="input", float_format="%.10g")
    manifest = {
        "python_version": platform.python_version(),
        "sources": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                    for path in inputs],
        "versions": {name: version(name) for name in
                     ("thermal-twin", "numpy", "pandas", "scipy", "matplotlib")},
        "settings": {"coverage_bins_per_axis": 5, "figure_dpi": 300,
                     "maximum_requires_all_18_sensors": True,
                     "correlation_policy": "pairwise complete, separate pooled and within-case",
                     "fan_unit": "unverified", "random_sampling": False},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "quality_summary.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    from thermal_twin.audit_plots import create_figures
    create_figures(data, cases, output / "figures")
    write_report(output, quality, cases, missing, statistics, dependencies, coverage, dictionary)
    return quality
