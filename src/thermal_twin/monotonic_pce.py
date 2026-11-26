"""Normalized Legendre PCE fitted to measured targets with monotonicity constraints.

Input order: CPU power, inlet temperature, raw fan signal. Assumed derivative
signs: +, +, -. For total degree <=2, derivatives are affine, so checking all
eight box vertices enforces their signs throughout that box (to solver tolerance).
Vertices supply no temperature labels and never enter the data-fit objective.
The box is a shape-assumption domain, not a validated/safe control domain.
"""

from dataclasses import dataclass
from dataclasses import asdict
from itertools import product
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.polynomial.legendre import legder, legval
from scipy.optimize import LinearConstraint, minimize

from configs.data_config import INPUT_COLUMNS
from configs.pce_config import DEFAULT_PCE_CONFIG
from thermal_twin.data import DatasetValidationError
from thermal_twin.inputs import load_observations
from thermal_twin.preprocessing import TARGET_COLUMN

SIGNS = np.array([1., 1., -1.])
VERTICES = np.array(list(product((-1., 1.), repeat=3)))
METHODS = ("ordinary", "monotonicity")


def error_metrics(predicted, measured):
    error = np.asarray(predicted)-np.asarray(measured)
    spread = np.sum((measured-np.mean(measured))**2)
    return {"n": len(error), "RMSE_C": float(np.sqrt(np.mean(error**2))),
            "MAE_C": float(np.mean(abs(error))), "max_abs_error_C": float(np.max(abs(error))),
            "R2": float(1-np.sum(error**2)/spread) if spread > 0 else None}


