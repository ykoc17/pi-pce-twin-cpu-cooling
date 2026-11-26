# Presentation review 2

Reviewed **26 November 2026**. Your task: present the idea, motivation, problem and planned methods in **eight minutes: four per presenter**.

Reviewed the PDF, source files, figures, code, results, references and notes. The follow-up deck has **24 main slides and 6 backup slides**. The two requested fixes are included below. No rehearsal or recording was available; scores are retained from the earlier review, not newly graded.

## A. Executive assessment

The revised presentation explains its limits more clearly. It shows prediction errors, explains why some generated temperatures should not be trusted, and separates assumed distributions from real temperature fluctuations. The largest remaining problem is length: there is too much for eight minutes. Methods that still need testing are acceptable if clearly called planned work. Focus on the problem, your approach, demonstrated results and next steps.

## B. Estimated grading

| Criterion | Weight | Estimated score (/10) | Weighted points | Reason |
| --- | --- | --- | --- | --- |
| Slides | 10% | 8.0 | 8.00 | Consistent appearance; useful prediction plot; some crowded slides. |
| Timing | 15% | 2.5, estimated | 3.75 | All main slides would take much longer than eight minutes. |
| Content | 60% | 8.0 | 48.00 | Main scientific issues corrected; further testing needed and acknowledged. |
| Q&A | 15% | 7.5, estimated | 11.25 | Better evidence; prepare explanations of remaining assumptions. |
| **Total** | **100%** | **Provisional** | **71.00/100** | **An estimate, not an examiner's actual grade.** |

Actual timing, presenter balance and answers are **not assessable without watching you present**. Planned methods are not automatically marked down for being unfinished.

## C. Prioritized findings

**High:** substantial grade impact. **Medium:** needs explanation or improvement. **Low:** smaller presentation issue.

| Priority | Slide | What the issue means | What to do |
| --- | --- | --- | --- |
| High | 1-24, main slides | About 20 seconds per slide is too little for explaining equations and graphs. | Present about eight slides; keep the rest for questions. |
| Medium | 15-16 / 30, physics model and prediction test | **Fixed:** the excluded experiment no longer helps choose the formula. The new check reports RMSE 4.49 degrees C. It is still an early check because these data already informed project development. | Keep the early-check label. Collect new measurements for a fresh final test. |
| Medium | 15 / 17 / 30, generated points | **Fixed:** all generated points stay out of training. Formula, input ranges and screening cutoff are rebuilt from training experiments only. The 118 full-data points remain unverified guesses. | Keep them withheld until checks against measurements justify them. Repeat training-only preparation inside future PCE tuning too. |
| Medium | 20 / 27, proposed control | The equation works **if** its assumptions hold. The inlet fluctuation range, trustworthy operating settings and prediction-error allowance are not established yet. | Explain the experiments needed. Keep control offline meanwhile; test emergency protection and a safe fallback before deployment. |
| Medium | 7 / 19 / 23, sensitivity | You explain how to study sensitivity, but have not calculated which input matters most. | Say the ranking is planned. Expected heating/cooling trends are not measured importance. |
| Medium | 22, workflow | How software reads sensors, stores data and sends hardware commands is unspecified. | Give a simple example setup. Distinguish measured CPU power from a power limit the controller can set. |
| Medium | 13 / 25, data preparation | Requiring 60 rather than 30 stable minutes reduces 19 observations to 14. Several observations share an experiment. | Explain that 19 depends on your rules. Check whether conclusions change with these rules; keep whole experiments together when testing predictions. |
| Medium | 29, pressure units | Files disagree about Pa versus kPa. The original article/dataset could not be checked online. | Ask the data owners. Omit unused pressure information; do not guess a conversion. |
| Low | 7 / 12-15 / 18 / 20 | Small graph labels and crowded equations may be hard to read. | Enlarge key figures; explain one equation at a time; put calculations in backup. |

No confirmed critical scientific error remains within the material inspected.

Checks: **147 code tests passed**, including checks that changing the excluded experiment cannot change its training formula or generated points. [New accuracy results](results/physics_training_review/report.md): **RMSE 4.49 degrees C**, largest error **13.26 degrees C**. The earlier 3.45 degrees C result is marked exploratory. The full-data illustration still has 10 excluded/118 unused points; training-only counts differ by experiment. The quadratic fit's condition number remains **701.97**: weights may change strongly when data change slightly. Original data/results were preserved.

Methods checked against the [UQLab manual](https://www.uqlab.com/pce-user-manual), [Shen-Braatz paper](https://web.mit.edu/braatzgroup/Shen_AIChE_2016.pdf) and official SciPy documentation. Dataset/article references remain independently unverified because access failed.

## D. Timing assessment

Explaining all main slides would likely take **20-26 minutes**, excluding backup. This is an estimate, not a rehearsal result. Introduction, data and calculations take disproportionate time.

Suggested shorter route: **7:30 speaking time, plus 30 seconds spare**.

| Presenter | Current slides to use | Time |
| --- | --- | ---: |
| A | 1: opening; 2: motivation; 13: data and limits; 6: PCE idea | 3:45 |
| B | 15: physics idea; 16: prediction results; 20: proposed control; 23: next steps | 3:45 |

Skip remaining detail; practise the handover. Keep backup 25-30 for questions.

## E. Q&A preparation

1. **Can your controller guarantee safety today?** No. Its assumptions need testing. It predicts temperatures averaged over a period; separate hardware protection must handle short peaks. **Prepare:** explain the required tests.

2. **Why replace mean plus standard deviation?** Spread from inlet changes excludes model mistakes. The proposal checks the full inlet range and adds room for prediction error. **Prepare:** explain how to establish that allowance.

3. **Why remove ten generated temperatures?** The formula predicts above the measured range without representing CPU throttling. The other 118 are also not approved for training. **Prepare:** explain what evidence would justify using them.

4. **Why did RMSE rise from 3.45 to 4.49 degrees C?** The new check chooses the formula without looking at the experiment being scored. It sometimes picks four constants, which predict worse. Both scores concern the thermal rule, not PCE. **Prepare:** explain why a fresh final test still needs new measurements.

5. **Why a quadratic (second-degree polynomial) with 19 observations?** Its ten weights can be fitted, but may be unreliable. **Prepare:** compare simpler fits and methods that discourage unstable weights.

6. **What do the uniform distributions mean?** They are assumptions for building PCE and calculating averages/sensitivity under a chosen scenario. They are not measured fluctuation patterns. **Prepare:** distinguish these from local inlet fluctuations used for control.

7. **Why PCE if the physics formula is already fast?** PCE can fit additional measurement patterns and gives simple mean/variance formulas. Improvement remains unproven. **Prepare:** compare accuracy and computation time fairly.

8. **Are the 19 observations steady and independent?** They pass chosen stability rules, but this proves neither perfect equilibrium nor independence. **Prepare:** explain the rules and the 19-to-14 observation change.

## F. Final action plan

1. [ ] Practise an eight-slide talk with equal speaking time.
2. [ ] Understand the prediction plot and why a separate final accuracy test is needed.
3. [ ] Explain the tests needed before the controller can be used safely.
4. [ ] Compare PCE, physics-guided PCE and the physics formula before claiming an improvement.
5. [ ] Prepare plain answers about distributions, unstable fitted weights, selection rules, units and hardware connections.
