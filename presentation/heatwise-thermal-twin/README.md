# HEATWISE thermal twin presentation

A presentation using the supplied RWTH-CI Beamer template. Edit `main.tex` in
VS Code for the project title, contributor names, and shared formatting.
The PDF contains the template's blue title page followed by:

- **Introduction**, editable in `sections/introduction.tex` (five slides):
  motivation; a facility photo and dataset overview; the air-cooling subset and
  actuator optimization objective; the proposed digital twin;
  the rationale for experimental rather than purely synthetic training data.
- **Input Data**, editable in `sections/input-data.tex` (four context slides): operating
  cases and model variables; two slides on dataset problems; preprocessing and
  steady-state selection. Problems are numbered **1. Sparsity**, **2. Unverified
  unit of fan signal**, and **3. Input Dependence**. The first two use the inlet/fan
  scatter plot; the third uses `input_correlation_matrix.pdf` from the audit.
- **Preprocessing results**, a subsection under Input Data, editable in
  `sections/preprocessing-results.tex` (five slides): selection steps; the full
  selection overview and color meanings; an enlarged case 4 example; converting
  each selected interval into one PCE observation; and the per-case results
  (19 accepted observations from 25 candidate periods). The target is the maximum
  of the 18 CPU means over the same selected timestamps, not the average of
  instantaneous maxima. No predictive model has been fitted.
