import tempfile
import unittest

from pathlib import Path

from core.history import RunHistoryManager


class TestRunHistoryManager(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.manager = RunHistoryManager(
            self.temp_dir.name
        )

        self.sample_run = {
            "run_id": "test-run-001",
            "success": True,

            "stats": {
                "passed": 10,
                "failed": 0,
                "total": 10
            },

            "configuration": {
                "iterations": 5,
                "workers": 2,
                "random_seed": 42
            }
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_run(self):

        result = self.manager.record_run(self.sample_run)

        self.assertEqual(
            result["run_id"],
            "test-run-001"
        )

        self.assertTrue(
            (Path(self.temp_dir.name) / "test-run-001.json").exists()
        )

    def test_list_runs(self):

        self.manager.record_run(self.sample_run)

        runs = self.manager.list_runs()

        self.assertEqual(len(runs), 1)

    def test_get_run(self):

        self.manager.record_run(self.sample_run)

        result = self.manager.get_run("test-run-001")

        self.assertIsNotNone(result)
        self.assertTrue(result["success"])

    def test_compare_runs(self):

        first = self.manager.record_run(self.sample_run)

        second_data = {
            "run_id": "test-run-002",
            "success": False,

            "stats": {
                "passed": 8,
                "failed": 2,
                "total": 10
            },

            "configuration": {
                "iterations": 10,
                "workers": 4,
                "random_seed": 99
            }
        }

        second = self.manager.record_run(second_data)

        comparison = self.manager.compare_runs(
            first["run_id"],
            second["run_id"]
        )

        self.assertTrue(comparison["success_changed"])

        self.assertIn(
            "workers",
            comparison["configuration_changes"]
        )

        self.assertIn(
            "failed",
            comparison["statistics_changes"]
        )

    def test_export_run(self):

        self.manager.record_run(self.sample_run)

        export_path = Path(self.temp_dir.name) / "exports" / "report.json"

        result = self.manager.export_run(
            "test-run-001",
            export_path
        )

        self.assertTrue(Path(result).exists())

    def test_invalid_run_data(self):

        with self.assertRaises(ValueError):

            self.manager.record_run("invalid data")


if __name__ == "__main__":
    unittest.main()