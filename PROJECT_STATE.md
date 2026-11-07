# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Branch: main
Current HEAD: 4b0282a1f211826381b4918688703655bde3ec74

## Objective

Build a scientifically defensible prototype for NASA Space Apps 2026 challenge "Be An Earth System Trend Detective". The project is a modular Earth-system trend detection workflow, not a claim of inventing a universal algorithm or physical law.

## Current implementation

Workflow: **Acquire → Validate → Clean → Process → Verify → Visualize**

- NASA POWER daily point data: T2M and PRECTOTCORR.
- NASA MODIS/Terra MOD13Q1.061 NDVI and pixel-reliability COGs through Microsoft Planetary Computer STAC collection `modis-13Q1-061`.
- The MODIS adapter selects one 16-day composite per calendar month, nearest to day 15; validates item IDs/version 061; obtains SAS tokens for the exact Azure storage account/container; reads small COG windows with Rasterio; and derives pixel coordinates from the COG affine transform and CRS.
- Only MODIS pixel-reliability code 0 enters NDVI analysis.
- Annual pixel medians require at least 3 quality-screened monthly composites per pixel-year.
- The pipeline automatically selects the longest contiguous trend period with at least 11 monthly composites/year. The current data snapshot at this location yields a core period of 2003-2023. Incomplete edge years 2001-2002 and 2024-2025 are excluded from long-term trend inference.
- Per-pixel Sen slopes and Mann-Kendall trend tests; Benjamini-Yekutieli spatial q-values. Temporal autocorrelation is not yet adjusted, so these q-values are exploratory, not definitive significance claims.
- Annual aggregate NDVI uses a fixed set of pixels present in every year of the core period, preventing changing spatial coverage from driving the overall trend.
- Pettitt change-point screening and robust MAD anomaly screening for annual series.
- Monthly NDVI/POWER cross-source anomaly correlations are restricted to the core period overlap; exploratory association only, not validation or causation.
- Outputs: JSON, CSV, GeoJSON, SVG charts, and a self-contained offline HTML report with clickable spatial trend grid.
- `HACKATHON_PITCH.md` contains the project brief, challenge alignment, methods, safeguards and next upgrades.

## Important modules

- `science_core/pipeline.py`, `principles.py`: six-stage orchestration.
- `analysis.py`: NASA POWER validation and descriptive summaries.
- `statistical_analysis.py`: annual/monthly/seasonal POWER summaries, descriptive OLS and correlations.
- `trend_analysis.py`: Mann-Kendall and Sen slope.
- `change_point.py`: Pettitt single change-point test.
- `anomaly_analysis.py`: robust MAD anomaly screening.
- `spatial_analysis.py`: annual per-pixel NDVI medians, coverage-based core period selection, fixed-panel annual summaries, per-pixel trends and BY q-values.
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
- Status at handoff: in progress.
- This run uses coverage-based 2003-2023 core period selection, fixed-panel annual NDVI, minimum 3 valid composites per pixel-year, cross-source analysis restricted to the core period, and the generated offline HTML report.
- Do not claim the final integrated report is complete until this run succeeds and its artifact/report.html are inspected.

## Offline tests

- Latest core implementation test run #62: success, 59 tests passed.
- Subsequent changes after #62 are mainly report text and project documentation; check newest test runs if needed.
- Live NASA data workflow is manual-only now to conserve GitHub Actions quota. Offline tests still run on pushes.

## Scientific caveats

- NASA POWER is a gridded estimate, not a local weather-station record.
- MOD13Q1 NDVI is a vegetation index, not temperature or precipitation.
- NDVI and POWER have different spatial support.
- Monthly correlations do not establish causation or validate either source.
- Mann-Kendall and Pettitt p-values are not adjusted for temporal autocorrelation. BY q-values are therefore exploratory.
- The spatial subset is a local sample, not a region-wide census.
- Planetary Computer STAC collection license metadata must be followed; do not assume the hosted collection is public-domain simply because the source product is NASA.

## Immediate next steps

1. Monitor run #21 and inspect logs/artifact.
2. Confirm report.json records core trend period 2003-2023, monthly coverage counts, 2024-2025 partial coverage, fixed-panel pixel count and cross-source period.
3. Inspect `report.html` offline: verify clickable pixel grid, charts, core period, q-value caveat and source links.
4. Review annual CSV, per-pixel trend CSV, GeoJSON, coverage chart and cross-source CSV.
5. If run #21 succeeds, prepare the final hackathon submission text and a short demo workflow. Avoid further live runs unless a material scientific change is needed.
6. Next scientific upgrade, if time allows: temporal-autocorrelation-aware trend inference. A direct precipitation cross-check with GPM IMERG is a later extension; the currently discovered Planetary Computer GPM HHR collection only covers through 2021 and does not provide enough recent overlap for the current POWER period.

## Work constraints

Work only on this NASA project until the hackathon begins on 2026-11-14. Unrelated project automations have been paused. NASA-only daytime work automation is scheduled for 2026-11-08 through 2026-11-13, Asia/Dushanbe.
