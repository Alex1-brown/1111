# NASA Universal Science Core

A reusable, testable scientific-data pipeline. The first validation targets are NASA POWER daily point data and NASA GIBS MODIS true-colour browse imagery.

The project is independent of paid app-hosting platforms. Source code, tests, provenance and reproducible commands live in GitHub.

## The six-stage scientific workflow

**Acquire → Validate → Clean → Process → Verify → Visualize**

The reusable orchestrator is `science_core.pipeline.run_pipeline`. It accepts six domain-specific functions and passes each stage's output to the next. A failed stage stops execution and raises `PipelineError` naming the stage. Verification must explicitly return `True`; a false or ambiguous result is rejected.

This is a software architecture pattern, not a universal scientific equation or a substitute for domain-specific physics, statistics, units, uncertainty analysis, or scientific review. See `science_core/principles.py` for the canonical labels and `science_core/pipeline.py` for the executable implementation.

## Current NASA data modules

- `science_core.nasa`: public NASA POWER and GIBS retrieval.
- `science_core.analysis`: fill-value filtering, descriptive statistics, monthly means, POWER payload analysis, and RGB browse-image comparison.
- `science_core.cli`: end-to-end demonstration for the current POWER/GIBS validation dataset.
- `science_core.pipeline`: reusable six-stage orchestration layer; domain-specific functions are supplied by each workflow.

## Quick start

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Fetch the current NASA validation dataset (requires internet):

```bash
python -m science_core.cli --latitude 38.5598 --longitude 68.7870 --start 20240101 --end 20241231 --output artifacts
```

The command writes JSON metrics and downloaded imagery under `artifacts/`.

## Scientific cautions

- NASA POWER is gridded analysis/reanalysis-derived data, not a direct weather-station observation.
- GIBS true-colour imagery is a browse visualization. Raw RGB differences are not calibrated reflectance differences and are not validated land-cover change.
- A single year cannot establish a long-term climate trend.
- This repository is a research prototype, not a certified scientific instrument.

## Sources

- NASA POWER API: https://power.larc.nasa.gov/docs/
- NASA GIBS API: https://nasa-gibs.github.io/gibs-api-docs/
- NASA Earthdata: https://www.earthdata.nasa.gov/

## License

MIT. See `LICENSE`.
