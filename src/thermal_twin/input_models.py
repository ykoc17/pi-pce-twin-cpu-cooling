"""ETH UQLab.py input objects and validated Gaussian-copula transformations.

Reference model A and optional scenario model B are separate objects. No inference
or nearest-positive-definite repair is requested from UQLab. Public APIs are
isolated here because the local Python port is currently an open beta.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import numpy as np
import uqlab

from configs.data_config import INPUT_COLUMNS
from configs.input_config import DEFAULT_INPUT_CONFIG


def marginal_candidates(lower: float, upper: float) -> dict[str, dict]:
    """Fixed illustrative densities; uniform alone is selected, no AIC/BIC fit."""
    if not np.isfinite([lower, upper]).all() or lower >= upper:
        raise ValueError("Uniform bounds must be finite with lower < upper.")
    return {
        "Uniform (selected)": {"Type": "Uniform", "Parameters": [lower, upper]},
        "Triangular (illustrative)": {
            "Type": "Triangular", "Parameters": [lower, upper, (lower + upper) / 2],
        },
        "Beta(2,2) (illustrative)": {"Type": "Beta", "Parameters": [2, 2, lower, upper]},
    }


def validate_correlation(matrix, config=DEFAULT_INPUT_CONFIG) -> np.ndarray:
    """Require a well-conditioned latent-normal correlation; never repair it."""
    try:
        correlation = np.asarray(matrix, dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError("Gaussian correlation must be a numerical 3 x 3 matrix.") from exc
    if correlation.shape != (3, 3) or not np.isfinite(correlation).all():
        raise ValueError("Gaussian correlation must be a finite 3 x 3 matrix.")
    if not np.allclose(correlation, correlation.T, rtol=0, atol=config.matrix_tolerance):
        raise ValueError("Gaussian correlation must be symmetric.")
    if not np.allclose(np.diag(correlation), 1, rtol=0, atol=config.matrix_tolerance):
        raise ValueError("Gaussian correlation must have a unit diagonal.")
    eigenvalues = np.linalg.eigvalsh(correlation)
    if eigenvalues.min() <= config.minimum_eigenvalue:
        raise ValueError("Gaussian correlation must be strictly positive definite and nonsingular.")
    if np.linalg.cond(correlation) >= config.maximum_condition_number:
        raise ValueError("Gaussian correlation is too ill-conditioned for a stable Nataf transform.")
    return correlation.copy()


@dataclass
class InputModel:
    """A specified probability measure, not an inferred physical uncertainty law."""

    options: dict
    uq_input: object

    @property
    def bounds(self) -> np.ndarray:
        return np.asarray([m["Parameters"] for m in self.options["Marginals"]], dtype=float)

    def standardized(self, values) -> np.ndarray:
        """Map bounded physical inputs to [-1,1] for a Legendre reference basis."""
        values = self._values(values)
        lower, upper = self.bounds.T
        if np.any((values < lower) | (values > upper)):
            raise ValueError("Input lies outside the specified uniform reference bounds.")
        return 2 * (values - lower) / (upper - lower) - 1

    @staticmethod
    def _values(values) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        if values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all():
            raise ValueError("Expected a finite (N, 3) array in the documented input order.")
        return values

    def to_independent_normals(self, physical) -> np.ndarray:
        """Forward Nataf: X -> Phi^-1(F(X)) -> independent standard normals.

        Exact uniform endpoints have infinite normal scores. Reject them instead
        of silently clipping data, changing bounds, or forcing finite scores.
        """
        physical = self._values(physical)
        lower, upper = self.bounds.T
        if np.any((physical <= lower) | (physical >= upper)):
            raise ValueError("Nataf requires strictly interior uniform inputs; endpoints map to infinity.")
        transformed = np.asarray(uqlab.natafTransform(
            physical, self.uq_input.Marginals, self.uq_input.Copula,
        ), dtype=float)
        if not np.isfinite(transformed).all():
            raise ValueError("Nataf normal scores are nonfinite; inputs are too close to a bound.")
        return transformed

    def from_independent_normals(self, normal) -> np.ndarray:
        """Inverse Nataf: independent normals -> correlated normals -> X."""
        normal = self._values(normal)
        physical = np.asarray(uqlab.invNatafTransform(
            normal, self.uq_input.Marginals, self.uq_input.Copula,
        ), dtype=float)
        lower, upper = self.bounds.T
        if not np.isfinite(physical).all() or np.any((physical <= lower) | (physical >= upper)):
            raise ValueError("Normal scores saturate uniform bounds numerically; use less extreme scores.")
        return physical


def create_reference_model(parameters: list[dict]) -> InputModel:
    """Create model A in the local official ETH Python port, without cloud calls."""
    if len(parameters) != 3 or [p["input"] for p in parameters] != list(INPUT_COLUMNS):
        raise ValueError("Parameters must follow the three configured PCE inputs in order.")
    options = {
        "Name": "A_independent_reference",
        "Marginals": [
            {"Name": p["input"], **marginal_candidates(p["lower"], p["upper"])["Uniform (selected)"]}
            for p in parameters
        ],
        "Copula": {"Type": "Independent"},
    }
    uqlab.cli("-nosplash")
    return InputModel(options, uqlab.createInput(deepcopy(options), "-private"))


def create_scenario_model(reference: InputModel, scenario: dict) -> InputModel:
    """Model B: user-specified Gaussian copula with the same uniform marginals.

    gaussian_correlation is the correlation of latent normal variables. It is
    not the Pearson correlation of the bounded physical inputs.
    """
    if scenario.get("input_order") != list(INPUT_COLUMNS):
        raise ValueError("Scenario input_order must match the three configured PCE inputs exactly.")
    if not isinstance(scenario.get("name"), str) or not scenario["name"].strip():
        raise ValueError("Scenario requires a nonempty name.")
    if not isinstance(scenario.get("description"), str) or not scenario["description"].strip():
        raise ValueError("Scenario requires a description explaining its assumptions.")
    matrix = validate_correlation(scenario.get("gaussian_correlation"))
    options = deepcopy(reference.options)
    options["Name"] = "B_" + scenario["name"]
    options["Copula"] = {"Type": "Gaussian", "Parameters": matrix.tolist()}
    return InputModel(options, uqlab.createInput(deepcopy(options), "-private"))


def candidate_densities(grid, lower: float, upper: float) -> dict[str, np.ndarray]:
    """Evaluate each fixed one-dimensional candidate through UQLab.py."""
    uqlab.cli("-nosplash")
    densities = {}
    for name, marginal in marginal_candidates(lower, upper).items():
        input_object = uqlab.createInput({"Marginals": [marginal]}, "-private")
        densities[name] = np.asarray(uqlab.evalPDF(np.asarray(grid)[:, None], input_object)).ravel()
    return densities
