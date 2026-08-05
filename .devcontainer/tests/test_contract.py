import json
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

        forbidden = ("ror", "room-of-requirement", "docker-in-docker", "docker-outside-of-docker")
        configuration_text = (DEVCONTAINER_ROOT / "devcontainer.json").read_text().lower()
        dockerfile_text = self.dockerfile.lower()
        for value in forbidden:
            self.assertNotIn(value, configuration_text)
            self.assertNotIn(value, dockerfile_text)


if __name__ == "__main__":
    unittest.main()
