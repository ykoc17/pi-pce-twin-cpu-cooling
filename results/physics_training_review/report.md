# Early physics-model accuracy check and training-only generated points

## What changed

The old 3.45 C RMSE helped choose three rather than four constants. It is an early
accuracy check, not a separate final test. Original results/physics files are preserved.

This new check leaves one complete experiment out. The other four alone choose
between three and four constants using inner case-wise tests. The selected formula
is refitted to those four, then predicts the experiment that was kept out.

Pooled outer RMSE: **4.489 C**. Largest absolute error:
**13.264 C**. These are thermal-rule results, not PCE results.
The full dataset already informed model development, so this remains an early
internal check. New experiments are needed for a genuinely fresh final test.

| Test case | Training rows | Test rows | Constants selected | Test RMSE (C) | Generated: excluded | Generated: withheld |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 15 | 4 | 4 | 7.600 | 9 | 119 |
| 2 | 15 | 4 | 4 | 3.730 | 9 | 119 |
| 3 | 14 | 5 | 3 | 3.369 | 11 | 117 |
| 4 | 15 | 4 | 3 | 2.852 | 10 | 118 |
| 5 | 17 | 2 | 3 | 1.863 | 11 | 117 |

## Generated-point policy

- Keep the existing full-data 128-point plot only as a diagnostic illustration.
  Its 10/118 split is not reused during testing.
- In every outer training set, refit the rule and fan reference, derive input
  bounds from training rows, and generate 128 points with the fixed Sobol seed.
- Screen against the maximum training target only. The cutoff is a diagnostic
  convention, not a known throttling or safety limit. Counts can differ by fold.
- Every generated point has physics-loss weight zero: excluded above the cutoff,
  otherwise withheld pending operating-domain/regime validation. None enters fitting.
- For future PCE tuning, repeat this preparation within each inner training split
  too. Do not use precomputed full-data labels or any held-out target/input to
  construct a training rule, ranges or screening cutoff.
- Compare measured-data-only PCE and the thermal rule before approving physics
  targets. Model-generated labels add assumptions, not experimental evidence.

## Reproduce

    .\.venv\Scripts\python.exe -B scripts/review_physics_training.py

Output CSVs record training/test period IDs, constants, ranges, cutoff, diagnostic
points and status. All original observations and fitted-model artifacts are unchanged.
