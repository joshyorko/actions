import json
import os
import tomllib
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
            "poetry version --short",
            "twine check --strict",
            "zipfile",
            "email.parser",
            "actions.work_items",
            "actions.workitems",
            "actions_work_items",
            "git diff --check",
        ):
            self.assertIn(command, verification)

        self.assertIn("(($# > 1))", verification)
        self.assertIn("usage:", verification)
        self.assertIn("mktemp -d", verification)
        self.assertIn("caller-supplied artifact directory must be empty", verification)
        self.assertIn('artifact_dir_owner="caller"', verification)
        self.assertIn('artifact_dir_owner="temporary"', verification)
        self.assertIn('[[ "$artifact_dir_owner" == "temporary" ]]', verification)
        self.assertLess(
            verification.index("trap cleanup EXIT"),
            verification.index('artifact_dir=$(mktemp -d)'),
        )
        self.assertLess(
            verification.index("trap cleanup EXIT"),
            verification.index('venv_dir=$(mktemp -d)'),
        )
        self.assertIn('venv_dir=""', verification)
        self.assertIn('artifact_dir=""', verification)

        self.assertTrue((REPOSITORY_ROOT / "work-items" / "poetry.lock").is_file())
        action_server_lock = (REPOSITORY_ROOT / "action_server" / "poetry.lock").read_text()
        self.assertIn('name = "actions-work-items"\nversion = "0.3.0"', action_server_lock)

    def test_work_items_pep_621_metadata_contract(self):
        pyproject_path = REPOSITORY_ROOT / "work-items" / "pyproject.toml"
        pyproject = tomllib.loads(pyproject_path.read_text())
        project = pyproject["project"]

        self.assertEqual(project["name"], "actions-work-items")
        self.assertEqual(project["version"], "0.3.0")
        self.assertEqual(project["requires-python"], ">=3.10,<4.0")
        self.assertEqual(
            project["urls"],
            {
                "Homepage": "https://github.com/joshyorko/actions",
                "Repository": "https://github.com/joshyorko/actions",
                "Documentation": "https://github.com/joshyorko/actions/tree/community/work-items",
                "Issues": "https://github.com/joshyorko/actions/issues",
            },
        )
        self.assertEqual(
            project["optional-dependencies"],
            {
                "redis": ["redis>=4.5.0"],
                "docdb": ["pymongo>=4.3.0"],
                "documentdb": ["pymongo>=4.3.0"],
                "all": ["redis>=4.5.0", "pymongo>=4.3.0"],
            },
        )
        self.assertEqual(
            pyproject["tool"]["poetry"]["packages"],
            [
                {"include": "actions", "from": "src"},
                {"include": "actions_work_items", "from": "src"},
            ],
        )
        self.assertIn("twine", pyproject["tool"]["poetry"]["group"]["dev"]["dependencies"])

        init_path = REPOSITORY_ROOT / "work-items" / "src" / "actions" / "work_items" / "__init__.py"
        self.assertIn('__version__ = "0.3.0"', init_path.read_text())

    def test_work_items_pypi_documentation_contract(self):
        readme = (REPOSITORY_ROOT / "work-items" / "README.md").read_text()
        changelog = (REPOSITORY_ROOT / "work-items" / "docs" / "CHANGELOG.md").read_text()

        self.assertIn("## Backend Support", readme)
        for backend in ("SQLite", "FileAdapter", "Redis", "MongoDB / DocumentDB", "Action Server"):
            self.assertIn(backend, readme)
        self.assertIn("| SQLite |", readme)
        self.assertIn("| Redis | Experimental |", readme)
        self.assertIn("| MongoDB / DocumentDB | Experimental |", readme)
        for heading in (
            "## Quick Start",
            "## Safety and Determinism",
            "## Migrating from robocorp-workitems",
        ):
            self.assertIn(heading, readme)
        quick_start = readme[readme.index("## Quick Start") : readme.index("## Payloads")]
        for term in ("seed_input", "reserve", "outputs.create", "item.done()"):
            self.assertIn(term, quick_start)
        self.assertIn("actions_work_items", readme)
        self.assertIn("__version__", readme)
        self.assertIn("workitems.outputs.create(payload=None, files=None, save=True)", readme)
        payload = readme[readme.index("## Payloads") : readme.index("## Files")]
        self.assertNotIn("ExceptionType", payload)
        self.assertTrue(changelog.startswith("# Changelog\n\n## 0.3.0 - 2026-08-05"))

    def test_work_items_release_workflow_contract(self):
        workflow = (
            REPOSITORY_ROOT / ".github" / "workflows" / "work_items_release.yml"
        ).read_text()

        self.assertIn("pull_request:", workflow)
        self.assertIn("branches:\n      - community", workflow)
        self.assertIn('"actions-work-items-*"', workflow)
        self.assertNotIn("workflow_dispatch", workflow)
        self.assertNotIn("id-token", workflow)
        self.assertIn("poetry==2.1.1", workflow)
        self.assertIn('python-version: "3.12"', workflow)
        self.assertNotIn("cache: poetry", workflow)

        for action in (
            "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5",
            "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5",
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4",
            "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093 # v4",
        ):
            self.assertIn(action, workflow)

        self.assertIn("verify-work-items work-items/dist", workflow)
        self.assertIn("name: actions-work-items-dist", workflow)
        self.assertIn("needs: verify", workflow)
        self.assertIn("environment: pypi", workflow)
        self.assertIn(
            "startsWith(github.ref, 'refs/tags/actions-work-items-')", workflow
        )
        self.assertIn("git merge-base --is-ancestor", workflow)
        self.assertIn("origin/community", workflow)
        self.assertIn("check-tag-version", workflow)
        self.assertIn("PYPI_TOKEN_ACTIONS_WORK_ITEMS", workflow)
        self.assertIn("poetry publish --no-interaction", workflow)

        for path in (
            "work-items/**",
            "action_server/poetry.lock",
            ".devcontainer/bin/verify-work-items",
            ".devcontainer/tests/**",
            ".github/workflows/work_items_release.yml",
            "docs/skills/work-items.md",
        ):
            self.assertIn(path, workflow)

    def test_smoke_contract(self):
        smoke = DEVCONTAINER_ROOT / "bin" / "smoke"
        self.assertTrue(smoke.is_file(), f"missing {smoke}")
        self.assertTrue(os.access(smoke, os.X_OK), f"{smoke} is not executable")

        smoke_text = smoke.read_text()
        self.assertIn("set -Eeuo pipefail", smoke_text)
        self.assertIn("id -u", smoke_text)
        self.assertIn("Python 3.12.", smoke_text)
        self.assertIn("v22.", smoke_text)
        self.assertIn("uv 0.12.1", smoke_text)
        self.assertIn("Poetry (version 2.1.1)", smoke_text)
        self.assertIn('"$repo_root/.devcontainer/bin/bootstrap"', smoke_text)
        self.assertIn('"$repo_root/.devcontainer/bin/verify-work-items"', smoke_text)

    def test_host_docker_command_requires_the_repository_root(self):
        guidance = (REPOSITORY_ROOT / "docs/skills/repository-operations.md").read_text()
        work_items_guidance = (REPOSITORY_ROOT / "docs/skills/work-items.md").read_text()
        self.assertIn("Run host Docker commands only from the repository root", guidance)
        self.assertIn("repo_root=$(git rev-parse --show-toplevel)", guidance)
        self.assertIn('cd "$repo_root"', guidance)
        self.assertNotIn(
            "from any directory in the mounted repository", work_items_guidance
        )
        self.assertIn(
            "host-side Docker command; run it from the repository root",
            work_items_guidance,
        )
        self.assertIn("in-container scripts are cwd-independent", work_items_guidance)


if __name__ == "__main__":
    unittest.main()
