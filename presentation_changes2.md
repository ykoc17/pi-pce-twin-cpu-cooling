# Presentation changes for review 2

The existing presentation PDF was updated by editing its editable Beamer sources and rebuilding it. This retains searchable equations, clickable citations and the RWTH template. The new PDF contains **24 main slides and 5 backup slides**. Numbers below are **PDF page numbers**, matching the slide footers.

## Requested corrections

| Request | Original → new slide | Exact change and reason |
| --- | --- | --- |
| 1. Untested combinations / missing model error | 19 → **20**, “Proposed robust control”; new **27** | Replaced `mu + k sigma` with the maximum predicted temperature across a local inlet interval **plus a one-sided final-PCE prediction-error allowance**. Added a requirement that the entire interval lies within a validated operating domain, alongside the existing actuator/rate bounds. Explicitly excludes using the rectangular box or its convex hull as evidence of support. The inlet envelope, error bound and domain are not established, so autonomous commands are gated off. Added the verified-fallback/hardware-protection prerequisites. Backup states the bound's assumptions, interval-mean scope, and how a quadratic's inlet maximum can be checked. This corrects the formulation; it does **not** claim that new validation or a safety certificate has been obtained. |
| 2. Over-temperature synthetic targets | 16 → **17**, “Generating more points”; **15**, **23** | Replaced the unscreened figure with a plot highlighting **10 excluded targets in red** and **118 withheld candidates in gray**. Exclude predictions above the measured maximum, **94.4545 °C**; the original rule reaches **116.9443 °C**. Explain that the rule lacks throttling feedback and high-temperature targets cannot represent validated behavior. Do not clip to 94 °C, which would invent a throttling law. The remaining 118 are not automatically trusted; **zero synthetic points are used in fitting now**. Slide 15 specifies zero physics weight until extra points are validated; conclusion uses the same status. The cutoff is labeled a screening rule, not a hardware limit. |
| 3. Visible validation evidence | New **16**, “Thermal-rule validation”; **15** | Added the existing measured-versus-held-out-predicted figure at readable size. Explain five leave-one-case-out folds, refitting constants and fan reference inside each fold, and the perfect-prediction line. Show pooled RMSE **3.45 °C** and largest absolute error **5.76 °C**. Explicitly identify these as thermal-rule results, not PCE results or a safety bound; disclose that model selection reused the folds and plan nested/new-data assessment. Slide 15 points to this figure. |
| 4. Degree-feasibility overstatement | **13**, new **26** | Replaced “Only polynomial degrees 1 and 2 are feasible” with “Our starting choice: degrees 1 and 2.” State full-basis counts **4/10/20** and the quadratic conditioning warning **kappa ≈ 702**. Explain that sparse/regularized higher degrees remain possible and all choices need validation. Backup defines the normalized Legendre design, ranks **4/10/19**, and condition numbers **4.38/701.97** for linear/quadratic designs. No predictive PCE was fitted to obtain these diagnostics. |
| 5. Reference distributions versus uncertainty | **7**, **10**, **14**; 17 → **18**; 18 → **19**; 22 → **23** | Label independent uniforms as polynomial **basis weighting**, not measured operating probabilities or prediction error. Label global Sobol analysis hypothetical under that reference. Remove the claim that a copula/transformation is required; explain that dependent operating modeling needs evidence and a copula cannot create coverage. Keep local inlet variation separate and require separate measurements for its width. Conditional-moment example remains explicitly illustrative. Sensitivity slide explains that inlet-only Sobol is 1 when variance is nonzero and cannot rank all three inputs. |
| 6. Approximate steadiness / threshold sensitivity | **11–13**; new **25** | Describe the selected periods as **approximately steady**. Slide 13 prominently retains **19 observations**, adding “60-minute dwell: 14 observations.” Backup gives the complete one-at-a-time threshold table: baseline 19; 60-minute dwell 14; standard deviation 0.75 °C → 14; full drift 0.02 °C/min → 14; local drift 0.04 °C/min → 15; 40-minute discard → 18. Clarify that stability is not proof of equilibrium or sample independence. Selection code/data remain unchanged. |
| 7. DP provenance / methods citations | **8**; new **28–29** | Remove the unused DP column entirely. Trace the discrepancy to the `dp_setpoint_kPa` field and raw README versus the Pa pressure-channel dictionary and audit interpretation. Preserve source metadata; the actual setpoint unit remains unconfirmed rather than silently relabeled. Backup asks for owner confirmation. Add linked references for PCE/moments/Sobol, conditional robust-design PCE, bounded nonlinear least squares and scrambled Sobol sampling. Record dataset/article provenance and external verification limits. |
| 8. Cover date | **1** | Added **1.12.2026** under the authors. The RWTH template also places that date in the standard content-slide footers automatically. |

## Consistency corrections accompanying those requests

