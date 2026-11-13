import unittest

from science_core.block_bootstrap_benchmark import run_block_bootstrap_calibration


class BlockBootstrapBenchmarkTests(unittest.TestCase):
    def test_small_calibration_is_reproducible_and_reports_coverage(self):
        kwargs = {
            "sample_sizes": (10,),
            "phis": (0.0,),
            "block_lengths": (2,),
            "outer_replicates": 8,
            "bootstrap_replicates": 100,
            "seed": 77,
        }
        first = run_block_bootstrap_calibration(**kwargs)
        second = run_block_bootstrap_calibration(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(len(first["scenarios"]), 1)
        scenario = first["scenarios"][0]
        self.assertEqual(scenario["outer_replicates"], 8)
        self.assertEqual(scenario["bootstrap_replicates_per_fit"], 100)
        self.assertGreaterEqual(scenario["null_empirical_rejection_rate"], 0.0)
        self.assertLessEqual(scenario["null_empirical_rejection_rate"], 1.0)
        self.assertGreaterEqual(scenario["slope_ci_empirical_coverage"], 0.0)
        self.assertLessEqual(scenario["slope_ci_empirical_coverage"], 1.0)
        self.assertEqual(len(scenario["null_wilson_95"]), 2)
        self.assertEqual(len(scenario["slope_ci_wilson_95"]), 2)

    def test_invalid_calibration_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            run_block_bootstrap_calibration(sample_sizes=(9,))
        with self.assertRaises(ValueError):
            run_block_bootstrap_calibration(phis=(1.0,))
        with self.assertRaises(ValueError):
            run_block_bootstrap_calibration(block_lengths=(0,))
        with self.assertRaises(ValueError):
            run_block_bootstrap_calibration(bootstrap_replicates=99)


if __name__ == "__main__":
    unittest.main()
