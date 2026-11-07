"""Quantitative MOD13Q1 NDVI access through the public ORNL DAAC TESViS API.

CSV subset responses preserve the MODIS granule filename, including collection
version. JSON is used once for exact grid georeferencing metadata.
"""
from __future__ import annotations

import csv
import io
import json
import re
import time
from collections import defaultdict
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


def _extract_product_version(filename: str) -> str | None:
    """Extract collection version from a MODIS granule filename."""
    match = re.search(r"\.(\d{3})\.\d{13}(?:\.|$)", filename)
    if match:
        return match.group(1)
    match = re.search(r"\.(\d{3})\.", filename)
    return match.group(1) if match else None


def _request(path: str, params: dict[str, object], accept: str,
             timeout: int, opener: Callable[..., object] | None) -> bytes:
    request = Request(
        f"{API_BASE}/{path}?{urlencode(params)}",
        headers={"Accept": accept, "User-Agent": "EarthSystemTrendDetective/0.1"},
    )
    open_url = opener or urlopen
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with open_url(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise ModisSubsetError(f"ORNL API HTTP {exc.code}: {exc.reason}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt == 2:
                raise ModisSubsetError(f"ORNL API request failed: {exc}") from exc
        time.sleep(1.5 * (attempt + 1))
    raise ModisSubsetError(f"ORNL API request failed: {last_error}")


def _get_json(path: str, params: dict[str, object], timeout: int = 90,
              opener: Callable[..., object] | None = None) -> dict[str, object] | list[object]:
    try:
        payload = json.loads(_request(path, params, "application/json", timeout, opener).decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ModisSubsetError(f"ORNL API returned invalid JSON: {exc}") from exc
    if not isinstance(payload, (dict, list)):
        raise ModisSubsetError("ORNL API response is not a JSON object or array.")
    return payload


def _get_csv(path: str, params: dict[str, object], timeout: int = 90,
             opener: Callable[..., object] | None = None) -> str:
    try:
        return _request(path, params, "text/csv", timeout, opener).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ModisSubsetError(f"ORNL API returned invalid CSV encoding: {exc}") from exc


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
    """Download NDVI and pixel-reliability bands for a local MODIS grid.

    radius_km is the distance above/below and left/right of the center, so 2
    creates an approximately 4 km by 4 km subset. Only pixel-reliability code
    0 (good data) is accepted into analysis observations. CSV is used because
    its granule filename exposes the collection version.
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

    first_date = selected[0]["modis_date"]
    metadata_payload = _get_json(f"{PRODUCT}/subset", {
        **common,
        "startDate": first_date,
        "endDate": first_date,
        "kmAboveBelow": radius_km,
        "kmLeftRight": radius_km,
    }, opener=opener)
    if not isinstance(metadata_payload, dict):
        raise ModisSubsetError("ORNL grid metadata response is not a JSON object.")
    try:
        metadata = {
            "nrows": int(metadata_payload["nrows"]),
            "ncols": int(metadata_payload["ncols"]),
            "cellsize_m": float(metadata_payload["cellsize"]),
            "xllcorner_m": float(metadata_payload["xllcorner"]),
            "yllcorner_m": float(metadata_payload["yllcorner"]),
            "latitude": float(metadata_payload["latitude"]),
            "longitude": float(metadata_payload["longitude"]),
            "header": str(metadata_payload.get("header", "")),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ModisSubsetError(f"ORNL response is missing grid georeferencing metadata: {exc}") from exc
    if metadata["nrows"] <= 0 or metadata["ncols"] <= 0 or metadata["cellsize_m"] <= 0:
        raise ModisSubsetError("ORNL returned invalid grid dimensions or cell size.")

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
        csv_payload = _get_csv(f"{PRODUCT}/subset", request_params, opener=opener)
        parsed: dict[str, dict[str, tuple[list[int | None], str]]] = defaultdict(dict)
        for row in csv.reader(io.StringIO(csv_payload)):
            if len(row) < 6:
                continue
            filename = row[0].strip()
            band = filename.rsplit(".", 1)[-1]
            if band not in {NDVI_BAND, QUALITY_BAND}:
                continue
            modis_date = row[2].strip()
            version = _extract_product_version(filename)
            if not version:
                raise ModisSubsetError(
                    f"Cannot determine collection version from ORNL granule filename: {filename!r}"
                )
            if version != expected_version:
                raise ModisSubsetError(
                    f"Expected MOD13Q1 version {expected_version}, received {version}; "
                    "refusing to mix product versions in one trend analysis."
                )
            values: list[int | None] = []
            for raw in row[5:]:
                try:
                    values.append(int(raw))
                except (TypeError, ValueError):
                    values.append(None)
            parsed[modis_date][band] = (values, version)

        for date_item in chunk:
            modis_date = date_item["modis_date"]
            bands = parsed.get(modis_date, {})
            if NDVI_BAND not in bands or QUALITY_BAND not in bands:
                raise ModisSubsetError(f"Missing NDVI or pixel-reliability CSV row for {modis_date}.")
            ndvi_values, ndvi_version = bands[NDVI_BAND]
            qa_values, qa_version = bands[QUALITY_BAND]
            if ndvi_version != qa_version:
                raise ModisSubsetError(f"NDVI and QA collection versions differ for {modis_date}.")
            expected_pixels = metadata["nrows"] * metadata["ncols"]
            if len(ndvi_values) != expected_pixels or len(qa_values) != expected_pixels:
                raise ModisSubsetError(
                    f"Pixel count mismatch for {modis_date}: expected {expected_pixels}, "
                    f"got NDVI={len(ndvi_values)}, QA={len(qa_values)}."
                )
            product_versions.add(ndvi_version)
            calendar = date_item["calendar_date"]
            for index, (ndvi_raw, qa_raw) in enumerate(zip(ndvi_values, qa_values)):
                row_index, col = divmod(index, metadata["ncols"])
                if ndvi_raw is None or qa_raw is None:
                    quality_counts["other_or_fill"] += 1
                    raw_records.append({
                        "date": calendar, "row": row_index, "column": col,
                        "ndvi_raw": ndvi_raw, "ndvi": None, "quality_code": qa_raw,
                    })
                    continue
                ndvi = ndvi_raw * NDVI_SCALE
                if qa_raw == 0:
                    quality_counts["good"] += 1
                elif qa_raw == 1:
                    quality_counts["marginal"] += 1
                elif qa_raw == 2:
                    quality_counts["snow_or_ice"] += 1
                elif qa_raw == 3:
                    quality_counts["cloudy"] += 1
                else:
                    quality_counts["other_or_fill"] += 1
                raw_records.append({
                    "date": calendar, "row": row_index, "column": col,
                    "ndvi_raw": ndvi_raw,
                    "ndvi": ndvi if -2000 <= ndvi_raw <= 10000 else None,
                    "quality_code": qa_raw,
                })
                if qa_raw == GOOD_QUALITY and -2000 <= ndvi_raw <= 10000:
                    valid_observations.append((row_index, col, calendar.replace("-", ""), ndvi))
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
