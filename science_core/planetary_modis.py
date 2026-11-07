"""NASA MOD13Q1.061 COG access through the public Microsoft Planetary Computer STAC API."""
from __future__ import annotations

import json
import math
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from typing import Callable

STAC_API = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS_API = "https://planetarycomputer.microsoft.com/api/sas/v1"
COLLECTION_ID = "modis-13Q1-061"
PRODUCT_PREFIX = "MOD13Q1."
NDVI_ASSET = "250m_16_days_NDVI"
QUALITY_ASSET = "250m_16_days_pixel_reliability"
NDVI_SCALE = 0.0001
NDVI_FILL = -3000
GOOD_QUALITY = 0
DOI = "https://doi.org/10.5067/MODIS/MOD13Q1.061"


class PlanetaryModisError(RuntimeError):
    """Raised when STAC search, signing, or MODIS COG extraction fails."""


def _http_json(
    url: str,
    params: dict[str, object] | None = None,
    *,
    opener: Callable[..., object] | None = None,
    timeout: int = 90,
) -> dict[str, object]:
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "EarthSystemTrendDetective/0.3"})
    open_url = opener or urlopen
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with open_url(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise PlanetaryModisError("Planetary Computer returned a non-object JSON response.")
            return payload
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise PlanetaryModisError(f"Planetary Computer HTTP {exc.code}: {exc.reason}") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 2:
                raise PlanetaryModisError(f"Planetary Computer request failed: {exc}") from exc
        time.sleep(1.5 * (attempt + 1))
    raise PlanetaryModisError(f"Planetary Computer request failed: {last_error}")


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = float(ring[i][0]), float(ring[i][1])
        xj, yj = float(ring[j][0]), float(ring[j][1])
        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-30) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _geometry_contains(geometry: dict[str, object], lon: float, lat: float) -> bool:
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "Polygon" and isinstance(coords, list):
        return bool(coords) and _point_in_ring(lon, lat, coords[0])
    if kind == "MultiPolygon" and isinstance(coords, list):
        return any(poly and _point_in_ring(lon, lat, poly[0]) for poly in coords)
    return False


def _search_items(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    radius_km: int,
    opener: Callable[..., object] | None,
) -> list[dict[str, object]]:
    lat_delta = radius_km / 110.574
    lon_delta = radius_km / (111.320 * max(0.01, math.cos(math.radians(latitude))))
    bbox = [
        max(-180.0, longitude - lon_delta),
        max(-90.0, latitude - lat_delta),
        min(180.0, longitude + lon_delta),
        min(90.0, latitude + lat_delta),
    ]
    params = {
        "collections": COLLECTION_ID,
        "bbox": ",".join(f"{value:.7f}" for value in bbox),
        "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
        "limit": 1000,
    }
    payload = _http_json(f"{STAC_API}/search", params, opener=opener)
    items = list(payload.get("features", []))
    next_link = next((link for link in payload.get("links", []) if link.get("rel") == "next"), None)
    while next_link:
        method = str(next_link.get("method", "GET")).upper()
        href = str(next_link["href"])
        if method == "GET":
            payload = _http_json(href, opener=opener)
        elif method == "POST":
            body = json.dumps(next_link.get("body", {})).encode("utf-8")
            request = Request(href, data=body, headers={
                "Accept": "application/geo+json", "Content-Type": "application/json",
                "User-Agent": "EarthSystemTrendDetective/0.3",
            })
            open_url = opener or urlopen
            with open_url(request, timeout=90) as response:
                payload = json.loads(response.read().decode("utf-8"))
        else:
            raise PlanetaryModisError(f"Unsupported STAC pagination method: {method}")
        items.extend(payload.get("features", []))
        next_link = next((link for link in payload.get("links", []) if link.get("rel") == "next"), None)

    selected = []
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    for item in items:
        if not isinstance(item, dict) or not str(item.get("id", "")).startswith(PRODUCT_PREFIX):
            continue
        item_id = str(item.get("id", ""))
        if ".061." not in item_id:
            raise PlanetaryModisError(f"STAC item does not identify MOD13Q1 collection 061: {item_id}")
        props = item.get("properties", {})
        if str(props.get("platform", "")).lower() != "terra":
            continue
        try:
            composite_start = date.fromisoformat(str(props["start_datetime"])[:10])
            composite_end = date.fromisoformat(str(props["end_datetime"])[:10])
        except (KeyError, ValueError):
            continue
        if composite_start < start or composite_start > end:
            continue
        geometry = item.get("geometry")
        if not isinstance(geometry, dict) or not _geometry_contains(geometry, longitude, latitude):
            continue
        item["__composite_date"] = composite_start.isoformat()
        selected.append(item)

    selected.sort(key=lambda item: str(item["__composite_date"]))
    deduplicated: dict[str, dict[str, object]] = {}
    for item in selected:
        deduplicated.setdefault(str(item["__composite_date"]), item)
    if not deduplicated:
        raise PlanetaryModisError("No Terra MOD13Q1.061 items cover the requested point and date range.")
    return list(deduplicated.values())



