"""Robust anomaly screening for numeric environmental time series."""
from __future__ import annotations

from math import isfinite
from statistics import median
from typing import Iterable


def robust_anomalies(
    date_values: Iterable[tuple[str, float]],
    threshold: float = 3.5,
) -> list[dict[str, object]]:
    """Return modified-z scores using median absolute deviation (MAD).

    A constant or zero-MAD series cannot support a meaningful robust z-score;
    those observations receive score 0 and are not flagged.
    """
    if threshold <= 0 or not isfinite(threshold):
        raise ValueError("threshold must be a positive finite number.")
    points = [(str(date), float(value)) for date, value in date_values]
    if any(not isfinite(value) for _, value in points):
        raise ValueError("Anomaly input values must be finite.")
    if not points:
        return []
    center = median([value for _, value in points])
    mad = median([abs(value - center) for _, value in points])
    output = []
    for date, value in points:
        if mad == 0:
            score = 0.0 if value == center else None
            is_anomaly = value != center
        else:
            score = 0.6744897501960817 * (value - center) / mad
            is_anomaly = abs(score) > threshold
        output.append({
            "date": date,
            "value": value,
            "median": center,
            "mad": mad,
            "modified_z_score": score,
            "is_anomaly": is_anomaly,
            "threshold": threshold,
        })
    return output
