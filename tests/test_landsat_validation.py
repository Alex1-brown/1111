import unittest

import numpy as np

from science_core.landsat_validation import (
    INVALID_QA_PIXEL_BITS,
    _average_ranks,
    _pearson,
    _spearman,
    ndvi_from_landsat_arrays,
)


class LandsatValidationTests(unittest.TestCase):
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
