# Steady-state preprocessing diagnostics

Output: `data\processed\steady_state.csv`. Accepted operating observations: **19**.

| Case | Candidate periods | Accepted observations | Rejected periods | Accepted samples |
| --- | --- | --- | --- | --- |
| 1 | 5 | 4 | 1 | 60 |
| 2 | 5 | 4 | 1 | 116 |
| 3 | 5 | 5 | 0 | 108 |
| 4 | 5 | 4 | 1 | 92 |
| 5 | 5 | 2 | 3 | 45 |

## Selection algorithm

1. Retain only case IDs 1-5 with finite values for all three inputs. Unlabeled rows,
   invalid labels, and missing/invalid inputs are excluded and break continuity.
2. Break continuity on case changes, excluded rows, or any interval other than
   5 minutes. Within each continuous block, compare
   median input levels in two 15-minute windows,
   separated by a 15-minute transition guard. Both
   comparison windows must have approximately constant inputs. Sustained level
   differences define new candidates, including ramps whose individual steps are small.
   Nearby detections less than 30 minutes
   apart are consolidated to the strongest change, with earliest-start tie breaking.
   Isolated spikes do not establish new operating levels. No required number of
   periods or workload percentages is hardcoded.
   If enabled and present, `cpu_utilisation_pct__mean` supplies additional workload-change
   evidence. It is a segmentation marker only, never a PCE input or a temperature
   target. Missing marker values fall back to input-level evidence. Values above
   100 are retained without clipping or claiming calibrated workload percentages.
   No time sorting, interpolation, resampling, or missing-sensor imputation is performed.
   DP is not used; segmentation never examines CPU temperatures.
3. Discard the first 20 minutes after each candidate starts.
4. Require at least 30 minutes of retained consecutive,
   sensor-complete data AFTER that discard. Duration is end minus start, so seven
   five-minute samples span 30 minutes, rather than 35.
5. Check every CPU's sample standard deviation, peak-to-peak range, and absolute
   linear drift, plus peak-to-peak ranges of every input. These checks must pass
   both in every contained 30-minute sliding window
   and over the entire retained interval. Gradual drift cannot pass by chaining
   individually similar neighboring observations. Missing sensors break valid windows.
6. Select the longest passing interval per candidate period; equal lengths select
   the earliest start. Other stable fragments of that same period are not emitted
   as additional training rows. Overlapping stability windows are diagnostic only.

## Effective thresholds

All defaults and validation rules live in `configs/preprocessing_config.py`.
The exact effective values, including CLI overrides, are saved in `manifest.json`.

```json
{
  "sample_interval_minutes": 5.0,
  "minimum_dwell_minutes": 30.0,
  "initial_settling_minutes": 20.0,
  "stability_window_minutes": 30.0,
  "level_comparison_window_minutes": 15.0,
  "transition_guard_minutes": 15.0,
  "minimum_change_separation_minutes": 30.0,
  "use_workload_marker": true,
  "workload_step_pct": 10.0,
  "workload_range_pct": 10.0,
  "cpu_power_step_abs_W": 80.0,
  "cpu_power_step_relative": 0.04,
  "inlet_temperature_step_C": 1.0,
  "fan_power_step_raw": 0.06,
  "cpu_power_range_abs_W": 40.0,
  "cpu_power_range_relative": 0.04,
  "inlet_temperature_range_C": 1.0,
  "fan_power_range_abs_raw": 0.025,
  "fan_power_range_relative": 0.03,
  "cpu_temperature_std_C": 1.0,
  "cpu_temperature_range_C": 3.0,
  "cpu_temperature_window_drift_C_per_minute": 0.08,
  "cpu_temperature_drift_C_per_minute": 0.03
}
```

Differences between CPU median levels use absolute + relative *
max(abs(previous level), abs(following level)).
Input range limits use absolute + relative * abs(interval mean). Inlet and fan
step limits are absolute. Fan power remains an **unverified-unit raw signal**;
these tolerances do not imply watts or kilowatts. All 18 CPU sensors must be finite.
Temperature checks are per sensor, not just checks of the hottest CPU.
The rolling drift limit (0.08 C/min)
allows short-window apparent slopes from one-degree sensor steps. The full-interval
limit remains stricter (0.03 C/min).
Local jitter tolerance never substitutes for the full-interval drift check.
The default 30-minute thermal window reduces sensitivity to short-window sensor
quantization; the default per-CPU standard-deviation limit is 1 C, rather than
requiring an almost constant quantized reading. The 3 C temperature-range limit,
0.03 C/min full-period drift limit, 20-minute initial discard, 30-minute retained
dwell, and complete-18-sensor requirement remain in force. Defaults describe
stationary measured fluctuations and must still be reviewed as heuristics, not
as a calibrated proof of physical equilibrium or a way to obtain a desired count.

## Aggregation and target

Each output row averages the three inputs and each of the 18 CPU temperatures over
the SAME retained timestamps. Original input and CPU column names contain these
period means. `equilibrium_max_cpu_temp_C` is the **maximum of the 18 CPU means**.
It is not the time average of instantaneous system maxima; the latter is retained
only as a diagnostic column. Per-CPU standard deviations and drifts, maximum sensor
variability, timestamps, sample count, case, and candidate identity are recorded.

## Sample accounting

- rejected_unstable_or_unselected: 776 rows
- accepted: 421 rows
- discarded_initial_settling: 96 rows
- excluded_unlabeled_transition: 25 rows
- excluded_incomplete_cpu_temperatures: 15 rows

Rejected candidate reasons:

- no_stable_window: 3 periods
- no_interval_meeting_full_stability: 2 periods
- no_contiguous_complete_sensor_dwell: 1 periods

`row_diagnostics.csv` accounts for every original CSV row, including source record
number, raw case label, complete-sensor flags, rolling checks, and final selection.
`period_diagnostics.csv` records every candidate, acceptance or rejection reason,
candidate and retained bounds, and full-interval stability metrics for accepted data.
`figures/` contains an overview and a figure for each present case in PNG and PDF,
showing accepted, rejected, discarded-settling, and excluded measurements on the
original time series. Gray crosses flag available-only temperature maxima when
some CPU readings are missing; they never contribute to accepted observations.

## Interpretation and limits

These are nonoverlapping operating-period observations, NOT a proof of statistical
independence. Successive periods can share thermal history, hardware, controls,
and measurement bias; later validation must still respect case/time grouping.
The counts above must not be read as independent random experimental replicates.
Missing inputs can fragment a physical run; candidate IDs and rejected fragments
are retained for review. Short physical plateaus may not provide enough evidence
for two-sided change detection or the required settling and dwell intervals.
Repeated operating conditions are
not merged across interruptions or cases.

The defaults are reproducible heuristics, not externally calibrated equilibrium
thresholds. They establish observed stability at five-minute resolution, not a
physical proof of equilibrium. The source does not specify whether five-minute
values were sampled or averaged. In particular, slow drift below configured
limits and sensor quantization can remain. No predictive models were fitted.
