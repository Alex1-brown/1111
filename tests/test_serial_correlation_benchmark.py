import random
import unittest

from science_core.serial_correlation_benchmark import (
    run_ar1_calibration,
    simulate_ar1,
    wilson_interval_95,
)


class SerialCorrelationBenchmarkTests(unittest.TestCase):
    def test_ar1_generator_is_reproducible_and_finite(self):
        first = simulate_ar1(30, -0.4, random.Random(123))
        second = simulate_ar1(30, -0.4, random.Random(123))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 30)
        self.assertTrue(all(value == value for value in first))

    def test_wilson_interval_contains_observed_proportion(self):
        lower, upper = wilson_interval_95(5, 100)
        self.assertLessEqual(lower, 0.05)
        self.assertGreaterEqual(upper, 0.05)
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)

    def test_calibration_is_deterministic_and_reports_both_tests(self):
        first = run_ar1_calibration(
            sample_sizes=(10,),
            phis=(0.0, 0.4),
            replicates=30,
            seed=19,
        )
        second = run_ar1_calibration(
            sample_sizes=(10,),
            phis=(0.0, 0.4),
            replicates=30,
            seed=19,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first["scenarios"]), 2)
        for scenario in first["scenarios"]:
            self.assertEqual(scenario["replicates"], 30)
            self.assertGreaterEqual(scenario["iid_empirical_rate"], 0.0)
            self.assertLessEqual(scenario["iid_empirical_rate"], 1.0)
            self.assertGreaterEqual(scenario["reported_empirical_rate"], 0.0)
            self.assertLessEqual(scenario["reported_empirical_rate"], 1.0)
            self.assertEqual(len(scenario["iid_wilson_95"]), 2)
            self.assertEqual(len(scenario["reported_wilson_95"]), 2)

    def test_invalid_ar1_and_calibration_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            simulate_ar1(20, 1.0, random.Random(1))
        with self.assertRaises(ValueError):
            run_ar1_calibration(sample_sizes=(9,), replicates=10)
        with self.assertRaises(ValueError):
            run_ar1_calibration(phis=(-1.0,), replicates=10)
        with self.assertRaises(ValueError):
            run_ar1_calibration(replicates=0)


if __name__ == "__main__":
    unittest.main()
