"""Validate the dataset contract and reject common corruptions."""

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from configs.data_config import INPUT_COLUMNS
from thermal_twin.data import (
    DatasetValidationError,
    inspect_dataset,
    load_dataset,
    validate_dataset,
)


def test_valid_data_is_not_modified(valid_frame):
    before = valid_frame.copy(deep=True)
    report = validate_dataset(valid_frame)
    assert (report.rows, report.columns) == (1333, 219)
    assert set(report.case_counts) == {1, 2, 3, 4, 5}
    assert sum(report.case_counts.values()) + report.transition_rows == 1333
    assert report.transition_rows > 0
    assert len(report.cpu_temperature_columns) == 18
    pd.testing.assert_frame_equal(valid_frame, before)


@pytest.mark.parametrize("column", ["time_local", "case_id", *INPUT_COLUMNS])
def test_missing_required_column(valid_frame, column):
    with pytest.raises(DatasetValidationError, match=f"Missing required columns: {column}"):
        validate_dataset(valid_frame.drop(columns=column))


@pytest.mark.parametrize("axis", ["rows", "columns"])
def test_wrong_original_dimensions(valid_frame, axis):
    frame = valid_frame.iloc[:-1] if axis == "rows" else valid_frame.drop(columns="other_0")
    with pytest.raises(DatasetValidationError, match="1333 rows and 219 columns"):
        validate_dataset(frame)


@pytest.mark.parametrize("replacement", ["cpu_temp_C__mean", "cpu_temp_C__srv10_cpu1"])
def test_individual_cpu_columns_required(valid_frame, replacement):
    frame = valid_frame.rename(columns={"cpu_temp_C__srv1_cpu1": replacement})
    with pytest.raises(DatasetValidationError, match="exactly 18 individual CPU"):
        validate_dataset(frame)


def test_extra_cpu_column(valid_frame):
    valid_frame = valid_frame.rename(columns={"other_0": "cpu_temp_C__srv10_cpu1"})
    with pytest.raises(DatasetValidationError, match="found 19"):
        validate_dataset(valid_frame)


@pytest.mark.parametrize("bad_id", [0, 6, 1.5, "unknown"])
def test_invalid_case_id(valid_frame, bad_id):
    valid_frame["case_id"] = valid_frame["case_id"].astype(object)
    valid_frame.loc[1, "case_id"] = bad_id
    with pytest.raises(DatasetValidationError, match="case IDs|case_id"):
        validate_dataset(valid_frame)


def test_missing_experimental_case(valid_frame):
    valid_frame.loc[valid_frame["case_id"].eq(5), "case_id"] = 4
    with pytest.raises(DatasetValidationError, match="five experimental case IDs"):
        validate_dataset(valid_frame)


def test_transition_rows_required(valid_frame):
    valid_frame["case_id"] = valid_frame["case_id"].fillna(1)
    with pytest.raises(DatasetValidationError, match="unlabeled transition"):
        validate_dataset(valid_frame)


@pytest.mark.parametrize(
    ("timestamp", "message"),
    [
        ("not-a-time", "valid timestamps"),
        (None, "missing timestamps"),
        ("2024-10-31 10:00:00", "strictly increasing"),
        ("2024-10-31 09:55:00", "strictly increasing"),
        ("2024-10-31 10:06:00", "five-minute"),
    ],
)
def test_invalid_timestamps(valid_frame, timestamp, message):
    valid_frame.loc[1, "time_local"] = timestamp
    with pytest.raises(DatasetValidationError, match=message):
        validate_dataset(valid_frame)


def test_missing_file(tmp_path):
    with pytest.raises(DatasetValidationError, match="Dataset file not found"):
        inspect_dataset(tmp_path / "missing.csv")


@pytest.mark.parametrize(
    ("contents", "message"),
    [("", "empty"), ("a,a\n1,2\n", "duplicate"), ("a,b\n1\n", "fields")],
)
def test_malformed_csv(tmp_path, contents, message):
    path = tmp_path / "invalid.csv"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(DatasetValidationError, match=message):
        load_dataset(path)


def test_csv_round_trip_keeps_transition_rows(valid_frame, tmp_path):
    path = tmp_path / "synthetic.csv"
    valid_frame.to_csv(path, index=False)
    before = path.read_bytes()
    report = inspect_dataset(path)
    assert report.transition_rows == int(valid_frame["case_id"].isna().sum())
    assert path.read_bytes() == before


def test_original_dataset_is_valid_and_unchanged():
    path = Path(__file__).resolve().parents[1] / "data/raw/ocp_air_cooling_5min.csv"
    if not path.is_file():
        pytest.skip("Original HEATWISE dataset is not available in this checkout")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    report = inspect_dataset(path)
    assert report.case_counts == {1: 249, 2: 304, 3: 237, 4: 309, 5: 209}
    assert report.transition_rows == 25
    assert str(report.start_time) == "2024-10-31 10:00:00"
    assert str(report.end_time) == "2024-11-05 01:00:00"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
