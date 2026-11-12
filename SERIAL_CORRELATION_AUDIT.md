# Serial-correlation method audit

Last reviewed: 2026-11-12

## Why this audit exists

The project uses the Hamed–Rao (1998) modified Mann–Kendall variance approximation for sufficiently long, equally spaced annual series. That method is approximate: its variance correction depends on an estimated autocorrelation function, lag selection, sample length, and the assumed time-series structure. A software threshold of 10 observations is not, by itself, evidence that the resulting p-value is calibrated.

## Formula and implementation comparison

The approximation in Hamed and Rao (1998), Eq. 30, uses a **signed** weighted sum of significant autocorrelations of detrended ranks:

\[
\frac{n}{n_S^*}=1+\frac{2}{n(n-1)(n-2)}
\sum_{i=1}^{n-1}(n-i)(n-i-1)(n-i-2)\rho_S(i).
\]

The sign matters. Negative rank autocorrelation can reduce the variance of the Mann–Kendall statistic; replacing the signed sum with its absolute value changes that behavior.

The current repository implementation retains the signed sum and uses a two-sided 95% white-noise bound for lag selection. The public pyMannKendall source currently applies abs(sni) after accumulating its selected-lag sum. That implementation is therefore not a neutral reference oracle for negative autocorrelation; it differs from the signed expression printed in Eq. 30. See the [paper](https://doi.org/10.1016/S0022-1694(97)00125-X) and [pyMannKendall source](https://github.com/mmhs013/pyMannKendall/blob/master/pymannkendall/pymannkendall.py).

Hamed and Rao's empirical significance-level tables used 2,000 simulated samples and reported results for sample sizes 60, 120 and 240. They note that the approximation becomes less accurate for strong autocorrelation and smaller sample sizes. Their paper also reports using a 10% threshold for selecting significant rank autocorrelations in the calibration shown in Table 4. The project currently uses a 5% threshold and permits correction from n=10. Those settings are not the same calibration experiment.

## Reproducible project-specific benchmark

Run:

    python -m science_core.serial_correlation_benchmark --n 20 60 --phi -0.7 -0.4 0 0.4 0.7 --replicates 2000 --seed 20261112 --output artifacts/serial_correlation_calibration.json

The benchmark generates stationary Gaussian AR(1) series with unit marginal variance and **zero deterministic trend**. It runs the repository's actual mann_kendall implementation and compares:
- the iid reference p-value;
- the p-value currently reported by the project, including Hamed–Rao when the existing code applies it;
- the fraction of simulations for which the correction was applied;
- the mean applied variance factor; and
- Wilson 95% intervals for the empirical rejection rates at nominal alpha 0.05.

This is an algorithm calibration experiment, not satellite data, not a simulation of Earth observations, and not a universal assessment of all environmental time series. The benchmark does not tune or silently change the method. Interpret the result by comparing the empirical rejection rate and its Wilson interval with the nominal 0.05 level, separately for each AR(1) coefficient and sample size.

## Observed project-specific calibration

The fixed-seed GitHub Actions run [#43179095375](https://github.com/Alex1-brown/1111/actions/runs/43179095375) completed the 2,000-replicate-per-scenario benchmark and uploaded artifact [13925202462](https://github.com/Alex1-brown/1111/actions/runs/43179095375/artifacts/13925202462).

| n | AR(1) phi | iid rejection rate | Current reported rejection rate | Hamed–Rao applied |
|---:|---:|---:|---:|---:|
| 20 | −0.7 | 0.15% | 8.65% | 62.20% |
| 20 | −0.4 | 0.75% | 8.90% | 83.75% |
| 20 | 0.0 | 4.75% | 7.75% | 98.45% |
| 20 | +0.4 | 17.60% | 20.20% | 99.00% |
| 20 | +0.7 | 36.05% | 32.95% | 99.35% |
| 60 | −0.7 | 0.00% | 6.75% | 66.00% |
| 60 | −0.4 | 0.65% | 12.05% | 80.70% |
| 60 | 0.0 | 4.50% | 9.00% | 98.80% |
| 60 | +0.4 | 18.40% | 16.55% | 99.20% |
| 60 | +0.7 | 39.65% | 24.80% | 99.65% |

For white-noise nulls (phi=0), the current reported rate was 7.75% at n=20 and 9.00% at n=60; both 95% Wilson intervals excluded the nominal 5% level. For negative autocorrelation, the current correction also produced substantially more rejections than the iid reference. Under positive autocorrelation it reduced false rejections in some scenarios but remained far above 5%. These are finite Monte Carlo estimates for the stated Gaussian AR(1) models, not universal properties of all environmental series.

**Decision:** the current Hamed–Rao plug-in p-values are not sufficiently calibrated for inferential use in this project under the tested settings. The repository now keeps them as sensitivity diagnostics and withholds them from the spatial BY inferential family for nonconstant pixels. Sen slopes remain descriptive; iid p-values remain reference-only. The block bootstrap is retained as a separate sensitivity analysis and must itself be assessed for calibration and coverage.

## Interpretation policy

- Do not describe a nonconstant pixel trend as statistically significant from the current Hamed–Rao or iid p-value.
- Keep nonconstant pixel p-values and BY q-values null until a calibrated inference method is established.
- Retain Hamed–Rao p-values and variance factors as explicitly labelled sensitivity diagnostics.
- Use block-bootstrap p-values only for the complete consecutive pixel subset actually analyzed; do not imply they validate all pixels.
- Test lag-threshold sensitivity and alternative autocorrelation methods before restoring a spatial inferential family.
- Do not infer a GPM trend until authenticated quantitative GPM observations have actually been ingested.

No satellite observations are generated by this benchmark. No GPM observations were downloaded or analyzed in this audit.
