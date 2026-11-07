"""Date sampling helpers for repeatable multi-date satellite imagery tests."""
from datetime import date, timedelta
from statistics import mean, median
from typing import Mapping, Sequence


def sample_dates(start: str, end: str, count: int = 60) -> list[str]:
    """Return exactly count evenly spaced ISO dates, including both endpoints."""
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if last <= first:
        raise ValueError("Imagery end date must be later than start date.")
    if count < 2:
        raise ValueError("At least two imagery dates are required.")
    span = (last - first).days
    if count > span + 1:
        raise ValueError("Requested image count exceeds available calendar dates.")
    dates = [(first + timedelta(days=round(i * span / (count - 1)))).isoformat() for i in range(count)]
    if len(set(dates)) != count:
        raise ValueError("Could not generate the requested number of unique imagery dates.")
    return dates


def summarize_sequence(comparisons: Sequence[Mapping[str, object]]) -> dict[str, float | int]:
    """Summarize adjacent-image RGB comparisons without implying calibrated change."""
    if not comparisons:
        raise ValueError("At least one adjacent-image comparison is required.")
    changed = [float(item["changed_pixel_percent"]) for item in comparisons]
    differences = [float(item["mean_absolute_rgb_difference"]) for item in comparisons]
    return {
        "comparison_count": len(comparisons),
        "mean_changed_pixel_percent": mean(changed),
        "median_changed_pixel_percent": median(changed),
        "mean_absolute_rgb_difference": mean(differences),
    }
