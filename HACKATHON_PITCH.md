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
- **USGS Landsat 8/9 Collection 2 Level-2 Surface Reflectance** — 30 m red/NIR reflectance and QA bands, used as a cross-sensor consistency check for the overlapping 2013–2023 period.
- **NASA GPM IMERG Final Daily V07 adapter** — local NetCDF ingestion for daily precipitation in mm/day, valid half-hour sample counts, random-error metadata, and strict complete-year aggregation. This adapter is implemented but has not yet processed GPM observations; it is not presented as a completed validation.

The current demonstration samples a 17 × 17 MODIS pixel window around the selected location. One 16-day composite is selected per calendar month, nearest to mid-month. Only pixel-reliability code 0 is accepted. An annual pixel median requires at least three quality-screened monthly composites.

## How the analysis works

1. Validate source metadata, units, dates, coordinate reference systems, missing values and product version.
2. Screen MODIS pixels using the official pixel-reliability layer.
3. Select the longest continuous MODIS period with at least 11 monthly composites in every year. For the current location and collection snapshot, this produces a core trend period of **2003–2023**. The 2001–2002 and 2024–2025 coverage is incomplete and is not used for long-term trend inference.
4. Calculate annual per-pixel NDVI medians and descriptive Sen slopes.
5. Compute dependence diagnostics, but withhold nonconstant pixel p-values and spatial q-values: the current Hamed–Rao and residual moving-block bootstrap implementations failed the project's AR(1) calibration checks. BY correction is not applied to uncalibrated p-values.
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
- **How well supported?** — reports coverage, QA filters, descriptive Sen slopes and explicit uncertainty limits. Inferential p/q claims for nonconstant spatial pixels are withheld because both current dependence-aware methods failed AR(1) calibration. The QA-v3 Landsat comparison has nine usable years; its nominal iid normal-approximation p-value is 0.076 and its interval crosses zero. Neither statistic corrects temporal autocorrelation, so it does not independently confirm a significant MODIS trend.

It also makes incomplete coverage visible. Years with insufficient monthly observations are excluded from trend inference rather than being silently treated as complete.

## Scientific safeguards and current limits

- NASA POWER gridded values are not local weather-station measurements.
- NDVI measures vegetation greenness; it is not air temperature or precipitation.
- MODIS NDVI and NASA POWER have different spatial supports.
- Correlation does not establish causation or validate either source.
- The current Hamed–Rao and residual moving-block bootstrap implementations failed project-specific AR(1) calibration; their p/q values and intervals are sensitivity diagnostics only. The five-year POWER window and Pettitt change-point p-values remain unadjusted for serial dependence.
- Spatial BY q-values are withheld for nonconstant pixels. A multiple-testing adjustment cannot repair uncalibrated input p-values.
- The current spatial window is a local sample, not a region-wide census.
- GPM IMERG has not yet been downloaded or analyzed. Its 0.1° grid is much coarser than MODIS NDVI, and mountainous terrain plus changing satellite constellation can affect precipitation estimates.
- The Landsat cross-sensor comparison is a consistency check, not ground truth. Two of eleven selected years failed the valid-pixel threshold; n = 9 is too short for the configured Hamed–Rao correction, and the resulting nominal trend test is not significant.
- The Planetary Computer STAC collection has its own license metadata; source redistribution must follow the current collection terms and NASA LP DAAC citation guidance.

## Next scientific upgrades

1. Improve Landsat annual coverage by examining alternative summer scenes for the two failed years while preserving the documented high-aerosol and pixel-quality screens.
2. Develop and independently calibrate an alternative dependence-aware trend test and Sen-slope interval; do not restore p/q inference until type-I error and interval coverage are acceptable across null and trend scenarios.
3. Obtain a spatially subsetted GPM IMERG Final Daily V07 NetCDF through authenticated GES DISC access, then compare its precipitation series with NASA POWER as a cross-source consistency check (not ground-truth validation).
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
