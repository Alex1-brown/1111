# Project state and handoff

Last updated: 2026-11-13
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
- Per-pixel Sen slopes are descriptive effect-size estimates. Hamed–Rao variance-based intervals and p-values are nominal sensitivity diagnostics only; their calibration is not established.
- The fixed-seed AR(1) calibration showed non-nominal rejection rates under several zero-trend null scenarios. Nonconstant Hamed–Rao p-values are therefore withheld from spatial inference; iid p-values remain reference-only, and nonconstant pixel p/q fields are null until a calibrated method is established.
- The 2026-11-13 residual moving-block bootstrap calibration (n=20/60, phi=-0.4/0/+0.4/+0.7, block lengths 2/3/4; 200 outer × 399 inner replicates) found null rejection rates of 1.5–26.0% and nominal 95% Sen-interval coverage of 60.5–93.0%. Its p-values, BY transforms and intervals are sensitivity-only; BY cannot repair uncalibrated p-values. Nonconstant spatial p/q inference remains withheld.
- Annual aggregate NDVI uses a fixed set of pixels present in every year of the core period, preventing changing spatial coverage from driving the overall trend.
- Pettitt change-point screening and robust MAD anomaly screening for annual series.
- Monthly NDVI/POWER cross-source anomaly correlations are restricted to the core period overlap; exploratory association only, not validation or causation.
- Independent Landsat 8/9 Collection 2 Level-2 cross-sensor check was rerun on 2026-11-11 with QA policy v3 and existing NASA artifact #22. Nine of eleven selected years passed; 2015 and 2016 retained only 225 and 3 pixels. All nine successful windows had full raster coverage. Landsat n=9: Sen slope −0.00279 NDVI/year, nominal iid p=0.0763, nominal 95% CI [−0.00655, +0.00014]. Matched MODIS n=9: slope −0.00361, nominal iid p=0.2515, CI [−0.00561, +0.00270]. Neither trend is significant at 0.05; Hamed–Rao and block bootstrap were not applied because n<10. The p-values/intervals do not correct temporal autocorrelation. This is a consistency check, not independent confirmation or ground truth.
- Outputs: JSON, CSV, GeoJSON, SVG charts, and a self-contained offline HTML report with clickable spatial trend grid.
- `HACKATHON_PITCH.md` contains the project brief, challenge alignment, methods, safeguards and next upgrades.

## Important modules

- `science_core/pipeline.py`, `principles.py`: six-stage orchestration.
- `analysis.py`: NASA POWER validation and descriptive summaries.
- `statistical_analysis.py`: annual/monthly/seasonal POWER summaries, descriptive OLS and correlations.
- `trend_analysis.py`: Mann–Kendall, Sen slope, nominal Sen intervals and Hamed–Rao modified variance diagnostics for eligible regular series.
- `block_bootstrap_benchmark.py`: reproducible AR(1) type-I-error and Sen-interval coverage benchmark for the existing residual moving-block bootstrap.
- `change_point.py`: Pettitt single change-point test.
- `anomaly_analysis.py`: robust MAD anomaly screening.
- `spatial_analysis.py`: annual per-pixel NDVI medians, coverage-based core period selection, fixed-panel annual summaries, per-pixel Sen slopes, Hamed–Rao sensitivity diagnostics and a conservative inference gate.
- `planetary_modis.py`: STAC search, monthly sampling, COG signing/window reads and quality screening.
- `landsat_validation.py`: Landsat 8/9 C2 L2 NDVI cross-check with QA v3, full-window coverage checks, per-flag QA counts (including rejected low-valid-pixel scenes), paired MODIS comparisons and trend-direction diagnostics.
- `gpm_imerg.py`: credential-aware local GPM IMERG Final Daily V07 NetCDF reader, dimension/grid/version/unit checks, half-hour-count QC, SHA-256 provenance, and strict annual per-pixel coverage summaries. No GPM data have yet been downloaded or analyzed.
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

