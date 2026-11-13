"""Offline residual moving-block bootstrap sensitivity analysis for MODIS NDVI.

Run after extracting a NASA live-data artifact:
    python -m science_core.bootstrap_validation artifacts --spatial-replicates 5000

Hamed-Rao and block-bootstrap p/q values are diagnostic only pending empirical
calibration. BY adjustment cannot repair miscalibrated input p-values.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from math import ceil
from pathlib import Path

import numpy as np


def sen_slope(years: np.ndarray, values: np.ndarray) -> float:
    """Median of all pairwise slopes using actual year differences."""
    left, right = np.triu_indices(len(values), 1)
    slopes = (values[right] - values[left]) / (years[right] - years[left])
    return float(np.median(slopes))


def mann_kendall_score(values: np.ndarray) -> int:
    """Unstandardized Mann-Kendall S statistic."""
    left, right = np.triu_indices(len(values), 1)
    return int(np.sign(values[right] - values[left]).sum())


def benjamini_yekutieli(p_values: list[float] | np.ndarray) -> np.ndarray:
    """Benjamini-Yekutieli adjusted q-values, valid under arbitrary dependence."""
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("p-values must be a finite one-dimensional array in [0, 1].")
    if not len(p):
        return np.asarray([], dtype=float)
    order = np.argsort(p, kind="mergesort")
    m = len(p)
    harmonic = float(np.sum(1.0 / np.arange(1, m + 1)))
    ranks = np.arange(1, m + 1, dtype=float)
    raw = p[order] * m * harmonic / ranks
    adjusted_sorted = np.minimum.accumulate(raw[::-1])[::-1]
    adjusted = np.empty(m, dtype=float)
    adjusted[order] = np.clip(adjusted_sorted, 0.0, 1.0)
    return adjusted


def moving_block_bootstrap_mk(
    years: np.ndarray,
    values: np.ndarray,
    *,
    block_length: int,
    replicates: int,
    seed: int,
    slope_interval: bool = False,
) -> dict[str, float | int | None]:
    """Residual circular moving-block bootstrap, retained as sensitivity only.

    The two-sided empirical p-value compares absolute bootstrap S statistics
    with the observed absolute S. If requested, the percentile interval
    resamples detrended residuals and adds the fitted Sen trend back. Neither
    output is calibrated for inferential use; see BLOCK_BOOTSTRAP_AUDIT.md.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    if years.ndim != 1 or values.ndim != 1 or len(years) != len(values):
        raise ValueError("years and values must be one-dimensional arrays of equal length.")
    if len(values) < 10 or np.any(~np.isfinite(years)) or np.any(~np.isfinite(values)):
        raise ValueError("At least ten finite annual observations are required.")
    if np.any(np.diff(years) != 1):
        raise ValueError("Moving-block validation requires consecutive annual observations.")
    if block_length < 1 or block_length > len(values):
        raise ValueError("block_length must be between 1 and the series length.")
    if replicates < 100:
        raise ValueError("At least 100 bootstrap replicates are required.")

    n = len(values)
    slope = sen_slope(years, values)
    residuals = values - slope * (years - years[0])
    left, right = np.triu_indices(n, 1)
    observed_s = int(np.sign(values[right] - values[left]).sum())

    rng = np.random.default_rng(seed)
    block_count = ceil(n / block_length)
    starts = rng.integers(0, n, size=(replicates, block_count))
    offsets = np.arange(block_length)
    indices = (starts[:, :, None] + offsets[None, None, :]) % n
    samples = residuals[indices].reshape(replicates, -1)[:, :n]

    bootstrap_scores = np.sign(samples[:, right] - samples[:, left]).sum(axis=1)
    exceedances = int(np.count_nonzero(np.abs(bootstrap_scores) >= abs(observed_s)))
    result: dict[str, float | int | None] = {
        "sen_slope": slope,
        "observed_mk_s": observed_s,
        "exceedances": exceedances,
        "replicates": replicates,
        "p_value": (exceedances + 1) / (replicates + 1),
        "block_length": block_length,
        "p_value_status": "sensitivity_only_not_calibrated_for_inference",
        "inferential_use_permitted": False,
        "ci_lower": None,
        "ci_upper": None,
        "ci_status": None,
    }

    if slope_interval:
        trend = slope * (years - years[0])
        bootstrap_values = samples + trend
        bootstrap_slopes = np.median(
            (bootstrap_values[:, right] - bootstrap_values[:, left])
            / (years[right] - years[left]),
            axis=1,
        )
        lower, upper = np.quantile(bootstrap_slopes, [0.025, 0.975])
        result["ci_lower"] = float(lower)
        result["ci_upper"] = float(upper)
        result["ci_status"] = "sensitivity_only_not_calibrated_for_inference"
    return result


