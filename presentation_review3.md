# Presentation review 3

Reviewed **26 November 2026**: **30 rendered slides (24 main, 6 backup)**, sources, figures, code, results, references and notes. Brief: **eight minutes, four per presenter**, covering motivation, problem, idea and methods. No rehearsal/recording or additional speaker notes. Presentation/source files were unchanged.

## A. Executive assessment

Model choice is now separated from scoring, generated temperatures stay out of training, and control is clearly a proposal. The visuals are consistent and the prediction plot is useful. The main weaknesses are excessive length and an unclear explanation of why PCE adds value here. Explain the research question and planned comparison directly; give calculations less speaking time.

## B. Estimated grading

| Criterion | Weight | Estimated score (/10) | Weighted points | Justification |
| --- | --- | --- | --- | --- |
| Slides | 10% | 8.0 | 8.00 | Complete title/authors/date; consistent style; some small figures and crowded formulas. |
| Timing | 15% | 2.5, estimate | 3.75 | Explaining all main slides would exceed eight minutes. |
| Content | 60% | 8.5 | 51.00 | Major scientific concerns addressed; stronger model testing; central PCE argument needs focus. |
| Q&A | 15% | 8.0, preparation estimate | 12.00 | Good evidence and backups; prepare explanations of the remaining assumptions. |
| **Total** | **100%** | **Provisional** | **74.75/100** | **Estimated readiness, not an observed examination grade.** |

Actual timing, presenter balance and live answers are **not assessable**. Scores estimate readiness. Unfinished methods are not automatically penalized in a concept presentation.

## C. Prioritized findings

No confirmed critical scientific error was found.

| Priority | Slide | Issue | Recommended improvement |
| --- | --- | --- | --- |
| High | 1-24, main presentation | About 20 seconds per slide leaves little time to explain the mathematics and graphs. | Choose 8-10 main slides; keep detailed calculations and repeated context for questions. |
| High | 7, “PCE: Advantages”; 15; 18; 20 | The physics formula is already cheap; the controller does not use the presented mean/variance. Why add PCE? | Ask whether physics guidance improves predictions with limited data. Compare against data-only PCE and the thermal formula. Explain: moments support analysis; control checks worst-case PCE temperature. |
| Medium | 15-16 / 30, thermal rule / accuracy check | Slide 15 shows three constants; slide 16 scores a procedure sometimes choosing four. Its 4.49-degree RMSE is not the score of that single three-constant fit. | Label it “accuracy of the model-choice procedure.” The difference from 3.45 degrees does not measure selection bias alone. |
| Medium | 20 / 27, proposed control | The inlet range, model-error allowance and trusted operating region remain unestablished. | Test nearby CPU/fan settings under measured inlet fluctuations; check prediction errors. Keep control offline and retain separate peak protection. |
| Medium | 4 / 20 / 22, control goal / workflow | Raw fan signal is not calibrated fan power; measured CPU power is not itself a command. Hardware/software connections remain vague. | Call the objective a trade-off using a cooling-effort proxy. Name the proposed sensor, storage and command path; distinguish a CPU power-cap command from measured power. |
| Medium | 7 / 19 / 23, sensitivity / conclusion | The slides explain sensitivity methods but do not yet answer which of the three inputs matters most. | Explicitly call that ranking planned. Distinguish expected physical trends from calculated importance; explain that inputs are measured, not reconstructed from one temperature. |
| Low | 15, “Adding Physics” | The text calls z_j generated targets, but the equations use z_j as input locations. | Label z_j “extra input points”; their temperature targets are T_phys(z_j). |
| Low | 7 / 12-15 / 18 / 20 | Small plot labels and dense explanations remain difficult to absorb on a projector. | Enlarge the key evidence; show one main equation at a time. Move the full conditional-moment calculation to backup. |

**Checks:** reproduced RMSE **4.489°C**, maximum error **13.264°C**, and choices **4/4/3/3/3** in memory. All **640** generated points have zero training weight. Rechecked quadratic conditioning (**701.97**) and slide-18 formulas by numerical integration. Latest recorded run: **147 tests passed**, not rerun here. See [accuracy evidence](results/physics_training_review/report.md).

Model-choice separation matches [official validation guidance](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html). [Zenodo](https://zenodo.org/records/23237930) now confirms dataset identity; its kPa description conflicts with local Pa labels. Full article/archive inspection remained blocked. [IEA figures](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai) match slide 2. PCE references: [UQLab manual](https://www.uqlab.com/pce-user-manual), [Shen-Braatz paper](https://web.mit.edu/braatzgroup/Shen_AIChE_2016.pdf).

## D. Timing assessment

Estimated duration: **18-24 minutes**, excluding backup, assuming graphs/equations are explained. Not timed. Introduction/data and calculations take disproportionate time.

Build a shorter talk in this order; target **7:30 plus 30 seconds spare**:

| Presenter | Current slides and focus | Speaking time |
| --- | --- | ---: |
| A | 1: opening; 2: motivation; 9: data problem; 13: 19 observations; 6: PCE idea | 3:45 |
| B | 15: physics guidance; 16: evidence; 20: proposed decision; 23: next steps | 3:45 |

Explain selected points; rehearse the handover. Reserve backup 25-30 for questions.

## E. Q&A preparation

1. **What does 4.49°C RMSE measure?** The procedure that chooses three or four constants without using the experiment being scored. It is neither PCE accuracy nor a fresh external test. **Prepare:** explain the distinction from the fixed three-constant fit.

2. **Why is the largest error 13.26°C?** Case 1 is overpredicted: 107.72°C versus 94.45°C measured. The largest underprediction is 6.06°C. Neither is a guaranteed error limit. **Prepare:** discuss the weak coverage and unstable four-constant choice.

3. **Why PCE when the thermal formula is fast?** Flexible fitting and simple mean/variance/sensitivity calculations motivate testing it; improvement remains unproven. **Prepare:** define the comparison and success measure.

4. **Why not train on the remaining 118 points?** They are formula outputs, not new evidence. All are withheld; training-only generation prevents information from the test entering training. **Prepare:** explain what measurement-based checks would justify using them.

5. **Are independent uniforms realistic?** They define an assumed reference scenario for PCE, not observed operating probabilities. Local inlet fluctuations are separate. **Prepare:** explain how their range will be measured.

6. **Can the controller guarantee safety now?** No. The operating region and error allowance need justification, and averaged temperatures do not protect against short peaks. **Prepare:** describe the planned experiments and hardware fallback.

7. **Are 19 observations enough for a quadratic?** Ten weights can be fitted, but the data may not determine them reliably. The stability rules also change the sample count. **Prepare:** explain grouped testing, simpler models and methods that discourage unstable weights.

8. **Can one temperature identify all three inputs?** Generally no; inputs are measured directly. **Prepare:** distinguish fitting polynomial weights from recovering unknown inputs; estimate evaluation cost without claiming an unmeasured speed advantage.

## F. Final action plan

1. [ ] Build and rehearse the short talk with equal speaking time.
2. [ ] State the research question and planned comparison that justify PCE.
3. [ ] Clearly distinguish the displayed thermal formula from the model-choice accuracy score.
4. [ ] Explain the practical validation and hardware steps before control could be used.
5. [ ] Simplify dense slides; prepare concise answers using the existing backup evidence.
