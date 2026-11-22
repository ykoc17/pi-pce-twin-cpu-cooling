"""Assumed PCE reference inputs and optional, separately specified scenarios."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from importlib.metadata import version
from itertools import combinations
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

from configs.data_config import DEFAULT_DATA_PATH, EXPECTED_CASE_IDS, INPUT_COLUMNS
from configs.input_config import DEFAULT_INPUT_CONFIG
from thermal_twin.data import DatasetValidationError
from thermal_twin.input_models import create_reference_model, create_scenario_model, marginal_candidates

UNITS = ("W", "degC", "unverified raw signal")
SOURCES = {
    "package": "https://pypi.org/project/uqlab/0.800/",
    "documentation": "https://www.uqlab.com/#documentation",
    "citation": "Marelli and Sudret (2014), UQLab: A framework for uncertainty quantification in MATLAB.",
}


def _numeric_input(value):
    # Python's correctly rounded conversion preserves the CSV's floating-point
    # values without pandas' deprecated float_precision argument.
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def load_observations(path: Path, config=DEFAULT_INPUT_CONFIG) -> pd.DataFrame:
    """Read period means, never raw five-minute rows or duration-weighted samples."""
    if not path.is_file():
        raise DatasetValidationError(f"Steady-state observations not found: {path}. Run thermal-twin preprocess first.")
    try:
        data = pd.read_csv(path, converters={column: _numeric_input for column in INPUT_COLUMNS})
    except (UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise DatasetValidationError(f"Cannot read steady-state observations {path}: {exc}") from exc
    required = ("case_id", "operating_period_id", "start_time", "end_time", *INPUT_COLUMNS)
    missing = sorted(set(required).difference(data.columns))
    if missing:
        raise DatasetValidationError("Missing processed-data columns: " + ", ".join(missing))
    if len(data) != config.expected_observations:
        raise DatasetValidationError(
            f"Expected {config.expected_observations} accepted operating observations; found {len(data)}. "
            "Review preprocessing and configs/input_config.py before changing the reference domain."
        )
    for column in ("case_id", "operating_period_id", *INPUT_COLUMNS):
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if not np.isfinite(data[column].to_numpy(dtype=float)).all():
            raise DatasetValidationError(f"Processed input {column} must contain only finite numbers; no rows are dropped.")
    if set(data["case_id"]) != EXPECTED_CASE_IDS:
        raise DatasetValidationError("Processed observations must contain exactly cases 1-5, without transitions.")
    ids = data["operating_period_id"]
    if ids.duplicated().any() or (ids <= 0).any() or (ids % 1 != 0).any():
        raise DatasetValidationError("Each processed row must have a unique positive integer operating_period_id.")
    for column in ("start_time", "end_time"):
        data[column] = pd.to_datetime(data[column], errors="coerce")
        if data[column].isna().any():
            raise DatasetValidationError(f"Processed {column} contains missing or invalid timestamps.")
    if (data["end_time"] <= data["start_time"]).any():
        raise DatasetValidationError("Every processed interval must end after it starts.")
    if not data["start_time"].is_monotonic_increasing or (
        data["start_time"].iloc[1:].to_numpy() <= data["end_time"].iloc[:-1].to_numpy()
    ).any():
        raise DatasetValidationError("Processed intervals must be ordered and nonoverlapping.")
    return data


def uniform_parameters(data: pd.DataFrame) -> list[dict]:
    """Use exact unweighted observed extrema; do not round, pad or fit bounds."""
    parameters = []
    for column, unit in zip(INPUT_COLUMNS, UNITS):
        values = data[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or not len(values):
            raise ValueError(f"Finite observations are required for {column}.")
        lower, upper = float(values.min()), float(values.max())
        marginal_candidates(lower, upper)  # validates nondegenerate support
        parameters.append({
            "input": column, "distribution": "Uniform", "lower": lower, "upper": upper,
            "unit": unit, "observations": len(values), "unique_values": int(np.unique(values).size),
            "reference_mean": (lower + upper) / 2,
            "reference_std": (upper - lower) / np.sqrt(12),
            "bound_origin": "exact min/max of accepted operating-period means",
        })
    return parameters


def marginal_diagnostics(data: pd.DataFrame, parameters: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Descriptive QQ/CDF distances only; iid goodness-of-fit p-values are invalid."""
    records, quantiles = [], []
    for parameter in parameters:
        column = parameter["input"]
        values = np.sort(data[column].to_numpy(dtype=float))
        n = len(values)
        lower, upper = parameter["lower"], parameter["upper"]
        cdf = (values - lower) / (upper - lower)
        probabilities = (np.arange(n) + 0.5) / n
        theoretical = lower + probabilities * (upper - lower)
        records.append({
            "input": column, "n": n, "unique_values": np.unique(values).size,
            "tied_observations_beyond_first": n - np.unique(values).size,
            "experimental_mean": float(values.mean()),
            "experimental_std": float(values.std(ddof=1)),
            "reference_mean": parameter["reference_mean"], "reference_std": parameter["reference_std"],
            "descriptive_cdf_distance": float(max(
                np.max(np.arange(1, n + 1) / n - cdf), np.max(cdf - np.arange(n) / n),
            )),
            "qq_rmse_in_input_units": float(np.sqrt(np.mean((values - theoretical) ** 2))),
            "interpretation": "sampling-design mismatch, not a physical-distribution goodness-of-fit test",
            "p_value": "not applicable: controlled design, grouped observations, data-selected bounds",
        })
        quantiles.extend({"input": column, "plotting_probability": float(p),
                          "uniform_quantile": float(q), "observed_order_statistic": float(v)}
                         for p, q, v in zip(probabilities, theoretical, values))
    return pd.DataFrame(records), pd.DataFrame(quantiles)


