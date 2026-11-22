import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import uuid

from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree


PYTEST_PLUGIN = r'''
import json
import os
import random


def pytest_collection_modifyitems(session, config, items):

    seed = int(os.environ["FLAKEHUNTER_SEED"])

    generator = random.Random(seed)
    generator.shuffle(items)

    collection_file = os.environ["FLAKEHUNTER_COLLECTION_FILE"]

    with open(collection_file, "w", encoding="utf-8") as file:
        json.dump(
            [item.nodeid for item in items],
            file,
            indent=4
        )


def pytest_runtest_logstart(nodeid, location):

    order_file = os.environ["FLAKEHUNTER_ORDER_FILE"]

    with open(order_file, "a", encoding="utf-8") as file:
        file.write(json.dumps(nodeid) + "\n")
'''


class RandomizedTestRunner:

    def __init__(self, repository_path, timeout=60):

        self.root = Path(repository_path).resolve()
        self.timeout = timeout

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

    def run(self, iterations=10, seed=42, test_path=None):

        if iterations <= 0:
            raise ValueError("Iterations must be greater than zero")

        if not isinstance(seed, int):
            raise ValueError("Seed must be an integer")

        run_id = str(uuid.uuid4())

        iteration_results = []

        for number in range(iterations):

            current_seed = seed + number

            print(
                f"Running iteration {number + 1}/{iterations} "
                f"(seed={current_seed})..."
            )

            result = self._execute_iteration(
                iteration_number=number + 1,
                seed=current_seed,
                test_path=test_path
            )

            iteration_results.append(result)

        successful = sum(
            1 for result in iteration_results
            if result["success"]
        )

        failed = iterations - successful

        total_tests = sum(
            result["statistics"]["total"]
            for result in iteration_results
        )

        total_failures = sum(
            result["statistics"]["failed"]
            + result["statistics"]["errors"]
            for result in iteration_results
        )

        return {

            "run_id": run_id,

            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "repository": str(self.root),

            "configuration": {
                "iterations": iterations,
                "base_seed": seed,
                "timeout": self.timeout
            },

            "summary": {
                "total_iterations": iterations,
                "successful_iterations": successful,
                "failed_iterations": failed,
                "total_test_executions": total_tests,
                "total_test_failures": total_failures
            },

            "iterations": iteration_results,

            "success": failed == 0
        }

    def _execute_iteration(
        self,
        iteration_number,
        seed,
        test_path
    ):

        with tempfile.TemporaryDirectory(
            prefix="flakehunter_random_"
        ) as temporary_directory:

            temp = Path(temporary_directory)

            plugin_file = temp / "flakehunter_order_plugin.py"
            xml_file = temp / "results.xml"
            collection_file = temp / "collection.json"
            order_file = temp / "execution_order.jsonl"

            plugin_file.write_text(
                PYTEST_PLUGIN,
                encoding="utf-8"
            )

            command = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-p",
                "flakehunter_order_plugin",
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

            existing_pythonpath = environment.get(
                "PYTHONPATH",
                ""
            )

            environment["PYTHONPATH"] = (
                str(temp)
                + os.pathsep
                + existing_pythonpath
            )

            environment["FLAKEHUNTER_SEED"] = str(seed)

            environment["FLAKEHUNTER_COLLECTION_FILE"] = str(
                collection_file
            )

            environment["FLAKEHUNTER_ORDER_FILE"] = str(
                order_file
            )

            stdout = ""
            stderr = ""
            exit_code = None
            timed_out = False

            import time

            start_time = time.perf_counter()

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

            collection_order = self._read_json(
                collection_file,
                default=[]
            )

            execution_order = self._read_json_lines(
                order_file
            )

            tests = []

            if xml_file.exists():

                try:
                    tests = self._parse_xml(xml_file)

                except ElementTree.ParseError:
                    stderr += "\nUnable to parse pytest XML output."

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

                "iteration": iteration_number,

                "seed": seed,

                "collection_order": collection_order,

                "execution_order": execution_order,

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
    def _read_json(file_path, default):

        if not file_path.exists():
            return default

        try:

            return json.loads(
                file_path.read_text(encoding="utf-8")
            )

        except (json.JSONDecodeError, OSError):
            return default

    @staticmethod
    def _read_json_lines(file_path):

        if not file_path.exists():
            return []

        results = []

        try:

            for line in file_path.read_text(
                encoding="utf-8"
            ).splitlines():

                if line.strip():
                    results.append(json.loads(line))

        except (json.JSONDecodeError, OSError):
            return results

        return results

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

    parser = argparse.ArgumentParser(
        description="FLAKEHUNTER Randomized Test Runner"
    )

    parser.add_argument("repository")

    parser.add_argument(
        "--iterations",
        type=int,
        default=10
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
        default="reports/randomized_report.json"
    )

    args = parser.parse_args()

    runner = RandomizedTestRunner(
        args.repository,
        timeout=args.timeout
    )

    results = runner.run(
        iterations=args.iterations,
        seed=args.seed,
        test_path=args.test
    )

    report_path = runner.save_report(
        results,
        args.report
    )

    print("\nRANDOMIZED EXECUTION SUMMARY")
    print(json.dumps(results["summary"], indent=4))

    print("\nReport saved:", report_path)