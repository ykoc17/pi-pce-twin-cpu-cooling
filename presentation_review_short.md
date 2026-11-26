# Review: shortened thermal digital twin presentation

Reviewed 26 November 2026: all 37 rendered pages, LaTeX, notes, figure scripts, data, fitting code and saved checks. Main slides 1–12 form the **eight-minute concept talk**; backups follow the index. Four minutes per presenter; fitted-model results are appropriately deferred. No presentation/scientific files changed.

### A. Executive assessment

The deck provides a credible concept talk and categorized technical deep dive. The facility photo, readable selection plot and early research question strengthen the story. Monotonicity constraints have scientific support ([Sharma et al.](https://arxiv.org/abs/2402.15115)). Reference uncertainty, prediction error and deployment limits are distinguished correctly. Remaining weaknesses concern experimental scope, comparison success criteria, and preprocessing details. Timing is plausible but unmeasured. No confirmed critical scientific error was found.

### B. Estimated grading

| Criterion | Weight | Estimated score (/10) | Weighted points | Justification |
| --- | --- | --- | --- | --- |
| Slides | 10% | 8.5 | 8.50 | Complete title/authors/date; consistent layout and useful photo. Some backup graphics and derivative spacing remain weak. |
| Timing | 15% | 8.0, plan estimate | 12.00 | Script fits plausibly; equal split is planned, but no rehearsal evidence or recovery buffer. Actual delivery: not assessable. |
| Content | 60% | 8.2 | 49.20 | Sound concept and equations; scope, comparison criteria and reproducibility need sharper explanations. |
| Q&A | 15% | 8.0, readiness estimate | 12.00 | Organized backups support technical answers; experimental interpretation remains vulnerable. Live performance: not assessable. |
| **Total** | **100%** | | **81.70/100, indicative** | Conditional estimate, not an observed presentation grade. |

### C. Prioritized findings

| Priority | Slide | Issue | Recommended improvement |
| --- | --- | --- | --- |
| High | 3, experiment; 7, monotonicity; 10, twin | Scope is underspecified. Source notes say server fans stayed at 900 rpm; tunnel pressure controlled airflow. Total power hides CPU load distribution. | Add “fixed nine-server setup and tested workload pattern.” Distinguish tunnel cooling from server fans; different workloads can change the hottest CPU at equal power. |
| High | 8, comparison; C4 (p28) | Five cases permit an early comparison, but no clear success rule is stated. Outside-range flags are good; a pooled error alone could still hide a failing case or dangerous underprediction. | Predefine the main error measure and report each case, worst underprediction, and inside/outside-range results. Call this an early internal comparison; reserve a fresh test for new measurements. |
| Medium | A5, “Full preprocessing checklist” (p18); A7 (p20) | “Stable” lacks some numerical definitions, including input-change and temperature-range limits. | Add a backup table from `preprocessing_config.py`, distinguishing sliding-window and whole-interval checks. |
| Medium | 9, coefficient moments; 6, PCE | The displayed variance formula requires an **orthonormal** basis. That condition is explained in B3, but omitted beside the main formula. | Add “For normalized, orthonormal Legendre terms.” This is a missing condition in the explanation, not an error in the implemented calculation. |
| Medium | A1, measured ranges (p14); B3, reference bounds (p23) | The two range tables differ because one uses raw measurements and the other uses processed interval averages. Their headings do not make this explicit. | Label them “raw recorded ranges” and “19 processed-observation ranges.” Explain that validation splits use training-only bounds. |
| Medium | 10, application; E3, optimization (p33) | Actuator/energy limitations are acknowledged; the trade-off weight and operating-choice solver remain unspecified. | In backup, define the weight's units/choice and propose a search or constrained solver. Distinguish this calculation from SLSQP used to fit coefficients. |
| Medium | 2–11, spoken route | The schedule uses every second. Slides 6–9 introduce several unfamiliar ideas consecutively; explaining all backup links would exceed the allowance. | Rehearse to 7:30–7:40, retain an equal split, and leave backup navigation to Q&A. Shorten statistics/hardware commentary first. |
| Low | 7; A6 (p19), D1 (p29), E3 (p33) | Slide 7's derivative fractions are crowded vertically. Several inherited backup labels/equations remain small. | Increase derivative-row spacing. Enlarge the relevant backup panel when answering questions; move supporting explanation onto an extra backup if needed. |

**Checks:** all 19 targets match raw interval means; six are ≥93.5°C. Conditioning (701.97), D1 moments, C3 corner reasoning and figure hashes check out. The [IEA](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai) and [Zenodo](https://zenodo.org/records/23237930) support the introduction. Fan/DP meanings remain unverified.

### D. Timing assessment

The notes contain approximately **767 spoken words**: 395 for presenter 1 and 372 for presenter 2, excluding pointing cues. At 110–130 words/minute, speech takes about 5.9–7.0 minutes; allowing 60–100 seconds for pointing, equations and handover gives roughly **7–8.6 minutes**. This is an estimate; no recording was available.

Suggested rehearsal budget:

| Presenter | Allocation | Focus |
| --- | --- | --- |
| 1 | 1:45 + 0:55 + 1:00 | Introduction; preprocessing; PCE |
| 2 | 1:05 + 0:55 + 0:30 + 1:10 | PI-PCE; comparison; UQ; application/outlook/closing |

Each speaks for 3:40, leaving 40 seconds total contingency. Introduction is the largest compressible section; methods and the comparison plan deserve protection. Backups are outside the eight-minute route.

### E. Q&A preparation

1. **Why PCE rather than ordinary polynomial regression?**  
   It is polynomial regression in an orthonormal basis, making reference moments and sensitivity calculations convenient. Better accuracy is not automatic. **Gap:** demonstrate the practical value in the later comparison.

2. **What makes these constraints physical?**  
   They encode expected heating/cooling directions while other inputs stay fixed; they do not solve a PDE. **Gap:** confirm cooling-signal ordering and decide how to handle contradictory evidence.

3. **Can nineteen observations show improvement?**  
   They support an early grouped comparison; degree selection stays inside training cases. **Gap:** agree on success criteria and obtain fresh cases.

4. **Why independent uniforms despite coupled experimental inputs?**  
   They define equal weighting for the basis and hypothetical Sobol analysis, not operating probabilities. **Gap:** obtain a supported operating/disturbance model for real uncertainty claims.

5. **Why do eight corners suffice?**  
   For total degree at most two, first derivatives are affine; their extreme values occur at box corners. This guarantees signs inside that box to numerical tolerance. **Gap:** no extension to higher degrees or outside the box.

6. **Does the temperature prediction protect CPUs from overheating?**  
   It predicts interval-average temperatures, not short peaks. E3/E4 require validated support and error allowances. **Gap:** establish these and verify protection/fallback.

7. **What happens if throttling changes the observed trend?**  
   High-temperature points are flagged, not proven throttled. Retain them and investigate frequency/workload evidence rather than deleting inconvenient data. **Gap:** establish which observations actually involve throttling.

8. **Is this already a functioning digital twin?**  
   It is a proposed configuration of surrogate, measurement updates, decisions and safety checks. **Gap:** actuator interfaces and validated closed-loop operation remain future work.

### F. Final action plan

1. [ ] State the hardware/workload scope and distinguish tunnel cooling from server fans.
2. [ ] Define comparison success, per-case errors and underprediction reporting.
3. [ ] Add numerical preprocessing criteria and label raw versus processed ranges in backup.
4. [ ] State the orthonormal-basis condition; clarify the proposed operating-choice calculation.
5. [ ] Rehearse both halves with contingency and improve crowded/small technical elements.

**Limitations:** delivery, projection and live Q&A are unobserved. Full article text and the dynamically served UQLab manual were unavailable for complete inspection. Saved threshold checks were inspected, not rerun exhaustively. No new fitting or full test-suite run; achieved model performance was not graded.