- **Input distributions**, another subsection under Input Data, editable in
  `sections/input-distributions.tex` (seven slides): exact-span uniform assumptions;
  experimental histograms; illustrative candidate densities; uniform QQ plots;
  observed versus assumed joint coverage; and the dependent-scenario limitations
  and Nataf transformation. Concept A is an independent reference for a Legendre
  basis and later hypothetical UQ/Sobol analysis. Concept B is an optional,
  explicitly specified Gaussian-copula scenario, not an estimated operating law.
  The first slide explicitly credits **UQLab from ETH Zürich**, briefly defines it
  as a framework for uncertainty quantification, states that its Python version
  UQLab.py 0.800 created the input distributions, and links to
  [www.uqlab.com](https://www.uqlab.com/).
  Slide **22** records the decision to use **model A**, the independent uniform
  reference, while acknowledging the experimental dependencies and untested
  combinations. Model B remains an optional scenario tool.
- **Project summary**, editable in `sections/project-summary.tex`, is slide
  **23**: inputs, output, distributions, dependencies, assumptions, completed work
  and the next step. No predictive model has been fitted yet.
- **Model**, editable in `sections/model.tex`, starts on slide **24** with the
  subsection **Polynomial Chaos Expansion** (nine slides, **24--32**). It explains
  PCE as a weighted polynomial surrogate, the three inputs and temperature target,
  the independent uniform reference assumptions and their connection to a
  normalized Legendre basis. The planned scope is degrees 1 and 2: the full
  total-degree coefficient formula `M(d,p) = binomial(d+p,p)` gives 4, 10 and 20
  coefficients for degrees 1, 2 and 3 with three inputs. A full cubic cannot be
  uniquely estimated by unrestricted ordinary least squares with 19 observations;
  20 is only the algebraic minimum with a full-rank design, not a validation
  guarantee. No model-fitting code is added by these presentation slides.
  Slide **26** maps the digital twin into a table: model equation, planned solver
  and very fast surrogate evaluation; the three operating parameters with
  uniform ranges and no initial state; scalar output; 18 CPU/IPMI measurement
  channels, sampling frequency and aggregation operator; the 19 fitted targets;
  and the thermal quantity of interest for the proposed control problem.
  Slide **27** explains that three unknown inputs cannot generally be uniquely
  identified from one maximum-temperature observable. Our inputs are measured;
  inverse calibration is not part of the current workflow. It has no fixed run
  count, and more evaluations do not resolve non-uniqueness. With two known
  inputs, inversion for the third requires a unique, sufficiently sensitive
  relationship. This is distinct from coefficient fitting and control optimization.
  Slide **28** adds expected input sensitivities, possible nonlinearity/noise,
  the experimental budget and the need for well-spread observations beyond the
  algebraic coefficient count. Expected physical trends are hypotheses, not results.
  Slide **29** explains the advantages: efficient input-UQ calculations for the
  planned soft-constraint control optimization, coefficient-based Sobol analysis,
  lightweight polynomial regression, and ETH UQLab.py as the selected PCE
  framework. Input models already use UQLab; predictive PCE fitting remains
  planned. Control margins require validated uncertainty, beyond global input
  variability alone. Slide **30** covers the limited 19 observations, the
  independence assumption of classical Sobol formulas (not a universal PCE
  restriction), the observed inlet/fan dependence, and possible underfitting by
  degrees 1/2. Neural networks are presented as a potential alternative with much
  larger, well-covered data and validation, not as automatically superior.
  Slide **31** specifies five-fold **leave-one-case-out** validation: train on four
  complete cases and predict the fifth for each degree. It gives train/validation
  counts, formulas for per-fold RMSE, MAE, R2 and maximum absolute error, and the
  held-out residual convention `observed - predicted`. Degrees 1 and 2 use the
  same folds and are compared with fold-wise/pooled held-out metrics and residuals.
  The workload is 10 fits and 38 held-out predictions, followed by one final fit
  of the selected degree on all 19 observations; no new experiments are needed.
  This is a validation protocol: no predictive PCE or validation results are
  currently implemented/saved. Small-fold R2 and possible case extrapolation are noted.
  Slide **32** distinguishes fast pointwise OLS LOO from case-level validation,
  adds global/local decision metrics, and specifies training-only/nested grouped
  tuning for a fair model comparison.
- **Adding Physics: Physics-Informed PCE**, under Model, is editable in
  `sections/physics-informed.tex` (slides **33--35**): the proposed effective
  thermal-resistance relationship, the data-plus-physics training loss and its
  weights/check points, calibration, possible benefits and limitations.
  The raw fan/reference ratio is dimensionless, not a conversion to watts.
  No physical parameters or PI-PCE have been fitted.
- **Uncertainty Quantification**, in `sections/remaining-topics.tex` and
  `sections/uncertainty-control.tex` (slides **36--38**): zero extra predictions
  for global mean/variance; illustrative 10,000-sample distribution estimates;
  aleatory/epistemic distinctions; conditional inlet-disturbance moments with
  controls fixed; and a proposed Cantelli-bound interpretation of a thermal target.
  The operating disturbance law, risk level and safety margin are not calibrated.
- **Sobol Sensitivity Analysis**, in `sections/remaining-topics.tex` (slide **39**):
  first-order/total coefficient formulas, zero extra predictions after fitting,
  independent-reference interpretation, latent-variable caveat and optional input removal.
- **Optimization Problem: Soft-constrained optimal control**, in
  `sections/optimization.tex` (slides **40--41**): CPU/cooling/slack tradeoff,
  conditional thermal target, actuator bounds, change limits and supported-domain
  restriction; solver, hardware mapping and independent confirmation requirements.
- **The whole digital twin workflow**, in `sections/workflow.tex` (slides **42--45**):
  potential data streams, two-way connectivity, fast operating/safety loop,
  slower retraining and future LHS experiments, infrastructure and conceptual deployment.
- **Other possible directions: GPs**, in `sections/alternatives.tex` (slides **46--47**):
  small-data GP alternative, conditional predictive uncertainty and its limits,
  and a common-case benchmark against standard/physics-informed PCE.
- **Conclusion and Outlook**, in `sections/remaining-topics.tex` (slide **48**):
  completed inspection/audit/preprocessing/input models versus proposed modeling,
  UQ/sensitivity/optimization and conceptual live control. No predictive results are invented.

The Introduction has the subsections **Motivation and Context** (three slides),
**Why a Digital Twin?** (one slide), and **Why not Synthetic Data?** (one slide).
No separate divider slides are generated. The dataset overview appears beside
`images/datacenter.jpeg`; the project-specific air-cooling subset and control
objective follow on the next slide. The overview is not repeated in Input Data. The image
credit uses the RWTH template's native `\footlinetext` command with a link to the
RISE source article. The proposed control and safety architecture is explicitly
conceptual; the project scope is offline development and evaluation.

Figures reference the existing vector PDFs in `../../results/audit/figures/`
and `../../results/preprocessing/figures/`, plus `../../results/inputs/figures/`
and `../../results/inputs_example_scenario/figures/`. Recreate the input figures
before building with `thermal-twin inputs` and
`thermal-twin inputs --scenario configs/input_scenario_example.json --output results/inputs_example_scenario`.
The example scenario is explicitly illustrative, not fitted from the 19 periods.
The selection overview is shown in
full; the case 4 example enlarges its power and temperature panels. Green bands
denote accepted intervals, orange points are rejected or unselected, yellow
points are discarded settling readings, and gray points/crosses are excluded.
The dashed green line is the maximum of the period's 18 CPU averages.
Selected panels are cropped using LaTeX `trim` and `clip`; the original figures
remain unchanged. Sources are linked or named at the bottom of each slide.
The institute and date fields remain blank and can be filled in in the preamble.

## Coverage of the supplied project notes

The presentation incorporates the supplied notes into the relevant chapters.
Earlier alternatives in the notes are reconciled with the subsequent project decisions:

| Notes topic | Presentation location and interpretation |
| --- | --- |
| Digital-twin objective: data, physics, data-driven methods, repeated analysis and deployment | Introduction; slides 33--48 distinguish the proposed concept from completed data work. |
| Model map, input parameters, observable and decision quantity | Slide 26; the decision needs CPU/fan settings, guided by temperature and its thermal margin. |
| Input sensitivity, identifiability, cost and run counts | Slides 27--31, 36 and 39. Evaluation remains described as very fast because it is a surrogate, with no invented timing. |
| Nonlinearity, noise and experimental budget | Slide 28. More independent, well-spread periods are desirable; no universal sample-count guarantee is given. |
| Experimental design, refinement and final full-model/experimental check | Slides 32, 41 and 44. Optimized LHS is a possible future design, not a claim about existing HEATWISE data. |
| Reference marginals, sampling versus physical uncertainty, dependencies | Slides 16--22 and 37--39. Retain agreed independent uniforms rather than MLE/AIC/BIC fitting. Nataf assumes a Gaussian copula; Rosenblatt is mentioned as an unused alternative. |
| Steady state, thermal inertia and data-only baseline | Preprocessing/PCE chapters; slides 37 and 43. No transient prediction is claimed. |
| Physical resistance model, physics loss, calibration and validation | Slides 33--35; fit physical parameters and tune the loss only inside training cases. |
| LOO/k-fold and global/local metrics | Slides 31--32. Analytic pointwise LOO is not the five-fold case protocol; validation is not computationally free. |
| Control-specific UQ and risk interpretation | Slides 37--38. Conditional moments differ from global reference variance; Cantelli is a proposed valid bound, not an implemented plant guarantee. |
| Sobol interpretation and input elimination | Slide 39. Latent-variable indices need care; removal is not a required outcome. |
| Soft-constrained optimization and practical data limitations | Slides 40--41. Add penalized thermal slack to match the agreed soft-constraint concept; keep actuator/domain bounds hard. |
| Previous settings and measurement operator | Previous settings constrain control changes (40), not the steady-state initial state. The scalar prediction is directly observed, but constructing its measured target requires 18-sensor averaging/max aggregation (26), rather than an identity on raw sensor data. |
| Online/slower learning loops, streams and two-way connection | Slides 42--44; independent safety uses actual temperatures and the control rate is not inferred from five-minute archive spacing. |
| Infrastructure and deployment | Slide 45: acquisition, MQTT/OPC UA examples, time-series storage, Python/UQLab, edge execution, actuation, safety and maintenance. No live stack is installed. |
| GP/PCE/PI-PCE comparison | Slides 46--47; GP uncertainty is conditional on assumptions, and UQ/Sobol remain possible without the simple PCE coefficient formulas. |
| Implementation status and outlook | Slides 23 and 48 retain the actual completed stages; later modeling/control sections are proposed work. |

## Build from the command line

Prerequisites: Python 3.12+ (already required by the project) and a current
MiKTeX or TeX Live installation with LuaLaTeX. No Python packages, Perl, or
`latexmk` are needed. The build also detects the usual Windows MiKTeX installation
locations if LuaLaTeX is not on PATH.

From the repository root:

```powershell
python presentation/heatwise-thermal-twin/build.py
```

Or from this folder:

```powershell
python build.py
```

On Linux/macOS, use `python3` if `python` is unavailable. To select an executable:

```powershell
python build.py --engine "C:/path/to/lualatex.exe"
```

The PDF is always written to
`presentation/heatwise-thermal-twin/pdf/heatwise-thermal-twin.pdf`, regardless of
the folder from which the script is called. Intermediate files and compilation
logs stay in `build/`. A failed compilation exits with a nonzero status and prints
the LaTeX diagnostics; the last successfully built PDF is preserved.

The script generates the classes and packages from `../rwth-ci/source/` into
`build/rwth-ci/`, then compiles the presentation twice. It uses the supplied
template rather than an independently installed RWTH-CI version and leaves the
template files untouched.

## Edit and build in VS Code

Open the repository folder, edit `main.tex`, and use **Terminal > Run Build Task**
(`Ctrl+Shift+B`) to run **Build HEATWISE presentation**. The task calls the same
Python script as the command above. Open the PDF from `pdf/` after building; a
PDF viewer extension is optional. If you open only this presentation folder in
VS Code, use `python build.py` in the integrated terminal.

## Image paths

All image paths are resolved relative to this presentation folder:

- Project figures stay at their existing locations. Use, for example,
  `\includegraphics[width=\linewidth]{../../results/audit/figures/inputs_and_max_temperature_timeseries.png}`.
- Put additional presentation-specific images in `images/` and reference them
  as `images/filename.png`.
- Reference template images directly as `../rwth-ci/<path-to-image>`.
  Do not copy template images into `images/`.

Project figures are referenced in place. The logo is
`../rwth-ci/tex/cf4dt-logo.png`, configured with the `logofile` class option in
`main.tex`. Separate class options with commas, including the option immediately
before `logofile`. To use a different logo, update that path.

## TeX dependencies and troubleshooting

The template requires LaTeX 2023-10-01 or newer and its normal dependencies,
including Beamer, PGF/TikZ, `fontspec`, `babel` (English), `anyfontsize`, and
`trimclip` (from `adjustbox`). Its font setup selects Arial when available and
otherwise uses Arimo. Install any missing packages using MiKTeX Console or the
TeX Live package manager; in MiKTeX, enabling automatic installation of missing
packages makes the first build easier. An up-to-date full TeX Live installation
also provides the dependencies.

For compilation errors, read the diagnostics printed by the build script or
`build/heatwise-thermal-twin.log`. If template generation fails, its log is saved
as `build/rwth-ci.log`. Close external PDF viewers that lock the output file
before rebuilding.
