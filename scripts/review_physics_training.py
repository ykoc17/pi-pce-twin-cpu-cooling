"""Archived thermal-rule check; current presentation uses fit_monotonic_pce.py."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from configs.physics_config import DEFAULT_PHYSICS_CONFIG
from thermal_twin.physics import error_metrics, load_training_data
from thermal_twin.physics_validation import nested_case_review


def main():
    source = ROOT / "data/processed/steady_state.csv"
    output = ROOT / "results/physics_training_review"
    output.mkdir(parents=True, exist_ok=True)
    data = load_training_data(source)
    result = nested_case_review(data)
    for name, table in result.items():
        table.to_csv(output / f"{name}.csv", index=False)
    predictions = result["predictions"]
    metrics = error_metrics(predictions.predicted_C, predictions.measured_C)
    manifest = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "config": asdict(DEFAULT_PHYSICS_CONFIG), "outer_metrics": metrics,
                "selection": "inner pooled case-wise RMSE, 3 vs 4 constants; ties choose 3",
                "status": "early internal check; dataset already informed model development",
                "synthetic_points_used_in_training": 0}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7"]
    with plt.rc_context({"font.size": 10, "pdf.fonttype": 42, "axes.spines.top": False,
                         "axes.spines.right": False}):
        fig, ax = plt.subplots(figsize=(4.4, 4.2), layout="constrained")
        bounds = predictions[["measured_C", "predicted_C"]].to_numpy()
        lim = (float(bounds.min()) - 3, float(bounds.max()) + 3)
        ax.plot(lim, lim, "--", color="0.5", linewidth=1)
        for case, color, marker in zip(sorted(data.case_id.unique()), colors, ["o", "s", "^", "D", "v"]):
            group = predictions.loc[predictions.held_out_case.eq(case)]
            ax.scatter(group.measured_C, group.predicted_C, color=color, marker=marker,
                       s=36, label=f"Case {int(case)}")
        ax.set(xlabel="Measured maximum interval-mean CPU temperature (C)",
               ylabel="Predicted after training-only model choice (C)", xlim=lim, ylim=lim)
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
        for ext in ("pdf", "png"):
            fig.savefig(output / f"early_predictions.{ext}", dpi=180)
        plt.close(fig)
    rows = "\n".join(
        f"| {r.held_out_case} | {r.training_n} | {r.n} | {r.selected_constants} | {r.RMSE_C:.3f} | "
        f"{r.excluded_points} | {r.withheld_points} |" for r in result["folds"].itertuples())
    report = f"""# Early physics-model accuracy check and training-only generated points

## What changed

The old 3.45 C RMSE helped choose three rather than four constants. It is an early
accuracy check, not a separate final test. Original results/physics files are preserved.

This new check leaves one complete experiment out. The other four alone choose
between three and four constants using inner case-wise tests. The selected formula
is refitted to those four, then predicts the experiment that was kept out.

Pooled outer RMSE: **{metrics['RMSE_C']:.3f} C**. Largest absolute error:
**{metrics['max_abs_error_C']:.3f} C**. These are thermal-rule results, not PCE results.
The full dataset already informed model development, so this remains an early
internal check. New experiments are needed for a genuinely fresh final test.

| Test case | Training rows | Test rows | Constants selected | Test RMSE (C) | Generated: excluded | Generated: withheld |
| --- | --- | --- | --- | --- | --- | --- |
{rows}

## Generated-point policy

- Keep the existing full-data 128-point plot only as a diagnostic illustration.
  Its 10/118 split is not reused during testing.
- In every outer training set, refit the rule and fan reference, derive input
  bounds from training rows, and generate 128 points with the fixed Sobol seed.
- Screen against the maximum training target only. The cutoff is a diagnostic
  convention, not a known throttling or safety limit. Counts can differ by fold.
- Every generated point has physics-loss weight zero: excluded above the cutoff,
  otherwise withheld pending operating-domain/regime validation. None enters fitting.
- For future PCE tuning, repeat this preparation within each inner training split
  too. Do not use precomputed full-data labels or any held-out target/input to
  construct a training rule, ranges or screening cutoff.
- Compare measured-data-only PCE and the thermal rule before approving physics
  targets. Model-generated labels add assumptions, not experimental evidence.

## Reproduce

    .\\.venv\\Scripts\\python.exe -B scripts/review_physics_training.py

Output CSVs record training/test period IDs, constants, ranges, cutoff, diagnostic
points and status. All original observations and fitted-model artifacts are unchanged.
"""
    (output / "report.md").write_text(report, encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(result["folds"][["held_out_case", "selected_constants", "excluded_points", "withheld_points"]].to_string(index=False))


if __name__ == "__main__":
    main()
