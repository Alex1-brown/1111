"""CLI to fetch and analyze multi-year NASA POWER + GIBS data."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from .analysis import analyze_power_payload, compare_rgb_pixels
from .imagery_series import sample_dates, summarize_sequence
from .nasa import fetch_gibs_image, fetch_power, utc_timestamp
from .analysis import valid_values
from .statistical_analysis import analyze_power_timeseries
from .planetary_modis import fetch_mod13q1, pixel_center_lonlat
from .spatial_analysis import (
    annual_pixel_medians, analyze_pixel_trends, summarize_fixed_annual_panel,
    select_complete_year_range,
)
from .trend_analysis import mann_kendall
from .change_point import pettitt_test
from .anomaly_analysis import robust_anomalies
from .cross_source_analysis import analyze_monthly_cross_source
from .visualization import render_line_chart
from .html_report import render_html_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and analyze public NASA POWER and GIBS data.")
    parser.add_argument("--latitude", type=float, default=38.5598)
    parser.add_argument("--longitude", type=float, default=68.7870)
    parser.add_argument("--start", default="20210101", help="NASA POWER start date, YYYYMMDD")
    parser.add_argument("--end", default="20251231", help="NASA POWER end date, YYYYMMDD")
    parser.add_argument("--imagery-start", default="2021-01-01")
    parser.add_argument("--imagery-end", default="2025-12-31")
    parser.add_argument("--image-count", type=int, default=60)
    parser.add_argument("--minimum-images", type=int, default=50,
                        help="Minimum number of valid images required for a successful run")
    parser.add_argument("--skip-gibs", action="store_true",
                        help="Skip uncalibrated NASA GIBS browse imagery; quantitative MODIS NDVI remains enabled")
    parser.add_argument("--bbox", default="67.5,37.5,70,39.5", help="west,south,east,north in EPSG:4326")
    parser.add_argument("--image-width", type=int, default=512)
    parser.add_argument("--image-height", type=int, default=512)
    parser.add_argument("--ndvi-start", default="2001-01-01")
    parser.add_argument("--ndvi-end", default="2025-12-31")
    parser.add_argument("--ndvi-radius-km", type=int, default=2,
                        help="MODIS subset radius in km around the center point")
    parser.add_argument("--ndvi-minimum-years", type=int, default=15)
    parser.add_argument("--ndvi-minimum-composites-per-pixel-year", type=int, default=3,
                        help="Minimum quality-screened monthly composites for an annual pixel median")
    parser.add_argument("--ndvi-minimum-monthly-composites-per-year", type=int, default=11,
                        help="Monthly composites/year required to include a year in the trend period")
    parser.add_argument("--skip-ndvi", action="store_true",
                        help="Skip quantitative MODIS NDVI download and spatial analysis")
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    args = parser.parse_args()

    bbox = tuple(float(part) for part in args.bbox.split(","))
    if len(bbox) != 4:
        parser.error("--bbox must contain west,south,east,north")
    if not args.skip_gibs and not 1 <= args.minimum_images <= args.image_count:
        parser.error("--minimum-images must be between 1 and --image-count")
    if args.ndvi_minimum_years < 3:
        parser.error("--ndvi-minimum-years must be at least 3")
    if args.ndvi_minimum_composites_per_pixel_year < 1:
        parser.error("--ndvi-minimum-composites-per-pixel-year must be at least 1")
    if args.ndvi_minimum_monthly_composites_per_year < 1:
        parser.error("--ndvi-minimum-monthly-composites-per-year must be at least 1")
    if not 1 <= args.ndvi_radius_km <= 100:
        parser.error("--ndvi-radius-km must be between 1 and 100")
    if args.skip_gibs:
        dates = []
    else:
        try:
            dates = sample_dates(args.imagery_start, args.imagery_end, args.image_count)
        except ValueError as exc:
            parser.error(str(exc))

    args.output.mkdir(parents=True, exist_ok=True)
    print("Fetching NASA POWER daily data...", flush=True)
    power_payload, power_source = fetch_power(args.latitude, args.longitude, args.start, args.end)
    (args.output / "nasa_power.json").write_text(json.dumps(power_payload, indent=2), encoding="utf-8")
    metrics = analyze_power_payload(power_payload)
    parameters = power_payload["properties"]["parameter"]
    fill_value = float(power_payload["header"].get("fill_value", -999.0))
    temperature_series, _ = valid_values(parameters["T2M"], fill_value)
    precipitation_series, _ = valid_values(parameters["PRECTOTCORR"], fill_value)
    time_series_analysis = analyze_power_timeseries(temperature_series, precipitation_series)

    ndvi_summary = {"status": "skipped"}
    cross_source_summary = {"status": "unavailable"}
    ndvi_error = None
    ndvi_data = None
    ndvi_annual_rows = []
    pixel_trends = []
    if not args.skip_ndvi:
        try:
            print("Fetching NASA MOD13Q1.061 NDVI COGs from Microsoft Planetary Computer...", flush=True)
            ndvi_data = fetch_mod13q1(
                args.latitude, args.longitude,
                args.ndvi_start, args.ndvi_end, args.ndvi_radius_km,
            )
            ndvi_dir = args.output / "modis_ndvi"
            ndvi_dir.mkdir(parents=True, exist_ok=True)
            raw_path = ndvi_dir / "ndvi_pixel_observations.csv"
            with raw_path.open("w", newline="", encoding="utf-8") as csv_file:
                fields = ["date", "row", "column", "ndvi_raw", "ndvi", "quality_code"]
                writer = csv.DictWriter(csv_file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(ndvi_data["raw_records"])

            annual_pixels = annual_pixel_medians(
                ndvi_data["valid_observations"],
                minimum_observations_per_year=args.ndvi_minimum_composites_per_pixel_year,
            )
            trend_start_year, trend_end_year, composite_counts_by_year = select_complete_year_range(
                ndvi_data["composite_dates"],
                minimum_composites_per_year=args.ndvi_minimum_monthly_composites_per_year,
                minimum_years=args.ndvi_minimum_years,
            )
            annual_pixels_core = {
                pixel: [(year, value) for year, value in series
                        if trend_start_year <= year <= trend_end_year]
                for pixel, series in annual_pixels.items()
            }
            annual_pixels_core = {
                pixel: series for pixel, series in annual_pixels_core.items()
                if len(series) >= args.ndvi_minimum_years
            }
            pixel_trends = analyze_pixel_trends(
                annual_pixels_core, minimum_years=args.ndvi_minimum_years
            )
            grid_meta = ndvi_data["grid"]
            features = []
            for trend in pixel_trends:
                lon, lat = pixel_center_lonlat(
                    grid_meta, trend["row"], trend["column"]
                )
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": trend,
                })
            geojson_path = ndvi_dir / "ndvi_spatial_trends.geojson"
            geojson_path.write_text(json.dumps({
                "type": "FeatureCollection", "features": features,
            }, indent=2), encoding="utf-8")

            trend_fields = [
                "row", "column", "years", "first_year", "last_year",
                "sen_slope_ndvi_per_year", "kendall_tau", "p_value",
                "trend_method", "q_value_by",
                "by_q_le_0_05_temporal_uncorrected", "serial_correlation_adjusted",
            ]
            trend_path = ndvi_dir / "ndvi_spatial_trends.csv"
            with trend_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=trend_fields)
                writer.writeheader()
                writer.writerows(pixel_trends)

            annual_buckets = defaultdict(list)
            for series in annual_pixels.values():
                for year, value in series:
                    annual_buckets[year].append(value)
            fixed_panel_rows, fixed_panel_pixel_count = summarize_fixed_annual_panel(
                annual_pixels_core, trend_start_year, trend_end_year
            )
            fixed_by_year = {row["year"]: row for row in fixed_panel_rows}
            annual_years = sorted(set(annual_buckets) | set(fixed_by_year) | set(composite_counts_by_year))
            ndvi_annual_rows = [
                {
                    "year": year,
                    "median_of_pixel_annual_medians": median(annual_buckets[year]) if annual_buckets[year] else None,
                    "mean_of_pixel_annual_medians": (
                        sum(annual_buckets[year]) / len(annual_buckets[year]) if annual_buckets[year] else None
                    ),
                    "pixels_with_valid_data": len(annual_buckets[year]),
                    "fixed_panel_median": fixed_by_year.get(year, {}).get("fixed_panel_median"),
                    "fixed_panel_mean": fixed_by_year.get(year, {}).get("fixed_panel_mean"),
                    "fixed_panel_pixels": fixed_by_year.get(year, {}).get("fixed_panel_pixels", 0),
                    "trend_period_included": year in fixed_by_year,
                    "selected_monthly_composites": composite_counts_by_year.get(year, 0),
                }
                for year in annual_years
            ]
            fixed_ndvi_series = [
                (int(row["year"]), float(row["fixed_panel_median"]))
                for row in ndvi_annual_rows if row["fixed_panel_median"] is not None
            ]
            ndvi_change_detection = {
                "fixed_panel_pixels": fixed_panel_pixel_count,
                "period": [trend_start_year, trend_end_year],
                "mann_kendall_sen": mann_kendall(
                    [(float(year), value) for year, value in fixed_ndvi_series]
                ),
                "pettitt": pettitt_test(fixed_ndvi_series),
                "robust_anomalies": robust_anomalies(
                    [(str(year), value) for year, value in fixed_ndvi_series]
                ),
                "interpretation_caveat": (
                    "Pettitt and Mann-Kendall p-values do not correct for temporal autocorrelation. "
                    "The fixed pixel panel prevents changing spatial coverage from driving the aggregate series."
                ),
            }
            annual_path = ndvi_dir / "ndvi_annual_summary.csv"
            with annual_path.open("w", newline="", encoding="utf-8") as csv_file:
                fields = [
                    "year", "median_of_pixel_annual_medians",
                    "mean_of_pixel_annual_medians", "pixels_with_valid_data",
                    "fixed_panel_median", "fixed_panel_mean", "fixed_panel_pixels",
                    "trend_period_included", "selected_monthly_composites",
                ]
                writer = csv.DictWriter(csv_file, fieldnames=fields)
                writer.writeheader()
                writer.writerows(ndvi_annual_rows)

            try:
                common_start_year = max(int(args.start[:4]), int(args.ndvi_start[:4]))
                common_end_year = min(int(args.end[:4]), int(args.ndvi_end[:4]))
                cross_source = analyze_monthly_cross_source(
                    temperature_series, precipitation_series,
                    ndvi_data["valid_observations"],
                    start_year=common_start_year, end_year=min(common_end_year, trend_end_year),
                )
                cross_path = ndvi_dir / "monthly_cross_source.csv"
                cross_fields = [
                    "year", "month", "ndvi_median", "temperature_mean_c",
                    "precipitation_total_mm", "ndvi_observations",
                    "temperature_daily_count", "precipitation_daily_count",
                    "ndvi_anomaly", "temperature_anomaly_c", "precipitation_anomaly_mm",
                ]
                with cross_path.open("w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=cross_fields)
                    writer.writeheader()
                    writer.writerows(cross_source["monthly_rows"])
                cross_source_summary = {
                    key: value for key, value in cross_source.items() if key != "monthly_rows"
                }
                cross_source_summary["status"] = "success"
                cross_source_summary["artifact_csv"] = str(cross_path)
            except Exception as exc:
                cross_source_summary = {"status": "failed", "error": str(exc)}
                print(f"Cross-source monthly analysis failed: {exc}", flush=True)

            ndvi_summary = {
                "status": "success",
                "product": ndvi_data["product"],
                "product_versions": ndvi_data["product_versions"],
                "source": ndvi_data["source"],
                "source_api": ndvi_data["source_api"],
                "collection_id": ndvi_data["collection_id"],
                "tile_ids": ndvi_data["tile_ids"],
                "doi": ndvi_data["doi"],
                "ndvi_band": ndvi_data["ndvi_band"],
                "quality_band": ndvi_data["quality_band"],
                "ndvi_scale_factor": ndvi_data["ndvi_scale_factor"],
                "quality_policy": ndvi_data["quality_policy"],
                "date_start": ndvi_data["start_date"],
                "date_end": ndvi_data["end_date"],
                "composite_count": ndvi_data["composite_count"],
                "monthly_composite_counts_by_year": composite_counts_by_year,
                "trend_period": [trend_start_year, trend_end_year],
                "minimum_monthly_composites_per_year_for_trend": args.ndvi_minimum_monthly_composites_per_year,
                "available_composite_count": ndvi_data["available_composite_count"],
                "sampling_strategy": ndvi_data["sampling_strategy"],
                "grid": {
                    key: value for key, value in grid_meta.items() if key != "header"
                },
                "radius_km": args.ndvi_radius_km,
                "raw_pixel_observations": len(ndvi_data["raw_records"]),
                "quality_accepted_pixel_observations": len(ndvi_data["valid_observations"]),
                "quality_counts": ndvi_data["quality_counts"],
                "pixels_with_annual_data": len(annual_pixels),
                "pixels_with_trend_estimates": len(pixel_trends),
                "pixels_by_q_le_0_05_temporal_uncorrected": sum(
                    bool(item["by_q_le_0_05_temporal_uncorrected"]) for item in pixel_trends
                ),
                "fixed_panel_pixels": fixed_panel_pixel_count,
                "annual_fixed_panel_change_detection": ndvi_change_detection,
                "multiple_testing_method": "Benjamini-Yekutieli",
                "minimum_years_per_pixel": args.ndvi_minimum_years,
                "minimum_composites_per_pixel_year": args.ndvi_minimum_composites_per_pixel_year,
                "artifacts": {
                    "raw_pixel_observations_csv": str(raw_path),
                    "annual_summary_csv": str(annual_path),
                    "spatial_trends_csv": str(trend_path),
                    "spatial_trends_geojson": str(geojson_path),
                    "monthly_cross_source_csv": cross_source_summary.get("artifact_csv"),
                },
                "geolocation_warning": (
                    "GeoJSON pixel centers use the authoritative affine transform and CRS read from the "
                    "NASA MOD13Q1.061 cloud-optimized GeoTIFF. Pixel centers are transformed to EPSG:4326."
                ),
                "scientific_limitations": [
                    "MOD13Q1 is a 16-day best-pixel composite, not a daily observation.",
                    "Only SummaryQA/pixel-reliability code 0 is accepted; this strict filter reduces coverage.",
                    "One 16-day composite per calendar month is selected nearest to mid-month; this monthly sampling suppresses some within-month variability.",
                    "Annual medians suppress seasonal variation but also hide within-year changes.",
                    "Annual aggregate NDVI uses a fixed spatial pixel panel across the requested years; all-pixel coverage is reported separately to expose missingness.",
                    "Mann-Kendall and Pettitt p-values are not adjusted for temporal autocorrelation.",
                    f"Trend inference is restricted to {trend_start_year}-{trend_end_year}, the longest contiguous period meeting the monthly composite coverage threshold; 2024-2025 are incomplete in this tile.",
                    "BY corrects the spatial multiple-testing burden only conditional on valid pixel p-values.",
                    "The subset is a local 4 km by 4 km sample window, not a map of all Tajikistan.",
                ],
            }
            print(json.dumps({
                "modis_ndvi_composites": ndvi_data["composite_count"],
                "modis_ndvi_valid_observations": len(ndvi_data["valid_observations"]),
                "modis_ndvi_pixels_with_trends": len(pixel_trends),
                "modis_ndvi_pixels_by_q05_temporal_uncorrected": ndvi_summary["pixels_by_q_le_0_05_temporal_uncorrected"],
            }, indent=2), flush=True)
        except Exception as exc:
            ndvi_error = str(exc)
            ndvi_summary = {"status": "failed", "error": ndvi_error}
            print(f"MODIS NDVI analysis failed: {ndvi_error}", flush=True)

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Pillow is required. Install dependencies with: pip install -r requirements.txt") from exc

    image_dir = args.output / "modis_series"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_records, comparisons, failed_images = [], [], []
    previous_pixels = None
    dimensions = (args.image_width, args.image_height)
    total_image_bytes = 0

    for index, image_date in enumerate(dates, start=1):
        print(f"Fetching NASA GIBS image {index}/{len(dates)}: {image_date}", flush=True)
        image_path = image_dir / f"modis_{image_date}.png"
        try:
            image_url, image_bytes = fetch_gibs_image(image_date, bbox, image_path, *dimensions)
            with Image.open(image_path) as image:
                image.verify()
            with Image.open(image_path) as image:
                rgb = image.convert("RGB")
                if rgb.size != dimensions:
                    raise ValueError(f"Unexpected dimensions {rgb.size}; expected {dimensions}")
                current_pixels = rgb.tobytes()
        except Exception as exc:
            image_path.unlink(missing_ok=True)
            failed_images.append({"date": image_date, "error": str(exc)[:500]})
            print(f"Image unavailable or invalid for {image_date}: {exc}", flush=True)
            continue

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

    image_summary = summarize_sequence(comparisons) if comparisons else {
        "comparison_count": 0,
        "mean_changed_pixel_percent": None,
        "median_changed_pixel_percent": None,
        "mean_absolute_rgb_difference": None,
    }
    charts_dir = args.output / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = {}
    annual_power_rows = time_series_analysis["annual"]
    for chart_name, title, y_label, key in (
        ("annual_temperature.svg", "Annual mean 2 m air temperature", "Temperature (°C)", "mean_temperature_c"),
        ("annual_precipitation.svg", "Annual corrected precipitation total", "Precipitation (mm)", "precipitation_total_mm"),
    ):
        chart_path = charts_dir / chart_name
        chart_path.write_text(render_line_chart(
            [(str(row["year"]), float(row[key])) for row in annual_power_rows],
            title, y_label,
        ), encoding="utf-8")
        chart_paths[chart_name] = str(chart_path)
    if ndvi_summary.get("status") == "success":
        ndvi_chart_path = charts_dir / "annual_ndvi.svg"
        ndvi_chart_path.write_text(render_line_chart(
            [(str(row["year"]), float(row["fixed_panel_median"]))
             for row in ndvi_annual_rows if row["fixed_panel_median"] is not None],
            f"Annual median MODIS NDVI — fixed {ndvi_summary['fixed_panel_pixels']}-pixel panel", "NDVI",
        ), encoding="utf-8")
        chart_paths["annual_ndvi.svg"] = str(ndvi_chart_path)
        ndvi_summary["artifacts"]["annual_ndvi_svg"] = str(ndvi_chart_path)
        coverage_chart_path = charts_dir / "annual_ndvi_coverage.svg"
        coverage_chart_path.write_text(render_line_chart(
            [(str(row["year"]), float(row["pixels_with_valid_data"])) for row in ndvi_annual_rows],
            "Annual MODIS NDVI spatial coverage", "Pixels with valid data",
        ), encoding="utf-8")
        chart_paths["annual_ndvi_coverage.svg"] = str(coverage_chart_path)
        ndvi_summary["artifacts"]["annual_ndvi_coverage_svg"] = str(coverage_chart_path)

    report = {
        "generated_at_utc": utc_timestamp(),
        "dataset_scope": {
            "power_daily_start": args.start, "power_daily_end": args.end,
            "imagery_start": args.imagery_start, "imagery_end": args.imagery_end,
            "requested_satellite_images": 0 if args.skip_gibs else args.image_count,
            "minimum_required_satellite_images": 0 if args.skip_gibs else args.minimum_images,
            "downloaded_satellite_images": len(image_records),
            "failed_image_requests": len(failed_images),
            "image_dimensions": list(dimensions), "total_imagery_bytes": total_image_bytes,
        },
        "power_source_url": power_source,
        "power": metrics,
        "power_time_series_analysis": time_series_analysis,
        "modis_ndvi": ndvi_summary,
        "cross_source_monthly_analysis": cross_source_summary,
        "annual_change_detection": {
            "power_temperature": {
                "pettitt": pettitt_test([(int(row["year"]), float(row["mean_temperature_c"])) for row in time_series_analysis["annual"]]),
                "robust_anomalies": robust_anomalies([(str(row["year"]), float(row["mean_temperature_c"])) for row in time_series_analysis["annual"]]),
            },
            "power_precipitation": {
                "pettitt": pettitt_test([(int(row["year"]), float(row["precipitation_total_mm"])) for row in time_series_analysis["annual"]]),
                "robust_anomalies": robust_anomalies([(str(row["year"]), float(row["precipitation_total_mm"])) for row in time_series_analysis["annual"]]),
            },
            "ndvi_fixed_panel": ndvi_summary.get("annual_fixed_panel_change_detection"),
        },
        "charts": chart_paths,
        "imagery": {
            "status": "skipped" if args.skip_gibs else "collected",
            "source": "NASA GIBS", "layer": "MODIS_Terra_CorrectedReflectance_TrueColor",
            "bbox_epsg4326": bbox, "images": image_records, "failed_requests": failed_images,
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
            "MODIS NDVI trends are local vegetation indicators and do not directly validate air temperature or precipitation.",
            "Monthly NDVI-climate associations are exploratory and do not establish causation or validate either source.",
        ],
    }
    html_path = args.output / "report.html"
    report["html_report"] = str(html_path)
    if ndvi_summary.get("status") == "success":
        ndvi_summary["artifacts"]["html_report"] = str(html_path)
    html_path.write_text(
        render_html_report(report, pixel_trends, chart_paths),
        encoding="utf-8",
    )
    report_path = args.output / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for filename, rows in (
        ("annual_summary.csv", time_series_analysis["annual"]),
        ("monthly_climatology.csv", time_series_analysis["monthly_climatology"]),
        ("seasonal_summary.csv", time_series_analysis["meteorological_seasons"]),
    ):
        rows = list(rows)
        if rows:
            with (args.output / filename).open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    print(f"Report saved: {report_path}", flush=True)
    print(json.dumps({
        "temperature_daily_records": metrics["temperature_2m_c"]["count"],
        "precipitation_daily_records": metrics["precipitation_corrected_mm_day"]["count"],
        "satellite_images_requested": args.image_count,
        "satellite_images_downloaded": len(image_records),
        "satellite_image_failures": len(failed_images),
        "minimum_images_required": args.minimum_images,
        "adjacent_image_comparisons": len(comparisons),
        "mean_changed_pixel_percent": image_summary["mean_changed_pixel_percent"],
        "annual_temperature_trend_c_per_year": time_series_analysis["descriptive_linear_trends"]["annual_mean_temperature"]["slope_per_year"],
        "annual_precipitation_trend_mm_per_year": time_series_analysis["descriptive_linear_trends"]["annual_precipitation_total"]["slope_per_year"],
        "daily_temperature_precipitation_pearson_r": time_series_analysis["daily_temperature_precipitation_pearson_r"],
        "modis_ndvi_status": ndvi_summary.get("status"),
        "cross_source_common_months": cross_source_summary.get("common_months"),
        "cross_source_anomaly_correlations": cross_source_summary.get("anomaly_correlations"),
        "chart_files": len(chart_paths),
        "total_imagery_megabytes": round(total_image_bytes / (1024 * 1024), 2),
        "html_report": str(html_path),
    }, indent=2))
    if not args.skip_gibs and len(image_records) < args.minimum_images:
        print(f"ERROR: only {len(image_records)} valid images; {args.minimum_images} required.", flush=True)
        return 2
    if ndvi_error:
        print("ERROR: quantitative MODIS NDVI analysis did not complete.", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
