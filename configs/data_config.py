"""Paths and schema constants for the original HEATWISE air-cooling dataset."""

import re
from pathlib import Path

DEFAULT_DATA_PATH = Path("data/raw/ocp_air_cooling_5min.csv")
EXPECTED_SHAPE = (1333, 219)
INPUT_COLUMNS = (
    "total_cpu_power_W",
    "server_inlet_air_temp_tunnel_C",
    "tunnel_fan_power_raw",
)
CPU_TEMPERATURE_PATTERN = re.compile(r"cpu_temp_C__srv\d+_cpu\d+")
EXPECTED_CPU_COLUMNS = frozenset(
    f"cpu_temp_C__srv{server}_cpu{cpu}"
    for server in range(1, 10)
    for cpu in (1, 2)
)
EXPECTED_CASE_IDS = frozenset(range(1, 6))
WORKLOAD_COLUMN = "cpu_utilisation_pct__mean"
