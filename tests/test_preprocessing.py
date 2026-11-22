"""Synthetic traces establish selection behavior without learning from target data."""

from dataclasses import replace
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from configs.data_config import INPUT_COLUMNS, WORKLOAD_COLUMN
from configs.preprocessing_config import DEFAULT_PREPROCESSING_CONFIG, PreprocessingConfig
from thermal_twin.cli import main
from thermal_twin.data import DatasetValidationError
from thermal_twin.preprocessing import CPU_COLUMNS, TARGET_COLUMN, extract_steady_states


def trace(samples=30, case=1):
    return pd.DataFrame({
        "time_local": pd.date_range("2024-01-01", periods=samples, freq="5min").strftime("%Y-%m-%d %H:%M:%S"),
        "case_id": np.full(samples, case, dtype=float),
        INPUT_COLUMNS[0]: np.full(samples, 1000.0), INPUT_COLUMNS[1]: np.full(samples, 25.0),
        INPUT_COLUMNS[2]: np.full(samples, 0.2),
        **{column: np.full(samples, 60.0) for column in CPU_COLUMNS},
    })


def test_constant_trace_yields_one_period_after_discard_and_preserves_raw():
    raw = trace()
    before = raw.copy(deep=True)
    result = extract_steady_states(raw)
    assert len(result.observations) == len(result.periods) == 1
    observation = result.observations.iloc[0]
    assert observation["start_time"] == pd.Timestamp("2024-01-01 00:20:00")
    assert observation["sample_count"] == 26
    assert observation["duration_minutes"] == 125
    assert observation[TARGET_COLUMN] == 60
    assert observation["max_cpu_temperature_std_C"] == 0
    assert result.rows["selection_status"].eq("discarded_initial_settling").sum() == 4
    pd.testing.assert_frame_equal(raw, before)


def test_transient_must_finish_beyond_fixed_settling_interval():
    raw = trace()
    temperatures = np.maximum(100 - 4 * np.arange(len(raw)), 60)
    raw[list(CPU_COLUMNS)] = np.repeat(temperatures[:, None], len(CPU_COLUMNS), axis=1)
    result = extract_steady_states(raw)
    assert len(result.observations) == 1
    assert result.observations.iloc[0]["start_time"] == pd.Timestamp("2024-01-01 00:50:00")
    assert result.observations.iloc[0][TARGET_COLUMN] == 60


def test_persistent_small_drift_is_rejected_even_with_low_window_variance():
    raw = trace()
    temperature = 60 + 0.04 * np.arange(len(raw)) * 5
    raw[list(CPU_COLUMNS)] = np.repeat(temperature[:, None], len(CPU_COLUMNS), axis=1)
    result = extract_steady_states(raw)
    assert result.observations.empty
    assert result.periods.iloc[0]["reason"] == "no_interval_meeting_full_stability"
    assert result.rows["window_temperature_stable"].any()
    assert result.rows["window_max_cpu_temperature_std_C"].max() < 0.75


def test_noise_can_fail_stability_without_a_linear_drift():
    raw = trace()
    raw[CPU_COLUMNS[0]] = 60 + np.resize([-1.2, 1.2], len(raw))
    result = extract_steady_states(raw)
    assert result.observations.empty
    assert result.rows["window_max_abs_cpu_temperature_drift_C_per_minute"].max() == pytest.approx(0)


def test_quantized_stationary_trace_passes_local_jitter_and_global_drift_checks():
    raw = trace()
    raw[CPU_COLUMNS[0]] = np.resize([60.0, 60.0, 60.0, 61.0, 61.0, 61.0], len(raw))
    result = extract_steady_states(raw, replace(DEFAULT_PREPROCESSING_CONFIG, stability_window_minutes=20))
    assert len(result.observations) == 1
    assert result.rows["window_max_abs_cpu_temperature_drift_C_per_minute"].max() == pytest.approx(0.06)
    assert result.observations.iloc[0]["max_abs_cpu_temperature_drift_C_per_minute"] <= 0.03


