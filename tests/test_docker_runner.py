import subprocess
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from core.docker_runner import DockerTestRunner


class TestDockerTestRunner(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = Path(self.temp_dir.name)

        self.runner = DockerTestRunner(
            repository_path=self.repository,
            timeout=60
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("core.docker_runner.subprocess.run")
    def test_successful_execution(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="3 passed",
            stderr=""
        )

        result = self.runner.run()

        self.assertTrue(result["success"])
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["stdout"], "3 passed")
        self.assertFalse(result["timed_out"])

        self.assertEqual(mock_run.call_count, 2)

    @patch("core.docker_runner.subprocess.run")
    def test_failed_execution(self, mock_run):
        mock_run.side_effect = [
            MagicMock(
                returncode=1,
                stdout="1 failed",
                stderr="AssertionError"
            ),
            MagicMock(returncode=0)
        ]

        result = self.runner.run()

        self.assertFalse(result["success"])
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("AssertionError", result["stderr"])

    @patch("core.docker_runner.subprocess.run")
    def test_timeout_handling(self, mock_run):
        mock_run.side_effect = [
            subprocess.TimeoutExpired(
                cmd="docker run",
                timeout=60,
                output="partial output",
                stderr="timeout"
            ),
            MagicMock(returncode=0)
        ]

        result = self.runner.run()

        self.assertTrue(result["timed_out"])
        self.assertFalse(result["success"])

    @patch("core.docker_runner.subprocess.run")
    def test_docker_command_arguments(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="passed",
            stderr=""
        )

        self.runner.run()

        command = mock_run.call_args_list[0][0][0]

        self.assertIn("docker", command)
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("--read-only", command)

        mount_index = command.index("--mount")
        self.assertIn(
            "readonly",
            command[mount_index + 1]
        )

    @patch("core.docker_runner.subprocess.run")
    def test_container_cleanup(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="passed",
            stderr=""
        )

        result = self.runner.run()

        self.assertEqual(mock_run.call_count, 2)

        cleanup_command = mock_run.call_args_list[1][0][0]

        self.assertEqual(cleanup_command[1], "rm")
        self.assertIn("-f", cleanup_command)

    @patch("core.docker_runner.subprocess.run")
    def test_docker_not_found(self, mock_run):
        mock_run.side_effect = [
            FileNotFoundError("Docker not found"),
            MagicMock(returncode=0)
        ]

        result = self.runner.run()

        self.assertFalse(result["success"])
        self.assertIn("Docker executable", result["stderr"])


if __name__ == "__main__":
    unittest.main()