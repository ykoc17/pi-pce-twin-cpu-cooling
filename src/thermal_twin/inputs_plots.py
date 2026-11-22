"""Publication figures that separate observed sampling from assumed measures."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from configs.data_config import INPUT_COLUMNS
from thermal_twin.input_models import candidate_densities

AXIS_LABELS = ("Total CPU power (W)", "Inlet temperature (°C)", "Fan signal\n(raw; unit unverified)")
CASE_COLORS = ("#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7")


def _save(fig, output, name):
    for suffix in ("png", "pdf"):
        metadata = {"CreationDate": None, "ModDate": None} if suffix == "pdf" else {}
        fig.savefig(output / f"{name}.{suffix}", dpi=300, bbox_inches="tight", metadata=metadata)
    plt.close(fig)


def plot_input_diagnostics(data, parameters, qq, reference_samples, scenario_samples, output, config):
    style = {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
             "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42,
             "axes.grid": False, "figure.facecolor": "white"}
    with plt.rc_context(style):
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
        for ax, parameter, label in zip(axes, parameters, AXIS_LABELS):
            lower, upper = parameter["lower"], parameter["upper"]
            values = data[parameter["input"]]
            ax.hist(values, bins=np.linspace(lower, upper, config.histogram_bins + 1),
                    density=True, color="#0072B2", alpha=0.65, edgecolor="white",
                    label="19 period means")
            ax.hlines(1 / (upper - lower), lower, upper, color="#D55E00", linewidth=2,
                      label="Assumed uniform A")
            ax.plot(values, np.zeros(len(values)), "|", color="#333333", markersize=8)
            ax.set(xlabel=label, ylabel="Density", title=f"{len(values)} observations; equal period weights")
            ax.legend(fontsize=8)
        fig.suptitle("Experimental sampling histograms — not physical uncertainty", fontsize=13)
        _save(fig, output, "experimental_histograms")

        fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
        for ax, parameter, label in zip(axes, parameters, AXIS_LABELS):
            lower, upper = parameter["lower"], parameter["upper"]
            grid = np.linspace(lower, upper, config.density_grid_points)
            densities = candidate_densities(grid, lower, upper)
            for (name, density), color, linestyle in zip(
                densities.items(), ("#D55E00", "#0072B2", "#009E73"), ("-", "--", ":"),
            ):
                ax.plot(grid, density, color=color, linestyle=linestyle, linewidth=2, label=name)
            ax.set(xlabel=label, ylabel="Probability density")
            ax.set_ylim(bottom=0)
            ax.legend(fontsize=8)
        fig.suptitle("Candidate reference densities — fixed assumptions, no distribution fitting", fontsize=13)
        _save(fig, output, "candidate_densities")

        fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), layout="constrained")
        for ax, parameter, label in zip(axes, parameters, AXIS_LABELS):
            lower, upper = parameter["lower"], parameter["upper"]
            points = qq.loc[qq["input"].eq(parameter["input"])]
            ax.plot([lower, upper], [lower, upper], "--", color="#888888", label="Uniform reference line")
            ax.scatter(points["uniform_quantile"], points["observed_order_statistic"],
                       color="#0072B2", s=25, zorder=3, label="Experimental period means")
            ax.set(xlabel="Assumed uniform quantiles\n" + label,
                   ylabel="Observed ordered values", title=label.split("\n")[0])
            ax.legend(fontsize=7)
        fig.suptitle("QQ comparison — differences describe the controlled sampling design", fontsize=13)
        _save(fig, output, "uniform_qq")

        fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharex=True, sharey=True, layout="constrained")
        samples = (None, reference_samples, scenario_samples)
        titles = ("Observed: 19 accepted periods", "A: independent uniform reference", "B: optional Gaussian-copula scenario")
        for ax, sample, title in zip(axes, samples, titles):
            if sample is not None:
                ax.scatter(sample[:, 1], sample[:, 2], s=4, color="#888888", alpha=0.2,
                           rasterized=True, label="Assumed synthetic inputs")
            for case, color in enumerate(CASE_COLORS, 1):
                points = data.loc[data["case_id"].eq(case)]
                ax.scatter(points[INPUT_COLUMNS[1]], points[INPUT_COLUMNS[2]], s=35, color=color,
                           edgecolors="white", linewidths=0.4, zorder=3, label=f"Case {case}")
            if sample is None and ax is axes[2]:
                ax.text(0.5, 0.45, "Inactive by default\nNo reliable operating-law fit\nfrom this controlled experiment",
                        transform=ax.transAxes, ha="center", va="center", fontsize=10,
                        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "alpha": 0.95})
            ax.set(title=title, xlabel=AXIS_LABELS[1], ylabel=AXIS_LABELS[2])
        axes[0].legend(fontsize=8, loc="upper left")
        fig.suptitle("Joint coverage: assumed probability does not establish experimental support", fontsize=12)
        _save(fig, output, "joint_input_concepts")

        fig, axes = plt.subplots(1, 2, figsize=(8, 3.6), layout="constrained")
        labels = ("CPU power", "Inlet temp.", "Fan (raw)")
        for ax, method in zip(axes, ("pearson", "spearman")):
            correlation = data[list(INPUT_COLUMNS)].corr(method=method).to_numpy()
            im = ax.imshow(correlation, vmin=-1, vmax=1, cmap="RdBu_r")
            ax.set(xticks=range(3), yticks=range(3), xticklabels=labels, yticklabels=labels,
                   title=method.capitalize())
            for i in range(3):
                for j in range(3):
                    ax.text(j, i, f"{correlation[i, j]:.2f}", ha="center", va="center",
                            color="white" if abs(correlation[i, j]) > 0.6 else "black")
        fig.colorbar(im, ax=axes, shrink=0.8, label="Descriptive correlation")
        fig.suptitle("19 period means: experimental association, not a fitted copula", fontsize=12)
        _save(fig, output, "observed_dependencies")
