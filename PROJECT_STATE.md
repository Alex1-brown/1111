# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Default branch: main

## Real-data scope
- NASA POWER daily point API: default 2021-01-01 through 2025-12-31; parameters T2M and PRECTOTCORR.
- NASA GIBS MODIS Terra true-colour: request 60 evenly sampled dates across the same five-year period, 512 × 512 pixels each; require at least 50 valid images for a successful run.
- Failed image requests are recorded in report.json; each request retries up to three times. Only valid PNG images with the expected dimensions count.
- A dedicated GitHub Actions workflow downloads the live datasets and uploads generated artifacts for 14 days. Raw imagery is not committed to Git.
- The live workflow must complete before claiming any image count or live NASA retrieval success.

## Architecture
Acquire → Validate → Clean → Process → Verify → Visualize is a reusable software workflow, not a physical law. Domain-specific science, units, assumptions, uncertainty and independent verification remain necessary.

- science_core/principles.py: workflow labels.
- science_core/pipeline.py: generic six-stage orchestrator.
- science_core/analysis.py: POWER payload summaries and RGB comparison.
- science_core/nasa.py: NASA POWER and GIBS retrieval with bounded retries.
- science_core/imagery_series.py: deterministic image date sampling and sequence summary.
- science_core/cli.py: live data retrieval, per-image failure recording and report generation.
- tests/test_analysis.py: offline tests for analysis, date sampling, sequence summaries and pipeline behavior.
- .github/workflows/nasa-live-validation.yml: live retrieval and artifact upload.

## Verification status
Offline unit tests passed on the previous code revision. The retry/failure-tolerant live downloader and dedicated workflow are newly added and need CI execution. No live NASA image count is verified until the live workflow produces its report and artifacts.

## Scientific limitations
NASA POWER is gridded analysis/reanalysis-derived data, not a local station observation. GIBS true-colour RGB is browse imagery, not calibrated reflectance or land-cover classification. Clouds, atmosphere, illumination and compositing affect RGB differences. Five years alone do not establish a long-term climate trend.

## Efficient development
Batch related edits into one commit, run offline tests first, use Actions only at meaningful checkpoints, do not commit raw imagery, preserve source metadata, and never commit credentials or personal data.
