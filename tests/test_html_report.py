import tempfile
import unittest
from pathlib import Path

from science_core.html_report import render_html_report


class HTMLReportTests(unittest.TestCase):
    def test_render_contains_summary_grid_and_caveats(self):
        with tempfile.TemporaryDirectory() as folder:
            chart = Path(folder) / "chart.svg"
            chart.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
            report = {
                "generated_at_utc": "2026-11-07T00:00:00Z",
                "modis_ndvi": {
                    "composite_count": 12,
                    "available_composite_count": 24,
                    "fixed_panel_pixels": 8,
                    "trend_period": [2003, 2023],
                    "grid": {"nrows": 2, "ncols": 2},
                    "annual_fixed_panel_change_detection": {
                        "pettitt": {"change_point_year": 2018}
                    },
                },
                "power_time_series_analysis": {"paired_valid_days": 100},
                "cross_source_monthly_analysis": {
                    "common_months": 10,
                    "anomaly_correlations": {
                        "ndvi_vs_temperature_pearson_r": 0.2,
                        "ndvi_vs_temperature_spearman_rho": 0.3,
                        "ndvi_vs_precipitation_pearson_r": 0.1,
                        "ndvi_vs_precipitation_spearman_rho": 0.15,
                    },
                },
            }
            trends = [
                {"row": 0, "column": 0, "sen_slope_ndvi_per_year": -0.01,
                 "sen_slope_ci_95_lower_ndvi_per_year": -0.015,
                 "sen_slope_ci_95_upper_ndvi_per_year": -0.005,
                 "q_value_by": None, "p_value_hamed_rao_sensitivity": 0.02,
                 "temporal_eligible": True, "inferential_eligible": False, "years": 20,
                 "serial_correlation_adjusted": True,
                 "serial_correlation_status": "applied",
                 "sen_slope_ci_95_method": "Hamed-Rao modified variance"},
                {"row": 0, "column": 1, "sen_slope_ndvi_per_year": 0.01,
                 "sen_slope_ci_95_lower_ndvi_per_year": 0.005,
                 "sen_slope_ci_95_upper_ndvi_per_year": 0.015,
                 "q_value_by": None, "p_value_iid": 0.02, "years": 20,
                 "serial_correlation_adjusted": False,
                 "serial_correlation_status": "irregular_time_spacing",
                 "sen_slope_ci_95_method": "iid nominal interval"},
            ]
            html = render_html_report(report, trends, {"annual_ndvi.svg": str(chart)})
            self.assertIn("Earth System Trend Detective", html)
            self.assertIn("Select a grid cell", html)
            self.assertIn("temporal autocorrelation", html)
            self.assertIn("nominal 95% CI", html)
            self.assertIn("[-0.01500, -0.00500] NDVI/year", html)
            self.assertIn("Hamed-Rao variance sensitivity computed", html)
            self.assertIn("Hamed-Rao sensitivity p-value 0.02 is diagnostic only", html)
            self.assertIn("withheld pending Hamed-Rao calibration", html)
            self.assertIn("not eligible for adjusted inference", html)
            self.assertIn("2018", html)
            self.assertIn("2003–2023", html)
            self.assertIn("0.200", html)
            self.assertIn("NDVI vs temperature", html)
            self.assertIn("<svg", html)

    def test_render_handles_missing_charts_and_grid(self):
        html = render_html_report({}, [], {"annual_ndvi.svg": "/missing/annual_ndvi.svg"})
        self.assertIn("Spatial trend grid unavailable", html)
        self.assertIn("Chart unavailable", html)


if __name__ == "__main__":
    unittest.main()
