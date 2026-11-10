import unittest
from datetime import date

import numpy as np

from science_core.landsat_validation import (
    INVALID_QA_PIXEL_BITS,
    _average_ranks,
    _pearson,
    _spearman,
    ndvi_from_landsat_arrays,
    _nearest_modis_composite,
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
        ndvi, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation)
        expected_red = 15000 * 0.0000275 - 0.2
        expected_nir = 25000 * 0.0000275 - 0.2
        expected = (expected_nir - expected_red) / (expected_nir + expected_red)
        self.assertTrue(valid[0, 0])
        self.assertAlmostEqual(float(ndvi[0, 0]), expected)
        self.assertFalse(valid[0, 1])
        self.assertTrue(np.isnan(ndvi[0, 1]))

    def test_all_invalid_qa_bits_are_excluded(self):
        red = np.full((1, 6), 15000, dtype=np.uint16)
        nir = np.full((1, 6), 25000, dtype=np.uint16)
        qa = np.array([[1 << bit for bit in range(6)]], dtype=np.uint16)
        saturation = np.zeros((1, 6), dtype=np.uint16)
        _, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation)
        self.assertEqual(int(valid.sum()), 0)
        self.assertEqual(INVALID_QA_PIXEL_BITS, 63)

    def test_saturation_and_fill_values_are_excluded(self):
        red = np.array([[0, 15000, 15000]], dtype=np.uint16)
        nir = np.array([[25000, 25000, 25000]], dtype=np.uint16)
        qa = np.zeros((1, 3), dtype=np.uint16)
        saturation = np.array([[0, 1, 0]], dtype=np.uint16)
        _, valid = ndvi_from_landsat_arrays(red, nir, qa, saturation)
        self.assertEqual(int(valid.sum()), 1)

    def test_average_ranks_and_spearman_handle_ties(self):
        self.assertEqual(_average_ranks([2.0, 1.0, 1.0]), [3.0, 1.5, 1.5])
        self.assertAlmostEqual(_spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(_pearson([1, 2, 3], [2, 4, 6]), 1.0)


if __name__ == "__main__":
    unittest.main()
