# Change to PCE with monotonicity constraints

The current method fits the **same 19 measured temperature targets**. It replaces
the fitted thermal-resistance formula, formula-generated temperature targets and
mixed physics loss. Historical experiments and reviews remain archived.

## Presentation changes (new slide numbers)

| Slide | Change and reason |
| --- | --- |
| 6, Polynomial Chaos Expansion | Clarified the implementation: normalized Legendre PCE fitted with SciPy; UQLab remains the input-model/UQ framework. |
| 7, Polynomial Chaos Expansion: Advantages | Added monotonicity constraints as shape guidance that preserves the PCE basis and coefficient moment formulas. |
| 14, Input distributions | Used easier wording: the uniform reference gives equal weight across each range. It is not a measured operating probability distribution. |
| 15, PCE with monotonicity constraints | Replaced the earlier thermal rule and mixed loss. Showed the three derivative signs, measured-data least squares, fixed-other-input interpretation, allowance for flat responses, and eight derivative-check corners without temperature labels. Flagged the assumed fan ordering and the distinction between sensible shape and validated accuracy/safety. |
| 16, Early PCE comparison | Replaced the old thermal-formula score with paired plots of predictions against measurements. Reported nested case-wise RMSE 5.76 C vs 5.55 C and largest absolute error 12.21 C for both. Degree selection happens inside training cases. Eight of 19 test inputs fall outside the corresponding training box. Both final fits select degree 1 and coincide; the small score change is not a proven general gain. |
| Old 17, generated-target diagnostics | Removed this slide. Generated temperatures do not enter the new method. Subsequent main slides move forward by one number. |
| 17, Conditional inlet-temperature moments | Labelled the numerical quadratic as an illustration, since the actual selected model is linear. Limited the illustrative inlet half-width to 0 < delta <= 2 C so that this local curve respects the increasing-temperature assumption. Explained that the actual degree-1 model has b2 = 0. |
| 20, Digital Twin Definition | Updated the model row to the implemented PCE with monotonicity constraints and selected degree 1. |
| 21, Digital Twin Workflow | Replaced the earlier PI-PCE fitting label with PCE plus monotonicity. Operational optimization remains a proposal. |
| 22, Conclusion and Outlook | Replaced the earlier thermal-formula result with the measured-only PCE comparison. New experiments must test the monotonicity assumptions, prediction errors and operating domain. |
| 25, Degree choice and conditioning | Linked the degree-1/2 design diagnostics to the current PCE outputs. Retained the qualified degree-counting argument. |
| 26, What the control bound requires | Removed the obsolete thermal-teacher wording; independent validation must assess errors and missing physics in the final PCE. |
| 27, Bibliography | Added the physics-constrained PCE method reference and SciPy linear-constraint/SLSQP documentation. Removed references specific to the abandoned formula-fitting/generated-target method. |
| 28, Data provenance | Replaced the old generated-target policy with measured-target model artifacts and the fan-ordering assumption. All 19 targets, including six temperature flags, are preserved. |
| 29, Monotonicity constraints across the input range | Added the degree-1/2 argument: each first derivative is affine, so its signs at eight box corners suffice throughout that box, to numerical tolerance. This gives 24 linear inequalities, not extra training targets. |
| 30, Fair comparison of the two PCE fits | Added the inner/outer case-wise protocol, train-only scaling and constraint bounds, and fixed-degree diagnostics. Explained the unstable ordinary quadratic and why the early score difference does not establish reliable superiority. |

The deck has **23 main slides and 7 backup slides**. The cover date remains
01.12.2026. The RWTH template is retained. The prediction-slide layout was checked
after rendering and adjusted to keep its notes above the footer.

## Implementation and evidence

- Added `src/thermal_twin/monotonic_pce.py`, plotting support and
  `configs/pce_config.py`. Added the `fit-pce` CLI command and
  `scripts/fit_monotonic_pce.py` for an unreinstalled checkout.
- Three assumed derivative signs: CPU power positive, inlet temperature positive,
  raw fan signal negative, with other inputs fixed. Zero derivatives are allowed.
- Minimize measured squared error subject to the signs. Total degrees 1 and 2;
  normalized Legendre basis; no physics-loss weight, fitted thermal teacher, PDE
  residual, synthetic temperature labels or ridge regularization.
- Eight corners per fit enforce 24 linear inequalities with SciPy SLSQP and
  analytic derivatives. Verify convergence and feasibility; fail rather than
  silently accepting an invalid constrained fit. Sign tolerance is 1e-6 C per
  normalized input coordinate. No guarantee outside that fit's training box.
- Compare methods with five outer held-out cases. Within each outer training set,
  choose degree using case-wise tests on those training cases alone. Recompute
  all scaling and bounds within every fit. Score every outer test observation.
- Write coefficients, exact ranges, predictions, model-choice scores, derivative
  checks, source hashes, plots and a report to `results/monotonic_pce/`. Slide
  metrics are imported from the generated `slide_metrics.tex`.
- Update the root and presentation READMEs. Mark earlier thermal-rule scripts
  and CLI help as archived/legacy. Do not use or overwrite their old results.

## Results and verification

| Early held-out comparison | Ordinary PCE | PCE with monotonicity constraints |
| --- | ---: | ---: |
| Predictions | 19 | 19 |
| RMSE [C] | 5.761 | 5.553 |
| Mean absolute error [C] | 4.901 | 4.486 |
| Largest absolute error [C] | 12.213 | 12.213 |
| Final selected degree | 1 | 1 |

The two final coefficient vectors are identical. The nested score change comes
from selecting a constrained quadratic in one outer case, rather than a linear
model. These are early internal checks on data already used during development;
new measurements are needed for a fresh final test. The errors are not safety bounds.

**157 tests passed**, including derivative checks, enforcement between corners,
failure handling, coefficient moments, serialization, held-out-case isolation,
CLI outputs and preservation of source bytes. The processed-data SHA-256 matches
the manifest (`c7e97366301e21139c4d1859d09d0c5be132042db7c30d6ebf8615a3ac91661d`).
The final outer/all-data constrained derivative checks are nonnegative to the
stated tolerance. PDF compilation and visual layout checks were also performed.

Reproduce from the repository root:

```powershell
.\.venv\Scripts\python.exe -B scripts/fit_monotonic_pce.py
.\.venv\Scripts\python.exe presentation/heatwise-thermal-twin/build.py
```
