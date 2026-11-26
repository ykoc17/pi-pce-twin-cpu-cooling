"""Three-constant steady-state thermal-resistance rule and physics check points.

T_phys = T_inlet + offset + P_CPU * K * (F / F_ref)**(-gamma)

Total power over 18 CPUs approximates the hottest CPU, so K is an effective
resistance of the server set, not the resistance of one CPU package. The fan
signal has an unverified unit; only the dimensionless ratio F / F_ref is used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import qmc

from configs.data_config import DEFAULT_DATA_PATH, INPUT_COLUMNS
from configs.physics_config import DEFAULT_PHYSICS_CONFIG, PhysicsConfig
from thermal_twin.data import DatasetValidationError
from thermal_twin.inputs import load_observations, uniform_parameters
from thermal_twin.preprocessing import TARGET_COLUMN

PHYSICS_COLUMN = "T_phys_C"


def _inputs(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all():
        raise ValueError("Expected a finite (N, 3) array: CPU power, inlet temperature, fan signal.")
    if np.any(values[:, 2] <= 0):
        raise ValueError("The thermal-resistance rule requires a positive fan signal.")
    return values


@dataclass(frozen=True)
class PhysicsModel:
    """Fitted constants. R0 stays zero for the project's three-constant rule."""

    offset_C: float
    K_C_per_W: float
    gamma: float
    fan_reference: float
    R0_C_per_W: float = 0.0

    def resistance(self, inputs) -> np.ndarray:
        ratio = _inputs(inputs)[:, 2] / self.fan_reference
        return self.R0_C_per_W + self.K_C_per_W * ratio ** -self.gamma

    def predict(self, inputs) -> np.ndarray:
        inputs = _inputs(inputs)
        return inputs[:, 1] + self.offset_C + inputs[:, 0] * self.resistance(inputs)

    def derivatives(self, inputs) -> np.ndarray:
        """Columns: dT/dP (C/W), dT/dT_inlet, dT/dF (C per raw fan-signal unit)."""
        inputs = _inputs(inputs)
        power, fan = inputs[:, 0], inputs[:, 2]
        cooling = self.K_C_per_W * (fan / self.fan_reference) ** -self.gamma
        return np.column_stack([
            self.R0_C_per_W + cooling, np.ones(len(inputs)), -power * cooling * self.gamma / fan,
        ])


def fit_physics(inputs, targets, config: PhysicsConfig = DEFAULT_PHYSICS_CONFIG, *,
                include_R0: bool = False) -> PhysicsModel:
    """Bounded nonlinear least squares from several starts; F_ref is the training median.

    include_R0 adds the fourth constant and exists only for the saved comparison.
    """
    inputs = _inputs(inputs)
    targets = np.asarray(targets, dtype=float)
    if targets.shape != (len(inputs),) or not np.isfinite(targets).all():
        raise ValueError("Targets must be a finite vector matching the inputs.")
    count = 4 if include_R0 else 3
    if len(targets) <= count:
        raise ValueError(f"Fitting {count} constants requires more than {count} observations.")
    reference = float(np.median(inputs[:, 2]))

    def model(theta):
        offset, k, gamma = (float(value) for value in theta[:3])
        return PhysicsModel(offset, k, gamma, reference, float(theta[3]) if include_R0 else 0.0)

    limit, resistance = config.max_abs_offset_C, config.max_resistance_C_per_W
    lower = [-limit, 0.0, config.min_gamma, 0.0][:count]
    upper = [limit, resistance, config.max_gamma, resistance][:count]
    best = None
    for offset, r0, k, gamma in config.starts:
        solution = least_squares(
            lambda theta: model(theta).predict(inputs) - targets, [offset, k, gamma, r0][:count],
            bounds=(lower, upper), x_scale=[5.0, 0.01, 0.3, 0.01][:count],
            xtol=1e-12, ftol=1e-12, gtol=1e-12,
        )
        if solution.success and (best is None or solution.cost < best.cost):
            best = solution
    if best is None:
        raise ValueError("The thermal-resistance fit did not converge from any starting point.")
    return model(best.x)