def test_every_sensor_is_checked_not_only_instantaneous_maximum():
    raw = trace()
    raw[CPU_COLUMNS[0]] = 90
    raw[CPU_COLUMNS[1]] = 60 + 0.05 * np.arange(len(raw)) * 5
    result = extract_steady_states(raw)
    assert result.rows["cpu_temp_max_C"].eq(90).all()
    assert result.observations.empty


@pytest.mark.parametrize("column,second_level", [
    (INPUT_COLUMNS[0], 1300), (INPUT_COLUMNS[1], 35), (INPUT_COLUMNS[2], 0.35),
])
def test_input_steps_create_separate_dwell_periods(column, second_level):
    raw = trace(40)
    raw.loc[20:, column] = second_level
    result = extract_steady_states(raw)
    assert len(result.periods) == len(result.observations) == 2
    assert result.observations["operating_period_id"].is_unique
    assert result.observations.iloc[1]["start_time"] == pd.Timestamp("2024-01-01 02:00:00")


@pytest.mark.parametrize("column,levels", [
    (INPUT_COLUMNS[0], [1000, 1100, 1200, 1300]),
    (INPUT_COLUMNS[1], [25, 25.8, 26.6, 27.4]),
    (INPUT_COLUMNS[2], [0.20, 0.24, 0.28, 0.32]),
])
def test_gradual_input_transition_recovers_distinct_plateaus(column, levels):
    raw = trace(50)
    raw.loc[20:23, column] = levels
    raw.loc[24:, column] = levels[-1]
    # Require inlet plateaus tighter than each intermediate ramp step, so the
    # exact-level mean assertions below do not include admissible edge readings.
    config = replace(DEFAULT_PREPROCESSING_CONFIG, inlet_temperature_range_C=0.5)
    result = extract_steady_states(raw, config)
    assert len(result.periods) == len(result.observations) == 2
    assert result.observations.iloc[0][column] == pytest.approx(levels[0])
    assert result.observations.iloc[1][column] == pytest.approx(levels[-1])
    assert result.observations.iloc[1]["start_time"] >= pd.Timestamp("2024-01-01 01:55:00")


def test_isolated_input_spike_does_not_create_extra_operating_conditions():
    raw = trace(60)
    raw.loc[20, INPUT_COLUMNS[0]] = 1600
    result = extract_steady_states(raw)
    assert len(result.periods) == len(result.observations) == 1
    assert result.observations.iloc[0][INPUT_COLUMNS[0]] == 1000


def test_multiple_load_levels_are_not_capped_to_a_desired_count():
    raw = trace(100)
    for start, level in [(25, 1250), (50, 1500), (75, 1000)]:
        raw.loc[start:, INPUT_COLUMNS[0]] = level
    result = extract_steady_states(raw)
    assert len(result.observations) == 4
    assert result.observations[INPUT_COLUMNS[0]].tolist() == [1000, 1250, 1500, 1000]


def test_optional_workload_marker_separates_levels_with_nearly_equal_power():
    raw = trace(60)
    raw[WORKLOAD_COLUMN] = np.where(np.arange(len(raw)) < 30, 103.0, 77.0)
    result = extract_steady_states(raw)
    assert len(result.observations) == 2
    assert result.observations[INPUT_COLUMNS[0]].eq(1000).all()
    assert WORKLOAD_COLUMN not in result.observations.columns
    without_marker = extract_steady_states(raw, replace(DEFAULT_PREPROCESSING_CONFIG, use_workload_marker=False))
    assert len(without_marker.observations) == 1


def test_missing_workload_values_do_not_discard_valid_input_data():
    raw = trace()
    raw[WORKLOAD_COLUMN] = np.nan
    result = extract_steady_states(raw)
    assert len(result.observations) == 1


def test_segmentation_is_independent_of_cpu_temperature_values():
    raw = trace(60)
    raw.loc[30:, INPUT_COLUMNS[0]] = 1300
    before = extract_steady_states(raw).rows["operating_period_id"]
    raw.loc[:, list(CPU_COLUMNS)] = 100 + np.arange(len(raw))[:, None] * np.ones((1, len(CPU_COLUMNS)))
    after = extract_steady_states(raw).rows["operating_period_id"]
    pd.testing.assert_series_equal(before, after)


