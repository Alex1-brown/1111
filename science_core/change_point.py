"""Non-parametric single change-point detection for ordered numeric series."""
from __future__ import annotations

from math import exp, isfinite
from typing import Iterable


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


def pettitt_test(year_values: Iterable[tuple[int, float]]) -> dict[str, object]:
    """Estimate one abrupt distribution shift using Pettitt's rank test.

    The returned p-value is the standard large-sample approximation. It is
    not adjusted for serial autocorrelation or for searching many pixels.
    The reported change year is the first year after the maximizing split.
    """
    points = sorted((int(year), float(value)) for year, value in year_values)
    if any(not isfinite(value) for _, value in points):
        raise ValueError("Pettitt test values must be finite.")
    if len({year for year, _ in points}) != len(points):
        raise ValueError("Pettitt test requires at most one value per year.")
    n = len(points)
    if n < 4:
        return {
            "n": n, "change_point_year": None, "statistic": None,
            "p_value": None, "method": "Pettitt",
            "autocorrelation_adjusted": False,
        }
    ranks = _average_ranks([value for _, value in points])
    cumulative = 0.0
    best_statistic = -1.0
    best_split = None
    for split in range(1, n):
        cumulative += ranks[split - 1]
        statistic = abs(2.0 * cumulative - split * (n + 1))
        if statistic > best_statistic:
            best_statistic = statistic
            best_split = split
    if best_statistic <= 0 or best_split is None:
        p_value = 1.0
        change_year = None
    else:
        p_value = min(1.0, 2.0 * exp((-6.0 * best_statistic ** 2) / (n ** 3 + n ** 2)))
        change_year = points[best_split][0]
    return {
        "n": n,
        "change_point_year": change_year,
        "statistic": best_statistic,
        "p_value": p_value,
        "method": "Pettitt",
        "autocorrelation_adjusted": False,
    }
