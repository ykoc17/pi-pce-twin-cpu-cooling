"""Selection diagnostics on the original five-minute time series."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt

from configs.data_config import EXPECTED_CASE_IDS, INPUT_COLUMNS
from thermal_twin.preprocessing import TARGET_COLUMN


def plot_selection(result, output: Path):
    """Show retained samples, rejected samples, warmup, and incomplete sensors."""
    output.mkdir(parents=True, exist_ok=True)
    style = {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
             "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42}
    with plt.rc_context(style):
        _plot(result.rows, result.observations, output, "selection_overview", "All original measurements")
        for case in sorted(EXPECTED_CASE_IDS):
            rows = result.rows.loc[result.rows["case_id"].eq(case)]
            if not rows.empty:
                observations = result.observations.loc[result.observations["case_id"].eq(case)]
                _plot(rows, observations, output, f"case_{case}_selection", f"Case {case}")


def _plot(rows, observations, output, name, title):
    accepted = rows["selection_status"].eq("accepted")
    settling = rows["selection_status"].eq("discarded_initial_settling")
    excluded = rows["selection_status"].str.startswith("excluded_")
    rejected = ~(accepted | settling | excluded)
    groups = [(accepted, "#009E73"), (rejected, "#D55E00"),
              (settling, "#E69F00"), (excluded, "#888888")]
    labels = ["Total CPU power (W)", "Inlet temperature (°C)",
              "Fan signal (raw; unit unverified)", "CPU temperature (°C)"]
    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True, layout="constrained")
    for index, (ax, column, label) in enumerate(zip(axes, (*INPUT_COLUMNS, "cpu_temp_max_C"), labels)):
        ax.plot(rows["time_local"], rows[column], color="#999999", linewidth=0.7, zorder=1)
        for mask, color in groups:
            selected = rows.loc[mask]
            ax.scatter(selected["time_local"], selected[column], color=color, s=8,
                       alpha=0.75, edgecolors="none", zorder=2)
        for observation in observations.itertuples():
            ax.axvspan(observation.start_time, observation.end_time, color="#009E73", alpha=0.09)
        ax.set_ylabel(label.replace(" (", "\n("))
        ax.text(0.007, 0.93, f"({chr(97 + index)})", transform=ax.transAxes, va="top", fontweight="bold")
        ax.grid(alpha=0.18)
    incomplete = rows.loc[~rows["complete_cpu_temperatures"]]
    axes[-1].scatter(incomplete["time_local"], incomplete["cpu_temp_observed_max_C"],
                     color="#666666", marker="x", s=22, linewidths=0.8, zorder=3)
    for _, observation in observations.iterrows():
        axes[-1].hlines(observation[TARGET_COLUMN], observation["start_time"], observation["end_time"],
                        color="#004d3a", linestyle="--", linewidth=1.4, zorder=4)
    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
    axes[-1].xaxis.set_major_locator(locator)
    axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    axes[-1].set_xlabel("Original source local time (timezone unspecified)")
    fig.suptitle(f"Steady-state selection — {title}", fontsize=14)
    handles = [Line2D([], [], color=color, marker="o", linestyle="none", markersize=4, label=label)
               for color, label in (("#009E73", "Accepted"), ("#D55E00", "Rejected / unselected"),
                                    ("#E69F00", "Initial settling discarded"), ("#888888", "Excluded"))]
    handles += [Line2D([], [], color="#666666", marker="x", linestyle="none", markersize=5,
                       label="Incomplete sensors: available maximum"),
                Line2D([], [], color="#004d3a", linestyle="--", label="Target: max of CPU means")]
    fig.legend(handles=handles, loc="outside lower center", ncols=3, frameon=False, fontsize=9)
    for suffix in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if suffix == "pdf" else {}
        fig.savefig(output / f"{name}.{suffix}", dpi=300, bbox_inches="tight", metadata=metadata)
    plt.close(fig)
