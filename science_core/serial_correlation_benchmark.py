"""Monte Carlo calibration checks for the project's Mann-Kendall inference.

This is an algorithm benchmark only. It generates stationary Gaussian AR(1)
null series with no deterministic trend; it does not generate or imitate
satellite observations.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from statistics import mean
from typing import Sequence

from .trend_analysis import mann_kendall

ALPHA = 0.05
DEFAULT_SAMPLE_SIZES = (20, 60)
DEFAULT_PHIS = (-0.7, -0.4, 0.0, 0.4, 0.7)
DEFAULT_REPLICATES = 2000
DEFAULT_SEED = 20261112


def simulate_ar1(
    sample_size: int,
    phi: float,
    rng: random.Random,
) -> list[float]:
    """Generate a stationary Gaussian AR(1) series with unit marginal variance."""
    if sample_size < 2:
        raise ValueError("sample_size must be at least 2.")
    if not math.isfinite(phi) or abs(phi) >= 1.0:
        raise ValueError("phi must be finite and strictly between -1 and 1.")

    innovation_sd = math.sqrt(1.0 - phi * phi)
    values = [rng.gauss(0.0, 1.0)]
    for _ in range(1, sample_size):
        values.append(phi * values[-1] + innovation_sd * rng.gauss(0.0, 1.0))
    return values


def wilson_interval_95(successes: int, total: int) -> tuple[float, float]:
    """Two-sided 95% Wilson score interval for a binomial proportion."""
    if total < 1 or not 0 <= successes <= total:
        raise ValueError("Require total >= 1 and 0 <= successes <= total.")
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    half_width = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def run_ar1_calibration(
    sample_sizes: Sequence[int] = DEFAULT_SAMPLE_SIZES,
    phis: Sequence[float] = DEFAULT_PHIS,
    replicates: int = DEFAULT_REPLICATES,
    seed: int = DEFAULT_SEED,
) -> dict[str, object]:
    """Compare iid and current reported MK p-values under zero-trend AR(1) nulls.

    The project's Hamed-Rao lag-selection rule is left unchanged. The returned
    rates are model-specific empirical rejection frequencies, not universal
    guarantees for environmental time series.
    """
    if not sample_sizes or any(int(size) < 10 for size in sample_sizes):
        raise ValueError("Every sample size must be at least 10.")
    if not phis or any(not math.isfinite(float(phi)) or abs(float(phi)) >= 1.0 for phi in phis):
        raise ValueError("Every phi must be finite and strictly between -1 and 1.")
    if replicates < 1:
        raise ValueError("replicates must be at least 1.")

    scenarios: list[dict[str, object]] = []
    scenario_index = 0
    for sample_size in sample_sizes:
        for phi in phis:
            rng = random.Random(seed + scenario_index * 104729)
            scenario_index += 1
            iid_rejections = 0
            reported_rejections = 0
            adjusted_count = 0
            nonpositive_fallbacks = 0
            variance_factors: list[float] = []

            for _ in range(replicates):
                values = simulate_ar1(int(sample_size), float(phi), rng)
                points = [(float(index), value) for index, value in enumerate(values)]
                result = mann_kendall(points)
                iid_p = result["p_value_two_sided_iid"]
                reported_p = result["p_value_two_sided"]
                if iid_p is None or reported_p is None:
                    raise RuntimeError("Mann-Kendall returned a missing p-value for a valid series.")

                iid_rejections += float(iid_p) < ALPHA
                reported_rejections += float(reported_p) < ALPHA
                if result["serial_correlation_adjusted"]:
                    adjusted_count += 1
                    factor = result["serial_correlation_variance_factor"]
                    if factor is not None:
                        variance_factors.append(float(factor))
                elif result["serial_correlation_status"] == "nonpositive_variance_factor":
                    nonpositive_fallbacks += 1

            iid_low, iid_high = wilson_interval_95(iid_rejections, replicates)
            reported_low, reported_high = wilson_interval_95(reported_rejections, replicates)
            scenarios.append({
                "sample_size": int(sample_size),
                "ar1_phi": float(phi),
                "replicates": replicates,
                "nominal_alpha": ALPHA,
                "iid_rejections": iid_rejections,
                "iid_empirical_rate": iid_rejections / replicates,
                "iid_wilson_95": [iid_low, iid_high],
                "reported_rejections": reported_rejections,
                "reported_empirical_rate": reported_rejections / replicates,
                "reported_wilson_95": [reported_low, reported_high],
                "hamed_rao_applied_fraction": adjusted_count / replicates,
                "mean_applied_variance_factor": (
                    mean(variance_factors) if variance_factors else None
                ),
                "nonpositive_factor_fallback_count": nonpositive_fallbacks,
            })

    return {
        "benchmark": "zero-trend stationary Gaussian AR(1) Monte Carlo",
        "data_type": "synthetic statistical null series; not satellite observations",
        "marginal_variance": 1.0,
        "nominal_alpha": ALPHA,
        "seed": seed,
        "replicates_per_scenario": replicates,
        "sample_sizes": [int(value) for value in sample_sizes],
        "ar1_phi_values": [float(value) for value in phis],
        "method_note": (
            "iid p-values are compared with the project's current reported p-values. "
            "Hamed-Rao uses the repository's signed rank-autocorrelation sum and its "
            "existing 95% lag-selection threshold; no method parameters are changed."
        ),
        "scenarios": scenarios,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calibrate Mann-Kendall inference under stationary Gaussian AR(1) null series."
    )
    parser.add_argument("--n", nargs="+", type=int, default=list(DEFAULT_SAMPLE_SIZES))
    parser.add_argument("--phi", nargs="+", type=float, default=list(DEFAULT_PHIS))
    parser.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    args = parser.parse_args(argv)

    result = run_ar1_calibration(args.n, args.phi, args.replicates, args.seed)
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
