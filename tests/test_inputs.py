"""Input-model assumptions, exact bounds, UQLab densities and Nataf numerics."""

from dataclasses import replace
import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from scipy.special import ndtr, ndtri
import uqlab

from configs.data_config import INPUT_COLUMNS
from configs.input_config import DEFAULT_INPUT_CONFIG
from thermal_twin.cli import main
from thermal_twin.data import DatasetValidationError
from thermal_twin.input_models import (
    candidate_densities, create_reference_model, create_scenario_model, validate_correlation,
)
from thermal_twin.inputs import (
    dependency_diagnostics, dependence_assessment, load_observations,
    marginal_diagnostics, run_inputs, uniform_parameters,
)


@pytest.fixture
def observations():
    count = 19
    start = pd.date_range("2024-01-01", periods=count, freq="2h")
    return pd.DataFrame({
        "operating_period_id": np.arange(1, count + 1),
        "case_id": np.repeat([1, 2, 3, 4, 5], [4, 4, 5, 4, 2]),
        "start_time": start, "end_time": start + pd.Timedelta(minutes=30),
        INPUT_COLUMNS[0]: np.linspace(384.735294117647, 1786.22580645161, count),
        INPUT_COLUMNS[1]: np.repeat([25.0, 35.0, 45.08, 45.0, 45.0], [4, 4, 5, 4, 2]),
        INPUT_COLUMNS[2]: np.linspace(0.121636363636, 0.730571428571, count),
    })


@pytest.fixture
def reference(observations):
    return create_reference_model(uniform_parameters(observations))


@pytest.fixture
def scenario():
    return {
        "name": "specified_test_scenario", "description": "Synthetic Gaussian-copula test, not an estimated law.",
        "input_order": list(INPUT_COLUMNS),
        "gaussian_correlation": [[1, 0.2, -0.1], [0.2, 1, 0.7], [-0.1, 0.7, 1]],
    }


def test_exact_unweighted_bounds_and_uniform_joint_pdf(observations, reference):
    parameters = uniform_parameters(observations)
    for i, parameter in enumerate(parameters):
        assert parameter["lower"] == observations[INPUT_COLUMNS[i]].min()
        assert parameter["upper"] == observations[INPUT_COLUMNS[i]].max()
        assert reference.uq_input.Marginals[i]["Type"].lower() == "uniform"
        assert reference.uq_input.Marginals[i]["Parameters"] == [parameter["lower"], parameter["upper"]]
    assert reference.uq_input.Copula[0]["Type"] == "Independent"
    midpoint = reference.bounds.mean(axis=1)[None, :]
    expected_density = 1 / np.prod(reference.bounds[:, 1] - reference.bounds[:, 0])
    assert np.asarray(uqlab.evalPDF(midpoint, reference.uq_input)).item() == pytest.approx(expected_density)
    np.testing.assert_allclose(reference.standardized(reference.bounds.T), [[-1] * 3, [1] * 3])
    np.testing.assert_allclose(reference.standardized(midpoint), 0, atol=1e-14)


def test_fixed_candidate_densities_integrate_to_one_and_remain_distinct():
    x = np.linspace(2.5, 7.1, 10001)
    densities = candidate_densities(x, x[0], x[-1])
    assert list(densities) == ["Uniform (selected)", "Triangular (illustrative)", "Beta(2,2) (illustrative)"]
    for name, density in densities.items():
        assert np.trapezoid(density, x) == pytest.approx(1, abs=1e-7), name
    assert densities["Uniform (selected)"][0] > 0
    assert densities["Beta(2,2) (illustrative)"][0] == 0


def test_uniform_reference_legendre_normalization():
    # Exact Gaussian quadrature verifies the stated convention under Uniform[-1,1].
    nodes, weights = np.polynomial.legendre.leggauss(6)
    basis = np.polynomial.legendre.legvander(nodes, 3) * np.sqrt(2 * np.arange(4) + 1)
    np.testing.assert_allclose(basis.T @ (weights[:, None] / 2 * basis), np.eye(4), atol=1e-14)


def test_dependent_transform_matches_analytic_cholesky_and_round_trips(reference, scenario):
    model = create_scenario_model(reference, scenario)
    normal = np.random.default_rng(42).normal(size=(200, 3))
    lower, upper = reference.bounds.T
    lower_cholesky = np.linalg.cholesky(scenario["gaussian_correlation"])
    expected = lower + (upper - lower) * ndtr(normal @ lower_cholesky.T)
    physical = model.from_independent_normals(normal)
    np.testing.assert_allclose(physical, expected, rtol=2e-14, atol=1e-12)
    np.testing.assert_allclose(model.to_independent_normals(physical), normal, rtol=1e-9, atol=1e-9)
    probabilities = np.random.default_rng(11).uniform(0.05, 0.95, (200, 3))
    physical = lower + (upper - lower) * probabilities
    independent = model.to_independent_normals(physical)
    np.testing.assert_allclose(model.from_independent_normals(independent), physical, atol=1e-10)
    assert reference.options["Copula"] == {"Type": "Independent"}


