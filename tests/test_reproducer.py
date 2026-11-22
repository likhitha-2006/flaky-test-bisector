import json
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from core.reproducer import FailureReproducer


class TestFailureReproducer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.root = Path(self.temp_dir.name)
        self.reports_dir = self.root / "reports"
        self.reports_dir.mkdir()

        self.reproducer = FailureReproducer(
            self.root,
            reports_dir=self.reports_dir
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_result(self, status="passed"):
        failed = status in ("failed", "error")

        return {
            "run_id": "test-run",
            "success": not failed,
            "statistics": {
                "total": 1,
                "passed": 0 if failed else 1,
                "failed": 1 if status == "failed" else 0,
                "errors": 1 if status == "error" else 0,
                "timed_out": False
            },
            "tests": [{
                "name": "test_example",
                "classname": "test_sample",
                "status": status,
                "details": "Sample assertion failure" if failed else ""
            }],
            "stdout": "",
            "stderr": ""
        }

    def test_invalid_repository(self):
        with self.assertRaises(ValueError):
            FailureReproducer(
                self.root / "missing"
            )

    def test_invalid_attempts(self):
        with self.assertRaises(ValueError):
            self.reproducer.reproduce(
                test_path="test_sample.py",
                attempts=0
            )

    @patch("core.reproducer.TestExecutor.execute")
    def test_stable_test(self, mock_execute):
        mock_execute.return_value = self.make_result("passed")

        result = self.reproducer.reproduce(
            test_path="test_sample.py",
            attempts=3
        )

        self.assertEqual(
            result["summary"]["reproduced_failures"], 0
        )

        self.assertEqual(
            result["summary"]["not_reproduced"], 3
        )

    @patch("core.reproducer.TestExecutor.execute")
    def test_consistently_failing_test(self, mock_execute):
        mock_execute.return_value = self.make_result("failed")

        result = self.reproducer.reproduce(
            test_path="test_sample.py",
            attempts=3
        )

        self.assertEqual(
            result["summary"]["reproduced_failures"], 3
        )

        self.assertTrue(
            result["summary"]["reproduced_consistently"]
        )

    @patch("core.reproducer.TestExecutor.execute")
    def test_failure_details_are_captured(self, mock_execute):
        mock_execute.return_value = self.make_result("failed")

        result = self.reproducer.reproduce(
            test_path="test_sample.py",
            attempts=1
        )

        self.assertIn(
            "Sample assertion failure",
            result["attempts"][0]["failed_tests"][0]["details"]
        )

    @patch("core.reproducer.TestExecutor.execute")
    def test_json_report_is_created(self, mock_execute):
        mock_execute.return_value = self.make_result("passed")

        result = self.reproducer.reproduce(
            test_path="test_sample.py",
            attempts=1
        )

        report_path = Path(result["report_path"])

        self.assertTrue(report_path.exists())

        with open(report_path, encoding="utf-8") as file:
            saved_report = json.load(file)

        self.assertIn("summary", saved_report)
        self.assertIn("attempts", saved_report)


if __name__ == "__main__":
    unittest.main()