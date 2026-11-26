"""Command-line tools"""

from __future__ import annotations

import argparse
from dataclasses import replace
import sys
from pathlib import Path

from configs.data_config import DEFAULT_DATA_PATH, INPUT_COLUMNS
from thermal_twin.data import DatasetValidationError, inspect_dataset


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, returning a nonzero status for invalid datasets."""
    parser = argparse.ArgumentParser(prog="thermal-twin", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Validate the original air-cooling CSV")
    inspect.add_argument(
        "--data", type=Path, default=DEFAULT_DATA_PATH,
        help="CSV path (default: %(default)s, relative to the current directory)",
    )
    audit = commands.add_parser("audit", help="Create descriptive tables and publication figures")
    audit.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Air-cooling CSV path")
    audit.add_argument("--cases", type=Path, help="CASES.csv path (default: beside the dataset)")
    audit.add_argument("--dictionary", type=Path,
                       help="DATA_DICTIONARY.csv path (default: beside the dataset)")
    audit.add_argument("--output", type=Path, default=Path("results/audit"),
                       help="Output directory (default: %(default)s)")
    preprocess = commands.add_parser("preprocess", help="Extract approximately steady operating observations")
    preprocess.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Air-cooling CSV path")
    preprocess.add_argument("--output", type=Path, default=Path("data/processed/steady_state.csv"))
    preprocess.add_argument("--diagnostics", type=Path, default=Path("results/preprocessing"))
    preprocess.add_argument("--min-dwell-minutes", type=float,
                            help="Minimum retained duration after settling (default: preprocessing config)")
    preprocess.add_argument("--initial-settling-minutes", type=float,
                            help="Initial interval to discard (default: preprocessing config)")
    preprocess.add_argument("--stability-window-minutes", type=float,
                            help="Sliding stability window (default: preprocessing config)")
    from configs.input_config import DEFAULT_INPUTS_OUTPUT, DEFAULT_OBSERVATIONS_PATH
    inputs = commands.add_parser("inputs", help="Specify reference input distributions and diagnose sampling/coverage")
    inputs.add_argument("--data", type=Path, default=DEFAULT_OBSERVATIONS_PATH,
                        help="Accepted operating-period CSV (default: %(default)s)")
    inputs.add_argument("--output", type=Path, default=DEFAULT_INPUTS_OUTPUT,
                        help="Results directory (default: %(default)s)")
    inputs.add_argument("--scenario", type=Path,
                        help="Optional JSON specifying a Gaussian-copula operating scenario; never fitted automatically")
    from configs.physics_config import DEFAULT_PHYSICS_OUTPUT
    physics = commands.add_parser("fit-physics", help="Legacy thermal-rule experiment; current method is fit-pce")
    physics.add_argument("--data", type=Path, default=DEFAULT_OBSERVATIONS_PATH,
                         help="Accepted operating-period CSV (default: %(default)s)")
    physics.add_argument("--output", type=Path, default=DEFAULT_PHYSICS_OUTPUT,
                         help="Results directory (default: %(default)s)")
    from configs.pce_config import DEFAULT_PCE_OUTPUT
    pce = commands.add_parser("fit-pce", help="Fit measured-data PCE with monotonicity constraints")
    pce.add_argument("--data", type=Path, default=DEFAULT_OBSERVATIONS_PATH)
    pce.add_argument("--output", type=Path, default=DEFAULT_PCE_OUTPUT)
    args = parser.parse_args(argv)
    try:
        if args.command == "fit-pce":
            from thermal_twin.monotonic_pce import run_pce
            result = run_pce(args.data, args.output)
            print(f"PCE with monotonicity constraints: {args.output / 'report.md'}")
            print(result["metrics"][["method", "RMSE_C", "max_abs_error_C"]].to_string(index=False))
            print("19 measured observations; no synthetic temperature targets. Early case-wise comparison only.")
            return 0
        if args.command == "fit-physics":
            from thermal_twin.physics import run_physics
            result = run_physics(args.data, args.output)
            model = result["model"]
            print(f"Thermal-resistance rule fitted to {result['observations']} observations: {args.output / 'report.md'}")
            print(f"  offset={model.offset_C:.3f} C, K={model.K_C_per_W:.5f} C/W, gamma={model.gamma:.4f}, "
                  f"F_ref={model.fan_reference:.6f} (raw, unverified unit)")
            print(f"  RMSE: training {result['training']['RMSE_C']:.2f} C, "
                  f"held-out cases {result['held_out']['RMSE_C']:.2f} C")
            print(f"{result['check_points']} check points saved. They are not measurements; no PCE is fitted.")
            return 0
        if args.command == "inputs":
            from thermal_twin.inputs import run_inputs
            result = run_inputs(args.data, args.output, args.scenario)
            print(f"Input models and diagnostics: {args.output / 'report.md'}")
            print(f"A: independent uniform reference; exact spans of {result['observations']} period means.")
            for parameter in result["parameters"]:
                print(f"  {parameter['input']}: Uniform({parameter['lower']:.12g}, {parameter['upper']:.12g})")
            print(f"B: {result['scenario']['status']}; no operating distribution estimated from the controlled design.")
            print("Experimental sampling is not physical uncertainty. Fan-signal unit is unverified.")
            return 0
        if args.command == "preprocess":
            from configs.preprocessing_config import DEFAULT_PREPROCESSING_CONFIG
            from thermal_twin.preprocessing import run_preprocess
            overrides = {name: value for name, value in {
                "minimum_dwell_minutes": args.min_dwell_minutes,
                "initial_settling_minutes": args.initial_settling_minutes,
                "stability_window_minutes": args.stability_window_minutes,
            }.items() if value is not None}
            try:
                config = replace(DEFAULT_PREPROCESSING_CONFIG, **overrides)
            except ValueError as exc:
                parser.error(str(exc))
            result = run_preprocess(args.data, output=args.output, diagnostics=args.diagnostics, config=config)
            print(f"Saved {len(result.observations)} steady operating observations: {args.output}")
            print(result.case_counts[["case_id", "accepted_operating_periods"]].to_string(index=False))
            print(f"Diagnostics: {args.diagnostics / 'report.md'}")
            print("Counts are nonoverlapping operating periods; statistical independence is not established.")
            return 0
        if args.command == "audit":
            from thermal_twin.audit import FAN_UNIT_NOTE, run_audit
            quality = run_audit(args.data, cases_path=args.cases,
                                dictionary_path=args.dictionary, output=args.output)
            print(f"Audit complete: {args.output / 'report.md'}")
            print(f"{quality['rows']} rows; {quality['transition_rows']} transition rows; "
                  f"{quality['incomplete_cpu_temperature_rows']} incomplete CPU-temperature rows")
            print(FAN_UNIT_NOTE)
            return 0
        report = inspect_dataset(args.data)
    except DatasetValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: Could not read inputs or write outputs: {exc}", file=sys.stderr)
        return 1

    print(f"Validated HEATWISE air-cooling dataset: {args.data}")
    print(f"Original CSV: {report.rows} rows x {report.columns} columns")
    print("Experimental cases: " + ", ".join(
        f"{case} ({count} rows)" for case, count in report.case_counts.items()
    ))
    print(f"Unlabeled transition rows: {report.transition_rows}")
    print("Input columns: " + ", ".join(INPUT_COLUMNS))
    print(f"Individual CPU temperature columns: {len(report.cpu_temperature_columns)}")
    print(f"Time range (source local time): {report.start_time} to {report.end_time}")
    print("Time ordering: strictly increasing; timestamp spacing: 5 minutes")
    return 0
