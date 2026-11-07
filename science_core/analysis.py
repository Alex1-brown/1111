"""Pure analysis functions: no network access and no hidden data fabrication."""
from __future__ import annotations

from math import isfinite, sqrt
from statistics import median
from typing import Iterable, Mapping, Sequence


def valid_values(series: Mapping[str, object], fill_value: float = -999.0) -> tuple[list[tuple[str, float]], int]:
    """Return sorted valid observations and the number of rejected/missing values."""
    accepted: list[tuple[str, float]] = []
    missing = 0
    for date, raw in sorted(series.items()):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            missing += 1
            continue
        if not isfinite(value) or value == fill_value:
            missing += 1
            continue
        accepted.append((str(date), value))
    return accepted, missing


def summarize(values: Sequence[float], missing: int = 0) -> dict[str, float | int]:
    """Population descriptive statistics. Raises when no valid observations exist."""
    if not values:
        raise ValueError("No valid numeric observations.")
    if any(not isfinite(float(value)) for value in values):
        raise ValueError("Values must all be finite numbers.")
    ordered = sorted(float(value) for value in values)
    mean = sum(ordered) / len(ordered)
    variance = sum((value - mean) ** 2 for value in ordered) / len(ordered)
    return {
        "count": len(ordered),
        "missing": int(missing),
        "mean": mean,
        "min": ordered[0],
        "max": ordered[-1],
        "median": float(median(ordered)),
        "standard_deviation": sqrt(variance),
    }


def monthly_means(date_values: Iterable[tuple[str, float]]) -> list[dict[str, float | str]]:
    """Group YYYYMMDD observations by calendar month."""
    buckets: dict[str, list[float]] = {}
    for date, value in date_values:
        if len(date) < 6 or not date[:6].isdigit():
            raise ValueError(f"Invalid NASA date key: {date!r}")
        month = date[4:6]
        buckets.setdefault(month, []).append(float(value))
    return [
        {"month": month, "mean": sum(items) / len(items), "count": len(items)}
        for month, items in sorted(buckets.items())
    ]


def compare_rgb_pixels(before: bytes, after: bytes, width: int, height: int, threshold: float = 20.0) -> dict[str, float | int]:
    """Compare equal-sized packed RGB byte buffers; not a calibrated change detector."""
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive.")
    expected = width * height * 3
    if len(before) != expected or len(after) != expected:
        raise ValueError(f"Expected {expected} RGB bytes per image.")
    if threshold < 0:
        raise ValueError("Threshold must be non-negative.")

    total_difference = 0.0
    changed = 0
    for offset in range(0, expected, 3):
        difference = (
            abs(before[offset] - after[offset])
            + abs(before[offset + 1] - after[offset + 1])
            + abs(before[offset + 2] - after[offset + 2])
        ) / 3.0
        total_difference += difference
        if difference >= threshold:
            changed += 1

    pixels = width * height
    return {
        "width": width,
        "height": height,
        "pixels": pixels,
        "threshold": threshold,
        "mean_absolute_rgb_difference": total_difference / pixels,
        "changed_pixels": changed,
        "changed_pixel_percent": changed * 100.0 / pixels,
    }


def analyze_power_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Validate and summarize a NASA POWER daily JSON response."""
    try:
        header = payload["header"]
        properties = payload["properties"]
        geometry = payload["geometry"]
        parameters = properties["parameter"]  # type: ignore[index]
        fill = float(header.get("fill_value", -999.0))  # type: ignore[union-attr]
        temperature, temp_missing = valid_values(parameters["T2M"], fill)  # type: ignore[index]
        precipitation, rain_missing = valid_values(parameters["PRECTOTCORR"], fill)  # type: ignore[index]
        coords = geometry["coordinates"]  # type: ignore[index]
        if len(coords) < 3:
            raise ValueError("NASA POWER response is missing location coordinates.")
        return {
            "location": {
                "longitude": float(coords[0]),
                "latitude": float(coords[1]),
                "elevation_m": float(coords[2]),
            },
            "period": {
                "start": str(header["start"]),  # type: ignore[index]
                "end": str(header["end"]),  # type: ignore[index]
                "time_standard": str(header.get("time_standard", "unknown")),  # type: ignore[union-attr]
            },
            "source": {
                "title": str(header.get("title", "NASA POWER")),  # type: ignore[union-attr]
                "provider": str(header.get("api", {}).get("name", "NASA POWER")),  # type: ignore[union-attr]
                "upstream": list(header.get("sources", [])),  # type: ignore[union-attr]
                "fill_value": fill,
            },
            "temperature_2m_c": {
                **summarize([value for _, value in temperature], temp_missing),
                "monthly": monthly_means(temperature),
            },
            "precipitation_corrected_mm_day": {
                **summarize([value for _, value in precipitation], rain_missing),
                "sum_of_daily_values": sum(value for _, value in precipitation),
            },
        }
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError(f"Unexpected or incomplete NASA POWER response: {exc}") from exc
