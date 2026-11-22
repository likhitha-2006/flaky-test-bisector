import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path

from core.executor import TestExecutor


class ParallelTestRunner:

    def __init__(self, repository_path, workers=4, timeout=60):

        self.root = Path(repository_path).resolve()
        self.workers = workers
        self.timeout = timeout

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        if workers <= 0:
            raise ValueError("Workers must be greater than zero")

        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

    def run(self, test_path=None):

        run_id = str(uuid.uuid4())

        with tempfile.TemporaryDirectory(
            prefix="flakehunter_parallel_"
        ) as temp_dir:

            xml_path = Path(temp_dir) / "parallel_results.xml"

            command = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-q",
                "-n",
                str(self.workers),
                "--dist=load",
                "--junitxml",
                str(xml_path)
            ]

            if test_path:
                command.append(str(test_path))
            else:
                command.append(".")

            environment = os.environ.copy()

            environment["PYTHONDONTWRITEBYTECODE"] = "1"

            start_time = time.perf_counter()

            stdout = ""
            stderr = ""
            exit_code = None
            timed_out = False

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

                stderr += "\nFLAKEHUNTER: Parallel execution timed out."

            except OSError as error:

                stderr = str(error)
                exit_code = -1

            duration = round(
                time.perf_counter() - start_time,
                4
            )

            tests = []

            if xml_path.exists():

                try:

                    tests = TestExecutor._parse_xml(
                        xml_path
                    )

                except Exception as error:

                    stderr += (
                        "\nUnable to parse parallel test report: "
                        + str(error)
                    )

            passed = sum(
                1 for test in tests
                if test["status"] == "passed"
            )

            failed = sum(
                1 for test in tests
                if test["status"] == "failed"
            )

            errors = sum(
                1 for test in tests
                if test["status"] == "error"
            )

            skipped = sum(
                1 for test in tests
                if test["status"] == "skipped"
            )

            return {

                "run_id": run_id,

                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),

                "repository": str(self.root),

                "configuration": {

                    "workers": self.workers,
                    "timeout": self.timeout,
                    "distribution": "load"

                },

                "command": command,

                "statistics": {

                    "total": len(tests),
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "skipped": skipped,

                    "duration_seconds": duration,

                    "exit_code": exit_code,

                    "timed_out": timed_out

                },

                "tests": tests,

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

    parser = argparse.ArgumentParser(
        description="FLAKEHUNTER Parallel Test Runner"
    )

    parser.add_argument("repository")

    parser.add_argument(
        "--workers",
        type=int,
        default=4
    )

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
        default="reports/parallel_report.json"
    )

    args = parser.parse_args()

    runner = ParallelTestRunner(
        args.repository,
        workers=args.workers,
        timeout=args.timeout
    )

    results = runner.run(
        test_path=args.test
    )

    report_path = runner.save_report(
        results,
        args.report
    )

    print("\nPARALLEL EXECUTION SUMMARY")

    print(json.dumps(
        results["statistics"],
        indent=4
    ))

    print("\nReport saved:", report_path)