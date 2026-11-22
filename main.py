import argparse
import json
import subprocess
import sys

from core.scanner import RepositoryScanner
from core.history import RunHistoryManager
from core.docker_runner import DockerTestRunner
from core.reproducer import FailureReproducer


def greet(name):
    return f"Hello {name}"


def calculate(a, b):
    return a + b


def run_module(module, arguments):
    """Execute an existing FLAKEHUNTER module."""

    command = [
        sys.executable,
        "-m",
        module
    ] + arguments

    result = subprocess.run(command)

    return result.returncode


def main():

    parser = argparse.ArgumentParser(
        description="FLAKEHUNTER - Flaky Test & Race Condition Hunter"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    # SCAN
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan a Python repository"
    )
    scan_parser.add_argument("repository")

    # RUN
    run_parser = subparsers.add_parser(
        "run",
        help="Execute repository tests"
    )
    run_parser.add_argument("repository")
    run_parser.add_argument("--timeout", type=int, default=60)
    run_parser.add_argument("--test")

    # RANDOMIZE
    random_parser = subparsers.add_parser(
        "randomize",
        help="Run tests in randomized order"
    )
    random_parser.add_argument("repository")
    random_parser.add_argument("--iterations", type=int, default=10)
    random_parser.add_argument("--seed", type=int, default=42)

    # PARALLEL
    parallel_parser = subparsers.add_parser(
        "parallel",
        help="Run tests in parallel"
    )
    parallel_parser.add_argument("repository")
    parallel_parser.add_argument("--workers", type=int, default=4)

    # LATENCY
    latency_parser = subparsers.add_parser(
        "latency",
        help="Run tests with simulated latency"
    )
    latency_parser.add_argument("repository")
    latency_parser.add_argument("--min-delay", type=float, default=0.1)
    latency_parser.add_argument("--max-delay", type=float, default=1.0)
    latency_parser.add_argument("--seed", type=int, default=42)

    # FLAKY ANALYSIS
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Detect flaky tests"
    )
    analyze_parser.add_argument("repository")
    analyze_parser.add_argument("--iterations", type=int, default=10)

    # RACE ANALYSIS
    race_parser = subparsers.add_parser(
        "race",
        help="Analyze potential race conditions"
    )
    race_parser.add_argument("repository")

    # FAILURE ISOLATION
    isolate_parser = subparsers.add_parser(
        "isolate",
        help="Isolate failing tests"
    )
    isolate_parser.add_argument("repository")

    # HISTORY
    subparsers.add_parser(
        "history",
        help="Display execution history"
    )

    # DOCKER
    docker_parser = subparsers.add_parser(
        "docker",
        help="Execute tests inside an isolated Docker container"
    )
    docker_parser.add_argument("repository")
    docker_parser.add_argument("--timeout", type=int, default=60)
    docker_parser.add_argument("--test")
    docker_parser.add_argument(
        "--image",
        default="flakehunter-python:3.11"
    )

    # FAILURE REPRODUCTION
    reproduce_parser = subparsers.add_parser(
        "reproduce",
        help="Reproduce and investigate test failures"
    )
    reproduce_parser.add_argument("repository")
    reproduce_parser.add_argument("--test", required=True)
    reproduce_parser.add_argument("--test-name")
    reproduce_parser.add_argument("--attempts", type=int, default=3)
    reproduce_parser.add_argument("--timeout", type=int, default=60)
    reproduce_parser.add_argument("--seed", type=int)

    args = parser.parse_args()

    # SCAN EXECUTION
    if args.command == "scan":

        scanner = RepositoryScanner(args.repository)

        results = scanner.scan()

        print(json.dumps(results, indent=4))

        scanner.save_report("reports/scan_report.json")

        return 0

    # NORMAL TEST EXECUTION
    elif args.command == "run":

        extra = [
            args.repository,
            "--timeout", str(args.timeout)
        ]

        if args.test:
            extra.extend(["--test", args.test])

        return run_module("core.executor", extra)

    # RANDOMIZED EXECUTION
    elif args.command == "randomize":

        return run_module(
            "core.randomizer",
            [
                args.repository,
                "--iterations", str(args.iterations),
                "--seed", str(args.seed)
            ]
        )

    # PARALLEL EXECUTION
    elif args.command == "parallel":

        return run_module(
            "core.parallel",
            [
                args.repository,
                "--workers", str(args.workers)
            ]
        )

    # LATENCY SIMULATION
    elif args.command == "latency":

        return run_module(
            "core.latency",
            [
                args.repository,
                "--min-delay", str(args.min_delay),
                "--max-delay", str(args.max_delay),
                "--seed", str(args.seed)
            ]
        )

    # FLAKY ANALYSIS
    elif args.command == "analyze":

        return run_module(
            "core.flaky_detector",
            [
                args.repository,
                "--iterations", str(args.iterations)
            ]
        )

    # RACE ANALYSIS
    elif args.command == "race":

        return run_module(
            "core.race_analyzer",
            [args.repository]
        )

    # FAILURE ISOLATION
    elif args.command == "isolate":

        return run_module(
            "core.isolator",
            [args.repository]
        )

    # EXECUTION HISTORY
    elif args.command == "history":

        manager = RunHistoryManager()

        records = manager.list_runs()

        print(json.dumps(records, indent=4))

        print(f"\nTotal recorded executions: {len(records)}")

        return 0

    # DOCKER EXECUTION
    elif args.command == "docker":

        runner = DockerTestRunner(
            repository_path=args.repository,
            image=args.image,
            timeout=args.timeout
        )

        result = runner.run(test_path=args.test)

        print("\n========== FLAKEHUNTER DOCKER EXECUTION ==========")

        print(json.dumps(result, indent=4))

        if result["success"]:
            print("\nDocker test execution completed successfully!")
            return 0

        print("\nDocker test execution failed.")
        return 1

    # FAILURE REPRODUCTION
    elif args.command == "reproduce":

        reproducer = FailureReproducer(
            repository_path=args.repository,
            timeout=args.timeout
        )

        result = reproducer.reproduce(
            test_path=args.test,
            test_name=args.test_name,
            attempts=args.attempts,
            seed=args.seed
        )

        print("\n========== FLAKEHUNTER FAILURE REPRODUCTION ==========")

        print(json.dumps(result, indent=4))

        print("\nReproduction report generated:")
        print(result["report_path"])

        return 0


if __name__ == "__main__":
    sys.exit(main())