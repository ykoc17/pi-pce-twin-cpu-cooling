# thermal-twin

A reproducible Python project for a steady-state thermal digital twin using the
HEATWISE experimental dataset. The project provides dataset loading,
validation, `thermal-twin inspect`, and descriptive exploration with `thermal-twin audit`.
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

Use Python 3.11 or newer. Run these commands from the repository root. All packages
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

The second install adds pytest. NumPy, pandas, SciPy, scikit-learn, and matplotlib
are declared runtime dependencies; the inspection step uses pandas and the
standard library. No additional runtime dependencies are required.
The audit also uses NumPy, SciPy (rank correlations), and matplotlib.

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

## Project layout

```text
./
├── pyproject.toml
├── requirements-lock.txt
├── README.md
├── data/
│   ├── raw/                 # Original HEATWISE files; never modified
│   └── processed/           # Reserved for later processing
├── src/
│   └── thermal_twin/        # Python package and CLI
├── tests/
├── results/
│   ├── audit/               # Generated report, figures, tables, and provenance
│   ├── figures/
│   ├── tables/
│   └── models/
└── configs/
```

Dataset provenance, limitations, and column descriptions are provided in the
existing `data/raw/README.md`, `CASES.csv`, and `DATA_DICTIONARY.csv`. Data files
are not bundled into the installed Python package.
