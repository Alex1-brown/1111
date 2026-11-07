import unittest

from science_core.cross_source_analysis import analyze_monthly_cross_source


class CrossSourceAnalysisTests(unittest.TestCase):
    def test_monthly_alignment_and_anomaly_correlations(self):
        temp, rain, ndvi = [], [], []
        for year in range(2020, 2025):
            offset = year - 2022
            for month in range(1, 13):
                date = f"{year}{month:02d}15"
                temp.append((date, 10 + month + offset))
                rain.append((date, 20 + month * 2 + offset * 3))
                ndvi.append((0, 0, date, 0.2 + month * 0.01 + offset * 0.02))
        result = analyze_monthly_cross_source(temp, rain, ndvi, 2020, 2024)
        self.assertEqual(result["common_months"], 60)
        corr = result["anomaly_correlations"]
        self.assertAlmostEqual(corr["ndvi_vs_temperature_pearson_r"], 1.0)
        self.assertGreater(corr["ndvi_vs_temperature_spearman_rho"], 0.98)
        self.assertAlmostEqual(corr["ndvi_vs_precipitation_pearson_r"], 1.0)
        self.assertEqual(corr["lagged_pair_count"], 59)
        self.assertIn("ndvi_vs_temperature_pearson_r", result["detrended_anomaly_correlations"])

    def test_no_common_months_returns_null_correlations(self):
        result = analyze_monthly_cross_source(
            [("20200101", 1)], [("20200101", 2)], [(0, 0, "20210101", 0.4)],
            2020, 2021,
        )
        self.assertEqual(result["common_months"], 0)
        self.assertIsNone(result["anomaly_correlations"]["ndvi_vs_temperature_pearson_r"])

    def test_invalid_dates_and_year_range_fail(self):
        with self.assertRaises(ValueError):
            analyze_monthly_cross_source([], [], [], 2025, 2020)
        with self.assertRaises(ValueError):
            analyze_monthly_cross_source([("2020-01-01", 1)], [], [], 2020, 2021)


if __name__ == "__main__":
    unittest.main()
