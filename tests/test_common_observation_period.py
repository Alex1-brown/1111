import unittest

from science_core.cli import common_observation_year_bounds


class CommonObservationPeriodTests(unittest.TestCase):
    def test_edge_years_are_not_limited_by_annual_trend_core_period(self):
        # MODIS annual trend inference may end in 2023 because 2024-2025
        # coverage is incomplete, but matched 2024-2025 months remain useful
        # for exploratory monthly cross-source analysis.
        self.assertEqual(
            common_observation_year_bounds(
                "20210101", "20251231", "2001-01-01", "2025-12-31"
            ),
            (2021, 2025),
        )

    def test_non_overlapping_source_periods_are_rejected(self):
        with self.assertRaises(ValueError):
            common_observation_year_bounds(
                "20210101", "20211231", "2022-01-01", "2025-12-31"
            )


if __name__ == "__main__":
    unittest.main()