def _sample_one_per_month(items: list[dict[str, object]]) -> list[dict[str, object]]:
    """Select one 16-day composite per calendar month, nearest to mid-month."""
    monthly: dict[str, list[dict[str, object]]] = {}
    for item in items:
        key = str(item["__composite_date"])[:7]
        monthly.setdefault(key, []).append(item)
    selected = []
    for month in sorted(monthly):
        candidates = monthly[month]
        selected.append(min(
            candidates,
            key=lambda item: (
                abs(date.fromisoformat(str(item["__composite_date"])).day - 15),
                str(item["id"]),
            ),
        ))
    return selected


def _get_sas_token_for_href(href: str, opener: Callable[..., object] | None = None) -> str:
    """Get a SAS token for the exact Azure storage account/container of an asset."""
    parsed = urlparse(href)
    account = parsed.netloc.split(".")[0]
    path_parts = parsed.path.lstrip("/").split("/")
    if not account or len(path_parts) < 2:
        raise PlanetaryModisError(f"Cannot identify Azure storage container from asset URL: {href}")
    container = path_parts[0]
    payload = _http_json(f"{SAS_API}/token/{account}/{container}", opener=opener)
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        raise PlanetaryModisError(f"Planetary Computer returned no SAS token for {account}/{container}.")
    return token


def _sign_href(href: str, token: str) -> str:
    parsed = urlparse(href)
    if not parsed.netloc.endswith(".blob.core.windows.net"):
        return href
    if any(key in parsed.query for key in ("se=", "sig=", "sp=")):
        return href
    token = token.lstrip("?")
    return href + ("&" if "?" in href else "?") + token


def _to_dataset_xy(dataset: object, longitude: float, latitude: float) -> tuple[float, float]:
    crs = getattr(dataset, "crs", None)
    if crs is None:
        raise PlanetaryModisError("MODIS COG has no CRS.")
    if str(crs).upper() in {"EPSG:4326", "OGC:CRS84"}:
        return longitude, latitude
    from rasterio.warp import transform
    xs, ys = transform("EPSG:4326", crs, [longitude], [latitude])
    return float(xs[0]), float(ys[0])


def pixel_center_lonlat(grid: dict[str, object], row: int, column: int) -> tuple[float, float]:
    """Convert a subset pixel center using the exact COG affine transform and CRS."""
    from rasterio.transform import Affine, xy
    from rasterio.warp import transform
    if not (0 <= row < int(grid["nrows"]) and 0 <= column < int(grid["ncols"])):
        raise ValueError("Pixel index lies outside the MODIS subset grid.")
    affine = Affine(*grid["window_transform"][:6])
    x, y = xy(affine, row, column, offset="center")
    lon, lat = transform(str(grid["crs"]), "EPSG:4326", [x], [y])
    return float(lon[0]), float(lat[0])


