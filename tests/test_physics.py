"""Thermal-resistance rule: recovery, bounds, group separation and check points."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from configs.data_config import INPUT_COLUMNS
from configs.physics_config import DEFAULT_PHYSICS_CONFIG, PhysicsConfig
from thermal_twin.cli import main
from thermal_twin.data import DatasetValidationError
from thermal_twin.inputs import uniform_parameters
from thermal_twin.physics import (
    TARGET_COLUMN, PhysicsModel, check_point_table, compare_variants, error_metrics, fit_physics,
    load_training_data, parameter_uncertainty, run_physics, sample_check_points, validate_by_case,
)

COLUMNS = list(INPUT_COLUMNS)
TRUTH = PhysicsModel(offset_C=3.0, K_C_per_W=0.03, gamma=0.4, fan_reference=0.36)
REAL_DATA = Path(__file__).resolve().parents[1] / "data/processed/steady_state.csv"


@pytest.fixture
def observations():
    """Five clusters like the experiment, with noise-free targets from known constants."""
    regimes = [(25.0, 0.13, 4), (35.0, 0.24, 4), (45.0, 0.36, 5), (45.0, 0.53, 4), (45.0, 0.72, 2)]
    records = []
    for case, (inlet, fan, count) in enumerate(regimes, start=1):
        for i, power in enumerate(np.linspace(400, 1300 + 50 * case, count)):
            records.append({"case_id": case, COLUMNS[0]: power, COLUMNS[1]: inlet,
                            COLUMNS[2]: fan + 0.002 * i})
    data = pd.DataFrame(records)
    start = pd.date_range("2024-01-01", periods=len(data), freq="2h")
    data.insert(0, "operating_period_id", np.arange(1, len(data) + 1))
    data["start_time"], data["end_time"] = start, start + pd.Timedelta(minutes=30)
    data[TARGET_COLUMN] = TRUTH.predict(data[COLUMNS])
    return data


def write(data, path):
    data.to_csv(path, index=False)
    return path


def test_prediction_matches_the_written_equation():
    expected = 45 + 3.0 + 1000 * 0.03 * (0.5 / 0.36) ** -0.4
    assert TRUTH.predict([[1000, 45, 0.5]])[0] == pytest.approx(expected)


def test_fit_recovers_known_function(observations):
    model = fit_physics(observations[COLUMNS], observations[TARGET_COLUMN])
    assert model.offset_C == pytest.approx(TRUTH.offset_C, abs=1e-4)
    assert model.gamma == pytest.approx(TRUTH.gamma, abs=1e-5)
    # K is tied to its own reference: compare the reference-free resistance.
    np.testing.assert_allclose(model.resistance(observations[COLUMNS]),
                               TRUTH.resistance(observations[COLUMNS]), rtol=1e-6)
    assert model.R0_C_per_W == 0
    assert model.fan_reference == observations[COLUMNS[2]].median()


def test_fit_respects_bounds_for_unphysical_targets(observations):
    # Temperature falling with power would need a negative resistance.
    targets = 90 - 0.02 * observations[COLUMNS[0]]
    model = fit_physics(observations[COLUMNS], targets)
    assert 0 <= model.K_C_per_W <= DEFAULT_PHYSICS_CONFIG.max_resistance_C_per_W
    assert DEFAULT_PHYSICS_CONFIG.min_gamma <= model.gamma <= DEFAULT_PHYSICS_CONFIG.max_gamma


def test_derivatives_match_finite_differences(observations):
    points = observations[COLUMNS].to_numpy()
    analytic = TRUTH.derivatives(points)
    for column, step in enumerate((1e-2, 1e-4, 1e-6)):
        shift = np.zeros(3)
        shift[column] = step
        numeric = (TRUTH.predict(points + shift) - TRUTH.predict(points - shift)) / (2 * step)
        np.testing.assert_allclose(analytic[:, column], numeric, rtol=1e-5)
    assert (analytic[:, 0] > 0).all() and (analytic[:, 2] < 0).all()


@pytest.mark.parametrize("bad", [
    [[1000, 45, 0.0]], [[1000, 45, -0.1]], [[np.nan, 45, 0.3]], [[1000, 45]], [1000, 45, 0.3],
])
def test_invalid_inputs_are_rejected(bad):
    with pytest.raises(ValueError):
        TRUTH.predict(bad)


def test_fit_rejects_bad_targets_and_too_few_rows(observations):
    with pytest.raises(ValueError, match="Targets"):
        fit_physics(observations[COLUMNS], np.full(len(observations), np.nan))
    with pytest.raises(ValueError, match="more than 3"):
        fit_physics(observations[COLUMNS][:3], observations[TARGET_COLUMN][:3])


def test_held_out_case_never_influences_its_own_fold(observations):
    _, original = validate_by_case(observations)
    changed = observations.copy()
    held_out = changed["case_id"].eq(3)
    changed.loc[held_out, TARGET_COLUMN] += 40
    changed.loc[held_out, COLUMNS[2]] *= 1.3
    _, modified = validate_by_case(changed)
    names = ["offset_C", "K_C_per_W", "gamma", "fan_reference"]
    pd.testing.assert_frame_equal(original.loc[original.held_out_case.eq(3), names],
                                  modified.loc[modified.held_out_case.eq(3), names])
    assert not np.allclose(original.loc[original.held_out_case.eq(1), names],
                           modified.loc[modified.held_out_case.eq(1), names])


def test_every_observation_is_predicted_exactly_once(observations):
    predictions, folds = validate_by_case(observations)
    assert sorted(predictions["operating_period_id"]) == sorted(observations["operating_period_id"])
    assert folds["n"].sum() == len(observations)
    assert folds.set_index("held_out_case").loc[1, "inputs_outside_training_range"]


def test_extra_constant_is_not_identifiable(observations):
    three = fit_physics(observations[COLUMNS], observations[TARGET_COLUMN] + np.sin(np.arange(19)))
    four = fit_physics(observations[COLUMNS], observations[TARGET_COLUMN] + np.sin(np.arange(19)),
                       include_R0=True)
    targets = observations[TARGET_COLUMN] + np.sin(np.arange(19))
    assert (parameter_uncertainty(four, observations[COLUMNS], targets, include_R0=True)["scaled_condition_number"]
            > 5 * parameter_uncertainty(three, observations[COLUMNS], targets)["scaled_condition_number"])


def test_check_points_cover_the_box_reproducibly(observations):
    parameters = uniform_parameters(observations)
    points = sample_check_points(parameters)
    assert points.shape == (2 ** DEFAULT_PHYSICS_CONFIG.check_point_power, 3)
    np.testing.assert_array_equal(points, sample_check_points(parameters))
    other = sample_check_points(parameters, replace(DEFAULT_PHYSICS_CONFIG, check_point_seed=1))
    assert not np.array_equal(points, other)
    for i, parameter in enumerate(parameters):
        assert points[:, i].min() >= parameter["lower"] and points[:, i].max() <= parameter["upper"]
        # Sobol balance: every eighth of each range receives exactly 1/8 of the points.
        counts, _ = np.histogram(points[:, i], bins=8, range=(parameter["lower"], parameter["upper"]))
        assert (counts == len(points) / 8).all()
    # Untested combinations are covered: cool inlet with strong fan signal.
    assert ((points[:, 1] < 30) & (points[:, 2] > 0.5)).any()


def test_check_point_targets_come_from_the_rule(observations):
    points = sample_check_points(uniform_parameters(observations))
    table = check_point_table(TRUTH, points, highest_measured_C=80.0)
    np.testing.assert_allclose(table["T_phys_C"], TRUTH.predict(points))
    assert (table["above_highest_measured_target"] == (table["T_phys_C"] > 80.0)).all()


def test_error_metrics():
    metrics = error_metrics([1.0, 2.0, 5.0], [1.0, 2.0, 3.0])
    assert metrics["RMSE_C"] == pytest.approx(np.sqrt(4 / 3))
    assert metrics["max_abs_error_C"] == 2
    assert error_metrics([1.0], [2.0])["R2"] is None


@pytest.mark.parametrize("override", [
    {"starts": ()}, {"min_gamma": 6.0}, {"check_point_power": 0}, {"max_abs_offset_C": float("nan")},
])
def test_invalid_config(override):
    with pytest.raises(ValueError):
        PhysicsConfig(**override)


def test_cli_saves_outputs_without_touching_source(observations, tmp_path, capsys):
    source = write(observations, tmp_path / "steady.csv")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "physics"
    assert main(["fit-physics", "--data", str(source), "--output", str(output)]) == 0
    assert "not measurements" in capsys.readouterr().out
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    saved = json.loads((output / "parameters.json").read_text(encoding="utf-8"))
    assert set(saved["constants"]) == {"offset_C", "K_C_per_W", "gamma", "fan_reference"}
    assert saved["monotonicity"]["temperature_falls_with_fan_signal"]
    for name in ("physics_response", "held_out_predictions", "check_points"):
        for suffix in ("png", "pdf"):
            assert (output / "figures" / f"{name}.{suffix}").stat().st_size > 0
    assert len(pd.read_csv(output / "tables/check_points.csv")) == 128
    assert "not measurements" in (output / "report.md").read_text(encoding="utf-8")


def test_output_may_not_contain_source_or_enter_raw_data(observations, tmp_path):
    source = write(observations, tmp_path / "steady.csv")
    with pytest.raises(DatasetValidationError, match="must not contain source"):
        run_physics(source, tmp_path)
    with pytest.raises(DatasetValidationError, match="outside raw data"):
        run_physics(source, Path("data/raw/physics"))


@pytest.mark.parametrize("change, message", [
    (lambda d: d.drop(columns=TARGET_COLUMN), "Missing processed-data columns"),
    (lambda d: d.assign(**{TARGET_COLUMN: "x"}), "finite numbers"),
    (lambda d: d.assign(**{COLUMNS[2]: -d[COLUMNS[2]]}), "positive fan-signal"),
])
def test_invalid_training_data(observations, tmp_path, change, message):
    with pytest.raises(DatasetValidationError, match=message):
        load_training_data(write(change(observations), tmp_path / "bad.csv"))


@pytest.mark.skipif(not REAL_DATA.is_file(), reason="processed observations are not available")
def test_real_observations_support_three_constants():
    comparison = compare_variants(load_training_data(REAL_DATA)).set_index(["subset", "constants"])
    assert comparison.loc[("all_accepted", 3), "n"] == 19
    assert comparison.loc[("sensitivity_without_throttled", 3), "n"] == 13
    for subset in ("all_accepted", "sensitivity_without_throttled"):
        assert comparison.loc[(subset, 3), "held_out_RMSE_C"] < comparison.loc[(subset, 4), "held_out_RMSE_C"]
        assert comparison.loc[(subset, 4), "max_abs_parameter_correlation"] > 0.99
