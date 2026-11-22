import argparse
import json
import uuid

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from core.executor import TestExecutor


class FlakyTestDetector:

    def __init__(
        self,
        repository_path,
        iterations=10,
        timeout=60
    ):

        self.root = Path(repository_path).resolve()

        self.iterations = iterations
        self.timeout = timeout

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        if iterations <= 0:
            raise ValueError("Iterations must be greater than zero")

        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

        self.executor = TestExecutor(
            self.root,
            timeout=timeout
        )

    def analyze(self, test_path=None):

        run_id = str(uuid.uuid4())

        executions = []

        test_history = defaultdict(list)

        for iteration in range(1, self.iterations + 1):

            print(
                f"Flaky analysis: iteration "
                f"{iteration}/{self.iterations}"
            )

            result = self.executor.execute(
                test_path=test_path
            )

            executions.append({

                "iteration": iteration,

                "run_id": result["run_id"],

                "statistics": result["statistics"],

                "success": result["success"]

            })

            for test in result["tests"]:

                identity = self._get_test_identity(test)

                test_history[identity].append({

                    "iteration": iteration,

                    "status": test["status"],

                    "duration_seconds": test[
                        "duration_seconds"
                    ],

                    "details": test["details"]

                })

        analyzed_tests = []

        for identity, history in test_history.items():

            analyzed_tests.append(
                self._analyze_test(identity, history)
            )

        flaky_tests = [
            test for test in analyzed_tests
            if test["classification"] == "flaky"
        ]

        consistently_failed = [
            test for test in analyzed_tests
            if test["classification"] == "consistently_failed"
        ]

        stable_tests = [
            test for test in analyzed_tests
            if test["classification"] == "stable_passed"
        ]

        total_executions = sum(
            len(test["history"])
            for test in analyzed_tests
        )

        total_failures = sum(
            test["failed_count"] + test["error_count"]
            for test in analyzed_tests
        )

        return {

            "run_id": run_id,

            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "repository": str(self.root),

            "configuration": {

                "iterations": self.iterations,

                "timeout": self.timeout

            },

            "summary": {

                "total_unique_tests": len(analyzed_tests),

                "flaky_tests": len(flaky_tests),

                "consistently_failed_tests": len(
                    consistently_failed
                ),

                "stable_tests": len(stable_tests),

                "total_test_executions": total_executions,

                "total_failures": total_failures

            },

            "executions": executions,

            "tests": analyzed_tests,

            "flaky_test_details": flaky_tests,

            "success": len(flaky_tests) == 0
                and len(consistently_failed) == 0

        }

    @staticmethod
    def _get_test_identity(test):

        return (
            f"{test.get('file') or ''}::"
            f"{test.get('classname') or ''}::"
            f"{test.get('name') or ''}"
        )

    @staticmethod
    def _analyze_test(identity, history):

        passed = sum(
            1 for item in history
            if item["status"] == "passed"
        )

        failed = sum(
            1 for item in history
            if item["status"] == "failed"
        )

        errors = sum(
            1 for item in history
            if item["status"] == "error"
        )

        skipped = sum(
            1 for item in history
            if item["status"] == "skipped"
        )

        total = len(history)

        failures = failed + errors

        if passed > 0 and failures > 0:

            classification = "flaky"

        elif failures == total and total > 0:

            classification = "consistently_failed"

        elif passed == total and total > 0:

            classification = "stable_passed"

        elif skipped == total and total > 0:

            classification = "skipped"

        else:

            classification = "incomplete"

        failure_rate = round(
            (failures / total) * 100,
            2
        ) if total else 0

        return {

            "test_id": identity,

            "classification": classification,

            "total_runs": total,

            "passed_count": passed,

            "failed_count": failed,

            "error_count": errors,

            "skipped_count": skipped,

            "failure_rate_percent": failure_rate,

            "history": history

        }

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
        description="FLAKEHUNTER Flaky Test Detector"
    )

    parser.add_argument("repository")

    parser.add_argument(
        "--iterations",
        type=int,
        default=10
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
        default="reports/flaky_analysis.json"
    )

    args = parser.parse_args()

    detector = FlakyTestDetector(
        args.repository,
        iterations=args.iterations,
        timeout=args.timeout
    )

    results = detector.analyze(
        test_path=args.test
    )

    report_path = detector.save_report(
        results,
        args.report
    )

    print("\nFLAKY TEST ANALYSIS SUMMARY")

    print(json.dumps(
        results["summary"],
        indent=4
    ))

    print("\nReport saved:", report_path)