"""Independent Landsat 8/9 summer NDVI cross-check for the MODIS study window."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

from .planetary_modis import (
    STAC_API,
    _geometry_contains,
    _get_sas_token_for_href,
    _http_json,
    _sign_href,
    _to_dataset_xy,
)
from .trend_analysis import mann_kendall

LANDSAT_COLLECTION = "landsat-c2-l2"
LANDSAT_ASSETS = ("red", "nir08", "qa_pixel", "qa_radsat")
SR_SCALE = 0.0000275
SR_OFFSET = -0.2
SR_MIN_DN = 7273
SR_MAX_DN = 43636
INVALID_QA_PIXEL_BITS = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)


class LandsatValidationError(RuntimeError):
    """Raised when the independent Landsat cross-check cannot be completed."""


def ndvi_from_landsat_arrays(
    red_dn: np.ndarray,
    nir_dn: np.ndarray,
    qa_pixel: np.ndarray,
    qa_radsat: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert Landsat C2 L2 SR DNs to NDVI and return the strict clear-pixel mask."""
    red = np.asarray(red_dn, dtype=np.float64)
    nir = np.asarray(nir_dn, dtype=np.float64)
    qa = np.asarray(qa_pixel, dtype=np.uint16)
    saturation = np.asarray(qa_radsat, dtype=np.uint16)
    if not (red.shape == nir.shape == qa.shape == saturation.shape):
        raise ValueError("Landsat red, NIR, QA_PIXEL, and QA_RADSAT arrays must share one grid.")

    valid = (
        (red >= SR_MIN_DN) & (red <= SR_MAX_DN)
        & (nir >= SR_MIN_DN) & (nir <= SR_MAX_DN)
        & ((qa & INVALID_QA_PIXEL_BITS) == 0)
        & (saturation == 0)
    )
    red_reflectance = red * SR_SCALE + SR_OFFSET
    nir_reflectance = nir * SR_SCALE + SR_OFFSET
    denominator = nir_reflectance + red_reflectance
    valid &= np.isfinite(denominator) & (denominator > 0)
    ndvi = np.full(red.shape, np.nan, dtype=np.float64)
    ndvi[valid] = (
        (nir_reflectance[valid] - red_reflectance[valid])
        / denominator[valid]
    )
    valid &= np.isfinite(ndvi) & (ndvi >= -1.0) & (ndvi <= 1.0)
    ndvi[~valid] = np.nan
    return ndvi, valid


def _search_landsat_items(
    latitude: float,
    longitude: float,
    start_year: int,
    end_year: int,
    radius_km: int,
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
        "collections": LANDSAT_COLLECTION,
        "bbox": ",".join(f"{value:.7f}" for value in bbox),
        "datetime": f"{start_year}-01-01T00:00:00Z/{end_year}-12-31T23:59:59Z",
        "limit": 1000,
    }
    payload = _http_json(f"{STAC_API}/search", params)
    items = list(payload.get("features", []))
    next_link = next((link for link in payload.get("links", []) if link.get("rel") == "next"), None)
    while next_link:
        if str(next_link.get("method", "GET")).upper() != "GET":
            raise LandsatValidationError("Landsat STAC pagination returned an unsupported non-GET link.")
        payload = _http_json(str(next_link["href"]))
        items.extend(payload.get("features", []))
        next_link = next((link for link in payload.get("links", []) if link.get("rel") == "next"), None)
    return items


def _select_one_scene_per_year(
    items: list[dict[str, object]],
    latitude: float,
    longitude: float,
    start_year: int,
    end_year: int,
    maximum_cloud_cover: float,
) -> list[dict[str, object]]:
    candidates: dict[int, list[dict[str, object]]] = defaultdict(list)
    for item in items:
        props = item.get("properties", {})
        platform = str(props.get("platform", "")).lower()
        if platform not in {"landsat-8", "landsat-9"}:
            continue
        try:
            cloud = float(props["eo:cloud_cover"])
            acquired = date.fromisoformat(str(props["datetime"])[:10])
        except (KeyError, TypeError, ValueError):
            continue
        if cloud > maximum_cloud_cover or not (start_year <= acquired.year <= end_year):
            continue
        if not (date(acquired.year, 6, 1) <= acquired <= date(acquired.year, 9, 30)):
            continue
        geometry = item.get("geometry")
        if not isinstance(geometry, dict) or not _geometry_contains(geometry, longitude, latitude):
            continue
        assets = item.get("assets", {})
        if not all(name in assets and assets[name].get("href") for name in LANDSAT_ASSETS):
            continue
        item["__date"] = acquired.isoformat()
        item["__cloud_cover"] = cloud
        candidates[acquired.year].append(item)

    selected = []
    for year in range(start_year, end_year + 1):
        scenes = candidates.get(year, [])
        if not scenes:
            continue
        target = date(year, 7, 15)
        selected.append(min(
            scenes,
            key=lambda item: (
                abs((date.fromisoformat(str(item["__date"])) - target).days),
                float(item["__cloud_cover"]),
                str(item.get("id", "")),
            ),
        ))
    return selected


