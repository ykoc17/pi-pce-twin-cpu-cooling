"""Reproduce archived review-2 evidence, not the current monotonicity workflow.

Run from the repository root. Screening is a presentation/proposed-training policy,
not a refit: no PCE is trained and the original 128-point artifact is preserved.
"""
import hashlib
import itertools
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numpy.polynomial.legendre import legval

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "presentation/heatwise-thermal-twin/images/review2"
INPUTS = ["total_cpu_power_W", "server_inlet_air_temp_tunnel_C", "tunnel_fan_power_raw"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(ROOT / "data/processed/steady_state.csv")
    points = pd.read_csv(ROOT / "results/physics/tables/check_points.csv")
    pred = pd.read_csv(ROOT / "results/physics/tables/held_out_predictions.csv")
    target = data.equilibrium_max_cpu_temp_C
    excluded = points.T_phys_C.gt(target.max())
    assert len(data) == 19 and len(points) == 128 and excluded.sum() == 10
    assert np.array_equal(excluded, points.above_highest_measured_target)
    points["presentation_status"] = np.where(
        excluded, "excluded_above_measured_maximum", "withheld_pending_domain_and_regime_validation")
    points["current_physics_loss_weight"] = 0.0
    points.to_csv(OUT / "screened_check_points.csv", index=False)
    error = pred.predicted_C - pred.measured_C
    assert np.allclose(error, pred.residual_predicted_minus_measured_C)
    x = data[INPUTS].to_numpy()
    xi = 2 * (x - x.min(axis=0)) / np.ptp(x, axis=0) - 1
    designs = {}
    for degree in (1, 2, 3):
        terms = [a for a in itertools.product(range(degree + 1), repeat=3) if sum(a) <= degree]
        design = np.column_stack([
            np.prod([np.sqrt(2 * a[k] + 1) * legval(xi[:, k], [0] * a[k] + [1])
                     for k in range(3)], axis=0) for a in terms])
        designs[str(degree)] = dict(columns=len(terms), rank=int(np.linalg.matrix_rank(design)),
                                    condition_number=float(np.linalg.cond(design)))
    sources = ["data/processed/steady_state.csv", "results/physics/tables/check_points.csv",
               "results/physics/tables/held_out_predictions.csv",
               "results/preprocessing_review/threshold_sensitivity.csv", "data/raw/CASES.csv",
               "results/physics_training_review/manifest.json",
               "results/physics_training_review/predictions.csv",
               "results/physics_training_review/check_points.csv"]
    separate_check = json.loads((ROOT / "results/physics_training_review/manifest.json").read_text(encoding="utf-8"))
    evidence = dict(observations=len(data), generated=len(points), excluded=int(excluded.sum()),
                    withheld=int((~excluded).sum()), current_training_points=0,
                    measured_max_C=float(target.max()), synthetic_max_C=float(points.T_phys_C.max()),
                    validation_rmse_C=float(np.sqrt(np.mean(error ** 2))),
                    validation_metrics_scope="early fixed-three-constant check reused for model choice",
                    separate_model_choice_check=separate_check,
                    generated_point_scope="full-data diagnostic illustration only; never reused in a training fold",
                    validation_max_abs_C=float(abs(error).max()), designs=designs,
                    source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources})
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    with plt.rc_context({"font.size": 11, "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False}):
        fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), layout="constrained")
        for ax, col, label in zip(axes, INPUTS[:2], ["Total CPU power [W]", "Inlet temperature [°C]"]):
            ax.scatter(points.loc[~excluded, col], points.loc[~excluded, INPUTS[2]],
                       s=21, c="#999999", marker="x", label="118 withheld candidates")
            ax.scatter(points.loc[excluded, col], points.loc[excluded, INPUTS[2]],
                       s=44, c="#CC3311", marker="x", linewidths=1.7, label="10 excluded targets")
            ax.scatter(data[col], data[INPUTS[2]], s=28, c="#00549F", edgecolor="white",
                       linewidth=0.4, zorder=3, label="19 measurements")
            ax.set(xlabel=label, ylabel="Fan signal [unit unverified]")
            ax.grid(alpha=.15)
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="outside upper center", ncols=3, fontsize=10)
        fig.savefig(OUT / "screened_check_points.pdf")
        fig.savefig(OUT / "screened_check_points.png", dpi=180)
        plt.close(fig)
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
