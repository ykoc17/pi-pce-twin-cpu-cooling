# PCE with monotonicity constraints

## Method

Use the same **19 measured operating observations** and target:
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
Numerical tolerance is 1e-06 C per normalized coordinate.
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
| ordinary | 19 | 5.761 | 4.901 | 12.213 |
| monotonicity | 19 | 5.553 | 4.486 | 12.213 |

| Held-out case | Method | Selected degree | RMSE (C) | Rows outside training box |
| --- | --- | --- | --- | --- |
| 1 | ordinary | 1 | 8.943 | 4 |
| 1 | monotonicity | 1 | 8.943 | 4 |
| 2 | ordinary | 1 | 3.839 | 1 |
| 2 | monotonicity | 1 | 3.839 | 1 |
| 3 | ordinary | 1 | 3.652 | 1 |
| 3 | monotonicity | 2 | 2.097 | 1 |
| 4 | ordinary | 1 | 5.275 | 0 |
| 4 | monotonicity | 1 | 5.275 | 0 |
| 5 | ordinary | 1 | 6.076 | 2 |
| 5 | monotonicity | 1 | 6.076 | 2 |

## Fixed-degree diagnostics (not a new independent test)

| Method | Fixed degree | Case-wise RMSE (C) | Largest absolute error (C) |
| --- | --- | --- | --- |
| ordinary | 1 | 5.761 | 12.213 |
| ordinary | 2 | 150.110 | 293.872 |
| monotonicity | 1 | 5.761 | 12.213 |
| monotonicity | 2 | 6.111 | 14.688 |

All-data model selection repeats the case-wise degree comparison on the 19 training
rows, then refits. Selected degrees: **{'ordinary': 1, 'monotonicity': 1}**. Both select degree 1
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
There are 112 fits in this complete comparison; no simulator runs.

    thermal-twin fit-pce

From an unreinstalled source checkout:

    .\.venv\Scripts\python.exe -B scripts/fit_monotonic_pce.py

The archived thermal-rule artifacts are preserved for provenance, but are not used
by this path. Method reference: Sharma, Novak and Shields, physics-constrained PCE,
https://arxiv.org/abs/2402.15115 . Numerical implementation: SciPy SLSQP / LinearConstraint.
