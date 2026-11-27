# Presentation review 10

Reviewed 27 November 2026. Main slide numbers below are logical slides; Appendix codes are stable identifiers.

### A. Executive assessment

This is a scientifically credible concept presentation, with a clear target definition, consistent visuals, appropriate validation structure, and unusually careful uncertainty caveats. The new C5–C8 walkthrough makes the mathematics defensible. The largest weaknesses are the unverified cooling coordinate, fragile quadratic estimation, and insufficiently explicit research question and success criteria. The proposed control diagram needs stronger visible qualification. No confirmed critical mathematical error was found. Results are intentionally deferred to the final presentation; their absence is appropriate for this agreed scope.

### B. Estimated grading

| Criterion | Weight | Estimated score (/10) | Weighted points | Justification |
| --- | --- | --- | --- | --- |
| Slides | 10% | 8.8 | 8.8 | Complete title/authors/date and consistent branding; readable main figures and useful reveals. Some Appendix graphics remain small. |
| Timing | 15% | 10.0, assumed | 15.0 | Full credit under the requested assumption of delivery within eight minutes. |
| Content | 60% | 8.4 | 50.4 | Correct core equations and sound concept scope; experimental interpretation, evaluation criteria and numerical robustness need sharpening. |
| Q&A | 15% | 10.0, assigned | 15.0 | Full credit as requested; actual live performance was not observed. |
| **Total** | **100%** | | **89.2/100** | Conditional estimate, not an observed examiner grade. |

