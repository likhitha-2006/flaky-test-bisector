import json
import tempfile
import unittest

from pathlib import Path

from core.randomizer import RandomizedTestRunner


class TestRandomizedTestRunner(unittest.TestCase):

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

def test_four():
    assert 4 == 4
""",
            encoding="utf-8"
        )

        self.runner = RandomizedTestRunner(
            self.repository
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_randomized_execution(self):

        results = self.runner.run(
            iterations=2,
            seed=42
        )

        self.assertEqual(
            results["summary"]["total_iterations"],
            2
        )

        self.assertEqual(
            results["summary"]["successful_iterations"],
            2
        )

    def test_test_execution_order_recorded(self):

        results = self.runner.run(
            iterations=1,
            seed=42
        )

        execution_order = results["iterations"][0][
            "execution_order"
        ]

        self.assertEqual(len(execution_order), 4)

    def test_seed_recorded(self):

        results = self.runner.run(
            iterations=1,
            seed=100
        )

        self.assertEqual(
            results["iterations"][0]["seed"],
            100
        )

    def test_same_seed_reproduces_order(self):

        first = self.runner.run(
            iterations=1,
            seed=123
        )

        second = self.runner.run(
            iterations=1,
            seed=123
        )

        first_order = first["iterations"][0][
            "execution_order"
        ]

        second_order = second["iterations"][0][
            "execution_order"
        ]

        self.assertEqual(
            first_order,
            second_order
        )

    def test_invalid_iterations(self):

        with self.assertRaises(ValueError):

            self.runner.run(iterations=0)

    def test_report_generation(self):

        results = self.runner.run(
            iterations=1,
            seed=42
        )

        report_path = self.repository / "report.json"

        saved_path = self.runner.save_report(
            results,
            report_path
        )

        self.assertTrue(Path(saved_path).exists())

        saved_data = json.loads(
            Path(saved_path).read_text(encoding="utf-8")
        )

        self.assertIn("iterations", saved_data)


if __name__ == "__main__":
    unittest.main()