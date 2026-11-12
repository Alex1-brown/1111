# NASA GPM IMERG Final Daily V07 adapter

## Product selected

The adapter targets **GPM_3IMERGDF V07**, the NASA GES DISC Level-3 Final daily product.

- Product page: https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary
- DOI: https://doi.org/10.5067/GPM/IMERGDF/DAY/07
- Spatial resolution: 0.1° × 0.1° (about 10 km)
- Temporal resolution: one UTC day, 00:00–24:00
- Primary variable: `precipitation`, units `mm/day`
- Completeness diagnostic: `precipitation_cnt`, number of valid half-hourly samples (0–48)
- Uncertainty: `randomError`, units `mm/day`
- Separate microwave-only estimate: `MWprecipitation`, not substituted for the combined variable

The V07 daily value is the mean of valid half-hourly precipitation rates multiplied by 24. A zero precipitation value is valid when the sample count is positive. The count is a completeness diagnostic, not a standalone accuracy guarantee. The daily product is UTC-based; do not label it as a local-calendar-day total without re-aggregation from half-hourly data.

## Authentication and access

GES DISC downloads require a free NASA Earthdata Login account and authorization of the GES DISC application. The adapter does **not** bypass authentication and does not attempt remote downloads.

Check the local credential configuration:

```bash
python -m science_core.gpm_imerg --status
```

The check looks for `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD`, `EARTHDATA_TOKEN`, or credentials in `~/.netrc` (Windows: `~/_netrc`). It reports only whether credentials appear to be present; it does not authenticate them and never prints secret values. If none are found, the status is `blocked_missing_credentials`.

To configure a local netrc file, use the following placeholder format and protect it from other users:

```text
machine urs.earthdata.nasa.gov
  login YOUR_EARTHDATA_USERNAME
  password YOUR_EARTHDATA_PASSWORD
```

On Unix-like systems, restrict permissions with `chmod 600 ~/.netrc`. Never commit `.netrc`, `_netrc`, passwords, or tokens. The current adapter reads **local GES DISC spatial/temporal subset NetCDF files**; it does not download global daily granules. Use the GES DISC subset/download interface to select the study window and date range, then place the resulting `.nc4` or `.nc` files in a local directory.

## Local ingestion

Install dependencies and run:

```bash
python -m pip install -r requirements.txt
python -m science_core.gpm_imerg --input-dir path/to/gpm_subset --output-dir artifacts/gpm_imerg
```

Or pass explicit files with `--input file1.nc4 file2.nc4`.

Outputs:
- `gpm_report.json`: product identity, DOI, source-file SHA-256 hashes, global attributes, units, grid metadata, QC counts, and limitations.
- `gpm_annual_grid.csv`: per-grid-cell annual coverage and observed-day sums.

The reader normalizes NetCDF dimension order to `(time, lat, lon)`, checks that files share the same coordinate grid, rejects duplicate UTC dates, validates the precipitation units, and records source-file hashes. It does not silently regrid mismatched files.

## Quality policy and annual totals

A daily grid cell is accepted only when:
- precipitation is present, finite, and non-negative;
- `precipitation_cnt` is an integer between 1 and 48.

An optional `--minimum-valid-half-hours N` (1–48) applies a stricter user-selected completeness screen. The default does not impose an arbitrary count threshold. `randomError` is retained as an uncertainty field and is not used as a precipitation rejection mask. `MWprecipitation` remains a separate microwave-only estimate. There is no optical cloud mask for this precipitation product; the adapter explicitly reports that no cloud mask was applied.

The adapter reports observed-day sums for incomplete years, but writes `annual_total_mm` only when every calendar day in that year is valid for that pixel. It does not fill missing days or scale partial sums to a full-year estimate. This strict rule may leave some pixel-years ineligible for trend analysis.

## Interpretation limits

IMERG is a multisatellite precipitation estimate, not a rain-gauge observation. NASA notes that skill can be lower over complex terrain and that changes in the satellite constellation can introduce artifacts in multi-year analyses. This matters in mountainous Tajikistan. A comparison with NASA POWER would be a cross-source consistency check, not ground-truth validation: the products have different spatial support and processing.

The GES DISC catalog snapshot consulted on 2026-11-12 listed GPM_3IMERGDF V07 temporal coverage through 2025-09-30. Recheck the live catalog and product version before selecting the final analysis period; do not assume V07 extends to the present.

**No GPM observations have yet been downloaded or analyzed for this project.** The adapter and offline tests establish a safe ingestion path only. No GPM trend, map, or MODIS/POWER validation result is claimed.
