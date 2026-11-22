import json
import uuid

from datetime import datetime
from pathlib import Path
from typing import Optional

from core.executor import TestExecutor


class RunHistoryManager:

    def __init__(self, history_dir="execution_history"):

        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def record_run(self, run_data):

        if not isinstance(run_data, dict):
            raise ValueError("Run data must be a dictionary.")

        run_id = run_data.get("run_id") or str(uuid.uuid4())

        record = run_data.copy()

        record["run_id"] = run_id
        record["recorded_at"] = datetime.now().isoformat()

        file_path = self.history_dir / f"{run_id}.json"

        if file_path.exists():
            raise ValueError(f"Run ID already exists: {run_id}")

        self._write_json(file_path, record)

        return record

    def list_runs(self, limit=None):

        records = []

        for file_path in self.history_dir.glob("*.json"):

            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    records.append(json.load(file))

            except (json.JSONDecodeError, OSError):
                continue

        records.sort(
            key=lambda item: item.get("recorded_at", ""),
            reverse=True
        )

        if limit is not None:

            if limit < 1:
                raise ValueError("Limit must be at least 1.")

            records = records[:limit]

        return records

    def get_run(self, run_id):

        file_path = self.history_dir / f"{run_id}.json"

        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def compare_runs(self, first_run_id, second_run_id):

        first = self.get_run(first_run_id)
        second = self.get_run(second_run_id)

        if first is None or second is None:
            raise ValueError("One or both execution records were not found.")

        first_stats = first.get("stats", {})
        second_stats = second.get("stats", {})

        first_config = first.get("configuration", {})
        second_config = second.get("configuration", {})

        return {
            "first_run": first_run_id,
            "second_run": second_run_id,

            "success_changed": (
                first.get("success") != second.get("success")
            ),

            "success": {
                "first": first.get("success"),
                "second": second.get("success")
            },

            "statistics": {
                "first": first_stats,
                "second": second_stats
            },

            "configuration_changes": self._compare_dicts(
                first_config,
                second_config
            ),

            "statistics_changes": self._compare_dicts(
                first_stats,
                second_stats
            )
        }

    def export_run(self, run_id, output_path):

        record = self.get_run(run_id)

        if record is None:
            raise ValueError("Execution record not found.")

        output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        self._write_json(output_path, record)

        return str(output_path)

    @staticmethod
    def _compare_dicts(first, second):

        changes = {}

        all_keys = set(first.keys()) | set(second.keys())

        for key in all_keys:

            first_value = first.get(key)
            second_value = second.get(key)

            if first_value != second_value:

                changes[key] = {
                    "first": first_value,
                    "second": second_value
                }

        return changes

    @staticmethod
    def _write_json(file_path, data):

        with open(file_path, "w", encoding="utf-8") as file:

            json.dump(
                data,
                file,
                indent=4,
                default=str
            )