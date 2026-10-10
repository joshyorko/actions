"""Validate an explicit native Action Server runtime against its build receipt."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import stat
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

import archive_native_artifact_provenance as provenance
from write_native_artifact_manifest import (
    packaged_tree_inventory,
    packaged_tree_sha256,
    sha256,
)

MAX_NATIVE_TREE_ENTRIES = 100_000
MAX_NATIVE_FILE_BYTES = 2 * 1024**3
MAX_NATIVE_TOTAL_BYTES = 8 * 1024**3
MAX_NATIVE_MANIFEST_BYTES = 4 * 1024**2
MAX_NATIVE_INVENTORY_BYTES = 64 * 1024**2
MAX_NATIVE_PROVENANCE_BYTES = 2 * 1024**3
MAX_NATIVE_ASSETS_ZIP_BYTES = 8 * 1024**3


def _check_bounded_tree(root: Path) -> None:
    count = 0
    total_bytes = 0
    for path in root.rglob("*"):
        count += 1
        if count > MAX_NATIVE_TREE_ENTRIES:
            raise ValueError("native package exceeds the entry-count limit")
        metadata = path.lstat()
        if stat.S_ISREG(metadata.st_mode):
            size = metadata.st_size
        elif stat.S_ISLNK(metadata.st_mode):
            try:
                target = path.resolve(strict=True)
            except (OSError, RuntimeError) as error:
                raise ValueError("native package symlink target is invalid") from error
            size = target.stat().st_size if target.is_file() else 0
        elif stat.S_ISDIR(metadata.st_mode):
            size = 0
        else:
            raise ValueError("native package contains an unsupported filesystem entry")
        if size > MAX_NATIVE_FILE_BYTES:
            raise ValueError("native package file exceeds the per-file size limit")
        total_bytes += size
        if total_bytes > MAX_NATIVE_TOTAL_BYTES:
            raise ValueError("native package exceeds the aggregate size limit")


def _check_tar_member_limit(path: Path) -> None:
    if path.stat().st_size > MAX_NATIVE_PROVENANCE_BYTES:
        raise ValueError("native provenance archive exceeds the size limit")
    try:
        with tarfile.open(path, "r:*") as archive:
            declared_bytes = 0
            for count, member in enumerate(archive, start=1):
                if count > MAX_NATIVE_TREE_ENTRIES + 2:
                    raise ValueError(
                        "native provenance archive exceeds the member limit"
                    )
                if member.size < 0 or member.size > MAX_NATIVE_FILE_BYTES:
                    raise ValueError(
                        "native provenance member exceeds the per-file size limit"
                    )
                declared_bytes += member.size
                if declared_bytes > MAX_NATIVE_TOTAL_BYTES:
                    raise ValueError(
                        "native provenance exceeds the aggregate size limit"
                    )
    except (OSError, tarfile.TarError) as error:
        raise ValueError("native provenance archive is invalid") from error


@dataclass(frozen=True)
class ValidatedNativeArtifact:
    selector_path: Path
    inventory_path: Path
    receipt: dict[str, object]


def _git_tree(source_sha: str, repository: Path) -> str:
    if len(source_sha) != 40 or any(
        char not in "0123456789abcdef" for char in source_sha
    ):
        raise ValueError("native build source SHA is invalid")
    try:
        result = subprocess.run(
            ["git", "rev-parse", f"{source_sha}^{{tree}}"],
            cwd=repository,
            capture_output=True,
            check=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("native build source tree is unavailable") from error
    tree = result.stdout.strip()
    if len(tree) != 40 or any(char not in "0123456789abcdef" for char in tree):
        raise ValueError("native build source tree is invalid")
    return tree


def validate_native_artifact(
    kind: str,
    package_root: Path,
    manifest_path: Path,
    inventory_path: Path,
    provenance_path: Path,
    *,
    assets_zip_path: Path | None = None,
    repository: Path | None = None,
) -> ValidatedNativeArtifact:
    """Bind one explicitly selected executable to manifest and full-tree evidence."""
    if kind not in {"frozen", "go-wrapper"}:
        raise ValueError("native artifact kind is unsupported")
    package_root = package_root.resolve(strict=True)
    manifest_path = manifest_path.resolve(strict=True)
    inventory_path = inventory_path.resolve(strict=True)
    provenance_path = provenance_path.resolve(strict=True)
    frozen_tree = (package_root / "dist" / "action-server").resolve(strict=True)
    if not frozen_tree.is_relative_to(package_root) or not frozen_tree.is_dir():
        raise ValueError("native frozen package root escapes selected bundle")
    for path, limit, label in (
        (manifest_path, MAX_NATIVE_MANIFEST_BYTES, "manifest"),
        (inventory_path, MAX_NATIVE_INVENTORY_BYTES, "inventory"),
    ):
        if path.stat().st_size > limit:
            raise ValueError(f"native provenance {label} exceeds the size limit")
    _check_bounded_tree(frozen_tree)
    _check_tar_member_limit(provenance_path)
    manifest, entries, manifest_bytes, inventory_bytes = provenance._measure(
        frozen_tree, manifest_path, inventory_path
    )
    provenance._verify_tar(
        provenance_path,
        frozen_tree,
        manifest_path,
        inventory_path,
        entries,
        manifest_bytes,
        inventory_bytes,
    )
    if manifest.get("platform") != platform.system():
        raise ValueError("native build platform does not match this host")
    if manifest.get("architecture") != platform.machine():
        raise ValueError("native build architecture does not match this host")
    run_id = manifest.get("workflow_run_id")
    attempt = manifest.get("workflow_run_attempt")
    if not isinstance(run_id, str) or not run_id.isdigit():
        raise ValueError("native build workflow run identity is invalid")
    if not isinstance(attempt, str) or not attempt.isdigit() or int(attempt) < 1:
        raise ValueError("native build workflow attempt identity is invalid")
    source_sha = manifest.get("source_sha")
    if not isinstance(source_sha, str):
        raise ValueError("native build source SHA is invalid")
    repo = (repository or Path(__file__).resolve().parents[2]).resolve(strict=True)
    source_tree = _git_tree(source_sha, repo)
    suffix = ".exe" if platform.system() == "Windows" else ""
    expected_paths = {
        "frozen": f"dist/action-server/action-server{suffix}",
        "go-wrapper": f"dist/final/action-server{suffix}",
    }
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(expected_paths):
        raise ValueError("native build artifact records are invalid")
    for artifact_kind, expected_path in expected_paths.items():
        record = artifacts.get(artifact_kind)
        if not isinstance(record, dict) or record.get("path") != expected_path:
            raise ValueError("native build artifact path inventory is invalid")
        executable = package_root / expected_path
        try:
            metadata = executable.lstat()
        except OSError as error:
            raise ValueError("native build executable is missing") from error
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("native build executable must be a regular file")
        if sha256(executable) != record.get("sha256"):
            raise ValueError("native build executable hash does not match manifest")
        if record.get("assets_zip_path") != "go-wrapper/assets/assets.zip":
            raise ValueError("native build assets archive locator is invalid")
        if record.get("assets_zip_sha256") != artifacts["frozen"].get(
            "assets_zip_sha256"
        ):
            raise ValueError("native build assets archive identities do not match")
    selected = artifacts.get(kind)
    if not isinstance(selected, dict) or selected.get("path") != expected_paths[kind]:
        raise ValueError("native selected artifact path does not match manifest")
    selected_path = (package_root / expected_paths[kind]).resolve(strict=True)
    if not selected_path.is_relative_to(package_root) or not selected_path.is_file():
        raise ValueError("native selected artifact escapes bundle")
    if sha256(selected_path) != selected.get("sha256"):
        raise ValueError("native selected executable hash does not match manifest")

    assets_sha = selected.get("assets_zip_sha256")
    if not isinstance(assets_sha, str) or len(assets_sha) != 64:
        raise ValueError("native embedded asset archive digest is invalid")
    if kind == "go-wrapper":
        if assets_zip_path is None:
            raise ValueError("Go-wrapper mode requires its measured assets archive")
        assets_zip_path = assets_zip_path.resolve(strict=True)
        if assets_zip_path.stat().st_size > MAX_NATIVE_ASSETS_ZIP_BYTES:
            raise ValueError("Go-wrapper assets archive exceeds the size limit")
        if sha256(assets_zip_path) != assets_sha:
            raise ValueError("Go-wrapper assets archive hash does not match manifest")
        try:
            with zipfile.ZipFile(assets_zip_path) as assets:
                expected_files = {
                    str(entry["path"]): str(entry["content_sha256"])
                    for entry in entries
                    if entry["kind"] == "file"
                    or (entry["kind"] == "symlink" and entry["content_sha256"])
                }
                observed_files = {}
                members = assets.infolist()
                if len(members) > MAX_NATIVE_TREE_ENTRIES:
                    raise ValueError(
                        "Go-wrapper assets archive exceeds the member limit"
                    )
                total_uncompressed = 0
                total_read = 0
                for member in members:
                    if (
                        member.file_size > MAX_NATIVE_FILE_BYTES
                        or member.file_size < 0
                        or member.compress_size < 0
                    ):
                        raise ValueError(
                            "Go-wrapper assets archive member exceeds size limits"
                        )
                    total_uncompressed += member.file_size
                    if total_uncompressed > MAX_NATIVE_TOTAL_BYTES:
                        raise ValueError(
                            "Go-wrapper assets archive exceeds aggregate size limit"
                        )
                    path = PurePosixPath(member.filename)
                    windows_path = PureWindowsPath(member.filename)
                    if (
                        member.is_dir()
                        or path.is_absolute()
                        or windows_path.is_absolute()
                        or windows_path.drive
                        or "\\" in member.filename
                        or "\x00" in member.filename
                        or member.filename != path.as_posix()
                        or any(part in {"", ".", ".."} for part in path.parts)
                        or member.filename in observed_files
                    ):
                        raise ValueError(
                            "Go-wrapper assets archive member path is invalid"
                        )
                    digest = hashlib.sha256()
                    member_read = 0
                    try:
                        with assets.open(member, "r") as stream:
                            while chunk := stream.read(1024 * 1024):
                                member_read += len(chunk)
                                total_read += len(chunk)
                                if (
                                    member_read > MAX_NATIVE_FILE_BYTES
                                    or total_read > MAX_NATIVE_TOTAL_BYTES
                                ):
                                    raise ValueError(
                                        "Go-wrapper assets archive exceeds observed size limits"
                                    )
                                digest.update(chunk)
                    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
                        raise ValueError(
                            "Go-wrapper assets archive member is corrupt"
                        ) from error
                    observed_files[path.as_posix()] = digest.hexdigest()
                if observed_files != expected_files:
                    raise ValueError(
                        "Go-wrapper assets archive files do not match inventory"
                    )
        except (OSError, zipfile.BadZipFile) as error:
            raise ValueError("Go-wrapper assets archive is invalid") from error
    elif (
        assets_zip_path is not None
        and sha256(assets_zip_path.resolve(strict=True)) != assets_sha
    ):
        raise ValueError("native assets archive hash does not match manifest")

    return ValidatedNativeArtifact(
        selector_path=selected_path,
        inventory_path=inventory_path,
        receipt={
            "selected_kind": kind,
            "selected_path": expected_paths[kind],
            "selected_executable_sha256": selected["sha256"],
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "inventory_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
            "provenance_sha256": sha256(provenance_path),
            "package_tree_sha256": packaged_tree_sha256(frozen_tree),
            "embedded_files_sha256": selected["embedded_files_sha256"],
            "assets_zip_sha256": assets_sha,
            "build_source_sha": source_sha,
            "build_source_tree": source_tree,
            "workflow_run_id": run_id,
            "workflow_run_attempt": attempt,
            "platform": manifest["platform"],
            "architecture": manifest["architecture"],
        },
    )


def validate_go_extraction(
    home: Path,
    inventory_path: Path,
    *,
    embedded_files_sha256: str,
    assets_zip_sha256: str,
) -> dict[str, object]:
    """Require the wrapper's extracted tree to equal the measured frozen package."""
    internal_root = home.resolve(strict=True) / ".actions/bin/action-server/internal"
    if not internal_root.is_dir() or internal_root.is_symlink():
        raise ValueError("Go-wrapper extracted package root is missing or linked")
    versions = [path for path in internal_root.iterdir() if path.is_dir()]
    if len(versions) != 1 or versions[0].is_symlink():
        raise ValueError("Go-wrapper extracted package version is ambiguous")
    extracted = versions[0].resolve(strict=True)
    if not extracted.is_relative_to(internal_root.resolve(strict=True)):
        raise ValueError("Go-wrapper extracted package escapes its task-owned home")
    if inventory_path.stat().st_size > MAX_NATIVE_INVENTORY_BYTES:
        raise ValueError("native package inventory exceeds the size limit")
    _check_bounded_tree(extracted)
    app_hash = extracted / "app_hash"
    if (
        not app_hash.is_file()
        or app_hash.read_text(encoding="utf-8").strip() != assets_zip_sha256
    ):
        raise ValueError("Go-wrapper extracted archive identity does not match")
    try:
        expected = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("native package inventory is unreadable") from error
    expected_files = {
        str(item["path"]): str(item["content_sha256"])
        for item in expected
        if item["kind"] == "file"
        or (item["kind"] == "symlink" and item["content_sha256"])
    }
    observed_files: dict[str, str] = {}
    observed_directories = set()
    for path in extracted.rglob("*"):
        relative = path.relative_to(extracted).as_posix()
        if relative in {"app_hash", "extract.lock", "lastLaunchTouch"}:
            continue
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("Go-wrapper extracted package contains a symlink")
        if stat.S_ISREG(metadata.st_mode):
            observed_files[relative] = sha256(path)
        elif stat.S_ISDIR(metadata.st_mode):
            observed_directories.add(relative)
        else:
            raise ValueError(
                "Go-wrapper extracted package contains an unsupported entry"
            )
    if observed_files != expected_files:
        raise ValueError("Go-wrapper extracted package inventory does not match")
    expected_directories = {
        parent.as_posix()
        for relative in expected_files
        for parent in PurePosixPath(relative).parents
        if parent.as_posix() != "."
    }
    if observed_directories != expected_directories:
        raise ValueError(
            "Go-wrapper extracted package directory inventory does not match"
        )
    observed = packaged_tree_inventory(extracted)
    observed = [
        item
        for item in observed
        if item["path"] not in {"app_hash", "extract.lock", "lastLaunchTouch"}
    ]
    digest = hashlib.sha256()
    for item in observed:
        mode = item["mode"]
        if not isinstance(mode, int):
            raise ValueError("Go-wrapper extracted package mode is invalid")
        relative_bytes = str(item["path"]).encode("utf-8")
        digest.update(relative_bytes + b"\0" + str(mode & 0o777).encode() + b"\0")
        if item["kind"] == "symlink":
            digest.update(b"link\0" + str(item["link_target"]).encode() + b"\0")
        elif item["kind"] == "directory":
            digest.update(b"directory\0")
        else:
            digest.update(b"file\0" + bytes.fromhex(str(item["content_sha256"])))
    observed_tree = digest.hexdigest()
    files_digest = hashlib.sha256()
    for relative_path, content_sha in sorted(observed_files.items()):
        files_digest.update(
            relative_path.encode("utf-8") + b"\0" + bytes.fromhex(content_sha)
        )
    if files_digest.hexdigest() != embedded_files_sha256:
        raise ValueError("Go-wrapper extracted package file digest does not match")
    return {
        "path_from_home": extracted.relative_to(home.resolve(strict=True)).as_posix(),
        "extracted_tree_sha256": observed_tree,
    }
