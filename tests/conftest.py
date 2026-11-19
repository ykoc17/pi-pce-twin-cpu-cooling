"""Synthetic full-shape data keep unit tests independent of raw measurements."""

import numpy as np
import pandas as pd
import pytest

from thermal_twin.data import EXPECTED_CPU_COLUMNS, EXPECTED_SHAPE, INPUT_COLUMNS


@pytest.fixture
def valid_frame():
    rows, columns = EXPECTED_SHAPE
    values = {
        "time_local": pd.date_range("2024-10-31 10:00:00", periods=rows, freq="5min")
        .strftime("%Y-%m-%d %H:%M:%S"),
        "case_id": np.resize([np.nan, 1, 2, 3, 4, 5], rows),
        **{column: np.ones(rows) for column in INPUT_COLUMNS},
        **{column: np.full(rows, 40.0) for column in sorted(EXPECTED_CPU_COLUMNS)},
    }
    values.update({f"other_{i}": np.zeros(rows) for i in range(columns - len(values))})
    return pd.DataFrame(values)