def dependency_diagnostics(data: pd.DataFrame) -> pd.DataFrame:
    """Pooled, within-case and leave-one-case-out scores; no independence test."""
    groups = [("all_accepted", data)]
    groups += [(f"case_{case}", data.loc[data["case_id"].eq(case)]) for case in sorted(EXPECTED_CASE_IDS)]
    groups += [(f"without_case_{case}", data.loc[data["case_id"].ne(case)])
               for case in sorted(EXPECTED_CASE_IDS)]
    records = []
    for scope, frame in groups:
        for first, second in combinations(INPUT_COLUMNS, 2):
            record = {"scope": scope, "first": first, "second": second, "n": len(frame)}
            for method in ("pearson", "spearman", "kendall"):
                if len(frame) < 3 or min(frame[first].nunique(), frame[second].nunique()) < 2:
                    record[method] = None
                else:
                    record[method] = float(frame[[first, second]].corr(method=method).iloc[0, 1])
            records.append(record)
    return pd.DataFrame(records)


def dependence_assessment(data: pd.DataFrame) -> dict:
    """Scientific refusal to infer an operating law from the controlled design."""
    return {
        "estimation_status": "not_estimated_from_HEATWISE",
        "n_observations": len(data),
        "case_counts": {str(int(k)): int(v) for k, v in data["case_id"].value_counts().sort_index().items()},
        "reasons": [
            "Only 19 selected periods from five controlled experimental cases; iid operational sampling is not established.",
            "Inlet and fan settings were coupled by the case design; observed correlation describes that design.",
            "Inlet values cluster near three setpoints, with ties and gaps; a smooth Gaussian copula is not established.",
            "Unequal accepted counts per case are selection outcomes, not operating-scenario probabilities.",
            "A nonsingular empirical correlation would not establish statistical reliability or Gaussian-copula adequacy.",
        ],
        "scenario_policy": "Only an explicitly supplied latent-normal correlation matrix creates model B; no automatic fit or repair.",
        "gaussian_copula_assumption": "Uniform marginal CDFs transformed to correlated Gaussian scores; Gaussian dependence is assumed, not demonstrated.",
        "endpoint_policy": "Exact uniform endpoints have infinite normal scores; forward Nataf rejects endpoints rather than clipping them.",
        "sobol_policy": "Classical coefficient-based Sobol decomposition applies to A's independent reference measure. Do not reuse it for B's physical inputs. Indices in B's independent latent coordinates describe those coordinates.",
    }


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_inputs(data_path: Path, output: Path, scenario_path: Path | None = None,
               config=DEFAULT_INPUT_CONFIG) -> dict:
    """Save separate models, reproducible diagnostics and publication figures."""
    data_path, output = Path(data_path), Path(output)
    protected = [data_path] + ([Path(scenario_path)] if scenario_path else [])
    if output.resolve().is_relative_to(DEFAULT_DATA_PATH.resolve().parent) or any(
        path.resolve().is_relative_to(output.resolve()) for path in protected
    ):
        raise DatasetValidationError("Input-model output must be outside raw data and must not contain source files.")
    data = load_observations(data_path, config)
    try:
        parameters = uniform_parameters(data)
        reference = create_reference_model(parameters)
        scenario = None
        dependent = None
        if scenario_path:
            try:
                scenario = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid scenario JSON: {exc}") from exc
            if not isinstance(scenario, dict):
                raise ValueError("Scenario JSON must contain an object.")
            dependent = create_scenario_model(reference, scenario)
    except (ValueError, TypeError) as exc:
        raise DatasetValidationError(str(exc)) from exc

    diagnostics, qq = marginal_diagnostics(data, parameters)
    dependencies = dependency_diagnostics(data)
    assessment = dependence_assessment(data)
    # Common independent normal draws allow a direct A/B comparison without
    # altering NumPy's process-wide RNG or pretending these are new experiments.
    normals = np.random.default_rng(config.seed).standard_normal((config.diagnostic_samples, 3))
    reference_samples = reference.from_independent_normals(normals)
    scenario_samples = dependent.from_independent_normals(normals) if dependent else None
    scenario_record = {
        "concept": "B_optional_dependent_operating_scenario",
        "status": "user_specified_not_fitted" if dependent else "not_requested",
        "estimation": assessment,
    }
    if dependent:
        correlation = np.asarray(scenario["gaussian_correlation"])
        recovered = dependent.to_independent_normals(scenario_samples)
        scenario_record.update({
            "scenario": scenario, "uqlab_options": dependent.options,
            "matrix_eigenvalues": np.linalg.eigvalsh(correlation).tolist(),
            "matrix_condition_number": float(np.linalg.cond(correlation)),
            "inverse_then_forward_max_abs_normal_error": float(np.max(np.abs(recovered - normals))),
            "sample_physical_pearson": np.corrcoef(scenario_samples, rowvar=False).tolist(),
            "implied_population_uniform_pearson_and_spearman": (
                6 / np.pi * np.arcsin(correlation / 2)
            ).tolist(),
            "validation_status": "Numerical checks only; scenario probabilities and physical coverage are not validated.",
        })

    figures, tables = output / "figures", output / "tables"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(parameters).to_csv(tables / "distribution_parameters.csv", index=False, float_format="%.17g")
    diagnostics.to_csv(tables / "marginal_diagnostics.csv", index=False)
    qq.to_csv(tables / "qq_quantiles.csv", index=False)
    dependencies.to_csv(tables / "input_dependencies.csv", index=False)
    data.groupby("case_id")[list(INPUT_COLUMNS)].agg(["count", "min", "max"]).to_csv(tables / "case_spans.csv")
    pd.DataFrame(reference_samples, columns=INPUT_COLUMNS).to_csv(tables / "reference_samples.csv", index=False)
    if dependent:
        pd.DataFrame(scenario_samples, columns=INPUT_COLUMNS).to_csv(tables / "scenario_samples.csv", index=False)
    elif (tables / "scenario_samples.csv").exists():
        # Remove only this command's obsolete derived artifact on a rerun.
        (tables / "scenario_samples.csv").unlink()
    _write_json(output / "reference_model.json", {
        "concept": "A_assumed_independent_reference", "purpose": "Legendre PCE basis and hypothetical global UQ/Sobol studies",
        "uqlab_options": reference.options, "parameters": parameters,
        "standardization": "xi_i = 2*(x_i-lower_i)/(upper_i-lower_i)-1",
        "orthonormal_basis": "Products of sqrt(2*n+1)*P_n(xi_i), under the independent uniform reference measure",
        "physical_uncertainty_inferred": False, "joint_coverage_validated": False,
    })
    _write_json(output / "scenario_model.json", scenario_record)
    _write_json(output / "candidate_densities.json", {
        p["input"]: marginal_candidates(p["lower"], p["upper"]) for p in parameters
    })
    assumptions = {
        "experimental_sampling": "Each accepted period has equal descriptive weight; no weighting by duration or number of raw readings.",
        "reference_A": "All three uniform marginals are assumed independent. This is a chosen mathematical reference measure, not an empirical independence conclusion.",
        "bounds": "Exact extrema of the 19 period means, without rounding or padding. Data-dependent bounds are not physical or safety limits.",
        "candidate_densities": "Uniform selected by instruction; symmetric triangular and Beta(2,2) are fixed illustrative alternatives, not fitted or ranked.",
        "QQ_and_histograms": "Compare the experimental sampling pattern with a chosen reference; mismatches are expected. No iid GOF p-values, maximum likelihood, AIC or BIC.",
        "joint_coverage": "The reference box includes untested combinations, including low inlet temperature with high fan signal. A Gaussian copula also assigns mass in untested gaps; it is not a coverage boundary.",
        "physical_uncertainty": "Input variability, sensor uncertainty, surrogate error and uncertainty in fitted coefficients are different. No physical uncertainty law is inferred.",
        "scenario_B": assessment,
        "fan_unit": "tunnel_fan_power_raw has unverified units; no W/kW conversion.",
        "scope": "Input probability models and diagnostics only; no predictive PCE or temperature model, propagated output UQ or Sobol indices have been fitted/computed.",
    }
    _write_json(output / "assumptions.json", assumptions)
    from thermal_twin.inputs_plots import plot_input_diagnostics
    plot_input_diagnostics(data, parameters, qq, reference_samples, scenario_samples, figures, config)
    manifest = {
        "source": str(data_path), "source_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "observations": len(data), "input_order": list(INPUT_COLUMNS), "config": asdict(config),
        "scenario_source": str(scenario_path) if scenario_path else None,
        "scenario_sha256": hashlib.sha256(Path(scenario_path).read_bytes()).hexdigest() if scenario_path else None,
        "python": platform.python_version(),
        "versions": {name: version(name) for name in ("thermal-twin", "uqlab", "numpy", "pandas", "scipy", "matplotlib")},
        "backend": "Official ETH UQLab.py, local execution; no cloud credentials or uploads",
        "sources": SOURCES,
    }
    _write_json(output / "manifest.json", manifest)
    _write_report(output, parameters, dependencies, assessment, scenario_record, manifest)
    return {"parameters": parameters, "scenario": scenario_record, "observations": len(data)}


