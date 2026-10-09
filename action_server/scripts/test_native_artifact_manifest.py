"""Contract tests for the credential-free native artifact manifest."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import write_native_artifact_manifest as manifest_writer


class NativeArtifactManifestTests(unittest.TestCase):
    def test_records_hashes_for_unix_and_windows_suffixes(self):
        for system, suffix in (("Linux", ""), ("Windows", ".exe")):
            with self.subTest(
                system=system
            ), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                package = root / "action_server"
                frozen = package / "dist/action-server" / f"action-server{suffix}"
                wrapper = package / "dist/final" / f"action-server{suffix}"
                frozen.parent.mkdir(parents=True)
                wrapper.parent.mkdir(parents=True)
                frozen.write_bytes(b"frozen executable bytes")
                wrapper.write_bytes(b"Go wrapper executable bytes")
                (package / "dist/action-server/_internal").mkdir(parents=True)
                (package / "dist/action-server/_internal/module.py").write_bytes(
                    b"packaged module"
                )
                (package / "go-wrapper/assets").mkdir(parents=True)
                (package / "go-wrapper/assets/assets.zip").write_bytes(b"assets")
                (package / "go-wrapper/main.go").write_text("package main\n")
                (package / "go-wrapper/go.mod").write_text("module fixture\n")
                (package / "go-wrapper/go.sum").write_text("fixture checksum\n")
                output = package / "output/native-artifact-manifest.json"
                with (
                    mock.patch.object(
                        manifest_writer.subprocess,
                        "run",
                        side_effect=[
                            mock.Mock(stdout="a" * 40 + "\n"),
                            mock.Mock(stdout="go version go1.23.0 linux/amd64\n"),
                        ],
                    ),
                    mock.patch.object(
                        manifest_writer.platform, "system", return_value=system
                    ),
                ):
                    result = manifest_writer.write_manifest(
                        package,
                        source_sha="a" * 40,
                        workflow_run_id="123456",
                        workflow_run_attempt="2",
                        runner_os="windows-2022"
                        if system == "Windows"
                        else "ubuntu-22.04",
                        build_command="build-executable --go-wrapper",
                        output=output,
                    )
                saved = json.loads(output.read_text(encoding="utf-8"))
                tree_inventory_path = package / "output/native-artifact-tree-inventory.json"
                tree_inventory = json.loads(
                    tree_inventory_path.read_text(encoding="utf-8")
                )
                self.assertEqual(saved, result)
                self.assertEqual(
                    result["artifacts"]["frozen"]["sha256"],
                    hashlib.sha256(b"frozen executable bytes").hexdigest(),
                )
                self.assertEqual(
                    result["artifacts"]["go-wrapper"]["sha256"],
                    hashlib.sha256(b"Go wrapper executable bytes").hexdigest(),
                )
                self.assertEqual(result["source_sha"], "a" * 40)
                self.assertEqual(result["platform"], system)
                self.assertEqual(
                    tree_inventory,
                    manifest_writer.packaged_tree_inventory(
                        package / "dist/action-server"
                    ),
                )
                for runtime in ("frozen", "go-wrapper"):
                    artifact = result["artifacts"][runtime]
                    self.assertEqual(
                        artifact["embedded_files_sha256"],
                        manifest_writer.packaged_files_sha256(
                            package / "dist/action-server"
                        ),
                    )
                    self.assertEqual(
                        artifact["assets_zip_sha256"],
                        hashlib.sha256(b"assets").hexdigest(),
                    )
                    self.assertEqual(
                        artifact["wrapper_source_sha256"],
                        manifest_writer.source_files_sha256(
                            package,
                            (
                                "go-wrapper/main.go",
                                "go-wrapper/go.mod",
                                "go-wrapper/go.sum",
                            ),
                        ),
                    )
                    self.assertEqual(
                        artifact["frozen_package_tree_sha256"],
                        manifest_writer.packaged_tree_sha256(
                            package / "dist/action-server"
                        ),
                    )
                self.assertEqual(
                    result["artifacts"]["go-wrapper"]["assets_zip_path"],
                    "go-wrapper/assets/assets.zip",
                )
                self.assertEqual(
                    result["python_version"], manifest_writer.platform.python_version()
                )
                self.assertEqual(
                    result["go_version"], "go version go1.23.0 linux/amd64"
                )
                self.assertEqual(
                    result["artifact_downloads"]["go-wrapper"]["artifact_name"],
                    f"action-server-unauthenticated-{'windows-2022' if system == 'Windows' else 'ubuntu-22.04'}",
                )
                self.assertEqual(
                    result["artifact_downloads"]["go-wrapper"]["archive_path"],
                    f"action-server{suffix}",
                )
                self.assertEqual(
                    result["artifact_downloads"]["frozen"]["archive_path"],
                    f"dist/action-server/action-server{suffix}",
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
