"""Descriptive time-series analysis for paired NASA POWER daily observations."""
from __future__ import annotations

from collections import defaultdict
from math import isfinite, sqrt
from typing import Iterable


def _linear_trend(points: list[tuple[float, float]]) -> dict[str, float | int | None]:
    """Ordinary least-squares slope and R²; descriptive, not a significance test."""
    if len(points) < 2:
        return {"n": len(points), "slope_per_year": None, "r_squared": None}
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_mean, y_mean = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if denominator == 0:
        return {"n": len(points), "slope_per_year": None, "r_squared": None}
    slope = sum((x - x_mean) * (y - y_mean) for x, y in points) / denominator
    intercept = y_mean - slope * x_mean
    residual = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    total = sum((y - y_mean) ** 2 for y in ys)
    r_squared = 1.0 if total == 0 and residual == 0 else (0.0 if total == 0 else 1 - residual / total)
    return {"n": len(points), "slope_per_year": slope, "r_squared": r_squared}


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    sx = sum(v * v for v in dx)
    sy = sum(v * v for v in dy)
    if sx == 0 or sy == 0:
        return None
    return sum(x * y for x, y in zip(dx, dy)) / sqrt(sx * sy)


def analyze_power_timeseries(
    temperature: Iterable[tuple[str, float]],
    precipitation: Iterable[tuple[str, float]],
) -> dict[str, object]:
    """Build annual/monthly summaries, simple trends and paired daily correlation."""
    temp = {str(d): float(v) for d, v in temperature if isfinite(float(v))}
    rain = {str(d): float(v) for d, v in precipitation if isfinite(float(v))}
    paired_dates = sorted(set(temp) & set(rain))
    if not paired_dates:
        raise ValueError("No overlapping valid temperature and precipitation dates.")

    annual: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"temperature": [], "precipitation": []})
    monthly: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"temperature": [], "precipitation": []})
    seasonal: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"temperature": [], "precipitation": []})
    season_names = {"12": "DJF", "01": "DJF", "02": "DJF", "03": "MAM", "04": "MAM", "05": "MAM",
                    "06": "JJA", "07": "JJA", "08": "JJA", "09": "SON", "10": "SON", "11": "SON"}
    for day in paired_dates:
        year, month = day[:4], day[4:6]
        if len(day) != 8 or not year.isdigit() or not month.isdigit():
            continue
        annual[year]["temperature"].append(temp[day])
        annual[year]["precipitation"].append(rain[day])
        monthly[month]["temperature"].append(temp[day])
        monthly[month]["precipitation"].append(rain[day])
        seasonal[season_names[month]]["temperature"].append(temp[day])
        seasonal[season_names[month]]["precipitation"].append(rain[day])

    annual_rows = []
    for year in sorted(annual):
        t, p = annual[year]["temperature"], annual[year]["precipitation"]
        annual_rows.append({
            "year": int(year), "paired_days": len(t),
            "mean_temperature_c": sum(t) / len(t),
            "precipitation_total_mm": sum(p),
            "mean_daily_precipitation_mm": sum(p) / len(p),
        })
    monthly_rows = []
    for month in sorted(monthly):
        t, p = monthly[month]["temperature"], monthly[month]["precipitation"]
        monthly_rows.append({
            "month": int(month), "paired_days": len(t),
            "mean_temperature_c": sum(t) / len(t),
            "mean_daily_precipitation_mm": sum(p) / len(p),
            "precipitation_total_mm": sum(p),
        })
    seasonal_rows = []
    for season in ("DJF", "MAM", "JJA", "SON"):
        t, p = seasonal[season]["temperature"], seasonal[season]["precipitation"]
        if t:
            seasonal_rows.append({
                "season": season, "paired_days": len(t),
                "mean_temperature_c": sum(t) / len(t),
                "mean_daily_precipitation_mm": sum(p) / len(p),
            })

    return {
        "paired_valid_days": len(paired_dates),
        "paired_date_start": paired_dates[0],
        "paired_date_end": paired_dates[-1],
        "annual": annual_rows,
        "monthly_climatology": monthly_rows,
        "meteorological_seasons": seasonal_rows,
        "descriptive_linear_trends": {
            "annual_mean_temperature": _linear_trend([
                (float(row["year"]), float(row["mean_temperature_c"])) for row in annual_rows
            ]),
            "annual_precipitation_total": _linear_trend([
                (float(row["year"]), float(row["precipitation_total_mm"])) for row in annual_rows
            ]),
        },
        "daily_temperature_precipitation_pearson_r": _pearson(
            [temp[d] for d in paired_dates], [rain[d] for d in paired_dates]
        ),
        "interpretation": (
            "Descriptive analysis of a short five-year gridded dataset. Linear slopes and daily correlation "
            "are exploratory, not proof of climate change, causation, or local station accuracy. "
            "Temperature at 2 m and precipitation are different physical variables; their correlation "
            "does not validate either measurement."
        ),
    }
