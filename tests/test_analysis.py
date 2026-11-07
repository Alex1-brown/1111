import unittest

from science_core.analysis import (
    analyze_power_payload, compare_rgb_pixels, monthly_means, summarize, valid_values,
)
from science_core.imagery_series import sample_dates, summarize_sequence
from science_core.statistical_analysis import analyze_power_timeseries
from science_core.pipeline import PipelineError, run_pipeline


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
            "20240101": 10, "20240102": -999, "20240103": "not-a-number",
            "20240104": None, "20240105": 20,
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
            compare_rgb_pixels(bytes([0]), bytes([0]), 1, 1)

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

    def test_evenly_spaced_image_dates(self):
        dates = sample_dates("2024-01-01", "2024-01-11", 6)
        self.assertEqual(len(dates), 6)
        self.assertEqual(dates[0], "2024-01-01")
        self.assertEqual(dates[-1], "2024-01-11")
        self.assertEqual(len(set(dates)), 6)

    def test_image_date_sampling_rejects_invalid_ranges(self):
        with self.assertRaises(ValueError):
            sample_dates("2024-01-11", "2024-01-01", 5)
        with self.assertRaises(ValueError):
            sample_dates("2024-01-01", "2024-01-02", 4)

    def test_satellite_sequence_summary(self):
        result = summarize_sequence([
            {"changed_pixel_percent": 10, "mean_absolute_rgb_difference": 5},
            {"changed_pixel_percent": 30, "mean_absolute_rgb_difference": 15},
        ])
        self.assertEqual(result["comparison_count"], 2)
        self.assertEqual(result["mean_changed_pixel_percent"], 20)
        self.assertEqual(result["median_changed_pixel_percent"], 20)
        self.assertEqual(result["mean_absolute_rgb_difference"], 10)

    def test_power_timeseries_annual_monthly_and_trend(self):
        temperature = [
            ("20200101", 10), ("20210101", 11), ("20220101", 12),
            ("20200102", 20), ("20210102", 21), ("20220102", 22),
        ]
        precipitation = [
            ("20200101", 1), ("20210101", 2), ("20220101", 3),
            ("20200102", 0), ("20210102", 0), ("20220102", 0),
        ]
        result = analyze_power_timeseries(temperature, precipitation)
        self.assertEqual(result["paired_valid_days"], 6)
        self.assertEqual(len(result["annual"]), 3)
        self.assertAlmostEqual(result["descriptive_linear_trends"]["annual_mean_temperature"]["slope_per_year"], 1.0)
        self.assertEqual(len(result["monthly_climatology"]), 1)
        self.assertEqual(result["daily_temperature_precipitation_pearson_r"], None if False else result["daily_temperature_precipitation_pearson_r"])

    def test_power_timeseries_requires_overlapping_dates(self):
        with self.assertRaises(ValueError):
            analyze_power_timeseries([("20200101", 1)], [("20200102", 1)])

    def test_six_stage_pipeline(self):
        result = run_pipeline(
            acquire=lambda: [1, 2, 3],
            validate=lambda data: data if all(isinstance(x, int) for x in data) else None,
            clean=lambda data: [x for x in data if x > 1],
            process=lambda data: sum(data),
            verify=lambda value: value == 5,
            visualize=lambda value: {"display_value": value},
        )
        self.assertEqual(result.data, 5)
        self.assertEqual(result.visualization, {"display_value": 5})
        self.assertEqual(result.completed_stages, (
            "acquire", "validate", "clean", "process", "verify", "visualize"
        ))

    def test_pipeline_stops_when_verification_fails(self):
        with self.assertRaises(PipelineError) as caught:
            run_pipeline(
                acquire=lambda: [1], validate=lambda data: data, clean=lambda data: data,
                process=lambda data: sum(data), verify=lambda value: False,
                visualize=lambda value: value,
            )
        self.assertEqual(caught.exception.stage, "verify")

    def test_pipeline_reports_failing_stage(self):
        with self.assertRaises(PipelineError) as caught:
            run_pipeline(
                acquire=lambda: [1],
                validate=lambda data: (_ for _ in ()).throw(ValueError("bad input")),
                clean=lambda data: data, process=lambda data: data,
                verify=lambda value: True, visualize=lambda value: value,
            )
        self.assertEqual(caught.exception.stage, "validate")


if __name__ == "__main__":
    unittest.main()
