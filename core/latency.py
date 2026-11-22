import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import uuid

from datetime import datetime, timezone
from pathlib import Path

from core.executor import TestExecutor


LATENCY_PLUGIN = r'''
import os
import random
import time


def pytest_configure(config):

    seed = int(os.environ["FLAKEHUNTER_LATENCY_SEED"])

    random.seed(seed)


def pytest_runtest_setup(item):

    minimum = float(os.environ["FLAKEHUNTER_LATENCY_MIN"])
    maximum = float(os.environ["FLAKEHUNTER_LATENCY_MAX"])

    delay = random.uniform(minimum, maximum)

    time.sleep(delay)
'''


class LatencyTestRunner:

    def __init__(
        self,
        repository_path,
        minimum_delay=0.1,
        maximum_delay=1.0,
        timeout=60
    ):

        self.root = Path(repository_path).resolve()

        self.minimum_delay = minimum_delay
        self.maximum_delay = maximum_delay
        self.timeout = timeout

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        if minimum_delay < 0:
            raise ValueError("Minimum delay cannot be negative")

        if maximum_delay < minimum_delay:
            raise ValueError(
                "Maximum delay must be greater than or equal to minimum delay"
            )

        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

    def run(self, seed=42, test_path=None):

        if not isinstance(seed, int):
            raise ValueError("Seed must be an integer")

        run_id = str(uuid.uuid4())

        with tempfile.TemporaryDirectory(
            prefix="flakehunter_latency_"
        ) as temp_dir:

            temp = Path(temp_dir)

            plugin_file = temp / "flakehunter_latency_plugin.py"
            xml_file = temp / "results.xml"

            plugin_file.write_text(
                LATENCY_PLUGIN,
                encoding="utf-8"
            )

            command = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-p",
                "flakehunter_latency_plugin",
                "-q",
                "--junitxml",
                str(xml_file)
            ]

            if test_path:
                command.append(str(test_path))
            else:
                command.append(".")

            environment = os.environ.copy()

            environment["PYTHONDONTWRITEBYTECODE"] = "1"

            environment["PYTHONPATH"] = (
                str(temp)
                + os.pathsep
                + environment.get("PYTHONPATH", "")
            )

            environment["FLAKEHUNTER_LATENCY_SEED"] = str(seed)

            environment["FLAKEHUNTER_LATENCY_MIN"] = str(
                self.minimum_delay
            )

            environment["FLAKEHUNTER_LATENCY_MAX"] = str(
                self.maximum_delay
            )

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

                stderr += "\nFLAKEHUNTER: Latency execution timed out."

            except OSError as error:

                stderr = str(error)
                exit_code = -1

            duration = round(
                time.perf_counter() - start_time,
                4
            )

            tests = []

            if xml_file.exists():

                try:

                    tests = TestExecutor._parse_xml(
                        xml_file
                    )

                except Exception as error:

                    stderr += (
                        "\nUnable to parse test report: "
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

                    "minimum_delay": self.minimum_delay,
                    "maximum_delay": self.maximum_delay,
                    "seed": seed,
                    "timeout": self.timeout

                },

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
        description="FLAKEHUNTER Latency Simulation"
    )

    parser.add_argument("repository")

    parser.add_argument(
        "--min-delay",
        type=float,
        default=0.1
    )

    parser.add_argument(
        "--max-delay",
        type=float,
        default=1.0
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42
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
        default="reports/latency_report.json"
    )

    args = parser.parse_args()

    runner = LatencyTestRunner(
        args.repository,
        minimum_delay=args.min_delay,
        maximum_delay=args.max_delay,
        timeout=args.timeout
    )

    results = runner.run(
        seed=args.seed,
        test_path=args.test
    )

    report_path = runner.save_report(
        results,
        args.report
    )

    print("\nLATENCY SIMULATION SUMMARY")

    print(json.dumps(
        results["statistics"],
        indent=4
    ))

    print("\nReport saved:", report_path)