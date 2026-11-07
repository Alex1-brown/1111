"""CLI to fetch a small reproducible NASA POWER + GIBS validation package."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analysis import analyze_power_payload, compare_rgb_pixels
from .nasa import fetch_gibs_image, fetch_power, utc_timestamp


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and analyze public NASA POWER and GIBS data.")
    parser.add_argument("--latitude", type=float, default=38.5598)
    parser.add_argument("--longitude", type=float, default=68.7870)
    parser.add_argument("--start", default="20240101")
    parser.add_argument("--end", default="20241231")
    parser.add_argument("--before", default="2025-06-01")
    parser.add_argument("--after", default="2025-07-01")
    parser.add_argument("--bbox", default="67.5,37.5,70,39.5", help="west,south,east,north in EPSG:4326")
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    args = parser.parse_args()

    bbox = tuple(float(part) for part in args.bbox.split(","))
    if len(bbox) != 4:
        parser.error("--bbox must contain west,south,east,north")

    args.output.mkdir(parents=True, exist_ok=True)
    print("Fetching NASA POWER daily data...")
    power_payload, power_source = fetch_power(args.latitude, args.longitude, args.start, args.end)
    (args.output / "nasa_power.json").write_text(json.dumps(power_payload, indent=2), encoding="utf-8")
    metrics = analyze_power_payload(power_payload)

    print("Fetching NASA GIBS MODIS browse images...")
    before_path = args.output / f"modis_{args.before}.png"
    after_path = args.output / f"modis_{args.after}.png"
    before_url, before_bytes = fetch_gibs_image(args.before, bbox, before_path)
    after_url, after_bytes = fetch_gibs_image(args.after, bbox, after_path)

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow is required for image comparison. Install with: pip install -r requirements.txt") from exc

    with Image.open(before_path) as image:
        before = image.convert("RGB")
        before_pixels = before.tobytes()
        dimensions = before.size
    with Image.open(after_path) as image:
        after = image.convert("RGB")
        if image.size != dimensions:
            raise ValueError("NASA GIBS images have different dimensions.")
        after_pixels = image.tobytes()

    image_metrics = compare_rgb_pixels(before_pixels, after_pixels, dimensions[0], dimensions[1])
    report = {
        "generated_at_utc": utc_timestamp(),
        "power_source_url": power_source,
        "power": metrics,
        "imagery": {
            "source": "NASA GIBS",
            "layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "bbox_epsg4326": bbox,
            "before": {"date": args.before, "url": before_url, "file": str(before_path), "bytes": before_bytes},
            "after": {"date": args.after, "url": after_url, "file": str(after_path), "bytes": after_bytes},
            "rgb_comparison": image_metrics,
            "interpretation_warning": "Browse-image RGB differences are not calibrated reflectance or validated land-cover change.",
        },
        "scientific_limitations": [
            "NASA POWER is gridded analysis/reanalysis-derived data, not a direct weather-station observation.",
            "A single seasonal year cannot establish a long-term climate trend.",
            "Clouds, atmosphere, illumination and visualization affect RGB image differences.",
        ],
    }
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report saved: {report_path}")
    print(json.dumps({
        "temperature_mean_c": metrics["temperature_2m_c"]["mean"],
        "valid_daily_temperature_records": metrics["temperature_2m_c"]["count"],
        "image_changed_pixel_percent": image_metrics["changed_pixel_percent"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
