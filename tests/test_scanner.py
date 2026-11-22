import tempfile
import unittest

from pathlib import Path

from core.scanner import RepositoryScanner


class TestRepositoryScanner(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.root = Path(self.temp_dir.name)

        (self.root / "test_sample.py").write_text(
            """
def test_login():
    assert True

def test_logout():
    assert True

class TestUser:

    def test_user_creation(self):
        assert True

    def test_user_deletion(self):
        assert True
""",
            encoding="utf-8"
        )

        (self.root / "main.py").write_text(
            """
def hello():
    return "Hello"
""",
            encoding="utf-8"
        )

        (self.root / "pytest.ini").write_text(
            "[pytest]\n",
            encoding="utf-8"
        )

    def tearDown(self):

        self.temp_dir.cleanup()

    def test_python_file_discovery(self):

        scanner = RepositoryScanner(self.root)

        results = scanner.scan()

        self.assertEqual(
            results["statistics"]["total_python_files"],
            2
        )

    def test_test_file_discovery(self):

        scanner = RepositoryScanner(self.root)

        results = scanner.scan()

        self.assertEqual(
            results["statistics"]["total_test_files"],
            1
        )

    def test_function_discovery(self):

        scanner = RepositoryScanner(self.root)

        results = scanner.scan()

        self.assertEqual(
            results["statistics"]["total_test_functions"],
            4
        )

    def test_class_discovery(self):

        scanner = RepositoryScanner(self.root)

        results = scanner.scan()

        self.assertEqual(
            results["statistics"]["total_test_classes"],
            1
        )

    def test_configuration_discovery(self):

        scanner = RepositoryScanner(self.root)

        results = scanner.scan()

        self.assertIn(
            "pytest.ini",
            results["configuration_files"]
        )

    def test_invalid_repository(self):

        with self.assertRaises(FileNotFoundError):

            RepositoryScanner(
                self.root / "nonexistent"
            )


if __name__ == "__main__":

    unittest.main()