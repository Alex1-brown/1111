"""CLI to fetch and analyze multi-year NASA POWER + GIBS data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import analyze_power_payload, compare_rgb_pixels
from .imagery_series import sample_dates, summarize_sequence
from .nasa import fetch_gibs_image, fetch_power, utc_timestamp


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and analyze public NASA POWER and GIBS data.")
    parser.add_argument("--latitude", type=float, default=38.5598)
    parser.add_argument("--longitude", type=float, default=68.7870)
    parser.add_argument("--start", default="20210101", help="NASA POWER start date, YYYYMMDD")
    parser.add_argument("--end", default="20251231", help="NASA POWER end date, YYYYMMDD")
    parser.add_argument("--imagery-start", default="2021-01-01")
    parser.add_argument("--imagery-end", default="2025-12-31")
    parser.add_argument("--image-count", type=int, default=60)
    parser.add_argument("--bbox", default="67.5,37.5,70,39.5", help="west,south,east,north in EPSG:4326")
    parser.add_argument("--image-width", type=int, default=512)
    parser.add_argument("--image-height", type=int, default=512)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    args = parser.parse_args()

    bbox = tuple(float(part) for part in args.bbox.split(","))
    if len(bbox) != 4:
        parser.error("--bbox must contain west,south,east,north")
    try:
        dates = sample_dates(args.imagery_start, args.imagery_end, args.image_count)
    except ValueError as exc:
        parser.error(str(exc))

    args.output.mkdir(parents=True, exist_ok=True)
    print("Fetching NASA POWER daily data...")
    power_payload, power_source = fetch_power(args.latitude, args.longitude, args.start, args.end)
    (args.output / "nasa_power.json").write_text(json.dumps(power_payload, indent=2), encoding="utf-8")
    metrics = analyze_power_payload(power_payload)

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow is required. Install dependencies with: pip install -r requirements.txt") from exc

    image_dir = args.output / "modis_series"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_records, comparisons = [], []
    previous_pixels = None
    dimensions = (args.image_width, args.image_height)
    total_image_bytes = 0

    for index, image_date in enumerate(dates, start=1):
        print(f"Fetching NASA GIBS image {index}/{len(dates)}: {image_date}")
        image_path = image_dir / f"modis_{image_date}.png"
        image_url, image_bytes = fetch_gibs_image(image_date, bbox, image_path, *dimensions)
        with Image.open(image_path) as image:
            rgb = image.convert("RGB")
            if rgb.size != dimensions:
                raise ValueError(f"Unexpected image dimensions for {image_date}: {rgb.size}; expected {dimensions}.")
            current_pixels = rgb.tobytes()

        if previous_pixels is not None:
            comparison = compare_rgb_pixels(previous_pixels, current_pixels, *dimensions)
            comparison["from_date"] = image_records[-1]["date"]
            comparison["to_date"] = image_date
            comparisons.append(comparison)

        image_records.append({
            "date": image_date, "source": "NASA GIBS",
            "layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "url": image_url, "file": str(image_path), "bytes": image_bytes,
            "width": dimensions[0], "height": dimensions[1],
        })
        total_image_bytes += image_bytes
        previous_pixels = current_pixels

    image_summary = summarize_sequence(comparisons)
    report = {
        "generated_at_utc": utc_timestamp(),
        "dataset_scope": {
            "power_daily_start": args.start, "power_daily_end": args.end,
            "imagery_start": args.imagery_start, "imagery_end": args.imagery_end,
            "requested_satellite_images": args.image_count,
            "downloaded_satellite_images": len(image_records),
            "image_dimensions": list(dimensions), "total_imagery_bytes": total_image_bytes,
        },
        "power_source_url": power_source,
        "power": metrics,
        "imagery": {
            "source": "NASA GIBS", "layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "bbox_epsg4326": bbox, "images": image_records,
            "adjacent_image_comparisons": comparisons, "sequence_summary": image_summary,
            "interpretation_warning": (
                "Browse-image RGB differences are not calibrated reflectance, land-cover classification, "
                "or proof of environmental change. Clouds, atmosphere, illumination and compositing affect values."
            ),
        },
        "scientific_limitations": [
            "NASA POWER gridded analysis/reanalysis-derived values are not direct local weather-station observations.",
            "NASA GIBS MODIS true-colour images are browse imagery, not calibrated spectral measurements.",
            "RGB differences are screening indicators only; scientific land-cover change needs validated products and methods.",
            "Five years of data alone are not sufficient to establish every long-term climate trend.",
        ],
    }
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report saved: {report_path}")
    print(json.dumps({
        "temperature_daily_records": metrics["temperature_2m_c"]["count"],
        "precipitation_daily_records": metrics["precipitation_corrected_mm_day"]["count"],
        "satellite_images_downloaded": len(image_records),
        "adjacent_image_comparisons": len(comparisons),
        "mean_changed_pixel_percent": image_summary["mean_changed_pixel_percent"],
        "total_imagery_megabytes": round(total_image_bytes / (1024 * 1024), 2),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
