"""Consistent, headless publication figures for the descriptive audit."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

from thermal_twin.audit import AIRFLOW, CPU_COLUMNS, DOMAIN_COLUMNS, MAX_TEMP
from configs.data_config import INPUT_COLUMNS

# Five distinguishable colors from the Okabe-Ito palette; transitions are gray.
COLORS = {1: "#0072B2", 2: "#E69F00", 3: "#009E73", 4: "#D55E00", 5: "#CC79A7"}
LABELS = {
    INPUT_COLUMNS[0]: "Total CPU power (W)",
    INPUT_COLUMNS[1]: "Inlet temperature (°C)",
    INPUT_COLUMNS[2]: "Fan signal (raw; unit unverified)",
    AIRFLOW: "Measured airflow (m³/h)",
    MAX_TEMP: "Maximum CPU temperature (°C)",
}


def _save(fig, folder, name):
    for suffix in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if suffix == "pdf" else {}
        fig.savefig(folder / f"{name}.{suffix}", dpi=300, bbox_inches="tight", metadata=metadata)
    plt.close(fig)


def _legend(include_transition=True):
    handles = [Line2D([], [], linestyle="none", marker="o", color=color,
                      markersize=5, label=f"Case {case}") for case, color in COLORS.items()]
    if include_transition:
        handles.append(Line2D([], [], linestyle="none", marker="x", color="#777777",
                              markersize=5, label="Transition"))
    return handles


def _scatter(ax, data, first, second):
    transitions = data.loc[data["is_transition"]]
    ax.scatter(transitions[first], transitions[second], color="#777777", marker="x",
               s=14, alpha=0.5, linewidths=0.7, zorder=1)
    for case, color in COLORS.items():
        subset = data.loc[data["case_id"].eq(case)]
        ax.scatter(subset[first], subset[second], color=color, s=13, alpha=0.55,
                   edgecolors="none", zorder=2)
    ax.set_xlabel(LABELS[first])
    ax.set_ylabel(LABELS[second])
    ax.grid(alpha=0.2)


def create_figures(data, cases, output: Path) -> None:
    """Render observed measurements only; never fit curves or synthesize input tuples."""
    output.mkdir(parents=True, exist_ok=True)
    style = {
        "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12,
        "axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.fontsize": 9, "axes.spines.top": False, "axes.spines.right": False,
        "savefig.facecolor": "white", "pdf.fonttype": 42, "ps.fonttype": 42,
    }
    with plt.rc_context(style):
        _time_series(data, cases, output)
        _correlations(data, output)
        _pairwise(data, output)
        _fan_airflow(data, output)
        _coverage(data, output)
        _cpu_temperatures(data, output)


def _time_series(data, cases, output):
    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True, layout="constrained")
    for index, (ax, column) in enumerate(zip(axes, (*INPUT_COLUMNS, MAX_TEMP))):
        for _, case in cases.iterrows():
            ax.axvspan(case["start"], case["end"], color=COLORS[int(case["case_id"])], alpha=0.13)
        ax.plot(data["time_local"], data[column], color="#222222", linewidth=0.85)
        if column == MAX_TEMP:
            incomplete = data["cpu_temp_valid_count"].lt(18)
            ax.scatter(data.loc[incomplete, "time_local"],
                       data.loc[incomplete, "cpu_temp_observed_max_C"],
                       marker="x", color="#777777", s=22, linewidths=0.9,
                       label="Available sensors only (incomplete)", zorder=3)
            ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False,
                      borderaxespad=0)
        ax.set_ylabel(LABELS[column].replace(" (", "\n("))
        ax.text(0.006, 0.91, f"({chr(97 + index)})", transform=ax.transAxes,
                va="top", fontweight="bold")
        ax.grid(alpha=0.2)
    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
    axes[-1].xaxis.set_major_locator(locator)
    axes[-1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    axes[-1].set_xlabel("Source local time (timezone unspecified)")
    axes[0].set_title("HEATWISE air cooling: inputs and maximum CPU temperature", loc="left", pad=28)
    handles = [Patch(facecolor=color, alpha=0.4, label=f"Case {case}")
               for case, color in COLORS.items()]
    handles.append(Patch(facecolor="white", edgecolor="#aaaaaa", label="Transition"))
    axes[0].legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1.01),
                   ncols=6, frameon=False, borderaxespad=0)
    _save(fig, output, "inputs_and_max_temperature_timeseries")


def _correlations(data, output):
    selected = data.loc[data["case_id"].isin(range(1, 6)), list(INPUT_COLUMNS)]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.6), layout="constrained")
    ticklabels = ["CPU power", "Inlet temperature", "Fan signal\n(unit unverified)"]
    for ax, method in zip(axes, ("pearson", "spearman")):
        matrix = selected.corr(method=method)
        artist = ax.imshow(np.ma.masked_invalid(matrix.to_numpy()), vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(3), ticklabels, rotation=25, ha="right")
        ax.set_yticks(range(3), ticklabels)
        ax.set_title(f"{'Pearson r' if method == 'pearson' else 'Spearman ρ'}")
        for row in range(3):
            for col in range(3):
                value = matrix.iloc[row, col]
                ax.text(col, row, f"{value:.2f}" if np.isfinite(value) else "n/a",
                        ha="center", va="center", color="white" if abs(value) > 0.65 else "black")
    fig.colorbar(artist, ax=axes, shrink=0.8, label="Correlation")
    fig.suptitle("Input dependencies: labeled cases, pairwise-complete observations")
    _save(fig, output, "input_correlation_matrix")


def _pairwise(data, output):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), layout="constrained")
    for index, (ax, pair) in enumerate(zip(axes, combinations(DOMAIN_COLUMNS, 2))):
        _scatter(ax, data, *pair)
        ax.set_title(f"({chr(97 + index)})")
    fig.legend(handles=_legend(), loc="outside lower center", ncols=6, frameon=False)
    fig.suptitle("Observed input pairs by experimental case")
    _save(fig, output, "pairwise_input_scatter")


def _fan_airflow(data, output):
    fig, ax = plt.subplots(figsize=(7, 5), layout="constrained")
    _scatter(ax, data, INPUT_COLUMNS[2], AIRFLOW)
    ax.set_title("Raw fan signal and measured airflow")
    fig.legend(handles=_legend(), loc="outside lower center", ncols=3, frameon=False)
    _save(fig, output, "fan_power_vs_airflow")


def _coverage(data, output):
    fig = plt.figure(figsize=(9, 7), layout="constrained")
    ax = fig.add_subplot(111, projection="3d")
    for case, color in COLORS.items():
        subset = data.loc[data["case_id"].eq(case)]
        ax.scatter(subset[DOMAIN_COLUMNS[0]], subset[DOMAIN_COLUMNS[1]], subset[DOMAIN_COLUMNS[2]],
                   color=color, s=12, alpha=0.5, edgecolors="none", depthshade=False)
    ax.set_xlabel("Inlet temperature (°C)", labelpad=9)
    ax.set_ylabel("Fan signal\n(raw; unit unverified)", labelpad=14)
    ax.set_zlabel("Total CPU power (W)", labelpad=12)
    ax.view_init(elev=24, azim=-55)
    ax.set_title("Operating-condition coverage: observed labeled input triples", pad=16)
    fig.legend(handles=_legend(False), loc="outside lower center", ncols=5, frameon=False)
    _save(fig, output, "operating_condition_coverage")


def _cpu_temperatures(data, output):
    # Display heatmap columns chronologically only for plotting; source tables stay in source order.
    selected = data.loc[data["time_local"].notna()].sort_values("time_local")
    if selected.empty:
        return
    matrix = selected[list(CPU_COLUMNS)].to_numpy(dtype=float).T
    fig, ax = plt.subplots(figsize=(11, 6.8), layout="constrained")
    cmap = plt.get_cmap("inferno").with_extremes(bad="#bdbdbd")
    x = mdates.date2num(selected["time_local"].to_numpy())
    # nearest shading accommodates missing time steps; missing sensors retain gray cells.
    artist = ax.pcolormesh(x, np.arange(18), np.ma.masked_invalid(matrix),
                           shading="nearest", cmap=cmap, rasterized=True)
    ax.set_yticks(range(18), [column.removeprefix("cpu_temp_C__").replace("_", " / ")
                             for column in CPU_COLUMNS])
    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlabel("Source local time (timezone unspecified)")
    ax.set_ylabel("Individual CPU sensor")
    ax.set_title("All 18 measured CPU temperatures; gray cells indicate missing readings")
    fig.colorbar(artist, ax=ax, label="CPU temperature (°C)", pad=0.02)
    _save(fig, output, "all_cpu_temperatures")
