# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Default branch: main
Current HEAD at handoff: 9eee42eb0e3e965e33389e67139c936ce8db2988

## Objective

Build a reproducible Earth-system trend-detection prototype for NASA Space Apps 2026 challenge "Be An Earth System Trend Detective". The system is a modular scientific workflow, not a claim of a new universal physical law or a first-ever data-analysis tool.

## Current data pipeline

- NASA POWER daily point data: T2M and PRECTOTCORR, default 2021-01-01 through 2025-12-31.
- NASA GIBS MODIS Terra true-colour browse images: 60 sampled dates, 512x512; RGB differences are screening-only and not calibrated remote sensing.
- Quantitative MODIS/Terra MOD13Q1 NDVI and pixel-reliability bands through the public ORNL DAAC TESViS subset API. Default period 2001-01-01 through 2025-12-31; a 2 km radius around the POWER reference coordinate (approximately 4x4 km). Requests are batched in at most 10 composite dates.
- Only pixel-reliability code 0 is accepted into NDVI trend analysis. NDVI scale factor 0.0001 is applied. Raw values and QA codes are retained in CSV.
- The CLI now writes annual pixel medians, per-pixel Mann-Kendall/Sen trends, BY-adjusted q-values, spatial-trend CSV and GeoJSON, plus JSON report.
- The quantitative MODIS workflow is integrated into the live CLI and current GitHub Actions run #4 is processing the new 25-year NDVI dataset. Verify that run before claiming the live NDVI outputs exist.

## Architecture and modules

- `science_core/pipeline.py`, `principles.py`: Acquire -> Validate -> Clean -> Process -> Verify -> Visualize orchestration; domain methods remain separate.
- `science_core/analysis.py`: NASA POWER payload checks, summaries, RGB browse comparison.
- `science_core/statistical_analysis.py`: paired daily POWER annual/monthly/seasonal summaries, OLS descriptive slopes, Pearson correlation, annual and seasonal non-parametric trend outputs.
- `science_core/trend_analysis.py`: Mann-Kendall, exact permutation p-values for annual n<=8, Sen slope, Seasonal Mann-Kendall.
- `science_core/spatial_analysis.py`: annual per-pixel NDVI medians, per-pixel trends, Benjamini-Yekutieli spatial multiple-testing correction, approximate MODIS sinusoidal geolocation helper.
- `science_core/ornl_modis.py`: public ORNL DAAC MOD13Q1 NDVI and pixel-reliability downloader; retries transient HTTP failures; raw QA retained.
- `science_core/cross_source_analysis.py`: monthly NDVI/POWER alignment, calendar-month anomalies, Pearson/Spearman associations, previous-month precipitation association and detrended anomaly correlations. This module is tested but not yet wired into the CLI report.
- `science_core/visualization.py`: dependency-free SVG line chart renderer. This module is tested but not yet wired into the CLI report.
- `science_core/cli.py`: live NASA/ORNL collection and JSON/CSV/GeoJSON report artifacts.
- Offline tests currently cover the analysis, statistical, spatial, ORNL adapter, visualization and cross-source modules.

## Verification status

- Live NASA data run #3 (2026-11-07): 1,826 daily POWER temperature records; 1,826 precipitation records; 59/60 valid GIBS images; 58 adjacent RGB comparisons. Artifact: https://github.com/Alex1-brown/1111/actions/runs/42384269989/artifacts/13578264908
- Offline tests run #21: success, 31 tests.
- Offline tests run #22: success, 31 tests.
- Offline tests run #23: success, 35 tests.
- Offline tests run #24 (cross-source module): in progress at handoff; check status.
- Live data run #4 (new MOD13Q1 NDVI pipeline): in progress at handoff; run URL https://github.com/Alex1-brown/1111/actions/runs/42387847600. Check actual step logs, report, and artifact before claiming success.
- New live run is intentionally the only one triggered for the integrated quantitative MODIS pipeline. Do not launch duplicate live runs unless the first fails or code materially changes.

## Scientific limitations and next priorities

1. Check live run #4. If it succeeds, extract actual NDVI composite count, quality-filtered pixel count, grid dimensions, per-pixel trend count, FDR-significant count, annual summary and artifact URL. Inspect report metadata and GeoJSON coordinate assumptions.
2. Wire `cross_source_analysis.py` into the CLI using the common 2021-2025 months. Export `monthly_cross_source.csv`; keep all associations explicitly exploratory, not validation or causation.
3. Wire `visualization.py` into the CLI to produce annual temperature, precipitation and NDVI SVG charts. Add chart paths to report.json.
4. Verify MODIS row/column geolocation against authoritative ORNL source metadata before claiming precise GeoJSON coordinates. Current transform treats request coordinate as middle-pixel center and is explicitly approximate.
5. Add temporal autocorrelation diagnostics/adjustment before treating Mann-Kendall p-values as inferential. Current MK p-values are not adjusted for serial autocorrelation. BY corrects spatial multiple testing only conditional on valid pixel p-values.
6. Consider change-point detection, robust anomalies, confidence intervals and map presentation after core outputs are validated.
7. Preserve raw data, QA, source/version/DOI, units, processing settings and failure records. Never synthesize missing satellite observations.
8. Keep NASA live Actions usage low: offline tests on code changes; only one live collection run after a meaningful integrated data-pipeline change.

## Known interpretation constraints

- NASA POWER is a gridded product, not a local weather-station measurement.
- MOD13Q1 is a 16-day vegetation-index composite, not a direct temperature or precipitation measurement.
- NDVI is a local approximately 4x4 km sample; POWER is a gridded point estimate. Their spatial supports differ.
- Annual medians suppress seasonal variation and hide within-year dynamics.
- Five-year POWER records alone do not establish long-term climate trends.
- A detected trend is not an explanation of its cause.
