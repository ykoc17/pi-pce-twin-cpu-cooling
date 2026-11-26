# HEATWISE air-cooling exploratory audit

This is descriptive analysis of the original five-minute measurements. No predictive
models, surrogate fits, steady-state selection, or parameter optimization were performed.
See `manifest.json` for source SHA-256 hashes, package versions, and analysis settings.

## Data quality

- Original dimensions: 1333 rows by 219 columns.
- Dimensions match the expected 1333 by 219 original CSV: True.
- Missing cells: 325; unlabeled transitions: 25.
- Exact duplicate rows after the first: 0.
- Repeated measurement vectors excluding time and case labels: 0.
  Repeated measurements are descriptive counts, not automatically erroneous duplicates.
- Duplicate timestamps: 0; invalid nonmissing
  timestamps: 0; missing timestamps: 0.
- Strictly increasing timestamps: True; all intervals exactly
  five minutes: True. Source order is retained.
- Observed time span: 2024-10-31 10:00:00 to 2024-11-05 01:00:00.
  Timestamps are source local time; the timezone is unspecified.
- Invalid case labels: 0; case labels disagreeing with
  CASES.csv windows: 0; case sample counts match: True.
- Nonfinite numerical values: 0; invalid numerical cells:
  0. Only the analysis copy treats these as missing.

Columns with missing source values:

| column | missing_count |
| --- | --- |
| case_id | 25 |
| cpu_power_W__srv8_cpu1 | 15 |
| cpu_power_W__srv8_cpu2 | 15 |
| cpu_utilisation_pct__srv8 | 15 |
| cpu_temp_C__srv8_cpu1 | 15 |
| cpu_temp_C__srv8_cpu2 | 15 |
| server_inlet_temp_C__srv8 | 15 |
| server_outlet_temp_C__srv8 | 15 |
| dimm_temp_C__srv8_sensor1 | 15 |
| dimm_temp_C__srv8_sensor2 | 15 |
| dimm_temp_C__srv8_sensor3 | 15 |
| dimm_temp_C__srv8_sensor4 | 15 |
| pch_temp_C__srv8 | 15 |
| server_fan_speed_rpm__srv8_fan1 | 15 |
| server_fan_speed_rpm__srv8_fan2 | 15 |
| cpu_freq_Hz__srv8_cpu1_mean | 15 |
| cpu_freq_Hz__srv8_cpu1_max | 15 |
| cpu_freq_Hz__srv8_cpu1_min | 15 |
| cpu_freq_Hz__srv8_cpu2_mean | 15 |
| cpu_freq_Hz__srv8_cpu2_max | 15 |
| cpu_freq_Hz__srv8_cpu2_min | 15 |

`tables/missing_values.csv` covers every original column; `numerical_ranges.csv`
contains finite-value distributions, quantiles, and unique counts. Timestamp anomalies
and exact duplicate source records have separate tables, even when empty.

## Inputs and measured airflow

Finite-value ranges over all original rows, including transitions:

| column | count | min | median | max |
| --- | --- | --- | --- | --- |
| total_cpu_power_W | 1333 | 329 | 1315 | 2312 |
| server_inlet_air_temp_tunnel_C | 1333 | 23.4 | 44.8 | 46.4 |
| tunnel_fan_power_raw | 1333 | 0.117 | 0.358 | 0.766 |
| tunnel_airflow_m3_h | 1333 | 169 | 274 | 373 |

CPU power is the sum reported across the 18 CPUs, inlet temperature is the wind-tunnel
measurement before the servers, and airflow is the measured venturi-meter signal
in m3/h. Fan signal is on its original, unverified-unit scale. Tables retain
within-case distributions rather than treating these marginal ranges as a tested box.

## CPU temperatures

All 18 individual sensors are analyzed in `grouped_statistics.csv` and displayed in
`figures/all_cpu_temperatures.*`. Their overall observed range is
32–95 C.
There are 15 timestamps with fewer than 18
finite CPU readings. `cpu_temp_max_C` is missing for those timestamps; it is the
confirmed maximum across all 18 CPUs only when all readings are available.
The strict maximum ranges from 36 to 95 C.
`cpu_temp_observed_max_C` separately records the maximum of available sensors,
which can understate the true system maximum. Neither missing readings nor maximum
temperatures are imputed. `tables/audit_timeseries.csv` retains every timestamp,
all CPU sensors, both maxima, input values, airflow, and the valid-sensor count.

## Five experimental cases and actual coverage

Only air-cooling entries for `ocp_air_cooling_5min.csv` are selected from CASES.csv;
hybrid cases 6–8 are excluded. Windows are inclusive and checked against existing labels.

| case_id | Inlet setpoint (C) | DP setpoint (Pa) | Rows | Fan raw min | Fan raw max | CPU W min | CPU W max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 25 | 2 | 249 | 0.12 | 0.145 | 359 | 1904 |
| 2 | 35 | 4 | 304 | 0.213 | 0.266 | 360 | 1923 |
| 3 | 45 | 6 | 237 | 0.338 | 0.391 | 370 | 2208 |
| 4 | 45 | 8 | 309 | 0.481 | 0.581 | 363 | 1995 |
| 5 | 45 | 10 | 209 | 0.677 | 0.766 | 329 | 2218 |

