# Independent statistical sensitivity check

**Dataset run:** [NASA live data collection #22](https://github.com/Alex1-brown/1111/actions/runs/42662224195)  
**Code snapshot:** `3bb97306227867aef2781eb49a0b36574da46e2f`  
**Study area:** Dushanbe, Tajikistan — 38.5598° N, 68.7870° E  
**Trend interval:** 2003–2023

## Primary MODIS result

The live pipeline retrieved 515 available Terra MOD13Q1.061 STAC items and selected 272 monthly composites. Across a 17 × 17 local pixel window it produced 78,608 raw pixel observations; 43,891 passed the strict pixel-reliability code-0 filter (55.8%). A fixed 231-pixel panel was available for every year from 2003 through 2023.

Of 261 pixels with Sen-slope estimates, 233 met the temporal eligibility rules for the Hamed–Rao test and spatial Benjamini–Yekutieli family. **136 of those 233 pixels passed BY q ≤ 0.05; 135 had negative Sen slopes and one had a positive slope.** The other 28 trend estimates were excluded from adjusted spatial inference rather than being assigned an adjusted p-value.

For the fixed-panel median series, Sen slope was **−0.0026409 NDVI units/year**, Kendall tau was **−0.662**, and the Hamed–Rao Mann–Kendall p-value was **3.06 × 10⁻⁵**. The variance factor was 1.0 and no detrended-rank ACF lag crossed the configured significance threshold. Pettitt's test placed a possible change point in 2013 (p = 0.0107), but that p-value is not adjusted for temporal autocorrelation.

The fixed-panel median NDVI moved from 0.2734 in 2003 to 0.20615 in 2023, a **24.6% decrease** relative to the 2003 value. This is a local vegetation-index result, not proof of a specific cause or a national trend for Tajikistan.

## Moving-block bootstrap sensitivity analysis

To check whether the spatial result depended entirely on the Hamed–Rao variance approximation, a separate offline sensitivity analysis was run on the same 233 temporally eligible pixel series:

- Sen-detrend each annual pixel series.
- Resample circular blocks of residuals, preserving short-range dependence within each block.
- Compare the absolute bootstrap Mann–Kendall S statistics with the observed absolute S.
- Use 5,000 replicates per pixel and block lengths of 2, 3, and 4 years.
- Apply Benjamini–Yekutieli correction separately within each block-length family.

| Inference family | Pixels with BY q ≤ 0.05 |
|---|---:|
| Primary Hamed–Rao | 136 |
| Moving blocks, 2 years | 137 |
| Moving blocks, 3 years | 141 |
| Moving blocks, 4 years | 146 |
| Bootstrap significant at all three block lengths | **132** |

The 3-year bootstrap family shared 127 significant pixels with the Hamed–Rao family. Across all three bootstrap block lengths, 132 pixels remained significant; 127 of those also passed the primary Hamed–Rao analysis (93.4% of the primary significant set). Of the 132 bootstrap-robust pixels, 131 had negative slopes and one had a positive slope. This agreement is a useful robustness signal, although it does not prove that either method is perfectly calibrated.

For the fixed-panel aggregate series, a 5,000-replicate residual moving-block bootstrap produced zero null S statistics as extreme as observed for each block length. The plus-one empirical p-value was therefore 1/5,001 (approximately 0.00020). The bootstrap 95% Sen-slope intervals also excluded zero:

| Block length | Bootstrap 95% Sen-slope interval (NDVI/year) |
|---|---|
| 2 years | [−0.003445, −0.001845] |
| 3 years | [−0.003342, −0.001916] |
| 4 years | [−0.003303, −0.001953] |

## Meteorological context

NASA POWER contributed 1,826 paired daily records for 2021–2025. The five annual values did **not** establish a significant temperature or precipitation trend (annual Mann–Kendall p = 1.00 for temperature and p = 0.483 for precipitation). The monthly NDVI–temperature anomaly correlation was positive (Pearson r = 0.508 across 36 common months), but it is exploratory only: the spatial supports differ, serial dependence is not removed, and correlation does not establish causation. No warming or precipitation-causation claim is made from this short interval.

## Reproduction

After extracting the NASA Actions artifact. The current sensitivity run is [GitHub Actions validation #25](https://github.com/Alex1-brown/1111/actions/runs/42665439281):

```bash
python -m pip install -r requirements.txt
python -m science_core.bootstrap_validation artifacts --spatial-replicates 5000 --fixed-panel-replicates 5000 --block-lengths 2,3,4
```

The script writes `ndvi_block_bootstrap_validation.csv` and `ndvi_block_bootstrap_validation.json` under `artifacts/modis_ndvi/`.


## Independent cross-sensor check: Landsat 8/9

**Quality-screening update:** the numerical Landsat results below come from the first live run, which applied QA_PIXEL and QA_RADSAT but did not yet screen the separate SR_QA_AEROSOL band. A code review against the USGS QA specification identified that omission. The current validation branch now also rejects aerosol-QA fill pixels and pixels with the high-aerosol level (bits 6–7 = 3). The stricter code has passed its offline unit tests, but the live Landsat workflow has not yet been rerun with this additional mask. Therefore, the Landsat counts, trend statistics, and cross-sensor correlations below are **provisional pre-aerosol-screen results**, not the final strict-QA result.

A separate 2013–2023 comparison used USGS Landsat 8/9 Collection 2 Level-2 Surface Reflectance in the same 4 km × 4 km window. The Planetary Computer STAC search returned 997 candidate items. One summer scene per year, nearest to July 15 within June 1–September 30 and with scene cloud cover no greater than 40%, was selected. All 11 years were represented and no selected scene failed pixel-quality checks.

Landsat surface reflectance was converted using the USGS Collection 2 scale factor 0.0000275 and offset −0.2. QA_PIXEL fill, dilated-cloud, cirrus, cloud, cloud-shadow, and snow flags were excluded; pixels with any QA_RADSAT flag were also excluded. Each scene retained 17,681–17,689 clear pixels in the 17,689-pixel local window.

The Landsat summer median NDVI declined from 0.25462 in 2013 to 0.21289 in 2023 (−16.4%). Its Sen slope was **−0.004024 NDVI/year**, Kendall tau was **−0.60**, and Hamed–Rao Mann–Kendall p = **0.01273**. The Hamed–Rao variance factor was 1.0 with no detrended-rank ACF lags selected; the p-value is therefore the normal-approximation result without a variance inflation/deflation.

A 5,000-replicate residual circular moving-block bootstrap also supported a negative Landsat trend:

| Block length | Bootstrap p-value | 95% Sen-slope interval (NDVI/year) |
|---|---:|---|
| 2 years | 0.00400 | [−0.005391, −0.002811] |
| 3 years | 0.00060 | [−0.005190, −0.002807] |
| 4 years | 0.00020 | [−0.005084, −0.003115] |

The comparison pairs each Landsat scene with the nearest same-year quality-screened MOD13Q1 composite, rather than pooling all July observations. The measured MODIS-minus-Landsat date offsets were:

| Year | Landsat date | MODIS composite date | MODIS − Landsat (days) |
|---|---|---|---:|
| 2013 | 2013-07-17 | 2013-07-12 | −5 |
| 2014 | 2014-07-11 | 2014-07-12 | +1 |
| 2015 | 2015-07-07 | 2015-07-12 | +5 |
| 2016 | 2016-07-16 | 2016-07-11 | −5 |
| 2017 | 2017-07-19 | 2017-07-12 | −7 |
| 2018 | 2018-07-15 | 2018-07-12 | −3 |
| 2019 | 2019-07-18 | 2019-07-12 | −6 |
| 2020 | 2020-07-04 | 2020-07-11 | +7 |
| 2021 | 2021-07-14 | 2021-07-12 | −2 |
| 2022 | 2022-07-18 | 2022-07-12 | −6 |
| 2023 | 2023-07-13 | 2023-07-12 | −1 |

The absolute temporal mismatch was **1–7 days** for all 11 years. The updated code now records both acquisition dates and the signed offset, and rejects a pair if the nearest same-year MODIS composite is more than 24 days away. With these observed dates, the matched values are the same July composites used in the original calculation: Pearson r = **0.512** and Spearman rho = **0.473**. Both sensors show a negative 2013–2023 direction, but agreement is moderate rather than exact. Their pixel sizes (30 m vs 250 m), spectral responses, compositing, and acquisition dates differ. MODIS is a 16-day composite, so its composite date is not an exact instantaneous observation. This is an independent-sensor consistency check, not a ground-truth validation or proof of cause.

USGS product reference: [Landsat 8–9 OLI/TIRS Collection 2 Level-2 DOI](https://doi.org/10.5066/P9OGBGM6). USGS documents the surface-reflectance scale/offset and states that Landsat products have no restrictions on use when properly cited. See [USGS surface-reflectance guidance](https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-reflectance) and [QA band definitions](https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands).

## Limitations

The residual bootstrap assumes the detrended residual process is sufficiently stationary. Circular block length is a sensitivity parameter, so several lengths are reported. These bootstrap p-values are not an independent satellite measurement and do not remove sensor, land-cover, or confounding concerns. The analysis is limited to one local 4 km × 4 km Dushanbe window. MODIS NDVI measures vegetation greenness, not temperature or biomass directly. The NASA POWER five-year series is too short to support long-term climate conclusions.

**Interpretation:** the Dushanbe study window shows a strong, spatially coherent decline in MODIS NDVI over 2003–2023. The aggregate trend and most spatial signals remain under multiple temporal block-length sensitivity checks. The result does not identify the cause; land-cover change, urbanization, water availability, and sensor-related effects require separate investigation.
