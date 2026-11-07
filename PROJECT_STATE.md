# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Branch: main
Current HEAD at handoff: 7ea1177872498e31c5e06697ea11266ad072a8ca

## Objective

Build a scientifically defensible prototype for NASA Space Apps 2026 challenge "Be An Earth System Trend Detective". The project is a modular Earth-system trend detection workflow, not a claim of inventing a universal algorithm or physical law.

## Active quantitative data sources

- NASA POWER daily point data: T2M and PRECTOTCORR, default 2021-01-01 to 2025-12-31.
- NASA MODIS/Terra MOD13Q1.061 NDVI and pixel-reliability COGs through the public Microsoft Planetary Computer STAC API collection `modis-13Q1-061`.
- The STAC collection is filtered to item IDs beginning `MOD13Q1.` and platform `terra`; item IDs must contain collection `.061.`.
- Assets used: `250m_16_days_NDVI` and `250m_16_days_pixel_reliability`.
- Planetary Computer COG assets are in the Azure container `modis-061-cogs` under storage account `modiseuwest`. SAS tokens must be requested for the exact account/container in the asset URL: `/api/sas/v1/token/modiseuwest/modis-061-cogs`. A collection-level token for `modis-13Q1-061` may target a different container and produce HTTP 403 for COGs.
- Rasterio reads small HTTP-range windows from the COGs. The COG affine transform and CRS are used for pixel geolocation; the workflow no longer relies on approximate row/column offsets from the requested coordinate.
- NDVI scale factor 0.0001; valid raw range -2000..10000; fill -3000. Only pixel-reliability code 0 is accepted.
- Default date range 2001-01-01 to 2025-12-31; default sample radius 2 km each side of center (about 4 km x 4 km).
- NASA POWER and MODIS NDVI are compared monthly for their common period 2021-2025. The report includes calendar-month anomalies, Pearson/Spearman correlations, prior-month precipitation associations and detrended anomaly correlations. These are exploratory associations, not validation or causation.
- NASA GIBS true-colour browse imagery is optional and skipped by the default live workflow. It is not calibrated science data.
- Report outputs: JSON, CSV, GeoJSON, and SVG annual charts.

## Active modules

- `science_core/pipeline.py`, `principles.py`: six-stage orchestration.
- `analysis.py`: NASA POWER validation and descriptive summaries; optional RGB browse comparison.
- `statistical_analysis.py`: annual/monthly/seasonal POWER summaries, descriptive OLS and non-parametric trend outputs.
- `trend_analysis.py`: Mann-Kendall, exact permutation p-values for annual n<=8, Sen slope and Seasonal Mann-Kendall.
- `spatial_analysis.py`: annual per-pixel NDVI medians, pixel trends, BY spatial multiple-testing correction.
- `planetary_modis.py`: STAC search, item/tile selection, container-scoped SAS token, COG window reads, NDVI/QA screening and COG geolocation.
- `ornl_modis.py`: legacy ORNL DAAC adapter; not used by the live CLI because its version metadata was not reliably exposed by the JSON subset response.
- `cross_source_analysis.py`: monthly NDVI/POWER alignment and anomaly correlations.
- `visualization.py`: dependency-free SVG line charts.
- `cli.py`: end-to-end collection and report artifacts.
- `requirements.txt` includes `rasterio>=1.4.3`.

## Verification status

- Offline tests run #41: success after adding the container-specific SAS token assertion.
- Offline tests run #42: verify README-only change; check status if useful.
- Live run #14: failed with HTTP 403 because the first Planetary Computer adapter used a collection-level token for the HDF container instead of the COG container.
- Live run #15: current code uses the correct account/container SAS endpoint; it is in progress as of 2026-11-07T16:02Z. URL: https://github.com/Alex1-brown/1111/actions/runs/42389209673
- Do not claim successful live MODIS analysis until run #15 (or a later latest-HEAD run) completes and its artifact/logs are inspected.
- Earlier NASA POWER-only live run #3 succeeded with 1,826 temperature records and 1,826 precipitation records. It is superseded for the final scientific report.
- Live workflow skips GIBS by default and uses `cancel-in-progress: true` to avoid stale queued runs.

## Scientific limitations

- NASA POWER is a gridded point estimate, not a local weather-station observation.
- MOD13Q1 NDVI is a 16-day vegetation-index composite, not direct temperature or precipitation.
- NDVI spatial support is a local approximately 4 km sample; POWER is a gridded point. Monthly associations are exploratory, not direct validation.
- Annual medians suppress seasonality and within-year dynamics.
- Mann-Kendall p-values are not yet corrected for temporal autocorrelation. BY corrects spatial multiple testing only conditional on valid pixel p-values.
- A detected trend does not establish its cause.
- COG affine geolocation is source-derived; still inspect CRS, transform, row/column orientation and a reference point in the live artifact before claiming high-precision map accuracy.

## Immediate next steps

1. Monitor live run #15. If successful, inspect COG item count, item IDs, tile IDs, raster grid metadata, QA counts, valid pixel observations, NDVI annual medians, per-pixel trends, BY q-values, monthly cross-source rows, chart files, GeoJSON and artifact URL.
2. Verify the COG asset signing worked for `modiseuwest/modis-061-cogs`; confirm there are no HTTP 403s.
3. Inspect the MODIS COG affine transform and CRS and verify the requested center coordinate maps to the expected pixel.
4. If run #15 fails, inspect the exact first COG read error before changing the data source again.
5. Add temporal autocorrelation diagnostics/adjustment before making inferential significance claims.
6. Keep Actions usage low: offline tests for code-only changes; one live run after a meaningful integrated pipeline change.

## Work constraints

Work only on this NASA project until the hackathon begins on 2026-11-14. Unrelated project automations have been paused. The NASA-only daytime work automation is scheduled for 2026-11-08 through 2026-11-13, Asia/Dushanbe.