- Latest GPM-adapter main-branch run #43176506577 passed all 100 tests. The serial-correlation audit PR test run #43179105801 passed all 104 tests.
- Block-bootstrap calibration workflow #43387777284 passed all 106 offline unit tests and completed the 24-scenario Monte Carlo benchmark; artifact ID 14018714703.
- The ten GPM-specific tests cover missing/present credential detection without secret disclosure, NetCDF dimension-order normalization and provenance, units, half-hour-count QC, duplicate dates, and complete-year aggregation.
- The live NASA data workflow remains manual-only. No new live NASA collection was started for this adapter.

## Scientific caveats

- NASA POWER is a gridded estimate, not a local weather-station record.
- MOD13Q1 NDVI is a vegetation index, not temperature or precipitation.
- NDVI and POWER have different spatial support.
- Monthly correlations do not establish causation or validate either source.
- The current Hamed–Rao implementation failed nominal 5% calibration in several tested Gaussian AR(1) null scenarios. Its p-values are now sensitivity-only and excluded from the spatial BY family for nonconstant pixels. The Sen interval variance approximation is also not independently calibrated.
- The current residual moving-block bootstrap also failed AR(1) calibration: rejection rates were as high as 26%, and nominal 95% Sen-interval coverage was as low as 60.5%. Its p/q values and intervals are diagnostic only. Do not describe old bootstrap BY counts as significant.
- Pettitt p-values remain unadjusted for serial dependence. Five-year POWER annual/seasonal summaries are too short for the Hamed–Rao correction and remain exploratory.
- Spatial BY q-values are currently withheld for nonconstant pixel series because both the current Hamed–Rao and residual moving-block bootstrap p-values failed project-specific AR(1) calibration. A q-value adjustment cannot repair miscalibrated input p-values.
- The spatial subset is a local sample, not a region-wide census.
- Planetary Computer STAC collection license metadata must be followed; do not assume the hosted collection is public-domain simply because the source product is NASA.

## Serial-correlation calibration audit (2026-11-12)

- The benchmark module ran 2,000 replicates for each of ten stationary Gaussian AR(1) null scenarios (n=20/60; phi=-0.7,-0.4,0,+0.4,+0.7). White-noise false-positive rates for the current reported p-value were 7.75% and 9.00%, with 95% Wilson intervals excluding 5%; several other scenarios were also materially above nominal.
- Based on that result, Hamed–Rao p-values are retained only as sensitivity diagnostics. Nonconstant pixel p-values and BY q-values are withheld pending a calibrated method; the HTML report and CSV now distinguish sensitivity p-values from inferential p-values.
- The block-bootstrap validator now selects temporally eligible pixels independently of the Hamed–Rao inferential gate and reports short/gapped exclusions explicitly.
- Benchmark artifact: https://github.com/Alex1-brown/1111/actions/runs/43179095375/artifacts/13925202462. This is statistical method testing, not satellite-data simulation.
- Moving-block bootstrap audit: https://github.com/Alex1-brown/1111/actions/runs/43387777284; artifact 14018714703; detailed interpretation in BLOCK_BOOTSTRAP_AUDIT.md. This is statistical method testing, not satellite-data simulation.

## Immediate next steps

1. Run `python -m science_core.gpm_imerg --status` in the user's data environment; if credentials are available, obtain a spatially subsetted GPM_3IMERGDF V07 NetCDF through authenticated GES DISC access. Compare GPM and POWER only over matched UTC periods and after accounting for their different spatial support; call this a cross-source consistency check, not ground-truth validation.
2. Do not restore nonconstant spatial p/q inference until an alternative method passes independent type-I-error and interval-coverage calibration across null, trend, autocorrelation and missingness scenarios. The current residual moving-block bootstrap is sensitivity-only.
3. Examine alternative Landsat summer scenes for 2015/2016 without relaxing the high-aerosol or pixel-quality screens.
4. Add a sensitivity comparison for optional interpolated-aerosol exclusion, reporting coverage and trend eligibility.
5. Prepare a reproducible challenge demo and final submission. Do not rerun NASA live data collection unless a material scientific change requires it.

## Work constraints

Work only on this NASA project until the hackathon begins on 2026-11-14. Unrelated project automations have been paused. The final scheduled development run is 2026-11-13; no further planned runs occur after this date.
