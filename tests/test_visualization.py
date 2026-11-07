import unittest

from science_core.visualization import render_line_chart


class VisualizationTests(unittest.TestCase):
    def test_cli_module_imports(self):
        from science_core.cli import main
        self.assertTrue(callable(main))

    def test_chart_contains_title_and_values(self):
        svg = render_line_chart([("2020", 1.2), ("2021", 1.5)], "NDVI trend", "NDVI")
        self.assertIn("NDVI trend", svg)
        self.assertIn("2020", svg)
        self.assertIn("2021", svg)
        self.assertIn("<polyline", svg)

    def test_empty_chart_is_explicit(self):
        svg = render_line_chart([], "No data", "Value")
        self.assertIn("No valid observations", svg)

    def test_chart_escapes_xml_text(self):
        svg = render_line_chart([("2020", 1)], "A & B", "X < Y")
        self.assertIn("A &amp; B", svg)
        self.assertIn("X &lt; Y", svg)

    def test_invalid_values_and_dimensions_fail(self):
        with self.assertRaises(ValueError):
            render_line_chart([("2020", float("nan"))], "bad", "x")
        with self.assertRaises(ValueError):
            render_line_chart([], "bad", "x", width=100, height=100)


if __name__ == "__main__":
    unittest.main()
