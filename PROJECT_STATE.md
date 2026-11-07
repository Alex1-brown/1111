# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Default branch: main

## Real-data scope
- NASA POWER daily point API: default 2021-01-01 through 2025-12-31; parameters T2M and PRECTOTCORR.
- NASA GIBS MODIS Terra true-colour: request 60 evenly sampled dates across the same five-year period, 512 × 512 pixels each; require at least 50 valid images for a successful run.
- Failed image requests are recorded in report.json; each request retries up to three times. Only valid PNG images with the expected dimensions count.
- Raw imagery is not committed to Git; live artifacts are uploaded for 14 days.

## Architecture
Acquire → Validate → Clean → Process → Verify → Visualize is a reusable software workflow, not a physical law.

- science_core/analysis.py: POWER payload summaries, monthly means and RGB browse-image comparisons.
- science_core/statistical_analysis.py: paired-date annual/monthly/seasonal POWER summaries, descriptive OLS slopes and daily Pearson correlation.
- science_core/nasa.py: NASA POWER and GIBS retrieval with bounded retries.
- science_core/imagery_series.py: deterministic image date sampling and sequence summary.
- science_core/cli.py: live retrieval, analysis, JSON report and CSV export.
- tests/test_analysis.py: offline unit tests.

## Verification status
- Previous live NASA run (2026-11-07): 1,826 daily records for each POWER parameter; 59/60 valid GIBS true-colour images; 58 adjacent RGB comparisons.
- New statistical-analysis code is committed. The Python offline test workflow has been triggered by the commit; check its result before treating the new code as verified.
- A fresh live run is required to generate actual annual/monthly/seasonal results and CSV artifacts from NASA POWER using the new code.

## Scientific limitations and next milestone
- NASA POWER gridded analysis/reanalysis-derived values are not direct local weather-station observations.
- GIBS true-colour RGB browse images are not calibrated reflectance or land-cover classification.
- A real quantitative satellite comparison requires MODIS/Terra MOD11A1.061 LST data, quality screening, spatial/temporal aggregation and a careful distinction between land-surface temperature and 2 m air temperature.
- Five years alone do not establish a robust long-term climate trend. Slopes and correlations in this project are exploratory and do not establish causation.
- Do not claim satellite accuracy, environmental change or climate attribution without independent validation and uncertainty analysis.
