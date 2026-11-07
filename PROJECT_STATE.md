# Project state and handoff

Last updated: 2026-11-07
Repository: https://github.com/Alex1-brown/1111
Default branch: main

## Purpose
Build a reproducible, modular scientific-data toolkit for the NASA Space Apps Challenge. Keep the core independent from the user interface and from any single challenge dataset.

## Canonical scientific workflow
The project uses this repeatable architecture:
**Acquire → Validate → Clean → Process → Verify → Visualize**
(Russian: **Получить данные → Проверить данные → Очистить данные → Обработать данные → Проверить результат → Визуализировать результат**).

This is a workflow pattern, not a universal equation like E=mc² and not a physical law. It organizes data handling; each scientific domain still requires its own validated equations, units, assumptions, uncertainty estimates, and interpretation.

The canonical labels are defined in `science_core/principles.py`.

## Current implementation
- `science_core/principles.py`: canonical six-stage workflow labels in Russian and English.
- `science_core/analysis.py`: pure-Python data validation, summaries, monthly means, RGB image comparison, and NASA POWER payload analysis.
- `science_core/nasa.py`: URL construction and retrieval helpers for NASA POWER and NASA GIBS MODIS true-colour imagery.
- `science_core/cli.py`: command-line data collection and report generation.
- `tests/test_analysis.py`: offline unit tests.
- `.github/workflows/tests.yml`: CI workflow.
- `README.md`: setup and current scientific limitations.

## Verified status
GitHub Actions run #4, commit `115849438b223a4d2815e386b1b94b411c881086`, completed successfully on 2026-11-07. The job installed dependencies and passed the offline unit-test step.

This confirms the current automated unit tests pass. It does NOT yet prove every live NASA endpoint, every downloaded image, or scientific interpretations are correct. The newly added principles module is a small constants/documentation module and has not yet been included in a new CI run.

## Scientific safeguards
- NASA POWER gridded/reanalysis-style values must not be described as local weather-station observations.
- GIBS true-colour browse-image RGB differences are visual comparisons, not calibrated reflectance, land-cover classification, or proof of environmental change.
- A single year of data cannot establish a long-term climate trend.
- Preserve source, date, coordinates, units, missing-value handling, and processing steps in generated reports.

## Efficient development rules
1. Read this file and the relevant source/test files before changing code; do not reread the whole repository without a reason.
2. Prefer one coherent batch of related changes over many tiny commits.
3. Add or update offline tests with each meaningful analytical change.
4. Run tests locally when possible; use GitHub Actions for meaningful checkpoints, not for every edit.
5. Avoid rerunning successful workflows. Retry only failed jobs when appropriate.
6. Do not add dependencies unless they materially improve correctness or reduce complexity.
7. Keep large datasets and generated imagery out of Git history. Store only small examples or metadata; use release artifacts or external authoritative sources for larger outputs.
8. Never commit API keys, credentials, personal data, or large raw downloads.
9. Keep this handoff file updated when architecture, verified status, or the next priority changes.
10. Treat the six-stage workflow as the common project structure, not as a substitute for challenge-specific scientific methods.

## Next technical priorities
1. Inspect the current NASA POWER and GIBS retrieval code for robust timeouts, HTTP errors, and clear failure messages.
2. Add small offline fixtures for NASA POWER responses and image-processing edge cases.
3. Make CLI output deterministic and include provenance/units in its JSON report.
4. Only then select one official NASA Space Apps 2026 challenge and implement its specific scientific workflow. Do not claim challenge compliance until its required datasets and outputs are implemented and validated.
