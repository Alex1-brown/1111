# Earth System Trend Detective Engine

A reproducible, evidence-first workflow combining NASA POWER climate observations with quality-screened NASA MODIS/Terra NDVI to analyze environmental trends, spatial patterns, coverage, and uncertainty for a local study area in Tajikistan.

## Windows desktop launch

For Windows 10/11, download and extract the repository ZIP, install Python 3.12 or newer, and double-click `START_HERE_WINDOWS.bat`. The first run creates an isolated `.venv` and installs dependencies; later runs reuse them. The Russian desktop interface accepts coordinates, selects an output folder, shows collection progress, and opens the generated offline HTML report. It runs the same `science_core.cli` pipeline as the command-line workflow; GIBS browse imagery is skipped by default so the primary analysis uses quantitative MODIS NDVI. See [QUICK_START_RU.md](QUICK_START_RU.md).

## Default live dataset
- NASA POWER daily T2M and PRECTOTCORR data: 2021-01-01 through 2025-12-31.
- NASA GIBS MODIS Terra true-colour imagery: 60 evenly sampled dates over the same period, 512 × 512 pixels.
- The live workflow requires at least 50 valid images. Failed dates are recorded rather than silently replaced; each image request is retried up to three times.
- Adjacent successful images are compared using simple RGB pixel differences. This is an exploratory browse-image comparison, not calibrated remote sensing.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m science_core.cli --image-count 60 --minimum-images 50
```

The CLI writes `artifacts/nasa_power.json`, `artifacts/report.json`, downloaded PNG files under `artifacts/modis_series/`, and (unless `--skip-ndvi` is set) quantitative MODIS NDVI data, annual summaries, and spatial trend GeoJSON under `artifacts/modis_ndvi/`.

## GitHub Actions
The **NASA live data collection** workflow is manual-only (`workflow_dispatch`) to avoid consuming Actions quota on code-only commits. Start it from the Actions tab when a fresh dataset is needed. It uploads the report and quantitative MODIS/POWER outputs as a downloadable artifact for 14 days. The separate Python tests workflow runs offline on code pushes and pull requests.

## Important scientific limitations
- NASA POWER values are gridded analysis/reanalysis-derived estimates, not direct measurements from a local weather station.
- GIBS MODIS true-colour images are browse imagery. RGB changes are not calibrated reflectance, land-cover classification, or proof of environmental change.
- Clouds, atmospheric conditions, illumination, compositing and missing observations can affect image comparisons.
- Five years alone do not establish a long-term climate trend. Any scientific conclusion needs a domain-specific hypothesis, suitable validated data, uncertainty analysis and independent checks.


## Statistical analysis outputs

The live CLI now also produces a descriptive analysis of the actual paired NASA POWER daily records:
- annual mean 2 m air temperature and annual precipitation totals;
- calendar-month climatology and meteorological-season summaries;
- exploratory ordinary-least-squares slopes across annual summaries;
- paired daily Pearson correlation between temperature and precipitation;
- CSV exports: `annual_summary.csv`, `monthly_climatology.csv`, and `seasonal_summary.csv`.

These are descriptive results for the selected five-year period, not proof of long-term climate change or causation. A temperature–precipitation correlation does not validate either variable.

## Satellite validation status

The current MODIS Terra true-colour GIBS PNGs are browse imagery and cannot be used as calibrated land-surface temperature measurements. A proper satellite comparison requires a quantitative product such as MODIS/Terra MOD11A1.061 daytime/nighttime land-surface temperature, with quality flags and cloud screening, followed by spatial and temporal aggregation. Land-surface temperature is not the same physical quantity as 2 m air temperature, so any comparison must explicitly account for that distinction.


## Non-parametric trend analysis

The analytical core calculates Mann–Kendall scores, Sen slopes and Seasonal Mann–Kendall summaries. The current Hamed–Rao (1998) implementation is retained as a sensitivity diagnostic, not an inferential test: the project-specific Gaussian AR(1) calibration found rejection rates above the nominal 0.05 level in several scenarios. Its p-values and variance-based slope intervals are not used to claim significance.

A separate calibration of the repository's residual circular moving-block bootstrap also failed: empirical null rejection ranged from 1.5% to 26.0%, and nominal 95% Sen-interval coverage ranged from 60.5% to 93.0% across the tested AR(1) scenarios. Its p-values, BY-transformed q-values and percentile intervals are sensitivity diagnostics only. See [SERIAL_CORRELATION_AUDIT.md](SERIAL_CORRELATION_AUDIT.md) and [BLOCK_BOOTSTRAP_AUDIT.md](BLOCK_BOOTSTRAP_AUDIT.md).

Short 3–8 point series may receive an exact permutation p-value only under an iid/exchangeability assumption; this does not correct serial dependence. The current five-year NASA POWER window is exploratory. For nonconstant spatial NDVI series, inferential p-values and q-values are withheld. Sen slopes remain descriptive effect-size estimates. A BY adjustment is not run on uncalibrated p-values.

 
## Spatial trend statistics

The spatial analysis module supports per-pixel annual NDVI medians, Sen slopes, coverage diagnostics and dependence-sensitivity metadata. Because the current Hamed–Rao and residual block-bootstrap implementations failed the project's AR(1) calibration checks, nonconstant pixel p-values and BY q-values are withheld. The live pipeline reads pixel coordinates from the COG affine transform and CRS, then transforms pixel centers to EPSG:4326.


## Quantitative satellite vegetation analysis

The live CLI now retrieves NASA MODIS/Terra MOD13Q1.061 NDVI and pixel-reliability COGs through the public Microsoft Planetary Computer STAC API. It uses the official collection ID, public container-scoped SAS token for the COG storage container, and the source COG affine transform/CRS for pixel geolocation. It selects the available 16-day composites for the requested period, retains the raw NDVI and QA values, applies the 0.0001 NDVI scale factor, and accepts only pixel-reliability code 0 for the analysis. It aggregates valid composites to annual per-pixel medians, calculates descriptive Sen slopes and diagnostic Mann–Kendall statistics, and exports pixel trend points as GeoJSON plus CSV summaries. Spatial p/q inference and BY correction for nonconstant pixels are withheld pending a calibrated dependence-aware test.

Default NDVI period: 2001-01-01 through 2025-12-31; local subset radius: 2 km around the POWER reference coordinate (approximately 4 × 4 km). The live data source is the explicit MOD13Q1.061 STAC collection; item IDs are checked for collection 061. COG pixel windows are read using HTTP range requests and a container-scoped Planetary Computer SAS token. The report records collection ID, tile IDs, COG grid CRS/transform and quality policy. Trend inference automatically selects the longest contiguous interval with at least 11 monthly composites per year; the current tile's robust core period is 2003-2023, while 2024-2025 are incomplete and are excluded from long-term trend tests.

Licensing note: the Planetary Computer STAC collection declares its license as proprietary, while listing NASA LP DAAC as producer/licensor/processor. Before redistributing source assets, follow the collection's current license metadata, NASA LP DAAC citation guidance and Planetary Computer data-license terms.

Important limits: NDVI is a vegetation indicator, not a direct measurement of climate or air temperature. Annual aggregation suppresses seasonality. Both current dependence-aware trend tests failed project-specific AR(1) calibration; their p-values and intervals are diagnostic only. Pettitt change-point p-values remain unadjusted for serial dependence. No nonconstant spatial p/q significance claims are currently made.


## SVG visualization layer

The CLI exports labelled SVG line charts for annual temperature, precipitation, NDVI and NDVI spatial coverage under `artifacts/charts/`, plus a self-contained offline `artifacts/report.html` with a clickable trend grid and cross-source correlation summary.


## Cross-source monthly comparison

A separate analysis module aligns monthly MODIS NDVI with NASA POWER 2 m air temperature and corrected precipitation over the full calendar-year overlap of the two source observation windows. This period is independent of the stricter MODIS annual-trend core period: an incomplete edge year is excluded from long-term annual trend inference, but its individually matched months can still contribute to exploratory cross-source analysis. The module calculates month-of-year anomalies, exploratory Pearson/Spearman associations, previous-month precipitation associations, and correlations after removing a linear time component. This is a comparison of related environmental indicators, not a direct validation: NDVI is a local 4 km sample median while POWER is a gridded point estimate. Autocorrelation, confounding and causation are not resolved.


The default live validation workflow skips NASA GIBS true-colour browse imagery because it is not calibrated science data and its repeated image requests add latency without improving the quantitative trend analysis. GIBS remains available as an optional exploratory layer when running the CLI without `--skip-gibs`. The core live run prioritizes quality-screened MOD13Q1 NDVI, NASA POWER time series, cross-source monthly analysis, spatial trend GeoJSON, CSV, JSON and SVG charts.


## Primary sources and specifications

- NASA Space Apps 2026 challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/
- NASA MODIS/Terra MOD13Q1 Version 6.1 product and citation: https://doi.org/10.5067/MODIS/MOD13Q1.061
- Microsoft Planetary Computer MODIS 13Q1 Collection 061: https://planetarycomputer.microsoft.com/api/stac/v1/collections/modis-13Q1-061
- Microsoft Planetary Computer SAS token documentation: https://planetarycomputer.microsoft.com/docs/concepts/sas/
- Microsoft Planetary Computer data-license guidance: https://planetarycomputer.microsoft.com/docs/overview/about/#data-licenses
- NASA POWER Daily API documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- Hamed, K. H. & Rao, A. R. (1998), A modified Mann-Kendall trend test for autocorrelated data, Journal of Hydrology 204, 182–196. https://doi.org/10.1016/S0022-1694(97)00125-X
- Collaud Coen et al. (2020), Effects of the prewhitening method, the time granularity, and the time segmentation on the Mann–Kendall trend detection and the associated Sen's slope. https://doi.org/10.5194/amt-13-6945-2020

The project records product version, source, DOI, units, QA policy and analysis settings in its generated report. If a source response does not match the expected product version or schema, the pipeline fails that data stage rather than silently mixing incompatible records.

## Competition submission and AI-use disclosure

See [SUBMISSION_BRIEF.md](SUBMISSION_BRIEF.md) for the challenge alignment, data sources, methods, limitations, reproducibility instructions, and AI-use disclosure. AI tools assisted with software implementation, review, and documentation; NASA observations are retrieved from the cited providers and are not AI-generated. No NASA branding or insignia is AI-generated or modified.

## Data attribution and licensing

See [DATA_AND_SOFTWARE_LICENSES.md](DATA_AND_SOFTWARE_LICENSES.md) for NASA data citations, source reuse notes, software licensing, and AI-use disclosure. The project code is MIT-licensed; NASA data must retain the source-specific citations and reuse terms.

## Statistical robustness check

After downloading and extracting a live-data artifact, run `python -m science_core.bootstrap_validation artifacts` only as a sensitivity analysis. Its p-values, BY transforms and percentile intervals are not calibrated for inference. See [BLOCK_BOOTSTRAP_AUDIT.md](BLOCK_BOOTSTRAP_AUDIT.md) for the reproducible AR(1) calibration and [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for historical results and limitations.

## Independent Landsat cross-check

The validation workflow also compares summer Landsat 8/9 Collection 2 Level-2 NDVI with the nearest quality-screened MOD13Q1 composite in the same Dushanbe window. Landsat pixels are screened with QA_PIXEL, QA_RADSAT, and SR_QA_AEROSOL (including high-aerosol rejection); sensor-date pairs more than 24 days apart are rejected. Run `python -m science_core.landsat_validation artifacts` after extracting the NASA artifact. The current QA-v3 result has nine usable years; its nominal iid p-values and intervals do not correct for temporal autocorrelation. The block-bootstrap method is not used for inference. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for methods, results, and limitations.


## GPM IMERG Final Daily adapter (credential-gated)

The repository now includes a local NetCDF ingestion adapter for NASA GPM IMERG Final Daily V07 (`GPM_3IMERGDF`). It validates the `precipitation` variable in mm/day, the `precipitation_cnt` half-hour completeness count, optional `randomError`, coordinate-grid consistency, UTC dates, source metadata, and SHA-256 provenance. It normalizes NetCDF dimension order and exports per-pixel annual coverage. Annual totals are emitted only when every calendar day is valid; incomplete years are not extrapolated.

Run `python -m science_core.gpm_imerg --status` to check whether Earthdata credentials appear to be configured. This is a presence check, not authentication. The adapter does not bypass Earthdata Login and does not download remote granules; use the GES DISC subset interface to obtain local spatial/temporal NetCDF files, then run `python -m science_core.gpm_imerg --input-dir path/to/gpm_subset`. See [GPM_IMERG.md](GPM_IMERG.md). **No GPM observations or GPM trend results are currently included in the project.**
