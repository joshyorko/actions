import json
import os
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
DEVCONTAINER_ROOT = REPOSITORY_ROOT / ".devcontainer"


class DevContainerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configuration = json.loads(
            (DEVCONTAINER_ROOT / "devcontainer.json").read_text()
        )
        dockerfile = DEVCONTAINER_ROOT / "Dockerfile"
        cls.dockerfile = dockerfile.read_text() if dockerfile.exists() else ""

    def test_static_devcontainer_contract(self):
        self.assertEqual(self.configuration.get("build", {}).get("dockerfile"), "Dockerfile")
        self.assertEqual(self.configuration.get("remoteUser"), "vscode")
        self.assertEqual(
            self.configuration.get("postCreateCommand"), ".devcontainer/bin/bootstrap"
        )

        mounts = self.configuration.get("mounts", [])
        self.assertIn(
            "source=actions-uv-cache,target=/home/vscode/.cache/uv,type=volume",
            mounts,
        )
        self.assertIn(
            "source=actions-poetry-cache,target=/home/vscode/.cache/pypoetry,type=volume",
            mounts,
        )

        for digest in (
            "sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7",
            "sha256:752ea8a2f758c34002a0461bd9f1cee4f9a3c36d48494586f60ffce1fc708e0e",
            "sha256:cf4eedcaa81655197f625739489effcbe71b61ceb1506f332c3facae5deceded",
        ):
            self.assertIn(digest, self.dockerfile)
        self.assertIn("POETRY_VERSION=2.1.1", self.dockerfile)
        for cache_environment in (
            "UV_CACHE_DIR=/home/vscode/.cache/uv",
            "POETRY_CACHE_DIR=/home/vscode/.cache/pypoetry",
            "npm_config_cache=/home/vscode/.npm",
        ):
            self.assertIn(cache_environment, self.dockerfile)
        self.assertIn("mkdir -p /home/vscode/.cache/uv /home/vscode/.cache/pypoetry /home/vscode/.npm", self.dockerfile)
        self.assertIn("chown -R vscode:vscode /home/vscode/.cache /home/vscode/.npm", self.dockerfile)

        forbidden = ("ror", "room-of-requirement", "docker-in-docker", "docker-outside-of-docker")
        configuration_text = (DEVCONTAINER_ROOT / "devcontainer.json").read_text().lower()
        dockerfile_text = self.dockerfile.lower()
        for value in forbidden:
            self.assertNotIn(value, configuration_text)
            self.assertNotIn(value, dockerfile_text)

    def test_work_items_poetry_release_gate_contract(self):
        for script_name in ("bootstrap", "verify-work-items"):
            script = DEVCONTAINER_ROOT / "bin" / script_name
            self.assertTrue(script.is_file(), f"missing {script}")
            self.assertTrue(os.access(script, os.X_OK), f"{script} is not executable")

            script_text = script.read_text()
            self.assertIn("set -Eeuo pipefail", script_text)
            self.assertIn('${BASH_SOURCE[0]}', script_text)
            self.assertNotIn("uv sync", script_text)

        verification = (DEVCONTAINER_ROOT / "bin" / "verify-work-items").read_text()
        bootstrap = (DEVCONTAINER_ROOT / "bin" / "bootstrap").read_text()
        self.assertIn("poetry sync --no-interaction", bootstrap)
        self.assertNotIn("poetry install --sync", bootstrap)
        for command in (
            "poetry check --lock",
            "ruff check src tests",
            "pytest tests",
            "poetry build",
            "actions.work_items",
            "actions.workitems",
            "actions_work_items",
            "git diff --check",
        ):
            self.assertIn(command, verification)

        self.assertTrue((REPOSITORY_ROOT / "work-items" / "poetry.lock").is_file())
        action_server_lock = (REPOSITORY_ROOT / "action_server" / "poetry.lock").read_text()
        self.assertIn('name = "actions-work-items"\nversion = "0.2.4"', action_server_lock)


if __name__ == "__main__":
    unittest.main()
