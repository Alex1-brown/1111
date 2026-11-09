import unittest

import numpy as np

from science_core.bootstrap_validation import (
    benjamini_yekutieli,
    mann_kendall_score,
    moving_block_bootstrap_mk,
    sen_slope,
)


class BootstrapValidationTests(unittest.TestCase):
    def test_mann_kendall_score_direction(self):
        self.assertEqual(mann_kendall_score(np.array([1.0, 2.0, 3.0])), 3)
        self.assertEqual(mann_kendall_score(np.array([3.0, 2.0, 1.0])), -3)

    def test_sen_slope_uses_actual_year_spacing(self):
        years = np.array([2000.0, 2001.0, 2003.0])
        values = np.array([1.0, 2.0, 4.0])
        self.assertAlmostEqual(sen_slope(years, values), 1.0)

    def test_by_adjustment_is_bounded_and_monotone_in_rank_order(self):
        p_values = np.array([0.03, 0.001, 0.2, 0.04])
        q_values = benjamini_yekutieli(p_values)
        self.assertTrue(np.all((q_values >= 0) & (q_values <= 1)))
        order = np.argsort(p_values)
        self.assertTrue(np.all(np.diff(q_values[order]) >= -1e-12))

    def test_block_bootstrap_is_reproducible_and_recovers_clear_trend(self):
        years = np.arange(2000.0, 2012.0)
        values = np.array([0.1, 0.13, 0.12, 0.16, 0.17, 0.18,
                           0.20, 0.22, 0.21, 0.25, 0.27, 0.28])
        first = moving_block_bootstrap_mk(
            years, values, block_length=2, replicates=400, seed=123, slope_interval=True
        )
        second = moving_block_bootstrap_mk(
            years, values, block_length=2, replicates=400, seed=123, slope_interval=True
        )
        self.assertEqual(first, second)
        self.assertLess(first["p_value"], 0.05)
        self.assertGreater(first["ci_lower"], 0.0)
        self.assertGreater(first["ci_upper"], first["ci_lower"])


if __name__ == "__main__":
    unittest.main()
