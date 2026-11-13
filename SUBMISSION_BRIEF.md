# Project submission brief

## Earth System Trend Detective Engine

**Challenge:** NASA Space Apps 2026 — Be An Earth System Trend Detective

### The question

How has vegetation greenness changed across a local 4 km × 4 km study window centred on Dushanbe, Tajikistan (38.5598° N, 68.7870° E), where are the strongest pixel-level changes, and how much confidence can be placed in those signals?

### What the tool does

The project combines two NASA data streams:

- **NASA Terra MODIS MOD13Q1.061:** 250 m, 16-day vegetation-index composites. The pipeline retrieves NDVI and pixel-reliability layers, applies the documented 0.0001 scale factor, and admits only reliability code 0 into the strict analysis.
- **NASA POWER:** daily 2 m air temperature and corrected precipitation for a five-year recent comparison window.

A credential-aware local ingestion adapter has also been implemented for **NASA GPM IMERG Final Daily V07**. It is not part of the current scientific results because no GPM granules have yet been obtained or analyzed.

The pipeline selects one MODIS composite per calendar month, nearest to the middle of the month; checks that raster grids remain aligned; aggregates quality-screened observations into annual pixel medians; and selects a contiguous trend interval only when annual composite coverage meets the configured threshold.

It then calculates per-pixel Sen slopes and Mann–Kendall diagnostics, reports coverage, a fixed-pixel panel, change-point candidates, anomalies, and exploratory monthly comparisons with NASA POWER. The current Hamed–Rao and residual moving-block bootstrap implementations failed project-specific AR(1) calibration; their p-values, BY transforms and intervals are sensitivity diagnostics only. Nonconstant spatial p/q inference and BY correction are withheld until a calibrated method is established.

### Why the design is evidence-first

The software keeps three things separate:

1. **Observed direction and magnitude:** Sen slope and annual NDVI summaries.
2. **Statistical evidence:** Sen-slope effect sizes, temporal-eligibility diagnostics and explicit withholding of inferential p/q claims while dependence-aware methods remain uncalibrated.
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
- NASA GPM IMERG Final Daily V07: https://doi.org/10.5067/GPM/IMERGDF/DAY/07
- NASA Space Apps challenge: https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/

### Limitations

The study window is local, not a national map of Tajikistan. MODIS 16-day best-pixel composites are not daily observations. Strict quality filtering reduces valid coverage. Annual medians suppress within-year seasonality. POWER is a gridded estimate, not a local weather-station record. Temporal autocorrelation, confounding, and the physical mismatch between NDVI and meteorological variables limit causal interpretation. Any significance claim must be tied to the exact method and eligible test family reported by the current run.

### AI-use disclosure

AI tools assisted with software implementation, code review, statistical-method review, and documentation. The source observations and derived measurements are retrieved from the cited scientific data providers; they are not AI-generated. No NASA logo, insignia, or NASA-branded visual asset is generated or modified by AI.

### Independent sensitivity check

The historical Dushanbe artifact is accompanied by residual circular moving-block bootstrap outputs for 2-, 3-, and 4-year blocks. The 2026-11-13 AR(1) calibration found non-nominal rejection rates and undercoverage of nominal 95% Sen intervals; therefore those p-values and BY transforms are sensitivity diagnostics only, not statistical significance or FDR-controlled inference. See [BLOCK_BOOTSTRAP_AUDIT.md](BLOCK_BOOTSTRAP_AUDIT.md) and [VALIDATION_REPORT.md](VALIDATION_REPORT.md). This is not an independent satellite validation or causal attribution.

### Landsat cross-sensor consistency check (QA v3)

The same 4 km × 4 km window was checked with one selected Landsat 8/9 Collection 2 Level-2 summer scene per year from 2013–2023. QA policy v3 applies the documented QA_PIXEL, QA_RADSAT and SR_QA_AEROSOL filters, rejects high-aerosol pixels, retains interpolated-aerosol pixels by default while counting them, and requires full-window coverage. Nine of eleven selected years met the 500-valid-pixel minimum. The 2015 and 2016 scenes retained 225 and 3 valid pixels respectively and are treated as missing years, not zero NDVI.

For the nine eligible Landsat years, Sen slope was −0.00279 NDVI/year, Kendall tau −0.500, Mann–Kendall p = 0.0763, and the nominal 95% Sen interval was [−0.00655, +0.00014]. The matched MODIS subset for those same nine years had Sen slope −0.00361 NDVI/year, p = 0.2515, and nominal 95% interval [−0.00561, +0.00270]. Neither trend is statistically significant at α = 0.05; both intervals include zero. Hamed–Rao and residual block-bootstrap inference were not run because n = 9 is below the documented ten-observation minimum. The paired window-median correlations were Pearson r = 0.375 and Spearman rho = 0.267; mean absolute difference was 0.0190 NDVI. These are descriptive cross-sensor consistency statistics, not pixel-wise accuracy or ground-truth validation. Do not use the earlier pre-QA-v3 Landsat trend and bootstrap numbers as current results.

See [VALIDATION_REPORT.md](VALIDATION_REPORT.md) for per-year counts, the QA policy, source provenance, and the distinction between historical and current runs.

### GPM IMERG adapter status

The repository includes a local NetCDF reader for GPM_3IMERGDF V07, checking the daily precipitation variable in mm/day, the valid half-hour sample count, optional random-error metadata, coordinate-grid consistency, product version, UTC dates, and source-file SHA-256 hashes. Annual grid-cell totals are emitted only when every calendar day is valid; incomplete years are not extrapolated. Run `python -m science_core.gpm_imerg --status` to check whether Earthdata credentials appear configured, then use authenticated GES DISC spatial/temporal subsetting to obtain local files. This check only detects credential presence; it does not authenticate or download. No GPM observations, maps, trends, or GPM-versus-POWER comparison are claimed yet. See [GPM_IMERG.md](GPM_IMERG.md).
