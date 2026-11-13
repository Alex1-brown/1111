# Residual moving-block bootstrap calibration audit

**Date:** 2026-11-13  
**Repository branch:** `benchmark/block-bootstrap-20261113`  
**Benchmark run:** [GitHub Actions #43387777284](https://github.com/Alex1-brown/1111/actions/runs/43387777284)  
**Artifact:** [block-bootstrap-calibration.json](https://github.com/Alex1-brown/1111/actions/runs/43387777284/artifacts/14018714703)

## Question

Can the repository's current `moving_block_bootstrap_mk` implementation be treated as an inferential test with nominal 0.05 type-I error, and do its percentile Sen-slope intervals achieve nominal 95% coverage under simple serially correlated data?

## Reproducible design

The benchmark calls the existing `science_core.bootstrap_validation.moving_block_bootstrap_mk` implementation without changing its algorithm or parameters.

- Null experiment: stationary Gaussian AR(1) series with zero deterministic trend.
- Interval-coverage experiment: a known Sen slope of **+0.01 units/year** plus an independent stationary Gaussian AR(1) error series.
- Sample sizes: 20 and 60 annual observations.
- AR(1) coefficients: −0.4, 0, +0.4, +0.7.
- Circular block lengths: 2, 3 and 4 years.
- Outer Monte Carlo replicates: 200 per scenario.
- Bootstrap resamples per fit: 399.
- Nominal test level: 0.05.
- Seed: 20261113.
- Uncertainty for empirical proportions: two-sided 95% Wilson score intervals.

The AR(1) generator has unit marginal variance and stationary Gaussian initialization. These are statistical test series only; they are not satellite observations and do not imitate Earth-system data.

## Results

Ranges below are the minimum and maximum empirical rates across block lengths 2, 3 and 4 for each sample-size / autocorrelation combination.

| n | AR(1) phi | Null rejection rate (nominal 5%) | Sen 95% interval coverage (nominal 95%) |
|---:|---:|---:|---:|
| 20 | −0.4 | 4.0–8.0% | 85.0–91.0% |
| 20 | 0.0 | 4.0–8.5% | 81.0–86.0% |
| 20 | +0.4 | 12.5–15.5% | 71.0–74.5% |
| 20 | +0.7 | 22.0–23.5% | 60.5–63.0% |
| 60 | −0.4 | 1.5–3.0% | 89.0–93.0% |
| 60 | 0.0 | 4.0–6.5% | 89.0–92.5% |
| 60 | +0.4 | 8.0–11.5% | 77.5–81.0% |
| 60 | +0.7 | 16.5–26.0% | 66.5–74.0% |

For example, at n=60 and phi=+0.7 with block length 2, the null rejection rate was **26.0%** (95% Wilson interval **20.4–32.5%**), while the nominal 95% Sen interval covered the true slope in **66.5%** of experiments (95% Wilson interval **59.7–72.7%**). The complete 24-scenario values and Wilson intervals are in the linked JSON artifact.

## Decision

**The current residual circular moving-block bootstrap is not calibrated for inferential use under the tested AR(1) models.**

- False-positive rates materially exceed 0.05 for positive serial dependence, reaching 26.0%.
- Empirical coverage of the nominal 95% Sen intervals ranges from 60.5% to 93.0%, below the nominal target in every scenario's point estimate.
- Negative autocorrelation can also make the test conservative.
- A Benjamini–Yekutieli transform cannot repair uncalibrated input p-values.

Therefore the project must not label its current block-bootstrap p-values or BY-transformed q-values as statistical significance or FDR-controlled inference. The block-bootstrap Sen intervals must not be presented as calibrated 95% confidence intervals. Retain all of them only as clearly marked sensitivity diagnostics. Nonconstant spatial p/q inference remains withheld; Sen slopes remain descriptive effect-size estimates.

This audit does not prove that every possible block-bootstrap design fails. It evaluates only the exact residual circular implementation and settings stated above. A different null-generating scheme, block-length rule, studentization or dependence model would require a new independent calibration before any inferential use.

## Reproduction

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m science_core.block_bootstrap_benchmark \
  --n 20 60 \
  --phi -0.4 0 0.4 0.7 \
  --block-lengths 2 3 4 \
  --outer-replicates 200 \
  --bootstrap-replicates 399 \
  --seed 20261113 \
  --output artifacts/block_bootstrap_calibration.json
```

The benchmark workflow completed successfully and ran **106 offline unit tests** before the calibration. No NASA live-data workflow was started.
