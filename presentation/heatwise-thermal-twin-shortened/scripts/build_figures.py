"""Make a readable two-panel data figure; never fit a model or change source data."""

from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parents[1]
PROJECT = HERE.parents[1]
RAW = PROJECT / "data/raw/ocp_air_cooling_5min.csv"
OBS = PROJECT / "data/processed/steady_state.csv"


def main():
    raw = pd.read_csv(RAW, parse_dates=["time_local"])
    obs = pd.read_csv(OBS, parse_dates=["start_time", "end_time"])
    cpu = [name for name in raw if name.startswith("cpu_temp_C__srv")]
    if len(cpu) != 18 or len(obs) != 19:
        raise ValueError("Expected the unchanged 18-CPU dataset and 19 observations.")
    origin = raw.time_local.min()
    hours = (raw.time_local-origin).dt.total_seconds()/3600
    complete = np.isfinite(raw[cpu].to_numpy()).all(axis=1)
    temperature = raw[cpu].max(axis=1).where(complete)
    for row in obs.itertuples():
        retained = raw.loc[raw.time_local.between(row.start_time, row.end_time)]
        if retained.empty or not np.isfinite(retained[cpu].to_numpy()).all():
            raise ValueError("An accepted interval contains missing CPU measurements.")
        if not np.isclose(retained[cpu].mean().max(), row.equilibrium_max_cpu_temp_C, rtol=0, atol=1e-8):
            raise ValueError("The accepted interval does not reproduce its saved target.")
    output = HERE / "images"
    output.mkdir(exist_ok=True)
    with plt.rc_context({"font.size": 17, "axes.labelsize": 18, "xtick.labelsize": 16,
                         "ytick.labelsize": 16, "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False}):
        fig, axes = plt.subplots(2, 1, figsize=(9, 3.8), sharex=True, layout="constrained")
        for ax, values in zip(axes, [raw.total_cpu_power_W, temperature]):
            for row in obs.itertuples():
                left = (row.start_time-origin).total_seconds()/3600
                right = (row.end_time-origin).total_seconds()/3600
                ax.axvspan(left, right, color="#009E73", alpha=.20, linewidth=0)
            ax.plot(hours, values, color="#263746", linewidth=1.2)
            ax.grid(axis="y", alpha=.15)
            ax.set_xlim(0, hours.max())
        axes[0].set_ylabel("CPU power\n(W)")
        axes[0].set_yticks([0, 1000, 2000])
        axes[1].set_ylabel("CPU max\n("+chr(176)+"C)")
        axes[1].set_yticks([40, 60, 80, 100])
        axes[1].set_xlabel("Elapsed time (hours)")
        axes[1].set_xticks([0, 24, 48, 72, 96])
        for ext in ("pdf", "png"):
            fig.savefig(output/f"selection_readable.{ext}", dpi=200)
        plt.close(fig)
    evidence = {
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "observations_sha256": hashlib.sha256(OBS.read_bytes()).hexdigest(),
        "observations": len(obs), "cpu_sensors": len(cpu),
        "plotted_temperature": "maximum of 18 recorded values; missing if any CPU is missing",
        "fitted_target": "maximum of 18 interval-average CPU temperatures",
        "selection": "unchanged start/end times from steady_state.csv",
        "model_fitting": False,
    }
    (output/"selection_readable.json").write_text(json.dumps(evidence, indent=2)+"\n", encoding="utf-8")
    print(f"Wrote readable data figure and provenance to {output}")


if __name__ == "__main__":
    main()