The designed regimes are (inlet setpoint C, differential-pressure setpoint Pa):
(25, 2), (35, 4), (45, 6), (45, 8), and (45, 10). CASES.csv and the source README label
this setpoint kPa, but the measured `tunnel_diff_pressure_WT3_SA3_Pa` is documented in Pa
with high confidence and follows the same 2-10 values, so Pa is used here. The source
column name `dp_setpoint_kPa` is kept unchanged; confirm the unit with the data owners.
**Differential pressure is not fan power.** Each case has a narrow observed raw fan-signal band and a broad CPU
load range. Dataset notes describe 100%, 75%, 50%, 25%, and idle stress-ng steps;
the audit does not infer exact load plateaus or equate CPU watts to those percentages.
Measured inlet temperatures vary within cases, including adjustment transients.
Case labels describe curated setpoint stretches and do not certify thermal equilibrium
after every load or setpoint change. Full measured ranges per case are in `case_summary.csv`.

The three PCE inputs were **not varied independently over a full factorial design**.
For example, the high-fan bands in cases 4–5 were tested around the 45 C inlet
setpoint, not at 25 or 35 C. Combining their fan values with a 25 C inlet creates
an untested operating regime even if every coordinate is inside its individual range.
CPU power was swept within the five case trajectories; a min/max box for a case
does not mean every continuous triple inside it was measured.

The five-bin-per-axis, equal-width measured-domain grid has 31 occupied
cells out of 125. Bin occupancy is resolution-dependent and is only a
coverage diagnostic, not a safety boundary or a measure of physical feasibility.
`observed_input_combinations.csv` lists actual complete labeled triples with counts;
`coverage_grid.csv` includes empty cells. Transition rows appear in time-series and
scatter plots, but are excluded from case-domain occupancy and the input correlation matrix.

## Input dependencies and measured airflow

Pairwise-complete correlations on labeled cases:

| first | second | pairwise_complete_rows | pearson_r | spearman_rho |
| --- | --- | --- | --- | --- |
| total_cpu_power_W | server_inlet_air_temp_tunnel_C | 1308 | 0.0632245 | 0.192941 |
| total_cpu_power_W | tunnel_fan_power_raw | 1308 | 0.0721316 | -0.0345935 |
| server_inlet_air_temp_tunnel_C | tunnel_fan_power_raw | 1308 | 0.837545 | 0.808003 |
| tunnel_fan_power_raw | tunnel_airflow_m3_h | 1308 | 0.983763 | 0.996141 |

Pearson and Spearman correlations are also reported for all rows, transitions, and
each individual case in `input_dependencies.csv`. Sample counts accompany every
pair; undefined correlations for constant or insufficient data remain missing.
Pooled relationships mix setpoint changes with within-case behavior. Near-zero
correlation does not establish independence, and strong pooled correlation does
not establish causality. Time samples are serially dependent, so this report does
not attach independent-sample p-values to them.

Within-case CPU-power versus raw-fan Pearson correlations range from
-0.974 to -0.433; compare these with the
pooled value in the table. For this dataset the pooled near-zero correlation
conceals strong negative dependencies within cases. The experiment's operating
sequence and controlled setpoints must be considered before assigning independent
input distributions. No causal interpretation or fitted fan law is claimed.

Fan signal versus measured venturi airflow is shown using observed points, by case,
with no fitted curve. It describes this experiment and does not calibrate fan energy.
Classical independent-input PCE and Sobol assumptions must be examined before
later analysis: drawing the three marginal distributions independently would
generate combinations absent from this experiment.

## Unverified fan-power unit

The unit of tunnel_fan_power_raw is unverified. DATA_DICTIONARY.csv lists unit='unverified' and low confidence. Values are retained on their raw scale; they are not converted to W or kW and cannot support calibrated fan-energy costs.

The selected dictionary entry gives unit `unverified`, confidence
`low`, and description: Wind-tunnel fan power; values 0.1-0.9 suggest kW or normalised, unit NOT verified (paper quotes ~40 W)
The original source-column name is retained in `tables/variable_metadata.csv`;
an original label containing W does not verify the curated signal's unit.
Every figure labels this axis as a raw fan signal with unverified unit.

## Why extrapolation is dangerous

The observed data support only the measured case trajectories and their sampled
load steps. Neither separate marginal limits, occupied coarse bins, nor even an
enclosing convex hull establish support for arbitrary joint operating points.
Gaps between inlet/fan regimes remain untested. An eventual surrogate could give
smooth, precise-looking predictions there without experimental validation;
temperature-limit and energy-optimization decisions would then be unsupported.
Further experiments or independently validated physics are needed to assess those
combinations. The five-minute acquisition/averaging convention is unspecified,
steady-state intervals still require a separate selection step, and all observed
temperature extrema are measurements rather than validated operating limits.

## Reproduction and outputs

Run `thermal-twin audit` from the repository root after installation. Tables are
CSV files, figures are 300-dpi PNG and PDF, and all outputs are under this directory.
No raw input is overwritten. Analysis uses numeric coercion only in memory,
pairwise-complete correlations, and complete labeled input tuples for coverage.
Figure colors consistently identify cases; gray points/background identify transitions
or missing sensor values as described in each figure. No random sampling is used.
