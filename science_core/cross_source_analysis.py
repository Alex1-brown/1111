"""Exploratory monthly alignment of NASA POWER climate and MODIS NDVI."""
from __future__ import annotations

from collections import defaultdict
from math import isfinite, sqrt
from statistics import median
from typing import Iterable


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    dx, dy = [x - mx for x in xs], [y - my for y in ys]
    sx, sy = sum(x * x for x in dx), sum(y * y for y in dy)
    if sx == 0 or sy == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / sqrt(sx * sy)


def _average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[ordered[position][0]] = average_rank
        start = end
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    return _pearson(_average_ranks(xs), _average_ranks(ys))


def _detrend(values: list[float]) -> list[float]:
    """Remove a descriptive least-squares linear time component."""
    if len(values) < 3:
        return []
    xs = [float(index) for index in range(len(values))]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(values) / len(values)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return []
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / denominator
    intercept = y_mean - slope * x_mean
    return [value - (intercept + slope * x) for x, value in zip(xs, values)]


def analyze_monthly_cross_source(
    temperature_daily: Iterable[tuple[str, float]],
    precipitation_daily: Iterable[tuple[str, float]],
    ndvi_observations: Iterable[tuple[int, int, str, float]],
    start_year: int = 2021,
    end_year: int = 2025,
) -> dict[str, object]:
    """Align monthly POWER T2M/PRECTOTCORR with quality-screened MODIS NDVI.

    NDVI is the median of valid pixel-composite observations in each month.
    Climate anomalies are calculated relative to each calendar month's mean
    over the selected common period. Associations are exploratory, not
    cross-validation or evidence of causation.
    """
    if start_year > end_year:
        raise ValueError("start_year must not exceed end_year")
    temp_buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    rain_buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    ndvi_buckets: dict[tuple[int, int], list[float]] = defaultdict(list)

    for target, records in ((temp_buckets, temperature_daily), (rain_buckets, precipitation_daily)):
        for date, raw in records:
            if len(date) != 8 or not date.isdigit():
                raise ValueError(f"Invalid daily date key: {date!r}")
            year, month = int(date[:4]), int(date[4:6])
            value = float(raw)
            if start_year <= year <= end_year and 1 <= month <= 12 and isfinite(value):
                target[(year, month)].append(value)

    for _row, _col, date, raw in ndvi_observations:
        if len(date) != 8 or not date.isdigit():
            raise ValueError(f"Invalid NDVI date key: {date!r}")
        year, month = int(date[:4]), int(date[4:6])
        value = float(raw)
        if start_year <= year <= end_year and 1 <= month <= 12 and isfinite(value):
            ndvi_buckets[(year, month)].append(value)

    common = sorted(set(temp_buckets) & set(rain_buckets) & set(ndvi_buckets))
    rows = []
    for year, month in common:
        rows.append({
            "year": year,
            "month": month,
            "ndvi_median": float(median(ndvi_buckets[(year, month)])),
            "temperature_mean_c": sum(temp_buckets[(year, month)]) / len(temp_buckets[(year, month)]),
            "precipitation_total_mm": sum(rain_buckets[(year, month)]),
            "ndvi_observations": len(ndvi_buckets[(year, month)]),
            "temperature_daily_count": len(temp_buckets[(year, month)]),
            "precipitation_daily_count": len(rain_buckets[(year, month)]),
        })

    climatology: dict[int, dict[str, list[float]]] = defaultdict(
        lambda: {"ndvi": [], "temperature": [], "precipitation": []}
    )
    for row in rows:
        bucket = climatology[row["month"]]
        bucket["ndvi"].append(row["ndvi_median"])
        bucket["temperature"].append(row["temperature_mean_c"])
        bucket["precipitation"].append(row["precipitation_total_mm"])

    for row in rows:
        bucket = climatology[row["month"]]
        row["ndvi_anomaly"] = row["ndvi_median"] - sum(bucket["ndvi"]) / len(bucket["ndvi"])
        row["temperature_anomaly_c"] = row["temperature_mean_c"] - sum(bucket["temperature"]) / len(bucket["temperature"])
        row["precipitation_anomaly_mm"] = row["precipitation_total_mm"] - sum(bucket["precipitation"]) / len(bucket["precipitation"])

    ndvi_anomaly = [float(row["ndvi_anomaly"]) for row in rows]
    temp_anomaly = [float(row["temperature_anomaly_c"]) for row in rows]
    rain_anomaly = [float(row["precipitation_anomaly_mm"]) for row in rows]
    row_by_month = {(row["year"], row["month"]): row for row in rows}
    lagged_ndvi, lagged_rain = [], []
    for row in rows:
        year, month = int(row["year"]), int(row["month"])
        previous = (year - 1, 12) if month == 1 else (year, month - 1)
        if previous in row_by_month:
            lagged_ndvi.append(float(row["ndvi_anomaly"]))
            lagged_rain.append(float(row_by_month[previous]["precipitation_anomaly_mm"]))

    detrended_ndvi = _detrend(ndvi_anomaly)
    detrended_temp = _detrend(temp_anomaly)
    detrended_rain = _detrend(rain_anomaly)
    detrended_lagged_ndvi = _detrend(lagged_ndvi)
    detrended_lagged_rain = _detrend(lagged_rain)

    return {
        "common_months": len(rows),
        "start_year": start_year,
        "end_year": end_year,
        "monthly_rows": rows,
        "anomaly_correlations": {
            "ndvi_vs_temperature_pearson_r": _pearson(ndvi_anomaly, temp_anomaly),
            "ndvi_vs_temperature_spearman_rho": _spearman(ndvi_anomaly, temp_anomaly),
            "ndvi_vs_precipitation_pearson_r": _pearson(ndvi_anomaly, rain_anomaly),
            "ndvi_vs_precipitation_spearman_rho": _spearman(ndvi_anomaly, rain_anomaly),
            "ndvi_vs_previous_month_precipitation_pearson_r": _pearson(lagged_ndvi, lagged_rain),
            "lagged_pair_count": len(lagged_ndvi),
        },
        "detrended_anomaly_correlations": {
            "ndvi_vs_temperature_pearson_r": _pearson(detrended_ndvi, detrended_temp),
            "ndvi_vs_temperature_spearman_rho": _spearman(detrended_ndvi, detrended_temp),
            "ndvi_vs_precipitation_pearson_r": _pearson(detrended_ndvi, detrended_rain),
            "ndvi_vs_precipitation_spearman_rho": _spearman(detrended_ndvi, detrended_rain),
            "ndvi_vs_previous_month_precipitation_pearson_r": _pearson(
                detrended_lagged_ndvi, detrended_lagged_rain
            ),
        },
        "interpretation_warning": (
            "Exploratory associations only. NDVI is a 4 km x 4 km local subset median, while NASA POWER "
            "is a gridded point estimate; spatial supports differ. Monthly anomalies reduce the average "
            "seasonal cycle; the second set additionally removes a linear time component. Neither removes "
            "autocorrelation, confounding or establishes causation. These correlations do not validate either source."
        ),
    }
