import json
import tempfile
import unittest

from pathlib import Path

from core.latency import LatencyTestRunner


class TestLatencyTestRunner(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.repository = Path(self.temp_dir.name)

        (self.repository / "test_sample.py").write_text(
            """
def test_one():
    assert 1 == 1

def test_two():
    assert 2 == 2

def test_three():
    assert 3 == 3
""",
            encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_latency_execution(self):

        runner = LatencyTestRunner(
            self.repository,
            minimum_delay=0.01,
            maximum_delay=0.02
        )

        results = runner.run(seed=42)

        self.assertTrue(results["success"])

        self.assertEqual(
            results["statistics"]["total"],
            3
        )

    def test_all_tests_pass(self):

        runner = LatencyTestRunner(
            self.repository,
            minimum_delay=0,
            maximum_delay=0
        )

        results = runner.run()

        self.assertEqual(
            results["statistics"]["passed"],
            3
        )

    def test_invalid_minimum_delay(self):

        with self.assertRaises(ValueError):

            LatencyTestRunner(
                self.repository,
                minimum_delay=-1
            )

    def test_invalid_delay_range(self):

        with self.assertRaises(ValueError):

            LatencyTestRunner(
                self.repository,
                minimum_delay=2,
                maximum_delay=1
            )

    def test_timeout_validation(self):

        with self.assertRaises(ValueError):

            LatencyTestRunner(
                self.repository,
                timeout=0
            )

    def test_report_generation(self):

        runner = LatencyTestRunner(
            self.repository,
            minimum_delay=0,
            maximum_delay=0
        )

        results = runner.run()

        report_path = self.repository / "latency_report.json"

        saved_path = runner.save_report(
            results,
            report_path
        )

        self.assertTrue(Path(saved_path).exists())

        saved_data = json.loads(
            Path(saved_path).read_text(encoding="utf-8")
        )

        self.assertIn("configuration", saved_data)


if __name__ == "__main__":
    unittest.main()