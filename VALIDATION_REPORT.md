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
| Moving blocks, 3 years | 138 |
| Moving blocks, 4 years | 146 |
| Bootstrap significant at all three block lengths | **132** |

The 3-year bootstrap family shared 128 significant pixels with the Hamed–Rao family. Across all three bootstrap block lengths, 132 pixels remained significant; 128 of those also passed the primary Hamed–Rao analysis. The direction was overwhelmingly negative in both families. This agreement is a useful robustness signal, although it does not prove that either method is perfectly calibrated.

For the fixed-panel aggregate series, a 5,000-replicate residual moving-block bootstrap produced zero null S statistics as extreme as observed for each block length. The plus-one empirical p-value was therefore 1/5,001 (approximately 0.00020). The bootstrap 95% Sen-slope intervals also excluded zero:

| Block length | Bootstrap 95% Sen-slope interval (NDVI/year) |
|---|---|
| 2 years | [−0.003445, −0.001845] |
| 3 years | [−0.003342, −0.001916] |
| 4 years | [−0.003303, −0.001953] |

## Meteorological context

NASA POWER contributed 1,826 paired daily records for 2021–2025. The five annual values did **not** establish a significant temperature or precipitation trend (annual Mann–Kendall p = 1.00 for temperature and p = 0.483 for precipitation). The monthly NDVI–temperature anomaly correlation was positive (Pearson r = 0.508 across 36 common months), but it is exploratory only: the spatial supports differ, serial dependence is not removed, and correlation does not establish causation. No warming or precipitation-causation claim is made from this short interval.

## Reproduction

After extracting the NASA Actions artifact:

```bash
python -m pip install -r requirements.txt
python -m science_core.bootstrap_validation artifacts --spatial-replicates 5000 --fixed-panel-replicates 5000 --block-lengths 2,3,4
```

The script writes `ndvi_block_bootstrap_validation.csv` and `ndvi_block_bootstrap_validation.json` under `artifacts/modis_ndvi/`.

## Limitations

The residual bootstrap assumes the detrended residual process is sufficiently stationary. Circular block length is a sensitivity parameter, so several lengths are reported. These bootstrap p-values are not an independent satellite measurement and do not remove sensor, land-cover, or confounding concerns. The analysis is limited to one local 4 km × 4 km Dushanbe window. MODIS NDVI measures vegetation greenness, not temperature or biomass directly. The NASA POWER five-year series is too short to support long-term climate conclusions.

**Interpretation:** the Dushanbe study window shows a strong, spatially coherent decline in MODIS NDVI over 2003–2023. The aggregate trend and most spatial signals remain under multiple temporal block-length sensitivity checks. The result does not identify the cause; land-cover change, urbanization, water availability, and sensor-related effects require separate investigation.
