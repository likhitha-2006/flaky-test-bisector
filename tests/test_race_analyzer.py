import json
import tempfile
import unittest

from pathlib import Path

from core.race_analyzer import RaceConditionAnalyzer


class TestRaceConditionAnalyzer(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.repository = Path(self.temp_dir.name)

    def tearDown(self):

        self.temp_dir.cleanup()

    def create_file(self, filename, content):

        file_path = self.repository / filename

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        return file_path

    def test_shared_mutable_state_detection(self):

        self.create_file(
            "test_shared.py",
            """
shared_list = []

def test_one():
    shared_list.append(10)
"""
        )

        analyzer = RaceConditionAnalyzer(
            self.repository
        )

        results = analyzer.analyze()

        self.assertGreater(
            results["summary"]["shared_state_findings"],
            0
        )

    def test_global_variable_detection(self):

        self.create_file(
            "test_global.py",
            """
counter = 0

def test_counter():
    global counter
    counter += 1
"""
        )

        analyzer = RaceConditionAnalyzer(
            self.repository
        )

        results = analyzer.analyze()

        self.assertGreater(
            results["summary"]["shared_state_findings"],
            0
        )

    def test_concurrency_detection(self):

        self.create_file(
            "test_thread.py",
            """
import threading

def test_thread():
    worker = threading.Thread(target=lambda: None)
    worker.start()
    worker.join()
"""
        )

        analyzer = RaceConditionAnalyzer(
            self.repository
        )

        results = analyzer.analyze()

        self.assertGreater(
            results["summary"]["concurrency_findings"],
            0
        )

    def test_timing_detection(self):

        self.create_file(
            "test_timing.py",
            """
import time

def test_timing():
    time.sleep(0.1)
"""
        )

        analyzer = RaceConditionAnalyzer(
            self.repository
        )

        results = analyzer.analyze()

        self.assertGreater(
            results["summary"]["timing_findings"],
            0
        )

    def test_clean_repository(self):

        self.create_file(
            "test_clean.py",
            """
def test_addition():
    assert 10 + 20 == 30
"""
        )

        analyzer = RaceConditionAnalyzer(
            self.repository
        )

        results = analyzer.analyze()

        self.assertEqual(
            results["summary"]["total_findings"],
            0
        )

    def test_report_generation(self):

        self.create_file(
            "test_sample.py",
            """
shared_data = {}

def test_example():
    assert True
"""
        )

        analyzer = RaceConditionAnalyzer(
            self.repository
        )

        results = analyzer.analyze()

        report_path = self.repository / "race_report.json"

        saved_path = analyzer.save_report(
            results,
            report_path
        )

        self.assertTrue(Path(saved_path).exists())

        saved_data = json.loads(
            Path(saved_path).read_text(encoding="utf-8")
        )

        self.assertIn(
            "risk_assessment",
            saved_data
        )


if __name__ == "__main__":
    unittest.main()