import csv
import io
import json
import unittest
from urllib.parse import parse_qs, urlparse

from science_core.ornl_modis import (
    NDVI_BAND, QUALITY_BAND, ModisSubsetError, fetch_mod13q1,
)


class FakeResponse:
    def __init__(self, payload, is_text=False):
        self.payload = payload
        self.is_text = is_text

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        if self.is_text:
            return self.payload.encode("utf-8")
        return json.dumps(self.payload).encode("utf-8")


class ORNLModisTests(unittest.TestCase):
    def _csv_rows(self, dates, version="061", filename_version=None):
        rows = []
        file_version = filename_version or version
        for item in dates:
            modis_date = item["modis_date"]
            for band in (NDVI_BAND, QUALITY_BAND):
                suffix = band
                filename = (
                    f"MOD13Q1.{modis_date}.h23v05.{file_version}."
                    f"2020060000000.{suffix}"
                )
                values = [5000, 6000, 7000, -3000] if band == NDVI_BAND else [0, 1, 2, 255]
                rows.append([
                    filename, "MOD13Q1", modis_date,
                    "Lat38.5Lon68.7Samp2Line2", "2020060000000", band,
                    *[str(value) for value in values],
                ])
        output = io.StringIO()
        csv.writer(output).writerows(rows)
        return output.getvalue()

    def test_download_uses_csv_filenames_and_filters_pixels(self):
        dates = [
            {"calendar_date": "2020-02-18", "modis_date": "A2020049"},
            {"calendar_date": "2020-03-05", "modis_date": "A2020065"},
        ]

        def opener(request, timeout=90):
            parsed = urlparse(request.full_url)
            if parsed.path.endswith("/dates"):
                return FakeResponse(dates)
            params = parse_qs(parsed.query)
            if request.get_header("Accept") == "text/csv":
                return FakeResponse(self._csv_rows(dates), is_text=True)
            return FakeResponse({
                "band": "all", "nrows": 2, "ncols": 2, "cellsize": 231.656,
                "latitude": 38.5, "longitude": 68.7,
                "xllcorner": 1000.0, "yllcorner": 2000.0,
                "header": "source metadata",
            })

        result = fetch_mod13q1(
            38.5, 68.7, "2020-01-01", "2020-12-31",
            radius_km=1, opener=opener, pause_seconds=0,
        )
        self.assertEqual(result["composite_count"], 2)
        self.assertEqual(len(result["raw_records"]), 8)
        self.assertEqual(len(result["valid_observations"]), 2)
        self.assertAlmostEqual(result["valid_observations"][0][3], 0.5)
        self.assertEqual(result["quality_counts"]["good"], 2)
        self.assertEqual(result["quality_counts"]["marginal"], 2)
        self.assertEqual(result["quality_counts"]["snow_or_ice"], 2)
        self.assertEqual(result["quality_counts"]["other_or_fill"], 2)
        self.assertEqual(result["product_versions"], ["061"])
        self.assertEqual(result["grid"]["xllcorner_m"], 1000.0)

    def test_legacy_product_version_is_rejected(self):
        dates = [{"calendar_date": "2020-02-18", "modis_date": "A2020049"}]
        def opener(request, timeout=90):
            parsed = urlparse(request.full_url)
            if parsed.path.endswith("/dates"):
                return FakeResponse(dates)
            if request.get_header("Accept") == "text/csv":
                return FakeResponse(self._csv_rows(dates, filename_version="006"), is_text=True)
            return FakeResponse({
                "nrows": 2, "ncols": 2, "cellsize": 231.656,
                "latitude": 38.5, "longitude": 68.7,
                "xllcorner": 1000.0, "yllcorner": 2000.0,
            })
        with self.assertRaisesRegex(ModisSubsetError, "refusing to mix product versions"):
            fetch_mod13q1(38.5, 68.7, "2020-01-01", "2020-12-31",
                          opener=opener, pause_seconds=0)

    def test_empty_date_range_fails(self):
        def opener(request, timeout=90):
            return FakeResponse([])
        with self.assertRaises(ModisSubsetError):
            fetch_mod13q1(38.5, 68.7, "2020-01-01", "2020-01-31",
                          opener=opener, pause_seconds=0)

    def test_invalid_inputs_fail_before_network(self):
        with self.assertRaises(ValueError):
            fetch_mod13q1(100, 68.7, opener=lambda *a, **k: None)
        with self.assertRaises(ValueError):
            fetch_mod13q1(38.5, 68.7, "2021-01-01", "2020-01-01",
                          opener=lambda *a, **k: None)


if __name__ == "__main__":
    unittest.main()
