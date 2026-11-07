"""Access quantitative MODIS/Terra MOD13Q1 NDVI subsets via ORNL DAAC TESViS.

The API is public and returns native MODIS pixel values plus quality bands.
Requests are limited to ten composite dates each. No Earthdata password is
required for this ORNL subset endpoint.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Callable

API_BASE = "https://modis.ornl.gov/rst/api/v1"
PRODUCT = "MOD13Q1"
NDVI_BAND = "250m_16_days_NDVI"
QUALITY_BAND = "250m_16_days_pixel_reliability"
NDVI_SCALE = 0.0001
NDVI_FILL = -3000
GOOD_QUALITY = 0


class ModisSubsetError(RuntimeError):
    """Raised when the source API returns incomplete or invalid MODIS data."""


def _extract_product_version(item: dict[str, object]) -> str | None:
    """Extract MODIS collection version from explicit metadata or granule filename."""
    explicit = item.get("version")
    if explicit:
        return str(explicit)
    filename = str(item.get("filename", ""))
    match = re.search(r"\.(\d{3})\.\d{13}(?:\.|$)", filename)
    if match:
        return match.group(1)
    match = re.search(r"\.(\d{3})\.", filename)
    return match.group(1) if match else None


def _get_json(path: str, params: dict[str, object], timeout: int = 90,
              opener: Callable[..., object] | None = None) -> dict[str, object] | list[object]:
    request = Request(
        f"{API_BASE}/{path}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "EarthSystemTrendDetective/0.1"},
    )
    open_url = opener or urlopen
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with open_url(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, (dict, list)):
                raise ModisSubsetError("ORNL API response is not a JSON object or array.")
            return payload
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise ModisSubsetError(f"ORNL API HTTP {exc.code}: {exc.reason}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 2:
                raise ModisSubsetError(f"ORNL API request failed: {exc}") from exc
        time.sleep(1.5 * (attempt + 1))
    raise ModisSubsetError(f"ORNL API request failed: {last_error}")


def fetch_mod13q1(
    latitude: float,
    longitude: float,
    start_date: str = "2001-01-01",
    end_date: str = "2025-12-31",
    radius_km: int = 2,
    *,
    expected_version: str = "061",
    opener: Callable[..., object] | None = None,
    pause_seconds: float = 0.15,
) -> dict[str, object]:
    """Download NDVI and pixel-reliability bands for one MODIS subset window.

    radius_km is the distance above/below and left/right of the center, so 2
    creates an approximately 4 km by 4 km sample window. Only reliability code
    0 (good data) is accepted into analysis observations.
    """
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Invalid geographic coordinates.")
    if not 1 <= radius_km <= 100:
        raise ValueError("radius_km must be between 1 and 100.")
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("start_date must not be after end_date.")

    common = {"latitude": latitude, "longitude": longitude}
    date_payload = _get_json(f"{PRODUCT}/dates", common, opener=opener)
    date_rows = (
        date_payload if isinstance(date_payload, list)
        else date_payload.get("dates") if isinstance(date_payload, dict)
        else None
    )
    if not isinstance(date_rows, list):
        raise ModisSubsetError("ORNL dates response has no dates list.")

    selected = []
    for row in date_rows:
        if not isinstance(row, dict):
            continue
        try:
            calendar_date = date.fromisoformat(str(row["calendar_date"]))
            modis_date = str(row["modis_date"])
        except (KeyError, ValueError) as exc:
            raise ModisSubsetError(f"Invalid date metadata from ORNL: {row!r}") from exc
        if start <= calendar_date <= end:
            selected.append({"calendar_date": calendar_date.isoformat(), "modis_date": modis_date})
    selected.sort(key=lambda item: item["calendar_date"])
    if not selected:
        raise ModisSubsetError("No MOD13Q1 composites found in the requested date range.")

    metadata = None
    raw_records: list[dict[str, object]] = []
    valid_observations: list[tuple[int, int, str, float]] = []
    quality_counts = {"good": 0, "marginal": 0, "snow_or_ice": 0, "cloudy": 0, "other_or_fill": 0}
    successful_dates: list[str] = []
    product_versions: set[str] = set()

    for offset in range(0, len(selected), 10):
        chunk = selected[offset:offset + 10]
        request_params = {
            **common,
            "startDate": chunk[0]["modis_date"],
            "endDate": chunk[-1]["modis_date"],
            "kmAboveBelow": radius_km,
            "kmLeftRight": radius_km,
        }
        subset_payload = _get_json(f"{PRODUCT}/subset", request_params, opener=opener)
        if pause_seconds:
            time.sleep(pause_seconds)
        if not isinstance(subset_payload, dict):
            raise ModisSubsetError("ORNL subset endpoint did not return a JSON object.")

        subset_items = subset_payload.get("subset", [])
        ndvi_rows = {
            str(item.get("modis_date")): item
            for item in subset_items
            if isinstance(item, dict) and item.get("band") == NDVI_BAND
        }
        quality_rows = {
            str(item.get("modis_date")): item
            for item in subset_items
            if isinstance(item, dict) and item.get("band") == QUALITY_BAND
        }
        for date_item in chunk:
            modis_date = date_item["modis_date"]
            if modis_date not in ndvi_rows or modis_date not in quality_rows:
                raise ModisSubsetError(f"Missing NDVI or QA layer for composite {modis_date}.")
            ndvi_item, qa_item = ndvi_rows[modis_date], quality_rows[modis_date]
            version = _extract_product_version(ndvi_item)
            if not version:
                raise ModisSubsetError(
                    f"Source product version is missing for {modis_date}; "
                    f"available subset fields: {sorted(ndvi_item.keys())}"
                )
            if version != expected_version:
                raise ModisSubsetError(
                    f"Expected MOD13Q1 version {expected_version}, received {version}; "
                    "refusing to mix product versions in one trend analysis."
                )
            product_versions.add(version)
            ndvi_values, qa_values = ndvi_item.get("data"), qa_item.get("data")
            if not isinstance(ndvi_values, list) or not isinstance(qa_values, list):
                raise ModisSubsetError(f"Invalid pixel arrays for composite {modis_date}.")
            if len(ndvi_values) != len(qa_values):
                raise ModisSubsetError(f"NDVI/QA pixel count mismatch for {modis_date}.")
            rows = int(subset_payload.get("nrows", 0))
            cols = int(subset_payload.get("ncols", 0))
            if rows <= 0 or cols <= 0 or len(ndvi_values) != rows * cols:
                raise ModisSubsetError(f"Unexpected grid dimensions for {modis_date}.")
            current_meta = {
                "nrows": rows,
                "ncols": cols,
                "cellsize_m": float(subset_payload["cellsize"]),
                "xllcorner_m": float(subset_payload["xllcorner"]),
                "yllcorner_m": float(subset_payload["yllcorner"]),
                "latitude": float(subset_payload["latitude"]),
                "longitude": float(subset_payload["longitude"]),
                "header": str(subset_payload.get("header", "")),
            }
            if metadata is None:
                metadata = current_meta
            elif any(metadata[key] != current_meta[key] for key in current_meta if key != "header"):
                raise ModisSubsetError("Grid metadata changed between date chunks.")
            calendar = date_item["calendar_date"]
            for index, (raw_ndvi, raw_qa) in enumerate(zip(ndvi_values, qa_values)):
                try:
                    ndvi_raw = int(raw_ndvi)
                    qa = int(raw_qa)
                except (TypeError, ValueError):
                    quality_counts["other_or_fill"] += 1
                    continue
                row, col = divmod(index, cols)
                ndvi = ndvi_raw * NDVI_SCALE
                if qa == 0:
                    quality_counts["good"] += 1
                elif qa == 1:
                    quality_counts["marginal"] += 1
                elif qa == 2:
                    quality_counts["snow_or_ice"] += 1
                elif qa == 3:
                    quality_counts["cloudy"] += 1
                else:
                    quality_counts["other_or_fill"] += 1
                raw_records.append({
                    "date": calendar, "row": row, "column": col,
                    "ndvi_raw": ndvi_raw,
                    "ndvi": ndvi if -2000 <= ndvi_raw <= 10000 else None,
                    "quality_code": qa,
                })
                if qa == GOOD_QUALITY and -2000 <= ndvi_raw <= 10000:
                    valid_observations.append((row, col, calendar.replace("-", ""), ndvi))
            successful_dates.append(calendar)

    if metadata is None or not successful_dates:
        raise ModisSubsetError("No valid MODIS subset data were downloaded.")
    return {
        "product": PRODUCT,
        "product_versions": sorted(product_versions),
        "source": "ORNL DAAC TESViS MODIS Global Subset Web Service",
        "source_api": f"{API_BASE}/{PRODUCT}",
        "doi": f"https://doi.org/10.5067/MODIS/MOD13Q1.{expected_version}",
        "ndvi_band": NDVI_BAND,
        "quality_band": QUALITY_BAND,
        "ndvi_scale_factor": NDVI_SCALE,
        "ndvi_fill_value": NDVI_FILL,
        "quality_policy": "Only pixel reliability code 0 (good data) enters analysis.",
        "start_date": successful_dates[0],
        "end_date": successful_dates[-1],
        "composite_count": len(set(successful_dates)),
        "grid": metadata,
        "quality_counts": quality_counts,
        "raw_records": raw_records,
        "valid_observations": valid_observations,
    }
