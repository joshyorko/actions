"""Contract tests for complete native provenance tar archives."""

from __future__ import annotations

import json
import os
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import archive_native_artifact_provenance as archive_writer
import write_native_artifact_manifest as manifest_writer


class NativeArtifactProvenanceArchiveTests(unittest.TestCase):
    def _fixture(self, directory: str):
        package = Path(directory) / "action_server"
        frozen = package / "dist/action-server"
        wrapper = package / "dist/final/action-server"
        assets = package / "go-wrapper/assets/assets.zip"
        (frozen / ".dylibs").mkdir(parents=True)
        wrapper.parent.mkdir(parents=True)
        assets.parent.mkdir(parents=True)
        executable = frozen / "action-server"
        executable.write_bytes(b"frozen executable")
        executable.chmod(0o755)
        (frozen / ".hidden-config").write_bytes(b"hidden input")
        (frozen / ".dylibs/libcompat.dylib").write_bytes(b"library bytes")
        wrapper.write_bytes(b"wrapper executable")
        assets.write_bytes(b"embedded assets")
        for path, content in {
            "go-wrapper/main.go": b"package main\n",
            "go-wrapper/process.go": b"package main\nfunc runChild() {}\n",
            "go-wrapper/go.mod": b"module fixture\n",
            "go-wrapper/go.sum": b"fixture checksum\n",
        }.items():
            source = package / path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(content)
        link = frozen / ".dylibs/libcompat-alias.dylib"
        symlink_supported = True
        try:
            link.symlink_to("libcompat.dylib")
        except (NotImplementedError, OSError):
            if os.name != "nt":
                raise
            symlink_supported = False
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
            mock.patch.object(manifest_writer.platform, "system", return_value="Linux"),
        ):
            manifest_writer.write_manifest(
                package,
                source_sha="a" * 40,
                workflow_run_id="123456",
                workflow_run_attempt="1",
                runner_os="ubuntu-22.04",
                build_command="build-executable --go-wrapper",
                output=output,
            )
        return (
            package,
            frozen,
            output,
            output.parent / "native-artifact-tree-inventory.json",
            symlink_supported,
        )

    @staticmethod
    def _reseal(package: Path, frozen: Path, manifest_path: Path, inventory_path: Path):
        inventory = manifest_writer.packaged_tree_inventory(frozen)
        inventory_path.write_text(json.dumps(inventory, indent=2) + "\n")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        file_digest = manifest_writer.packaged_files_sha256(frozen)
        tree_digest = manifest_writer.packaged_tree_sha256(frozen)
        for artifact in manifest["artifacts"].values():
            artifact["embedded_files_sha256"] = file_digest
            artifact["frozen_package_tree_sha256"] = tree_digest
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    def test_round_trip_preserves_dotfiles_modes_symlinks_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, symlink_supported = self._fixture(
                directory
            )
            directory_link_supported = True
            try:
                (frozen / "dylibs-alias").symlink_to(
                    ".dylibs", target_is_directory=True
                )
            except (NotImplementedError, OSError):
                if os.name != "nt":
                    raise
                directory_link_supported = False
            if directory_link_supported:
                self._reseal(package, frozen, manifest, inventory)
            first_archive = package / "output/native-artifact-provenance.tar"
            second_archive = package / "output/native-artifact-provenance-second.tar"
            archive_writer.create_archive(frozen, manifest, inventory, first_archive)
            archive_writer.create_archive(frozen, manifest, inventory, second_archive)
            self.assertEqual(first_archive.read_bytes(), second_archive.read_bytes())
            with tarfile.open(first_archive, "r:") as archive:
                names = {member.name for member in archive.getmembers()}
                self.assertIn("dist/action-server/.hidden-config", names)
                self.assertIn("dist/action-server/.dylibs/libcompat.dylib", names)
                self.assertIn("output/native-artifact-manifest.json", names)
                self.assertIn("output/native-artifact-tree-inventory.json", names)
                executable_member = archive.getmember(
                    "dist/action-server/action-server"
                )
                self.assertEqual(
                    executable_member.mode,
                    stat.S_IMODE((frozen / "action-server").lstat().st_mode),
                )
                if symlink_supported:
                    link_member = archive.getmember(
                        "dist/action-server/.dylibs/libcompat-alias.dylib"
                    )
                    self.assertTrue(link_member.issym())
                    self.assertEqual(link_member.linkname, "libcompat.dylib")
                if directory_link_supported:
                    directory_link_member = archive.getmember(
                        "dist/action-server/dylibs-alias"
                    )
                    self.assertTrue(directory_link_member.issym())
                    self.assertEqual(directory_link_member.linkname, ".dylibs")
                with tempfile.TemporaryDirectory() as extracted:
                    archive.extractall(extracted, filter="data")
                    extracted_tree = Path(extracted) / "dist/action-server"
                    self.assertEqual(
                        manifest_writer.packaged_tree_inventory(extracted_tree),
                        json.loads(inventory.read_text(encoding="utf-8")),
                    )
                    self.assertEqual(
                        manifest_writer.packaged_tree_sha256(extracted_tree),
                        json.loads(manifest.read_text(encoding="utf-8"))["artifacts"][
                            "frozen"
                        ]["frozen_package_tree_sha256"],
                    )
                    self.assertEqual(
                        manifest_writer.packaged_files_sha256(extracted_tree),
                        json.loads(manifest.read_text(encoding="utf-8"))["artifacts"][
                            "frozen"
                        ]["embedded_files_sha256"],
                    )
                    self.assertEqual(
                        (
                            Path(extracted) / "output/native-artifact-manifest.json"
                        ).read_bytes(),
                        manifest.read_bytes(),
                    )
                    self.assertEqual(
                        (
                            Path(extracted)
                            / "output/native-artifact-tree-inventory.json"
                        ).read_bytes(),
                        inventory.read_bytes(),
                    )

    def test_rejects_post_manifest_tree_drift_without_creating_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, _ = self._fixture(directory)
            (frozen / ".hidden-config").write_bytes(b"changed after measurement")
            output = package / "output/native-artifact-provenance.tar"
            with self.assertRaisesRegex(ValueError, "inventory does not match"):
                archive_writer.create_archive(frozen, manifest, inventory, output)
            self.assertFalse(output.exists())

    def test_rejects_inventory_metadata_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, _ = self._fixture(directory)
            inventory.write_text("[]\n", encoding="utf-8")
            output = package / "output/native-artifact-provenance.tar"
            with self.assertRaisesRegex(ValueError, "inventory does not match"):
                archive_writer.create_archive(frozen, manifest, inventory, output)
            self.assertFalse(output.exists())

    @unittest.skipIf(os.name == "nt", "symlink creation may require Windows privilege")
    def test_rejects_escaping_directory_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, _ = self._fixture(directory)
            outside = Path(directory) / "outside"
            outside.mkdir()
            (frozen / "escape-dir").symlink_to(outside, target_is_directory=True)
            self._reseal(package, frozen, manifest, inventory)
            output = package / "output/native-artifact-provenance.tar"
            with self.assertRaisesRegex(ValueError, "symlink target"):
                archive_writer.create_archive(frozen, manifest, inventory, output)
            self.assertFalse(output.exists())

    @unittest.skipIf(os.name == "nt", "symlink creation may require Windows privilege")
    def test_rejects_dangling_traversal_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, _ = self._fixture(directory)
            (frozen / "dangling").symlink_to("../../../missing")
            self._reseal(package, frozen, manifest, inventory)
            output = package / "output/native-artifact-provenance.tar"
            with self.assertRaisesRegex(ValueError, "symlink target"):
                archive_writer.create_archive(frozen, manifest, inventory, output)
            self.assertFalse(output.exists())

    @unittest.skipIf(os.name == "nt", "symlink creation may require Windows privilege")
    def test_rejects_absolute_internal_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, _ = self._fixture(directory)
            target = frozen / ".hidden-config"
            (frozen / "absolute-link").symlink_to(target)
            self._reseal(package, frozen, manifest, inventory)
            output = package / "output/native-artifact-provenance.tar"
            with self.assertRaisesRegex(ValueError, "must be relative"):
                archive_writer.create_archive(frozen, manifest, inventory, output)
            self.assertFalse(output.exists())

    def test_rejects_noncanonical_executable_locator_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest_path, inventory, _ = self._fixture(directory)
            outside = Path(directory) / "outside" / "payload"
            outside.parent.mkdir()
            outside.write_bytes(b"payload matching claimed hash")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"]["frozen"][
                "path"
            ] = "dist/action-server/../../outside/payload"
            manifest["artifacts"]["frozen"]["sha256"] = manifest_writer.sha256(outside)
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
            output = package / "output/native-artifact-provenance.tar"
            with self.assertRaisesRegex(ValueError, "executable locator"):
                archive_writer.create_archive(frozen, manifest_path, inventory, output)
            self.assertFalse(output.exists())

    def test_rejects_metadata_drift_during_archive_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, _ = self._fixture(directory)
            output = package / "output/native-artifact-provenance.tar"
            original_tar_info = archive_writer._tar_info
            mutated = False

            def mutate_after_snapshot(source, archive_path):
                nonlocal mutated
                info = original_tar_info(source, archive_path)
                if not mutated:
                    changed_manifest = json.loads(manifest.read_text(encoding="utf-8"))
                    changed_manifest["source_sha"] = (
                        "b" + changed_manifest["source_sha"][1:]
                    )
                    manifest.write_text(
                        json.dumps(changed_manifest, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    mutated = True
                return info

            with mock.patch.object(
                archive_writer, "_tar_info", side_effect=mutate_after_snapshot
            ):
                with self.assertRaisesRegex(ValueError, "metadata changed"):
                    archive_writer.create_archive(frozen, manifest, inventory, output)
            self.assertFalse(output.exists())

    @unittest.skipIf(os.name == "nt", "POSIX special mode bits are not portable")
    def test_archive_preserves_all_inventory_mode_bits(self):
        with tempfile.TemporaryDirectory() as directory:
            package, frozen, manifest, inventory, _ = self._fixture(directory)
            executable = frozen / "action-server"
            executable.chmod(0o4751)
            self._reseal(package, frozen, manifest, inventory)
            output = package / "output/native-artifact-provenance.tar"
            archive_writer.create_archive(frozen, manifest, inventory, output)
            with tarfile.open(output, "r:") as archive:
                member = archive.getmember("dist/action-server/action-server")
                self.assertEqual(member.mode, stat.S_IMODE(executable.lstat().st_mode))
            _, entries, manifest_bytes, inventory_bytes = archive_writer._measure(
                frozen, manifest, inventory
            )
            changed = package / "output/native-artifact-provenance-changed.tar"
            with tarfile.open(output, "r:") as old, tarfile.open(
                changed, "w", format=tarfile.PAX_FORMAT
            ) as new:
                for member in old.getmembers():
                    if member.name == "dist/action-server/action-server":
                        member.mode = 0o755
                    stream = old.extractfile(member) if member.isfile() else None
                    new.addfile(member, stream)
                    if stream is not None:
                        stream.close()
            with self.assertRaisesRegex(ValueError, "archive mode does not match"):
                archive_writer._verify_tar(
                    changed,
                    frozen,
                    manifest,
                    inventory,
                    entries,
                    manifest_bytes,
                    inventory_bytes,
                )


if __name__ == "__main__":
    unittest.main()