def fetch_mod13q1(
    latitude: float,
    longitude: float,
    start_date: str = "2001-01-01",
    end_date: str = "2025-12-31",
    radius_km: int = 2,
    *,
    opener: Callable[..., object] | None = None,
    raster_opener: Callable[..., object] | None = None,
) -> dict[str, object]:
    """Fetch quality-screened MOD13Q1.061 NDVI from public Planetary Computer COGs."""
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Invalid geographic coordinates.")
    if not 1 <= radius_km <= 100:
        raise ValueError("radius_km must be between 1 and 100.")
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("start_date must not be after end_date.")

    all_items = _search_items(latitude, longitude, start_date, end_date, radius_km, opener)
    items = _sample_one_per_month(all_items)
    print(
        f"STAC search returned {len(all_items)} Terra MOD13Q1.061 items; "
        f"selected {len(items)} monthly composites for COG analysis.",
        flush=True,
    )
    token_cache: dict[tuple[str, str], str] = {}
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError as exc:
        raise PlanetaryModisError("rasterio is required; install requirements.txt.") from exc

    open_raster = raster_opener or rasterio.open
    raw_records: list[dict[str, object]] = []
    valid_observations: list[tuple[int, int, str, float]] = []
    quality_counts = {"good": 0, "marginal": 0, "snow_or_ice": 0, "cloudy": 0, "other_or_fill": 0}
    grid = None
    item_ids = []
    tile_ids = []

    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_MULTIRANGE="YES",
    ):
        for item_index, item in enumerate(items, start=1):
            item_id = str(item["id"])
            if item_index == 1 or item_index % 10 == 0 or item_index == len(items):
                print(f"Reading MODIS COG {item_index}/{len(items)}: {item_id}", flush=True)
            assets = item.get("assets", {})
            if NDVI_ASSET not in assets or QUALITY_ASSET not in assets:
                raise PlanetaryModisError(f"Required NDVI/QA COG assets are missing from {item_id}.")
            raw_ndvi_href = str(assets[NDVI_ASSET]["href"])
            raw_qa_href = str(assets[QUALITY_ASSET]["href"])
            signed_hrefs = []
            for raw_href in (raw_ndvi_href, raw_qa_href):
                parsed_href = urlparse(raw_href)
                container_parts = parsed_href.path.lstrip("/").split("/")
                token_key = (parsed_href.netloc.split(".")[0], container_parts[0])
                if token_key not in token_cache:
                    token_cache[token_key] = _get_sas_token_for_href(raw_href, opener)
                signed_hrefs.append(_sign_href(raw_href, token_cache[token_key]))
            ndvi_href, qa_href = signed_hrefs
            composite_date = str(item["__composite_date"])
            with open_raster(ndvi_href) as ndvi_ds, open_raster(qa_href) as qa_ds:
                x, y = _to_dataset_xy(ndvi_ds, longitude, latitude)
                center_row, center_col = ndvi_ds.index(x, y)
                xres, yres = ndvi_ds.res
                half_cols = max(1, math.floor(radius_km * 1000 / abs(xres)))
                half_rows = max(1, math.floor(radius_km * 1000 / abs(yres)))
                window = Window(
                    center_col - half_cols, center_row - half_rows,
                    2 * half_cols + 1, 2 * half_rows + 1,
                )
                ndvi_array = ndvi_ds.read(1, window=window, boundless=True, fill_value=NDVI_FILL)
                qa_array = qa_ds.read(1, window=window, boundless=True, fill_value=255)
                if ndvi_array.shape != qa_array.shape:
                    raise PlanetaryModisError(f"NDVI/QA COG window shapes differ for {item_id}.")
                if ndvi_ds.crs != qa_ds.crs or ndvi_ds.transform != qa_ds.transform:
                    raise PlanetaryModisError(f"NDVI/QA COG georeferencing differs for {item_id}.")
                if grid is None:
                    window_transform = ndvi_ds.window_transform(window)
                    grid = {
                        "nrows": int(ndvi_array.shape[0]),
                        "ncols": int(ndvi_array.shape[1]),
                        "cellsize_m": float(abs(xres)),
                        "crs": str(ndvi_ds.crs),
                        "window_transform": list(window_transform)[:6],
                        "center_row": int(half_rows),
                        "center_column": int(half_cols),
                        "requested_latitude": latitude,
                        "requested_longitude": longitude,
                    }
                elif (
                    int(ndvi_array.shape[0]) != int(grid["nrows"])
                    or int(ndvi_array.shape[1]) != int(grid["ncols"])
                    or str(ndvi_ds.crs) != str(grid["crs"])
                ):
                    raise PlanetaryModisError("MODIS subset grid changed between composite dates.")

                ndvi_values = ndvi_array.tolist()
                qa_values = qa_array.tolist()
                date_key = composite_date.replace("-", "")
                for row_index, (ndvi_row, qa_row) in enumerate(zip(ndvi_values, qa_values)):
                    for col, (ndvi_raw_value, qa_raw_value) in enumerate(zip(ndvi_row, qa_row)):
                        ndvi_raw, qa = int(ndvi_raw_value), int(qa_raw_value)
                        ndvi_valid = -2000 <= ndvi_raw <= 10000
                        if qa == 0 and ndvi_valid:
                            quality_counts["good"] += 1
                        elif qa == 0:
                            quality_counts["other_or_fill"] += 1
                        elif qa == 1:
                            quality_counts["marginal"] += 1
                        elif qa == 2:
                            quality_counts["snow_or_ice"] += 1
                        elif qa == 3:
                            quality_counts["cloudy"] += 1
                        else:
                            quality_counts["other_or_fill"] += 1
                        ndvi = ndvi_raw * NDVI_SCALE
                        raw_records.append({
                            "date": composite_date,
                            "row": row_index,
                            "column": col,
                            "ndvi_raw": ndvi_raw,
                            "ndvi": ndvi if ndvi_valid else None,
                            "quality_code": qa,
                        })
                        if qa == GOOD_QUALITY and ndvi_valid:
                            valid_observations.append((row_index, col, date_key, ndvi))

            item_ids.append(item_id)
            tile_ids.append(str(item.get("properties", {}).get("modis:tile-id", "")))

    if grid is None or not raw_records:
        raise PlanetaryModisError("No MOD13Q1.061 pixel observations were extracted.")
    return {
        "product": "MOD13Q1",
        "product_versions": ["061"],
        "source": "NASA LP DAAC MOD13Q1.061 hosted as COGs by Microsoft Planetary Computer",
        "source_api": f"{STAC_API}/collections/{COLLECTION_ID}",
        "doi": DOI,
        "collection_id": COLLECTION_ID,
        "ndvi_band": NDVI_ASSET,
        "quality_band": QUALITY_ASSET,
        "ndvi_scale_factor": NDVI_SCALE,
        "ndvi_fill_value": NDVI_FILL,
        "quality_policy": "Only pixel reliability code 0 (good data) enters analysis.",
        "start_date": str(items[0]["__composite_date"]),
        "end_date": str(items[-1]["__composite_date"]),
        "composite_count": len(items),
        "available_composite_count": len(all_items),
        "sampling_strategy": "One 16-day composite per calendar month, nearest to day 15.",
        "grid": grid,
        "tile_ids": sorted(set(tile_ids)),
        "item_ids": item_ids,
        "quality_counts": quality_counts,
        "raw_records": raw_records,
        "valid_observations": valid_observations,
    }
