"""Create a self-contained archive bound to the native build manifest."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import posixpath
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from write_native_artifact_manifest import (
    packaged_files_sha256,
    packaged_tree_inventory,
    packaged_tree_sha256,
    sha256,
)

TREE_ARCHIVE_PATH = "dist/action-server"
MANIFEST_ARCHIVE_PATH = "output/native-artifact-manifest.json"
INVENTORY_ARCHIVE_PATH = "output/native-artifact-tree-inventory.json"


def _archive_name(relative_path: str) -> str:
    path = PurePosixPath(relative_path)
    windows_path = PureWindowsPath(relative_path)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or "\\" in relative_path
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("unsafe native provenance member path")
    return path.as_posix()


def _validate_link_target(relative_path: str, link_target: str) -> None:
    posix_target = PurePosixPath(link_target)
    windows_target = PureWindowsPath(link_target)
    if (
        posix_target.is_absolute()
        or windows_target.is_absolute()
        or windows_target.drive
    ):
        raise ValueError("native provenance symlink target must be relative")
    normalized = posixpath.normpath(
        posixpath.join(posixpath.dirname(relative_path), link_target.replace("\\", "/"))
    )
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError("native provenance symlink target escapes frozen package")


def _measure(
    frozen_tree: Path, manifest_path: Path, inventory_path: Path
) -> tuple[dict, list[dict], bytes, bytes]:
    frozen_tree = frozen_tree.resolve(strict=True)
    manifest_path = manifest_path.resolve(strict=True)
    inventory_path = inventory_path.resolve(strict=True)
    try:
        manifest_bytes = manifest_path.read_bytes()
        inventory_bytes = inventory_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        inventory = json.loads(inventory_bytes)
    except (OSError, ValueError) as error:
        raise ValueError(
            "native provenance manifest or inventory is unreadable"
        ) from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("native provenance manifest schema is invalid")
    if not isinstance(inventory, list):
        raise ValueError("native provenance tree inventory is invalid")
    measured = packaged_tree_inventory(frozen_tree)
    if inventory != measured:
        raise ValueError("native provenance tree inventory does not match package")
    file_digest = packaged_files_sha256(frozen_tree)
    tree_digest = packaged_tree_sha256(frozen_tree)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {"frozen", "go-wrapper"}:
        raise ValueError("native provenance artifact inventory is invalid")
    for kind, artifact in artifacts.items():
        if not isinstance(artifact, dict):
            raise ValueError("native provenance artifact record is invalid")
        if artifact.get("embedded_files_sha256") != file_digest:
            raise ValueError("native provenance embedded file digest does not match")
        if artifact.get("frozen_package_tree_sha256") != tree_digest:
            raise ValueError("native provenance package tree digest does not match")
        if artifact.get("frozen_package_tree_inventory_path") != INVENTORY_ARCHIVE_PATH:
            raise ValueError("native provenance inventory locator is invalid")
    frozen_binary_path = artifacts["frozen"].get("path")
    allowed_executables = {
        f"{TREE_ARCHIVE_PATH}/action-server",
        f"{TREE_ARCHIVE_PATH}/action-server.exe",
    }
    if frozen_binary_path not in allowed_executables:
        raise ValueError("native provenance frozen executable locator is invalid")
    frozen_relative = frozen_binary_path.removeprefix(f"{TREE_ARCHIVE_PATH}/")
    frozen_entry = next(
        (entry for entry in measured if entry["path"] == frozen_relative), None
    )
    frozen_binary = frozen_tree / frozen_relative
    if (
        frozen_entry is None
        or frozen_entry["kind"] != "file"
        or not frozen_binary.resolve(strict=True).is_relative_to(frozen_tree)
        or not frozen_binary.is_file()
        or sha256(frozen_binary) != artifacts["frozen"].get("sha256")
    ):
        raise ValueError("native provenance frozen executable digest does not match")
    downloads = manifest.get("artifact_downloads")
    if not isinstance(downloads, dict):
        raise ValueError("native provenance download locators are invalid")
    frozen_download = downloads.get("frozen")
    manifest_download = downloads.get("manifest")
    if (
        not isinstance(frozen_download, dict)
        or frozen_download.get("container_archive_path")
        != "native-artifact-provenance.tar"
        or frozen_download.get("archive_path") != artifacts["frozen"].get("path")
        or frozen_download.get("tree_archive_path") != TREE_ARCHIVE_PATH
        or frozen_download.get("inventory_archive_path") != INVENTORY_ARCHIVE_PATH
    ):
        raise ValueError("native provenance frozen archive locator is invalid")
    if (
        not isinstance(manifest_download, dict)
        or manifest_download.get("container_archive_path")
        != "native-artifact-provenance.tar"
        or manifest_download.get("archive_path") != MANIFEST_ARCHIVE_PATH
        or manifest_download.get("inventory_archive_path") != INVENTORY_ARCHIVE_PATH
    ):
        raise ValueError("native provenance manifest archive locator is invalid")

    root = frozen_tree.resolve()
    for entry in measured:
        if entry["kind"] != "symlink":
            continue
        source = frozen_tree.joinpath(*PurePosixPath(str(entry["path"])).parts)
        _validate_link_target(str(entry["path"]), source.readlink().as_posix())
        try:
            resolved_target = source.resolve(strict=True)
            resolved_target.relative_to(root)
        except (OSError, ValueError, RuntimeError) as error:
            raise ValueError(
                "native provenance symlink target must exist inside the frozen package"
            ) from error
        if entry["content_sha256"] is not None and not resolved_target.is_file():
            raise ValueError("native provenance file symlink target is not a file")
    return manifest, measured, manifest_bytes, inventory_bytes


def _tar_info(source: Path, archive_path: str) -> tarfile.TarInfo:
    metadata = source.lstat()
    info = tarfile.TarInfo(_archive_name(archive_path))
    info.mode = stat.S_IMODE(metadata.st_mode)
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    if stat.S_ISLNK(metadata.st_mode):
        info.type = tarfile.SYMTYPE
        info.linkname = source.readlink().as_posix()
        info.size = 0
    elif stat.S_ISDIR(metadata.st_mode):
        info.type = tarfile.DIRTYPE
        info.size = 0
    elif stat.S_ISREG(metadata.st_mode):
        info.type = tarfile.REGTYPE
        info.size = metadata.st_size
    else:
        raise ValueError("unsupported native provenance filesystem entry")
    return info


def _digest_stream(stream) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _verify_tar(
    archive_path: Path,
    frozen_tree: Path,
    manifest_path: Path,
    inventory_path: Path,
    entries: list[dict],
    manifest_bytes: bytes,
    inventory_bytes: bytes,
) -> None:
    expected_names = {TREE_ARCHIVE_PATH, MANIFEST_ARCHIVE_PATH, INVENTORY_ARCHIVE_PATH}
    expected_names.update(
        f"{TREE_ARCHIVE_PATH}/{_archive_name(str(entry['path']))}" for entry in entries
    )
    try:
        with tarfile.open(archive_path, mode="r:") as archive:
            members = archive.getmembers()
            by_name = {member.name: member for member in members}
            if len(by_name) != len(members) or set(by_name) != expected_names:
                raise ValueError("native provenance archive member set does not match")
            root_info = by_name[TREE_ARCHIVE_PATH]
            if not root_info.isdir():
                raise ValueError("native provenance archive root is not a directory")
            for entry in entries:
                relative = _archive_name(str(entry["path"]))
                member = by_name[f"{TREE_ARCHIVE_PATH}/{relative}"]
                if member.mode != int(entry["mode"]):
                    raise ValueError("native provenance archive mode does not match")
                if entry["kind"] == "directory":
                    if not member.isdir():
                        raise ValueError(
                            "native provenance directory type does not match"
                        )
                elif entry["kind"] == "symlink":
                    if not member.issym() or member.linkname != entry["link_target"]:
                        raise ValueError("native provenance symlink does not match")
                    _validate_link_target(relative, member.linkname)
                    source = frozen_tree.joinpath(*PurePosixPath(relative).parts)
                    try:
                        target = source.resolve(strict=True).relative_to(
                            frozen_tree.resolve()
                        )
                    except (OSError, ValueError, RuntimeError) as error:
                        raise ValueError(
                            "native provenance symlink target must exist inside the frozen package"
                        ) from error
                    if entry["content_sha256"] is not None:
                        target_member = by_name[
                            f"{TREE_ARCHIVE_PATH}/{target.as_posix()}"
                        ]
                        stream = archive.extractfile(target_member)
                        if stream is None:
                            raise ValueError(
                                "native provenance symlink target is absent"
                            )
                        with stream:
                            if _digest_stream(stream) != entry["content_sha256"]:
                                raise ValueError(
                                    "native provenance symlink target bytes do not match"
                                )
                elif entry["kind"] == "file":
                    if not member.isfile():
                        raise ValueError("native provenance file type does not match")
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ValueError("native provenance archived file is absent")
                    with stream:
                        if _digest_stream(stream) != entry["content_sha256"]:
                            raise ValueError(
                                "native provenance archived file bytes do not match"
                            )
                else:
                    raise ValueError("unsupported native provenance inventory kind")
            for name, expected_bytes in (
                (MANIFEST_ARCHIVE_PATH, manifest_bytes),
                (INVENTORY_ARCHIVE_PATH, inventory_bytes),
            ):
                stream = archive.extractfile(by_name[name])
                if stream is None:
                    raise ValueError("native provenance metadata member is absent")
                with stream:
                    if stream.read() != expected_bytes:
                        raise ValueError(
                            "native provenance metadata bytes do not match"
                        )
    except (OSError, tarfile.TarError, KeyError) as error:
        raise ValueError("native provenance archive is invalid") from error


def create_archive(
    frozen_tree: Path, manifest_path: Path, inventory_path: Path, output: Path
) -> Path:
    """Write a deterministic tar containing the exact measured tree and metadata."""
    frozen_tree = frozen_tree.resolve(strict=True)
    manifest_path = manifest_path.resolve(strict=True)
    inventory_path = inventory_path.resolve(strict=True)
    output = output.resolve(strict=False)
    if output.exists():
        raise FileExistsError("native provenance archive output already exists")
    if output.is_relative_to(frozen_tree):
        raise ValueError("native provenance archive cannot be inside frozen package")
    _, entries, manifest_bytes, inventory_bytes = _measure(
        frozen_tree, manifest_path, inventory_path
    )
    members: list[tuple[str, Path]] = [(TREE_ARCHIVE_PATH, frozen_tree)]
    members.extend(
        (
            f"{TREE_ARCHIVE_PATH}/{_archive_name(str(entry['path']))}",
            frozen_tree.joinpath(*PurePosixPath(str(entry["path"])).parts),
        )
        for entry in entries
    )
    members.sort(key=lambda item: item[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".native-artifact-provenance-", suffix=".tar", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with tarfile.open(temporary, mode="w", format=tarfile.PAX_FORMAT) as archive:
            archive.dereference = False
            for archive_name, source in members:
                info = _tar_info(source, archive_name)
                if info.isfile():
                    with source.open("rb") as stream:
                        archive.addfile(info, stream)
                else:
                    archive.addfile(info)
            for name, content in (
                (MANIFEST_ARCHIVE_PATH, manifest_bytes),
                (INVENTORY_ARCHIVE_PATH, inventory_bytes),
            ):
                info = tarfile.TarInfo(name)
                info.mode = 0o644
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
        _verify_tar(
            temporary,
            frozen_tree,
            manifest_path,
            inventory_path,
            entries,
            manifest_bytes,
            inventory_bytes,
        )
        _, after_entries, after_manifest, after_inventory = _measure(
            frozen_tree, manifest_path, inventory_path
        )
        if (
            after_entries != entries
            or after_manifest != manifest_bytes
            or after_inventory != inventory_bytes
        ):
            raise ValueError(
                "frozen package or metadata changed while archiving provenance"
            )
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=package / "output" / "native-artifact-provenance.tar",
    )
    args = parser.parse_args()
    create_archive(
        package / "dist" / "action-server",
        package / "output" / "native-artifact-manifest.json",
        package / "output" / "native-artifact-tree-inventory.json",
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
