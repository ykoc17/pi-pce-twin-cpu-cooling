"""Command-line tools"""

from __future__ import annotations

import argparse
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
    args = parser.parse_args(argv)
    try:
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
