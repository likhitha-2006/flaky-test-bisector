import json
import tempfile
import unittest

from pathlib import Path

from core.isolator import FailureIsolator


class TestFailureIsolator(unittest.TestCase):

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

        self.isolator = FailureIsolator(
            self.repository
        )

    def tearDown(self):

        self.temp_dir.cleanup()

    def test_collect_tests(self):

        tests = self.isolator._collect_tests()

        self.assertEqual(len(tests), 3)

    def test_no_failure_detected(self):

        results = self.isolator.isolate()

        self.assertFalse(
            results["summary"]["initial_failure_reproduced"]
        )

        self.assertEqual(
            results["summary"]["minimized_test_count"],
            3
        )

    def test_failure_isolation(self):

        (self.repository / "test_sample.py").write_text(
            """
def test_one():
    assert 1 == 1

def test_two():
    assert 2 == 2

def test_failure():
    assert 1 == 2
""",
            encoding="utf-8"
        )

        isolator = FailureIsolator(
            self.repository
        )

        results = isolator.isolate()

        self.assertTrue(
            results["summary"]["initial_failure_reproduced"]
        )

        self.assertEqual(
            results["summary"]["minimized_test_count"],
            1
        )

    def test_delta_debugging_algorithm(self):

        test_ids = [
            "test_one",
            "test_two",
            "test_three",
            "test_four"
        ]

        def failure_predicate(subset):

            return "test_three" in subset

        minimized = self.isolator._ddmin(
            test_ids,
            failure_predicate
        )

        self.assertEqual(
            minimized,
            ["test_three"]
        )

    def test_invalid_timeout(self):

        with self.assertRaises(ValueError):

            FailureIsolator(
                self.repository,
                timeout=0
            )

    def test_report_generation(self):

        results = self.isolator.isolate()

        report_path = self.repository / "isolation_report.json"

        saved_path = self.isolator.save_report(
            results,
            report_path
        )

        self.assertTrue(Path(saved_path).exists())

        saved_data = json.loads(
            Path(saved_path).read_text(encoding="utf-8")
        )

        self.assertIn(
            "attempt_history",
            saved_data
        )


if __name__ == "__main__":
    unittest.main()