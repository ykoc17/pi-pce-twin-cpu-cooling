# thermal-twin

A reproducible Python project for a steady-state thermal digital twin using the
HEATWISE experimental dataset. This initial step provides dataset loading,
validation, and the `thermal-twin inspect` command. PCE, physics-informed PCE,
uncertainty quantification, Sobol analysis, and constrained optimization are
planned later steps and are not implemented here.

The distribution and CLI are named `thermal-twin`. The Python import package is
`thermal_twin`; setuptools generates `src/thermal_twin.egg-info` from the
distribution name by converting hyphens to underscores.

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
│   ├── figures/
│   ├── tables/
│   └── models/
└── configs/
```

Dataset provenance, limitations, and column descriptions are provided in the
existing `data/raw/README.md`, `CASES.csv`, and `DATA_DICTIONARY.csv`. Data files
are not bundled into the installed Python package.
