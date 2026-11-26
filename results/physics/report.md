# Three-constant thermal-resistance rule and check points

Fitted to **19 accepted operating observations** from `data/processed/steady_state.csv`.
The preprocessing selection is unchanged.

    T_phys = T_inlet + offset + P_CPU * K * (F / F_ref)**(-gamma)

| Constant | Value | Linearized standard error |
| --- | --- | --- |
| offset (C) | 3.584 | 2.284 |
| K (C/W) | 0.03207 | 0.00188 |
| gamma | 0.3252 | 0.0363 |
| F_ref (raw fan signal) | 0.356111 | training median, not fitted |

## Fitting method

Bounded nonlinear least squares (`scipy.optimize.least_squares`, K >= 0, gamma > 0)
minimizes squared errors to the steady-state targets from 3 starting points.
F_ref is the median training fan signal. Every validation fold refits all constants
and F_ref on the four training cases only.

The rule uses total power of 18 CPUs to approximate the hottest CPU, so K is an
effective resistance. The fan-signal unit is **unverified**; only the dimensionless
ratio F/F_ref enters.

## Errors

| | RMSE (C) | MAE (C) | Max abs error (C) | R2 |
| --- | --- | --- | --- | --- |
| Training, all 19 | 3.35 | 3.10 | 5.19 | 0.959 |
| Held-out cases, pooled | 3.45 | 3.14 | 5.76 | 0.956 |

| Held-out case | n | RMSE | MAE | Max abs | offset | K | gamma | F_ref | Inputs outside training range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 | 4.53 | 4.40 | 5.67 | 4.50 | 0.0310 | 0.324 | 0.3684 | server_inlet_air_temp_tunnel_C, tunnel_fan_power_raw |
| 2 | 4 | 3.46 | 3.25 | 5.09 | 3.66 | 0.0316 | 0.325 | 0.3684 | total_cpu_power_W |
| 3 | 5 | 3.37 | 3.06 | 5.76 | 3.26 | 0.0365 | 0.317 | 0.2499 | server_inlet_air_temp_tunnel_C |
| 4 | 4 | 2.85 | 2.73 | 3.28 | 3.27 | 0.0359 | 0.326 | 0.2566 | none |
| 5 | 2 | 1.86 | 1.40 | 2.63 | 3.29 | 0.0323 | 0.329 | 0.3526 | total_cpu_power_W, tunnel_fan_power_raw |

Per-fold R2 in `tables/case_validation.csv` rests on 2-5 observations.

## Why three constants

A four-constant rule adds R0 to the bracket: R_th = R0 + K (F/F_ref)^(-gamma).

| Observations | n | Constants | Training RMSE | Held-out RMSE | Held-out max abs | Max parameter correlation | gamma across folds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_accepted | 19 | 3 | 3.35 | 3.45 | 5.76 | 0.923 | 0.32 to 0.33 |
| all_accepted | 19 | 4 | 3.35 | 4.48 | 13.26 | 0.997 | 0.32 to 0.95 |
| sensitivity_without_throttled | 13 | 3 | 1.02 | 1.26 | 3.18 | 0.915 | 0.27 to 0.29 |
| sensitivity_without_throttled | 13 | 4 | 1.01 | 2.47 | 5.44 | 0.999 | 0.32 to 0.82 |

Correlations near 1 mean the data cannot separate the constants. R0 was dropped after
seeing these held-out errors, so they are slightly optimistic for the chosen rule.

## CPU throttling

Some targets sit near 94 C because CPUs reduce frequency and power at that temperature;
there, temperature no longer responds freely to power. The main fit keeps all accepted
observations. `sensitivity_without_throttled` drops targets of at least
93.5 C for comparison only. Selecting by target value is
biased, and no observation is removed from `steady_state.csv`.

## Physical monotonicity

- Temperature rises with CPU power: True.
- Temperature falls with fan signal: True.

Checked analytically at all observations and all check points.

## Check points

`tables/check_points.csv` holds 128 scrambled Sobol input combinations over the
reference ranges (fixed seed), with T_phys from the rule. They are targets for the physics
part of a physics-informed loss. **They are not measurements**: they add no experimental
information, and untested regions rest on the rule alone. 10 of them exceed the highest
measured target, where real CPUs would throttle. For validation, refit the rule and
recompute T_phys inside every fold.

No PCE or physics-informed PCE is fitted in this step.

## Reproduce

```
thermal-twin fit-physics
```
