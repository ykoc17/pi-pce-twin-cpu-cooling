"""Read-only inspection of the original HEATWISE air-cooling dataset."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from configs.data_config import (
    CPU_TEMPERATURE_PATTERN,
    DEFAULT_DATA_PATH,
    EXPECTED_CASE_IDS,
    EXPECTED_CPU_COLUMNS,
    EXPECTED_SHAPE,
    INPUT_COLUMNS,
)


class DatasetValidationError(ValueError):
    """The supplied CSV does not meet the original dataset contract."""


@dataclass(frozen=True)
class InspectionReport:
    """Validated dataset dimensions, experimental labels, and time coverage."""

    rows: int
    columns: int
    case_counts: dict[int, int]
    transition_rows: int
    cpu_temperature_columns: tuple[str, ...]
    start_time: pd.Timestamp
    end_time: pd.Timestamp


def load_dataset(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Read the original CSV, rejecting duplicate headers and malformed records.

    No rows or columns are dropped, sorted, imputed, or written to disk.
    Use :func:`validate_dataset` to check the experimental data contract.
    """
    path = Path(path)
    if not path.is_file():
        raise DatasetValidationError(
            f"Dataset file not found: {path}. Place the original HEATWISE CSV "
            "at this location or pass --data PATH."
        )
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, [])
            if not header:
                raise DatasetValidationError(f"Dataset CSV is empty: {path}.")
            if len(set(header)) != len(header):
                raise DatasetValidationError("CSV contains duplicate column names.")
            for record_number, record in enumerate(reader, start=2):
                if len(record) != len(header):
                    raise DatasetValidationError(
                        f"CSV record {record_number} has {len(record)} fields; "
                        f"expected {len(header)}."
                    )
            handle.seek(0)
            return pd.read_csv(handle)
    except (OSError, UnicodeError, csv.Error, pd.errors.ParserError) as exc:
        raise DatasetValidationError(f"Cannot read dataset {path}: {exc}") from exc


def validate_dataset(frame: pd.DataFrame) -> InspectionReport:
    """Validate the full original dataset without modifying the dataframe."""
    if not frame.columns.is_unique:
        raise DatasetValidationError("Dataset contains duplicate column names.")
    required = ("time_local", "case_id", *INPUT_COLUMNS)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise DatasetValidationError("Missing required columns: " + ", ".join(missing))

    cpu_columns = tuple(
        column for column in frame.columns
        if CPU_TEMPERATURE_PATTERN.fullmatch(column)
    )
    if len(cpu_columns) != 18 or set(cpu_columns) != EXPECTED_CPU_COLUMNS:
        missing_cpu = sorted(EXPECTED_CPU_COLUMNS.difference(cpu_columns))
        unexpected_cpu = sorted(set(cpu_columns).difference(EXPECTED_CPU_COLUMNS))
        raise DatasetValidationError(
            "Expected exactly 18 individual CPU temperature columns "
            "matching cpu_temp_C__srv*_cpu* (servers 1-9, CPUs 1-2); "
            f"found {len(cpu_columns)}. Missing: {missing_cpu}; "
            f"unexpected: {unexpected_cpu}."
        )

    if frame.shape != EXPECTED_SHAPE:
        raise DatasetValidationError(
            f"Expected exactly 1333 rows and 219 columns in the original CSV; "
            f"found {frame.shape[0]} rows and {frame.shape[1]} columns."
        )

    try:
        cases = pd.to_numeric(frame["case_id"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise DatasetValidationError(
            "case_id must contain only experimental IDs 1-5 or empty transition labels."
        ) from exc
    observed_cases = set(cases.dropna().unique())
    if observed_cases != EXPECTED_CASE_IDS:
        raise DatasetValidationError(
            "Expected exactly five experimental case IDs (1-5); "
            f"found {sorted(observed_cases)}."
        )
    transition_rows = int(cases.isna().sum())
    if transition_rows == 0:
        raise DatasetValidationError("Expected unlabeled transition rows (empty case_id).")

    try:
        times = pd.to_datetime(
            frame["time_local"], format="%Y-%m-%d %H:%M:%S", errors="raise"
        )
    except (ValueError, TypeError) as exc:
        raise DatasetValidationError(
            "time_local must contain valid timestamps in YYYY-MM-DD HH:MM:SS format."
        ) from exc
    if times.isna().any():
        raise DatasetValidationError("time_local contains missing timestamps.")
    if not times.is_monotonic_increasing or times.duplicated().any():
        raise DatasetValidationError(
            "time_local must be strictly increasing, with no duplicate timestamps."
        )
    if not times.diff().iloc[1:].dt.total_seconds().eq(300).all():
        raise DatasetValidationError(
            "time_local must have exactly five-minute timestamp spacing between every row."
        )

    return InspectionReport(
        rows=len(frame),
        columns=len(frame.columns),
        case_counts={case: int(cases.eq(case).sum()) for case in sorted(EXPECTED_CASE_IDS)},
        transition_rows=transition_rows,
        cpu_temperature_columns=cpu_columns,
        start_time=times.iloc[0],
        end_time=times.iloc[-1],
    )


def inspect_dataset(path: str | Path = DEFAULT_DATA_PATH) -> InspectionReport:
    """Load and validate a CSV without changing the original file."""
    return validate_dataset(load_dataset(path))
