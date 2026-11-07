import json
import unittest
from urllib.parse import parse_qs, urlparse

from science_core.ornl_modis import (
    NDVI_BAND, QUALITY_BAND, ModisSubsetError, fetch_mod13q1,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ORNLModisTests(unittest.TestCase):
    def test_download_uses_quality_band_and_filters_pixels(self):
        dates = [
            {"calendar_date": "2020-02-18", "modis_date": "A2020049"},
            {"calendar_date": "2020-03-05", "modis_date": "A2020065"},
        ]

        def opener(request, timeout=90):
            parsed = urlparse(request.full_url)
            params = parse_qs(parsed.query)
            if parsed.path.endswith("/dates"):
                payload = {"dates": dates}
            else:
                band = params["band"][0]
                values = [5000, 6000, 7000, -3000]
                qa = [0, 1, 2, 255]
                payload = {
                    "nrows": 2, "ncols": 2, "cellsize": 231.656,
                    "latitude": 38.5, "longitude": 68.7,
                    "header": "source metadata",
                    "subset": [
                        {
                            "band": band,
                            "modis_date": item["modis_date"],
                            "data": values if band == NDVI_BAND else qa,
                            "version": "061",
                        }
                        for item in dates
                    ],
                }
            return FakeResponse(payload)

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

    def test_empty_date_range_fails(self):
        def opener(request, timeout=90):
            return FakeResponse({"dates": []})
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
