# Eight-minute presentation transcript

For the shortened presentation, slides **1–12**. Presenter 1 covers slides 1–6; presenter 2 covers slides 7–12. Handover: **4:00**.

Read the plain paragraphs aloud. Bracketed directions are silent cues. Each click reveals the next part of the current slide; advance normally between slides. Slide numbers refer to the numbers on the slides, not PDF page numbers. The appendix is for questions.

The timings include clicks and short pauses. Aim for a calm pace of roughly **115–120 words per minute** and check the timing in rehearsal.

## Presenter 1 — 0:00–4:00

### Slide 1 — Cover | 0:00–0:10

Today we introduce our concept for a thermal digital twin of a data center, using physics-informed polynomial chaos expansion.

### Slide 2 — Why a thermal digital twin? | 0:10–0:50

[Initially: introduction and statistics.]

Data centers support AI and many other services. They used around one and a half percent of global electricity in 2024. Cooling alone takes seven to over thirty percent of a facility’s electricity.

[Click 1: heat-driver diagram.]

More CPU power, warmer inlet air, or less cooling can raise CPU temperatures.

[Click 2: goal.]

Our goal is to support more computing within a temperature limit, while avoiding unnecessary cooling effort.

### Slide 3 — RISE ICE Datacenter | 0:50–1:25

[Initially: photo and experiment details. Point briefly to the photo.]

Our measurements come from the RISE ICE Datacenter research facility in Luleå, Sweden. We use its server wind-tunnel experiments: nine servers, eighteen CPUs, five air-cooling cases, and values recorded every five minutes.

[Click 1: input bullet.]

Our three model inputs are total CPU power, inlet air temperature, and the raw fan signal.

[Click 2: output bullet.]

The output is the largest averaged CPU temperature. I’ll explain how we construct that target.

### Slide 4 — Why start with measured data? | 1:25–2:00

[Initially: simulator-generated targets.]

Simulation could provide temperatures at many chosen settings. But detailed fluid simulation would require a data-center geometry and a solver such as OpenFOAM. Its assumptions would also introduce model uncertainty.

[Click 1: experimental measurements.]

We therefore start with experimental measurements: fewer points, but observations of real heating and cooling behavior.

[Click 2: bottom box.]

The workflow can later use additional measured or simulated data. Any improvement would still need validation.

### Slide 5 — From time series to 19 observations | 2:00–2:55

[Initially: graph and green caption. Point to a load change, then a green band.]

CPU temperatures take time to settle after a load change. The green bands mark the intervals we keep; each becomes one observation.

[Click 1: right-hand summary.]

We retain stable periods with all eighteen CPU readings and average within each period. This leaves nineteen approximately steady observations.

[Click 2: red limits box.]

The data are sparse, the inputs are coupled, and some high-temperature observations may involve throttling.

[Click 3: bottom target box.]

For each interval, we average each CPU’s temperature separately, then take the largest of those eighteen averages. Our model therefore describes settled temperatures, rather than short temperature peaks.

### Slide 6 — Polynomial Chaos Expansion | 2:55–4:00

[Initially: model box. Gesture to the sum, without reading every symbol.]

Our baseline is polynomial chaos expansion, or PCE. Here, it is a compact polynomial regression model. We combine known polynomial terms and fit their coefficients to the measured temperatures. Each input is scaled to the range minus one to one.

[Click 1: “Small enough to start.”]

We will start with linear and quadratic models: four or ten coefficients for three inputs. We choose the degree using training data.

[Click 2: “Why PCE?”]

PCE is fast to evaluate. Its coefficients also let us calculate temperature variation and input sensitivity directly.

[Click 3: input-distribution note.]

We use independent uniform reference distributions and normalized Legendre polynomials. This gives equal weight across the input ranges. It does not mean real operating conditions are equally likely or independent.

My colleague will now explain how we add physics.

[Handover at 4:00.]

## Presenter 2 — 4:00–8:00

### Slide 7 — Add monotonicity constraints | 4:00–5:05

[Initially: introductory bullet.]

Our question is whether physical trend guidance can improve a PCE trained on these same nineteen observations.

[Click 1: expected directions.]

We add monotonicity constraints. Change one input while keeping the other two fixed: more CPU power should not lower temperature; warmer inlet air should not lower it either; stronger cooling should not raise it. A zero slope is allowed.

[Click 2: fitting box.]

The formula still minimizes squared errors against measurements. The difference is that the coefficients must also satisfy those derivative signs. We generate no additional temperature targets.

[Click 3: assumptions warning.]

These directions are assumptions to test, especially the cooling signal’s meaning. They restrict implausible shapes, but they do not guarantee more accurate predictions.

### Slide 8 — Planned PCE versus PI-PCE comparison | 5:05–5:55

[Initially: case diagram and numbered steps. Point to the orange test case.]

We will compare ordinary PCE with physics-informed PCE using the same measurements and candidate polynomial bases.

We hold out one complete operating case. Within the other four cases, smaller case-wise tests choose the degree. We then refit and predict the untouched case. Repeating this gives predictions for all five held-out cases, without using a test case to choose its model.

[Click 1: comparison box.]

We will compare errors and heating or cooling trends, and flag predictions outside the training ranges. This is an early comparison, not a safety demonstration.

### Slide 9 — UQ and sensitivity | 5:55–6:45

[Initially: mean-and-variance box.]

With our normalized basis, the constant coefficient gives the mean. The remaining squared coefficients sum to the variance, under our chosen input distributions.

[Click 1: Sobol box.]

Sobol indices express shares of that variance. First-order means one input alone; total also includes interactions. For the total index, we sum squared coefficients of terms containing that input and divide by total variance.

[Click 2: bottom note.]

This describes model variation, not prediction error. For local inlet fluctuations, we would fix CPU and fan settings and rearrange the same polynomial, using a separately measured inlet range.

### Slide 10 — The proposed digital twin | 6:45–7:25

[Initially: main workflow. Follow the boxes from left to right.]

The surrogate is one part of the proposed twin. We measure current conditions, predict settled temperatures, and compare CPU-power and cooling choices. Actuation is a future step: it needs validated predictions, tested operating conditions, and a mapping to actual controls.

[Click 1: “Two other loops:” and both loops.]

A safety loop would monitor actual temperatures, with hardware protection and a verified fallback. A slower learning loop would collect new steady data, refit the model, and validate each update.

### Slide 11 — Outlook | 7:25–7:55

[Initially: current status.]

So far, we have established the nineteen-observation data foundation, the model concept, and the comparison plan.

[Click 1: transition arrow and backlog box together.]

Next, we will fit PCE and PI-PCE, compare prediction errors, and study sensitivity under the chosen reference. We will then update the digital twin concept based on the evidence. Improved prediction remains something to demonstrate.

### Slide 12 — Thanks | 7:55–8:00

Thank you for listening. We welcome your questions.

[Stop here. Use the appendix only when answering questions.]