def test_slow_input_drift_does_not_pass_through_adjacent_similarity():
    raw = trace()
    raw[INPUT_COLUMNS[0]] += np.arange(len(raw)) * 10
    config = replace(DEFAULT_PREPROCESSING_CONFIG, cpu_power_range_abs_W=20, cpu_power_range_relative=0)
    result = extract_steady_states(raw, config)
    assert len(result.periods) == 1  # No artificial splitting on small adjacent changes.
    assert result.observations.empty


@pytest.mark.parametrize("boundary", ["gap", "unlabeled", "case_change", "missing_input"])
def test_discontinuities_are_never_bridged(boundary):
    raw = trace(40)
    if boundary == "gap":
        raw = raw.drop(index=20)
    elif boundary == "unlabeled":
        raw.loc[20, "case_id"] = np.nan
    elif boundary == "case_change":
        raw.loc[20:, "case_id"] = 2
    else:
        raw.loc[20, INPUT_COLUMNS[0]] = np.nan
    result = extract_steady_states(raw)
    assert len(result.observations) == 2
    for observation in result.observations.itertuples():
        assert not (observation.start_time < pd.Timestamp("2024-01-01 01:40:00") < observation.end_time)


def test_incomplete_sensors_break_stable_intervals_without_inflating_period_count():
    raw = trace(40)
    raw.loc[20, CPU_COLUMNS[0]] = np.nan
    result = extract_steady_states(raw)
    assert len(result.periods) == len(result.observations) == 1
    assert result.observations.iloc[0]["start_time"] == pd.Timestamp("2024-01-01 01:45:00")
    assert result.rows.loc[20, "selection_status"] == "excluded_incomplete_cpu_temperatures"
    assert result.rows.loc[result.rows["selection_status"].eq("accepted"), "cpu_temp_valid_count"].eq(18).all()


def test_all_incomplete_temperatures_reject_period():
    raw = trace()
    raw[CPU_COLUMNS[0]] = np.nan
    result = extract_steady_states(raw)
    assert result.observations.empty
    assert result.periods.iloc[0]["reason"] == "no_contiguous_complete_sensor_dwell"


def test_target_is_max_of_sensor_means_rather_than_mean_of_instantaneous_maxima():
    raw = trace(12)
    raw[list(CPU_COLUMNS)] = 38.0
    raw[CPU_COLUMNS[0]] = np.resize([39.0, 41.0], len(raw))
    raw[CPU_COLUMNS[1]] = np.resize([41.0, 39.0], len(raw))
    config = replace(DEFAULT_PREPROCESSING_CONFIG, cpu_temperature_std_C=1.2)
    observation = extract_steady_states(raw, config).observations.iloc[0]
    assert observation[TARGET_COLUMN] == 40
    assert observation[CPU_COLUMNS[0]] == observation[CPU_COLUMNS[1]] == 40
    assert observation["mean_instantaneous_cpu_max_C"] == 41


def test_minimum_dwell_is_elapsed_retained_time_and_is_configurable():
    assert extract_steady_states(trace(10)).observations.empty  # 25 retained minutes.
    assert len(extract_steady_states(trace(11)).observations) == 1  # Exactly 30 retained minutes.
    config = replace(DEFAULT_PREPROCESSING_CONFIG, minimum_dwell_minutes=45)
    assert extract_steady_states(trace(11), config).observations.empty


def test_global_input_range_is_checked_in_addition_to_windows():
    raw = trace(50)
    raw[INPUT_COLUMNS[0]] += np.arange(len(raw)) * 2
    config = replace(DEFAULT_PREPROCESSING_CONFIG, cpu_power_range_abs_W=30, cpu_power_range_relative=0)
    result = extract_steady_states(raw, config)
    assert len(result.observations) == 1
    assert result.periods.iloc[0]["cpu_power_range_W"] <= 30
    assert result.observations.iloc[0]["sample_count"] == 16
    assert result.observations.iloc[0]["start_time"] == pd.Timestamp("2024-01-01 00:20:00")
    assert result.observations.iloc[0][INPUT_COLUMNS[0]] == 1023