def _load_annual_pixel_series(
    root: Path, start_year: int, end_year: int, minimum_observations: int
) -> dict[tuple[int, int], dict[int, float]]:
    source = root / "modis_ndvi" / "ndvi_pixel_observations.csv"
    grouped: dict[tuple[int, int, int], list[float]] = defaultdict(list)
    with source.open(newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            if item["quality_code"] != "0" or not item["ndvi"]:
                continue
            year = int(item["date"][:4])
            if start_year <= year <= end_year:
                pixel_year = (int(item["row"]), int(item["column"]), year)
                grouped[pixel_year].append(float(item["ndvi"]))

    annual: dict[tuple[int, int], dict[int, float]] = defaultdict(dict)
    for (row, column, year), values in grouped.items():
        if len(values) >= minimum_observations:
            annual[(row, column)][year] = float(np.median(values))
    return annual


def validate_artifact(
    root: Path,
    *,
    spatial_replicates: int = 5000,
    fixed_panel_replicates: int = 5000,
    block_lengths: tuple[int, ...] = (2, 3, 4),
    seed: int = 20261109,
    minimum_observations_per_year: int = 3,
) -> dict[str, object]:
    """Run spatial and fixed-panel bootstrap checks on an extracted artifact."""
    if not (root / "report.json").exists() and (root / "artifacts" / "report.json").exists():
        root = root / "artifacts"
    report_path = root / "report.json"
    trends_path = root / "modis_ndvi" / "ndvi_spatial_trends.csv"
    annual_path = root / "modis_ndvi" / "ndvi_annual_summary.csv"
    for path in (report_path, trends_path, annual_path, root / "modis_ndvi" / "ndvi_pixel_observations.csv"):
        if not path.exists():
            raise FileNotFoundError(path)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    period = report["modis_ndvi"]["trend_period"]
    start_year, end_year = int(period[0]), int(period[1])
    annual_pixels = _load_annual_pixel_series(
        root, start_year, end_year, minimum_observations_per_year
    )

    with trends_path.open(newline="", encoding="utf-8") as stream:
        trend_rows = list(csv.DictReader(stream))
    eligible = [
        item for item in trend_rows
        if item.get("temporal_eligible") == "True"
        or (
            item.get("temporal_eligible") is None
            and item.get("inferential_eligible") == "True"
        )
    ]
    if not eligible:
        raise ValueError("No temporally eligible pixels were found in the trend table.")

    per_pixel: list[dict[str, object]] = []
    bootstrap_p: dict[int, list[float]] = {length: [] for length in block_lengths}
    hamed_rao_significant: set[tuple[int, int]] = set()
    bootstrap_significant: dict[int, set[tuple[int, int]]] = {
        length: set() for length in block_lengths
    }

    skipped_short_or_gapped = 0
    for item in eligible:
        row, column = int(item["row"]), int(item["column"])
        series = annual_pixels.get((row, column), {})
        years = np.asarray(sorted(series), dtype=float)
        values = np.asarray([series[int(year)] for year in years], dtype=float)
        if len(years) < 10 or np.any(np.diff(years) != 1):
            skipped_short_or_gapped += 1
            continue

        hamed_rao_p = item.get("p_value_hamed_rao_sensitivity")
        hamed_rao_q = item.get("q_value_by")
        record: dict[str, object] = {
            "row": row,
            "column": column,
            "years": len(years),
            "sen_slope_ndvi_per_year": sen_slope(years, values),
            "hamed_rao_p_value_sensitivity": (
                float(hamed_rao_p) if hamed_rao_p not in (None, "") else None
            ),
            "hamed_rao_q_value_by_sensitivity": (
                float(hamed_rao_q) if hamed_rao_q not in (None, "") else None
            ),
            "inference_status": "withheld_pending_AR1_calibration",
            "inferential_use_permitted": False,
        }
        if item.get("by_q_le_0_05_in_eligible_family") == "True":
            hamed_rao_significant.add((row, column))

        for length in block_lengths:
            result = moving_block_bootstrap_mk(
                years, values,
                block_length=length,
                replicates=spatial_replicates,
                seed=seed + row * 100 + column + length * 100000,
            )
            record[f"p_block_{length}_sensitivity"] = result["p_value"]
            bootstrap_p[length].append(float(result["p_value"]))
        per_pixel.append(record)

    if not per_pixel:
        raise ValueError(
            "No temporally eligible pixels have at least ten consecutive annual observations "
            "after quality filtering; no bootstrap family was tested."
        )

    q_by_length = {
        length: benjamini_yekutieli(bootstrap_p[length])
        for length in block_lengths
    }
    for index, record in enumerate(per_pixel):
        flags = []
        for length in block_lengths:
            q_value = float(q_by_length[length][index])
            record[f"q_block_{length}_sensitivity"] = q_value
            flags.append(q_value <= 0.05)
            if q_value <= 0.05:
                bootstrap_significant[length].add((int(record["row"]), int(record["column"])))
        record["robust_sensitivity_q_le_0_05_all_block_lengths"] = all(flags)

    robust_all = set.intersection(*(bootstrap_significant[length] for length in block_lengths))
    length_three = 3 if 3 in block_lengths else block_lengths[0]
    overlap_l3 = hamed_rao_significant & bootstrap_significant[length_three]

    out_csv = root / "modis_ndvi" / "ndvi_block_bootstrap_validation.csv"
    fields = list(per_pixel[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(per_pixel)

    fixed_series: list[tuple[int, float]] = []
    with annual_path.open(newline="", encoding="utf-8") as stream:
        for item in csv.DictReader(stream):
            if item.get("fixed_panel_median"):
                fixed_series.append((int(item["year"]), float(item["fixed_panel_median"])))
    fixed_series.sort()
    fixed_years = np.asarray([year for year, _ in fixed_series], dtype=float)
    fixed_values = np.asarray([value for _, value in fixed_series], dtype=float)
    fixed_results = {
        str(length): moving_block_bootstrap_mk(
            fixed_years, fixed_values,
            block_length=length,
            replicates=fixed_panel_replicates,
            seed=seed + length * 100000,
            slope_interval=True,
        )
        for length in block_lengths
    }
    for result in fixed_results.values():
        result["p_value_interpretation"] = "sensitivity_only_not_calibrated_for_inference"
        result["ci_interpretation"] = "sensitivity_only_not_calibrated_for_inference"

    hamed_rao_count = len(hamed_rao_significant)
    summary: dict[str, object] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": (
            "Residual circular moving-block bootstrap after Sen detrending; two-sided "
            "Mann-Kendall S statistic; Benjamini-Yekutieli transform within the same "
            "temporally eligible pixel family. Diagnostic sensitivity only; not calibrated "
            "for inferential use under the tested AR(1) models."
        ),
        "inference_status": "withheld_pending_AR1_calibration",
        "inferential_use_permitted": False,
        "p_values_are_sensitivity_only": True,
        "by_q_values_are_sensitivity_only": True,
        "slope_intervals_are_sensitivity_only": True,
        "study_period": [start_year, end_year],
        "temporally_eligible_pixel_count": len(eligible),
        "bootstrap_eligible_pixel_family": len(per_pixel),
        "skipped_short_or_gapped_series": skipped_short_or_gapped,
        "spatial_replicates_per_pixel": spatial_replicates,
        "fixed_panel_replicates": fixed_panel_replicates,
        "block_lengths_years": list(block_lengths),
        "hamed_rao_by_q_le_0_05": hamed_rao_count,
        "bootstrap_sensitivity_q_le_0_05": {
            str(length): len(bootstrap_significant[length]) for length in block_lengths
        },
        "bootstrap_sensitivity_q_le_0_05_at_all_block_lengths": len(robust_all),
        "hamed_rao_diagnostic_overlap_with_block_length_3": len(overlap_l3),
        "hamed_rao_diagnostic_pixels_retained_by_all_block_lengths": len(
            hamed_rao_significant & robust_all
        ),
        "spatial_validation_csv": str(out_csv),
        "fixed_panel_block_bootstrap": fixed_results,
        "interpretation_limits": [
            "The residual bootstrap assumes the detrended residual process is sufficiently stationary.",
            "Circular block length is a sensitivity parameter; results are reported for multiple lengths.",
            "The current residual moving-block bootstrap is not calibrated for inferential use under the tested AR(1) null models.",
            "Its p-values, BY-transformed q-values and percentile slope intervals are sensitivity diagnostics only.",
            "BY adjustment does not repair uncalibrated input p-values and q<=0.05 must not be described as statistical significance.",
            "Hamed-Rao p-values are also diagnostic only and are excluded from the spatial BY inferential family.",
            "Bootstrap results apply only to pixels with at least ten consecutive annual observations and adequate quality coverage.",
        ],
    }
    out_json = root / "modis_ndvi" / "ndvi_block_bootstrap_validation.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["summary_json"] = str(out_json)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run offline moving-block bootstrap sensitivity checks on a NASA MODIS artifact."
    )
    parser.add_argument("artifact_dir", type=Path, help="Extracted artifact directory")
    parser.add_argument("--spatial-replicates", type=int, default=5000)
    parser.add_argument("--fixed-panel-replicates", type=int, default=5000)
    parser.add_argument("--block-lengths", default="2,3,4")
    parser.add_argument("--seed", type=int, default=20261109)
    parser.add_argument("--minimum-observations-per-year", type=int, default=3)
    args = parser.parse_args()
    lengths = tuple(int(value) for value in args.block_lengths.split(",") if value.strip())
    if not lengths or len(set(lengths)) != len(lengths):
        parser.error("--block-lengths must contain unique positive integers")
    if any(value < 1 for value in lengths):
        parser.error("--block-lengths must contain unique positive integers")
    summary = validate_artifact(
        args.artifact_dir,
        spatial_replicates=args.spatial_replicates,
        fixed_panel_replicates=args.fixed_panel_replicates,
        block_lengths=lengths,
        seed=args.seed,
        minimum_observations_per_year=args.minimum_observations_per_year,
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
