# Project state and handoff

Last updated: 2026-11-09
Repository: https://github.com/Alex1-brown/1111
Branch: main
Current HEAD: see the main branch for the live revision

## Objective

Build a scientifically defensible prototype for NASA Space Apps 2026 challenge "Be An Earth System Trend Detective". The project is a modular Earth-system trend detection workflow, not a claim of inventing a universal algorithm or physical law.

## Current implementation

Workflow: **Acquire → Validate → Clean → Process → Verify → Visualize**

- NASA POWER daily point data: T2M and PRECTOTCORR.
- NASA MODIS/Terra MOD13Q1.061 NDVI and pixel-reliability COGs through Microsoft Planetary Computer STAC collection `modis-13Q1-061`.
- The MODIS adapter selects one 16-day composite per calendar month, nearest to day 15; validates item IDs/version 061; obtains SAS tokens for the exact Azure storage account/container; reads small COG windows with Rasterio; and derives pixel coordinates from the COG affine transform and CRS. It now rejects any shape, CRS, or affine-transform mismatch across dates before combining pixel time series.
- Only MODIS pixel-reliability code 0 enters NDVI analysis.
- Annual pixel medians require at least 3 quality-screened monthly composites per pixel-year.
- The pipeline automatically selects the longest contiguous trend period with at least 11 monthly composites/year. The current data snapshot at this location yields a core period of 2003-2023. Incomplete edge years 2001-2002 and 2024-2025 are excluded from long-term trend inference.
- Per-pixel Sen slopes and nominal 95% intervals. For at least 10 equally spaced observations, Hamed–Rao (1998) modified Mann–Kendall variance correction uses significant autocorrelations of detrended ranks; the same modified variance is used for the Sen interval.
- Spatial BY q-values are computed only over temporally eligible pixel p-values. Irregular/short/unestimable series retain descriptive slopes and iid reference p-values but have null adjusted p-values and q-values. The correction remains approximate.
- Annual aggregate NDVI uses a fixed set of pixels present in every year of the core period, preventing changing spatial coverage from driving the overall trend.
- Pettitt change-point screening and robust MAD anomaly screening for annual series.
- Monthly NDVI/POWER cross-source anomaly correlations are restricted to the core period overlap; exploratory association only, not validation or causation.
- Outputs: JSON, CSV, GeoJSON, SVG charts, and a self-contained offline HTML report with clickable spatial trend grid.
- `HACKATHON_PITCH.md` contains the project brief, challenge alignment, methods, safeguards and next upgrades.

## Important modules

- `science_core/pipeline.py`, `principles.py`: six-stage orchestration.
- `analysis.py`: NASA POWER validation and descriptive summaries.
- `statistical_analysis.py`: annual/monthly/seasonal POWER summaries, descriptive OLS and correlations.
- `trend_analysis.py`: Mann–Kendall, Sen slope, nominal 95% Sen intervals and Hamed–Rao modified variance correction for eligible regular series.
- `change_point.py`: Pettitt single change-point test.
- `anomaly_analysis.py`: robust MAD anomaly screening.
- `spatial_analysis.py`: annual per-pixel NDVI medians, coverage-based core period selection, fixed-panel annual summaries, per-pixel trends and BY q-values over eligible tests only.
- `planetary_modis.py`: STAC search, monthly sampling, COG signing/window reads and quality screening.
- `cross_source_analysis.py`: monthly NDVI/POWER alignment and anomaly correlations.
- `visualization.py`: dependency-free SVG charts.
- `html_report.py`: standalone offline HTML report.
- `cli.py`: integrated data collection and report generation.

## Verified live runs

### Full MODIS COG run #15

- Run ID: 42389209673
- URL: https://github.com/Alex1-brown/1111/actions/runs/42389209673
- Status: success
- Artifact ID: 13581425371
- Artifact URL: https://github.com/Alex1-brown/1111/actions/runs/42389209673/artifacts/13581425371
- 515 available Terra MOD13Q1.061 composites; 272 monthly samples.
- 17 x 17 pixels; 231.656 m native pixel size.
- 78,608 pixel/composite rows; 43,891 good-quality observations (reliability code 0).
- 27,438 marginal, 2,837 snow/ice, 4,442 cloudy observations.
- This run preceded coverage-based trend-period selection and the offline HTML report integration; its trend statistics included incomplete edge years and must not be used as the final trend report.