def _signed_asset_urls(
    item: dict[str, object],
    token_cache: dict[tuple[str, str], str],
) -> dict[str, str]:
    signed = {}
    assets = item["assets"]
    for name in LANDSAT_ASSETS:
        href = str(assets[name]["href"])
        parsed = urlparse(href)
        parts = parsed.path.lstrip("/").split("/")
        key = (parsed.netloc.split(".")[0], parts[0])
        if key not in token_cache:
            token_cache[key] = _get_sas_token_for_href(href)
        signed[name] = _sign_href(href, token_cache[key])
    return signed


def _read_scene_ndvi(
    item: dict[str, object],
    latitude: float,
    longitude: float,
    radius_km: int,
    minimum_valid_pixels: int,
    token_cache: dict[tuple[str, str], str],
) -> dict[str, object]:
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError as exc:
        raise LandsatValidationError("rasterio is required for Landsat COG reading.") from exc

    urls = _signed_asset_urls(item, token_cache)
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
        GDAL_HTTP_MULTIRANGE="YES",
    ):
        with rasterio.open(urls["red"]) as red_ds:
            x, y = _to_dataset_xy(red_ds, longitude, latitude)
            center_row, center_col = red_ds.index(x, y)
            xres, yres = red_ds.res
            half_cols = max(1, math.floor(radius_km * 1000 / abs(xres)))
            half_rows = max(1, math.floor(radius_km * 1000 / abs(yres)))
            window = Window(
                center_col - half_cols, center_row - half_rows,
                2 * half_cols + 1, 2 * half_rows + 1,
            )
            red = red_ds.read(1, window=window, boundless=True, fill_value=0)
            transform = red_ds.window_transform(window)
            crs = red_ds.crs
            shape = red.shape

        arrays = {}
        for name in ("nir08", "qa_pixel", "qa_radsat"):
            with rasterio.open(urls[name]) as dataset:
                if dataset.crs != crs or dataset.transform != red_ds.transform:
                    raise LandsatValidationError(f"Landsat {name} grid does not align with red band.")
                values = dataset.read(1, window=window, boundless=True, fill_value=0)
                if values.shape != shape:
                    raise LandsatValidationError(f"Landsat {name} window shape differs from red band.")
                arrays[name] = values

    ndvi, valid = ndvi_from_landsat_arrays(red, arrays["nir08"], arrays["qa_pixel"], arrays["qa_radsat"])
    count = int(valid.sum())
    if count < minimum_valid_pixels:
        raise LandsatValidationError(
            f"Only {count} clear Landsat pixels in scene {item.get('id')}; "
            f"minimum required is {minimum_valid_pixels}."
        )
    return {
        "median_ndvi": float(np.nanmedian(ndvi)),
        "valid_pixels": count,
        "total_window_pixels": int(ndvi.size),
        "crs": str(crs),
        "window_transform": list(transform)[:6],
    }


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    a, b = np.asarray(left, dtype=float), np.asarray(right, dtype=float)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[order[position]] = average
        start = end
    return ranks


def _spearman(left: list[float], right: list[float]) -> float | None:
    if len(left) < 3 or len(left) != len(right):
        return None
    return _pearson(_average_ranks(left), _average_ranks(right))


