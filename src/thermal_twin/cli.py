"""Command-line entry point for dataset inspection."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thermal_twin.data import (
    DEFAULT_DATA_PATH,
    INPUT_COLUMNS,
    DatasetValidationError,
    inspect_dataset,
)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, returning a nonzero status for invalid datasets."""
    parser = argparse.ArgumentParser(prog="thermal-twin", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Validate the original air-cooling CSV")
    inspect.add_argument(
        "--data", type=Path, default=DEFAULT_DATA_PATH,
        help="CSV path (default: %(default)s, relative to the current directory)",
    )
    args = parser.parse_args(argv)
    try:
        report = inspect_dataset(args.data)
    except DatasetValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
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
