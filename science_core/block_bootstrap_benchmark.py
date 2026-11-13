"""Monte Carlo calibration of the repository's residual moving-block bootstrap.

The benchmark uses synthetic stationary Gaussian AR(1) errors only. It does
not generate or imitate satellite observations. It evaluates the exact
moving_block_bootstrap_mk implementation used by the artifact sensitivity
analysis, without tuning its settings.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Sequence

import numpy as np

from .bootstrap_validation import moving_block_bootstrap_mk
from .serial_correlation_benchmark import simulate_ar1, wilson_interval_95

DEFAULT_SAMPLE_SIZES = (20, 60)
DEFAULT_PHIS = (-0.4, 0.0, 0.4, 0.7)
DEFAULT_BLOCK_LENGTHS = (2, 3, 4)
DEFAULT_OUTER_REPLICATES = 200
DEFAULT_BOOTSTRAP_REPLICATES = 399
DEFAULT_SEED = 20261113
DEFAULT_TRUE_SLOPE = 0.01
ALPHA = 0.05


def run_block_bootstrap_calibration(
    sample_sizes: Sequence[int] = DEFAULT_SAMPLE_SIZES,
    phis: Sequence[float] = DEFAULT_PHIS,
    block_lengths: Sequence[int] = DEFAULT_BLOCK_LENGTHS,
    outer_replicates: int = DEFAULT_OUTER_REPLICATES,
    bootstrap_replicates: int = DEFAULT_BOOTSTRAP_REPLICATES,
    seed: int = DEFAULT_SEED,
    true_slope: float = DEFAULT_TRUE_SLOPE,
) -> dict[str, object]:
    """Measure null rejection and Sen-interval coverage for AR(1) models.

    Null experiments have zero deterministic slope. Coverage experiments use
    a known linear slope plus an independent AR(1) error process. Each result
    is conditional on the stated Gaussian AR(1) model and chosen block length.
    """
    if not sample_sizes or any(int(n) < 10 for n in sample_sizes):
        raise ValueError("Every sample size must be at least 10.")
    if not phis or any(not math.isfinite(float(phi)) or abs(float(phi)) >= 1 for phi in phis):
        raise ValueError("Every AR(1) phi must be finite and strictly between -1 and 1.")
    if not block_lengths or any(int(length) < 1 for length in block_lengths):
        raise ValueError("Block lengths must be positive.")
    if any(int(length) > max(int(n) for n in sample_sizes) for length in block_lengths):
        raise ValueError("A block length cannot exceed the largest sample size.")
    if outer_replicates < 1 or bootstrap_replicates < 100:
        raise ValueError("Require outer_replicates >= 1 and bootstrap_replicates >= 100.")
    if not math.isfinite(true_slope):
        raise ValueError("true_slope must be finite.")

    scenarios: list[dict[str, object]] = []
    scenario_index = 0
    for n_raw in sample_sizes:
        n = int(n_raw)
        years = np.arange(2000.0, 2000.0 + n)
        for phi_raw in phis:
            phi = float(phi_raw)
            rng = random.Random(seed + scenario_index * 104729)
            scenario_index += 1
            counts = {
                int(length): {
                    "null_rejections": 0,
                    "ci_covered": 0,
                    "ci_interval_failures": 0,
                }
                for length in block_lengths
            }

            for outer_index in range(outer_replicates):
                null_values = np.asarray(simulate_ar1(n, phi, rng), dtype=float)
                trend_noise = np.asarray(simulate_ar1(n, phi, rng), dtype=float)
                trend_values = true_slope * (years - years[0]) + trend_noise

                for length_raw in block_lengths:
                    length = int(length_raw)
                    null_seed = (
                        seed + scenario_index * 1_000_003
                        + outer_index * 10_007 + length * 101
                    )
                    ci_seed = null_seed + 50_000_003
                    null_result = moving_block_bootstrap_mk(
                        years, null_values,
                        block_length=length,
                        replicates=bootstrap_replicates,
                        seed=null_seed,
                    )
                    ci_result = moving_block_bootstrap_mk(
                        years, trend_values,
                        block_length=length,
                        replicates=bootstrap_replicates,
                        seed=ci_seed,
                        slope_interval=True,
                    )
                    current = counts[length]
                    current["null_rejections"] += float(null_result["p_value"]) < ALPHA
                    lower = ci_result["ci_lower"]
                    upper = ci_result["ci_upper"]
                    if lower is None or upper is None:
                        current["ci_interval_failures"] += 1
                    else:
                        current["ci_covered"] += float(lower) <= true_slope <= float(upper)

            for length_raw in block_lengths:
                length = int(length_raw)
                current = counts[length]
                rejection_rate = current["null_rejections"] / outer_replicates
                coverage_rate = current["ci_covered"] / outer_replicates
                rejection_interval = wilson_interval_95(
                    current["null_rejections"], outer_replicates
                )
                coverage_interval = wilson_interval_95(
                    current["ci_covered"], outer_replicates
                )
                scenarios.append({
                    "sample_size": n,
                    "ar1_phi": phi,
                    "block_length": length,
                    "outer_replicates": outer_replicates,
                    "bootstrap_replicates_per_fit": bootstrap_replicates,
                    "nominal_alpha": ALPHA,
                    "true_sen_slope_per_year": true_slope,
                    "null_rejections": current["null_rejections"],
                    "null_empirical_rejection_rate": rejection_rate,
                    "null_wilson_95": list(rejection_interval),
                    "slope_ci_covered": current["ci_covered"],
                    "slope_ci_empirical_coverage": coverage_rate,
                    "slope_ci_wilson_95": list(coverage_interval),
                    "slope_ci_interval_failures": current["ci_interval_failures"],
                })

    return {
        "benchmark": "residual circular moving-block bootstrap AR(1) calibration",
        "data_type": "synthetic statistical experiments; not satellite observations",
        "method_under_test": "science_core.bootstrap_validation.moving_block_bootstrap_mk",
        "method_note": (
            "The implementation is evaluated unchanged. Null p-values are tested "
            "under zero-trend stationary Gaussian AR(1) series. Slope intervals are "
            "tested on a known linear trend plus independent AR(1) errors. Results "
            "are conditional on the stated model, sample sizes and block lengths."
        ),
        "seed": seed,
        "nominal_alpha": ALPHA,
        "sample_sizes": [int(n) for n in sample_sizes],
        "ar1_phi_values": [float(phi) for phi in phis],
        "block_lengths": [int(length) for length in block_lengths],
        "outer_replicates": outer_replicates,
        "bootstrap_replicates_per_fit": bootstrap_replicates,
        "true_sen_slope_per_year": true_slope,
        "scenarios": scenarios,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calibrate the current moving-block bootstrap under Gaussian AR(1) models."
    )
    parser.add_argument("--n", nargs="+", type=int, default=list(DEFAULT_SAMPLE_SIZES))
    parser.add_argument("--phi", nargs="+", type=float, default=list(DEFAULT_PHIS))
    parser.add_argument("--block-lengths", nargs="+", type=int, default=list(DEFAULT_BLOCK_LENGTHS))
    parser.add_argument("--outer-replicates", type=int, default=DEFAULT_OUTER_REPLICATES)
    parser.add_argument("--bootstrap-replicates", type=int, default=DEFAULT_BOOTSTRAP_REPLICATES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--true-slope", type=float, default=DEFAULT_TRUE_SLOPE)
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    args = parser.parse_args(argv)

    result = run_block_bootstrap_calibration(
        sample_sizes=args.n,
        phis=args.phi,
        block_lengths=args.block_lengths,
        outer_replicates=args.outer_replicates,
        bootstrap_replicates=args.bootstrap_replicates,
        seed=args.seed,
        true_slope=args.true_slope,
    )
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
