import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

from science_core.gpm_imerg import (
    GPM_DOI,
    annual_grid_summaries,
    build_access_status,
    earthdata_credentials_status,
    quality_screen_daily_arrays,
    read_daily_netcdf_files,
)


class GPMIMERGTests(unittest.TestCase):
    def test_product_identity_is_versioned_and_citable(self):
        self.assertIn("IMERGDF/DAY/07", GPM_DOI)

    def test_missing_credentials_are_reported_without_network_access(self):
        status = build_access_status(environ={}, netrc_path="/path/that/does/not/exist")
        self.assertEqual(status["status"], "blocked_missing_credentials")
        self.assertFalse(status["download_attempted"])
        self.assertFalse(status["automatic_remote_download_enabled"])
        self.assertFalse(status["credentials"]["secret_values_exposed"])

    def test_environment_credentials_are_detected_without_exposing_values(self):
        status = earthdata_credentials_status({
            "EARTHDATA_USERNAME": "test-user",
            "EARTHDATA_PASSWORD": "not-a-real-secret",
        }, netrc_path="/path/that/does/not/exist")
        self.assertEqual(status["status"], "credentials_present_not_verified")
        self.assertNotIn("not-a-real-secret", str(status))
        self.assertNotIn("test-user", str(status))

    def test_netrc_credentials_are_detected_without_exposing_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".netrc"
            path.write_text(
                "machine urs.earthdata.nasa.gov login test-user password not-a-real-secret\n",
                encoding="utf-8",
            )
            os.chmod(path, 0o600)
            status = earthdata_credentials_status({}, path)
        self.assertEqual(status["status"], "credentials_present_not_verified")
        self.assertNotIn("not-a-real-secret", str(status))
        self.assertNotIn("test-user", str(status))

    def test_zero_precipitation_is_valid_when_count_is_positive(self):
        precipitation = np.array([[[0.0, 1.2, -1.0, np.nan]]])
        counts = np.array([[[48, 24, 48, 0]]])
        result = quality_screen_daily_arrays(precipitation, counts)
        self.assertEqual(result["valid_mask"].tolist(), [[[True, True, False, False]]])
        self.assertEqual(result["qc_summary"]["valid_grid_day_cells"], 2)
        self.assertTrue(result["qc_summary"]["zero_precipitation_is_valid_when_sample_count_is_positive"])

    def test_optional_half_hour_threshold_is_explicit_and_does_not_change_error_mask(self):
        precipitation = np.array([[[1.0, 2.0]]])
        counts = np.array([[[48, 12]]])
        errors = np.array([[[0.2, np.nan]]])
        result = quality_screen_daily_arrays(
            precipitation, counts, errors, minimum_valid_half_hours=24
        )
        self.assertEqual(result["valid_mask"].tolist(), [[[True, False]]])
        self.assertEqual(result["random_error_valid_mask"].tolist(), [[[True, False]]])
        self.assertEqual(result["qc_summary"]["valid_cells_below_user_threshold"], 1)
        self.assertTrue(result["qc_summary"]["random_error_is_uncertainty_not_a_precipitation_rejection_mask"])

    def test_invalid_half_hour_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            quality_screen_daily_arrays(
                np.ones((1, 1, 1)), np.ones((1, 1, 1)), minimum_valid_half_hours=49
            )

    def test_annual_totals_require_every_calendar_day(self):
        dates_2020 = [date(2020, 1, 1) + timedelta(days=i) for i in range(366)]
        dates_2021 = [date(2021, 1, 1) + timedelta(days=i) for i in range(365)]
        dates = dates_2020 + dates_2021
        values = np.ones((len(dates), 1, 1), dtype=float)
        valid = np.ones(values.shape, dtype=bool)
        valid[10, 0, 0] = False
        counts = np.full(values.shape, 48, dtype=float)
        rows = annual_grid_summaries(dates, values, valid, counts)
        by_year = {row["year"]: row for row in rows}
        self.assertEqual(by_year[2020]["valid_days"], 365)
        self.assertIsNone(by_year[2020]["annual_total_mm"])
        self.assertAlmostEqual(by_year[2020]["observed_day_sum_mm"], 365.0)
        self.assertEqual(by_year[2021]["annual_total_mm"], 365.0)
        self.assertEqual(by_year[2021]["analysis_status"], "complete_calendar_year")

    def test_duplicate_dates_are_rejected(self):
        dates = [date(2021, 1, 1), date(2021, 1, 1)]
        values = np.ones((2, 1, 1))
        with self.assertRaisesRegex(ValueError, "Duplicate dates"):
            annual_grid_summaries(dates, values, np.ones(values.shape, dtype=bool))

    def test_reader_transposes_netcdf_dimension_order_and_records_provenance(self):
        try:
            import netCDF4
        except ImportError:
            self.skipTest("netCDF4 is installed by requirements.txt in CI")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gpm_test.nc4"
            with netCDF4.Dataset(path, "w", format="NETCDF4") as dataset:
                dataset.createDimension("time", 2)
                dataset.createDimension("lat", 2)
                dataset.createDimension("lon", 3)
                dataset.setncattr("ShortName", "GPM_3IMERGDF")
                dataset.setncattr("VersionID", "07")
                lat = dataset.createVariable("lat", "f4", ("lat",))
                lon = dataset.createVariable("lon", "f4", ("lon",))
                time = dataset.createVariable("time", "f8", ("time",))
                lat[:] = [38.5, 38.6]
                lon[:] = [68.7, 68.8, 68.9]
                time.units = "days since 1980-01-06 00:00:00"
                time.calendar = "standard"
                time[:] = netCDF4.date2num(
                    [datetime(2020, 1, 1), datetime(2020, 1, 2)],
                    units=time.units,
                    calendar=time.calendar,
                )
                precip = dataset.createVariable(
                    "precipitation", "f4", ("time", "lon", "lat"), fill_value=-9999.0
                )
                precip.units = "mm/day"
                counts = dataset.createVariable(
                    "precipitation_cnt", "i2", ("time", "lon", "lat"), fill_value=-9999
                )
                counts.units = "count"
                errors = dataset.createVariable(
                    "randomError", "f4", ("time", "lon", "lat"), fill_value=-9999.0
                )
                errors.units = "mm/day"
                raw = np.arange(12, dtype=np.float32).reshape(2, 3, 2)
                precip[:] = raw
                counts[:] = np.full(raw.shape, 48, dtype=np.int16)
                errors[:] = np.full(raw.shape, 0.25, dtype=np.float32)

            result = read_daily_netcdf_files([path])
            self.assertEqual(result["dates"], [date(2020, 1, 1), date(2020, 1, 2)])
            self.assertEqual(result["precipitation"].shape, (2, 2, 3))
            self.assertEqual(
                result["precipitation"][0].tolist(),
                np.transpose(np.arange(6, dtype=np.float32).reshape(3, 2), (1, 0)).tolist(),
            )
            self.assertEqual(result["precipitation_count"].shape, (2, 2, 3))
            self.assertEqual(len(result["source_files"][0]["sha256"]), 64)
            self.assertEqual(result["source_files"][0]["global_attributes"]["VersionID"], "07")


if __name__ == "__main__":
    unittest.main()
