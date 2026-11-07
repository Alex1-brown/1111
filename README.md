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