def _values(values):
    values = np.asarray(values, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3 or not np.isfinite(values).all():
        raise ValueError("Expected finite (N,3) inputs in CPU/inlet/fan order.")
    return values


def indices(degree):
    if degree not in (1, 2):
        raise ValueError("Only total degree 1 or 2 supports this vertex certificate.")
    return np.array(sorted((a for a in product(range(degree+1), repeat=3) if sum(a) <= degree),
                           key=lambda a: (sum(a), a)), dtype=int)


def basis(values, powers, derivative=None):
    values = _values(values)
    columns = []
    for alpha in powers:
        column = np.ones(len(values))
        for axis, order in enumerate(alpha):
            coeff = np.r_[np.zeros(order), 1.]
            if derivative == axis:
                coeff = legder(coeff)
            column *= np.sqrt(2*order+1)*legval(values[:, axis], coeff)
        columns.append(column)
    return np.column_stack(columns)


def derivative_constraints(powers):
    return np.vstack([SIGNS[axis]*basis(VERTICES, powers, derivative=axis) for axis in range(3)])


@dataclass
class PCEModel:
    degree: int
    method: str
    lower: np.ndarray
    upper: np.ndarray
    powers: np.ndarray
    coefficients: np.ndarray
    diagnostics: dict

    def standardized(self, values):
        return 2*(_values(values)-self.lower)/(self.upper-self.lower)-1

    def predict(self, values):
        return basis(self.standardized(values), self.powers)@self.coefficients

    def gradient(self, values):
        z = self.standardized(values)
        return np.column_stack([basis(z, self.powers, derivative=i)@self.coefficients
                                *2/(self.upper[i]-self.lower[i]) for i in range(3)])

    def reference_moments(self):
        """Moments of this polynomial under its independent uniform reference only."""
        return {"mean_C": float(self.coefficients[0]),
                "variance_C2": float(self.coefficients[1:]@self.coefficients[1:])}

    def to_dict(self):
        return {"degree": self.degree, "method": self.method, "lower": self.lower.tolist(),
                "upper": self.upper.tolist(), "powers": self.powers.tolist(),
                "coefficients": self.coefficients.tolist(), "diagnostics": self.diagnostics,
                "reference_moments": self.reference_moments(), "input_order": list(INPUT_COLUMNS)}


def fit_pce(inputs, targets, degree=2, *, monotonic=False, config=DEFAULT_PCE_CONFIG):
    x = _values(inputs)
    y = np.asarray(targets, dtype=float)
    powers = indices(degree)
    if y.shape != (len(x),) or not np.isfinite(y).all() or len(y) < len(powers):
        raise ValueError("Need finite matching targets and at least as many rows as coefficients.")
    lower, upper = x.min(axis=0), x.max(axis=0)
    if np.any(upper <= lower):
        raise ValueError("Every training input must have a nonzero range.")
    A = basis(2*(x-lower)/(upper-lower)-1, powers)
    mean, scale = float(y.mean()), max(float(y.std()), 1.)
    normalized_y = (y-mean)/scale
    coefficients = np.linalg.lstsq(A, normalized_y, rcond=None)[0]
    B = derivative_constraints(powers)
    solver, iterations = "numpy.linalg.lstsq", 0
    if monotonic and (B@coefficients).min()*scale < -1e-10:
        row_norm = np.linalg.norm(B, axis=1)
        constraint = LinearConstraint(B/row_norm[:, None], 0., np.inf)
        def objective(c):
            error = A@c-normalized_y
            return float(error@error/len(y))
        def jacobian(c):
            return 2*A.T@(A@c-normalized_y)/len(y)
        solution = minimize(objective, np.zeros(len(powers)), jac=jacobian, method="SLSQP",
                            constraints=[constraint], options={"ftol": config.solver_tolerance,
                                                              "maxiter": config.max_iterations})
        if not solution.success:
            raise ValueError(f"Monotonicity-constrained fit did not converge: {solution.message}")
        coefficients = solution.x
        solver, iterations = "SciPy SLSQP; convex quadratic objective, linear inequalities", int(solution.nit)
    coefficients = coefficients*scale
    coefficients[0] += mean
    minimum = float((B@coefficients).min())
    if monotonic and minimum < -config.feasibility_tolerance:
        raise ValueError(f"Monotonicity check failed: minimum signed derivative {minimum:g}")
    return PCEModel(degree, "monotonicity" if monotonic else "ordinary", lower, upper, powers,
                    coefficients, {"rows": len(y), "coefficients": len(powers),
                    "design_rank": int(np.linalg.matrix_rank(A)), "design_condition": float(np.linalg.cond(A)),
                    "solver": solver, "iterations": iterations,
                    "minimum_signed_derivative_normalized_C": minimum,
                    "monotonicity_tolerance_C": config.feasibility_tolerance,
                    "synthetic_temperature_targets": 0, "regularization": "none"})


def _case_predictions(data, degree, method, config):
    records = []
    for case in sorted(data.case_id.unique()):
        training, test = data.loc[data.case_id.ne(case)], data.loc[data.case_id.eq(case)]
        model = fit_pce(training[list(INPUT_COLUMNS)], training[TARGET_COLUMN], degree,
                        monotonic=method == "monotonicity", config=config)
        predicted = model.predict(test[list(INPUT_COLUMNS)])
        records.extend({"held_out_case": int(case), "operating_period_id": int(period),
                        "measured_C": float(measured), "predicted_C": float(prediction),
                        "degree": degree, "method": method}
                       for period, measured, prediction in zip(test.operating_period_id, test[TARGET_COLUMN], predicted))
    return pd.DataFrame(records)


def choose_degree(training, method, config=DEFAULT_PCE_CONFIG):
    scores, predictions = [], []
    for degree in config.degrees:
        result = _case_predictions(training, degree, method, config)
        predictions.append(result)
        scores.append({"degree": degree, "method": method,
                       **error_metrics(result.predicted_C, result.measured_C)})
    selected = min(scores, key=lambda r: (r["RMSE_C"], r["degree"]))["degree"]
    return selected, pd.DataFrame(scores), pd.concat(predictions, ignore_index=True)


def compare_pce(data, config=DEFAULT_PCE_CONFIG):
    """Nested case-wise comparison; all scaling and constraints use training rows only."""
    if data.case_id.nunique() < 5:
        raise ValueError("This degree-selection protocol requires five experimental cases.")
    predictions, folds, selection, corner_checks = [], [], [], []
    for case in sorted(data.case_id.unique()):
        training, test = data.loc[data.case_id.ne(case)], data.loc[data.case_id.eq(case)]
        for method in METHODS:
            degree, scores, _ = choose_degree(training, method, config)
            scores.insert(0, "held_out_case", int(case))
            selection.append(scores)
            model = fit_pce(training[list(INPUT_COLUMNS)], training[TARGET_COLUMN], degree,
                            monotonic=method == "monotonicity", config=config)
            predicted = model.predict(test[list(INPUT_COLUMNS)])
            outside = np.any((test[list(INPUT_COLUMNS)].to_numpy() < model.lower) |
                             (test[list(INPUT_COLUMNS)].to_numpy() > model.upper), axis=1)
            predictions.append(pd.DataFrame({"held_out_case": int(case), "method": method,
                "degree": degree, "operating_period_id": test.operating_period_id.to_numpy(),
                "measured_C": test[TARGET_COLUMN].to_numpy(), "predicted_C": predicted,
                "outside_training_box": outside}))
            folds.append({"held_out_case": int(case), "method": method, "degree": degree,
                "training_period_ids": ",".join(map(str, training.operating_period_id)),
                "test_period_ids": ",".join(map(str, test.operating_period_id)),
                "training_case_ids": ",".join(map(str, sorted(training.case_id.unique()))),
                "training_bounds": [model.lower.tolist(), model.upper.tolist()],
                "coefficients": model.coefficients.tolist(),
                "outside_training_box": int(outside.sum()),
                **error_metrics(predicted, test[TARGET_COLUMN]), **model.diagnostics})
            corner_checks.append(_corner_table(model, int(case)))
    models, fixed_scores, fixed_predictions = {}, [], []
    for method in METHODS:
        degree, scores, pred = choose_degree(data, method, config)
        fixed_scores.append(scores); fixed_predictions.append(pred)
        models[method] = fit_pce(data[list(INPUT_COLUMNS)], data[TARGET_COLUMN], degree,
                                 monotonic=method == "monotonicity", config=config)
        corner_checks.append(_corner_table(models[method], "all_data"))
    prediction_table = pd.concat(predictions, ignore_index=True)
    metrics = pd.DataFrame([{"method": method, **error_metrics(group.predicted_C, group.measured_C)}
                           for method, group in prediction_table.groupby("method", sort=False)])
    return {"models": models, "predictions": prediction_table, "metrics": metrics,
            "folds": pd.DataFrame(folds), "selection": pd.concat(selection, ignore_index=True),
            "fixed_degree_scores": pd.concat(fixed_scores, ignore_index=True),
            "fixed_degree_predictions": pd.concat(fixed_predictions, ignore_index=True),
            "corner_checks": pd.concat(corner_checks, ignore_index=True)}


def _corner_table(model, fold):
    values = model.lower+(VERTICES+1)*(model.upper-model.lower)/2
    derivatives = model.gradient(values)
    records = []
    for i, vertex in enumerate(values):
        for axis, name in enumerate(INPUT_COLUMNS):
            records.append({"held_out_case": fold, "method": model.method, "degree": model.degree,
                            "vertex": i, "input": name, "derivative_physical": derivatives[i, axis],
                            "signed_derivative_normalized_C": derivatives[i, axis]*SIGNS[axis]
                              *(model.upper[axis]-model.lower[axis])/2,
                            **dict(zip(INPUT_COLUMNS, vertex))})
    return pd.DataFrame(records)


def run_pce(data_path: Path, output: Path, config=DEFAULT_PCE_CONFIG):
    data_path, output = Path(data_path), Path(output)
    if output.resolve().is_relative_to(Path("data/raw").resolve()) or data_path.resolve().is_relative_to(output.resolve()):
        raise DatasetValidationError("PCE output must be outside raw data and must not contain the source.")
    data = load_observations(data_path)
    if TARGET_COLUMN not in data:
        raise DatasetValidationError(f"Missing measured target: {TARGET_COLUMN}")
    data[TARGET_COLUMN] = pd.to_numeric(data[TARGET_COLUMN], errors="coerce")
    if not np.isfinite(data[TARGET_COLUMN]).all():
        raise DatasetValidationError("Measured temperature targets must be finite; no rows are dropped.")
    try:
        result = compare_pce(data, config)
    except ValueError as exc:
        raise DatasetValidationError(str(exc)) from exc
    output.mkdir(parents=True, exist_ok=True)
    for name, table in result.items():
        if isinstance(table, pd.DataFrame):
            table.to_csv(output/f"{name}.csv", index=False)
    x = data[list(INPUT_COLUMNS)].to_numpy()
    z = 2*(x-x.min(axis=0))/(x.max(axis=0)-x.min(axis=0))-1
    design_info = []
    for degree in (1, 2):
        A = basis(z, indices(degree))
        design_info.append({"degree": degree, "rows": len(x), "coefficients": A.shape[1],
                            "rank": int(np.linalg.matrix_rank(A)), "condition_number": float(np.linalg.cond(A))})
    pd.DataFrame(design_info).to_csv(output/"design_diagnostics.csv", index=False)
    models = {name: model.to_dict() for name, model in result["models"].items()}
    (output/"models.json").write_text(json.dumps(models, indent=2)+"\n", encoding="utf-8")
    evidence = {"source": data_path.as_posix(), "source_sha256": hashlib.sha256(data_path.read_bytes()).hexdigest(),
                "observations": len(data), "input_order": list(INPUT_COLUMNS), "target": TARGET_COLUMN,
                "config": asdict(config), "derivative_signs": SIGNS.tolist(),
                "derivative_sign_status": "assumed at fixed other inputs; fan ordering needs independent confirmation",
                "synthetic_temperature_targets": 0, "constraint_vertices_per_fit": 8,
                "constraint_domain": "training-only min/max box; shape prior, not validated control support",
                "selection": "inner case-wise RMSE selects total degree 1/2 separately for each method",
                "evaluation": "outer leave-one-case-out; early internal check, not fresh external data",
                "metrics": result["metrics"].to_dict("records"),
                "final_degrees": {k: v.degree for k,v in result["models"].items()},
                "design_diagnostics": design_info,
                "fit_count": 2*len(config.degrees)*5*4+2*5+2*len(config.degrees)*5+2,
                "legacy_thermal_rule_used": False, "regularization": "none"}
    (output/"manifest.json").write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    _write_pce_report(output, evidence, result)
    from thermal_twin.monotonic_pce_plots import plot_comparison
    plot_comparison(result, output)
    metrics = result["metrics"].set_index("method")
    fixed = result["fixed_degree_scores"].set_index(["method", "degree"])
    text = ("% Generated by fit-pce; do not edit.\n"
            f"\\newcommand{{\\ordinaryPceRmse}}{{{metrics.loc['ordinary','RMSE_C']:.2f}}}\n"
            f"\\newcommand{{\\monotonicPceRmse}}{{{metrics.loc['monotonicity','RMSE_C']:.2f}}}\n"
            f"\\newcommand{{\\ordinaryPceMaxError}}{{{metrics.loc['ordinary','max_abs_error_C']:.2f}}}\n"
            f"\\newcommand{{\\monotonicPceMaxError}}{{{metrics.loc['monotonicity','max_abs_error_C']:.2f}}}\n"
            f"\\newcommand{{\\finalMonotonicDegree}}{{{result['models']['monotonicity'].degree}}}\n"
            f"\\newcommand{{\\linearPceRmse}}{{{fixed.loc[('ordinary',1),'RMSE_C']:.2f}}}\n"
            f"\\newcommand{{\\ordinaryQuadraticRmse}}{{{fixed.loc[('ordinary',2),'RMSE_C']:.2f}}}\n"
            f"\\newcommand{{\\monotonicQuadraticRmse}}{{{fixed.loc[('monotonicity',2),'RMSE_C']:.2f}}}\n")
    (output/"slide_metrics.tex").write_text(text, encoding="utf-8")
    return result


def _write_pce_report(output, evidence, result):
    def rows(frame, columns):
        return "\n".join("| "+" | ".join(f"{value:.3f}" if isinstance(value, float) else str(value)
                                          for value in row)+" |" for row in frame[columns].itertuples(index=False,name=None))
    metric_rows = rows(result["metrics"], ["method", "n", "RMSE_C", "MAE_C", "max_abs_error_C"])
    fixed_rows = rows(result["fixed_degree_scores"], ["method", "degree", "RMSE_C", "max_abs_error_C"])
    fold_rows = rows(result["folds"], ["held_out_case", "method", "degree", "RMSE_C", "outside_training_box"])
    report = f"""# PCE with monotonicity constraints

## Method

Use the same **{evidence['observations']} measured operating observations** and target:
maximum of the 18 CPU interval averages. No synthetic temperature targets, fitted
thermal-resistance teacher, PDE residual, or physics-loss penalty is used.

Fit a normalized Legendre total-degree PCE by unregularized least squares.
Monotonicity constraints require temperature to be nondecreasing in CPU power and
inlet temperature, and nonincreasing in raw fan signal, with other inputs fixed.
These are working assumptions, not effects established by this correlated dataset.
The fan ordering must be checked independently. Flat responses are allowed.

For degrees 1 and 2, each first derivative is affine or constant. Its extrema over
the training min/max box occur at the eight vertices. The 24 vertex inequalities
are linear in PCE coefficients, so fitting is a convex quadratic problem. SLSQP uses
analytical gradients and a feasible constant starting polynomial. Solver success
and signed derivative feasibility are checked; failed fits raise an error.
Numerical tolerance is {evidence['config']['feasibility_tolerance']:g} C per normalized coordinate.
Vertices contain **no temperature labels** and never enter the data objective.
The box may include untested combinations; the imposed shape is not validation or
a safe-control certificate. No sign guarantee is claimed outside that box.

## Early comparison: separate degree choice from scoring

In each of five outer tests, keep a whole experimental case out. For each method,
choose degree 1 or 2 by pooled inner leave-one-training-case-out RMSE; exact ties
choose the lower degree. Refit on the four training cases and predict the fifth.
Every inner/outer fit derives scaling and the constraint box from its own training
rows only. All held-out rows are scored, including extrapolation outside training
bounds; these are flagged rather than silently removed or clipped.

| Method | Predictions | RMSE (C) | MAE (C) | Largest absolute error (C) |
| --- | --- | --- | --- | --- |
{metric_rows}

| Held-out case | Method | Selected degree | RMSE (C) | Rows outside training box |
| --- | --- | --- | --- | --- |
{fold_rows}

## Fixed-degree diagnostics (not a new independent test)

| Method | Fixed degree | Case-wise RMSE (C) | Largest absolute error (C) |
| --- | --- | --- | --- |
{fixed_rows}

All-data model selection repeats the case-wise degree comparison on the 19 training
rows, then refits. Selected degrees: **{evidence['final_degrees']}**. Both select degree 1
and their final coefficients coincide to numerical precision on this dataset.
The small nested-score improvement comes from the constrained method selecting a
quadratic in one outer case. It does not establish a reliable general improvement.
The unconstrained quadratic is especially unstable; monotonicity limits its shape
but does not remove missing coverage, noise or uncertainty in the assumptions.

This remains an early internal comparison: the dataset already informed project
development. New measurements are required for a genuinely fresh final test.
Coefficients retain their uniform-reference moment interpretation; that is not a
measured disturbance distribution or a model-error estimate. Live optimization
remains disabled until operating support and prediction-error bounds are justified.

## Artifacts and reproduction

`models.json`: coefficients, exact bounds, degree, solver diagnostics and reference
moments. CSVs: outer predictions, train/test IDs, inner scores, fixed-degree checks,
and vertex derivative checks. `manifest.json`: source hash, assumptions, configuration.
There are {evidence['fit_count']} fits in this complete comparison; no simulator runs.

    thermal-twin fit-pce

From an unreinstalled source checkout:

    .\\.venv\\Scripts\\python.exe -B scripts/fit_monotonic_pce.py

The archived thermal-rule artifacts are preserved for provenance, but are not used
by this path. Method reference: Sharma, Novak and Shields, physics-constrained PCE,
https://arxiv.org/abs/2402.15115 . Numerical implementation: SciPy SLSQP / LinearConstraint.
"""
    (output/"report.md").write_text(report, encoding="utf-8")
