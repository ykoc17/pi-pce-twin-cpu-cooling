# Presentation review

Reviewed **26 November 2026**: all **23 rendered slides**, linked LaTeX, figures, Python/configuration files, result tables/manifests, READMEs, and supplied concept notes. Brief: **8 minutes, two presenters, 4 minutes each**, emphasizing motivation, problem, idea and proposed methods. No rehearsal, speaker notes or recording were available. Presentation/source files were not modified.

## A. Executive assessment

The presentation has a reproducible experimental foundation, consistent visual identity and correct conditional-PCE algebra. Its main weakness is scope: 23 slides cannot communicate this material convincingly in eight minutes. Scientific vulnerabilities concern extrapolation, uncertainty interpretation, throttling evidence and inconsistent model/controller definitions. The implemented thermal-model validation deserves more prominence than the derivation slides. The concept brief does not require a completed PCE or controller; planned work is appropriately identified in the conclusion. Improve the grade by reducing the main deck, exposing validation evidence and stating precisely what the proposed method can establish.

## B. Estimated grading

| Criterion | Weight | Estimated score (/10) | Weighted points | Justification |
| --- | --- | --- | --- | --- |
| Slides | 10% | 7.5 | 7.50 | Consistent template; several dense formulas and miniature figures. |
| Timing | 15% | 2.5, feasibility estimate | 3.75 | Current material substantially exceeds eight minutes; no timed delivery observed. |
| Content | 60% | 6.5 | 39.00 | Sound foundations; consequential gaps in validation communication and control interpretation. |
| Q&A | 15% | 6.0, preparedness proxy | 9.00 | Repository supports several answers; methodological defenses need preparation. |
| **Total** | **100%** | **Provisional** | **59.25/100** | **Readiness projection, not an observed examination grade.** |

Live timing, actual presenter balance and live Q&A performance are **not assessable**. The timing/Q&A scores estimate deck feasibility and argument preparedness only; neither is a measured performance score.

## C. Prioritized findings

| Priority | Slide | Issue | Recommended improvement |
| --- | --- | --- | --- |
| Critical | 19, “Optimization Problem” | Box bounds permit untested combinations; inlet-only spread excludes model error. The formulation cannot establish thermal safety. | Present a proposed demonstration, restrict decisions to supported conditions, and justify disturbance width, risk factor and error margin. |
| High | Whole deck | 23 slides for eight minutes leaves about 21 seconds per slide. | Retain roughly eight main slides; move derivations, detailed tables and secondary motivation to backup. |
| High | 15–16, “Adding Physics” / “Generating more points” | Ten synthetic targets exceed the measured maximum; the largest is **116.94 °C**. The rule lacks throttling behavior. | Explain that these are unvalidated extrapolations; restrict or explicitly flag their training influence. Do not imply added experimental evidence. |
| High | 15, “Adding Physics” | RMSE lacks a visible validation protocol or prediction plot. Model selection reused held-out results. | Show the existing held-out prediction figure: five case-wise folds, pooled RMSE **3.45 °C**, maximum error **5.76 °C**. Disclose selection optimism; plan nested comparison. |
| High | 13, “Preprocessing results” | “Only degrees 1 and 2 are feasible” overstates sample-count logic. The normalized degree-2 design has condition number approximately **702**. | Say “we restrict full-basis models to degrees 1–2”; report conditioning and grouped validation. Sparse/regularized higher degrees are not mathematically impossible. |
| High | 10 / 14, dependence / distributions | Independent reference uniforms can be confused with physical operating uncertainty. “Copula ... needed” conflicts with the deliberate reference-model choice. | Explicitly separate basis-weighting assumptions from disturbance uncertainty. Label global Sobol results hypothetical; a copula cannot fill coverage gaps. |
| High | 20, “Digital Twin Definition” | The model is a temperature PCE, but its listed outputs are control actions. | Separate surrogate inputs/output from controller disturbance/decisions; retain maximum steady-state temperature as the surrogate output. |
| High | 9, “Problems with the dataset” | Six “throttled” observations are classified through a **93.5 °C target threshold**, not an explicit throttling flag in the fitting code. | Label them suspected/temperature-flagged unless frequency or authoritative experiment evidence confirms the mechanism. |
| Medium | 12–13, preprocessing | Stability thresholds appear definitive, although changing dwell to 60 minutes reduces 19 observations to 14. | Say “approximately steady”; put thresholds and sensitivity in backup. Distinguish nonoverlapping observations from independent replicates. |
| Medium | 5 / 11, synthetic data / steady-state PCE | CAD is not necessary for all synthetic models; PCE itself is not inherently limited to steady state. | Qualify both statements as choices of this project's CFD alternative and static surrogate. |
| Medium | 21, “Workflow” | Data exchange is drawn, but deployment and command interfaces remain unspecified. | Briefly identify acquisition, communication/storage, execution location and feasible CPU/fan actuators; label deployment conceptual. |
| Medium | 8 / references | Slide DP units are **Pa**, while `CASES.csv` and raw README label **kPa**. Later technical claims have few citations. | Resolve the provenance conflict before asserting either unit; omit DP from the short narrative if unused. Add compact method references/backup bibliography. |
| Low | 1 / 7 / 12–17 | Cover lacks course/date; small plot labels and dense algebra hinder projected readability. | Add course/date if required, enlarge one selected interval and validation plot, and move full derivations to backup. |

