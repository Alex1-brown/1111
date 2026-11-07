# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Default branch: main

## Purpose
Build a reproducible, modular scientific-data toolkit for the NASA Space Apps Challenge. Keep the core independent from the user interface and from any single challenge dataset.

## Canonical workflow and implementation
**Acquire → Validate → Clean → Process → Verify → Visualize**
(Russian: **Получить данные → Проверить данные → Очистить данные → Обработать данные → Проверить результат → Визуализировать результат**).

This is a repeatable software workflow, not a universal equation like E=mc² or a physical law. Every scientific domain still needs its own validated equations, units, assumptions, uncertainty estimates, and interpretation.

- `science_core/principles.py`: canonical workflow labels in Russian and English.
- `science_core/pipeline.py`: executable six-stage orchestrator. It passes each stage's output forward, stops on exceptions, reports the failed stage, and requires verifier result to be exactly True.
- `science_core/analysis.py`: pure analysis functions, NASA POWER payload validation/summaries, monthly means and RGB comparison.
- `science_core/nasa.py`: NASA POWER and GIBS URL construction and data retrieval.
- `science_core/cli.py`: current POWER + GIBS data collection and report generation.
- `tests/test_analysis.py`: offline tests, including pipeline success, failed verification, and stage error reporting.
- `.github/workflows/tests.yml`: CI workflow.

## Verification status
Before the pipeline addition, GitHub Actions run #4 passed the previous offline tests. The new pipeline code and three new tests have been committed but require the next GitHub Actions run; do not describe the new code as CI-verified until that run succeeds.

## Current limits
The generic orchestrator is implemented and tested by designed offline test cases, but no challenge-specific six-stage NASA workflow has yet been wired through it. The existing CLI still runs its own POWER/GIBS sequence. Live NASA endpoint behavior and scientific interpretations need separate validation.

Scientific safeguards:
- NASA POWER gridded/reanalysis-style values are not local weather-station observations.
- GIBS true-colour browse-image RGB differences are not calibrated reflectance, land-cover classification, or proof of environmental change.
- A single year of data cannot establish a long-term climate trend.
- Preserve source, date, coordinates, units, missing-value handling, and processing steps in reports.

## Efficient development rules
1. Read this file and only relevant source/test files before changes.
2. Batch related edits into coherent commits.
3. Add offline tests with meaningful analytical changes.
4. Use GitHub Actions for meaningful checkpoints, not every edit.
5. Do not rerun successful workflows without a reason.
6. Avoid unnecessary dependencies and large raw datasets in Git history.
7. Never commit API keys, credentials, or personal data.
8. Update this file when architecture, verification status, or next priority changes.

## Next priorities
1. Wire the current NASA POWER analysis through the generic pipeline.
2. Add deterministic provenance and units to the report.
3. Harden HTTP error handling and offline fixtures.
4. Select one official NASA Space Apps challenge and implement its required scientific workflow; do not claim challenge compliance before validation.
