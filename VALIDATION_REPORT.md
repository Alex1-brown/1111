# Independent statistical sensitivity check

> **Status correction — 2026-11-13:** The numeric p/q counts and bootstrap intervals in the historical sections below come from earlier artifacts and are not current inferential results. The subsequent Hamed–Rao calibration found non-nominal false-positive rates. The new residual moving-block bootstrap calibration found null rejection rates of 1.5–26.0% and nominal 95% Sen-interval coverage of only 60.5–93.0% under the tested Gaussian AR(1) models. Therefore historical Hamed–Rao and block-bootstrap p-values, BY q-values, and bootstrap intervals must be treated as sensitivity diagnostics only. Do not describe the historical “136/233” or “132” counts as statistically significant. Current nonconstant spatial p/q inference is withheld; Sen slopes remain descriptive. See [SERIAL_CORRELATION_AUDIT.md](SERIAL_CORRELATION_AUDIT.md) and [BLOCK_BOOTSTRAP_AUDIT.md](BLOCK_BOOTSTRAP_AUDIT.md).

**Dataset run:** [NASA live data collection #22](https://github.com/Alex1-brown/1111/actions/runs/42662224195)  
**Code snapshot:** `3bb97306227867aef2781eb49a0b36574da46e2f`  
**Study area:** Dushanbe, Tajikistan — 38.5598° N, 68.7870° E  
**Trend interval:** 2003–2023

## Historical MODIS snapshot — descriptive only; p/q inference superseded

The live pipeline retrieved 515 available Terra MOD13Q1.061 STAC items and selected 272 monthly composites. Across a 17 × 17 local pixel window it produced 78,608 raw pixel observations; 43,891 passed the strict pixel-reliability code-0 filter (55.8%). A fixed 231-pixel panel was available for every year from 2003 through 2023.

Of 261 pixels with Sen-slope estimates, 233 met the temporal eligibility rules used by the historical Hamed–Rao calculation. **136 of those 233 had historical BY q ≤ 0.05 (diagnostic only, not calibrated inference); 135 had negative Sen slopes and one had a positive slope.** The other 28 trend estimates were excluded from that historical adjusted family.

For the historical fixed-panel median series, Sen slope was **−0.0026409 NDVI units/year** and Kendall tau was **−0.662**. The historical Hamed–Rao diagnostic p-value was **3.06 × 10⁻⁵** (variance factor 1.0; no detrended-rank ACF lag selected), but it is not calibrated and is not inferential evidence. Pettitt's test identified a candidate change point in 2013 (p = 0.0107); that p-value is also unadjusted for temporal autocorrelation and is a screening result only.

The fixed-panel median NDVI moved from 0.2734 in 2003 to 0.20615 in 2023, a **24.6% decrease** relative to the 2003 value. This is a local vegetation-index result, not proof of a specific cause or a national trend for Tajikistan.

## Historical moving-block bootstrap output — not calibrated inference

To check whether the spatial result depended entirely on the Hamed–Rao variance approximation, a separate offline sensitivity analysis was run on the same 233 temporally eligible pixel series:

- Sen-detrend each annual pixel series.
- Resample circular blocks of residuals, preserving short-range dependence within each block.
- Compare the absolute bootstrap Mann–Kendall S statistics with the observed absolute S.
- Use 5,000 replicates per pixel and block lengths of 2, 3, and 4 years.
- Apply Benjamini–Yekutieli correction separately within each block-length family.

| Historical diagnostic family | Pixels with diagnostic BY q ≤ 0.05 (not inferential) |
|---|---:|
| Primary Hamed–Rao | 136 |
| Moving blocks, 2 years | 137 |
| Moving blocks, 3 years | 141 |
| Moving blocks, 4 years | 146 |
| Diagnostic q ≤ 0.05 at all three block lengths | **132** |

The 3-year bootstrap family shared 127 pixels with diagnostic q ≤ 0.05 in the historical Hamed–Rao family. Across all three bootstrap block lengths, 132 pixels had diagnostic q ≤ 0.05; 127 of those also had historical Hamed–Rao q ≤ 0.05 (93.4% of that historical set). Of these 132 pixels, 131 had negative slopes and one had a positive slope. This is historical sensitivity agreement only. The 2026-11-13 calibration subsequently showed that the current residual moving-block bootstrap is not calibrated for inferential use, so these counts are not evidence of statistical significance.

For the fixed-panel aggregate series, the historical 5,000-replicate residual moving-block bootstrap produced zero null S statistics as extreme as observed for each block length. The plus-one diagnostic p-value was therefore 1/5,001 (approximately 0.00020). The historical percentile intervals excluded zero, but the later calibration found that this interval procedure undercovers under serial dependence; these values are not calibrated 95% confidence intervals:

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


## Landsat quality and provenance fields

The Landsat CSV now records each selected STAC item ID and self URL, collection ID, acquisition date, source CRS, and raster window transform. Its JSON summary records the USGS DOI, Planetary Computer STAC endpoint, source band names, unitless surface-reflectance scaling, NDVI equation, and the exact QA policy. The project-level DN filter is 7,273–43,636, corresponding approximately to scaled reflectance 0–1; this is a conservative project filter, not the full USGS stored-DN valid range.

The current code uses QA policy v3 (landsat_c2_l2_land_ndvi_v3). It rejects QA_PIXEL bits 0–5 and 7 (fill, cloud/cirrus, shadow, snow and water); QA_RADSAT bits 3 and 4 (red B4 and NIR B5 saturation) plus bit 11 (terrain occlusion); and SR_QA_AEROSOL bits 0 and 2 (fill and water) plus aerosol level 3 (high; bits 6–7). Interpolated aerosol (SR_QA_AEROSOL bit 5) is counted and retained by default because the USGS documentation identifies it as an interpolation flag but does not designate it as invalid; an optional strict sensitivity flag can exclude it. Bit 1 (valid aerosol retrieval) is not required, so climatology-level aerosol may be retained unless another excluded flag is set. QA_RADSAT saturation in unrelated bands is not used to reject an NDVI pixel. Scene selection requires the STAC footprint to contain nine samples across the full nominal window, and the raster window is independently required to meet a minimum coverage fraction. Per-scene QA flag counts are emitted; counts can overlap.

The Landsat residual moving-block bootstrap is only run when there are at least ten unique, consecutive annual observations, matching the bootstrap implementation's preconditions. With fewer years or any annual gap, the JSON now reports `status: not_run` and the exact reason; it does not fail the entire cross-sensor comparison or fabricate a bootstrap result.

## Independent cross-sensor check: Landsat 8/9

**Quality-screening update (2026-11-11):** the first QA-v2 run against existing NASA artifact #22 completed, but only 8 of 11 selected years passed the 500-pixel threshold. Three selected scenes returned 499, 37 and 0 valid pixels. That run did not emit per-flag counts or enforce full-window coverage, so it cannot establish whether the losses came from aerosol interpolation, partial scene coverage or other QA flags. The current QA policy v3 therefore retains interpolated aerosol by default while reporting it, adds an optional strict interpolation sensitivity flag, and requires both full-window STAC footprint coverage and a raster-window coverage threshold. The numerical results below remain historical pre-v2 baselines; neither the v2 nor v3 run should be represented by those old values.

A separate 2013–2023 comparison used USGS Landsat 8/9 Collection 2 Level-2 Surface Reflectance in the same 4 km × 4 km window. The Planetary Computer STAC search returned 997 candidate items. One summer scene per year, nearest to July 15 within June 1–September 30 and with scene cloud cover no greater than 40%, was selected. All 11 years were represented and no selected scene failed pixel-quality checks.

Landsat surface reflectance was converted using the USGS Collection 2 scale factor 0.0000275 and offset −0.2. Under the previous mask, QA_PIXEL fill, dilated-cloud, cirrus, cloud, cloud-shadow, and snow flags were excluded, as were pixels with any QA_RADSAT flag. Each scene retained 17,681–17,689 pixels under that earlier mask. These counts are not comparable to QA policy v2 until the workflow is rerun.

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

## Landsat QA-v3 cross-sensor run — 2026-11-11

A Landsat-only validation run used the already-collected NASA MODIS artifact from live run #22 (run ID `42662224195`; no new NASA collection was started). The Landsat source was USGS Landsat 8/9 Collection 2 Level-2 Surface Reflectance, retrieved as COGs from the Microsoft Planetary Computer STAC collection. The STAC search returned 997 items. The selected analysis window was 4 km × 4 km.

QA policy v3 rejected QA_PIXEL fill/cloud/cirrus/shadow/snow/water, QA_RADSAT red B4 and NIR B5 saturation plus terrain occlusion, SR_QA_AEROSOL fill/water, and high-aerosol pixels. The interpolation flag was counted but retained by default; a separate optional mode can exclude it. All nine successful scenes had a raster-window coverage fraction of 1.0. Two selected years did not meet the minimum of 500 valid pixels: 2015 retained 225 and 2016 retained 3. They are missing observations, not zero-valued NDVI.

| Year | Landsat scene | Valid pixels | Valid fraction | Landsat median NDVI | Matched MODIS median NDVI | Landsat − MODIS |
|---:|---|---:|---:|---:|---:|---:|
| 2013 | LC08_L2SP_153033_20130717_02_T1 | 4,514 | 0.2552 | 0.2300 | 0.2530 | −0.0230 |
| 2014 | LC08_L2SP_154033_20140711_02_T1 | 11,385 | 0.6436 | 0.2425 | 0.2495 | −0.0070 |
| 2017 | LC08_L2SP_154033_20170719_02_T1 | 10,170 | 0.5749 | 0.2274 | 0.2345 | −0.0071 |
| 2018 | LC08_L2SP_153033_20180715_02_T1 | 6,163 | 0.3484 | 0.2037 | 0.2344 | −0.0307 |
| 2019 | LC08_L2SP_153033_20190718_02_T1 | 11,424 | 0.6458 | 0.2308 | 0.2384 | −0.0076 |
| 2020 | LC08_L2SP_153033_20200704_02_T1 | 5,192 | 0.2935 | 0.2225 | 0.2491 | −0.0266 |
| 2021 | LC08_L2SP_154033_20210714_02_T1 | 6,183 | 0.3495 | 0.1966 | 0.2540 | −0.0574 |
| 2022 | LC09_L2SP_153033_20220718_02_T1 | 6,513 | 0.3682 | 0.2006 | 0.2046 | −0.0040 |
| 2023 | LC08_L2SP_153033_20230713_02_T1 | 6,937 | 0.3922 | 0.2149 | 0.2073 | +0.0076 |

Across these nine paired annual window medians, Pearson r = **0.3750** and Spearman rho = **0.2667**. Mean bias (Landsat minus MODIS) = **−0.0173**, median bias = **−0.0076**, mean absolute difference = **0.0190**, and root-mean-square difference = **0.0252**. These are descriptive differences between window medians, not pixel-wise accuracy scores.

The Landsat series has n = 9, Kendall tau = **−0.500**, p = **0.0763**, and Sen slope = **−0.00279 NDVI/year** with nominal 95% interval **[−0.00655, +0.00014]**. The matched MODIS subset has n = 9, tau = **−0.333**, p = **0.2515**, and Sen slope = **−0.00361 NDVI/year** with nominal 95% interval **[−0.00561, +0.00270]**. Both slope estimates are negative, but **neither trend is statistically significant at α = 0.05 and both intervals include zero**. Hamed–Rao correction and residual block bootstrap were not run because n = 9 is below the documented 10-observation minimum; these p-values and intervals use the independent-observation normal approximation and do not correct for temporal autocorrelation.

For the nine successful scenes, the non-exclusive QA diagnostics reported 6,189–13,153 high-aerosol pixels, 15,709–15,753 interpolated-aerosol pixels, and 9–86 water pixels per 17,689-pixel window. Cloud, cirrus, shadow, snow and red/NIR saturation flags were zero in those successful windows. QA counts for the two failed scenes were not emitted by this run, so their low valid counts cannot be attributed to a single flag from the available output.

USGS cautions against using high-aerosol pixels and documents the aerosol interpolation flag separately from the high-aerosol level. The local result therefore uses the high-aerosol exclusion, records interpolation without rejecting it by default, and exposes an optional strict sensitivity mode. The USGS also documents surface-reflectance retrieval caveats for hyper-arid areas and aerosol retrieval failures; this is relevant when interpreting the local dry-region Landsat comparison. This cross-sensor check does **not** independently confirm a significant trend. It is not ground truth: Landsat 30 m and MODIS 250 m have different spatial support, spectral response, compositing and acquisition dates.

## Limitations

The residual bootstrap assumes the detrended residual process is sufficiently stationary. Circular block length is a sensitivity parameter, so several lengths are reported. These bootstrap p-values are not an independent satellite measurement and do not remove sensor, land-cover, or confounding concerns. The analysis is limited to one local 4 km × 4 km Dushanbe window. MODIS NDVI measures vegetation greenness, not temperature or biomass directly. The NASA POWER five-year series is too short to support long-term climate conclusions.

**Current interpretation:** historical Sen slopes indicate a negative descriptive direction for the Dushanbe fixed-panel NDVI series, but the historical Hamed–Rao and residual block-bootstrap p/q results are not calibrated for inference. The later QA-v3 Landsat comparison has only nine usable years and is not statistically significant under its nominal iid approximation. The project therefore does not currently claim a statistically confirmed spatial NDVI trend or a cause. Land-cover change, urbanization, water availability, sensor effects and cross-source differences require further investigation.
