"""Non-parametric trend statistics for environmental time series.

Implements Mann-Kendall and Sen's slope without third-party dependencies.
P-values are two-sided normal approximations; serial correlation is not
corrected, so users must inspect dependence before inferential interpretation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, permutations
from math import erfc, floor, sqrt
from statistics import NormalDist, median
from typing import Iterable


def _mk_components(values: list[float]) -> tuple[int, float, int]:
    n = len(values)
    score = sum((values[j] > values[i]) - (values[j] < values[i])
                for i, j in combinations(range(n), 2))
    ties = Counter(values)
    tie_term = sum(t * (t - 1) * (2 * t + 5) for t in ties.values() if t > 1)
    variance = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0
    return int(score), variance, n * (n - 1) // 2


def _sen_slope_ci_95(
    slopes: list[float], variance: float,
) -> tuple[float | None, float | None, str | None]:
    """Nominal 95% Sen interval from MK variance inversion (iid assumption)."""
    if not slopes:
        return None, None, None
    ordered = sorted(float(value) for value in slopes)
    if variance <= 0:
        if all(value == 0.0 for value in ordered):
            return 0.0, 0.0, "Degenerate constant series; every pairwise Sen slope is exactly zero"
        return None, None, None
    z_critical = NormalDist().inv_cdf(0.975)
    rank_width = z_critical * sqrt(variance)
    offset = floor((len(ordered) - rank_width) / 2.0 + 0.5)
    offset = max(0, min(offset, (len(ordered) - 1) // 2))
    return (
        ordered[offset], ordered[len(ordered) - offset - 1],
        "Mann-Kendall variance inversion; normal approximation; nominal 95%; assumes independent observations",
    )


def _mk_result(
    score: int, variance: float, comparisons_count: int, n: int,
    slope: float | None, slopes: list[float], method: str,
) -> dict[str, float | int | str | None | bool]:
    if n < 3 or comparisons_count == 0:
        z = p_value = tau = None
    elif variance <= 0:
        # A zero tie-corrected variance with actual comparisons is a constant series.
        z, p_value, tau = 0.0, 1.0, 0.0
    else:
        if score > 0:
            z = (score - 1) / sqrt(variance)
        elif score < 0:
            z = (score + 1) / sqrt(variance)
        else:
            z = 0.0
        p_value = erfc(abs(z) / sqrt(2.0))
        tau = score / comparisons_count
    if n < 3 or comparisons_count == 0:
        ci_lower = ci_upper = ci_method = None
    else:
        ci_lower, ci_upper, ci_method = _sen_slope_ci_95(slopes, variance)
    return {
        "n": n, "kendall_s": score, "kendall_tau": tau,
        "z": z, "p_value_two_sided": p_value,
        "sen_slope_per_year": slope,
        "sen_slope_ci_95_lower_per_year": ci_lower,
        "sen_slope_ci_95_upper_per_year": ci_upper,
        "sen_slope_ci_95_method": ci_method,
        "method": method, "serial_correlation_adjusted": False,
    }


def mann_kendall(year_values: Iterable[tuple[float, float]]) -> dict[str, object]:
    """Mann-Kendall test and Sen slope for (time_in_years, value) pairs."""
    points = sorted((float(x), float(y)) for x, y in year_values)
    if any(not (-float("inf") < x < float("inf") and -float("inf") < y < float("inf"))
           for x, y in points):
        raise ValueError("Trend inputs must be finite.")
    if len({x for x, _ in points}) != len(points):
        raise ValueError("Trend time coordinates must be unique.")
    values = [y for _, y in points]
    score, variance, comparisons_count = _mk_components(values)
    slopes = [
        (points[j][1] - points[i][1]) / (points[j][0] - points[i][0])
        for i, j in combinations(range(len(points)), 2)
    ]
    slope = float(median(slopes)) if slopes else None
    result = _mk_result(score, variance, comparisons_count, len(points), slope, slopes,
                        "Mann-Kendall normal approximation")
    if 3 <= len(values) <= 8:
        permutation_scores = [
            _mk_components(list(candidate))[0]
            for candidate in set(permutations(values))
        ]
        result["p_value_two_sided"] = (
            sum(abs(candidate) >= abs(score) for candidate in permutation_scores)
            / len(permutation_scores)
        )
        result["method"] = "Exact permutation Mann-Kendall"
    return result


def seasonal_mann_kendall(
    date_values: Iterable[tuple[str, float]],
    aggregation: str = "mean",
) -> dict[str, object]:
    """Seasonal MK on one monthly aggregate per year/month.

    Daily values are aggregated to year-month means (temperature) or totals
    (precipitation), then comparisons are made only within the same month
    across years. The test does not correct for serial dependence between years.
    """
    if aggregation not in {"mean", "sum"}:
        raise ValueError("aggregation must be 'mean' or 'sum'")
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for date, raw in date_values:
        if len(date) != 8 or not date.isdigit():
            raise ValueError(f"Invalid date key: {date!r}")
        year, month = int(date[:4]), int(date[4:6])
        if not 1 <= month <= 12:
            raise ValueError(f"Invalid month in date key: {date!r}")
        value = float(raw)
        if not (-float("inf") < value < float("inf")):
            continue
        buckets[(year, month)].append(value)

    monthly = {
        key: (sum(values) / len(values) if aggregation == "mean" else sum(values))
        for key, values in buckets.items()
    }
    total_score = 0
    total_variance = 0.0
    total_comparisons = 0
    slopes: list[float] = []
    years_used: set[int] = set()
    months_used: set[int] = set()
    for month in range(1, 13):
        series = sorted((year, value) for (year, m), value in monthly.items() if m == month)
        if len(series) < 2:
            continue
        values = [value for _, value in series]
        score, variance, comparisons_count = _mk_components(values)
        total_score += score
        total_variance += variance
        total_comparisons += comparisons_count
        years_used.update(year for year, _ in series)
        months_used.add(month)
        slopes.extend(
            (series[j][1] - series[i][1]) / (series[j][0] - series[i][0])
            for i, j in combinations(range(len(series)), 2)
        )

    slope = float(median(slopes)) if slopes else None
    return _mk_result(
        total_score, total_variance, total_comparisons, len(monthly), slope, slopes,
        f"Seasonal Mann-Kendall normal approximation ({aggregation} by year-month; "
        f"{len(months_used)} calendar months)",
    ) | {
        "years": len(years_used),
        "calendar_months": len(months_used),
        "monthly_observations": len(monthly),
        "aggregation": aggregation,
    }
