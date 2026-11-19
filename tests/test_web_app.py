"""Offline smoke tests for the browser wrapper; no NASA requests are made."""
import unittest

import web_app


class WebAppSmokeTests(unittest.TestCase):
    def test_health(self):
        self.assertEqual(web_app.health()["status"], "ok")

    def test_home_contains_live_controls(self):
        page = web_app.home()
        self.assertIn("Run NASA analysis", page)
        self.assertIn("/api/status", page)
        self.assertIn("/report", page)

    def test_run_request_rejects_invalid_coordinates(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            web_app.RunRequest(latitude=91, longitude=0)
        with self.assertRaises(ValidationError):
            web_app.RunRequest(latitude=0, longitude=181)

    def test_default_location_is_dushanbe(self):
        request = web_app.RunRequest()
        self.assertEqual(request.latitude, 38.5598)
        self.assertEqual(request.longitude, 68.7870)


if __name__ == "__main__":
    unittest.main()