def parameter_uncertainty(model: PhysicsModel, inputs, targets, *, include_R0: bool = False) -> dict:
    """Linearized standard errors and correlations; a local identifiability check.

    These assume independent equal-variance residuals. Grouped operating periods
    do not satisfy that exactly, so they are diagnostics, not confidence claims.
    """
    inputs, targets = _inputs(inputs), np.asarray(targets, dtype=float)
    ratio = inputs[:, 2] / model.fan_reference
    cooling = inputs[:, 0] * ratio ** -model.gamma
    columns = [np.ones(len(inputs)), cooling, -model.K_C_per_W * cooling * np.log(ratio)]
    names = ["offset_C", "K_C_per_W", "gamma"]
    if include_R0:
        columns.append(inputs[:, 0])
        names.append("R0_C_per_W")
    jacobian = np.column_stack(columns)
    residuals = model.predict(inputs) - targets
    variance = residuals @ residuals / (len(targets) - len(names))
    # Scale columns first: the constants differ by orders of magnitude.
    scale = np.linalg.norm(jacobian, axis=0)
    scaled = jacobian / scale
    unscaled = np.linalg.pinv(scaled.T @ scaled)
    spread = np.sqrt(np.diag(unscaled))
    correlation = unscaled / np.outer(spread, spread)
    errors = np.sqrt(variance) * spread / scale
    return {"names": names, "standard_errors": dict(zip(names, errors.tolist())),
            "correlation": correlation.tolist(),
            "max_abs_parameter_correlation": float(np.abs(correlation - np.eye(len(names))).max()),
            "scaled_condition_number": float(np.linalg.cond(scaled))}


def error_metrics(predicted, measured) -> dict:
    predicted, measured = np.asarray(predicted, dtype=float), np.asarray(measured, dtype=float)
    error = predicted - measured
    spread = np.sum((measured - measured.mean()) ** 2)
    return {"n": len(error), "RMSE_C": float(np.sqrt(np.mean(error ** 2))),
            "MAE_C": float(np.mean(np.abs(error))), "max_abs_error_C": float(np.max(np.abs(error))),
            "R2": float(1 - np.sum(error ** 2) / spread) if len(error) > 1 and spread > 0 else None}


