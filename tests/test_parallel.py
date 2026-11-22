import json
import tempfile
import unittest

from pathlib import Path

from core.parallel import ParallelTestRunner


class TestParallelTestRunner(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.repository = Path(self.temp_dir.name)

        (self.repository / "test_sample.py").write_text(
            """
def test_addition():
    assert 10 + 20 == 30

def test_subtraction():
    assert 30 - 10 == 20

def test_multiplication():
    assert 5 * 4 == 20

def test_division():
    assert 20 / 5 == 4

def test_comparison():
    assert 10 > 5

def test_boolean():
    assert True
""",
            encoding="utf-8"
        )

    def tearDown(self):

        self.temp_dir.cleanup()

    def test_parallel_execution(self):

        runner = ParallelTestRunner(
            self.repository,
            workers=2
        )

        results = runner.run()

        self.assertTrue(results["success"])

        self.assertEqual(
            results["statistics"]["total"],
            6
        )

    def test_all_tests_pass(self):

        runner = ParallelTestRunner(
            self.repository,
            workers=2
        )

        results = runner.run()

        self.assertEqual(
            results["statistics"]["passed"],
            6
        )

    def test_worker_configuration(self):

        runner = ParallelTestRunner(
            self.repository,
            workers=4
        )

        self.assertEqual(runner.workers, 4)

    def test_invalid_workers(self):

        with self.assertRaises(ValueError):

            ParallelTestRunner(
                self.repository,
                workers=0
            )

    def test_timeout_validation(self):

        with self.assertRaises(ValueError):

            ParallelTestRunner(
                self.repository,
                timeout=0
            )

    def test_report_generation(self):

        runner = ParallelTestRunner(
            self.repository,
            workers=2
        )

        results = runner.run()

        report_path = self.repository / "parallel_report.json"

        saved_path = runner.save_report(
            results,
            report_path
        )

        self.assertTrue(Path(saved_path).exists())

        saved_data = json.loads(
            Path(saved_path).read_text(encoding="utf-8")
        )

        self.assertIn("statistics", saved_data)


if __name__ == "__main__":
    unittest.main()