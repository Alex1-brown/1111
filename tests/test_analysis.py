import unittest

from science_core.analysis import (
    analyze_power_payload,
    compare_rgb_pixels,
    monthly_means,
    summarize,
    valid_values,
)


class AnalysisTests(unittest.TestCase):
    def test_summary(self):
        result = summarize([1, 2, 3, 4], missing=1)
        self.assertEqual(result["count"], 4)
        self.assertEqual(result["missing"], 1)
        self.assertEqual(result["mean"], 2.5)
        self.assertEqual(result["median"], 2.5)
        self.assertAlmostEqual(result["standard_deviation"], 1.11803398875)

    def test_fill_and_invalid_values_are_filtered(self):
        accepted, missing = valid_values({
            "20240101": 10,
            "20240102": -999,
            "20240103": "not-a-number",
            "20240104": None,
            "20240105": 20,
        })
        self.assertEqual(accepted, [("20240101", 10.0), ("20240105", 20.0)])
        self.assertEqual(missing, 3)

    def test_monthly_means(self):
        result = monthly_means([("20240101", 10), ("20240102", 20), ("20240201", 30)])
        self.assertEqual(result[0]["month"], "01")
        self.assertEqual(result[0]["mean"], 15)
        self.assertEqual(result[1]["count"], 1)

    def test_rgb_difference(self):
        result = compare_rgb_pixels(bytes([0, 0, 0, 10, 10, 10]), bytes([30, 30, 30, 10, 10, 10]), 2, 1, 20)
        self.assertEqual(result["changed_pixels"], 1)
        self.assertEqual(result["changed_pixel_percent"], 50)
        self.assertEqual(result["mean_absolute_rgb_difference"], 15)

    def test_rgb_rejects_wrong_dimensions(self):
        with self.assertRaises(ValueError):
            compare_rgb_pixels(b"\x00", b"\x00", 1, 1)

    def test_power_payload(self):
        payload = {
            "header": {
                "fill_value": -999, "start": "20240101", "end": "20240103",
                "time_standard": "UTC", "title": "NASA POWER",
                "api": {"name": "POWER"}, "sources": ["MERRA2"],
            },
            "geometry": {"coordinates": [68.7, 38.5, 1300]},
            "properties": {"parameter": {
                "T2M": {"20240101": 10, "20240102": 20, "20240103": -999},
                "PRECTOTCORR": {"20240101": 0, "20240102": 2, "20240103": -999},
            }},
        }
        result = analyze_power_payload(payload)
        self.assertEqual(result["location"]["latitude"], 38.5)
        self.assertEqual(result["temperature_2m_c"]["count"], 2)
        self.assertEqual(result["temperature_2m_c"]["mean"], 15)
        self.assertEqual(result["precipitation_corrected_mm_day"]["sum_of_daily_values"], 2)


if __name__ == "__main__":
    unittest.main()
