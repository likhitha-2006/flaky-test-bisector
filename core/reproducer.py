import json
import uuid
import time

from datetime import datetime, timezone
from pathlib import Path

from core.executor import TestExecutor


class FailureReproducer:

    def __init__(
        self,
        repository_path,
        timeout=60,
        reports_dir="reports"
    ):

        self.root = Path(repository_path).resolve()
        self.timeout = timeout
        self.reports_dir = Path(reports_dir)

        self.reports_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        if not self.root.is_dir():
            raise ValueError(
                f"Invalid repository path: {self.root}"
            )

        if timeout <= 0:
            raise ValueError(
                "Timeout must be greater than zero"
            )

        self.executor = TestExecutor(
            self.root,
            timeout=timeout
        )

    def reproduce(
        self,
        test_path,
        test_name=None,
        attempts=3,
        seed=None
    ):

        if attempts <= 0:
            raise ValueError(
                "Attempts must be greater than zero"
            )

        if not test_path:
            raise ValueError(
                "A test path is required"
            )

        reproductions = []

        for attempt in range(1, attempts + 1):

            print(
                f"Reproduction attempt "
                f"{attempt}/{attempts}"
            )

            result = self.executor.execute(
                test_path=test_path
            )

            matching_tests = result["tests"]

            if test_name:
                matching_tests = [
                    test for test in matching_tests
                    if (
                        test.get("name") == test_name
                        or test.get("classname") == test_name
                        or (
                            f"{test.get('classname')}::"
                            f"{test.get('name')}"
                        ) == test_name
                    )
                ]

            failed_tests = [
                test for test in matching_tests
                if test["status"] in ("failed", "error")
            ]

            reproductions.append({

                "attempt": attempt,

                "run_id": result["run_id"],

                "success": (
                    len(matching_tests) > 0
                    and len(failed_tests) == 0
                    and not result["statistics"]["timed_out"]
                ),

                "failed_tests": failed_tests,

                "matching_tests": matching_tests,

                "statistics": result["statistics"],

                "stdout": result["stdout"],

                "stderr": result["stderr"]

            })

        reproduced_count = sum(
            1 for item in reproductions
            if not item["success"]
        )

        report = {

            "reproduction_id": str(uuid.uuid4()),

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "repository": str(self.root),

            "target_test": test_name or test_path,

            "test_path": test_path,

            "configuration": {

                "attempts": attempts,

                "timeout": self.timeout,

                "seed": seed

            },

          "summary": {

    "total_attempts": attempts,

    "reproduced_failures": reproduced_count,

    "not_reproduced": attempts - reproduced_count,

    "reproduced_consistently": (
        reproduced_count == attempts
    ),

    "reproduction_rate_percent": round(
        reproduced_count / attempts * 100,
        2
    )

},

            "attempts": reproductions

        }

        report_path = (
            self.reports_dir
            / f"reproduction_{report['reproduction_id']}.json"
        )

        with open(
            report_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                default=str
            )

        report["report_path"] = str(report_path)

        return report