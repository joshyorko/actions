import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]


class ServiceOrchestrationTest(unittest.TestCase):
    def _run_host_smoke(self, docker_run_status=0):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            log_path = temporary_path / "docker.log"
            docker = temporary_path / "docker"
            docker.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%q ' \"$@\" >> \"$DOCKER_LOG\"\n"
                "printf '\\n' >> \"$DOCKER_LOG\"\n"
                "if [[ $1 == run ]]; then exit \"$DOCKER_RUN_STATUS\"; fi\n"
            )
            docker.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{temporary_path}:{environment['PATH']}",
                    "DOCKER_LOG": str(log_path),
                    "DOCKER_RUN_STATUS": str(docker_run_status),
                    "ACTIONS_DEVCONTAINER_IMAGE": "example/devcontainer:test",
                }
            )
            result = subprocess.run(
                [REPOSITORY_ROOT / ".devcontainer/bin/smoke-host"],
                cwd="/tmp",
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            return result, log_path.read_text()

    def test_host_smoke_attaches_verifier_to_services_and_cleans_up(self):
        result, docker_log = self._run_host_smoke()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("compose -f", docker_log)
        self.assertIn("up -d --wait", docker_log)
        self.assertIn("run --rm --user vscode", docker_log)
        self.assertIn("--network actions-work-items-persistent-backends_default", docker_log)
        self.assertIn("TEST_REDIS_URL=redis://redis:6379/15", docker_log)
        self.assertIn("TEST_MONGODB_URI=mongodb://mongodb:27017", docker_log)
        self.assertIn("example/devcontainer:test", docker_log)
        self.assertTrue(docker_log.rstrip().endswith("down --volumes --remove-orphans"))

    def test_host_smoke_cleans_up_when_verification_fails(self):
        result, docker_log = self._run_host_smoke(docker_run_status=42)

        self.assertEqual(result.returncode, 42)
        self.assertTrue(docker_log.rstrip().endswith("down --volumes --remove-orphans"))

    def test_in_container_verifier_requires_external_service_endpoints(self):
        environment = os.environ.copy()
        environment.pop("TEST_REDIS_URL", None)
        environment.pop("TEST_MONGODB_URI", None)

        result = subprocess.run(
            [REPOSITORY_ROOT / ".devcontainer/bin/verify-work-items"],
            cwd="/tmp",
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("TEST_REDIS_URL and TEST_MONGODB_URI are required", result.stderr)
        self.assertNotIn("poetry", result.stdout)


if __name__ == "__main__":
    unittest.main()