def test_global_temperature_variability_is_checked_beyond_local_windows():
    raw = trace()
    raw[CPU_COLUMNS[0]] += np.arange(len(raw)) * 0.1
    result = extract_steady_states(raw, replace(DEFAULT_PREPROCESSING_CONFIG, cpu_temperature_std_C=0.75))
    assert len(result.observations) == 1
    assert result.observations.iloc[0]["sample_count"] == 25
    assert result.observations.iloc[0]["max_cpu_temperature_std_C"] <= 0.75


def test_disjoint_stable_fragments_do_not_become_multiple_observations():
    raw = trace(60)
    raw.loc[25:34, CPU_COLUMNS[0]] = np.arange(10) * 2 + 60
    result = extract_steady_states(raw)
    assert len(result.periods) == len(result.observations) == 1


@pytest.mark.parametrize("case", [np.nan, 0, 6, 1.5])
def test_only_air_case_ids_are_used(case):
    result = extract_steady_states(trace(case=case))
    assert result.observations.empty
    assert result.periods.empty
    assert result.case_counts["accepted_operating_periods"].sum() == 0


@pytest.mark.parametrize("bad_time", ["invalid", None, "2024-01-01 00:00:00"])
def test_bad_chronology_is_a_clear_error(bad_time):
    raw = trace()
    raw.loc[1, "time_local"] = bad_time
    with pytest.raises(DatasetValidationError, match="timestamps"):
        extract_steady_states(raw)


@pytest.mark.parametrize("setting", [
    {"minimum_dwell_minutes": -1}, {"stability_window_minutes": 5},
    {"initial_settling_minutes": np.nan}, {"cpu_temperature_std_C": -0.1},
])
def test_invalid_config_is_rejected(setting):
    with pytest.raises(ValueError):
        PreprocessingConfig(**setting)


def test_preprocess_cli_outputs_provenance_and_reproducible_csv(tmp_path, capsys):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    source = raw_dir / "input.csv"
    trace(15).to_csv(source, index=False)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "processed/steady_state.csv"
    diagnostics = tmp_path / "diagnostics"
    args = ["preprocess", "--data", str(source), "--output", str(output),
            "--diagnostics", str(diagnostics), "--initial-settling-minutes", "10"]
    assert main(args) == 0
    assert "Saved 1 steady operating observations" in capsys.readouterr().out
    observations = pd.read_csv(output)
    assert observations.loc[0, "sample_count"] == 13
    manifest = json.loads((diagnostics / "manifest.json").read_text())
    assert manifest["config"]["initial_settling_minutes"] == 10
    assert manifest["source_sha256"] == before
    assert not manifest["dp_used"]
    assert manifest["pce_input_columns"] == list(INPUT_COLUMNS)
    assert manifest["auxiliary_workload_column"] is None
    assert len(pd.read_csv(diagnostics / "row_diagnostics.csv")) == 15
    assert len(list((diagnostics / "figures").glob("*.png"))) == 2
    assert len(list((diagnostics / "figures").glob("*.pdf"))) == 2
    assert "maximum of the 18 CPU means" in (diagnostics / "report.md").read_text()
    first = output.read_bytes()
    # Rerun the deterministic processing function, without rendering a second set of figures.
    again = extract_steady_states(pd.read_csv(source), replace(DEFAULT_PREPROCESSING_CONFIG,
                                                             initial_settling_minutes=10))
    assert first.replace(b"\r\n", b"\n") == again.observations.to_csv(
        index=False, float_format="%.12g", lineterminator="\n").encode("utf-8")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_cli_prevents_raw_output_overwrite(tmp_path, capsys):
    source = tmp_path / "raw/input.csv"
    assert main(["preprocess", "--data", str(source), "--output", str(source)]) == 1
    assert "outside the raw input directory" in capsys.readouterr().err