| Original → new slide | Change |
| --- | --- |
| **4** | Replace calibrated “fan power” notation in the control table with raw fan signal `F`, explicitly unit unverified; matches the model and objective. |
| **5** | Qualify the geometry/CAD requirement as applying to **detailed CFD**, rather than all synthetic-data models. |
| **9** | Change confirmed “CPU throttling” to **suspected CPU throttling**. Identify six targets at least 93.5 °C as a temperature-based flag, not confirmation from frequency telemetry; retain all 19 measurements. Shorten the text to fit its box. |
| **11** | Explain that **our static PCE**, lacking time/state input, does not predict transients. Remove the general claim that PCE cannot model dynamics. |
| **15** | Make fold-local teacher refitting, point regeneration/screening and tuning explicit. Shorten the last bullet to “Same Legendre PCE; linear least squares,” removing the loose PINN analogy and keeping the text inside its panel. |
| 17 → **18** | Shorten the title to “Conditional inlet-temperature moments”; keep the correct numerical derivation and specify separately measured disturbance width for control. |
| 18 → **19** | Require the same inlet range/distribution when comparing settings. Identify squared conditional coefficients as linear/curvature variance contributions. For a full total-degree quadratic, clarify that `b1` may vary with CPU/fan settings whereas `b2` is constant; for degree one, `b1` is constant and `b2 = 0`. |
| 20 → **21** | Separate surrogate coordinates/input/output from controller disturbance/decisions. Restore the surrogate output as maximum CPU interval-mean temperature; describe controller settings separately. Match the proposed domain/error bound and approximate-steadiness terminology. |
| 21 → **22** | Replace generic uncertainty margin with worst-case prediction plus error bound. Require the deployment gate before applying a choice; otherwise fallback. Label the workflow conceptual, with no live control, and retain independent peak protection. |
| 22 → **23** | Align completed/planned status with screened diagnostics, approximate steadiness, basis reference and the outstanding inlet/domain/error validation. |
| 23 → **24** | Thanks slide retained; only renumbered and receives the template date footer. |

## Backup and supporting artifacts

- **25:** selection-threshold sensitivity.
- **26:** degree choice and normalized-design conditioning.
- **27:** assumptions and validation needed for the proposed robust bound.
- **28:** linked methods bibliography.
- **29:** data provenance and unresolved units.
- Added `scripts/build_presentation_evidence.py`, which reproduces numerical checks, screening policy and the new plot without changing original results.
- Added `images/review2/screened_check_points.csv`: all 128 archived candidates have explicit exclusion/withholding status and current physics-loss weight zero. This is a presentation/proposed-training policy artifact; no production PCE trainer exists or was modified.
- Added `images/review2/evidence.json`: source hashes, counts, validation metrics, ranks and condition numbers.
- Added the screening plot as PDF/PNG; reused the original thermal-rule validation plot unchanged.
- Updated the presentation README to match the current slide map and implementation status.
- Saved the repeat review as `presentation_review2.md`. The existing `presentation_review.md` was preserved, including its pre-existing working-tree changes.

## Verification and limits

The deck was rebuilt with two LuaLaTeX passes, rendered and visually inspected. Layout adjustments keep the added notes within their slide bodies. Only the pre-existing cover overflow diagnostic remains. **144 repository tests passed**; screening/count/conditioning checks were independently recomputed from saved CSVs. Original raw/processed data, fitted model parameters, validation outputs and 128 diagnostic targets were preserved.

The eight-minute time limit is still a substantial issue: this request corrected content, without removing the existing main narrative. The second review recommends an eight-slide spoken route. No real inlet-disturbance law, validated PCE error envelope, certified domain, live controller, or independently confirmed DP unit has been manufactured to make the slides appear complete.

## Follow-up: separate model choice and keep generated points out of training

The two later requested corrections are now implemented in the code and deck.
The PDF now has **24 main slides and 6 backup slides**, with existing slide
numbers 1-29 preserved and the new protocol on **slide 30**.

- **Slide 15:** calls the accuracy result an early check; states that formula,
  input ranges and generated-point screening use training cases only. No extra
  targets are approved, so physics-loss weight is zero.
- **Slide 16:** renamed to “Early thermal-rule accuracy check.” Its new plot
  leaves one case out completely, chooses 3 vs 4 constants using only the other
  four, refits on those four and predicts the excluded case. The actual new
  RMSE is **4.49 C**, with largest absolute error **13.26 C**. The choice is
  4 constants for outer cases 1 and 2; 3 constants for cases 3, 4 and 5.
  This remains an early internal check because the existing dataset already
  informed development; new experiments are needed for a fresh final claim.
- **Slide 17:** labels the 128-point figure a full-data illustration, never a
  reusable training set. Its 10/118 split is not reused in validation. All 118
  remaining values stay withheld, not accepted as measured truth. Every test's
  formula, fan reference, input ranges and cutoff use only its training cases.
- **Slide 23:** conclusion now reports the separated early check and prioritizes
  measured-data-only PCE before approving physics-generated targets.
- **Slide 27:** removes the old numerical test-error example from the safety
  warning; no observed error is a safety certificate.
- **Slide 30:** explains the separate choice/test procedure and the optional
  fourth constant. Shows training-only generated-point counts: excluded
  **9/9/11/10/11**, withheld **119/119/117/118/117**. All have training weight zero.
- Added `src/thermal_twin/physics_validation.py` and
  `scripts/review_physics_training.py`. New results are saved separately in
  `results/physics_training_review/`; original results and observations remain
  unchanged. CSVs record train/test IDs, formula choice, input bounds, cutoff,
  predictions and all generated-point statuses.
- Added three meaningful tests: training-only bounds/cutoffs; changing an
  excluded experiment cannot alter its model choice or generated targets; every
  measured row is scored once and no generated point enters fitting.
  **147 tests passed**. Updated presentation evidence, README and the relevant
  review findings; the previous grading estimates were not recalculated.
