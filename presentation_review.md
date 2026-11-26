# Presentation review

Reviewed 26 November 2026: 30 rendered slides, LaTeX, figures, data, relevant code, tests and reports. **Eight minutes; two presenters, four minutes each.** This is a concept/methods assignment: absent model results are not penalized. No rehearsal or speaker notes were found; live delivery/Q&A are not assessable. Presentation and scientific files were unchanged.

### A. Executive assessment

The concept is scientifically credible. Monotonicity constraints are a defensible form of physics guidance ([Sharma et al.](https://arxiv.org/abs/2402.15115)); the slides correctly distinguish reference distributions from operating uncertainty and avoid claiming thermal safety. The greatest weakness is the amount of material for eight minutes. The control proposal also needs clearer links to actual actuators, useful computing work and the experimental setup. The main research question appears late. Prioritize a shorter spoken route.

### B. Estimated grading

| Criterion | Weight | Estimated score (/10) | Weighted points | Justification |
| --- | --- | --- | --- | --- |
| Slides | 10% | 8.5 | 8.50 | Consistent template and complete cover; some labels/equations are small. |
| Timing | 15% | 3.0, projected | 4.50 | Full 23-slide route exceeds eight minutes. Actual delivery: N/A. |
| Content | 60% | 8.0 | 48.00 | Sound method; control feasibility and scope need clarification. |
| Q&A | 15% | 7.5, readiness estimate | 11.25 | Actuator/assumption questions remain vulnerable. Live performance: N/A. |
| **Total** | **100%** | | **72.25/100, indicative** | Full-route scenario, not an observed grade. |

### C. Prioritized findings

No confirmed **Critical** equation error was identified. Findings concern omissions, communication and unverified assumptions.

| Priority | Slide | Issue | Recommended improvement |
| --- | --- | --- | --- |
| High | 1-23, main deck | Too much material; the specific PI-PCE method begins only at slide 15. | Use 9-11 main slides; move derivations/definitions to backup. Rehearse a four-minute handover. |
| High | 4, "Why a Digital Twin?"; 19, "Proposed robust control"; 21, workflow | Measured power and raw fan signal are treated as commands without an actuator mapping. Maximizing watts need not maximize useful computing; fan energy is uncalibrated. | Call this proposed operating-point selection. Identify actuators, define the objective's units/weight, and distinguish a power proxy from proven performance/energy savings. |
| High | 3, dataset; 15, "Physics-Informed PCE"; 19 | Total power hides CPU load distribution, which can affect maximum temperature. Only nine servers were tested; local notes say their fans stayed at 900 rpm. | Limit scope to measured hardware/workload patterns. Distinguish tunnel cooling from server-fan control; test other workloads before generalizing. |
| High | 16, "Planned comparison"; 30, protocol | Holding out a case can test an unseen inlet/fan regime, not just prediction between observed settings. Only five cases support the comparison. | Explain this distinction; retain backup 30's outside-range flags. Plan per-case errors, a fresh-data test and a predefined improvement criterion. |
| Medium | 2, motivation; 16 | The focused question arrives after extensive background. | Put "Can monotonicity constraints improve a PCE trained on 19 measurements?" beside the project goal. |
| Medium | 7, advantages; 17-19, moments/sensitivity/control | The detailed inlet-moment example does not feed directly into the worst-case constraint. This can obscure why both are included. | Say that moments describe inlet response, while robust control checks the whole inlet range plus model error. Move the algebra and one-input sensitivity discussion to backup. |
| Medium | 8, operating cases; 13, preprocessing results; 14, distributions | Small repeated time-series graphics and excessive decimal precision weaken immediate comprehension. | Keep one enlarged selection figure; point to one accepted interval. Round displayed bounds while preserving exact values in the files. |

### D. Timing assessment

**Estimated duration: 13-17 minutes**, assuming figures/equations are explained; backups excluded. Eight minutes allows roughly 22 seconds per substantive slide. Slides 17-20 are disproportionately detailed. Actual duration and speaking split are unknown.

Suggested allocation after shortening:

| Presenter | Time | Focus |
| --- | --- | --- |
| 1 | 0:00-1:00 | Motivation and question |
| 1 | 1:00-3:00 | Dataset, main problems, 19 approximately steady observations |
| 1 | 3:00-4:00 | PCE and the chosen reference distributions |
| 2 | 4:00-5:10 | PI-PCE and monotonicity constraints |
| 2 | 5:10-6:15 | Fair comparison plan |
| 2 | 6:15-7:45 | UQ/control purpose, limits and outlook |
| 2 | 7:45-8:00 | Buffer and closing |

### E. Q&A preparation

1. **Why PCE rather than ordinary polynomial regression?**  
   PCE uses an orthonormal polynomial basis, enabling direct moment/sensitivity calculations under a stated reference and simple derivative constraints.  
   **Gap:** Explain their project value without promising better prediction.

2. **What makes this physics-informed without a PDE?**  
   Heating/cooling directions restrict allowable curves without extra temperature labels or a solved PDE. An already-monotone baseline may be unchanged.  
   **Gap:** Decide how to handle evidence contradicting a constraint.

3. **Why independent uniforms when inputs are dependent?**  
   They give equal weighting across a reference box, not operating probabilities. Reference Sobol indices cannot establish a real operating ranking.  
   **Gap:** Obtain operating/disturbance data for real uncertainty.

4. **Why do eight corners suffice?**  
   For total degree at most two, derivatives are affine. Their extrema occur at box corners, so corner signs constrain the interior.  
   **Gap:** Do not extend this argument to higher degrees or outside the box.

5. **Can 19 observations establish improved accuracy?**  
   They support an early grouped comparison. Choose models within training cases; new experiments are needed for a fresh final test.  
   **Gap:** Predefine criteria and obtain independent cases.

6. **Does the temperature constraint guarantee safety?**  
   Only with a justified inlet envelope, error bound and tested domain. CPU interval averages do not bound instantaneous peaks; hardware protection remains necessary.  
   **Gap:** None of those deployment requirements is established yet.

7. **Can you command CPU power and fan effort directly?**  
   These are measured quantities. Mapping practical commands to power, cooling and useful performance remains future work.  
   **Gap:** Confirm interfaces, signal meaning and energy calibration.

8. **Why exactly 19 approximately steady observations?**  
   Stability rules accept 19 intervals, not independent equilibria. A 60-minute minimum retained duration leaves 14.  
   **Gap:** Justify tolerances and check threshold sensitivity.

### F. Final action plan

1. [ ] Rehearse an eight-minute, equally split route with 9-11 main slides.
2. [ ] Bound the control claim: actuators, objective meaning and experimental scope.
3. [ ] Introduce the research question early and define comparison success.
4. [ ] Move conditional-moment algebra and detailed control requirements to backup.
5. [ ] Enlarge the key data figure and rehearse the eight answers above.

**Checks and limits:** Recomputed all 19 input means/targets and checked completeness, cases and spacing. Confirmed condition number 701.97, slide 17's moments and saved threshold counts. [IEA statistics](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai), [dataset metadata](https://zenodo.org/records/23237930) and method references were checked. Experimental-article full text was unavailable; local fixed-fan-speed claims need author confirmation. Tests were not rerun. Retained model code/results are intentionally omitted from this concept deck.