def test_scenario_uniform_marginals_latent_covariance_and_whitening(reference, scenario):
    model = create_scenario_model(reference, scenario)
    normal = np.random.default_rng(25).normal(size=(20000, 3))
    physical = model.from_independent_normals(normal)
    lower, upper = model.bounds.T
    probabilities = (physical - lower) / (upper - lower)
    np.testing.assert_allclose(probabilities.mean(axis=0), 0.5, atol=0.008)
    np.testing.assert_allclose(probabilities.var(axis=0), 1 / 12, atol=0.003)
    latent = ndtri(probabilities)
    np.testing.assert_allclose(np.corrcoef(latent, rowvar=False), scenario["gaussian_correlation"], atol=0.025)
    whitened = model.to_independent_normals(physical)
    np.testing.assert_allclose(np.corrcoef(whitened, rowvar=False), np.eye(3), atol=0.025)


@pytest.mark.parametrize("matrix,match", [
    ([[1, 0], [0, 1]], "3 x 3"),
    ([[1, 0, 0], [0, float('nan'), 0], [0, 0, 1]], "finite"),
    ([[1, 0.1, 0], [0, 1, 0], [0, 0, 1]], "symmetric"),
    (np.diag([1, 2, 1]), "unit diagonal"),
    (np.ones((3, 3)), "positive definite"),
    ([[1, 0.99, 0.99], [0.99, 1, -0.99], [0.99, -0.99, 1]], "positive definite"),
    ([[1, 1-1e-12, 0], [1-1e-12, 1, 0], [0, 0, 1]], "positive definite"),
])
def test_invalid_copula_matrices_rejected_without_repair(matrix, match):
    with pytest.raises(ValueError, match=match):
        validate_correlation(matrix)


def test_condition_number_guard():
    with pytest.raises(ValueError, match="ill-conditioned"):
        validate_correlation([[1, 0.8, 0], [0.8, 1, 0], [0, 0, 1]],
                             replace(DEFAULT_INPUT_CONFIG, maximum_condition_number=5))


def test_transform_endpoint_domain_shape_and_saturation_guards(reference):
    for point in reference.bounds.T:
        with pytest.raises(ValueError, match="strictly interior"):
            reference.to_independent_normals(point[None, :])
    with pytest.raises(ValueError, match="outside"):
        reference.standardized(reference.bounds.T[:1] - 1)
    for bad in ([1, 2, 3], [[1, 2]], [[1, np.nan, 3]]):
        with pytest.raises(ValueError, match="finite"):
            reference.to_independent_normals(bad)
    with pytest.raises(ValueError, match="saturate"):
        reference.from_independent_normals([[100, 0, 0]])


def test_scenario_requires_documented_order_and_assumptions(reference, scenario):
    for changes, match in [({"input_order": list(reversed(INPUT_COLUMNS))}, "input_order"),
                           ({"name": ""}, "name"), ({"description": ""}, "description")]:
        with pytest.raises(ValueError, match=match):
            create_scenario_model(reference, {**scenario, **changes})


def test_qq_uses_midpoint_plotting_positions_and_has_no_gof_pvalues(observations):
    parameters = uniform_parameters(observations)
    diagnostics, qq = marginal_diagnostics(observations, parameters)
    first = qq.iloc[0]
    assert first["plotting_probability"] == pytest.approx(0.5 / 19)
    assert first["observed_order_statistic"] == observations[INPUT_COLUMNS[0]].min()
    assert first["uniform_quantile"] > first["observed_order_statistic"]
    assert diagnostics["p_value"].str.startswith("not applicable").all()
    assert len(qq) == 19 * 3


def test_no_automatic_copula_estimation_or_independence_claim(observations):
    assessment = dependence_assessment(observations)
    assert assessment["estimation_status"] == "not_estimated_from_HEATWISE"
    assert len(assessment["reasons"]) >= 4
    dependencies = dependency_diagnostics(observations)
    assert set(dependencies["scope"]) == {"all_accepted", *[f"case_{c}" for c in range(1, 6)],
                                          *[f"without_case_{c}" for c in range(1, 6)]}
    assert dependencies.loc[dependencies["scope"].eq("case_1"), "pearson"].isna().sum() == 2


