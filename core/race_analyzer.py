import argparse
import ast
import json
import os
import uuid

from datetime import datetime, timezone
from pathlib import Path


class RaceConditionAnalyzer:

    IGNORE_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "site-packages",
        "dist",
        "build"
    }

    CONCURRENCY_MODULES = {
        "threading",
        "multiprocessing",
        "concurrent"
    }

    TIMING_FUNCTIONS = {
        "sleep",
        "wait",
        "join"
    }

    def __init__(self, repository_path):

        self.root = Path(repository_path).resolve()

        if not self.root.exists():
            raise FileNotFoundError(self.root)

        if not self.root.is_dir():
            raise NotADirectoryError(self.root)

        self.findings = []
        self.scan_errors = []
        self.python_files = []

    def analyze(self):

        self.findings.clear()
        self.scan_errors.clear()
        self.python_files.clear()

        self._discover_files()

        for relative_path in self.python_files:

            file_path = self.root / relative_path

            try:

                source = file_path.read_text(
                    encoding="utf-8"
                )

                tree = ast.parse(source)

                visitor = RaceAnalysisVisitor(
                    relative_path
                )

                visitor.visit(tree)

                self.findings.extend(
                    visitor.findings
                )

            except (
                SyntaxError,
                UnicodeDecodeError,
                OSError
            ) as error:

                self.scan_errors.append({

                    "file": relative_path,

                    "error": str(error)

                })

        return self._build_report()

    def _discover_files(self):

        for current_root, directories, files in os.walk(
            self.root
        ):

            directories[:] = [
                directory
                for directory in directories
                if directory not in self.IGNORE_DIRS
            ]

            for filename in files:

                if not filename.endswith(".py"):
                    continue

                file_path = Path(current_root) / filename

                if file_path.is_symlink():
                    continue

                relative = str(
                    file_path.relative_to(self.root)
                )

                self.python_files.append(relative)

    def _build_report(self):

        shared_state = [
            finding for finding in self.findings
            if finding["category"] == "shared_state"
        ]

        concurrency = [
            finding for finding in self.findings
            if finding["category"] == "concurrency"
        ]

        timing = [
            finding for finding in self.findings
            if finding["category"] == "timing_sensitive"
        ]

        file_operations = [
            finding for finding in self.findings
            if finding["category"] == "shared_file_access"
        ]

        return {

            "analysis_id": str(uuid.uuid4()),

            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

            "repository": str(self.root),

            "summary": {

                "total_python_files": len(
                    self.python_files
                ),

                "total_findings": len(
                    self.findings
                ),

                "shared_state_findings": len(
                    shared_state
                ),

                "concurrency_findings": len(
                    concurrency
                ),

                "timing_findings": len(
                    timing
                ),

                "shared_file_findings": len(
                    file_operations
                ),

                "scan_errors": len(
                    self.scan_errors
                )

            },

            "risk_assessment": {

                "race_condition_detected": False,

                "potential_race_condition": (
                    len(shared_state) > 0
                    and len(concurrency) > 0
                ),

                "note": (
                    "Static analysis identifies potential "
                    "risk patterns. Runtime evidence is "
                    "required to confirm an actual race condition."
                )

            },

            "findings": self.findings,

            "scan_errors": self.scan_errors

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


class RaceAnalysisVisitor(ast.NodeVisitor):

    def __init__(self, file_path):

        self.file_path = file_path

        self.findings = []

        self.module_scope = True

    def _add_finding(
        self,
        category,
        severity,
        description,
        node,
        evidence
    ):

        self.findings.append({

            "category": category,

            "severity": severity,

            "file": self.file_path,

            "line": getattr(node, "lineno", 1),

            "description": description,

            "evidence": evidence,

            "confirmed": False,

            "classification": "potential_risk"

        })

    def visit_Assign(self, node):

        if self.module_scope:

            for target in node.targets:

                if self._is_mutable_assignment(
                    node.value
                ):

                    self._add_finding(

                        category="shared_state",

                        severity="medium",

                        description=(
                            "Module-level mutable state "
                            "may be shared between tests."
                        ),

                        node=node,

                        evidence=(
                            "Module-level mutable variable: "
                            + ast.unparse(target)
                        )

                    )

        if self._is_environment_assignment(node):

            self._add_finding(

                category="shared_state",

                severity="medium",

                description=(
                    "Environment variables are modified "
                    "and may affect other tests."
                ),

                node=node,

                evidence=ast.unparse(node)

            )

        self.generic_visit(node)

    def visit_AnnAssign(self, node):

        if (
            self.module_scope
            and self._is_mutable_assignment(node.value)
        ):

            self._add_finding(

                category="shared_state",

                severity="medium",

                description=(
                    "Module-level annotated mutable state "
                    "may be shared between tests."
                ),

                node=node,

                evidence=ast.unparse(node)

            )

        self.generic_visit(node)

    def visit_Global(self, node):

        self._add_finding(

            category="shared_state",

            severity="medium",

            description=(
                "Global variables are accessed or modified. "
                "This can introduce shared-state problems."
            ),

            node=node,

            evidence=(
                "Global declarations: "
                + ", ".join(node.names)
            )

        )

    def visit_Call(self, node):

        function_name = self._get_function_name(
            node.func
        )

        root_name = function_name.split(".")[0]

        if root_name in {
            "threading",
            "multiprocessing",
            "concurrent"
        }:

            self._add_finding(

                category="concurrency",

                severity="high",

                description=(
                    "Concurrency-related API detected. "
                    "Inspect shared resource access."
                ),

                node=node,

                evidence=function_name

            )

        elif function_name in {
            "Thread",
            "Process",
            "ThreadPoolExecutor",
            "ProcessPoolExecutor"
        }:

            self._add_finding(

                category="concurrency",

                severity="high",

                description=(
                    "A thread or process execution mechanism "
                    "was detected."
                ),

                node=node,

                evidence=function_name

            )

        if (
            function_name == "time.sleep"
            or function_name.endswith(".sleep")
        ):

            self._add_finding(

                category="timing_sensitive",

                severity="medium",

                description=(
                    "Artificial delay detected. "
                    "Test behavior may depend on timing."
                ),

                node=node,

                evidence=function_name

            )

        if (
            function_name in {
                "open",
                "Path.open"
            }
            and len(node.args) >= 2
        ):

            mode = node.args[1]

            if isinstance(mode, ast.Constant):

                if mode.value in {"w", "a", "w+", "a+"}:

                    self._add_finding(

                        category="shared_file_access",

                        severity="medium",

                        description=(
                            "File opened in write or append mode. "
                            "Concurrent tests may modify shared files."
                        ),

                        node=node,

                        evidence=ast.unparse(node)

                    )

        self.generic_visit(node)

    def visit_FunctionDef(self, node):

        previous_scope = self.module_scope

        self.module_scope = False

        self.generic_visit(node)

        self.module_scope = previous_scope

    def visit_AsyncFunctionDef(self, node):

        previous_scope = self.module_scope

        self.module_scope = False

        self.generic_visit(node)

        self.module_scope = previous_scope

    def visit_ClassDef(self, node):

        previous_scope = self.module_scope

        self.module_scope = False

        self.generic_visit(node)

        self.module_scope = previous_scope

    @staticmethod
    def _is_mutable_assignment(value):

        if isinstance(value, (ast.List, ast.Dict, ast.Set)):

            return True

        if isinstance(value, ast.Call):

            if isinstance(value.func, ast.Name):

                return value.func.id in {
                    "list",
                    "dict",
                    "set"
                }

        return False

    @staticmethod
    def _is_environment_assignment(node):

        for target in node.targets:

            if isinstance(target, ast.Subscript):

                if isinstance(target.value, ast.Attribute):

                    if (
                        isinstance(target.value.value, ast.Name)
                        and target.value.value.id == "os"
                        and target.value.attr == "environ"
                    ):

                        return True

        return False

    @staticmethod
    def _get_function_name(node):

        if isinstance(node, ast.Name):

            return node.id

        if isinstance(node, ast.Attribute):

            parent = RaceAnalysisVisitor._get_function_name(
                node.value
            )

            return parent + "." + node.attr

        return ""


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="FLAKEHUNTER Race Condition Analyzer"
    )

    parser.add_argument("repository")

    parser.add_argument(
        "--report",
        default="reports/race_analysis.json"
    )

    args = parser.parse_args()

    analyzer = RaceConditionAnalyzer(
        args.repository
    )

    results = analyzer.analyze()

    report_path = analyzer.save_report(
        results,
        args.report
    )

    print("\nRACE CONDITION ANALYSIS")

    print(json.dumps(
        results["summary"],
        indent=4
    ))

    print("\nRisk Assessment:")

    print(json.dumps(
        results["risk_assessment"],
        indent=4
    ))

    print("\nReport saved:", report_path)