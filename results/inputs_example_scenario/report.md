# Input distributions: two separate probability-model concepts

Read **19 accepted operating-period means** from `data\processed\steady_state.csv`.
Source SHA-256: `c7e97366301e21139c4d1859d09d0c5be132042db7c30d6ebf8615a3ac91661d`. Backend: official local ETH UQLab.py 0.800.

## A. Assumed independent reference distributions

| Input | Uniform lower bound | Uniform upper bound | Unit |
| --- | --- | --- | --- |
| total_cpu_power_W | 384.735294118 | 1786.22580645 | W |
| server_inlet_air_temp_tunnel_C | 25 | 45.0555555556 | degC |
| tunnel_fan_power_raw | 0.121636363636 | 0.730571428571 | unverified raw signal |

The JSON/CSV parameters retain full floating-point precision; the displayed table is rounded.
Bounds are exactly the smallest and largest accepted period means, without padding.
All three marginals are Uniform(a,b), with an explicitly independent copula.
Equal-width ranges receive equal reference weight. This is an assumption for a
Legendre PCE basis and hypothetical global UQ/Sobol analysis, not a conclusion
that the experimental inputs were independently sampled.
Map each input to xi=2*(x-a)/(b-a)-1. Normalized Legendre polynomials
sqrt(2*n+1)*P_n(xi) form an orthonormal tensor basis under A's product measure.
Existing experimental observations need not be iid uniform to use regression PCE;
coverage and regression conditioning still require review. No surrogate is fitted here.

## Histograms, candidate densities and QQ plots

Each period counts once; long periods do not get more descriptive weight.
The histogram describes the experiment and the preprocessing selection.
Uniform is the instructed reference. Symmetric triangular and Beta(2,2) curves
use the same bounds and fixed shape parameters, solely to illustrate other
possible assumptions. All candidate densities are evaluated with UQLab.py.
There is no density fitting, AIC/BIC ranking or claim of a best physical law.
QQ plots compare sorted observations with uniform quantiles at (i-0.5)/n.
Departures describe the controlled sampling pattern; they do not disprove a
deliberately chosen reference. CDF distances and QQ errors are descriptive;
no iid goodness-of-fit p-values are reported, including because bounds come from these data.

## B. Optional dependent operating-scenario model

Status: **user_specified_not_fitted**. HEATWISE estimation: **not_estimated_from_HEATWISE**.
The accepted observations have inlet/fan Pearson r=0.8263
and Spearman rho=0.7742. The earlier raw-data audit used
1,308 labeled time rows; those scores must not be confused with these 19 period means.
Pooled, within-case and leave-one-case-out scores are saved without independence p-values.

Why no dependent operating distribution is estimated:
- Only 19 selected periods from five controlled experimental cases; iid operational sampling is not established.
- Inlet and fan settings were coupled by the case design; observed correlation describes that design.
- Inlet values cluster near three setpoints, with ties and gaps; a smooth Gaussian copula is not established.
- Unequal accepted counts per case are selection outcomes, not operating-scenario probabilities.
- A nonsingular empirical correlation would not establish statistical reliability or Gaussian-copula adequacy.

An optional JSON scenario supplies a named **latent-normal correlation matrix**,
in the documented input order, with the same uniform marginals as A. This assumes
a **Gaussian copula**. A matrix's numerical validity does not establish physical
or statistical validity. No empirical correlation is silently substituted.
Matrices must be finite, symmetric, unit-diagonal, strictly positive definite and
well conditioned; invalid matrices are rejected without nearest-PD repair.
For uniform marginals, physical Pearson and Spearman correlations equal
(6/pi)*asin(R_ij/2) in the assumed population, not R_ij itself.

Forward Nataf: marginal CDF -> normal quantiles -> Cholesky whitening.
Inverse Nataf reverses these steps. Both use UQLab.py public APIs.
Exact uniform endpoints map to infinite normal scores, so forward transformation
rejects them rather than clipping the observed extrema. Extreme normal scores
that numerically saturate a uniform bound are also rejected. Interior round trips,
latent covariance and matrix rejection are covered by tests.
The optional samples are synthetic scenario illustrations, not new training data.
Classical independent-input Sobol formulas belong to A; do not apply them unchanged
to B's dependent physical inputs. Sobol indices of transformed independent normal
coordinates concern those coordinates, not the original three physical inputs.

## Interpretation and limits

The reference box includes untested combinations, such as 25 C inlet with high
fan signal. The cases do not fill that box. A Gaussian copula still places mass in
untested regions and does not enforce observed case trajectories or establish safe
operation. Neither concept validates extrapolation or optimization there.
Propagating assumed inputs would describe scenario variability, not by itself
sensor error, coefficient uncertainty or surrogate prediction error.
**The fan-signal unit is unverified**; no conversion to W or kW is made.
No predictive model, output uncertainty propagation or Sobol analysis is run in this step.

## Outputs and reproduction

`reference_model.json`, `scenario_model.json`, `candidate_densities.json`,
`assumptions.json` and `manifest.json` record models, assumptions and provenance.
`tables/` contains exact parameters, QQ points, descriptive diagnostics,
dependencies, case spans and reproducibly sampled reference/scenario inputs.
`figures/` contains publication PNG/PDF histograms, densities, QQ plots and joint comparisons.

```
thermal-twin inputs
thermal-twin inputs --scenario configs/input_scenario_example.json --output results/inputs_example_scenario
```

The example matrix is illustrative, not estimated from HEATWISE. The main default
report leaves B inactive. The local package needs Python >=3.12 and pandas >=3.0.3.
Sources: [official package](https://pypi.org/project/uqlab/0.800/); [ETH documentation](https://www.uqlab.com/#documentation).