@pytest.mark.parametrize("defect,match", [
    ("missing_column", "Missing processed-data columns"), ("missing_value", "finite"),
    ("wrong_count", "Expected 19"), ("transition", "finite"), ("case_six", "cases 1-5"),
    ("duplicate_period", "unique positive"), ("overlap", "ordered and nonoverlapping"),
    ("invalid_time", "invalid timestamps"), ("reversed_time", "end after"),
])
def test_processed_observation_validation(observations, tmp_path, defect, match):
    data = observations.copy()
    if defect == "missing_column": data = data.drop(columns=INPUT_COLUMNS[0])
    elif defect == "missing_value": data.loc[0, INPUT_COLUMNS[0]] = np.nan
    elif defect == "wrong_count": data = data.iloc[:-1]
    elif defect == "transition": data.loc[0, "case_id"] = np.nan
    elif defect == "case_six": data.loc[0, "case_id"] = 6
    elif defect == "duplicate_period": data.loc[1, "operating_period_id"] = 1
    elif defect == "overlap": data.loc[1, "start_time"] = data.loc[0, "start_time"]
    elif defect == "invalid_time": data.loc[0, "start_time"] = pd.NaT
    elif defect == "reversed_time": data.loc[0, "end_time"] = data.loc[0, "start_time"]
    path = tmp_path / "observations.csv"
    data.to_csv(path, index=False)
    with pytest.raises(DatasetValidationError, match=match):
        load_observations(path)


def test_constant_input_is_rejected(observations):
    observations[INPUT_COLUMNS[1]] = 25
    with pytest.raises(ValueError, match="lower < upper"):
        uniform_parameters(observations)


def test_inputs_cli_default_artifacts_and_reproducibility(observations, tmp_path, capsys):
    source, output = tmp_path / "observations.csv", tmp_path / "results"
    observations.to_csv(source, index=False)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    assert main(["inputs", "--data", str(source), "--output", str(output)]) == 0
    text = capsys.readouterr().out
    assert "A: independent uniform" in text
    assert "B: not_requested" in text
    assert "not physical uncertainty" in text
    model = json.loads((output / "reference_model.json").read_text())
    assert model["uqlab_options"]["Copula"]["Type"] == "Independent"
    assert model["physical_uncertainty_inferred"] is False
    assert json.loads((output / "scenario_model.json").read_text())["status"] == "not_requested"
    for figure in ("experimental_histograms", "candidate_densities", "uniform_qq",
                   "joint_input_concepts", "observed_dependencies"):
        assert (output / "figures" / f"{figure}.pdf").stat().st_size > 1000
        assert (output / "figures" / f"{figure}.png").stat().st_size > 1000
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    again = tmp_path / "again"
    run_inputs(source, again)
    for name in ("reference_model.json", "scenario_model.json", "assumptions.json", "manifest.json",
                 "tables/reference_samples.csv", "tables/distribution_parameters.csv"):
        assert (output / name).read_bytes() == (again / name).read_bytes(), name


def test_specified_scenario_artifacts_are_separate(observations, scenario, tmp_path, monkeypatch):
    source, specification, output = tmp_path / "observations.csv", tmp_path / "scenario.json", tmp_path / "out"
    observations.to_csv(source, index=False)
    specification.write_text(json.dumps(scenario))
    monkeypatch.setattr("thermal_twin.inputs_plots.plot_input_diagnostics", lambda *args: None)
    result = run_inputs(source, output, specification)
    assert result["scenario"]["status"] == "user_specified_not_fitted"
    assert result["scenario"]["inverse_then_forward_max_abs_normal_error"] < 1e-8
    assert (output / "tables/scenario_samples.csv").exists()
    reference = json.loads((output / "reference_model.json").read_text())
    assert reference["uqlab_options"]["Copula"] == {"Type": "Independent"}
    run_inputs(source, output)
    assert not (output / "tables/scenario_samples.csv").exists()
    assert json.loads((output / "scenario_model.json").read_text())["status"] == "not_requested"


def test_inputs_cli_errors_without_tracebacks(observations, tmp_path, capsys):
    assert main(["inputs", "--data", str(tmp_path / "missing.csv")]) == 1
    assert "Run thermal-twin preprocess" in capsys.readouterr().err
    source = tmp_path / "observations.csv"
    observations.to_csv(source, index=False)
    scenario = tmp_path / "scenario.json"
    scenario.write_text('[]')
    output = tmp_path / "out"
    assert main(["inputs", "--data", str(source), "--scenario", str(scenario), "--output", str(output)]) == 1
    assert "must contain an object" in capsys.readouterr().err
    assert not output.exists()
    assert main(["inputs", "--data", str(source), "--output", str(tmp_path)]) == 1
    assert "must not contain source files" in capsys.readouterr().err
