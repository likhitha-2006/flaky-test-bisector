import json
import csv

from pathlib import Path
from datetime import datetime


class ReportGenerator:

    def __init__(
        self,
        reports_dir="reports",
        history_dir="execution_history"
    ):
        self.reports_dir = Path(reports_dir)
        self.history_dir = Path(history_dir)

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def load_json_files(self, directory):

        records = []

        for file_path in directory.glob("*.json"):

            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)

                records.append({
                    "filename": file_path.name,
                    "data": data
                })

            except (json.JSONDecodeError, OSError):
                continue

        return records

    def generate_analytics(self):

        history = self.load_json_files(self.history_dir)
        reports = self.load_json_files(self.reports_dir)

        total_runs = len(history)

        successful_runs = sum(
            1 for item in history
            if item["data"].get("success") is True
        )

        failed_runs = sum(
            1 for item in history
            if item["data"].get("success") is False
        )

        success_rate = (
            round(successful_runs / total_runs * 100, 2)
            if total_runs else 0
        )

        total_duration = sum(
            float(item["data"].get("duration", 0))
            for item in history
        )

        execution_modes = {}

        for item in history:

            mode = item["data"].get(
                "execution_mode",
                "Other"
            )

            execution_modes[mode] = (
                execution_modes.get(mode, 0) + 1
            )

        flaky_summary = {
            "flaky_tests": 0,
            "stable_tests": 0,
            "consistently_failed_tests": 0,
            "total_test_executions": 0
        }

        for item in reports:

            data = item["data"]

            if "summary" in data:

                summary = data["summary"]

                if "flaky_tests" in summary:

                    flaky_summary["flaky_tests"] += summary.get(
                        "flaky_tests", 0
                    )

                    flaky_summary["stable_tests"] += summary.get(
                        "stable_tests", 0
                    )

                    flaky_summary["consistently_failed_tests"] += (
                        summary.get("consistently_failed_tests", 0)
                    )

                    flaky_summary["total_test_executions"] += (
                        summary.get("total_test_executions", 0)
                    )

        race_summary = {
            "potential_race_condition": 0,
            "race_condition_detected": 0
        }

        for item in reports:

            data = item["data"]

            if "risk_assessment" in data:

                assessment = data["risk_assessment"]

                for key in race_summary:

                    if assessment.get(key) is True:
                        race_summary[key] += 1

        analytics = {

            "generated_at": datetime.now().isoformat(),

            "execution_summary": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate_percent": success_rate,
                "total_execution_duration_seconds": round(
                    total_duration, 3
                )
            },

            "execution_modes": execution_modes,

            "flaky_test_summary": flaky_summary,

            "race_condition_summary": race_summary,

            "available_reports": [
                item["filename"] for item in reports
            ]
        }

        return analytics

    def export_json(self, output_path="reports/analytics_report.json"):

        analytics = self.generate_analytics()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as file:

            json.dump(
                analytics,
                file,
                indent=4
            )

        return str(output_path)

    def export_history_csv(
        self,
        output_path="reports/execution_history.csv"
    ):

        history = self.load_json_files(self.history_dir)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fields = [
            "run_id",
            "execution_mode",
            "repository",
            "success",
            "exit_code",
            "duration",
            "recorded_at"
        ]

        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            for item in history:

                record = item["data"]

                writer.writerow({
                    field: record.get(field, "")
                    for field in fields
                })

        return str(output_path)