### Monthly-sampled MODIS run #20

- Run ID: 42390016313
- URL: https://github.com/Alex1-brown/1111/actions/runs/42390016313
- Status: success
- Artifact ID: 13581530111
- Artifact URL: https://github.com/Alex1-brown/1111/actions/runs/42390016313/artifacts/13581530111
- 515 available composites; 272 monthly samples.
- 78,608 pixel/composite rows; 43,891 good-quality observations.
- Cross-source analysis in this earlier artifact used 36 common months across 2021-2025, including incomplete edge-year months; superseded by the current core-period restriction.
- This artifact showed why coverage control is necessary: only 1-2 selected composites were available in 2024 and 3 in 2025; those years cannot support full annual trend inference.

### Final integrated run #21

- Run ID: 42390671501
- URL: https://github.com/Alex1-brown/1111/actions/runs/42390671501
- Head SHA: aca7cc3d947e8ffdc720b3d34037fcc1caffe46f
- Status: success; artifact ID 13581860343 was downloaded and inspected.
- This run uses coverage-based 2003-2023 core period selection, fixed-panel annual NDVI, minimum 3 valid composites per pixel-year, and the generated offline HTML report.
- Run #21 completed successfully; artifact ID 13581860343 is available at https://github.com/Alex1-brown/1111/actions/runs/42390671501/artifacts/13581860343.
- Artifact inspection: 272 monthly MODIS samples; 17 × 17 pixel window; 78,608 raw pixel/composite rows; 43,891 reliability-code-0 observations; 231 pixels in the fixed annual panel; 261 pixel trend estimates; 33 matched NDVI/POWER months over 2021–2023. The artifact predates the Hamed–Rao correction, so its old per-pixel p/q values are a baseline only and must not be presented as corrected inference.

## Offline tests

- Last completed offline CI run before the current change set: Python tests run #72, success, on commit c43b4dbcc16b42329f1e93b68a332a89cb3e88cc.
- The current change set adds deterministic AR(1), irregular-spacing, seasonal-strata, spatial-eligibility and HTML-report regression tests. The resulting CI run must be checked after commit.
- Live NASA data workflow remains manual-only to conserve Actions quota; no new live collection is needed for this statistical change.

## Scientific caveats

- NASA POWER is a gridded estimate, not a local weather-station record.
- MOD13Q1 NDVI is a vegetation index, not temperature or precipitation.
- NDVI and POWER have different spatial support.
- Monthly correlations do not establish causation or validate either source.
- Hamed–Rao variance correction is approximate and only attempted for at least 10 equally spaced observations with estimable detrended-rank autocorrelation. Short/irregular series are excluded from the spatial BY family.
- Pettitt p-values remain unadjusted for serial dependence. Five-year POWER annual/seasonal summaries are too short for the Hamed–Rao correction and remain exploratory.
- BY q-values are conditional on the eligible pixel family; they do not establish causation or guarantee that all dependence is removed.
- The spatial subset is a local sample, not a region-wide census.
- Planetary Computer STAC collection license metadata must be followed; do not assume the hosted collection is public-domain simply because the source product is NASA.

## Immediate next steps

1. [Completed 2026-11-09] Download and inspect the successful run #21 artifact, including report JSON, annual summaries, per-pixel CSV/GeoJSON and offline HTML. Treat its pre-correction p/q values as a historical baseline only.
2. Review the new Hamed–Rao outputs from the next offline test run; verify how many pixels are eligible, how many are excluded for irregular spacing or unestimable residual-rank ACF, and whether q-values are computed only over the eligible family.
3. Benchmark the Hamed–Rao implementation against controlled AR(1) simulations and an independent reference implementation; test sensitivity to the significant-lag threshold and missing-year patterns.
4. Add an independent quantitative precipitation product such as GPM IMERG only after confirming open access, product version, units, QA flags, temporal aggregation and licensing. Do not call the current NDVI/POWER correlations validation.
5. Prepare a short reproducible demo and final hackathon submission. Avoid another live NASA data run unless a material scientific change requires it.

## Work constraints

Work only on this NASA project until the hackathon begins on 2026-11-14. Unrelated project automations have been paused. NASA-only daytime work automation is scheduled for 2026-11-08 through 2026-11-13, Asia/Dushanbe.
