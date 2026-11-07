"""Spatial trend analysis and multiple-testing control for raster time series."""
from __future__ import annotations

from collections import defaultdict
from math import cos, isfinite, pi
from statistics import median
from typing import Iterable, Mapping

from .trend_analysis import mann_kendall

MODIS_SINUSOIDAL_RADIUS_M = 6_371_007.181


def benjamini_yekutieli(p_values: Iterable[float | None]) -> list[float | None]:
    """Return BY-adjusted q-values, preserving input order and missing entries.

    BY controls false discovery rate under arbitrary dependence between tests,
    a conservative choice for spatially dependent pixels.
    """
    values = list(p_values)
    valid = []
    for index, value in enumerate(values):
        if value is None:
            continue
        p = float(value)
        if not isfinite(p) or not 0.0 <= p <= 1.0:
            raise ValueError("p-values must be finite and between 0 and 1.")
        valid.append((index, p))
    result: list[float | None] = [None] * len(values)
    m = len(valid)
    if not m:
        return result
    harmonic = sum(1.0 / rank for rank in range(1, m + 1))
    ordered = sorted(valid, key=lambda item: (item[1], item[0]))
    adjusted = [0.0] * m
    running_min = 1.0
    for position in range(m - 1, -1, -1):
        rank = position + 1
        raw = ordered[position][1] * m * harmonic / rank
        running_min = min(running_min, raw, 1.0)
        adjusted[position] = running_min
    for (index, _), q_value in zip(ordered, adjusted):
        result[index] = q_value
    return result


def annual_pixel_medians(
    observations: Iterable[tuple[int, int, str, float]],
    minimum_observations_per_year: int = 1,
) -> dict[tuple[int, int], list[tuple[int, float]]]:
    """Aggregate valid NDVI composites to annual per-pixel medians.

    Input rows are (row, column, YYYYMMDD, scaled_NDVI). Values outside the
    physical product range [-0.2, 1.0] are rejected.
    """
    if minimum_observations_per_year < 1:
        raise ValueError("minimum_observations_per_year must be at least 1.")
    buckets: dict[tuple[int, int, int], list[float]] = defaultdict(list)
    for row, col, date, raw in observations:
        if len(date) != 8 or not date.isdigit():
            raise ValueError(f"Invalid observation date: {date!r}")
        year = int(date[:4])
        value = float(raw)
        if not isfinite(value) or not -0.2 <= value <= 1.0:
            continue
        buckets[(int(row), int(col), year)].append(value)
    pixels: dict[tuple[int, int], list[tuple[int, float]]] = defaultdict(list)
    for (row, col, year), values in buckets.items():
        if len(values) >= minimum_observations_per_year:
            pixels[(row, col)].append((year, float(median(values))))
    return {key: sorted(series) for key, series in pixels.items()}


def analyze_pixel_trends(
    annual_values: Mapping[tuple[int, int], list[tuple[int, float]]],
    minimum_years: int = 15,
) -> list[dict[str, float | int | str | None]]:
    """Estimate per-pixel Mann-Kendall/Sen trends and BY-adjust spatial p-values."""
    if minimum_years < 3:
        raise ValueError("minimum_years must be at least 3.")
    provisional = []
    for (row, col), series in sorted(annual_values.items()):
        unique = {int(year): float(value) for year, value in series if isfinite(float(value))}
        ordered = sorted(unique.items())
        if len(ordered) < minimum_years:
            continue
        result = mann_kendall([(float(year), value) for year, value in ordered])
        provisional.append({
            "row": int(row),
            "column": int(col),
            "years": len(ordered),
            "first_year": ordered[0][0],
            "last_year": ordered[-1][0],
            "sen_slope_ndvi_per_year": result["sen_slope_per_year"],
            "kendall_tau": result["kendall_tau"],
            "p_value": result["p_value_two_sided"],
            "trend_method": result["method"],
        })
    q_values = benjamini_yekutieli([item["p_value"] for item in provisional])
    for item, q_value in zip(provisional, q_values):
        item["q_value_by"] = q_value
        item["by_q_le_0_05_temporal_uncorrected"] = q_value is not None and q_value <= 0.05
        item["serial_correlation_adjusted"] = False
    return provisional


