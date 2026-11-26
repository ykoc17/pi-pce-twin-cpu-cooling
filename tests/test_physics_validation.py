"""Check that outer test data cannot affect model choice or generated targets."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from configs.data_config import INPUT_COLUMNS
from configs.physics_config import DEFAULT_PHYSICS_CONFIG
from thermal_twin.physics import PhysicsModel, TARGET_COLUMN
from thermal_twin.physics_validation import nested_case_review, training_only_diagnostics


@pytest.fixture
def observations():
    records = []
    truth = PhysicsModel(3.0, 0.03, 0.4, 0.36)
    for case, (inlet, fan) in enumerate([(25, .13), (35, .24), (45, .36), (45, .53), (45, .72)], 1):
        for power in (400, 800, 1200, 1600):
            records.append(dict(zip(INPUT_COLUMNS, (power + case, inlet, fan + power / 1e6))) |
                           {"case_id": case, "operating_period_id": len(records) + 1})
    frame = pd.DataFrame(records)
    frame[TARGET_COLUMN] = truth.predict(frame[list(INPUT_COLUMNS)]) + np.sin(np.arange(len(frame)))
    return frame


CONFIG = replace(DEFAULT_PHYSICS_CONFIG, starts=(DEFAULT_PHYSICS_CONFIG.starts[1],), check_point_power=3)


def test_training_diagnostics_use_only_training_bounds_and_labels(observations):
    training = observations.loc[observations.case_id.ne(5)]
    model, ranges, checks = training_only_diagnostics(training, CONFIG)
    assert model.fan_reference == training[INPUT_COLUMNS[2]].median()
    assert checks.screen_cutoff_C.eq(training[TARGET_COLUMN].max()).all()
    for column, parameter in zip(INPUT_COLUMNS, ranges):
        assert parameter["lower"] == training[column].min()
        assert parameter["upper"] == training[column].max()
        assert checks[column].between(parameter["lower"], parameter["upper"]).all()
    assert checks.physics_loss_weight.eq(0).all()
    assert checks.loc[checks.above_highest_measured_target, "status"].eq(
        "excluded_above_training_maximum").all()
    assert checks.loc[~checks.above_highest_measured_target, "status"].eq(
        "withheld_pending_domain_and_regime_validation").all()


def test_changing_outer_test_cannot_change_training_pipeline(observations):
    original = nested_case_review(observations, CONFIG)
    changed = observations.copy()
    outer = changed.case_id.eq(3)
    changed.loc[outer, TARGET_COLUMN] += 100
    changed.loc[outer, INPUT_COLUMNS[0]] *= 3
    changed.loc[outer, INPUT_COLUMNS[1]] += 20
    changed.loc[outer, INPUT_COLUMNS[2]] *= 2
    modified = nested_case_review(changed, CONFIG)
    for key in ("selection", "check_points", "ranges"):
        pd.testing.assert_frame_equal(
            original[key].loc[original[key].held_out_case.eq(3)].reset_index(drop=True),
            modified[key].loc[modified[key].held_out_case.eq(3)].reset_index(drop=True))
    names = ["selected_constants", "offset_C", "K_C_per_W", "gamma", "R0_C_per_W",
             "fan_reference", "screen_cutoff_C", "training_period_ids"]
    pd.testing.assert_frame_equal(original["folds"].loc[original["folds"].held_out_case.eq(3), names],
                                  modified["folds"].loc[modified["folds"].held_out_case.eq(3), names])


def test_nested_review_predicts_each_real_row_once_and_never_uses_generated_labels(observations):
    result = nested_case_review(observations, CONFIG)
    assert sorted(result["predictions"].operating_period_id) == sorted(observations.operating_period_id)
    assert result["check_points"].physics_loss_weight.eq(0).all()
    assert result["folds"].synthetic_points_used_in_training.eq(0).all()
    for fold in result["folds"].itertuples():
        train_ids = set(map(int, fold.training_period_ids.split(",")))
        test_ids = set(map(int, fold.test_period_ids.split(",")))
        assert train_ids.isdisjoint(test_ids)
        assert str(fold.held_out_case) not in fold.training_case_ids.split(",")
        scores = result["selection"].loc[result["selection"].held_out_case.eq(fold.held_out_case)]
        expected = scores.sort_values(["inner_RMSE_C", "constants"]).iloc[0].constants
        assert fold.selected_constants == expected
