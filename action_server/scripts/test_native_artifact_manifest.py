"""Contract tests for the credential-free native artifact manifest."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import write_native_artifact_manifest as manifest_writer


class NativeArtifactManifestTests(unittest.TestCase):
    def test_records_actual_binary_hashes_and_measured_platform_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "action_server"
            frozen = package / "dist/action-server/action-server"
            wrapper = package / "dist/final/action-server"
            frozen.parent.mkdir(parents=True)
            wrapper.parent.mkdir(parents=True)
            frozen.write_bytes(b"frozen executable bytes")
            wrapper.write_bytes(b"Go wrapper executable bytes")
            output = package / "output/native-artifact-manifest.json"
            with mock.patch.object(
                manifest_writer.subprocess,
                "run",
                side_effect=[
                    mock.Mock(stdout="a" * 40 + "\n"),
                    mock.Mock(stdout="go version go1.23.0 linux/amd64\n"),
                ],
            ):
                result = manifest_writer.write_manifest(
                    package,
                    source_sha="a" * 40,
                    workflow_run_id="123456",
                    workflow_run_attempt="2",
                    runner_os="ubuntu-22.04",
                    build_command="build-executable --go-wrapper",
                    output=output,
                )
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved, result)
            self.assertEqual(
                result["artifacts"]["frozen"]["sha256"],
                manifest_writer.sha256(frozen),
            )
            self.assertEqual(
                result["artifacts"]["go-wrapper"]["sha256"],
                manifest_writer.sha256(wrapper),
            )
            self.assertEqual(result["source_sha"], "a" * 40)
            self.assertEqual(
                result["python_version"], manifest_writer.platform.python_version()
            )
            self.assertEqual(result["go_version"], "go version go1.23.0 linux/amd64")
            self.assertEqual(
                result["artifact_downloads"]["go-wrapper"]["artifact_name"],
                "action-server-unauthenticated-ubuntu-22.04",
            )
            self.assertEqual(
                result["artifact_downloads"]["go-wrapper"]["archive_path"],
                "action-server",
            )
            self.assertEqual(
                result["artifact_downloads"]["frozen"]["archive_path"],
                "dist/action-server/action-server",
            )
            self.assertEqual(
                result["artifact_downloads"]["manifest"]["archive_path"],
                "output/native-artifact-manifest.json",
            )
            self.assertIn("no candidate Core wheel", result["provenance_scope"])

    def test_rejects_unverified_source_sha_and_missing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "action_server"
            package.mkdir()
            with self.assertRaisesRegex(ValueError, "full lowercase commit SHA"):
                manifest_writer.write_manifest(
                    package,
                    source_sha="not-a-sha",
                    workflow_run_id="1",
                    workflow_run_attempt="1",
                    runner_os="ubuntu-22.04",
                    build_command="build",
                    output=package / "manifest.json",
                )
            with mock.patch.object(
                manifest_writer.subprocess,
                "run",
                return_value=mock.Mock(stdout="b" * 40 + "\n"),
            ):
                with self.assertRaisesRegex(ValueError, "does not match workflow SHA"):
                    manifest_writer.write_manifest(
                        package,
                        source_sha="a" * 40,
                        workflow_run_id="1",
                        workflow_run_attempt="1",
                        runner_os="ubuntu-22.04",
                        build_command="build",
                        output=package / "manifest.json",
                    )
            with mock.patch.object(
                manifest_writer.subprocess,
                "run",
                side_effect=[
                    mock.Mock(stdout="a" * 40 + "\n"),
                    mock.Mock(stdout="go version"),
                ],
            ):
                with self.assertRaisesRegex(
                    FileNotFoundError, "frozen executable missing"
                ):
                    manifest_writer.write_manifest(
                        package,
                        source_sha="a" * 40,
                        workflow_run_id="1",
                        workflow_run_attempt="1",
                        runner_os="ubuntu-22.04",
                        build_command="build",
                        output=package / "manifest.json",
                    )


if __name__ == "__main__":
    unittest.main()
