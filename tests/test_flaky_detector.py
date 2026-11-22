import json
import tempfile
import unittest

from pathlib import Path

from core.flaky_detector import FlakyTestDetector


class TestFlakyTestDetector(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.repository = Path(self.temp_dir.name)

        (self.repository / "test_sample.py").write_text(
            """
def test_stable():
    assert 10 + 20 == 30
""",
            encoding="utf-8"
        )

    def tearDown(self):

        self.temp_dir.cleanup()

    def test_stable_test_detection(self):

        detector = FlakyTestDetector(
            self.repository,
            iterations=2
        )

        results = detector.analyze()

        self.assertEqual(
            results["summary"]["stable_tests"],
            1
        )

        self.assertEqual(
            results["summary"]["flaky_tests"],
            0
        )

    def test_flaky_test_detection(self):

        (self.repository / "test_sample.py").write_text(
            """
from pathlib import Path

counter_file = Path(__file__).with_name("counter.txt")

def test_flaky():

    if counter_file.exists():
        count = int(counter_file.read_text())
    else:
        count = 0

    counter_file.write_text(str(count + 1))

    assert count % 2 == 0
""",
            encoding="utf-8"
        )

        detector = FlakyTestDetector(
            self.repository,
            iterations=4
        )

        results = detector.analyze()

        self.assertEqual(
            results["summary"]["flaky_tests"],
            1
        )

    def test_failure_rate_calculation(self):

        history = [
            {"iteration": 1, "status": "passed"},
            {"iteration": 2, "status": "failed"},
            {"iteration": 3, "status": "passed"},
            {"iteration": 4, "status": "failed"}
        ]

        result = FlakyTestDetector._analyze_test(
            "test_example",
            history
        )

        self.assertEqual(
            result["failure_rate_percent"],
            50.0
        )

        self.assertEqual(
            result["classification"],
            "flaky"
        )

    def test_consistently_failed_detection(self):

        history = [
            {"iteration": 1, "status": "failed"},
            {"iteration": 2, "status": "failed"},
            {"iteration": 3, "status": "failed"}
        ]

        result = FlakyTestDetector._analyze_test(
            "test_example",
            history
        )

        self.assertEqual(
            result["classification"],
            "consistently_failed"
        )

    def test_invalid_iterations(self):

        with self.assertRaises(ValueError):

            FlakyTestDetector(
                self.repository,
                iterations=0
            )

    def test_report_generation(self):

        detector = FlakyTestDetector(
            self.repository,
            iterations=2
        )

        results = detector.analyze()

        report_path = self.repository / "flaky_report.json"

        saved_path = detector.save_report(
            results,
            report_path
        )

        self.assertTrue(Path(saved_path).exists())

        saved_data = json.loads(
            Path(saved_path).read_text(encoding="utf-8")
        )

        self.assertIn("flaky_test_details", saved_data)


if __name__ == "__main__":
    unittest.main()