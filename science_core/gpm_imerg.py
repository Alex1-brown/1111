"""Credential-aware ingestion and QC for NASA GPM IMERG Final Daily V07.

This module deliberately does not download data. GES DISC granule downloads require
Earthdata Login; users obtain a spatially/temporally subsetted NetCDF file there,
then pass the local file to this reproducible reader.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import os
from datetime import date
from netrc import NetrcParseError, netrc
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

GPM_SHORT_NAME = "GPM_3IMERGDF"
GPM_VERSION = "07"
GPM_PRODUCT_NAME = "GPM IMERG Final Precipitation L3 1 day 0.1 degree x 0.1 degree V07"
GPM_DOI = "https://doi.org/10.5067/GPM/IMERGDF/DAY/07"
GPM_DATASET_URL = "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary"
EARTHDATA_LOGIN_URL = "https://urs.earthdata.nasa.gov/"
EARTHDATA_ACCESS_GUIDE = "https://urs.earthdata.nasa.gov/documentation/for_users/data_access"
PRECIPITATION_VARIABLE = "precipitation"
COUNT_VARIABLE = "precipitation_cnt"
RANDOM_ERROR_VARIABLE = "randomError"
MW_PRECIPITATION_VARIABLE = "MWprecipitation"
DAILY_UNITS = "mm/day"


class GPMIMERGError(RuntimeError):
    """Raised when a local IMERG file cannot be safely interpreted."""


def earthdata_credentials_status(
    environ: Mapping[str, str] | None = None,
    netrc_path: str | Path | None = None,
) -> dict[str, object]:
    """Report credential presence without reading secrets into the result or logs."""
    env = os.environ if environ is None else environ
    if env.get("EARTHDATA_TOKEN"):
        return {
            "status": "credentials_present_not_verified",
            "source": "EARTHDATA_TOKEN environment variable",
            "secret_values_exposed": False,
        }
    if env.get("EARTHDATA_USERNAME") and env.get("EARTHDATA_PASSWORD"):
        return {
            "status": "credentials_present_not_verified",
            "source": "EARTHDATA_USERNAME/EARTHDATA_PASSWORD environment variables",
            "secret_values_exposed": False,
        }

    if netrc_path is not None:
        candidates = [Path(netrc_path)]
    else:
        candidates = [Path.home() / ".netrc"]
        if os.name == "nt":
            candidates.append(Path.home() / "_netrc")

    for candidate in candidates:
        try:
            credentials = netrc(str(candidate)).authenticators("urs.earthdata.nasa.gov")
        except (OSError, NetrcParseError):
            continue
        if credentials and credentials[0] and credentials[2]:
            return {
                "status": "credentials_present_not_verified",
                "source": str(candidate.name),
                "secret_values_exposed": False,
            }

    return {
        "status": "missing_credentials",
        "source": None,
        "secret_values_exposed": False,
    }


def build_access_status(
    environ: Mapping[str, str] | None = None,
    netrc_path: str | Path | None = None,
) -> dict[str, object]:
    credentials = earthdata_credentials_status(environ, netrc_path)
    has_credentials = credentials["status"] == "credentials_present_not_verified"
    return {
        "status": (
            "credentials_present_manual_subset_required"
            if has_credentials else "blocked_missing_credentials"
        ),
        "credentials": credentials,
        "download_attempted": False,
        "automatic_remote_download_enabled": False,
        "product": GPM_SHORT_NAME,
        "version": GPM_VERSION,
        "dataset_url": GPM_DATASET_URL,
        "earthdata_login_url": EARTHDATA_LOGIN_URL,
        "access_guide": EARTHDATA_ACCESS_GUIDE,
        "message": (
            "Credentials appear to be configured but have not been authenticated. "
            "This build reads local GES DISC subset files and does not start remote downloads."
            if has_credentials else
            "Earthdata Login credentials were not found. No request or download was attempted. "
            "Register with NASA Earthdata and obtain a GES DISC subset before local ingestion."
        ),
    }


def _json_safe(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unit_is_mm_per_day(value: object) -> bool:
    normalized = str(value).lower().replace(" ", "").replace("**", "")
    return normalized in {"mm/day", "mmday-1", "mmday^-1", "mmd-1"}


def _find_variable(container: object, names: Sequence[str], required: bool = True):
    variables = getattr(container, "variables", {})
    for name in names:
        if name in variables:
            return variables[name]
    if required:
        raise GPMIMERGError(f"Required NetCDF variable is missing: {' or '.join(names)}")
    return None


def _to_time_lat_lon(variable: object, time_dim: str, lat_dim: str, lon_dim: str) -> np.ma.MaskedArray:
    dimensions = tuple(getattr(variable, "dimensions", ()))
    expected = (time_dim, lat_dim, lon_dim)
    if len(dimensions) != 3 or set(dimensions) != set(expected):
        raise GPMIMERGError(
            f"Variable {getattr(variable, 'name', '<unknown>')} must use exactly "
            f"the time/latitude/longitude dimensions; received {dimensions!r}."
        )
    axes = tuple(dimensions.index(name) for name in expected)
    return np.ma.transpose(np.ma.asarray(variable[:]), axes)


def _date_from_cf(value: object) -> date:
    try:
        return date(int(value.year), int(value.month), int(value.day))
    except (AttributeError, TypeError, ValueError) as exc:
        raise GPMIMERGError(f"Could not decode an IMERG time coordinate: {value!r}") from exc


def _dataset_container(dataset: object) -> object:
    if PRECIPITATION_VARIABLE in getattr(dataset, "variables", {}):
        return dataset
    groups = getattr(dataset, "groups", {})
    grid = groups.get("Grid") if hasattr(groups, "get") else None
    if grid is not None and PRECIPITATION_VARIABLE in getattr(grid, "variables", {}):
        return grid
    raise GPMIMERGError("No top-level or Grid/precipitation variable was found in the NetCDF file.")


def read_daily_netcdf_files(paths: Sequence[str | Path]) -> dict[str, object]:
    """Read one or more GPM_3IMERGDF daily NetCDF files into a common (time, lat, lon) grid."""
    if not paths:
        raise GPMIMERGError("Provide at least one local GPM IMERG NetCDF file.")
    try:
        import netCDF4
    except ImportError as exc:
        raise GPMIMERGError(
            "NetCDF support is not installed. Install project dependencies with "
            "python -m pip install -r requirements.txt."
        ) from exc

    slices: list[tuple[date, np.ma.MaskedArray, np.ma.MaskedArray,
                       np.ma.MaskedArray, np.ma.MaskedArray]] = []
    source_files: list[dict[str, object]] = []
    warnings: list[str] = []
    reference_lat: np.ndarray | None = None
    reference_lon: np.ndarray | None = None
    saw_random_error = False
    saw_mw_precipitation = False

    for raw_path in sorted((Path(item) for item in paths), key=lambda item: item.name):
        if not raw_path.is_file():
            raise GPMIMERGError(f"Input file does not exist: {raw_path}")
        try:
            with netCDF4.Dataset(raw_path, mode="r") as dataset:
                container = _dataset_container(dataset)
                lat_var = _find_variable(container, ("lat", "latitude"))
                lon_var = _find_variable(container, ("lon", "longitude"))
                time_var = _find_variable(container, ("time",))
                precipitation_var = _find_variable(container, (PRECIPITATION_VARIABLE,))
                count_var = _find_variable(container, (COUNT_VARIABLE,))
                error_var = _find_variable(container, (RANDOM_ERROR_VARIABLE,), required=False)
                mw_var = _find_variable(container, (MW_PRECIPITATION_VARIABLE,), required=False)

                units = getattr(precipitation_var, "units", None)
                if not _unit_is_mm_per_day(units):
                    raise GPMIMERGError(
                        f"{raw_path.name}: precipitation units must be mm/day; received {units!r}."
                    )
                if error_var is not None and not _unit_is_mm_per_day(
                    getattr(error_var, "units", None)
                ):
                    raise GPMIMERGError(
                        f"{raw_path.name}: randomError units must be mm/day."
                    )
                if mw_var is not None and not _unit_is_mm_per_day(getattr(mw_var, "units", None)):
                    raise GPMIMERGError(
                        f"{raw_path.name}: MWprecipitation units must be mm/day."
                    )

                lat = np.asarray(lat_var[:], dtype=np.float64).reshape(-1)
                lon = np.asarray(lon_var[:], dtype=np.float64).reshape(-1)
                if lat.size == 0 or lon.size == 0:
                    raise GPMIMERGError(f"{raw_path.name}: empty latitude/longitude coordinates.")
                if (not np.all(np.isfinite(lat)) or not np.all(np.isfinite(lon))
                        or np.any(np.abs(lat) > 90) or np.any(np.abs(lon) > 180)):
                    raise GPMIMERGError(f"{raw_path.name}: invalid geographic coordinates.")
                if np.unique(lat).size != lat.size or np.unique(lon).size != lon.size:
                    raise GPMIMERGError(f"{raw_path.name}: duplicate coordinate values.")

                if reference_lat is None:
                    reference_lat, reference_lon = lat, lon
                elif (lat.shape != reference_lat.shape or lon.shape != reference_lon.shape
                      or not np.allclose(lat, reference_lat, rtol=0, atol=1e-7)
                      or not np.allclose(lon, reference_lon, rtol=0, atol=1e-7)):
                    raise GPMIMERGError(
                        "IMERG files do not share an identical latitude/longitude grid; "
                        "regrid explicitly before combining them."
                    )

                if len(getattr(lat_var, "dimensions", ())) != 1 or len(getattr(lon_var, "dimensions", ())) != 1:
                    raise GPMIMERGError("Latitude and longitude coordinates must be one-dimensional.")
                if len(getattr(time_var, "dimensions", ())) != 1:
                    raise GPMIMERGError("Time coordinate must be one-dimensional.")
                lat_dim = lat_var.dimensions[0]
                lon_dim = lon_var.dimensions[0]
                time_dim = time_var.dimensions[0]
                precipitation = _to_time_lat_lon(
                    precipitation_var, time_dim, lat_dim, lon_dim
                )
                counts = _to_time_lat_lon(count_var, time_dim, lat_dim, lon_dim)
                if precipitation.shape != counts.shape:
                    raise GPMIMERGError(f"{raw_path.name}: precipitation/count grid shapes differ.")
                errors = (
                    _to_time_lat_lon(error_var, time_dim, lat_dim, lon_dim)
                    if error_var is not None else None
                )
                microwave = (
                    _to_time_lat_lon(mw_var, time_dim, lat_dim, lon_dim)
                    if mw_var is not None else None
                )
                if errors is not None and errors.shape != precipitation.shape:
                    raise GPMIMERGError(f"{raw_path.name}: randomError grid shape differs.")
                if microwave is not None and microwave.shape != precipitation.shape:
                    raise GPMIMERGError(f"{raw_path.name}: MWprecipitation grid shape differs.")

                time_units = getattr(time_var, "units", None)
                if not time_units:
                    raise GPMIMERGError(f"{raw_path.name}: time coordinate has no CF units.")
                calendar_name = getattr(time_var, "calendar", "standard")
                try:
                    decoded_times = netCDF4.num2date(
                        np.asarray(time_var[:]).reshape(-1),
                        units=time_units,
                        calendar=calendar_name,
                        only_use_cftime_datetimes=False,
                    )
                except TypeError:
                    decoded_times = netCDF4.num2date(
                        np.asarray(time_var[:]).reshape(-1),
                        units=time_units,
                        calendar=calendar_name,
                    )
                dates = [_date_from_cf(value) for value in np.asarray(decoded_times).reshape(-1)]
                if len(dates) != precipitation.shape[0]:
                    raise GPMIMERGError(f"{raw_path.name}: time coordinate and data length differ.")

                for index, observation_date in enumerate(dates):
                    error_slice = (
                        errors[index] if errors is not None
                        else np.ma.masked_all(precipitation.shape[1:], dtype=np.float64)
                    )
                    microwave_slice = (
                        microwave[index] if microwave is not None
                        else np.ma.masked_all(precipitation.shape[1:], dtype=np.float64)
                    )
                    slices.append((
                        observation_date, precipitation[index], counts[index],
                        error_slice, microwave_slice,
                    ))
                saw_random_error = saw_random_error or errors is not None
                saw_mw_precipitation = saw_mw_precipitation or microwave is not None

                attrs = {
                    name: _json_safe(dataset.getncattr(name))
                    for name in dataset.ncattrs()
                }
                short_name = attrs.get("ShortName") or attrs.get("short_name")
                version = attrs.get("VersionID") or attrs.get("version") or attrs.get("Version")
                if short_name and str(short_name).upper() != GPM_SHORT_NAME:
                    raise GPMIMERGError(
                        f"{raw_path.name}: expected {GPM_SHORT_NAME}, received {short_name!r}."
                    )
                if version and not str(version).upper().startswith("07"):
                    raise GPMIMERGError(
                        f"{raw_path.name}: expected IMERG V07, received {version!r}."
                    )
                if not short_name:
                    warnings.append(
                        f"{raw_path.name}: global ShortName metadata is absent; product identity "
                        "must be confirmed from the GES DISC download record."
                    )
                if not version:
                    warnings.append(
                        f"{raw_path.name}: global version metadata is absent; V07 identity "
                        "must be confirmed from the GES DISC download record."
                    )
                source_files.append({
                    "file_name": raw_path.name,
                    "size_bytes": raw_path.stat().st_size,
                    "sha256": _sha256(raw_path),
                    "global_attributes": attrs,
                    "precipitation_units": str(units),
                    "time_units": str(time_units),
                    "calendar": str(calendar_name),
                })
        except GPMIMERGError:
            raise
        except Exception as exc:
            raise GPMIMERGError(f"Could not read {raw_path.name}: {exc}") from exc

    if not slices or reference_lat is None or reference_lon is None:
        raise GPMIMERGError("No daily observations were found in the supplied files.")
    slices.sort(key=lambda item: item[0])
    dates = [item[0] for item in slices]
    if len(set(dates)) != len(dates):
        raise GPMIMERGError("Duplicate UTC calendar days were found across the supplied files.")

    return {
        "dates": dates,
        "latitudes": reference_lat,
        "longitudes": reference_lon,
        "precipitation": np.ma.stack([item[1] for item in slices]),
        "precipitation_count": np.ma.stack([item[2] for item in slices]),
        "random_error": (
            np.ma.stack([item[3] for item in slices]) if saw_random_error else None
        ),
        "mw_precipitation": (
            np.ma.stack([item[4] for item in slices]) if saw_mw_precipitation else None
        ),
        "source_files": source_files,
        "warnings": warnings,
    }


def quality_screen_daily_arrays(
    precipitation: np.ndarray,
    precipitation_count: np.ndarray,
    random_error: np.ndarray | None = None,
    minimum_valid_half_hours: int | None = None,
) -> dict[str, object]:
    """Apply transparent validity/completeness checks; do not invent a cloud mask."""
    precip = np.ma.asarray(precipitation, dtype=np.float64)
    counts = np.ma.asarray(precipitation_count, dtype=np.float64)
    if precip.ndim != 3 or counts.shape != precip.shape:
        raise ValueError("IMERG precipitation and count arrays must share (time, lat, lon) shape.")
    if minimum_valid_half_hours is not None and not 1 <= minimum_valid_half_hours <= 48:
        raise ValueError("minimum_valid_half_hours must be between 1 and 48.")

    precip_data = np.asarray(precip.filled(np.nan), dtype=np.float64)
    count_data = np.asarray(counts.filled(np.nan), dtype=np.float64)
    count_is_integer = np.isfinite(count_data) & (
        np.abs(count_data - np.rint(count_data)) < 1e-8
    )
    valid_precip = (
        ~np.ma.getmaskarray(precip)
        & np.isfinite(precip_data)
        & (precip_data >= 0)
    )
    valid_count = (
        ~np.ma.getmaskarray(counts)
        & count_is_integer
        & (count_data >= 1)
        & (count_data <= 48)
    )
    valid = valid_precip & valid_count
    below_threshold = np.zeros(valid.shape, dtype=bool)
    if minimum_valid_half_hours is not None:
        below_threshold = valid & (count_data < minimum_valid_half_hours)
        valid &= ~below_threshold

    error_data = None
    error_valid = None
    if random_error is not None:
        errors = np.ma.asarray(random_error, dtype=np.float64)
        if errors.shape != precip.shape:
            raise ValueError("IMERG randomError array must share the precipitation grid.")
        error_data = np.asarray(errors.filled(np.nan), dtype=np.float64)
        error_valid = (
            ~np.ma.getmaskarray(errors)
            & np.isfinite(error_data)
            & (error_data >= 0)
        )

    total = int(valid.size)
    valid_count_total = int(valid.sum())
    return {
        "precipitation_mm_day": np.where(valid, precip_data, np.nan),
        "valid_mask": valid,
        "precipitation_count": count_data,
        "random_error_mm_day": (
            np.where(error_valid, error_data, np.nan) if error_valid is not None else None
        ),
        "random_error_valid_mask": error_valid,
        "qc_summary": {
            "total_grid_day_cells": total,
            "valid_grid_day_cells": valid_count_total,
            "valid_fraction": valid_count_total / total if total else 0.0,
            "invalid_or_missing_precipitation": int((~valid_precip).sum()),
            "invalid_or_missing_half_hour_count": int((~valid_count).sum()),
            "valid_cells_below_user_threshold": int(below_threshold.sum()),
            "zero_precipitation_is_valid_when_sample_count_is_positive": True,
            "random_error_is_uncertainty_not_a_precipitation_rejection_mask": True,
            "cloud_mask_applied": False,
            "minimum_valid_half_hours": minimum_valid_half_hours,
        },
    }


def annual_grid_summaries(
    dates: Sequence[date],
    precipitation_mm_day: np.ndarray,
    valid_mask: np.ndarray,
    precipitation_count: np.ndarray | None = None,
) -> list[dict[str, object]]:
    """Summarize observed daily amounts by pixel; emit annual totals only for complete years."""
    values = np.asarray(precipitation_mm_day, dtype=np.float64)
    valid = np.asarray(valid_mask, dtype=bool)
    if values.ndim != 3 or valid.shape != values.shape or values.shape[0] != len(dates):
        raise ValueError("Dates, precipitation and valid mask must share (time, lat, lon) shape.")
    if len(set(dates)) != len(dates):
        raise ValueError("Duplicate dates cannot be aggregated.")
    counts = None
    if precipitation_count is not None:
        counts = np.asarray(precipitation_count, dtype=np.float64)
        if counts.shape != values.shape:
            raise ValueError("Precipitation count array must share the data grid.")

    years = sorted({item.year for item in dates})
    rows: list[dict[str, object]] = []
    for year in years:
        indices = [index for index, item in enumerate(dates) if item.year == year]
        expected_days = 366 if calendar.isleap(year) else 365
        year_valid = valid[indices]
        valid_days = year_valid.sum(axis=0)
        observed_sum = np.where(year_valid, values[indices], 0.0).sum(axis=0)
        mean_count = (
            np.where(year_valid, counts[indices], np.nan)
            if counts is not None else None
        )
        for row_index, col_index in np.ndindex(values.shape[1:]):
            day_count = int(valid_days[row_index, col_index])
            if day_count == 0:
                continue
            complete = day_count == expected_days
            record: dict[str, object] = {
                "year": year,
                "row": row_index,
                "column": col_index,
                "valid_days": day_count,
                "expected_days": expected_days,
                "daily_coverage_fraction": day_count / expected_days,
                "observed_day_sum_mm": float(observed_sum[row_index, col_index]),
                "annual_total_mm": (
                    float(observed_sum[row_index, col_index]) if complete else None
                ),
                "analysis_status": "complete_calendar_year" if complete else "incomplete_calendar_year",
            }
            if mean_count is not None:
                finite_counts = mean_count[:, row_index, col_index]
                finite_counts = finite_counts[np.isfinite(finite_counts)]
                record["mean_valid_half_hours"] = (
                    float(np.mean(finite_counts)) if finite_counts.size else None
                )
            rows.append(record)
    return rows


def analyze_local_files(
    paths: Sequence[str | Path],
    output_dir: str | Path,
    minimum_valid_half_hours: int | None = None,
) -> dict[str, object]:
    data = read_daily_netcdf_files(paths)
    screened = quality_screen_daily_arrays(
        data["precipitation"],
        data["precipitation_count"],
        data["random_error"],
        minimum_valid_half_hours,
    )
    annual_rows = annual_grid_summaries(
        data["dates"],
        screened["precipitation_mm_day"],
        screened["valid_mask"],
        screened["precipitation_count"],
    )

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    annual_csv = destination / "gpm_annual_grid.csv"
    fields = [
        "year", "row", "column", "latitude", "longitude", "valid_days",
        "expected_days", "daily_coverage_fraction", "observed_day_sum_mm",
        "annual_total_mm", "mean_valid_half_hours", "analysis_status",
    ]
    with annual_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in annual_rows:
            writer.writerow({
                **row,
                "latitude": float(data["latitudes"][int(row["row"])]),
                "longitude": float(data["longitudes"][int(row["column"])]),
            })

    dates = data["dates"]
    report: dict[str, object] = {
        "status": "processed_local_files",
        "product": GPM_PRODUCT_NAME,
        "short_name": GPM_SHORT_NAME,
        "version": GPM_VERSION,
        "doi": GPM_DOI,
        "dataset_url": GPM_DATASET_URL,
        "temporal_resolution": "daily UTC day (00:00–24:00)",
        "spatial_resolution": "0.1 degree",
        "primary_variable": PRECIPITATION_VARIABLE,
        "primary_units": DAILY_UNITS,
        "daily_value_definition": (
            "Daily mean precipitation rate: mean of valid half-hourly rates multiplied by 24; "
            "the value is expressed in mm/day and summed across days only for complete calendar years."
        ),
        "quality_policy": (
            "A grid-day is valid when precipitation is finite and non-negative and "
            "precipitation_cnt is an integer from 1 to 48. An optional user-selected minimum "
            "half-hour count can make this stricter. No optical cloud mask is applied."
        ),
        "uncertainty_policy": (
            "randomError is retained as an uncertainty variable and does not independently "
            "reject precipitation. MWprecipitation is a distinct microwave-only estimate and "
            "is not substituted for the combined precipitation variable."
        ),
        "date_range_utc": [min(dates).isoformat(), max(dates).isoformat()],
        "daily_records": len(dates),
        "grid": {
            "latitude_count": int(len(data["latitudes"])),
            "longitude_count": int(len(data["longitudes"])),
            "latitude_min": float(np.min(data["latitudes"])),
            "latitude_max": float(np.max(data["latitudes"])),
            "longitude_min": float(np.min(data["longitudes"])),
            "longitude_max": float(np.max(data["longitudes"])),
            "coordinate_reference": "geographic latitude/longitude; coordinates retained from source NetCDF",
        },
        "qc": screened["qc_summary"],
        "annual_grid_rows": len(annual_rows),
        "complete_annual_pixel_rows": sum(
            row["analysis_status"] == "complete_calendar_year" for row in annual_rows
        ),
        "annual_grid_csv": str(annual_csv),
        "source_files": data["source_files"],
        "warnings": data["warnings"] + [
            "Incomplete calendar years are not extrapolated; annual_total_mm is null unless every calendar day has a valid grid-cell value.",
            "The daily sample count is a completeness diagnostic, not a standalone accuracy guarantee.",
            "IMERG skill can be lower over complex terrain; changing satellite constellation can affect long-term homogeneity.",
            "No GPM-versus-POWER comparison or trend inference is performed by this ingestion stage.",
        ],
        "remote_download_attempted": False,
    }
    report_path = destination / "gpm_report.json"
    report["report_json"] = str(report_path)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Earthdata access or ingest local NASA GPM IMERG Final Daily V07 NetCDF subsets."
    )
    parser.add_argument("--input", nargs="*", default=None, help="Local GPM IMERG daily NetCDF files.")
    parser.add_argument("--input-dir", type=Path, help="Directory containing local .nc4/.nc NetCDF files.")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/gpm_imerg"))
    parser.add_argument(
        "--minimum-valid-half-hours", type=int, default=None,
        help="Optional stricter completeness screen (1-48); default accepts any positive count.",
    )
    parser.add_argument("--status", action="store_true", help="Only report Earthdata credential presence.")
    args = parser.parse_args(argv)

    if args.status or (not args.input and args.input_dir is None):
        status = build_access_status()
        print(json.dumps(status, indent=2))
        return 0

    inputs = [Path(item) for item in (args.input or [])]
    if args.input_dir is not None:
        if not args.input_dir.is_dir():
            raise SystemExit(f"Input directory does not exist: {args.input_dir}")
        inputs.extend(sorted(args.input_dir.glob("*.nc4")))
        inputs.extend(sorted(args.input_dir.glob("*.nc")))
    inputs = list(dict.fromkeys(inputs))
    if not inputs:
        raise SystemExit("No .nc4 or .nc input files were found.")
    try:
        report = analyze_local_files(
            inputs, args.output_dir, args.minimum_valid_half_hours
        )
    except (GPMIMERGError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({
        "status": report["status"],
        "daily_records": report["daily_records"],
        "qc": report["qc"],
        "annual_grid_rows": report["annual_grid_rows"],
        "complete_annual_pixel_rows": report["complete_annual_pixel_rows"],
        "report_json": report["report_json"],
        "annual_grid_csv": report["annual_grid_csv"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