def validate_landsat_against_modis(
    artifact_dir: Path,
    *,
    latitude: float = 38.5598,
    longitude: float = 68.7870,
    radius_km: int = 2,
    start_year: int = 2013,
    end_year: int = 2023,
    maximum_cloud_cover: float = 40.0,
    minimum_valid_pixels: int = 500,
) -> dict[str, object]:
    """Compare annual summer Landsat 8/9 NDVI with July MODIS NDVI in the same window."""
    root = artifact_dir
    if not (root / "modis_ndvi" / "ndvi_pixel_observations.csv").exists() and (
        root / "nasa-real-data-22" / "modis_ndvi" / "ndvi_pixel_observations.csv"
    ).exists():
        root = root / "nasa-real-data-22"
    raw_path = root / "modis_ndvi" / "ndvi_pixel_observations.csv"
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)

    modis_july: dict[int, list[float]] = defaultdict(list)
    with raw_path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["quality_code"] != "0" or not row["ndvi"]:
                continue
            year = int(row["date"][:4])
            if start_year <= year <= end_year and row["date"][5:7] == "07":
                modis_july[year].append(float(row["ndvi"]))

    items = _search_landsat_items(latitude, longitude, start_year, end_year, radius_km)
    selected = _select_one_scene_per_year(
        items, latitude, longitude, start_year, end_year, maximum_cloud_cover
    )
    token_cache: dict[tuple[str, str], str] = {}
    records = []
    failures = []
    for item in selected:
        year = int(str(item["__date"])[:4])
        try:
            result = _read_scene_ndvi(
                item, latitude, longitude, radius_km, minimum_valid_pixels, token_cache
            )
            modis_values = modis_july.get(year, [])
            if len(modis_values) < 20:
                raise LandsatValidationError(f"No adequate quality-screened July MODIS sample for {year}.")
            records.append({
                "year": year,
                "landsat_date": item["__date"],
                "platform": item.get("properties", {}).get("platform"),
                "scene_cloud_cover_percent": float(item["__cloud_cover"]),
                "landsat_clear_pixels": result["valid_pixels"],
                "landsat_window_pixels": result["total_window_pixels"],
                "landsat_summer_median_ndvi": result["median_ndvi"],
                "modis_july_median_ndvi": float(np.median(modis_values)),
                "difference_landsat_minus_modis": (
                    float(result["median_ndvi"]) - float(np.median(modis_values))
                ),
            })
        except Exception as exc:
            failures.append({"scene_id": str(item.get("id", "")), "year": year, "error": str(exc)[:500]})

    records.sort(key=lambda item: int(item["year"]))
    if len(records) < 6:
        raise LandsatValidationError(
            f"Only {len(records)} years passed Landsat quality checks; at least 6 are required. "
            f"Failures recorded: {len(failures)}."
        )

    years = [int(item["year"]) for item in records]
    landsat_values = [float(item["landsat_summer_median_ndvi"]) for item in records]
    modis_values = [float(item["modis_july_median_ndvi"]) for item in records]
    common = list(zip(years, landsat_values))
    landsat_trend = mann_kendall([(float(year), value) for year, value in common])

    output_dir = root / "modis_ndvi"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "landsat_modis_summer_crosscheck.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        fields = list(records[0].keys())
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    summary = {
        "status": "success",
        "source": "USGS Landsat 8/9 Collection 2 Level-2 Surface Reflectance, hosted as COGs by Microsoft Planetary Computer",
        "collection_id": LANDSAT_COLLECTION,
        "study_window": {
            "latitude": latitude, "longitude": longitude, "radius_km": radius_km,
            "description": "Same local 4 km x 4 km Dushanbe window as the MODIS analysis",
        },
        "period": [start_year, end_year],
        "season_window": "June 1 through September 30; one selected scene per year nearest July 15",
        "maximum_scene_cloud_cover_percent": maximum_cloud_cover,
        "minimum_clear_pixels_per_scene": minimum_valid_pixels,
        "selected_scene_count": len(records),
        "available_stac_items": len(items),
        "failed_selected_scenes": failures,
        "years": years,
        "pearson_r_landsat_vs_modis_july": _pearson(landsat_values, modis_values),
        "spearman_rho_landsat_vs_modis_july": _spearman(landsat_values, modis_values),
        "landsat_sen_mann_kendall": landsat_trend,
        "artifact_csv": str(csv_path),
        "interpretation_warning": (
            "Cross-sensor consistency check only. Landsat 30 m and MODIS 250 m have different "
            "spatial support, spectral response, compositing, acquisition dates, and processing. "
            "One summer scene per year does not establish a long-term trend or causal explanation."
        ),
    }
    json_path = output_dir / "landsat_modis_summer_crosscheck.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["artifact_json"] = str(json_path)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-check summer MODIS NDVI against independent Landsat 8/9 surface reflectance."
    )
    parser.add_argument("artifact_dir", type=Path)
    parser.add_argument("--latitude", type=float, default=38.5598)
    parser.add_argument("--longitude", type=float, default=68.7870)
    parser.add_argument("--radius-km", type=int, default=2)
    parser.add_argument("--start-year", type=int, default=2013)
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--maximum-cloud-cover", type=float, default=40.0)
    parser.add_argument("--minimum-valid-pixels", type=int, default=500)
    args = parser.parse_args()
    result = validate_landsat_against_modis(
        args.artifact_dir,
        latitude=args.latitude,
        longitude=args.longitude,
        radius_km=args.radius_km,
        start_year=args.start_year,
        end_year=args.end_year,
        maximum_cloud_cover=args.maximum_cloud_cover,
        minimum_valid_pixels=args.minimum_valid_pixels,
    )
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
