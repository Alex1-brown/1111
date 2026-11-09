import json
import unittest

import numpy as np
import rasterio
from rasterio.transform import Affine

from science_core.planetary_modis import (
    NDVI_ASSET, QUALITY_ASSET, PlanetaryModisError,
    _geometry_contains, _sign_href, _sample_one_per_month, fetch_mod13q1,
)


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeRaster:
    def __init__(self, asset, transform_shift=0):
        self.asset = asset
        self.transform_shift = transform_shift
        self.crs = rasterio.crs.CRS.from_epsg(4326)
        self.res = (250.0, 250.0)
        self.width = 100
        self.height = 100
        self.transform = Affine.identity()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def index(self, x, y):
        return 50, 50

    def read(self, band, window, boundless, fill_value):
        arr = np.full((int(window.height), int(window.width)),
                      5000 if self.asset == "ndvi" else 0, dtype=np.int16)
        if self.asset == "ndvi":
            arr[0, 0] = -3000
        else:
            arr[0, 1] = 1
            arr[0, 2] = 2
            arr[0, 3] = 3
        return arr

    def window_transform(self, window):
        return Affine.translation(
            window.col_off + self.transform_shift, window.row_off
        ) * Affine.scale(0.001, -0.001)


class PlanetaryModisTests(unittest.TestCase):
    def test_geometry_contains_point(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[68, 38], [69, 38], [69, 39], [68, 39], [68, 38]]],
        }
        self.assertTrue(_geometry_contains(geometry, 68.5, 38.5))
        self.assertFalse(_geometry_contains(geometry, 70, 40))

    def test_polygon_hole_excludes_point_from_footprint(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [
                [[68, 38], [70, 38], [70, 40], [68, 40], [68, 38]],
                [[68.4, 38.4], [68.6, 38.4], [68.6, 38.6], [68.4, 38.6], [68.4, 38.4]],
            ],
        }
        self.assertTrue(_geometry_contains(geometry, 68.2, 38.2))
        self.assertFalse(_geometry_contains(geometry, 68.5, 38.5))

    def test_multipolygon_checks_holes_and_other_polygon_parts(self):
        geometry = {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [[68, 38], [70, 38], [70, 40], [68, 40], [68, 38]],
                    [[68.4, 38.4], [68.6, 38.4], [68.6, 38.6], [68.4, 38.6], [68.4, 38.4]],
                ],
                [[[71, 38], [72, 38], [72, 39], [71, 39], [71, 38]]],
            ],
        }
        self.assertFalse(_geometry_contains(geometry, 68.5, 38.5))
        self.assertTrue(_geometry_contains(geometry, 71.5, 38.5))

    def test_monthly_sampling_selects_composite_nearest_to_midmonth(self):
        items = [
            {"id": "a", "__composite_date": "2020-01-01"},
            {"id": "b", "__composite_date": "2020-01-17"},
            {"id": "c", "__composite_date": "2020-02-02"},
            {"id": "d", "__composite_date": "2020-02-16"},
        ]
        selected = _sample_one_per_month(items)
        self.assertEqual([item["id"] for item in selected], ["b", "d"])

    def test_sign_href_adds_token_once(self):
        href = "https://modiseuwest.blob.core.windows.net/modis-061-cogs/a.tif"
        signed = _sign_href(href, "se=abc&sig=xyz")
        self.assertTrue(signed.endswith("?se=abc&sig=xyz"))
        self.assertEqual(_sign_href(signed, "se=other"), signed)

    def test_fetch_reads_quality_screened_ndvi(self):
        item = {
            "id": "MOD13Q1.A2020049.h23v05.061.2020060000000",
            "type": "Feature",
            "collection": "modis-13Q1-061",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[68, 38], [69, 38], [69, 39], [68, 39], [68, 38]]],
            },
            "properties": {
                "platform": "terra",
                "start_datetime": "2020-02-18T00:00:00Z",
                "end_datetime": "2020-03-05T23:59:59Z",
                "modis:tile-id": "51021004",
            },
            "assets": {
                NDVI_ASSET: {"href": "https://modiseuwest.blob.core.windows.net/modis-061-cogs/ndvi.tif"},
                QUALITY_ASSET: {"href": "https://modiseuwest.blob.core.windows.net/modis-061-cogs/qa.tif"},
            },
        }

        token_requests = []
        def http_opener(request, timeout=90):
            if "/token/" in request.full_url:
                token_requests.append(request.full_url)
                return FakeHTTPResponse({"token": "se=abc&sig=xyz"})
            return FakeHTTPResponse({"features": [item], "links": []})

        def raster_opener(url):
            return FakeRaster("ndvi" if "ndvi.tif" in url else "qa")

        result = fetch_mod13q1(
            38.5, 68.5, "2020-01-01", "2020-12-31", 2,
            opener=http_opener, raster_opener=raster_opener,
        )
        self.assertEqual(result["product_versions"], ["061"])
        self.assertEqual(result["composite_count"], 1)
        self.assertEqual(result["available_composite_count"], 1)
        self.assertEqual(result["grid"]["nrows"], 17)
        self.assertEqual(result["quality_counts"]["good"], 285)
        self.assertEqual(result["quality_counts"]["marginal"], 1)
        self.assertEqual(result["quality_counts"]["snow_or_ice"], 1)
        self.assertEqual(result["quality_counts"]["cloudy"], 1)
        self.assertEqual(len(result["valid_observations"]), 285)
        self.assertEqual(
            token_requests,
            ["https://planetarycomputer.microsoft.com/api/sas/v1/token/modiseuwest/modis-061-cogs"],
        )

    def test_rejects_pixel_grid_transform_shift_between_dates(self):
        first = {
            "id": "MOD13Q1.A2020049.h23v05.061.2020060000000",
            "type": "Feature",
            "collection": "modis-13Q1-061",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[68, 38], [69, 38], [69, 39], [68, 39], [68, 38]]],
            },
            "properties": {
                "platform": "terra",
                "start_datetime": "2020-02-18T00:00:00Z",
                "end_datetime": "2020-03-05T23:59:59Z",
                "modis:tile-id": "51021004",
            },
            "assets": {
                NDVI_ASSET: {"href": "https://modiseuwest.blob.core.windows.net/modis-061-cogs/ndvi.tif"},
                QUALITY_ASSET: {"href": "https://modiseuwest.blob.core.windows.net/modis-061-cogs/qa.tif"},
            },
        }
        second = json.loads(json.dumps(first))
        second["id"] = "MOD13Q1.A2020065.h23v05.061.2020070000000"
        second["properties"]["start_datetime"] = "2020-03-05T00:00:00Z"
        second["properties"]["end_datetime"] = "2020-03-21T23:59:59Z"

        def http_opener(request, timeout=90):
            if "/token/" in request.full_url:
                return FakeHTTPResponse({"token": "se=abc&sig=xyz"})
            return FakeHTTPResponse({"features": [first, second], "links": []})

        raster_calls = 0
        def raster_opener(url):
            nonlocal raster_calls
            raster_calls += 1
            # Each date opens NDVI then QA; both bands share the same shifted
            # affine transform, but the second date is deliberately misaligned.
            shift = 0 if raster_calls <= 2 else 1
            return FakeRaster("ndvi" if "ndvi.tif" in url else "qa", shift)

        with self.assertRaisesRegex(PlanetaryModisError, "affine transform changed"):
            fetch_mod13q1(
                38.5, 68.5, "2020-01-01", "2020-12-31", 2,
                opener=http_opener, raster_opener=raster_opener,
            )

    def test_rejects_empty_stac_search(self):
        def http_opener(request, timeout=90):
            if "/token/" in request.full_url:
                return FakeHTTPResponse({"token": "token"})
            return FakeHTTPResponse({"features": [], "links": []})
        with self.assertRaises(PlanetaryModisError):
            fetch_mod13q1(38.5, 68.5, "2020-01-01", "2020-12-31", opener=http_opener)


if __name__ == "__main__":
    unittest.main()
