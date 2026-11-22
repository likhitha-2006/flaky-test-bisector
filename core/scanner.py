import ast
import json
import os
from pathlib import Path


class RepositoryScanner:

    IGNORE_DIRS = {
        ".git", ".venv", "venv", "__pycache__",
        "node_modules", ".pytest_cache",
        "site-packages", "dist", "build"
    }

    PYTEST_CONFIGS = [
        "pytest.ini",
        "pyproject.toml",
        "tox.ini",
        "setup.cfg"
    ]

    def __init__(self, repository_path):

        self.root = Path(repository_path).resolve()

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        self.python_files = []
        self.test_files = []
        self.test_functions = []
        self.test_classes = []
        self.config_files = []
        self.scan_errors = []

    def scan(self):

        self.python_files.clear()
        self.test_files.clear()
        self.test_functions.clear()
        self.test_classes.clear()
        self.config_files.clear()
        self.scan_errors.clear()

        self._discover_files()
        self._discover_configurations()
        self._analyze_test_files()

        return self.get_results()

    def _discover_files(self):

        for current_root, directories, files in os.walk(self.root):

            directories[:] = [
                d for d in directories
                if d not in self.IGNORE_DIRS
            ]

            for filename in files:

                file_path = Path(current_root) / filename

                if file_path.is_symlink():
                    continue

                if filename.endswith(".py"):

                    relative = str(file_path.relative_to(self.root))
                    self.python_files.append(relative)

                    if filename.startswith("test_") or filename.endswith("_test.py"):
                        self.test_files.append(relative)

    def _discover_configurations(self):

        for name in self.PYTEST_CONFIGS:

            if (self.root / name).is_file():
                self.config_files.append(name)

    def _analyze_test_files(self):

        for relative in self.test_files:

            try:

                source = (self.root / relative).read_text(encoding="utf-8")
                tree = ast.parse(source)

                self._extract_tests(tree, relative)

            except (SyntaxError, UnicodeDecodeError, OSError) as error:

                self.scan_errors.append({
                    "file": relative,
                    "error": str(error)
                })

    def _extract_tests(self, tree, file_path):

        for node in ast.walk(tree):

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

                if node.name.startswith("test_"):

                    self.test_functions.append({
                        "name": node.name,
                        "file": file_path,
                        "line": node.lineno,
                        "type": "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                    })

            elif isinstance(node, ast.ClassDef):

                if node.name.startswith("Test"):

                    methods = [
                        method.name
                        for method in node.body
                        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and method.name.startswith("test_")
                    ]

                    self.test_classes.append({
                        "name": node.name,
                        "file": file_path,
                        "line": node.lineno,
                        "methods": methods
                    })

    def get_results(self):

        return {
            "repository": str(self.root),
            "statistics": {
                "total_python_files": len(self.python_files),
                "total_test_files": len(self.test_files),
                "total_test_functions": len(self.test_functions),
                "total_test_classes": len(self.test_classes),
                "total_config_files": len(self.config_files),
                "scan_errors": len(self.scan_errors)
            },
            "python_files": self.python_files,
            "test_files": self.test_files,
            "test_functions": self.test_functions,
            "test_classes": self.test_classes,
            "configuration_files": self.config_files,
            "scan_errors": self.scan_errors
        }

    def save_report(self, output_path):

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        output.write_text(
            json.dumps(self.get_results(), indent=4),
            encoding="utf-8"
        )

        return str(output.resolve())


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="FLAKEHUNTER Repository Scanner"
    )

    parser.add_argument("repository")

    args = parser.parse_args()

    scanner = RepositoryScanner(args.repository)

    print(json.dumps(scanner.scan(), indent=4))
