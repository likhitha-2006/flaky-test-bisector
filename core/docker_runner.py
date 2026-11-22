import subprocess
import time
import uuid

from pathlib import Path
from datetime import datetime, timezone


class DockerTestRunner:
    """
    Executes pytest inside an isolated Docker container.

    The source repository is mounted read-only.
    """

    def __init__(
        self,
        repository_path,
        image="flakehunter-python:3.11",
        timeout=60,
    ):
        self.repository_path = Path(repository_path).resolve()
        self.image = image
        self.timeout = timeout

        if not self.repository_path.is_dir():
            raise ValueError(
                f"Invalid repository path: {self.repository_path}"
            )

    def run(self, test_path=None):
        run_id = str(uuid.uuid4())
        container_name = f"flakehunter-{run_id[:12]}"

        result = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "repository": str(self.repository_path),
            "image": self.image,
            "timeout": self.timeout,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "duration": 0,
            "success": False,
            "timed_out": False,
            "container_id": None,
        }

        command = [
            "docker",
            "run",
            "--name",
            container_name,
            "--rm",
            "--network",
            "none",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--mount",
            (
                f"type=bind,source={self.repository_path},"
                "target=/workspace,readonly"
            ),
            "-w",
            "/workspace",
            self.image,
            "python",
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            "-q",
            test_path if test_path else ".",
        ]

        start_time = time.monotonic()

        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )

            result["exit_code"] = process.returncode
            result["stdout"] = process.stdout
            result["stderr"] = process.stderr
            result["success"] = process.returncode == 0

        except subprocess.TimeoutExpired as exc:
            result["timed_out"] = True
            result["stdout"] = exc.stdout or ""
            result["stderr"] = exc.stderr or "Execution timed out."

        except FileNotFoundError:
            result["stderr"] = "Docker executable was not found."

        except Exception as exc:
            result["stderr"] = str(exc)

        finally:
            result["duration"] = round(
                time.monotonic() - start_time, 3
            )

            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                text=True,
                check=False,
            )

        return result