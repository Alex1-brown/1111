import unittest

from science_core.change_point import pettitt_test
from science_core.anomaly_analysis import robust_anomalies


class ChangePointTests(unittest.TestCase):
    def test_pettitt_detects_known_step_change(self):
        points = [(year, 1.0 if year < 2010 else 10.0) for year in range(2000, 2020)]
        result = pettitt_test(points)
        self.assertEqual(result["change_point_year"], 2010)
        self.assertLess(result["p_value"], 0.01)
        self.assertFalse(result["autocorrelation_adjusted"])

    def test_pettitt_constant_series_has_no_change_point(self):
        result = pettitt_test([(year, 5.0) for year in range(2000, 2010)])
        self.assertIsNone(result["change_point_year"])
        self.assertEqual(result["p_value"], 1.0)

    def test_pettitt_small_series_returns_unavailable(self):
        result = pettitt_test([(2020, 1), (2021, 2), (2022, 3)])
        self.assertIsNone(result["p_value"])

    def test_pettitt_rejects_duplicate_years_and_nonfinite_values(self):
        with self.assertRaises(ValueError):
            pettitt_test([(2020, 1), (2020, 2), (2021, 3), (2022, 4)])
        with self.assertRaises(ValueError):
            pettitt_test([(2020, float("nan")), (2021, 2), (2022, 3), (2023, 4)])


class RobustAnomalyTests(unittest.TestCase):
    def test_modified_z_detects_extreme_value(self):
        values = [(f"2024-01-{day:02d}", 10.0) for day in range(1, 11)]
        values[-1] = ("2024-01-10", 100.0)
        result = robust_anomalies(values)
        self.assertTrue(result[-1]["is_anomaly"])
        self.assertFalse(result[0]["is_anomaly"])

    def test_zero_mad_does_not_flag_constant_series(self):
        result = robust_anomalies([("a", 3), ("b", 3), ("c", 3)])
        self.assertTrue(all(not row["is_anomaly"] for row in result))
        self.assertEqual(result[0]["mad"], 0)

    def test_invalid_threshold_and_nonfinite_values_fail(self):
        with self.assertRaises(ValueError):
            robust_anomalies([("a", 1)], 0)
        with self.assertRaises(ValueError):
            robust_anomalies([("a", float("inf"))])


if __name__ == "__main__":
    unittest.main()
