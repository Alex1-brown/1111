# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Default branch: main

## Real-data scope
- NASA POWER daily point API: default 2021-01-01 through 2025-12-31; parameters T2M and PRECTOTCORR. Approximately 1,826 daily records per parameter before fill-value filtering.
- NASA GIBS MODIS Terra true-colour: default 60 real images sampled evenly across the same five-year period, 512 × 512 pixels each.
- science_core/imagery_series.py generates reproducible dates and summarizes adjacent-image comparisons.
- science_core/cli.py downloads each requested image, validates dimensions, compares each consecutive pair and writes source/date/URL/size metadata to report.json.
- Raw imagery is stored locally and must not be committed to Git.

## Architecture
Acquire → Validate → Clean → Process → Verify → Visualize is a reusable software workflow, not a physical law. Domain-specific science, units, assumptions, uncertainty and independent verification remain necessary.

- science_core/principles.py: workflow labels.
- science_core/pipeline.py: generic six-stage orchestrator.
- science_core/analysis.py: POWER payload summaries and RGB comparison.
- science_core/nasa.py: NASA POWER and GIBS retrieval.
- science_core/imagery_series.py: image date sampling and sequence summary.
- science_core/cli.py: live data retrieval and report generation.
- tests/test_analysis.py: offline tests for analysis, date sampling, sequence summaries and pipeline behavior.

## Verification status
The earlier pipeline CI run passed. The expanded downloader and 60-image live retrieval have not yet been tested against NASA endpoints. Offline tests validate deterministic logic only. Never claim that 60 images have been downloaded until a live run and report confirm the actual count.

## Scientific limitations
NASA POWER is gridded analysis/reanalysis-derived data, not a local station observation. GIBS true-colour RGB is browse imagery, not calibrated reflectance or land-cover classification. Clouds, atmosphere, illumination and compositing affect RGB differences. Five years alone do not establish a long-term climate trend.

## Efficient development
Batch related edits into one commit, run offline tests first, use Actions only at meaningful checkpoints, do not commit raw imagery, preserve source metadata, and never commit credentials or personal data.
