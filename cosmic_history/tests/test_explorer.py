import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

class CosmicHistoryEvidenceTests(unittest.TestCase):
    def test_primary_study_values_are_present(self):
        self.assertIn('age:14.2,error:0.4', HTML)
        self.assertIn('age:12.3,error:null', HTML)
        self.assertIn('age:13.787', HTML)

    def test_source_links_are_present(self):
        for source in ("0004-6361/202451782", "0004-6361/202556292", "2268/334880"):
            self.assertIn(source, HTML)
            self.assertIn(source, README)

    def test_uncertainty_and_limitations_are_explicit(self):
        self.assertIn("internal uncertainties", HTML)
        self.assertIn("Do not average", README)
        self.assertIn("does not yet query Gaia/TESS archives live", HTML)

    def test_bilingual_controls_and_export_exist(self):
        for token in ('id="lang"', 'id="download"', 'id="showAll"', 'id="showSeismic"'):
            self.assertIn(token, HTML)
        self.assertIn("JSON", HTML)

    def test_html_is_self_contained_and_has_no_external_runtime_dependency(self):
        self.assertNotRegex(HTML, re.compile(r'<script[^>]+src=', re.I))
        self.assertNotRegex(HTML, re.compile(r'<link[^>]+stylesheet', re.I))
        self.assertIn("draw();setLang();", HTML)

if __name__ == "__main__":
    unittest.main()
