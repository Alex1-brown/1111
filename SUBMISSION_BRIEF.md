# Project submission brief

## Earth System Trend Detective Engine

**Challenge:** NASA Space Apps 2026 — Be An Earth System Trend Detective

### The question

How has vegetation greenness changed across a local 4 km × 4 km study window centred on Dushanbe, Tajikistan (38.5598° N, 68.7870° E), where are the strongest pixel-level changes, and how much confidence can be placed in those signals?

### What the tool does

The project combines two NASA data streams:

- **NASA Terra MODIS MOD13Q1.061:** 250 m, 16-day vegetation-index composites. The pipeline retrieves NDVI and pixel-reliability layers, applies the documented 0.0001 scale factor, and admits only reliability code 0 into the strict analysis.
- **NASA POWER:** daily 2 m air temperature and corrected precipitation for a five-year recent comparison window.

The pipeline selects one MODIS composite per calendar month, nearest to the middle of the month; checks that raster grids remain aligned; aggregates quality-screened observations into annual pixel medians; and selects a contiguous trend interval only when annual composite coverage meets the configured threshold.

It then calculates per-pixel Sen slopes and Mann–Kendall trend statistics, applies Hamed–Rao variance correction only when the annual series meets the method's regularity and estimability requirements, and applies Benjamini–Yekutieli correction only to the eligible spatial hypothesis family. It also reports coverage, a fixed-pixel panel, change-point diagnostics, anomalies, and exploratory monthly comparisons with NASA POWER.

### Why the design is evidence-first

The software keeps three things separate:

1. **Observed direction and magnitude:** Sen slope and annual NDVI summaries.
2. **Statistical evidence:** Mann–Kendall inference, temporal-dependence eligibility, and spatial multiple-testing correction.
3. **Context, not proof:** correlations between NDVI and POWER variables.

A pixel with an unavailable dependence-adjusted test does not receive a fabricated adjusted p-value or q-value. A short POWER time window is not presented as proof of long-term climate change. MODIS NDVI is not described as air temperature, and a correlation is not described as causation.

### Reproducibility

Install the dependencies and run:

```bash
python -m pip install -r requirements.txt
python -m science_core.cli --skip-gibs --image-count 60 --minimum-images 50
```

The default workflow is configured for a reproducible live data collection on GitHub Actions. It saves raw observations, quality counts, machine-readable JSON, CSV tables, GeoJSON pixel trends, SVG charts, and an offline HTML report.

### Primary NASA sources

- NASA Terra MOD13Q1.061: https://doi.org/10.5067/MODIS/MOD13Q1.061
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NASA Space Apps challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/

### Limitations

The study window is local, not a national map of Tajikistan. MODIS 16-day best-pixel composites are not daily observations. Strict quality filtering reduces valid coverage. Annual medians suppress within-year seasonality. POWER is a gridded estimate, not a local weather-station record. Temporal autocorrelation, confounding, and the physical mismatch between NDVI and meteorological variables limit causal interpretation. Any significance claim must be tied to the exact method and eligible test family reported by the current run.

### AI-use disclosure

AI tools assisted with software implementation, code review, statistical-method review, and documentation. The source observations and derived measurements are retrieved from the cited scientific data providers; they are not AI-generated. No NASA logo, insignia, or NASA-branded visual asset is generated or modified by AI.

### Independent sensitivity check

The current Dushanbe run is accompanied by a residual circular moving-block bootstrap check using 2-, 3-, and 4-year blocks, with Benjamini–Yekutieli correction within each eligible pixel family. See [VALIDATION_REPORT.md](VALIDATION_REPORT.md). This is a sensitivity analysis, not an independent satellite validation or causal attribution.

### Independent Landsat cross-sensor check

The same 4 km × 4 km window was checked with 11 USGS Landsat 8/9 Collection 2 Level-2 summer scenes (one per year, 2013–2023). The Landsat Sen slope was −0.00402 NDVI/year (Kendall tau −0.60; Hamed–Rao MK p = 0.0127). Residual moving-block bootstrap p-values were 0.0040, 0.00060, and 0.00020 for 2-, 3-, and 4-year blocks; all bootstrap slope intervals excluded zero. Landsat summer NDVI and July MODIS NDVI had Pearson r = 0.512 and Spearman rho = 0.473. This is cross-sensor consistency evidence, not ground truth or causal attribution; see [VALIDATION_REPORT.md](VALIDATION_REPORT.md).
