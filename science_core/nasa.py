"""Small, explicit clients for public NASA POWER and GIBS endpoints."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


POWER_ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
GIBS_ENDPOINT = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
MODIS_TRUE_COLOR = "MODIS_Terra_CorrectedReflectance_TrueColor"


def _download(url: str, timeout: int = 90, attempts: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "NASA-Universal-Science-Core/0.2"})
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                if not data:
                    raise RuntimeError(f"Empty response from {url}")
                return data
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                delay = min(2 ** attempt, 8)
                print(f"NASA request attempt {attempt}/{attempts} failed; retrying in {delay}s: {exc}", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"Could not download NASA resource after {attempts} attempts: {url}: {last_error}") from last_error


def power_url(latitude: float, longitude: float, start: str, end: str) -> str:
    for value in (start, end):
        datetime.strptime(value, "%Y%m%d")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Latitude/longitude are outside valid geographic ranges.")
    params = {
        "parameters": "T2M,PRECTOTCORR",
        "community": "AG",
        "longitude": str(longitude),
        "latitude": str(latitude),
        "start": start,
        "end": end,
        "format": "JSON",
        "time-standard": "UTC",
    }
    return POWER_ENDPOINT + "?" + urllib.parse.urlencode(params)


def fetch_power(latitude: float, longitude: float, start: str, end: str) -> tuple[dict, str]:
    url = power_url(latitude, longitude, start, end)
    raw = _download(url)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("NASA POWER returned invalid JSON.") from exc
    return payload, url


def gibs_image_url(date: str, bbox: tuple[float, float, float, float], width: int = 512, height: int = 512) -> str:
    datetime.strptime(date, "%Y-%m-%d")
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid EPSG:4326 bounding box.")
    if not (1 <= width <= 2048 and 1 <= height <= 2048):
        raise ValueError("Image dimensions must be between 1 and 2048.")
    params = {
        "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap",
        "TIME": date, "LAYERS": MODIS_TRUE_COLOR, "STYLES": "",
        "SRS": "EPSG:4326", "BBOX": ",".join(map(str, bbox)),
        "WIDTH": str(width), "HEIGHT": str(height), "FORMAT": "image/png",
    }
    return GIBS_ENDPOINT + "?" + urllib.parse.urlencode(params)


def fetch_gibs_image(date: str, bbox: tuple[float, float, float, float], output: Path, width: int = 512, height: int = 512) -> tuple[str, int]:
    url = gibs_image_url(date, bbox, width, height)
    data = _download(url)
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"NASA GIBS response is not a PNG image: {data[:120]!r}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return url, len(data)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
