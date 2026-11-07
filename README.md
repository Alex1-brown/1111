# NASA Universal Science Core

A reusable scientific-data pipeline. The first real-data validation target combines five years of NASA POWER daily meteorological data with a 60-image NASA GIBS MODIS true-colour time series for one region.

Raw satellite imagery is downloaded at run time and is not committed to the repository.

## Six-stage workflow

**Acquire → Validate → Clean → Process → Verify → Visualize**

The reusable orchestrator is science_core.pipeline.run_pipeline. It is a software architecture pattern, not a universal scientific equation or a substitute for domain-specific science, units, uncertainty analysis or review.

## Real NASA data scope

- NASA POWER daily point data: T2M (2 m air temperature) and PRECTOTCORR (corrected precipitation), 2021-01-01 through 2025-12-31 by default. This is approximately 1,826 daily records per parameter before fill-value filtering.
- NASA GIBS: 60 MODIS Terra corrected-reflectance true-colour browse images sampled evenly across the same five-year interval. Default image size: 512 × 512 pixels.
- Each image is stored locally with its date, request URL, dimensions and byte size. Consecutive images are compared and summarized.

GIBS true-colour RGB values are not calibrated spectral measurements. Clouds, atmosphere, illumination and compositing affect pixel differences. Do not interpret RGB difference percentages as measured land-cover change.

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

Download the default dataset (requires internet and may take several minutes):

```bash
python -m science_core.cli --latitude 38.5598 --longitude 68.7870 --start 20210101 --end 20251231 --imagery-start 2021-01-01 --imagery-end 2025-12-31 --image-count 60 --output artifacts
```

For a small pilot run, set image-count to 5 and use a shorter imagery date range. The default run downloads 60 actual NASA GIBS images; it does not generate synthetic satellite pictures. If NASA does not return a valid image for a requested date, the run stops instead of silently substituting fabricated data.

The command writes nasa_power.json, report.json and downloaded images under artifacts/modis_series/. Do not commit raw imagery to Git.

## Scientific cautions

- NASA POWER is gridded analysis/reanalysis-derived data, not a direct local weather-station observation.
- GIBS true-colour imagery is browse visualization, not calibrated reflectance.
- RGB differences are exploratory screening metrics, not validated land-cover change.
- Five years of observations do not automatically establish a long-term climate trend; suitable statistical tests, uncertainty estimates and longer context may be required.

## Sources

- NASA POWER API: https://power.larc.nasa.gov/docs/
- NASA GIBS API: https://nasa-gibs.github.io/gibs-api-docs/
- NASA Earthdata: https://www.earthdata.nasa.gov/

## License

MIT. See LICENSE.
