# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Branch: main
Current HEAD: 620e23b2f435a088b1f9cd503952f4cf9e35cade

## Objective

Prepare a scientifically defensible prototype for NASA Space Apps 2026 challenge "Be An Earth System Trend Detective". This is a modular analysis workflow, not a claim of inventing a new universal algorithm or physical law.

## Integrated data pipeline

- NASA POWER daily point data: T2M and PRECTOTCORR, default 2021-01-01 to 2025-12-31.
- Quantitative NASA MODIS/Terra MOD13Q1.061 NDVI and pixel-reliability data via ORNL DAAC TESViS public subset API, default 2001-01-01 to 2025-12-31.
- MOD13Q1 subsets are requested in batches of up to ten composites. The API dates endpoint returns a JSON array (not necessarily an object with a dates property); the adapter supports both shapes.
- The adapter requires product version 061 and refuses to mix legacy versions. It applies NDVI scale factor 0.0001 and only accepts pixel-reliability code 0. Raw NDVI and QA values are preserved.
- Default MODIS subset radius is 2 km around the POWER reference coordinate, approximately 4 x 4 km.
- Per-pixel annual NDVI medians, Mann-Kendall/Sen trends, Benjamini-Yekutieli q-values, spatial CSV and GeoJSON are generated.
- Monthly cross-source comparison aligns NDVI with POWER T2M/precipitation for common years, calculates calendar-month anomalies, Pearson/Spearman associations, prior-month precipitation associations and detrended anomaly correlations. It is exploratory, not validation or causation.
- SVG charts are generated for annual temperature, precipitation and NDVI.
- NASA GIBS true-colour RGB browse imagery remains optional exploratory context. The live workflow now passes --skip-gibs because RGB browse imagery is not calibrated science data and the repeated requests add latency without improving the quantitative trend analysis.
- The report contains source provenance, units, quality policy, limitations, outputs and error states.

## Modules

- `science_core/pipeline.py`, `principles.py`: six-stage orchestration.
- `analysis.py`: NASA POWER validation and descriptive summaries; RGB browse comparison.
- `statistical_analysis.py`: annual/monthly/seasonal POWER summaries, descriptive OLS and non-parametric trend results.
- `trend_analysis.py`: Mann-Kendall, exact permutation p-values for annual n<=8, Sen slope and Seasonal Mann-Kendall.
- `spatial_analysis.py`: annual per-pixel medians, pixel trends, BY correction and approximate MODIS sinusoidal coordinate helper.
- `ornl_modis.py`: ORNL DAAC MOD13Q1.061 NDVI and QA downloader with retries and version enforcement.
- `cross_source_analysis.py`: monthly NDVI/POWER alignment and anomaly correlations.
- `visualization.py`: dependency-free SVG line charts.
- `cli.py`: end-to-end collection and report artifacts.

## Tests and verification

- Latest fully verified offline suite: 40 tests passed in GitHub Actions run #28.
- Run #29 tests for the --skip-gibs change: completed successfully.
- Run #30 tests after changing concurrency: queued; verify when available.
- Earlier live run #3 (old pipeline) succeeded with 1,826 POWER temperature records, 1,826 precipitation records, 59/60 GIBS images and 58 RGB comparisons. Artifact: https://github.com/Alex1-brown/1111/actions/runs/42384269989/artifacts/13578264908
- Live run #4 (old CLI revision, with GIBS enabled and before the ORNL dates-array fix) has remained in progress since 2026-11-07T15:44:38Z. It is superseded and should not be treated as validation of the current code.
- Current intended live run #8 (latest HEAD, MOD13Q1.061 enforced, GIBS skipped, SVG and cross-source outputs enabled) is queued behind run #4. Run #7 is an earlier pending revision. Inspect Actions carefully; do not claim live MODIS results until a latest-HEAD run completes successfully.
- Current Actions concurrency uses `cancel-in-progress: true` to reduce stale pending work, but this does not retroactively cancel an already-running run. There is no confirmed cancellation of run #4.

## Scientific caveats

- POWER is a gridded point estimate, not a local weather-station observation.
- MOD13Q1 NDVI is a 16-day vegetation-index composite, not direct temperature or precipitation.
- NDVI spatial support is a local approximately 4x4 km sample; POWER is a gridded point. Monthly associations are exploratory, not direct validation.
- Annual medians suppress seasonal variation and hide within-year dynamics.
- Current Mann-Kendall p-values are not corrected for temporal autocorrelation. BY adjusts spatial multiple testing only conditional on valid pixel p-values.
- The GeoJSON coordinate helper currently assumes the requested coordinate is the center of the middle MODIS pixel and applies an inverse sinusoidal transform. It is explicitly approximate; verify against authoritative source geotransform before claiming precise geolocation.
- A statistically detected trend does not establish its cause.

## Immediate next steps

1. Monitor current live Actions runs. Run #4 is stale; #8 is the intended current revision.
2. When the latest-HEAD run completes, inspect logs and artifact contents: MOD13Q1 version, composite count, QA counts, accepted pixel observations, grid dimensions, trend pixels, BY-significant pixels, annual NDVI summary, monthly cross-source rows, SVG files and GeoJSON.
3. If ORNL API rejects version 061 or the subset API returns an unexpected shape, do not weaken version checks or mix versions. Inspect source response and select an authenticated/official alternative only if needed.
4. Verify MODIS geolocation against source metadata.
5. Add temporal autocorrelation diagnostics/adjustment before making inferential significance claims.
6. Preserve one live run per meaningful integrated pipeline change; use offline tests for other changes.

## Work constraints

Work only on this NASA project until the hackathon starts on 2026-11-14. Do not resume other projects during this period. The scheduled NASA-only daily work automation is set for daytime Asia/Dushanbe, 2026-11-08 through 2026-11-13. Previous automations for unrelated projects have been paused.
