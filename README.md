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

The CLI writes `artifacts/nasa_power.json`, `artifacts/report.json`, and the downloaded PNG files under `artifacts/modis_series/`.

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
