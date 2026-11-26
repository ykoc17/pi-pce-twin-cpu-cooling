"""Presentation figures from held-out measured targets only."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_comparison(result, output):
    predictions = result["predictions"]
    colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7"]
    with plt.rc_context({"font.size": 10, "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False}):
        fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.6), layout="constrained", sharex=True, sharey=True)
        limits = predictions[["measured_C", "predicted_C"]].to_numpy()
        limits = (float(limits.min())-3, float(limits.max())+3)
        for ax, method, title in zip(axes, ("ordinary", "monotonicity"),
                                    ("Ordinary PCE", "PCE with monotonicity constraints")):
            ax.plot(limits, limits, "--", color="0.5", linewidth=1)
            group = predictions.loc[predictions.method.eq(method)]
            for case, color, marker in zip(range(1, 6), colors, ["o", "s", "^", "D", "v"]):
                case_rows = group.loc[group.held_out_case.eq(case)]
                ax.scatter(case_rows.measured_C, case_rows.predicted_C, s=32, color=color,
                           marker=marker, label=f"Case {case}")
            ax.set(title=title, xlabel="Measured temperature (C)", xlim=limits, ylim=limits)
            ax.grid(alpha=.18)
        axes[0].set_ylabel("Predicted, whole case held out (C)")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="outside upper center", ncols=5, fontsize=9, frameon=False)
        for ext in ("pdf", "png"):
            fig.savefig(output/f"held_out_comparison.{ext}", dpi=180)
        plt.close(fig)