def validate_by_case(data: pd.DataFrame, config: PhysicsConfig = DEFAULT_PHYSICS_CONFIG, *,
                     include_R0: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leave one whole experimental case out; constants AND F_ref use training cases only."""
    predictions, folds = [], []
    columns = list(INPUT_COLUMNS)
    for case in sorted(data["case_id"].unique()):
        train, test = data[data["case_id"].ne(case)], data[data["case_id"].eq(case)]
        model = fit_physics(train[columns], train[TARGET_COLUMN], config, include_R0=include_R0)
        predicted = model.predict(test[columns])
        outside = [column for column in columns
                   if test[column].min() < train[column].min() or test[column].max() > train[column].max()]
        predictions.append(pd.DataFrame({
            "held_out_case": int(case), "operating_period_id": test["operating_period_id"].to_numpy(),
            "measured_C": test[TARGET_COLUMN].to_numpy(), "predicted_C": predicted,
            "residual_predicted_minus_measured_C": predicted - test[TARGET_COLUMN].to_numpy(),
        }))
        folds.append({"held_out_case": int(case), **asdict(model),
                      **error_metrics(predicted, test[TARGET_COLUMN]),
                      "inputs_outside_training_range": ";".join(outside)})
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(folds)


def sample_check_points(parameters: list[dict],
                        config: PhysicsConfig = DEFAULT_PHYSICS_CONFIG) -> np.ndarray:
    """Spread input combinations evenly (scrambled Sobol) over the reference ranges.

    The points carry no measurement. They include untested combinations on purpose,
    because the five tested inlet/fan clusters cannot determine a degree-2 PCE.
    """
    if [p["input"] for p in parameters] != list(INPUT_COLUMNS):
        raise ValueError("Parameters must follow the three configured inputs in order.")
    lower = np.array([p["lower"] for p in parameters], dtype=float)
    upper = np.array([p["upper"] for p in parameters], dtype=float)
    unit = qmc.Sobol(d=3, scramble=True, rng=config.check_point_seed).random_base2(config.check_point_power)
    return qmc.scale(unit, lower, upper)


def check_point_table(model: PhysicsModel, points, highest_measured_C: float) -> pd.DataFrame:
    """Attach T_phys, the target of the physics part of the loss. Not measurements."""
    table = pd.DataFrame(_inputs(points), columns=list(INPUT_COLUMNS))
    table[PHYSICS_COLUMN] = model.predict(points)
    table["above_highest_measured_target"] = table[PHYSICS_COLUMN] > highest_measured_C
    return table


def load_training_data(path: Path) -> pd.DataFrame:
    data = load_observations(path)
    if TARGET_COLUMN not in data:
        raise DatasetValidationError(f"Missing processed-data columns: {TARGET_COLUMN}")
    data[TARGET_COLUMN] = pd.to_numeric(data[TARGET_COLUMN], errors="coerce")
    if not np.isfinite(data[TARGET_COLUMN].to_numpy(dtype=float)).all():
        raise DatasetValidationError(f"Processed target {TARGET_COLUMN} must contain only finite numbers.")
    if (data[INPUT_COLUMNS[2]] <= 0).any():
        raise DatasetValidationError("The thermal-resistance rule requires positive fan-signal values.")
    return data


def compare_variants(data: pd.DataFrame, config: PhysicsConfig = DEFAULT_PHYSICS_CONFIG) -> pd.DataFrame:
    """Three versus four constants, on all observations and without throttled targets."""
    subsets = (("all_accepted", data),
               ("sensitivity_without_throttled",
                data[data[TARGET_COLUMN] < config.throttling_sensitivity_target_C]))
    records = []
    for subset, frame in subsets:
        for include in (False, True):
            inputs, targets = frame[list(INPUT_COLUMNS)], frame[TARGET_COLUMN]
            model = fit_physics(inputs, targets, config, include_R0=include)
            uncertainty = parameter_uncertainty(model, inputs, targets, include_R0=include)
            predictions, folds = validate_by_case(frame, config, include_R0=include)
            held_out = error_metrics(predictions["predicted_C"], predictions["measured_C"])
            records.append({
                "subset": subset, "constants": 4 if include else 3, "n": len(frame), **asdict(model),
                **{f"se_{name}": value for name, value in uncertainty["standard_errors"].items()},
                "max_abs_parameter_correlation": uncertainty["max_abs_parameter_correlation"],
                "training_RMSE_C": error_metrics(model.predict(inputs), targets)["RMSE_C"],
                "held_out_RMSE_C": held_out["RMSE_C"],
                "held_out_max_abs_error_C": held_out["max_abs_error_C"],
                "fold_gamma_min": folds["gamma"].min(), "fold_gamma_max": folds["gamma"].max(),
            })
    return pd.DataFrame(records)


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_physics(data_path: Path, output: Path, config: PhysicsConfig = DEFAULT_PHYSICS_CONFIG) -> dict:
    """Fit, validate by case, generate check points and save everything outside raw data."""
    data_path, output = Path(data_path), Path(output)
    if output.resolve().is_relative_to(DEFAULT_DATA_PATH.resolve().parent) or \
            data_path.resolve().is_relative_to(output.resolve()):
        raise DatasetValidationError("Physics output must be outside raw data and must not contain source files.")
    data = load_training_data(data_path)
    columns = list(INPUT_COLUMNS)
    try:
        parameters = uniform_parameters(data)
        model = fit_physics(data[columns], data[TARGET_COLUMN], config)
        uncertainty = parameter_uncertainty(model, data[columns], data[TARGET_COLUMN])
        predictions, folds = validate_by_case(data, config)
        comparison = compare_variants(data, config)
        points = sample_check_points(parameters, config)
    except ValueError as exc:
        raise DatasetValidationError(str(exc)) from exc
    checks = check_point_table(model, points, float(data[TARGET_COLUMN].max()))
    slopes = model.derivatives(np.vstack([data[columns].to_numpy(dtype=float), points]))
    monotonic = {"temperature_rises_with_power": bool((slopes[:, 0] > 0).all()),
                 "temperature_falls_with_fan_signal": bool((slopes[:, 2] < 0).all()),
                 "scope": "all observations and all check points"}
    training = error_metrics(model.predict(data[columns]), data[TARGET_COLUMN])
    held_out = error_metrics(predictions["predicted_C"], predictions["measured_C"])

    figures, tables = output / "figures", output / "tables"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(tables / "held_out_predictions.csv", index=False, float_format="%.12g")
    folds.to_csv(tables / "case_validation.csv", index=False, float_format="%.12g")
    comparison.to_csv(tables / "constant_comparison.csv", index=False, float_format="%.12g")
    checks.to_csv(tables / "check_points.csv", index=False, float_format="%.12g")
    fitted = {
        "equation": "T_phys = T_inlet + offset + P_CPU * K * (F / F_ref)**(-gamma)",
        "constants": {name: value for name, value in asdict(model).items() if name != "R0_C_per_W"},
        "uncertainty": uncertainty, "training": training, "held_out": held_out,
        "monotonicity": monotonic, "fan_unit": "unverified; only the ratio F/F_ref is used",
    }
    _write_json(output / "parameters.json", fitted)
    _write_json(output / "manifest.json", {
        "source": data_path.as_posix(), "source_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
        "observations": len(data), "input_order": columns, "target": TARGET_COLUMN, "config": asdict(config),
        "check_points": len(checks), "check_point_ranges": parameters, "python": platform.python_version(),
        "versions": {name: version(name) for name in ("thermal-twin", "numpy", "pandas", "scipy", "matplotlib")},
    })
    from thermal_twin.physics_plots import plot_physics
    plot_physics(data, model, predictions, checks, figures)
    _write_report(output, data_path, fitted, folds, comparison, checks, len(data), config)
    return {"model": model, "training": training, "held_out": held_out, "check_points": len(checks),
            "observations": len(data)}


def _write_report(output, data_path, fitted, folds, comparison, checks, count, config):
    constants, errors = fitted["constants"], fitted["uncertainty"]["standard_errors"]
    training, held_out, monotonic = fitted["training"], fitted["held_out"], fitted["monotonicity"]
    hot = int(checks["above_highest_measured_target"].sum())
    fold_lines = "\n".join(
        f"| {row.held_out_case} | {row.n} | {row.RMSE_C:.2f} | {row.MAE_C:.2f} | {row.max_abs_error_C:.2f} | "
        f"{row.offset_C:.2f} | {row.K_C_per_W:.4f} | {row.gamma:.3f} | {row.fan_reference:.4f} | "
        f"{row.inputs_outside_training_range.replace(';', ', ') or 'none'} |" for row in folds.itertuples())
    comparison_lines = "\n".join(
        f"| {row.subset} | {row.n} | {row.constants} | {row.training_RMSE_C:.2f} | {row.held_out_RMSE_C:.2f} | "
        f"{row.held_out_max_abs_error_C:.2f} | {row.max_abs_parameter_correlation:.3f} | "
        f"{row.fold_gamma_min:.2f} to {row.fold_gamma_max:.2f} |" for row in comparison.itertuples())
    metric = "| {} | {:.2f} | {:.2f} | {:.2f} | {:.3f} |"
    metric_lines = "\n".join(
        metric.format(label, m["RMSE_C"], m["MAE_C"], m["max_abs_error_C"], m["R2"])
        for label, m in ((f"Training, all {count}", training), ("Held-out cases, pooled", held_out)))
    text = f"""# Three-constant thermal-resistance rule and check points

Fitted to **{count} accepted operating observations** from `{data_path.as_posix()}`.
The preprocessing selection is unchanged.

    {fitted["equation"]}

| Constant | Value | Linearized standard error |
| --- | --- | --- |
| offset (C) | {constants["offset_C"]:.3f} | {errors["offset_C"]:.3f} |
| K (C/W) | {constants["K_C_per_W"]:.5f} | {errors["K_C_per_W"]:.5f} |
| gamma | {constants["gamma"]:.4f} | {errors["gamma"]:.4f} |
| F_ref (raw fan signal) | {constants["fan_reference"]:.6f} | training median, not fitted |

## Fitting method

Bounded nonlinear least squares (`scipy.optimize.least_squares`, K >= 0, gamma > 0)
minimizes squared errors to the steady-state targets from {len(config.starts)} starting points.
F_ref is the median training fan signal. Every validation fold refits all constants
and F_ref on the four training cases only.

The rule uses total power of 18 CPUs to approximate the hottest CPU, so K is an
effective resistance. The fan-signal unit is **unverified**; only the dimensionless
ratio F/F_ref enters.

## Errors

| | RMSE (C) | MAE (C) | Max abs error (C) | R2 |
| --- | --- | --- | --- | --- |
{metric_lines}

| Held-out case | n | RMSE | MAE | Max abs | offset | K | gamma | F_ref | Inputs outside training range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
{fold_lines}

Per-fold R2 in `tables/case_validation.csv` rests on 2-5 observations.

## Why three constants

A four-constant rule adds R0 to the bracket: R_th = R0 + K (F/F_ref)^(-gamma).

| Observations | n | Constants | Training RMSE | Held-out RMSE | Held-out max abs | Max parameter correlation | gamma across folds |
| --- | --- | --- | --- | --- | --- | --- | --- |
{comparison_lines}

Correlations near 1 mean the data cannot separate the constants. R0 was dropped after
seeing these held-out errors, so they are slightly optimistic for the chosen rule.

## CPU throttling

Some targets sit near 94 C because CPUs reduce frequency and power at that temperature;
there, temperature no longer responds freely to power. The main fit keeps all accepted
observations. `sensitivity_without_throttled` drops targets of at least
{config.throttling_sensitivity_target_C:g} C for comparison only. Selecting by target value is
biased, and no observation is removed from `steady_state.csv`.

## Physical monotonicity

- Temperature rises with CPU power: {monotonic["temperature_rises_with_power"]}.
- Temperature falls with fan signal: {monotonic["temperature_falls_with_fan_signal"]}.

Checked analytically at {monotonic["scope"]}.

## Check points

`tables/check_points.csv` holds {len(checks)} scrambled Sobol input combinations over the
reference ranges (fixed seed), with T_phys from the rule. They are targets for the physics
part of a physics-informed loss. **They are not measurements**: they add no experimental
information, and untested regions rest on the rule alone. {hot} of them exceed the highest
measured target, where real CPUs would throttle. For validation, refit the rule and
recompute T_phys inside every fold.

No PCE or physics-informed PCE is fitted in this step.

## Reproduce

```
thermal-twin fit-physics
```
"""
    (output / "report.md").write_text(text, encoding="utf-8")
