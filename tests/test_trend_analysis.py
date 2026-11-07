import unittest

from science_core.trend_analysis import mann_kendall, seasonal_mann_kendall
from science_core.statistical_analysis import analyze_power_timeseries


class TrendAnalysisTests(unittest.TestCase):
    def test_monotonic_increasing_series(self):
        result = mann_kendall([(2000, 1), (2001, 2), (2002, 3), (2003, 4), (2004, 5)])
        self.assertEqual(result["kendall_s"], 10)
        self.assertAlmostEqual(result["sen_slope_per_year"], 1.0)
        self.assertAlmostEqual(result["p_value_two_sided"], 2 / 120)
        self.assertEqual(result["method"], "Exact permutation Mann-Kendall")

    def test_monotonic_decreasing_series(self):
        result = mann_kendall([(2000, 5), (2001, 4), (2002, 3), (2003, 2), (2004, 1)])
        self.assertEqual(result["kendall_s"], -10)
        self.assertAlmostEqual(result["sen_slope_per_year"], -1.0)

    def test_ties_reduce_variance_and_zero_trend(self):
        result = mann_kendall([(1, 2), (2, 2), (3, 2), (4, 2)])
        self.assertEqual(result["kendall_s"], 0)
        self.assertEqual(result["p_value_two_sided"], 1.0)
        self.assertEqual(result["sen_slope_per_year"], 0.0)

    def test_duplicate_time_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            mann_kendall([(2000, 1), (2000, 2), (2001, 3)])

    def test_seasonal_mk_aggregates_monthly_temperature(self):
        rows = []
        for year in range(2020, 2025):
            for month in range(1, 13):
                rows.append((f"{year}{month:02d}15", 10 + (year - 2020) + month))
        result = seasonal_mann_kendall(rows, aggregation="mean")
        self.assertEqual(result["calendar_months"], 12)
        self.assertEqual(result["years"], 5)
        self.assertAlmostEqual(result["sen_slope_per_year"], 1.0)
        self.assertEqual(result["kendall_s"], 120)

    def test_seasonal_mk_precipitation_monthly_totals(self):
        rows = []
        for year in range(2020, 2025):
            for month in range(1, 13):
                rows.extend([
                    (f"{year}{month:02d}01", 1 + year - 2020),
                    (f"{year}{month:02d}02", 2 + year - 2020),
                ])
        result = seasonal_mann_kendall(rows, aggregation="sum")
        self.assertAlmostEqual(result["sen_slope_per_year"], 2.0)
        self.assertEqual(result["aggregation"], "sum")

    def test_time_series_report_includes_nonparametric_trends(self):
        temperature = []
        precipitation = []
        for year in range(2020, 2025):
            for month in range(1, 13):
                date = f"{year}{month:02d}15"
                temperature.append((date, float(year - 2019 + month)))
                precipitation.append((date, float((year - 2019) * 2 + month)))
        report = analyze_power_timeseries(temperature, precipitation)
        trends = report["nonparametric_trends"]
        self.assertIn("annual_temperature_mann_kendall_sen", trends)
        self.assertIn("seasonal_temperature_mann_kendall_sen", trends)
        self.assertEqual(
            trends["annual_temperature_mann_kendall_sen"]["method"],
            "Exact permutation Mann-Kendall",
        )

    def test_invalid_aggregation_and_dates(self):
        with self.assertRaises(ValueError):
            seasonal_mann_kendall([("20200101", 1)], "median")
        with self.assertRaises(ValueError):
            seasonal_mann_kendall([("20201301", 1)])


if __name__ == "__main__":
    unittest.main()
