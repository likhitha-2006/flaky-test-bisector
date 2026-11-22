import tempfile
import unittest

from pathlib import Path

from core.executor import TestExecutor


class TestExecutionEngine(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.root = Path(self.temp_dir.name)

        (self.root / "test_sample.py").write_text(
            """
def test_addition():
    assert 2 + 2 == 4

def test_subtraction():
    assert 5 - 2 == 3

def test_multiplication():
    assert 3 * 3 == 9
""",
            encoding="utf-8"
        )

        self.executor = TestExecutor(
            self.root,
            timeout=30
        )

    def tearDown(self):

        self.temp_dir.cleanup()

    def test_successful_execution(self):

        result = self.executor.execute()

        self.assertTrue(result["success"])

    def test_test_count(self):

        result = self.executor.execute()

        self.assertEqual(
            result["statistics"]["total"],
            3
        )

    def test_all_tests_pass(self):

        result = self.executor.execute()

        self.assertEqual(
            result["statistics"]["passed"],
            3
        )

        self.assertEqual(
            result["statistics"]["failed"],
            0
        )

    def test_failure_detection(self):

        (self.root / "test_failure.py").write_text(
            """
def test_failure():
    assert 10 == 20
""",
            encoding="utf-8"
        )

        result = self.executor.execute()

        self.assertFalse(result["success"])

        self.assertEqual(
            result["statistics"]["failed"],
            1
        )

    def test_timeout_validation(self):

        with self.assertRaises(ValueError):

            TestExecutor(
                self.root,
                timeout=0
            )

    def test_report_generation(self):

        result = self.executor.execute()

        report_path = self.root / "report.json"

        saved = TestExecutor.save_report(
            result,
            report_path
        )

        self.assertTrue(Path(saved).exists())


if __name__ == "__main__":

    unittest.main()