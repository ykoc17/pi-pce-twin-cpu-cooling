# Speaking notes: eight-minute concept talk

Main route: **slides 1-12 only**. Presenter 1 covers slides 1-6 (0:00-4:00).
Presenter 2 covers slides 7-12 (4:00-8:00). The handover is before PI-PCE.
The following is a rehearsal script; time includes pointing and short pauses.
Do not read every label or hardware detail aloud. The complete information is
available on the slides and in categorized appendix slides.

## Presenter 1: introduction, data and baseline

### 1. Cover - 0:00-0:10

Today we introduce our thermal digital twin concept. We will present the
model-comparison results in the final presentation.

### 2. Motivation - 0:10-0:50

**Reveals:** introduction/statistics initially; click for heat drivers; click for the goal.

Data centers combine growing computing demand with a cooling cost. In 2024,
they used about one and a half percent of global electricity. Cooling takes
roughly seven to over thirty percent of a facility's electricity. More CPU
power, warmer inlet air or less cooling can raise CPU temperatures. Our goal
is more available CPU power within a thermal budget, with less cooling waste.
Can physical trend guidance help a model trained on only nineteen observations?

**Point:** the cooling-share card, then the research question. The growth figure
is visible for context; do not read all three cards word for word.

### 3. RISE ICE Datacenter - 0:50-1:25

**Reveals:** photo/experiment initially; click for the box and input bullet; click for the output bullet.

This photo shows the RISE ICE Datacenter research facility in Lulea, Sweden.
Our data come from nine servers in its server wind tunnel. The original study
compared air cooling with two-phase chip cooling. We use the air-cooling data:
eighteen CPU temperatures, five operating cases, with recorded values every
five minutes. The three model inputs are CPU power, inlet temperature and the
raw fan signal.

**Point:** the facility photo first. The exact processor model is on the slide
for reference; there is no need to read it aloud.

### 4. Why measured data? - 1:25-2:00

**Reveals:** simulator box initially; click for measurements; click for the bottom box.

Simulation could give us more targets at chosen settings. But detailed CFD
would need the geometry and a fluid solver, and its assumptions would add
model uncertainty. We therefore start with experimental measurements: fewer
points, but real heating and cooling behavior. The workflow can use additional
simulated or measured data later, but more data would still need validation.

**Point:** the two columns and our choice. Do not expand this into a CFD tutorial.

### 5. Nineteen observations - 2:00-2:55

**Reveals:** graph/green caption initially; click for the right-hand summary; click for the red limits box; click for the bottom target box.

Our first model describes approximately steady operation. After a load change,
we allow temperatures to settle. The top curve shows CPU power; the bottom
shows the maximum recorded CPU temperature. Green bands are the accepted
intervals. We keep stable periods with all eighteen readings and average within
each interval, giving nineteen observations. We average each CPU separately,
then take the largest of those eighteen averages as the target. This is not
a prediction of short temperature peaks. The complete selection checklist is
in A5, including the longest-interval rule.

**Point:** one load change and one green band. A7 gives threshold sensitivity:
a 60-minute minimum retained duration leaves 14 observations.

### 6. PCE - 2:55-4:00

**Reveals:** model box initially; click for degree choice; click for PCE benefits; click for the input-reference box.

PCE means polynomial chaos expansion. Here it is compact polynomial regression:
known terms multiplied by fitted coefficients. We will start with linear and
quadratic models, giving four or ten coefficients for three inputs. We will
choose the degree using training cases. PCE is fast to evaluate and its
coefficients also give moments and input-influence information. We scale inputs
to minus one to one and use Legendre polynomials. Independent uniforms give
equal weight across the reference ranges. They define the basis, not real
operating probabilities. My colleague will explain the physical guidance.

**Handover at 4:00.** B1 explains the UQLab/SciPy roles; B3 gives scaling; B4
explains why the quadratic needs care. Do not open them during the main talk.

## Presenter 2: methods and digital twin application

### 7. PI-PCE - 4:00-5:05

**Reveals:** introductory bullet initially; click for expected directions; click for the fitting box; click for the assumptions warning.

Our physics-informed version adds monotonicity constraints. With other inputs
fixed, more CPU power should not lower temperature, a warmer inlet should not
lower it, and stronger cooling should not raise it. Zero slope is allowed.
These signs restrict the polynomial while it fits the same measured targets.
We create no extra temperature labels and solve no detailed fluid model.
These are assumptions to test, particularly the fan signal's meaning and the
effect of throttling. They may prevent implausible trends, but cannot guarantee
better accuracy.

