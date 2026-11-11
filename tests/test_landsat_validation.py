import unittest
from datetime import date

import numpy as np

from science_core.landsat_validation import (
    INVALID_QA_PIXEL_BITS,
    QA_RADSAT_REJECT_BITS,
    _average_ranks,
    _geometry_covers_window,
    _paired_error_metrics,
    _qa_flag_counts,
    _raster_window_coverage_fraction,
    _pearson,
    _spearman,
    ndvi_from_landsat_arrays,
    _nearest_modis_composite,
    _landsat_bootstrap_eligibility,
)


class LandsatValidationTests(unittest.TestCase):
    def test_landsat_pairs_with_nearest_same_year_modis_composite(self):
        composites = {
            date(2018, 7, 12): [0.2, 0.4, 0.6],
            date(2018, 8, 12): [0.3, 0.5, 0.7],
            date(2019, 7, 12): [0.1, 0.2, 0.3],
        }
        match = _nearest_modis_composite(composites, date(2018, 7, 15), 24)
        self.assertEqual(match, (date(2018, 7, 12), 0.4, -3))

    def test_landsat_modis_pairing_rejects_large_date_gap_and_other_year(self):
        composites = {date(2018, 6, 1): [0.2, 0.3, 0.4]}
        self.assertIsNone(
            _nearest_modis_composite(composites, date(2018, 7, 15), 24)
        )
        self.assertIsNone(
            _nearest_modis_composite(composites, date(2019, 6, 1), 24)
        )

    def test_landsat_modis_pairing_rejects_negative_tolerance(self):
        with self.assertRaises(ValueError):
            _nearest_modis_composite({}, date(2018, 7, 15), -1)

    def test_clear_pixel_uses_collection_two_scale_and_offset(self):
        red = np.array([[15000, 15000]], dtype=np.uint16)
        nir = np.array([[25000, 25000]], dtype=np.uint16)
        qa = np.array([[0, 1 << 3]], dtype=np.uint16)
        saturation = np.zeros((1, 2), dtype=np.uint16)
        aerosol = np.zeros((1, 2), dtype=np.uint16)
        ndvi, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation, aerosol)
        expected_red = 15000 * 0.0000275 - 0.2
        expected_nir = 25000 * 0.0000275 - 0.2
        expected = (expected_nir - expected_red) / (expected_nir + expected_red)
        self.assertTrue(valid[0, 0])
        self.assertAlmostEqual(float(ndvi[0, 0]), expected)
        self.assertFalse(valid[0, 1])
        self.assertTrue(np.isnan(ndvi[0, 1]))

    def test_all_invalid_qa_bits_are_excluded(self):
        red = np.full((1, 7), 15000, dtype=np.uint16)
        nir = np.full((1, 7), 25000, dtype=np.uint16)
        qa = np.array([[1 << bit for bit in (0, 1, 2, 3, 4, 5, 7)]], dtype=np.uint16)
        saturation = np.zeros((1, 7), dtype=np.uint16)
        aerosol = np.zeros((1, 7), dtype=np.uint16)
        _, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation, aerosol)
        self.assertEqual(int(valid.sum()), 0)
        self.assertEqual(INVALID_QA_PIXEL_BITS, 191)

    def test_saturation_is_band_specific_and_terrain_occlusion_is_excluded(self):
        red = np.array([[0, 15000, 15000, 15000, 15000]], dtype=np.uint16)
        nir = np.full((1, 5), 25000, dtype=np.uint16)
        qa = np.zeros((1, 5), dtype=np.uint16)
        # Band 1 saturation is unrelated to the red/NIR NDVI calculation.
        saturation = np.array([[0, 1 << 0, 1 << 3, 1 << 4, 1 << 11]], dtype=np.uint16)
        aerosol = np.zeros((1, 5), dtype=np.uint16)
        _, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation, aerosol)
        self.assertEqual(valid.tolist(), [[False, True, False, False, False]])
        self.assertEqual(QA_RADSAT_REJECT_BITS, (1 << 3) | (1 << 4) | (1 << 11))

    def test_water_is_excluded_and_interpolated_aerosol_is_retained_by_default(self):
        red = np.full((1, 4), 15000, dtype=np.uint16)
        nir = np.full((1, 4), 25000, dtype=np.uint16)
        qa = np.array([[1 << 7, 0, 0, 0]], dtype=np.uint16)
        saturation = np.zeros((1, 4), dtype=np.uint16)
        aerosol = np.array([[0, 1 << 2, 1 << 5, 0]], dtype=np.uint16)
        _, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation, aerosol)
        self.assertEqual(valid.tolist(), [[False, False, True, True]])

    def test_high_aerosol_and_aerosol_fill_are_excluded(self):
        red = np.full((1, 6), 15000, dtype=np.uint16)
        nir = np.full((1, 6), 25000, dtype=np.uint16)
        qa = np.zeros((1, 6), dtype=np.uint16)
        saturation = np.zeros((1, 6), dtype=np.uint16)
        # 0 = climatology, 01 = low, 11 = high, bit 0 = fill.
        # Interpolated aerosol is retained by default and can be screened explicitly.
        aerosol = np.array([[0, 1 << 6, 3 << 6, 1, 1 << 1, 1 << 5]], dtype=np.uint16)
        _, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation, aerosol)
        self.assertEqual(valid.tolist(), [[True, True, False, False, True, True]])
        _, strict_valid = ndvi_from_landsat_arrays(
            red, nir, qa, saturation, aerosol, exclude_interpolated_aerosol=True
        )
        self.assertEqual(strict_valid.tolist(), [[True, True, False, False, True, False]])

    def test_landsat_bootstrap_requires_ten_consecutive_annual_observations(self):
        eligible, reason = _landsat_bootstrap_eligibility(list(range(2013, 2023)))
        self.assertTrue(eligible)
        self.assertEqual(reason, "eligible")

        eligible, reason = _landsat_bootstrap_eligibility(list(range(2013, 2022)))
        self.assertFalse(eligible)
        self.assertIn("at_least_10", reason)

    def test_landsat_bootstrap_rejects_gaps_even_with_ten_years(self):
        years = [2013, 2014, 2015, 2016, 2018, 2019, 2020, 2021, 2022, 2023]
        eligible, reason = _landsat_bootstrap_eligibility(years)
        self.assertFalse(eligible)
        self.assertEqual(reason, "requires_unique_consecutive_annual_observations")

    def test_qa_flag_counts_are_non_exclusive_and_report_interpolation(self):
        qa = np.array([[0, 1 << 7, 1 << 3]], dtype=np.uint16)
        saturation = np.array([[0, 1 << 3, 0]], dtype=np.uint16)
        aerosol = np.array([[1 << 5, 1 << 2, 3 << 6]], dtype=np.uint16)
        counts = _qa_flag_counts(qa, saturation, aerosol)
        self.assertEqual(counts["total_pixels"], 3)
        self.assertEqual(counts["qa_pixel_water"], 1)
        self.assertEqual(counts["qa_pixel_cloud"], 1)
        self.assertEqual(counts["qa_radsat_red_saturation"], 1)
        self.assertEqual(counts["sr_qa_aerosol_interpolated"], 1)
        self.assertEqual(counts["sr_qa_aerosol_water"], 1)
        self.assertEqual(counts["sr_qa_aerosol_high"], 1)

    def test_scene_footprint_must_cover_the_full_window_not_only_the_centre(self):
        small = {
            "type": "Polygon",
            "coordinates": [[[-0.01, -0.01], [0.01, -0.01], [0.01, 0.01],
                             [-0.01, 0.01], [-0.01, -0.01]]],
        }
        large = {
            "type": "Polygon",
            "coordinates": [[[-0.04, -0.04], [0.04, -0.04], [0.04, 0.04],
                             [-0.04, 0.04], [-0.04, -0.04]]],
        }
        self.assertFalse(_geometry_covers_window(small, 0.0, 0.0, 2))
        self.assertTrue(_geometry_covers_window(large, 0.0, 0.0, 2))

    def test_raster_window_coverage_fraction_is_exact_for_axis_aligned_window(self):
        self.assertAlmostEqual(_raster_window_coverage_fraction(0, 0, 10, 10, 10, 10), 1.0)
        self.assertAlmostEqual(_raster_window_coverage_fraction(-5, 0, 10, 10, 10, 10), 0.5)
        self.assertEqual(_raster_window_coverage_fraction(20, 20, 10, 10, 10, 10), 0.0)

    def test_paired_error_metrics_are_descriptive_and_directional(self):
        metrics = _paired_error_metrics([0.5, 0.3, 0.7], [0.4, 0.5, 0.6])
        self.assertEqual(metrics["n"], 3)
        self.assertAlmostEqual(metrics["mean_bias_landsat_minus_modis"], 0.0)
        self.assertAlmostEqual(metrics["median_bias_landsat_minus_modis"], 0.1)
        self.assertAlmostEqual(metrics["mean_absolute_error"], 0.4 / 3)
        self.assertAlmostEqual(metrics["root_mean_square_error"], np.sqrt(0.02))
        self.assertIsNone(_paired_error_metrics([], []))
        with self.assertRaises(ValueError):
            _paired_error_metrics([0.1], [0.1, 0.2])

    def test_average_ranks_and_spearman_handle_ties(self):
        self.assertEqual(_average_ranks([2.0, 1.0, 1.0]), [3.0, 1.5, 1.5])
        self.assertAlmostEqual(_spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(_pearson([1, 2, 3], [2, 4, 6]), 1.0)


if __name__ == "__main__":
    unittest.main()
