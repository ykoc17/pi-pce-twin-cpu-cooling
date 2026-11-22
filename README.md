# thermal-twin

A reproducible Python project for a steady-state thermal digital twin using the
HEATWISE experimental dataset. The project provides dataset loading,
validation, `thermal-twin inspect`, descriptive exploration with `thermal-twin audit`,
steady-state preprocessing, and input probability models with `thermal-twin inputs`.
PCE, physics-informed PCE,
uncertainty quantification, Sobol analysis, and constrained optimization are
planned later steps and are not implemented here.

The distribution and CLI are named `thermal-twin`. The Python import package is
`thermal_twin`; setuptools generates `src/thermal_twin.egg-info` from the
distribution name by converting hyphens to underscores.

Dataset paths, expected dimensions, input and sensor names, and case IDs are
centralized in `configs/data_config.py`. The `configs` package is included in
installations alongside the src-layout `thermal_twin` package.

## Installation

Use Python 3.12 or newer (required by the local ETH UQLab.py port). Run these commands from the repository root. All packages
are installed with pip inside `.venv`.

Windows PowerShell:

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install .
python -m pip install ".[dev]"
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m pip install '.[dev]'
```

The second install adds pytest. Runtime dependencies include NumPy, pandas, SciPy,
scikit-learn, matplotlib and the official ETH **UQLab.py 0.800** (`uqlab` on PyPI).
UQLab.py requires pandas >=3.0.3 and installs its core dependencies, including
seaborn and quadprog. Its optional PyTorch/GPyTorch extras are not installed.
This is the local Python implementation, not the older cloud client `uqpylab`;
no account, authentication token, MATLAB installation or data upload is needed.
See the [official package](https://pypi.org/project/uqlab/0.800/).

`requirements-lock.txt` records the exact runtime and test dependency versions
used for verification on Windows with Python 3.13.13. To reproduce those package
versions in a fresh, activated Python 3.13 environment, install with constraints:

```bash
python -m pip install -c requirements-lock.txt '.[dev]'
```

The version ranges in `pyproject.toml` allow compatible releases on other supported
Python versions; the lock file represents the tested Python 3.13 environment.

## Inspect the dataset

Keep the original dataset at `data/raw/ocp_air_cooling_5min.csv`, then run:

```bash
thermal-twin inspect
thermal-twin inspect --data data/raw/ocp_air_cooling_5min.csv
python -m thermal_twin inspect
```

The default path is relative to the current working directory. For execution
outside the repository root, pass an absolute path with `--data`.

Inspection checks the original CSV before any filtering:

- Exactly 1,333 data rows and 219 columns, with unique column names and consistent
  CSV record widths.
- All five experimental `case_id` values (1–5), with empty labels retained as
  transition rows. Other labels are rejected.
- Inputs `total_cpu_power_W`, `server_inlet_air_temp_tunnel_C`, and
  `tunnel_fan_power_raw` are present.
- Exactly 18 individual `cpu_temp_C__srv*_cpu*` columns: two CPUs for each of
  servers 1–9. Aggregate temperature columns do not count.
- Valid, nonmissing `time_local` timestamps in strictly increasing order, without
  duplicates, and exactly five minutes between every pair of consecutive rows.

Successful inspection prints dimensions, case counts, transition counts, inputs,
the CPU sensor count, and the time range. Errors identify missing files, columns,
or invalid data and return exit status 1. Invalid CLI arguments return status 2.
Raw data are only read: no sorting, dropping, resampling, imputation, or writes
are performed. Timestamp timezone is unspecified in the source and is not assumed.
The dataset notes mark `tunnel_fan_power_raw` as low confidence; inspection retains
its original values and does not assume a calibrated unit.

## Exploratory audit

```bash
thermal-twin audit
thermal-twin audit --data data/raw/ocp_air_cooling_5min.csv --output results/audit
```

`CASES.csv` and `DATA_DICTIONARY.csv` default to the directory containing the data
CSV. Override them with `--cases PATH` and `--dictionary PATH`. Audit outputs must
be outside the raw input directories. Run after installing or reinstalling the
package with `python -m pip install .`.

The command writes `results/audit/report.md`, quality and provenance JSON files,
CSV summary tables in `results/audit/tables/`, and six figures in
`results/audit/figures/`, each as a 300-dpi PNG and a PDF:

- Inputs and maximum CPU temperature over time, with experimental case shading.
- Pearson and Spearman input correlation matrices.
- Pairwise input scatter plots colored by case, with separate transition markers.
- Raw fan signal versus measured airflow.
- Observed three-dimensional operating-condition coverage by case.
- A heatmap of all 18 CPU temperature sensors, with missing readings shown in gray.

Tables cover missing values in every source column, finite numerical ranges,
duplicate records, timestamp intervals and anomalies, CASES.csv window/count
checks, per-case distributions of inputs/airflow/all 18 temperatures/the maximum,
pooled and within-case correlations with sample counts, the audited time series,
actual observed input combinations, a five-bin-per-axis coverage grid including
empty cells, and source dictionary entries. The audit reports time and case
defects rather than aborting on them; missing required variables and invalid
metadata produce errors. CSV dimensions are reported and checked against the
expected original shape without preventing inspection of a smaller/damaged file.

The unit of **`tunnel_fan_power_raw` is unverified** in DATA_DICTIONARY.csv and its
confidence is low. Its values remain on the raw scale, including in figure labels;
the audit does not convert them to watts or kilowatts. Calibrated fan-energy costs
cannot be derived from this signal without clarification from the data owners.

The confirmed maximum `cpu_temp_max_C` requires all 18 finite sensor readings.
For incomplete timestamps it remains missing; `cpu_temp_observed_max_C` separately
records the maximum of available sensors. Missing sensors are never imputed.
Transitions remain in descriptive time-series and scatter figures and are excluded
from case-domain coverage and the input correlation matrices. Correlations also
have separate all-row, transition, and within-case summaries.

The experimental regimes combine inlet/pressure setpoints (25 C, 2 kPa),
(35 C, 4 kPa), and (45 C, 6/8/10 kPa), with CPU loads stepped within each case.
Pressure setpoints are not fan-power values. These trajectories do not fill the
three-input domain: combining separately observed marginal extremes can create an
untested operating condition. The report explains joint input dependence,
unmeasured combinations, and why case ranges or occupied coarse bins cannot
justify extrapolation. Case membership alone does not establish steady state.
No predictive models are fitted.

## Steady-state preprocessing

```bash
thermal-twin preprocess
thermal-twin preprocess --min-dwell-minutes 45 --initial-settling-minutes 30
```

The command writes `data/processed/steady_state.csv` and a diagnostics report at
`results/preprocessing/report.md`. Override destinations with `--output PATH` and
`--diagnostics DIRECTORY`; `--data PATH` selects a different source CSV. Raw input
directories are protected against output writes. Reinstall the package after
changing code or defaults with `python -m pip install .`.

Every time and stability threshold is defined in `configs/preprocessing_config.py`.
The frozen `PreprocessingConfig` records the defaults; the effective configuration,
source/output SHA-256 hashes, and software versions are saved in the diagnostics
manifest. CLI overrides are available for `--min-dwell-minutes`,
`--initial-settling-minutes`, and `--stability-window-minutes`.

The deterministic algorithm:

1. Keeps only cases 1–5 with finite values for all three inputs, retaining source
   order. Case changes, excluded rows, and time gaps break continuity. Within a
   continuous block, sustained changes between approximately constant input-level
   windows identify new plateaus, even when a transition spans several samples.
   Median levels from two 15-minute windows are compared across a 15-minute
   transition guard. Nearby detections within 30 minutes are consolidated; isolated
   spikes do not become additional operating conditions. No period count is forced.
   The optional recorded `cpu_utilisation_pct__mean` marker helps identify workload
   changes when CPU power changes little. It is used only for segmentation; the
   three PCE inputs remain CPU power, inlet temperature, and raw fan power. Missing
   utilization does not discard valid data. Its above-100 values are not clipped
   or interpreted as calibrated workload percentages. DP is not used.
2. Discards the first 20 minutes of each candidate by default, then requires at
   least 30 minutes of consecutive, sensor-complete observations. Duration means
   last timestamp minus first timestamp: seven five-minute observations span 30 minutes.
3. Checks all three input ranges and every CPU's temperature standard deviation,
   peak-to-peak range, and absolute linear drift in 30-minute sliding windows AND
   over the full accepted interval. Both local and global checks must pass.
   The per-CPU standard-deviation limit is 1 C and the peak-to-peak limit is 3 C.
   The default rolling drift tolerance is 0.08 C/min to accommodate one-degree
   sensor steps in short windows; full-interval drift is limited to 0.03 C/min.
4. Retains the longest admissible interval within each candidate, breaking equal
   lengths by earliest start. It emits at most one row per candidate; overlapping
   stability windows and other stable fragments do not become additional rows.

No missing readings are imputed, and accepted intervals never bridge incomplete
CPU readings. The initial settling interval alone does not establish equilibrium.
All inputs and temperatures in the output are means over the same retained
timestamps. The target `equilibrium_max_cpu_temp_C` is **the maximum of the 18
individual CPU means**, rather than the average of instantaneous maxima.
The output includes start/end timestamps, elapsed duration, sample count, case,
candidate ID, hottest CPU, and per-sensor variability and drift.

Diagnostics include every original row's selection/exclusion status, all candidate
periods and rejection reasons, accepted counts per case, and PNG/PDF plots of the
accepted and rejected observations on the original input/temperature time series.
Fan signal remains on its unverified-unit raw scale. These configurable heuristics
establish observed stability at five-minute resolution, not physical proof of
equilibrium. Nonoverlapping operating periods are not necessarily statistically
independent replicates; later validation must still respect time and case grouping.

## Input distributions

After preprocessing and reinstalling the package:

```bash
thermal-twin inputs
thermal-twin inputs --data data/processed/steady_state.csv --output results/inputs
```

The command requires the current **19 accepted operating observations**, with all
five cases, finite inputs, unique period IDs and ordered, nonoverlapping intervals.
It never uses the original 1,333 time rows to estimate an input distribution and
never weights a period by duration or raw sample count. If preprocessing changes
the count, explicitly review `configs/input_config.py` and the modeling domain.

Two probability-model concepts stay separate:

- **A: assumed independent reference.** Each of the three inputs is uniform
  between its exact minimum and maximum among the 19 period means, without
  rounding or padding. UQLab.py creates an input object with an explicitly
  independent copula. Scaling to [-1,1] gives the normalized Legendre basis
  convention for later PCE/global UQ/classical Sobol studies. Independence is a
  chosen reference assumption, not a result of the experimental dependence tests.
- **B: optional dependent operating scenario.** A named JSON file specifies a
  Gaussian-copula **latent-normal** correlation matrix; it does not replace A.
  The same uniform marginals are retained. The forward/inverse Nataf transforms
  use UQLab.py public APIs. Matrices must be symmetric, unit-diagonal, positive
  definite and well conditioned; invalid matrices are rejected without repair.
  Exact uniform endpoints have infinite normal scores and are rejected by the
  forward transform rather than silently clipped. The 19 observations from five
  controlled cases do not establish a reliable operating distribution or a
  Gaussian copula, so **no copula is automatically fitted**.

An illustrative, explicitly assumed scenario can be run separately:

```bash
thermal-twin inputs --scenario configs/input_scenario_example.json --output results/inputs_example_scenario
```

The example assumes latent inlet/fan correlation 0.75 and independence of CPU
power from that pair. This number is illustrative, not estimated from HEATWISE;
it differs from the physical Pearson correlation after transformation.
Replace the description and matrix only with an explicitly justified scenario.
The required input order is CPU power, inlet temperature, raw fan signal.

Results under `results/inputs/` include:

- `reference_model.json`, `scenario_model.json`, `candidate_densities.json`,
  `assumptions.json`, a source-hashed/versioned `manifest.json`, and `report.md`.
- CSV tables with full-precision bounds, marginal diagnostics, QQ points,
  pooled/within-case/leave-one-case-out dependencies, case spans and reproducible
  synthetic input samples. These synthetic samples are not new training data.
- Histograms, candidate densities, uniform QQ plots, observed dependence matrices
  and joint-coverage comparisons, each in 300-dpi PNG and vector PDF formats.

Uniform is selected by assumption. Symmetric triangular and Beta(2,2) densities
have fixed illustrative shapes on the same bounds; no likelihood fitting,
AIC/BIC ranking or iid goodness-of-fit p-values are used. QQ departures describe
the controlled experimental sampling pattern, not a physical uncertainty law.
The density histograms give each accepted period equal descriptive weight.

Both the independent reference box and a Gaussian copula can assign probability
to untested input combinations. Neither validates extrapolation or safe operation.
Classical Sobol formulas for A must not be applied unchanged to B's dependent
physical inputs. Operating variability also differs from sensor uncertainty,
coefficient uncertainty and surrogate prediction error. The fan-signal unit stays
**unverified**. No predictive model, propagated output UQ or Sobol indices are
implemented in this step. Source and raw data are preserved.

## Presentation

The RWTH-CI LaTeX presentation is in
[`presentation/heatwise-thermal-twin/`](presentation/heatwise-thermal-twin/README.md).
With Python and LuaLaTeX installed, build it from the repository root:

```bash
python presentation/heatwise-thermal-twin/build.py
```

The output is `presentation/heatwise-thermal-twin/pdf/heatwise-thermal-twin.pdf`.
In VS Code, `Ctrl+Shift+B` runs the same build. See the presentation README for
setup, editing, and image-path conventions.

## Tests

```bash
python -m pytest
```

Tests cover valid data, invalid dimensions, missing inputs, CPU sensor identity,
case labels, transitions, malformed CSVs, time ordering and spacing, CLI behavior,
and preservation of source bytes. Most tests use synthetic data. An integration
test validates the supplied raw CSV and its documented case counts; it is skipped
only when that file is absent. Tests import the installed src-layout package, so
install the project first and reinstall it after source changes.
Audit tests additionally cover sensor-complete maxima, nonfinite values,
timestamp defects, inclusive case windows, pairwise-complete correlations,
coverage count conservation, raw-unit preservation, provenance, and saved plots.
Preprocessing tests use synthetic traces with known plateaus, load steps, thermal
transients, noise, drift, missing sensors, and gaps. They check the aggregation
target, minimum dwell, global versus local stability, and reproducible output.
They also cover gradual transitions, isolated spikes, optional workload markers,
and segmentation that does not depend on temperatures or a desired period count.
Input-model tests check exact unweighted bounds, UQLab uniform densities and
candidate normalization, the Legendre normalization convention, Gaussian-copula
covariance, both Nataf round-trip directions, endpoint/numerical guards, invalid
matrix rejection, separate A/B artifacts, source preservation and reproducibility.

## Project layout

```text
./
├── pyproject.toml
├── requirements-lock.txt
├── README.md
├── data/
│   ├── raw/                 # Original HEATWISE files; never modified
│   └── processed/           # steady_state.csv from preprocess
├── src/
│   └── thermal_twin/        # Python package and CLI
├── tests/
├── results/
│   ├── audit/               # Generated report, figures, tables, and provenance
│   ├── preprocessing/       # Selection diagnostics and plots
│   ├── inputs/              # Independent reference and distribution diagnostics
│   ├── inputs_example_scenario/ # Explicitly assumed dependent-scenario example
│   ├── figures/
│   ├── tables/
│   └── models/
└── configs/
```

Dataset provenance, limitations, and column descriptions are provided in the
existing `data/raw/README.md`, `CASES.csv`, and `DATA_DICTIONARY.csv`. Data files
are not bundled into the installed Python package.
