# NASA Universal Science Core

A reusable, testable scientific-data pipeline. The first validation targets are:

1. **NASA POWER** daily point data (temperature and precipitation).
2. **NASA GIBS** MODIS true-colour browse imagery.

The project is deliberately independent of any paid app-hosting platform. Source code, tests, provenance and reproducible commands live in GitHub.

## Current scope

- Fetch real public NASA POWER and GIBS data.
- Preserve request URLs, timestamps, coordinates, layer names and metadata.
- Filter NASA fill values and calculate descriptive statistics.
- Compare RGB browse images with explicit warnings about interpretation.
- Run offline unit tests without making network calls.
- Run CI automatically on GitHub Actions.

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

Fetch the validation dataset:

```bash
python -m science_core.cli --latitude 38.5598 --longitude 68.7870 --start 20240101 --end 20241231 --output artifacts
```

The command writes JSON metrics and downloaded imagery under `artifacts/`.

## Scientific cautions

- NASA POWER is gridded analysis/reanalysis-derived data, not a direct weather-station observation.
- GIBS true-colour tiles are browse visualizations. Raw RGB differences are **not** calibrated reflectance differences and must not be presented as validated land-cover change.
- A single seasonal year cannot establish a long-term climate trend.
- This repository is a research prototype, not a certified scientific instrument.

## Architecture

`fetch` → `validate` → `process` → `verify` → `report`

The analysis functions are deterministic and tested separately from network access. Live integration checks are opt-in so ordinary tests remain reproducible and work offline.

## Sources

- NASA POWER API: https://power.larc.nasa.gov/docs/
- NASA GIBS API: https://nasa-gibs.github.io/gibs-api-docs/
- NASA Earthdata: https://www.earthdata.nasa.gov/

## License

MIT. See `LICENSE`.
