import unittest
from pathlib import Path

from science_core.desktop import PROJECT_ROOT, build_cli_command, validate_coordinates


class DesktopLauncherTests(unittest.TestCase):
    def test_dushanbe_coordinates_are_valid(self):
        self.assertEqual(
            validate_coordinates("38.5598", "68.7870"),
            (38.5598, 68.787),
        )

    def test_command_uses_the_science_pipeline_and_safe_defaults(self):
        command = build_cli_command(
            "38.5598", "68.7870", "artifacts", python_executable="python-test"
        )
        self.assertEqual(command[0], "python-test")
        self.assertIn("science_core.cli", command)
        self.assertIn("--skip-gibs", command)
        self.assertIn("2001-01-01", command)
        self.assertIn("20210101", command)
        self.assertIn("--longitude", command)
        output_index = command.index("--output") + 1
        self.assertEqual(Path(command[output_index]), PROJECT_ROOT / "artifacts")

    def test_invalid_and_non_finite_coordinates_are_rejected(self):
        for latitude, longitude in (
            ("north", "68"), ("91", "68"), ("38", "181"), ("nan", "68"), ("inf", "0")
        ):
            with self.subTest(latitude=latitude, longitude=longitude):
                with self.assertRaises(ValueError):
                    validate_coordinates(latitude, longitude)

    def test_empty_output_folder_is_rejected(self):
        with self.assertRaises(ValueError):
            build_cli_command("38", "68", "   ")


if __name__ == "__main__":
    unittest.main()
