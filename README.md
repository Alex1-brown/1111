# NASA data pipeline

A small, reproducible Python workflow for retrieving public NASA POWER daily point data and NASA GIBS MODIS Terra true-colour browse imagery for the Yavan/Dushanbe region of Tajikistan.

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
The **NASA live data collection** workflow runs when its workflow file is first added to `main`, and can later be started manually from the Actions tab. It uploads the report and imagery as a downloadable artifact for 14 days. The separate Python tests workflow remains an offline unit-test job.

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

The report now supplements descriptive OLS slopes with Mann-Kendall trend statistics and Sen's median slope for annual temperature and annual precipitation, plus Seasonal Mann-Kendall statistics on year-month aggregates (monthly means for temperature and monthly totals for precipitation). The output includes Kendall S, Kendall tau, Z, two-sided p-value, Sen slope per year and method metadata.

For annual series with 3–8 observations, the implementation uses an exact permutation p-value; larger annual series and seasonal tests use a two-sided normal approximation. Neither currently corrects for serial correlation. Five annual observations provide weak evidence, and seasonal tests need dependence diagnostics and a longer record before strong inference. Spatial multiple-testing correction is not yet implemented.

 
## Spatial trend statistics

The spatial analysis module supports per-pixel annual NDVI medians, per-pixel Mann-Kendall/Sen trend estimates, and Benjamini-Yekutieli adjusted q-values across pixels. BY is used as a conservative false-discovery-rate procedure under arbitrary dependence. The module also contains an explicitly approximate MODIS sinusoidal row/column geolocation helper; its center-pixel convention must be verified against each source response before map coordinates are treated as precise. This module is a tested analysis layer; the live MODIS ingestion adapter and full spatial map pipeline are separate pending work.


## Quantitative satellite vegetation analysis

The live CLI now retrieves MODIS/Terra MOD13Q1 NDVI and pixel-reliability data through the ORNL DAAC TESViS public subset API. It downloads 16-day composites in batches of ten dates, retains the raw NDVI and QA values, applies the 0.0001 NDVI scale factor, and accepts only pixel-reliability code 0 for the analysis. It aggregates valid composites to annual per-pixel medians, calculates Mann-Kendall/Sen trends, applies Benjamini-Yekutieli spatial multiple-testing correction, and exports pixel trend points as GeoJSON plus CSV summaries.

Default NDVI period: 2001-01-01 through 2025-12-31; local subset radius: 2 km around the POWER reference coordinate (approximately 4 × 4 km). The ORNL DAAC service documents a maximum of ten composite dates per subset request. The exact product version returned by the API is recorded in the report.

Important limits: NDVI is a vegetation indicator, not a direct measurement of climate or air temperature. Annual aggregation suppresses seasonality. Temporal autocorrelation is not yet corrected in the Mann-Kendall p-values, and the approximate pixel geolocation must be checked against source metadata before high-precision mapping. A spatially significant trend is not automatically a causal explanation.


## SVG visualization layer

The CLI exports labelled SVG line charts for annual temperature, precipitation and MODIS NDVI under `artifacts/charts/`.


## Cross-source monthly comparison

A separate analysis module aligns monthly MODIS NDVI with NASA POWER 2 m air temperature and corrected precipitation over their common years. It calculates month-of-year anomalies, exploratory Pearson/Spearman associations, previous-month precipitation associations, and correlations after removing a linear time component. This is a comparison of related environmental indicators, not a direct validation: NDVI is a local 4 km sample median while POWER is a gridded point estimate. Autocorrelation, confounding and causation are not resolved.
