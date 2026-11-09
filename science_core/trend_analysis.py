"""Non-parametric trend statistics for environmental time series.

Implements Mann-Kendall, seasonal Mann-Kendall and Sen's slope without
third-party dependencies. For at least ten equally spaced observations, the
Hamed-Rao modified variance correction is attempted using significant
autocorrelations of detrended ranks. Short, irregular or unestimable series
retain iid reference results and are explicitly marked unadjusted. The
correction and resulting nominal confidence limits remain approximate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, permutations
from math import ceil, erfc, floor, isfinite, sqrt
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


def _average_ranks(values: list[float]) -> list[float]:
    """Return one-based average ranks, preserving ties."""
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average_rank
        start = end
    return ranks


def _hamed_rao_adjustment(
    points: list[tuple[float, float]], slope: float,
) -> dict[str, object]:
    """Estimate the Hamed-Rao (1998) MK variance factor from detrended-rank ACF.

    The correction is only attempted for at least ten equally spaced observations.
    Only rank autocorrelations exceeding the approximate 95% white-noise bound
    are included. This is an approximate variance correction, not a guarantee
    that all serial dependence has been removed.
    """
    n = len(points)
    values = [value for _, value in points]
    if n >= 2 and all(value == values[0] for value in values):
        return {"applied": False, "status": "constant_series_no_trend", "factor": None, "lags": []}
    if n < 10:
        return {"applied": False, "status": "insufficient_length_n_lt_10", "factor": None, "lags": []}

    spacings = [points[index + 1][0] - points[index][0] for index in range(n - 1)]
    if not spacings or any(
        abs(step - spacings[0]) > 1e-9 * max(1.0, abs(spacings[0]))
        for step in spacings[1:]
    ):
        return {"applied": False, "status": "irregular_time_spacing", "factor": None, "lags": []}

    residuals = [
        value - slope * (time - points[0][0])
        for time, value in points
    ]
    ranks = _average_ranks(residuals)
    mean_rank = sum(ranks) / n
    denominator = sum((rank - mean_rank) ** 2 for rank in ranks)
    if denominator <= 0:
        return {"applied": False, "status": "unestimable_detrended_rank_acf", "factor": None, "lags": []}

    threshold = NormalDist().inv_cdf(0.975) / sqrt(n)
    weighted_sum = 0.0
    selected_lags = []
    for lag in range(1, n - 2):
        rho = sum(
            (ranks[index] - mean_rank) * (ranks[index + lag] - mean_rank)
            for index in range(n - lag)
        ) / denominator
        if abs(rho) > threshold:
            weight = (n - lag) * (n - lag - 1) * (n - lag - 2)
            weighted_sum += weight * rho
            selected_lags.append({"lag": lag, "rank_autocorrelation": rho})

    factor = 1.0 + 2.0 * weighted_sum / (n * (n - 1) * (n - 2))
    if not isfinite(factor) or factor <= 0:
        return {
            "applied": False, "status": "nonpositive_variance_factor",
            "factor": factor, "lags": selected_lags,
        }
    return {"applied": True, "status": "applied", "factor": factor, "lags": selected_lags}


def _sen_slope_ci_95(
    slopes: list[float], variance: float, method: str,
) -> tuple[float | None, float | None, str | None]:
    """Return Sen slope limits using the supplied MK variance.

    The lower and upper ranks follow the standard M1/M2 Sen interval indexing.
    The interval remains approximate when the supplied variance is approximate.
    """
    if not slopes:
        return None, None, None
    ordered = sorted(float(value) for value in slopes)
    if variance <= 0:
        if all(value == 0.0 for value in ordered):
            return 0.0, 0.0, "Degenerate constant series; every pairwise Sen slope is exactly zero"
        return None, None, None
    count = len(ordered)
    width = NormalDist().inv_cdf(0.975) * sqrt(variance)
    lower_index = max(0, min(count - 1, ceil((count - width) / 2.0) - 1))
    upper_index = max(0, min(count - 1, floor((count + width) / 2.0)))
    return ordered[lower_index], ordered[upper_index], method


def _mk_result(
    score: int, iid_variance: float, comparisons_count: int, n: int,
    slope: float | None, slopes: list[float], method: str,
    serial_info: dict[str, object], adjusted_variance: float | None = None,
) -> dict[str, object]:
    if n < 3 or comparisons_count == 0:
        z_iid = p_iid = tau = None
    elif iid_variance <= 0:
        z_iid, p_iid, tau = 0.0, 1.0, 0.0
    else:
        if score > 0:
            z_iid = (score - 1) / sqrt(iid_variance)
        elif score < 0:
            z_iid = (score + 1) / sqrt(iid_variance)
        else:
            z_iid = 0.0
        p_iid = erfc(abs(z_iid) / sqrt(2.0))
        tau = score / comparisons_count

    adjusted = bool(serial_info["applied"])
    inference_variance = (
        adjusted_variance if adjusted and adjusted_variance is not None
        else iid_variance
    )
    if n < 3 or comparisons_count == 0:
        z = p_value = None
        ci_lower = ci_upper = ci_method = None
    else:
        if inference_variance <= 0:
            z, p_value = 0.0, 1.0
        else:
            if score > 0:
                z = (score - 1) / sqrt(inference_variance)
            elif score < 0:
                z = (score + 1) / sqrt(inference_variance)
            else:
                z = 0.0
            p_value = erfc(abs(z) / sqrt(2.0))
        ci_description = (
            "Hamed-Rao (1998) modified variance; detrended-rank ACF; significant lags only; "
            "normal approximation; nominal 95%"
            if adjusted else
            "Mann-Kendall variance inversion; normal approximation; nominal 95%; "
            "assumes independent observations"
        )
        ci_lower, ci_upper, ci_method = _sen_slope_ci_95(
            slopes, inference_variance, ci_description
        )

    return {
        "n": n,
        "kendall_s": score,
        "kendall_tau": tau,
        "z": z,
        "z_iid": z_iid,
        "p_value_two_sided": p_value,
        "p_value_two_sided_iid": p_iid,
        "sen_slope_per_year": slope,
        "sen_slope_ci_95_lower_per_year": ci_lower,
        "sen_slope_ci_95_upper_per_year": ci_upper,
        "sen_slope_ci_95_method": ci_method,
        "method": method,
        "serial_correlation_adjusted": adjusted,
        "serial_correlation_method": (
            "Hamed & Rao (1998) modified Mann-Kendall variance correction"
        ),
        "serial_correlation_status": serial_info["status"],
        "serial_correlation_variance_factor": (
            serial_info["factor"] if adjusted else None
        ),
        "serial_correlation_lags_used": serial_info["lags"],
    }


def mann_kendall(year_values: Iterable[tuple[float, float]]) -> dict[str, object]:
    """Mann-Kendall/Sen analysis with Hamed-Rao correction when estimable.

    Hamed-Rao variance correction is attempted for at least ten equally spaced
    observations. For shorter or irregular series the returned p-value is the
    ordinary iid result and serial_correlation_adjusted is False.
    """
    points = sorted((float(x), float(y)) for x, y in year_values)
    if any(not (isfinite(x) and isfinite(y)) for x, y in points):
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
    serial_info = (
        _hamed_rao_adjustment(points, slope)
        if slope is not None else
        {"applied": False, "status": "insufficient_length_n_lt_10", "factor": None, "lags": []}
    )
    adjusted_variance = (
        variance * float(serial_info["factor"]) if serial_info["applied"] else None
    )
    method = (
        "Hamed-Rao modified Mann-Kendall normal approximation"
        if serial_info["applied"] else
        "Mann-Kendall normal approximation"
    )
    result = _mk_result(
        score, variance, comparisons_count, len(points), slope, slopes,
        method, serial_info, adjusted_variance,
    )

    if 3 <= len(values) <= 8:
        permutation_scores = [
            _mk_components(list(candidate))[0]
            for candidate in set(permutations(values))
        ]
        exact_p = (
            sum(abs(candidate) >= abs(score) for candidate in permutation_scores)
            / len(permutation_scores)
        )
        result["p_value_two_sided"] = exact_p
        result["p_value_two_sided_iid"] = exact_p
        result["method"] = "Exact permutation Mann-Kendall"
    return result


def seasonal_mann_kendall(
    date_values: Iterable[tuple[str, float]],
    aggregation: str = "mean",
) -> dict[str, object]:
    """Seasonal MK with within-calendar-month Hamed-Rao variance correction.

    Each calendar-month series is tested across years. The correction is used
    only when every contributing month stratum has at least ten equally spaced
    observations and estimable detrended-rank autocorrelation; otherwise the
    combined result remains iid and is explicitly marked unadjusted.
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
        if not isfinite(value):
            continue
        buckets[(year, month)].append(value)

    monthly = {
        key: (sum(values) / len(values) if aggregation == "mean" else sum(values))
        for key, values in buckets.items()
    }
    month_series = []
    all_slopes = []
    total_score = total_variance = total_comparisons = 0
    years_used: set[int] = set()
    months_used: set[int] = set()

    for month in range(1, 13):
        series = sorted(
            (year, value) for (year, current_month), value in monthly.items()
            if current_month == month
        )
        if len(series) < 2:
            continue
        values = [value for _, value in series]
        score, variance, comparisons_count = _mk_components(values)
        slopes = [
            (series[j][1] - series[i][1]) / (series[j][0] - series[i][0])
            for i, j in combinations(range(len(series)), 2)
        ]
        month_slope = float(median(slopes)) if slopes else None
        points = [(float(year), value) for year, value in series]
        serial_info = (
            _hamed_rao_adjustment(points, month_slope)
            if month_slope is not None else
            {"applied": False, "status": "insufficient_length_n_lt_10", "factor": None, "lags": []}
        )
        month_series.append((month, score, variance, comparisons_count, slopes, serial_info))
        total_score += score
        total_variance += variance
        total_comparisons += comparisons_count
        all_slopes.extend(slopes)
        years_used.update(year for year, _ in series)
        months_used.add(month)

    all_adjustable = bool(month_series) and all(item[5]["applied"] for item in month_series)
    adjusted_variance = None
    if all_adjustable:
        adjusted_variance = sum(
            variance * float(info["factor"])
            for _, _, variance, _, _, info in month_series
        )
        serial_info = {
            "applied": True,
            "status": "applied_all_calendar_month_strata",
            "factor": adjusted_variance / total_variance if total_variance > 0 else 1.0,
            "lags": [
                {
                    "month": month,
                    "lag": lag["lag"],
                    "rank_autocorrelation": lag["rank_autocorrelation"],
                }
                for month, _, _, _, _, info in month_series
                for lag in info["lags"]
            ],
        }
    else:
        serial_info = {
            "applied": False,
            "status": "not_applied_all_month_strata_not_eligible",
            "factor": None,
            "lags": [],
        }

    slope = float(median(all_slopes)) if all_slopes else None
    method = (
        f"Seasonal Hamed-Rao modified Mann-Kendall normal approximation "
        f"({aggregation} by year-month; {len(months_used)} calendar months)"
        if all_adjustable else
        f"Seasonal Mann-Kendall normal approximation "
        f"({aggregation} by year-month; {len(months_used)} calendar months)"
    )
    result = _mk_result(
        total_score, total_variance, total_comparisons, len(monthly),
        slope, all_slopes, method, serial_info, adjusted_variance,
    )
    return result | {
        "years": len(years_used),
        "calendar_months": len(months_used),
        "monthly_observations": len(monthly),
        "aggregation": aggregation,
    }
