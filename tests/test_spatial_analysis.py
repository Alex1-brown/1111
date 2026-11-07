import unittest

from science_core.spatial_analysis import (
    annual_pixel_medians, analyze_pixel_trends, benjamini_yekutieli,
    sinusoidal_pixel_center, sinusoidal_pixel_center_from_origin, summarize_fixed_annual_panel,
    select_complete_year_range,
)


class SpatialAnalysisTests(unittest.TestCase):
    def test_by_adjustment_preserves_order_and_missing(self):
        result = benjamini_yekutieli([0.01, None, 0.04, 0.03])
        self.assertIsNone(result[1])
        self.assertAlmostEqual(result[0], 0.055)
        self.assertAlmostEqual(result[2], 0.0733333333333)
        self.assertAlmostEqual(result[3], 0.0733333333333)

    def test_by_adjustment_rejects_invalid_p_values(self):
        with self.assertRaises(ValueError):
            benjamini_yekutieli([1.1])

    def test_annual_medians_filter_fill_and_out_of_range(self):
        records = [
            (0, 0, "20200101", 0.2),
            (0, 0, "20200701", 0.4),
            (0, 0, "20210101", 0.3),
            (0, 0, "20220101", -3000),
            (0, 1, "20200101", 1.2),
        ]
        result = annual_pixel_medians(records)
        self.assertEqual([year for year, _ in result[(0, 0)]], [2020, 2021])
        self.assertAlmostEqual(result[(0, 0)][0][1], 0.3)
        self.assertAlmostEqual(result[(0, 0)][1][1], 0.3)
        self.assertNotIn((0, 1), result)

    def test_annual_medians_require_minimum_composite_count_when_requested(self):
        records = [
            (0, 0, "20200101", 0.2),
            (0, 0, "20200601", 0.4),
            (0, 0, "20201201", 0.6),
            (0, 0, "20210101", 0.3),
        ]
        result = annual_pixel_medians(records, minimum_observations_per_year=2)
        self.assertEqual([year for year, _ in result[(0, 0)]], [2020])
        with self.assertRaises(ValueError):
            annual_pixel_medians(records, minimum_observations_per_year=0)

    def test_pixel_trends_and_fdr(self):
        data = {
            (0, 0): [(year, 0.2 + 0.01 * (year - 2000)) for year in range(2000, 2025)],
            (0, 1): [(year, 0.5) for year in range(2000, 2025)],
        }
        result = analyze_pixel_trends(data, minimum_years=15)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]["sen_slope_ndvi_per_year"], 0.01)
        self.assertTrue(result[0]["by_q_le_0_05_temporal_uncorrected"])
        self.assertFalse(result[1]["by_q_le_0_05_temporal_uncorrected"])

    def test_complete_year_range_excludes_partial_years(self):
        dates = (
            ["2001-01-15"] * 5 + ["2002-01-15"] * 10
            + [f"{year}-{month:02d}-15" for year in range(2003, 2024) for month in range(1, 13)]
            + ["2024-01-15", "2024-02-15", "2025-06-15", "2025-11-15", "2025-12-15"]
        )
        start, end, counts = select_complete_year_range(dates, 11, 15)
        self.assertEqual((start, end), (2003, 2023))
        self.assertEqual(counts[2024], 2)
        self.assertEqual(counts[2025], 3)

    def test_complete_year_range_requires_long_enough_period(self):
        with self.assertRaises(ValueError):
            select_complete_year_range(["2020-01-15", "2021-01-15"], 11, 3)

    def test_fixed_panel_uses_only_pixels_with_all_requested_years(self):
        data = {
            (0, 0): [(year, year / 100.0) for year in range(2001, 2026)],
            (0, 1): [(year, year / 100.0) for year in range(2001, 2025)],
            (0, 2): [(year, year / 100.0) for year in range(2002, 2026)],
        }
        rows, count = summarize_fixed_annual_panel(data, 2001, 2025)
        self.assertEqual(count, 1)
        self.assertTrue(all(row["fixed_panel_pixels"] == 1 for row in rows))
        self.assertAlmostEqual(rows[0]["fixed_panel_median"], 20.01)

    def test_sinusoidal_grid_center_matches_requested_center(self):
        lon, lat = sinusoidal_pixel_center(38.5598, 68.787, 4, 4, 9, 9, 231.656)
        self.assertAlmostEqual(lon, 68.787, places=10)
        self.assertAlmostEqual(lat, 38.5598, places=10)

    def test_exact_origin_grid_center_matches_expected_location(self):
        from math import cos, pi
        from science_core.spatial_analysis import MODIS_SINUSOIDAL_RADIUS_M
        latitude, longitude, cell = 38.5598, 68.787, 231.656
        lat_r, lon_r = latitude * pi / 180, longitude * pi / 180
        x_center = MODIS_SINUSOIDAL_RADIUS_M * lon_r * cos(lat_r)
        y_center = MODIS_SINUSOIDAL_RADIUS_M * lat_r
        xll = x_center - 4.5 * cell
        yll = y_center - 4.5 * cell
        lon, lat = sinusoidal_pixel_center_from_origin(xll, yll, 4, 4, 9, 9, cell)
        self.assertAlmostEqual(lon, longitude, places=9)
        self.assertAlmostEqual(lat, latitude, places=9)

    def test_sinusoidal_grid_adjacent_pixel_moves(self):
        center = sinusoidal_pixel_center(38.5598, 68.787, 4, 4, 9, 9, 231.656)
        east = sinusoidal_pixel_center(38.5598, 68.787, 4, 5, 9, 9, 231.656)
        self.assertGreater(east[0], center[0])
        self.assertAlmostEqual(east[1], center[1], places=5)


if __name__ == "__main__":
    unittest.main()
