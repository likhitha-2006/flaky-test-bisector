import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid

from datetime import datetime, timezone
from pathlib import Path


COLLECTION_PLUGIN = r'''
import json
import os


def pytest_collection_finish(session):

    output_file = os.environ["FLAKEHUNTER_COLLECTION_FILE"]

    nodeids = [
        item.nodeid
        for item in session.items
    ]

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(nodeids, file, indent=4)
'''


class FailureIsolator:

    def __init__(self, repository_path, timeout=60):

        self.root = Path(repository_path).resolve()
        self.timeout = timeout

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

        self.attempts = []

    def isolate(self, test_path=None):

        self.attempts.clear()

        run_id = str(uuid.uuid4())

        test_ids = self._collect_tests(test_path)

        if not test_ids:

            return self._build_result(
                run_id,
                [],
                [],
                False,
                "No tests were collected."
            )

        print("Collected tests:", len(test_ids))

        print("\nRunning initial test suite...")

        initial_result = self._run_tests(
            test_ids,
            label="initial"
        )

        if not initial_result["failure_detected"]:

            return self._build_result(
                run_id,
                test_ids,
                test_ids,
                False,
                "The initial test suite did not reproduce a failure."
            )

        print("\nInitial failure reproduced.")

        print("\nStarting delta debugging...")

        minimized = self._ddmin(
            test_ids,
            self._failure_predicate
        )

        print("\nFailure isolation completed.")

        return self._build_result(
            run_id,
            test_ids,
            minimized,
            True,
            "A minimal failure-inducing test set was identified."
        )

    def _collect_tests(self, test_path=None):

        with tempfile.TemporaryDirectory(
            prefix="flakehunter_collect_"
        ) as temp_dir:

            temp = Path(temp_dir)

            plugin_file = temp / "flakehunter_collect_plugin.py"

            output_file = temp / "collection.json"

            plugin_file.write_text(
                COLLECTION_PLUGIN,
                encoding="utf-8"
            )

            command = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-p",
                "flakehunter_collect_plugin",
                "--collect-only",
                "-q"
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

            environment["FLAKEHUNTER_COLLECTION_FILE"] = str(
                output_file
            )

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

                if process.returncode != 0:

                    raise RuntimeError(
                        "Test collection failed:\n"
                        + process.stdout
                        + process.stderr
                    )

                if not output_file.exists():
                    return []

                return json.loads(
                    output_file.read_text(
                        encoding="utf-8"
                    )
                )

            except subprocess.TimeoutExpired:

                raise TimeoutError(
                    "Test collection timed out."
                )

    def _run_tests(self, test_ids, label="attempt"):

        if not test_ids:

            return {
                "failure_detected": False,
                "test_count": 0,
                "failed_tests": [],
                "timed_out": False,
                "return_code": None
            }

        with tempfile.TemporaryDirectory(
            prefix="flakehunter_isolate_"
        ) as temp_dir:

            xml_file = Path(temp_dir) / "results.xml"

            command = [
                sys.executable,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "-q",
                "--junitxml",
                str(xml_file)
            ]

            command.extend(test_ids)

            environment = os.environ.copy()

            environment["PYTHONDONTWRITEBYTECODE"] = "1"

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

            except OSError as error:

                stderr = str(error)
                exit_code = -1

            failed_tests = []

            if xml_file.exists():

                try:

                    from core.executor import TestExecutor

                    parsed = TestExecutor._parse_xml(
                        xml_file
                    )

                    failed_tests = [
                        test for test in parsed
                        if test["status"] in {"failed", "error"}
                    ]

                except Exception as error:

                    stderr += (
                        "\nReport parsing error: "
                        + str(error)
                    )

            failure_detected = (
                not timed_out
                and exit_code not in (None, 0)
                and len(failed_tests) > 0
            )

            result = {

                "label": label,

                "test_count": len(test_ids),

                "tests": list(test_ids),

                "failure_detected": failure_detected,

                "failed_tests": failed_tests,

                "timed_out": timed_out,

                "return_code": exit_code,

                "stdout": stdout,

                "stderr": stderr

            }

            self.attempts.append(result)

            print(
                f"{label}: {len(test_ids)} tests | "
                f"{'FAIL' if failure_detected else 'PASS'}"
            )

            return result

    def _failure_predicate(self, test_ids):

        result = self._run_tests(
            test_ids,
            label=f"delta_attempt_{len(self.attempts) + 1}"
        )

        return result["failure_detected"]

    def _ddmin(self, test_ids, failure_predicate):

        current = list(test_ids)

        if not current:
            return []

        granularity = 2

        while len(current) >= 2:

            subsets = self._partition(
                current,
                granularity
            )

            reduced = False

            # First check whether any subset preserves the failure.

            for subset in subsets:

                if failure_predicate(subset):

                    current = subset

                    granularity = max(
                        granularity - 1,
                        2
                    )

                    reduced = True

                    break

            if reduced:
                continue

            # Then check whether removing a subset preserves failure.

            for subset in subsets:

                complement = [
                    item for item in current
                    if item not in subset
                ]

                if complement and failure_predicate(
                    complement
                ):

                    current = complement

                    granularity = max(
                        granularity - 1,
                        2
                    )

                    reduced = True

                    break

            if reduced:
                continue

            if granularity >= len(current):
                break

            granularity = min(
                len(current),
                granularity * 2
            )

        return current

    @staticmethod
    def _partition(items, parts):

        length = len(items)

        base_size, remainder = divmod(
            length,
            parts
        )

        result = []

        start = 0

        for index in range(parts):

            size = base_size + (
                1 if index < remainder else 0
            )

            result.append(
                items[start:start + size]
            )

            start += size

        return [
            subset for subset in result
            if subset
        ]

    def _build_result(
        self,
        run_id,
        original_tests,
        minimized_tests,
        initial_failure,
        message
    ):

        return {

            "run_id": run_id,

            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "repository": str(self.root),

            "configuration": {

                "timeout": self.timeout

            },

            "summary": {

                "initial_test_count": len(original_tests),

                "minimized_test_count": len(
                    minimized_tests
                ),

                "tests_removed": (
                    len(original_tests)
                    - len(minimized_tests)
                ),

                "attempts": len(self.attempts),

                "initial_failure_reproduced": initial_failure,

                "failure_isolated": (
                    initial_failure
                    and bool(minimized_tests)
                )

            },

            "message": message,

            "original_tests": original_tests,

            "minimized_tests": minimized_tests,

            "attempt_history": self.attempts

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
        description="FLAKEHUNTER Failure Isolation"
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
        default="reports/isolation_report.json"
    )

    args = parser.parse_args()

    isolator = FailureIsolator(
        args.repository,
        timeout=args.timeout
    )

    results = isolator.isolate(
        test_path=args.test
    )

    report_path = isolator.save_report(
        results,
        args.report
    )

    print("\nFAILURE ISOLATION SUMMARY")

    print(json.dumps(
        results["summary"],
        indent=4
    ))

    print("\nMessage:", results["message"])

    print("\nReport saved:", report_path)