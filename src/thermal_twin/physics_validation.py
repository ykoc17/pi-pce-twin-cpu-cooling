"""Separate thermal-rule model choice, outer testing and diagnostic generation.

Generated targets are never approved for PCE fitting by this module. Each outer
test case is excluded from model choice, fitting, bounds and target screening.
The existing dataset has already informed the project: these remain early checks,
not a new external test set or a safety guarantee.
"""

from dataclasses import asdict

import pandas as pd

from configs.data_config import INPUT_COLUMNS
from configs.physics_config import DEFAULT_PHYSICS_CONFIG
from thermal_twin.inputs import uniform_parameters
from thermal_twin.physics import (
    TARGET_COLUMN, check_point_table, error_metrics, fit_physics,
    sample_check_points, validate_by_case,
)


def training_only_diagnostics(training, config=DEFAULT_PHYSICS_CONFIG, *, include_R0=False):
    """Fit and screen using only the supplied training rows; do not supply test rows.

    The training maximum is a conservative diagnostic screen, not a physical
    throttling threshold. Passing that screen does not establish model validity.
    """
    model = fit_physics(training[list(INPUT_COLUMNS)], training[TARGET_COLUMN],
                        config, include_R0=include_R0)
    ranges = uniform_parameters(training)
    cutoff = float(training[TARGET_COLUMN].max())
    points = sample_check_points(ranges, config)
    checks = check_point_table(model, points, cutoff)
    checks["screen_cutoff_C"] = cutoff
    checks["status"] = checks.above_highest_measured_target.map({
        True: "excluded_above_training_maximum",
        False: "withheld_pending_domain_and_regime_validation",
    })
    checks["physics_loss_weight"] = 0.0
    return model, ranges, checks


def nested_case_review(data, config=DEFAULT_PHYSICS_CONFIG):
    """Five outer tests; use only each outer training set to choose 3 vs 4 constants.

    Inner selection uses pooled leave-one-training-case-out RMSE, lower wins;
    exact ties choose the simpler rule. No synthetic target enters any fit.
    Returned check points are diagnostics, not additional experimental evidence.
    """
    if data.case_id.nunique() < 4:
        raise ValueError("Nested case review requires at least four experimental cases.")
    predictions, summaries, checks_all, choices, ranges_all = [], [], [], [], []
    for held_out in sorted(data.case_id.unique()):
        training = data.loc[data.case_id.ne(held_out)]
        test = data.loc[data.case_id.eq(held_out)]
        scores = {}
        for constants in (3, 4):
            inner, _ = validate_by_case(training, config, include_R0=(constants == 4))
            score = error_metrics(inner.predicted_C, inner.measured_C)["RMSE_C"]
            scores[constants] = score
            choices.append({"held_out_case": int(held_out), "constants": constants,
                            "inner_RMSE_C": score,
                            "selection_case_ids": ",".join(map(str, sorted(training.case_id.unique())))})
        selected = min(scores, key=lambda k: (scores[k], k))
        model, ranges, checks = training_only_diagnostics(training, config, include_R0=(selected == 4))
        predicted = model.predict(test[list(INPUT_COLUMNS)])
        predictions.append(pd.DataFrame({
            "held_out_case": int(held_out), "operating_period_id": test.operating_period_id.to_numpy(),
            "measured_C": test[TARGET_COLUMN].to_numpy(), "predicted_C": predicted,
            "residual_predicted_minus_measured_C": predicted - test[TARGET_COLUMN].to_numpy(),
            "selected_constants": selected,
        }))
        checks.insert(0, "held_out_case", int(held_out))
        checks_all.append(checks)
        ranges_all.extend({"held_out_case": int(held_out), **r} for r in ranges)
        summaries.append({
            "held_out_case": int(held_out), "selected_constants": selected,
            "training_case_ids": ",".join(map(str, sorted(training.case_id.unique()))),
            "training_period_ids": ",".join(map(str, training.operating_period_id)),
            "test_period_ids": ",".join(map(str, test.operating_period_id)),
            "training_n": len(training), **error_metrics(predicted, test[TARGET_COLUMN]),
            **asdict(model), "screen_cutoff_C": float(training[TARGET_COLUMN].max()),
            "diagnostic_points": len(checks),
            "excluded_points": int(checks.above_highest_measured_target.sum()),
            "withheld_points": int((~checks.above_highest_measured_target).sum()),
            "synthetic_points_used_in_training": 0,
        })
    return {"predictions": pd.concat(predictions, ignore_index=True),
            "folds": pd.DataFrame(summaries), "selection": pd.DataFrame(choices),
            "check_points": pd.concat(checks_all, ignore_index=True), "ranges": pd.DataFrame(ranges_all)}