Supporting evidence: [physics results](results/physics/report.md), [selection sensitivity](results/preprocessing_review/report.md), [input assumptions](results/inputs/assumptions.json). Numerical metrics, hashes and the slide-17 moment formulas were independently checked; **144 tests passed against current source**. The [UQLab manual](https://www.uqlab.com/pce-user-manual) and [conditional-design PCE literature](https://web.mit.edu/braatzgroup/Shen_AIChE_2016.pdf) provide suitable method references. Article/Zenodo pages were inaccessible during checking; their correctness is unresolved, not disproven. The presentation README describes obsolete slide counts/content.

## D. Timing assessment

Estimated current duration: **18–24 minutes**, assuming explanations of equations and figures rather than rapid reading. This is a planning estimate. Proposed allocation, including brief opening/closing:

| Presenter | Main narrative | Minutes |
| --- | --- | ---: |
| A | Motivation/objective; data and 19 observations; coverage limitations; PCE choice | 4:00 |
| B | Physics guidance; conditional UQ; optimization/workflow; validation plan and takeaway | 4:00 |

Aim for **7:30 in rehearsal**, leaving 30 seconds for transitions/overrun. Slides 7, 15 and 17 are especially expensive to explain; the repeated motivation and full algebra should not consume the main talk.

## E. Q&A preparation

1. **Why trust a quadratic with 19 observations?** Ten coefficients fit algebraically, but conditioning and coverage govern reliability. Compare degrees using case-grouped validation. **Gap:** PCE validation is not implemented.

2. **Do 128 generated points solve the data shortage?** They improve representation of the calibrated rule, not experimental information; teacher errors propagate. **Gap:** demonstrate influence of extrapolated targets and physics weight.

3. **Why independent uniforms despite dependence?** They define a mathematical reference, not measured operating probabilities. **Gap:** justify the separate inlet-disturbance distribution and width.

4. **Does the thermal constraint guarantee a chosen failure probability?** Not automatically: a quadratic of a uniform input is generally non-Gaussian, and prediction error is omitted. **Gap:** specify a quantile or justified bound, model-error allowance and transient protection.

5. **What does the physical model actually predict?** One fitted maximum of 18 CPU interval means; its resistance is effective, not a package property. **Gap:** defend three-constant selection and limitations near throttling.

6. **Are all three inputs sensitive and identifiable?** The thermal rule assumes directional effects; empirical PCE rankings remain uncomputed. Three unknown inputs cannot generally be recovered uniquely from one scalar temperature; inputs are measured. **Gap:** state this distinction explicitly.

7. **How would commands reach the hardware?** Through supported power-cap and cooling interfaces, with independent temperature monitoring. Measured power need not equal a directly commandable variable. **Gap:** identify actual interfaces, delays and fan-signal meaning.

8. **Why are the selected intervals equilibrium observations?** They pass reproducible stability heuristics, not a physical equilibrium proof. **Gap:** justify acceptable drift and dwell from thermal behavior rather than the desired sample count.

## F. Final action plan

1. [ ] Reduce to approximately eight main slides; rehearse an equal four-minute split.
2. [ ] Clarify supported-domain and uncertainty limits of the proposed controller.
3. [ ] Promote held-out thermal-model evidence; disclose synthetic extrapolation and validation optimism.
4. [ ] Correct model/controller definitions, degree-feasibility wording and throttling certainty.
5. [ ] Prepare a cited backup pack covering conditioning, thresholds, assumptions, deployment and examiner questions.
