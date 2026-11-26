"""Run the measured-data PCE / monotonicity-constraints comparison from source."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(ROOT))

from thermal_twin.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["fit-pce", *sys.argv[1:]]))
