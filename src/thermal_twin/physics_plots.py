"""Publication figures for the thermal-resistance rule and its check points."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

from configs.data_config import INPUT_COLUMNS
from thermal_twin.inputs_plots import AXIS_LABELS, CASE_COLORS, _save
from thermal_twin.preprocessing import TARGET_COLUMN

MARKERS = ("o", "s", "^", "D", "v")


def _case_styles():
    return [(case, color, marker)
            for case, (color, marker) in enumerate(zip(CASE_COLORS, MARKERS), start=1)]


def _case_handles():
    return [Line2D([], [], linestyle="none", marker=marker, color=color, markersize=6, label=f"Case {case}")
            for case, color, marker in _case_styles()]


def plot_physics(data, model, predictions, checks, output):
    power, inlet, fan = INPUT_COLUMNS
    style = {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
             "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42, "figure.facecolor": "white"}
    with plt.rc_context(style):
        # Lines stay inside each case's measured power range: supported conditions only.
        fig, ax = plt.subplots(figsize=(6.2, 4.0), layout="constrained")
        for case, color, marker in _case_styles():
            group = data[data["case_id"].eq(case)]
            grid = np.linspace(group[power].min(), group[power].max(), 50)
            line = np.column_stack([grid, np.full(50, group[inlet].mean()), np.full(50, group[fan].mean())])
            ax.plot(grid, model.predict(line), color=color, linewidth=1.8)
            ax.scatter(group[power], group[TARGET_COLUMN], color=color, marker=marker, s=36, zorder=3)
        ax.set(xlabel=AXIS_LABELS[0], ylabel="Maximum CPU temperature (°C)")
        ax.grid(alpha=0.2)
        ax.legend(handles=_case_handles() + [Line2D([], [], color="#555555", linewidth=1.8, label="Fitted rule")],
                  fontsize=8)
        _save(fig, output, "physics_response")

        fig, ax = plt.subplots(figsize=(4.4, 4.2), layout="constrained")
        both = predictions[["measured_C", "predicted_C"]].to_numpy()
        limits = (both.min() - 3, both.max() + 3)
        ax.plot(limits, limits, color="#777777", linestyle="--", linewidth=1)
        for case, color, marker in _case_styles():
            group = predictions[predictions["held_out_case"].eq(case)]
            ax.scatter(group["measured_C"], group["predicted_C"], color=color, marker=marker, s=36, zorder=3)
        ax.set(xlabel="Measured (°C)", ylabel="Predicted, case held out (°C)", xlim=limits, ylim=limits)
        ax.grid(alpha=0.2)
        ax.legend(handles=_case_handles(), fontsize=8)
        _save(fig, output, "held_out_predictions")

        fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.5), layout="constrained")
        for ax, x in zip(axes, (inlet, power)):
            ax.scatter(checks[x], checks[fan], color="#8A8A8A", marker="x", s=16, linewidths=0.8, zorder=1)
            for case, color, marker in _case_styles():
                group = data[data["case_id"].eq(case)]
                ax.scatter(group[x], group[fan], color=color, marker=marker, s=40, zorder=3,
                           edgecolors="white", linewidths=0.5)
            ax.set(xlabel=AXIS_LABELS[INPUT_COLUMNS.index(x)], ylabel=AXIS_LABELS[2])
            ax.grid(alpha=0.2)
        check_handle = Line2D([], [], linestyle="none", marker="x", color="#8A8A8A", markersize=5,
                              label="Extra point")
        fig.legend(handles=_case_handles() + [check_handle], loc="outside upper center", ncols=6, fontsize=8,
                   frameon=False, handletextpad=0.1, columnspacing=1.0)
        _save(fig, output, "check_points")
