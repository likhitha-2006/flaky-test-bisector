import json
import subprocess
import sys
import tempfile
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


class TestExecutor:

    def __init__(self, repository_path, timeout=60):

        self.root = Path(repository_path).resolve()
        self.timeout = timeout

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

    def execute(self, test_path=None):

        run_id = str(uuid.uuid4())

        with tempfile.TemporaryDirectory(
            prefix="flakehunter_"
        ) as temp_dir:

            xml_path = Path(temp_dir) / "results.xml"

            command = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-q",
                "--junitxml",
                str(xml_path)
            ]

            if test_path:
                command.append(str(test_path))
            else:
                command.append(".")

            environment = __import__("os").environ.copy()

            environment["PYTHONDONTWRITEBYTECODE"] = "1"

            start_time = time.perf_counter()

            timed_out = False
            stdout = ""
            stderr = ""
            exit_code = None

            try:

                process = subprocess.run(
                    command,
                    cwd=str(self.root),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=environment,
                    encoding="utf-8",
                    errors="replace"
                )

                stdout = process.stdout
                stderr = process.stderr
                exit_code = process.returncode

            except subprocess.TimeoutExpired as error:

                timed_out = True

                stdout = self._decode(error.stdout)
                stderr = self._decode(error.stderr)

                stderr += "\nFLAKEHUNTER: Execution timed out."

            except OSError as error:

                stderr = str(error)
                exit_code = -1

            duration = round(
                time.perf_counter() - start_time,
                4
            )

            test_results = []

            if xml_path.exists():

                try:
                    test_results = self._parse_xml(xml_path)

                except ElementTree.ParseError:
                    stderr += "\nUnable to parse pytest XML output."

            passed = sum(
                1 for test in test_results
                if test["status"] == "passed"
            )

            failed = sum(
                1 for test in test_results
                if test["status"] == "failed"
            )

            errors = sum(
                1 for test in test_results
                if test["status"] == "error"
            )

            skipped = sum(
                1 for test in test_results
                if test["status"] == "skipped"
            )

            return {

                "run_id": run_id,

                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),

                "repository": str(self.root),

                "command": command,

                "configuration": {
                    "timeout": self.timeout
                },

                "statistics": {

                    "total": len(test_results),
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "skipped": skipped,

                    "duration_seconds": duration,

                    "exit_code": exit_code,

                    "timed_out": timed_out
                },

                "tests": test_results,

                "stdout": stdout,

                "stderr": stderr,

                "success": (
                    exit_code == 0
                    and not timed_out
                )
            }

    @staticmethod
    def _decode(value):

        if value is None:
            return ""

        if isinstance(value, bytes):
            return value.decode(
                "utf-8",
                errors="replace"
            )

        return str(value)

    @staticmethod
    def _parse_xml(xml_path):

        tree = ElementTree.parse(xml_path)

        root = tree.getroot()

        results = []

        for case in root.iter("testcase"):

            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")

            if failure is not None:

                status = "failed"
                details = failure.get("message", "")
                details += "\n" + (failure.text or "")

            elif error is not None:

                status = "error"
                details = error.get("message", "")
                details += "\n" + (error.text or "")

            elif skipped is not None:

                status = "skipped"
                details = skipped.get("message", "")

            else:

                status = "passed"
                details = ""

            results.append({

                "name": case.get("name"),

                "classname": case.get("classname"),

                "file": case.get("file"),

                "duration_seconds": float(
                    case.get("time", 0)
                ),

                "status": status,

                "details": details.strip()

            })

        return results

    @staticmethod
    def save_report(results, output_path):

        output = Path(output_path)

        output.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        output.write_text(
            json.dumps(results, indent=4),
            encoding="utf-8"
        )

        return str(output.resolve())


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="FLAKEHUNTER Test Execution Engine"
    )

    parser.add_argument("repository")

    parser.add_argument(
        "--timeout",
        type=int,
        default=60
    )

    parser.add_argument(
        "--test",
        default=None
    )

    parser.add_argument(
        "--report",
        default="reports/execution_report.json"
    )

    args = parser.parse_args()

    executor = TestExecutor(
        args.repository,
        timeout=args.timeout
    )

    results = executor.execute(args.test)

    report = executor.save_report(
        results,
        args.report
    )

    print(json.dumps(
        results["statistics"],
        indent=4
    ))

    print("\nReport saved:", report)