def _write_report(output, parameters, dependencies, assessment, scenario, manifest):
    rows = "\n".join(f"| {p['input']} | {p['lower']:.12g} | {p['upper']:.12g} | {p['unit']} |" for p in parameters)
    association = dependencies.loc[
        dependencies["scope"].eq("all_accepted") & dependencies["first"].eq(INPUT_COLUMNS[1])
        & dependencies["second"].eq(INPUT_COLUMNS[2])
    ].iloc[0]
    reasons = "\n".join("- " + reason for reason in assessment["reasons"])
    report = f"""# Input distributions: two separate probability-model concepts

Read **{manifest['observations']} accepted operating-period means** from `{manifest['source']}`.
Source SHA-256: `{manifest['source_sha256']}`. Backend: official local ETH UQLab.py {manifest['versions']['uqlab']}.

## A. Assumed independent reference distributions

| Input | Uniform lower bound | Uniform upper bound | Unit |
| --- | --- | --- | --- |
{rows}

The JSON/CSV parameters retain full floating-point precision; the displayed table is rounded.
Bounds are exactly the smallest and largest accepted period means, without padding.
All three marginals are Uniform(a,b), with an explicitly independent copula.
Equal-width ranges receive equal reference weight. This is an assumption for a
Legendre PCE basis and hypothetical global UQ/Sobol analysis, not a conclusion
that the experimental inputs were independently sampled.
Map each input to xi=2*(x-a)/(b-a)-1. Normalized Legendre polynomials
sqrt(2*n+1)*P_n(xi) form an orthonormal tensor basis under A's product measure.
Existing experimental observations need not be iid uniform to use regression PCE;
coverage and regression conditioning still require review. No surrogate is fitted here.

## Histograms, candidate densities and QQ plots

Each period counts once; long periods do not get more descriptive weight.
The histogram describes the experiment and the preprocessing selection.
Uniform is the instructed reference. Symmetric triangular and Beta(2,2) curves
use the same bounds and fixed shape parameters, solely to illustrate other
possible assumptions. All candidate densities are evaluated with UQLab.py.
There is no density fitting, AIC/BIC ranking or claim of a best physical law.
QQ plots compare sorted observations with uniform quantiles at (i-0.5)/n.
Departures describe the controlled sampling pattern; they do not disprove a
deliberately chosen reference. CDF distances and QQ errors are descriptive;
no iid goodness-of-fit p-values are reported, including because bounds come from these data.

## B. Optional dependent operating-scenario model

Status: **{scenario['status']}**. HEATWISE estimation: **{assessment['estimation_status']}**.
The accepted observations have inlet/fan Pearson r={association['pearson']:.4f}
and Spearman rho={association['spearman']:.4f}. The earlier raw-data audit used
1,308 labeled time rows; those scores must not be confused with these 19 period means.
Pooled, within-case and leave-one-case-out scores are saved without independence p-values.

Why no dependent operating distribution is estimated:
{reasons}

An optional JSON scenario supplies a named **latent-normal correlation matrix**,
in the documented input order, with the same uniform marginals as A. This assumes
a **Gaussian copula**. A matrix's numerical validity does not establish physical
or statistical validity. No empirical correlation is silently substituted.
Matrices must be finite, symmetric, unit-diagonal, strictly positive definite and
well conditioned; invalid matrices are rejected without nearest-PD repair.
For uniform marginals, physical Pearson and Spearman correlations equal
(6/pi)*asin(R_ij/2) in the assumed population, not R_ij itself.

Forward Nataf: marginal CDF -> normal quantiles -> Cholesky whitening.
Inverse Nataf reverses these steps. Both use UQLab.py public APIs.
Exact uniform endpoints map to infinite normal scores, so forward transformation
rejects them rather than clipping the observed extrema. Extreme normal scores
that numerically saturate a uniform bound are also rejected. Interior round trips,
latent covariance and matrix rejection are covered by tests.
The optional samples are synthetic scenario illustrations, not new training data.
Classical independent-input Sobol formulas belong to A; do not apply them unchanged
to B's dependent physical inputs. Sobol indices of transformed independent normal
coordinates concern those coordinates, not the original three physical inputs.

## Interpretation and limits

The reference box includes untested combinations, such as 25 C inlet with high
fan signal. The cases do not fill that box. A Gaussian copula still places mass in
untested regions and does not enforce observed case trajectories or establish safe
operation. Neither concept validates extrapolation or optimization there.
Propagating assumed inputs would describe scenario variability, not by itself
sensor error, coefficient uncertainty or surrogate prediction error.
**The fan-signal unit is unverified**; no conversion to W or kW is made.
No predictive model, output uncertainty propagation or Sobol analysis is run in this step.

## Outputs and reproduction

`reference_model.json`, `scenario_model.json`, `candidate_densities.json`,
`assumptions.json` and `manifest.json` record models, assumptions and provenance.
`tables/` contains exact parameters, QQ points, descriptive diagnostics,
dependencies, case spans and reproducibly sampled reference/scenario inputs.
`figures/` contains publication PNG/PDF histograms, densities, QQ plots and joint comparisons.

```
thermal-twin inputs
thermal-twin inputs --scenario configs/input_scenario_example.json --output results/inputs_example_scenario
```

The example matrix is illustrative, not estimated from HEATWISE. The main default
report leaves B inactive. The local package needs Python >=3.12 and pandas >=3.0.3.
Sources: [official package]({SOURCES['package']}); [ETH documentation]({SOURCES['documentation']}).
"""
    (output / "report.md").write_text(report, encoding="utf-8")