**Point:** each derivative sign and its meaning. The sum is measured squared
error. Full fitting details are C1; the eight-corner argument is C3.

### 8. Planned comparison - 5:05-6:00

**Reveals:** case diagram and numbered steps initially; click for the bottom comparison box.

We will compare ordinary PCE and PI-PCE using the same measurements and basis.
Here case one is held out. On the other four, smaller case-wise tests choose
the degree; we refit and predict case one. Repeat until each case has been
tested. Test cases cannot influence model choice. We will compare prediction
errors, underprediction and the expected heating or cooling trends. Some held-out
settings may fall outside the training ranges, which we will flag. Improvement
is a question to test, not an assumed result.

**Point:** orange test case and blue training cases. New cases will eventually
be needed for a fresh final test. C4 contains the complete protocol.

### 9. UQ and sensitivity - 6:00-6:40

**Reveals:** mean/variance box initially; click for the Sobol box; click for the bottom uncertainty note.

For the chosen input reference, the constant coefficient gives the mean, and
the other squared coefficients give the variance. Sobol indices divide that
variance among inputs and interactions. This describes the model under our
reference, not prediction error or measured operating risk. To study local
inlet variation, we would fix CPU and fan settings and rearrange the same
polynomial. The worked algebra is D1.

**Point:** variation on the left, input influence on the right. Do not claim an
operating sensitivity ranking that has not been established.

### 10. Digital twin concept - 6:40-7:25

**Reveals:** main workflow initially; click for “Two other loops:” and both safety/learning loops.

The surrogate is one component of the proposed twin. At a given inlet
temperature, it would help compare CPU and cooling choices. Fast decisions
use predictions; safety checks monitor measured temperatures; a slower learning
loop updates and revalidates the model from new settled data. Initially this
is an offline study. Live commands require tested conditions, error bounds
and actuator mapping. CPU power is a performance proxy, and the raw fan
signal is not yet a calibrated energy cost.

**Point:** the three loops. E2 retains storage, timestamps, versions and model
approval. E3/E4 contain the full control formulation and its limits.

### 11. Outlook - 7:25-7:55

**Reveals:** current status initially; click for the transition arrow and backlog box together.

Today we establish the data foundation, model concept and fair test plan.
For the final presentation we will fit and compare the models, report errors
and reference sensitivity, and assess offline operating choices. We also need
to confirm the fan meaning, address input dependencies and obtain new operating
cases before extending the application.

### 12. Closing - 7:55-8:00

Thank you for listening. We welcome your questions.

## How to use the appendix

The next PDF page is a clickable topic index. Each appendix shows its stable
code in its title/footer and has an Index return button. The main slides link
to relevant details. [coverage_map.md](coverage_map.md) lists every code and PDF
page and maps longer-deck slides to their locations or requested removal.

| Asked about | Go to |
| --- | --- |
| Input ranges / cases | A1 |
| Sparsity, throttling, correlations | A2-A3 |
| Complete selection rules | A5 |
| Why 19 / threshold choices | A6-A7 |
| UQLab, SciPy and the logo | B1 |
| Full Sobol formulas | B2 |
| Uniform reference and scaling | B3 |
| Degrees / condition number | B4 |
| Fitting and corner constraints | C1/C3 |
| Degree selection / test leakage | C4 |
| Conditional moments / sensitivity | D1-D2 |
| Twin definition / learning loop | E1-E2 |
| Optimization / safety requirements | E3-E4 |
| Full outlook | F1 |

## Rehearsal and Q&A

- Rehearse once without interruption. The schedule is a target, not measured
  performance. Reach the handover at exactly four minutes.
- If the first half runs long, shorten statistics/hardware commentary. Keep the
  target definition and the reference-distribution explanation.
- If the second half runs long, shorten slide 9. Keep the fair-comparison plan
  and the limits before control.
- An already-monotone PCE may be unchanged by constraints; improvement is not
  guaranteed. They are prior assumptions, not proof of causal physical laws.
- Uniform-reference moments are not a prediction-error estimate. A temperature
  limit needs separate evidence for disturbances, model errors and tested settings.
- A low-order polynomial is the surrogate component. A functioning linked twin
  would also need the measurement, checking and decision-update loops.