def sinusoidal_pixel_center(
    latitude: float,
    longitude: float,
    row: int,
    column: int,
    nrows: int,
    ncols: int,
    cellsize_m: float,
) -> tuple[float, float]:
    """Convert row/column offset to lon/lat using the MODIS sinusoidal grid.

    The requested center coordinate is treated as the center of the middle
    pixel. Confirm this convention against the returned source metadata before
    treating the resulting coordinates as high-precision geolocation.
    """
    if nrows < 1 or ncols < 1 or not (0 <= row < nrows and 0 <= column < ncols):
        raise ValueError("Pixel indices must lie inside a positive-sized grid.")
    if not isfinite(cellsize_m) or cellsize_m <= 0:
        raise ValueError("cellsize_m must be positive and finite.")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Invalid geographic center.")
    lat0 = latitude * pi / 180.0
    lon0 = longitude * pi / 180.0
    radius = MODIS_SINUSOIDAL_RADIUS_M
    x0 = radius * lon0 * cos(lat0)
    y0 = radius * lat0
    x = x0 + (column - (ncols - 1) / 2.0) * cellsize_m
    y = y0 + ((nrows - 1) / 2.0 - row) * cellsize_m
    lat = y / radius
    if abs(cos(lat)) < 1e-12:
        raise ValueError("Cannot invert sinusoidal coordinates near the poles.")
    lon = x / (radius * cos(lat))
    return lon * 180.0 / pi, lat * 180.0 / pi


def sinusoidal_pixel_center_from_origin(
    xllcorner_m: float,
    yllcorner_m: float,
    row: int,
    column: int,
    nrows: int,
    ncols: int,
    cellsize_m: float,
) -> tuple[float, float]:
    """Convert a MODIS sinusoidal raster row/column using source grid origin.

    xllcorner_m and yllcorner_m are the lower-left outer-corner coordinates
    supplied by the ORNL DAAC subset response. Row zero is the northernmost row.
    """
    if nrows < 1 or ncols < 1 or not (0 <= row < nrows and 0 <= column < ncols):
        raise ValueError("Pixel indices must lie inside a positive-sized grid.")
    if not all(isfinite(v) for v in (xllcorner_m, yllcorner_m, cellsize_m)) or cellsize_m <= 0:
        raise ValueError("Grid origin and cell size must be finite; cell size must be positive.")
    radius = MODIS_SINUSOIDAL_RADIUS_M
    x = xllcorner_m + (column + 0.5) * cellsize_m
    y = yllcorner_m + (nrows - row - 0.5) * cellsize_m
    latitude_rad = y / radius
    if abs(cos(latitude_rad)) < 1e-12:
        raise ValueError("Cannot invert sinusoidal coordinates near the poles.")
    longitude_rad = x / (radius * cos(latitude_rad))
    return longitude_rad * 180.0 / pi, latitude_rad * 180.0 / pi


def summarize_fixed_annual_panel(
    annual_values: Mapping[tuple[int, int], list[tuple[int, float]]],
    start_year: int,
    end_year: int,
) -> tuple[list[dict[str, float | int | None]], int]:
    """Summarize only pixels with valid annual medians in every requested year.

    This fixed spatial cohort prevents annual aggregate changes from being
    driven merely by a changing number/location of pixels with valid data.
    """
    if start_year > end_year:
        raise ValueError("start_year must not be after end_year.")
    years = list(range(start_year, end_year + 1))
    pixel_series = {
        pixel: {int(year): float(value) for year, value in series}
        for pixel, series in annual_values.items()
    }
    fixed_pixels = [
        pixel for pixel, values in pixel_series.items()
        if all(year in values for year in years)
    ]
    rows = []
    for year in years:
        values = [pixel_series[pixel][year] for pixel in fixed_pixels]
        rows.append({
            "year": year,
            "fixed_panel_median": float(median(values)) if values else None,
            "fixed_panel_mean": float(sum(values) / len(values)) if values else None,
            "fixed_panel_pixels": len(values),
        })
    return rows, len(fixed_pixels)


def select_complete_year_range(
    composite_dates: Iterable[str],
    minimum_composites_per_year: int = 11,
    minimum_years: int = 15,
) -> tuple[int, int, dict[int, int]]:
    """Find the longest consecutive period meeting annual composite coverage.

    Dates are selected monthly MODIS composite start dates. The chosen period
    is the longest contiguous run with at least the requested number of
    monthly composites in every year; ties prefer the more recent run.
    """
    if minimum_composites_per_year < 1:
        raise ValueError("minimum_composites_per_year must be at least 1.")
    if minimum_years < 1:
        raise ValueError("minimum_years must be at least 1.")
    counts: dict[int, int] = defaultdict(int)
    for raw_date in composite_dates:
        value = str(raw_date)
        if len(value) < 4 or not value[:4].isdigit():
            raise ValueError(f"Invalid MODIS composite date: {value!r}")
        counts[int(value[:4])] += 1
    eligible = sorted(year for year, count in counts.items()
                      if count >= minimum_composites_per_year)
    runs: list[list[int]] = []
    for year in eligible:
        if not runs or year != runs[-1][-1] + 1:
            runs.append([year])
        else:
            runs[-1].append(year)
    candidates = [run for run in runs if len(run) >= minimum_years]
    if not candidates:
        raise ValueError(
            "No contiguous MODIS period meets the requested annual composite "
            f"coverage ({minimum_composites_per_year}/year for {minimum_years} years)."
        )
    chosen = max(candidates, key=lambda run: (len(run), run[-1]))
    return chosen[0], chosen[-1], dict(sorted(counts.items()))
