# Hackathon project brief — Earth System Trend Detective Engine

## One-sentence description

A reproducible, evidence-first workflow that detects where Earth-system indicators change, estimates how much they change, checks whether patterns are statistically supported, and exposes data-quality limitations instead of hiding them.

## Problem

Open Earth-observation and climate datasets are powerful but difficult to compare responsibly. A chart can make a noisy, incomplete, or spatially inconsistent dataset look convincing. Analysts need a repeatable way to screen data quality, align observations, distinguish real signals from coverage artifacts, and communicate uncertainty.

## Solution

The project combines NASA gridded climate data and NASA satellite vegetation observations in a modular workflow:

**Acquire → Validate → Clean → Process → Verify → Visualize**

The pipeline is deliberately modular: the workflow is reusable, while scientific calculations remain specific to each variable and dataset. It does not claim one mathematical formula can correctly analyze every kind of information.

## NASA data used

- **NASA POWER Daily** — 2 m air temperature (T2M) and corrected precipitation (PRECTOTCORR), daily point extraction.
- **NASA MODIS/Terra MOD13Q1.061** — 250 m, 16-day NDVI and pixel-reliability data, accessed as cloud-optimized GeoTIFFs through the Microsoft Planetary Computer STAC collection.
- **USGS Landsat 8/9 Collection 2 Level-2 Surface Reflectance** — 30 m red/NIR reflectance and QA bands, used as an independent cross-sensor consistency check for the overlapping 2013–2023 period.

The current demonstration samples a 17 × 17 MODIS pixel window around the selected location. One 16-day composite is selected per calendar month, nearest to mid-month. Only pixel-reliability code 0 is accepted. An annual pixel median requires at least three quality-screened monthly composites.

## How the analysis works

1. Validate source metadata, units, dates, coordinate reference systems, missing values and product version.
2. Screen MODIS pixels using the official pixel-reliability layer.
3. Select the longest continuous MODIS period with at least 11 monthly composites in every year. For the current location and collection snapshot, this produces a core trend period of **2003–2023**. The 2001–2002 and 2024–2025 coverage is incomplete and is not used for long-term trend inference.
4. Calculate annual per-pixel NDVI medians, then estimate per-pixel Sen slopes and Mann–Kendall trends.
5. Apply the Hamed–Rao (1998) modified Mann–Kendall variance correction to per-pixel annual series with at least ten equally spaced observations and estimable detrended-rank autocorrelation. Apply Benjamini–Yekutieli correction only across temporally eligible pixel tests; ineligible pixels keep descriptive slopes but no adjusted p-value or q-value.
6. Build an annual aggregate from a fixed set of pixels present in every year of the core period, reducing bias from changing spatial coverage.
7. Apply Pettitt change-point screening and robust median-absolute-deviation anomaly screening to annual series.
8. Align monthly NDVI with NASA POWER temperature and precipitation anomalies over their common, adequately covered period. Correlations are exploratory associations, not causal evidence or direct validation of the climate product.

## What the user receives

- A self-contained offline HTML report with a clickable spatial trend grid.
- SVG charts for annual NDVI, spatial coverage, temperature and precipitation.
- CSV tables for annual, monthly, seasonal and per-pixel results.
- GeoJSON trend features that can be opened in GIS software.
- A JSON report recording sources, parameters, results and scientific limitations.

## Why it is useful

The system answers the central trend-detection questions:

- **What changed?** — identifies the indicator and detected pattern.
- **Where?** — maps the spatial distribution of per-pixel trends.
- **How much?** — estimates change rates with Sen's slope.
- **How well supported?** — reports p-values, spatial q-values, coverage, quality filters and limitations. The QA-v3 Landsat comparison currently has nine usable years; its negative Sen slope is not significant (p = 0.076, nominal 95% CI crosses zero), so it does not independently confirm the MODIS trend.

It also makes incomplete coverage visible. Years with insufficient monthly observations are excluded from trend inference rather than being silently treated as complete.

## Scientific safeguards and current limits

- NASA POWER gridded values are not local weather-station measurements.
- NDVI measures vegetation greenness; it is not air temperature or precipitation.
- MODIS NDVI and NASA POWER have different spatial supports.
- Correlation does not establish causation or validate either source.
- Hamed–Rao correction is approximate and is not attempted for short, irregular or unestimable series. The five-year POWER window and Pettitt change-point p-values remain unadjusted for serial dependence.
- Spatial BY q-values apply only to the eligible pixel family; they are not causal evidence and do not prove that all dependence has been removed.
- The current spatial window is a local sample, not a region-wide census.
- The Landsat cross-sensor comparison is a consistency check, not ground truth. Two of eleven selected years failed the valid-pixel threshold; n = 9 is too short for the configured Hamed–Rao correction, and the resulting nominal trend test is not significant.
- The Planetary Computer STAC collection has its own license metadata; source redistribution must follow the current collection terms and NASA LP DAAC citation guidance.

## Next scientific upgrades

1. Improve Landsat annual coverage by examining alternative summer scenes for the two failed years while preserving the documented high-aerosol and pixel-quality screens.
2. Benchmark the Hamed–Rao implementation against controlled AR(1) simulations and an independent reference implementation; assess sensitivity to lag selection and missing years.
3. Add an independent precipitation dataset such as GPM IMERG for a more direct precipitation cross-check.
4. Add quality-screened MODIS land-surface temperature, clearly distinguished from 2 m air temperature.
5. Expand from a local pixel window to a regional grid and evaluate sensitivity to spatial scale.
6. Add a benchmark suite using synthetic series with known trends, change points, missingness and autocorrelation.

## Primary references

- NASA POWER: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NASA MOD13Q1.061 DOI: https://doi.org/10.5067/MODIS/MOD13Q1.061
- Planetary Computer MODIS 13Q1 collection: https://planetarycomputer.microsoft.com/api/stac/v1/collections/modis-13Q1-061
- NASA Space Apps challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/
- Hamed & Rao (1998), modified Mann–Kendall test: https://doi.org/10.1016/S0022-1694(97)00125-X
- Collaud Coen et al. (2020), sensitivity of Mann–Kendall/Sen methods to autocorrelation and time granularity: https://doi.org/10.5194/amt-13-6945-2020
