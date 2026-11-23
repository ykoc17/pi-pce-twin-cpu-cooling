# Review of steady-state selection

Reviewed 2026-11-23. The implementation and saved results agree with the stated
selection criteria. No change to the production selector, thresholds, raw data,
processed observations, or presentation was needed for this review.

## Verification

- Regenerated observations match `data/processed/steady_state.csv` exactly after
  the documented CSV formatting. The saved source/output SHA-256 hashes match.
- Regenerated candidate diagnostics and row selection labels match saved results.
- Independently enumerated every possible retained contiguous interval within
  all 25 detected candidates. Independently recalculated input excursions,
  per-CPU sample standard deviations, ranges, and linear-regression slopes.
  All 19 saved intervals are the longest admissible intervals; ties correctly
  choose the earliest start. Rejected candidates have no admissible interval.
- All accepted rows belong to cases 1-5, have finite readings for all three
  inputs and all 18 CPUs, and follow consecutive five-minute timestamps.
  No excluded transition or incomplete sensor row enters an observation.
- Every accepted interval starts at least 20 minutes after its detected candidate
  begins, retains at least 30 minutes, and passes both local and complete-interval
  checks. In this dataset the retained durations are actually **40-335 minutes**
  and delays from detected candidate start are **20-140 minutes**.
- Recalculated all three input means, all 18 CPU means, and every target. The
  target is correctly the maximum of CPU means, rather than the mean of
  instantaneous maxima.
- Full test suite: **118 passed**. Initial test attempts encountered temporary
  directory setup errors; the successful run used an accessible project-local
  temporary directory.

The independent interval checks reuse the production candidate boundaries but
do not call its stability-metric or interval-selection functions. Segmentation
itself is covered by synthetic step, ramp, workload-marker, gap, and spike tests
and was checked against the five-case traces. This is not an independent physical
identification of the true equilibrium boundaries.

## What the code means by stable

All limits are in `configs/preprocessing_config.py`. Each applies both over
the entire retained interval and in every contained 30-minute sliding window,
except for the deliberately different local/global drift limits.

| Quantity | Acceptance limit |
| --- | --- |
| CPU power peak-to-peak range | 40 W + 4% of the absolute interval mean |
| Inlet-temperature peak-to-peak range | 1 C |
| Raw fan-signal peak-to-peak range | 0.025 + 3% of the absolute interval mean |
| Each CPU's sample standard deviation | 1 C |
| Each CPU's peak-to-peak temperature range | 3 C |
| Each CPU's absolute full-interval linear drift | 0.03 C/min |
| Each CPU's absolute 30-minute-window linear drift | 0.08 C/min |

Among accepted intervals, the greatest per-sensor standard deviation is
**0.9074 C**, the greatest range is **3 C**, and the greatest absolute
full-interval drift is **0.02667 C/min**. No threshold is violated.
The nearest full-interval input-range limit is reached to **99.05%** of its
allowed excursion (candidate 6, CPU power).

The local drift tolerance is larger to accommodate quantized sensor readings.
A long accepted interval need not contain a 30-minute subinterval that also
passes the stricter *full-interval* drift limit: a short window is checked
against 0.08 C/min; the whole retained interval is checked against 0.03 C/min.
This distinction explains empty `passing_30min_target_span_C` entries in
`accepted_interval_checks.csv`; these are not invalid accepted observations.

## Counts and rejected periods

| Case | Detected candidates | Accepted observations | Accepted readings |
| --- | ---: | ---: | ---: |
| 1 | 5 | 4 | 60 |
| 2 | 5 | 4 | 116 |
| 3 | 5 | 5 | 108 |
| 4 | 5 | 4 | 92 |
| 5 | 5 | 2 | 45 |
| Total | 25 | 19 | 421 |

There are five candidates per case because the detector recovers the workload
steps in these experiments, not because five candidates are hardcoded. In
addition to the three input signals, `cpu_utilisation_pct__mean` is enabled as
an auxiliary change-detection marker. It is not an extra PCE input. Candidate
boundaries use 15-minute level-comparison windows and a 15-minute transition
guard. DP and CPU temperatures are not used to establish these boundaries.

| Rejected candidate | Case | Why it fails |
| --- | --- | --- |
| 2 | 1 | Every post-discard 30-minute window exceeds the 1 C standard-deviation limit in at least one CPU. Even the best window has a worst-sensor standard deviation of 1.069 C. |
| 7 | 2 | Same issue; best worst-sensor standard deviation is 1.272 C. |
| 17 | 4 | Some local windows pass, but no retained interval satisfies all complete-interval checks, including the stricter drift limit. |
| 22 | 5 | Every post-discard window exceeds the standard-deviation limit; best worst-sensor standard deviation is 1.134 C. |
| 23 | 5 | Some local windows pass, but no interval satisfies all complete-interval checks. |
| 25 | 5 | Every row has incomplete CPU readings; no complete-sensor dwell is available. |

The overview shows the instantaneous maximum temperature, while selection checks
all 18 CPU traces. An apparently flat maximum therefore does not imply that the
period passes. Orange also means **rejected or unselected**: other fragments can
be stable but are not emitted because only one longest interval is kept per
candidate. One green band correctly represents one processed observation.

## Sensitivity to the thresholds

The following independent exhaustive checks keep the candidate segmentation
fixed and change one criterion at a time. These are sensitivity checks, not
replacement datasets; the original 19-row output is unchanged.

| Configuration | Accepted observations |
| --- | ---: |
| Current defaults | 19 |
| Temperature standard deviation at most 0.75 C | 14 |
| Full-interval drift at most 0.02 C/min | 14 |
| Local drift at most 0.04 C/min | 15 |
| Retained dwell at least 60 minutes | 14 |
| Initial discard at least 40 minutes | 18 |

Detailed per-case results are in `threshold_sensitivity.csv`.

## Interpretation and recommendation

The selected intervals are reasonable observations of approximately steady
operation at five-minute resolution. The visual selection agrees with their
calculated metrics. The count of 19 is a consequence of the chosen thresholds,
not an intrinsic number of equilibria or independent experimental replicates.

The criteria establish measured stability, not proof of physical equilibrium.
For scale, 0.03 C/min corresponds to 1.8 C/hour; the global range and standard
deviation checks also constrain drift, but small remaining trends can pass.
Twenty minutes is a minimum discard, not a measured thermal time constant.
The longest passing interval can be an early quiet stretch rather than the
final settled tail of a physical plateau. Choosing intervals based on observed
temperature stability can also favor quiet portions of a noisy process.

Keep the current data as a reproducible baseline, describe it as
**approximately steady operating observations**, and retain the threshold
sensitivity results when assessing subsequent PCE conclusions. Stronger claims
about equilibrium require justified thermal tolerances or higher-resolution
measurements. Choose thresholds for acceptable thermal drift and averaging
error, rather than to achieve a desired training-set size. Validation should
respect case/time grouping and the unequal 40-335 minute averaging durations.

## Reproduce

From the project root with the installed virtual environment:

```powershell
.\.venv\Scripts\python.exe scripts/review_preprocessing.py
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tmp/pytest-selection-review
```

Create the `.tmp` parent directory before using that pytest command. The review
script writes its CSV checks under `results/preprocessing_review/` and does not
modify production preprocessing artifacts.