**Evidence and limits.** Inspected all rendered main/Appendix slides, LaTeX, transcript, notes, code, tests and artifacts. Reconstructed all 19 targets and matched figure hashes. [IEA](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai) supports the statistics; [Zenodo](https://zenodo.org/records/23237930) supports the experimental description. Journal full text was inaccessible; instrument specifications, projection conditions and live performance remain unverified. Presentation/source files were unchanged.

### C. Prioritized findings

| Priority | Slide | Issue | Recommended improvement |
| --- | --- | --- | --- |
| High | 3, “RISE ICE Datacenter”; 7, “Add monotonicity constraints”; 10, “The Proposed Digital Twin” | The [source README](data/raw/README.md) says server fans stayed at 900 rpm and tunnel pressure controlled airflow. The raw signal's ordering and actuation remain unverified. | Label it a **tunnel cooling proxy**; distinguish server/tunnel controls, require calibration, and restrict claims to this setup/workload. |
| High | 6, “Polynomial Chaos Expansion”; B4, “Polynomial degree and conditioning”; C4, “Full comparison protocol” | The all-data quadratic condition number, approximately 702, understates validation difficulty. Recomputed inner training designs contain only **10–13 rows for 10 coefficients**, with condition numbers approximately **797–43,674**. Full rank does not imply stability. | Add these design diagnostics to B4. Predeclare a linear fallback or training-only regularization strategy, and report fold-level conditioning. Do not select safeguards using outer-test errors. |
| High | 2, “Why a thermal digital twin?”; 8, comparison; 11, “Outlook” | The operational goal does not state the regression research question. “Errors and trends” leaves success undefined; imposed compliance is not independent physical validation. | Ask whether monotonicity improves case-held-out prediction. Specify RMSE aggregation, worst underprediction and per-case/outside-range reporting; treat compliance as a diagnostic. |
| Medium | 10, “The Proposed Digital Twin”; E3–E4 | “Compare and Actuate” and “verified fallback” lack a visible deployment gate; spoken/Appendix qualifications are correct. | Add: **offline concept; actuation requires validated errors, actuator mapping and tested fallback**. CPU power remains a performance proxy. |
| Medium | 7; C1–C8, physics-informed fitting | The principal method paper is cited in code/report artifacts but absent from these slides. This weakens academic attribution. | Cite [Sharma, Novák and Shields](https://arxiv.org/html/2402.15115v2). Distinguish their inequality-penalty formulation from this project's direct linear constraints and low-degree corner certificate. |
| Medium | A5, “Full preprocessing checklist”; A7, threshold sensitivity | Qualitative stability descriptions omit configured thresholds; count sensitivity does not establish robustness of fitted conclusions. | Tabulate `configs/preprocessing_config.py` thresholds, separating whole-interval/sliding-window checks. Explain their heuristic basis; later repeat comparisons under plausible alternatives. |
| Medium | A1, measured ranges; B3, reference bounds | Range tables differ because A1 uses raw recordings and B3 uses processed observations; the headings do not clearly distinguish them. | Label both populations explicitly. State that each validation fit recalculates bounds from its training subset. |
| Low | 5, preprocessing; A6, selection results | The curve shows recorded maxima, whereas targets use interval means. The target box is correct. A6 labels are small. | Label the curve “maximum recorded CPU reading”; enlarge the relevant A6 panel for discussion. |

### D. Timing assessment

**Accepted duration: within 8:00, full credit by instruction.** Four minutes per presenter is an allocation assumption, not an independent measurement. No reallocation is necessary.

Retain: cover/motivation 0:50; experiment/data choice 1:10; preprocessing 0:55; PCE 1:05; PI-PCE 1:05; validation 0:50; UQ 0:50; twin concept 0:40; outlook/closing 0:35. Total: 8:00. The introduction is substantial but justified. Replace wording rather than extending delivery; reserve Appendix slides for questions. Harmonize the transcript/notes' 5–10-second differences around slides 8–10.

### E. Q&A preparation

Full Q&A credit is retained. These questions identify remaining preparation needs.

1. **What physics is actually imposed?** Three partial-derivative signs, with other inputs fixed; no heat-balance equation or synthetic temperature labels. They are shape assumptions. **Gap:** verify cooling-signal ordering. See C1, C6.

2. **Why do eight points suffice?** For total degree at most two, derivatives are affine and attain extrema at box vertices. Eight corners enforce three signs throughout that box to tolerance. **Gap:** avoid extending this guarantee to higher degrees or outside the box. See C3, C7.

3. **How are coefficients trained?** Evaluate basis terms into A and signed derivatives into B; solve least squares subject to Bc ≥ 0. The implementation retains a feasible ordinary fit or uses SLSQP. **Gap:** know dimensions: N×4/10 and 24×4/10. See C5–C8.

4. **Can 19 observations support a quadratic?** Possibly, but correlated inputs and nearly saturated inner fits make it fragile; rank alone is insufficient. **Gap:** predeclare the stability/fallback policy. See B4 and finding 2.

5. **Why independent uniforms when inputs are correlated?** They define a hypothetical product reference and orthonormal Legendre basis. Resulting Sobol indices describe that reference, not causal effects or observed operating probabilities. **Gap:** an evidence-based operating distribution remains unavailable. See A3, B3.

6. **How do you prevent optimistic validation?** Hold out complete cases; select degree and scale within training data. This remains an internal comparison because the dataset informed development. **Gap:** obtain genuinely fresh cases and declare aggregation criteria. See C4.

7. **Does the target protect against overheating?** It represents the largest interval-mean CPU temperature, not instantaneous peaks. No operational safety guarantee follows. **Gap:** validated error bounds, disturbance envelopes and tested fallback. See E4.

8. **What would establish success or failure?** Better held-out errors without unacceptable underprediction; identical models or worse performance are legitimate outcomes. **Gap:** specify the primary metric and practical acceptance threshold before interpreting results.

### F. Final action plan

- [ ] **1.** Clarify the tunnel signal, physical scope and calibration requirement.
- [ ] **2.** Add inner-fit conditioning evidence and a predeclared stability policy.
- [ ] **3.** Display the research question and explicit comparison criteria.
- [ ] **4.** Make the offline/control qualification visible on slide 10.
- [ ] **5.** Cite the PI-PCE paper and distinguish the project's implementation.
