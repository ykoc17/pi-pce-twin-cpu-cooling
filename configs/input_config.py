"""Reproducible input-model settings; no distribution parameters are fitted."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_OBSERVATIONS_PATH = Path("data/processed/steady_state.csv")
DEFAULT_INPUTS_OUTPUT = Path("results/inputs")


@dataclass(frozen=True)
class InputConfig:
    expected_observations: int = 19
    histogram_bins: int = 6
    density_grid_points: int = 301
    diagnostic_samples: int = 2048
    seed: int = 20261122
    matrix_tolerance: float = 1e-10
    minimum_eigenvalue: float = 1e-8
    maximum_condition_number: float = 1e8


DEFAULT_INPUT_CONFIG = InputConfig()
