"""Check audit processing, missing-sensor policy, metadata, and saved artifacts."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from thermal_twin.audit import (
    AIRFLOW, CPU_COLUMNS, DOMAIN_COLUMNS, MAX_TEMP, column_audit, coverage_grid,
    dependency_statistics, prepare_audit_data, run_audit, summarize_cases, timestamp_audit,
)
from thermal_twin.cli import main
from configs.data_config import INPUT_COLUMNS
from thermal_twin.data import DatasetValidationError


@pytest.fixture
def small_raw(valid_frame):
    raw = valid_frame.iloc[:12].copy()
    raw["case_id"] = [np.nan, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, np.nan]
    raw[INPUT_COLUMNS[0]] = np.arange(12) * 100 + 300.0
    raw[INPUT_COLUMNS[1]] = np.repeat([25.0, 35.0, 45.0], 4)
    raw[INPUT_COLUMNS[2]] = np.arange(12) * 0.02 + 0.1
    raw[AIRFLOW] = np.arange(12) * 10 + 170.0
    return raw


@pytest.fixture
def metadata(small_raw):
    definitions = pd.DataFrame([
        {"case_id": case, "cooling_mode": "air", "file": "ocp_air_cooling_5min.csv",
         "start": small_raw.loc[2 * case - 1, "time_local"],
         "end": small_raw.loc[2 * case, "time_local"], "n_samples": 2,
         "inlet_setpoint_C": [25, 35, 45, 45, 45][case - 1], "dp_setpoint_kPa": 2 * case}
        for case in range(1, 6)
    ])
    dictionary = pd.DataFrame([
        {"file": "ocp_air_cooling_5min.csv", "column": column, "description": column,
         "unit": "unverified" if column == INPUT_COLUMNS[2] else "test-unit",
         "confidence": "low" if column == INPUT_COLUMNS[2] else "high",
         "source_column_name": column}
        for column in (*INPUT_COLUMNS, AIRFLOW, *CPU_COLUMNS)
    ])
    return definitions, dictionary


def test_maximum_requires_all_18_finite_sensors_and_preserves_raw(small_raw):
    small_raw.loc[0, CPU_COLUMNS[0]] = 65
    small_raw.loc[1, CPU_COLUMNS[0]] = np.nan
    small_raw.loc[2, CPU_COLUMNS[0]] = np.inf
    small_raw.loc[3, list(CPU_COLUMNS)] = np.nan
    before = small_raw.copy(deep=True)
    data = prepare_audit_data(small_raw)
    assert data.loc[0, MAX_TEMP] == 65
    assert data.loc[1:3, MAX_TEMP].isna().all()
    assert data.loc[1, "cpu_temp_observed_max_C"] == 40
    assert data.loc[2, "cpu_temp_valid_count"] == 17
    assert pd.isna(data.loc[3, "cpu_temp_observed_max_C"])
    pd.testing.assert_frame_equal(small_raw, before)
    pd.testing.assert_series_equal(data[INPUT_COLUMNS[2]], small_raw[INPUT_COLUMNS[2]])


def test_missing_airflow_is_a_clear_error(small_raw):
    with pytest.raises(DatasetValidationError, match="Missing audit columns: tunnel_airflow"):
        prepare_audit_data(small_raw.drop(columns=AIRFLOW))


def test_missing_invalid_and_infinite_are_distinguished():
    raw = pd.DataFrame({"time_local": ["bad", None, "bad", "bad"],
                        "numeric": ["1", None, "broken", "inf"]})
    missing, ranges = column_audit(raw)
    record = missing.set_index("column").loc["numeric"]
    assert record["missing_count"] == 1
    assert record["invalid_numeric_count"] == 1
    assert record["infinite_count"] == 1
    assert ranges.iloc[0]["count"] == 1
    assert ranges.iloc[0]["min"] == ranges.iloc[0]["max"] == 1


def test_timestamp_audit_reports_defects_without_reordering():
    raw = pd.DataFrame({"time_local": [
        "2024-01-01 10:00:00", "2024-01-01 10:05:00", "2024-01-01 10:05:00",
        "2024-01-01 10:00:00", "2024-01-01 10:15:00", "invalid", None,
    ]})
    quality, anomalies = timestamp_audit(raw)
    assert quality["duplicate_timestamps_after_first"] == 2
    assert quality["nonpositive_intervals"] == 2
    assert quality["invalid_nonmissing_timestamps"] == 1
    assert quality["missing_timestamps"] == 1
    assert quality["intervals_not_five_minutes"] == 5
    assert not quality["strictly_increasing"]
    assert list(anomalies["csv_record"]) == [4, 5, 6, 7, 8]


def test_case_windows_are_inclusive_and_hybrid_cases_excluded(small_raw, metadata):
    definitions, _ = metadata
    hybrid = definitions.iloc[[0]].assign(case_id=6, cooling_mode="hybrid", file="hybrid.csv")
    summary = summarize_cases(prepare_audit_data(small_raw), pd.concat([definitions, hybrid]))
    assert summary["sample_count_matches"].all()
    assert summary["labeled_outside_window"].sum() == 0
    assert summary["window_rows_with_wrong_or_missing_label"].sum() == 0
    assert len(summary) == 5


def test_case_label_window_mismatch_is_reported(small_raw, metadata):
    definitions, _ = metadata
    small_raw.loc[1, "case_id"] = 2
    summary = summarize_cases(prepare_audit_data(small_raw), definitions)
    assert not summary["sample_count_matches"].all()
    assert summary["labeled_outside_window"].sum() == 1
    assert summary["window_rows_with_wrong_or_missing_label"].sum() == 1


def test_coverage_conserves_counts_excludes_transitions_and_keeps_empty_cells(small_raw):
    data = prepare_audit_data(small_raw)
    data.loc[2, DOMAIN_COLUMNS[0]] = np.nan
    grid = coverage_grid(data, bins=3)
    assert len(grid) == 27
    assert grid["observations"].sum() == 9
    assert (grid["observations"] == 0).any()
    assert grid[[f"case_{case}_rows" for case in range(1, 6)]].sum(axis=1).equals(
        grid["observations"])
    assert grid["case_1_rows"].sum() == 1
    # Maximum axis values must fall into the last bin, rather than being lost.
    assert grid["case_5_rows"].sum() == 2


def test_coverage_handles_constant_axis(small_raw):
    data = prepare_audit_data(small_raw)
    data[DOMAIN_COLUMNS[0]] = 25
    grid = coverage_grid(data, bins=2)
    assert grid["observations"].sum() == 10
    with pytest.raises(ValueError, match="positive integer"):
        coverage_grid(data, bins=0)


def test_dependencies_pairwise_complete_and_undefined_constants(small_raw):
    data = prepare_audit_data(small_raw)
    data.loc[1, INPUT_COLUMNS[0]] = np.nan
    data[INPUT_COLUMNS[1]] = 25
    summary = dependency_statistics(data)
    row = summary.loc[summary["scope"].eq("labeled_cases")
                      & summary["first"].eq(INPUT_COLUMNS[0])
                      & summary["second"].eq(INPUT_COLUMNS[2])].iloc[0]
    assert row["pairwise_complete_rows"] == 9
    assert row["excluded_rows"] == 1
    assert row["pearson_r"] == pytest.approx(1)
    assert row["spearman_rho"] == pytest.approx(1)
    assert summary.loc[summary["second"].eq(INPUT_COLUMNS[1]), "pearson_r"].isna().all()


def test_invalid_case_labels_are_not_reclassified_as_transitions(small_raw):
    small_raw["case_id"] = small_raw["case_id"].astype(object)
    small_raw.loc[1, "case_id"] = "unknown"
    data = prepare_audit_data(small_raw)
    assert not data.loc[1, "is_transition"]
    summary = dependency_statistics(data)
    assert summary.loc[summary["scope"].eq("transitions"), "pairwise_complete_rows"].eq(2).all()


def test_audit_end_to_end_cli_artifacts_and_provenance(small_raw, metadata, tmp_path, capsys):
    definitions, dictionary = metadata
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    path = raw_dir / "ocp_air_cooling_5min.csv"
    small_raw.to_csv(path, index=False)
    definitions.to_csv(raw_dir / "CASES.csv", index=False)
    dictionary.to_csv(raw_dir / "DATA_DICTIONARY.csv", index=False)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw_dir.iterdir()}
    output = tmp_path / "audit"
    assert main(["audit", "--data", str(path), "--output", str(output)]) == 0
    assert "unit of tunnel_fan_power_raw is unverified" in capsys.readouterr().out
    assert len(list((output / "figures").glob("*.png"))) == 6
    assert len(list((output / "figures").glob("*.pdf"))) == 6
    for path in (output / "figures").iterdir():
        assert path.stat().st_size > 1000
    manifest = json.loads((output / "manifest.json").read_text())
    assert {p["sha256"] for p in manifest["sources"]} == set(before.values())
    assert manifest["settings"]["fan_unit"] == "unverified"
    quality = json.loads((output / "quality_summary.json").read_text())
    assert quality["case_counts_match"]
    assert quality["transition_rows"] == 2
    assert quality["case_window_mismatch_rows"] == 0
    assert not quality["original_shape_matches"]  # Audit reports rather than hides defects.
    assert pd.read_csv(output / "tables/audit_timeseries.csv").shape[0] == 12
    assert pd.read_csv(output / "tables/observed_input_combinations.csv")["observations"].sum() == 10
    report = (output / "report.md").read_text(encoding="utf-8")
    assert "not varied independently" in report
    assert "unit of tunnel_fan_power_raw is unverified" in report
    assert "Why extrapolation is dangerous" in report
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw_dir.iterdir()}


def test_audit_rejects_output_inside_raw_directory(tmp_path):
    with pytest.raises(DatasetValidationError, match="outside the raw input"):
        run_audit(tmp_path / "raw/data.csv", output=tmp_path / "raw/audit")


def test_audit_missing_metadata_is_a_cli_error(small_raw, tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "data.csv"
    small_raw.to_csv(path, index=False)
    assert main(["audit", "--data", str(path), "--output", str(tmp_path / "audit")]) == 1
    assert "Metadata file not found" in capsys.readouterr().err
