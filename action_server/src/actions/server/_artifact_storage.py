import errno
import json
import os
import stat
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, Protocol


class ArtifactStorageError(Exception):
    """Base class for artifact-storage failures."""


class ArtifactStorageConfigurationError(ArtifactStorageError, ValueError):
    """The configured artifact-storage backend or root is invalid."""


class ArtifactStorageNotFoundError(ArtifactStorageError, FileNotFoundError):
    """An artifact run or file does not exist."""


class ArtifactStorage(Protocol):
    root: Path

    def create_run_artifacts_dir(self, relative_artifacts_dir: str) -> Path:
        ...

    def run_artifacts_dir(self, relative_artifacts_dir: str) -> Path:
        ...

    def list_files(self, relative_artifacts_dir: str) -> list[tuple[str, int]]:
        ...

    def read_text(self, relative_artifacts_dir: str, name: str) -> str:
        ...

    def read_bytes(self, relative_artifacts_dir: str, name: str) -> bytes:
        ...


def _relative_parts(path: PurePath, parent: PurePath) -> tuple[str, ...]:
    """Compare local Windows drive prefixes without changing paths used for I/O."""
    try:
        return path.relative_to(parent).parts
    except ValueError:
        if not isinstance(path, PureWindowsPath) or not isinstance(
            parent, PureWindowsPath
        ):
            raise

        def local_drive_spelling(value: PureWindowsPath) -> PureWindowsPath:
            drive = value.drive.removeprefix("\\\\?\\")
            if (
                value.root != "\\"
                or len(drive) != 2
                or drive[0]
                not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
                or drive[1] != ":"
            ):
                raise ValueError("Paths do not have equivalent local drive anchors")
            if any(
                part in {".", ".."}
                or part.endswith((".", " "))
                or ":" in part
                or PureWindowsPath(part).is_reserved()
                for part in value.parts[1:]
            ):
                raise ValueError("Ambiguous Windows component across drive prefixes")
            return PureWindowsPath(drive + "\\", *value.parts[1:])

        return (
            local_drive_spelling(path).relative_to(local_drive_spelling(parent)).parts
        )


def _is_link_or_reparse_point(path: Path) -> bool:
    # lstat observes the directory entry even when a junction target is missing.
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


@contextmanager
def _manifest_lock(path: Path) -> Iterator[None]:
    # Keep this file in place: unlinking it can give concurrent writers different
    # lock objects. The OS releases the lock even if its owning process exits.
    with path.open("a+b") as stream:
        if sys.platform == "win32":
            import msvcrt

            # Windows supports locking beyond EOF, so the persistent lock file
            # need not be initialized or written while another writer holds it.
            while True:
                stream.seek(0)
                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    if error.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    time.sleep(0.05)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


class FilesystemArtifactStorage:
    _MANIFEST = ".action-server-run-bindings.json"

    def __init__(self, root: Path):
        candidate = root.expanduser().absolute()
        if (
            not candidate.is_dir()
            or any(
                _is_link_or_reparse_point(part)
                for part in (candidate, *candidate.parents)
            )
            or not os.access(candidate, os.R_OK | os.W_OK | os.X_OK)
        ):
            raise ArtifactStorageConfigurationError(
                f"Artifact storage root must be an existing non-symlink directory: {root}"
            )
        # Windows expands 8.3 path components during resolve(). A spelling change
        # is not evidence of a link; links/reparse ancestors were rejected above.
        self.root = candidate.resolve(strict=True)

    @staticmethod
    def _canonical_key(value: str, label: str) -> PurePosixPath:
        if not value or "\\" in value:
            raise ArtifactStorageConfigurationError(f"Invalid {label}: {value!r}")
        key = PurePosixPath(value)
        if key.is_absolute() or any(part in {"", ".", ".."} for part in key.parts):
            raise ArtifactStorageConfigurationError(f"Invalid {label}: {value!r}")
        if key.as_posix() != value:
            raise ArtifactStorageConfigurationError(f"Non-canonical {label}: {value!r}")
        return key

    def _contained(self, path: Path, label: str, *, require_exists: bool) -> Path:
        absolute_path = path.absolute()
        try:
            relative_parts = _relative_parts(absolute_path, self.root)
        except ValueError as error:
            raise ArtifactStorageConfigurationError(
                f"{label} escapes storage root: {path}"
            ) from error
        # Check directory entries through the candidate's actual I/O namespace.
        current = absolute_path
        for _ in relative_parts:
            current = current.parent
        for part in relative_parts:
            current /= part
            if _is_link_or_reparse_point(current):
                raise ArtifactStorageConfigurationError(
                    f"{label} contains a symlink: {path}"
                )
        resolved = path.resolve(strict=False)
        try:
            resolved_parts = _relative_parts(resolved, self.root)
        except ValueError as error:
            raise ArtifactStorageConfigurationError(
                f"{label} escapes storage root: {path}"
            ) from error
        if not resolved_parts:
            raise ArtifactStorageConfigurationError(
                f"{label} cannot be the storage root: {path}"
            )
        return resolved

    def _run_dir(self, relative_artifacts_dir: str, *, require_exists: bool) -> Path:
        key = self._canonical_key(relative_artifacts_dir, "artifact run key")
        return self._contained(
            self.root.joinpath(*key.parts),
            "Artifact run path",
            require_exists=require_exists,
        )

    def _manifest_path(self, *, require_exists: bool) -> Path:
        return self._contained(
            self.root / self._MANIFEST,
            "Artifact binding manifest",
            require_exists=require_exists,
        )

    def _file(self, relative_artifacts_dir: str, name: str) -> Path:
        run_dir = self.run_artifacts_dir(relative_artifacts_dir)
        self._canonical_key(name, "artifact name")
        path = self._contained(
            run_dir / Path(name), "Artifact path", require_exists=False
        )
        if not path.is_file():
            raise ArtifactStorageNotFoundError(str(path))
        return path

    def create_run_artifacts_dir(self, relative_artifacts_dir: str) -> Path:
        run_dir = self._run_dir(relative_artifacts_dir, require_exists=False)
        if run_dir.exists() or run_dir.is_symlink():
            raise ArtifactStorageConfigurationError(
                f"Artifact run path already exists or is a symlink: {relative_artifacts_dir}"
            )
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def run_artifacts_dir(self, relative_artifacts_dir: str) -> Path:
        run_dir = self._run_dir(relative_artifacts_dir, require_exists=True)
        if not run_dir.is_dir():
            raise ArtifactStorageNotFoundError(str(run_dir))
        return run_dir

    def list_files(self, relative_artifacts_dir: str) -> list[tuple[str, int]]:
        run_dir = self.run_artifacts_dir(relative_artifacts_dir)
        files = []
        for path in run_dir.rglob("*"):
            if path.is_symlink():
                self._contained(path, "Artifact path", require_exists=True)
            elif path.is_file():
                resolved = self._contained(path, "Artifact path", require_exists=True)
                files.append(
                    (
                        PurePosixPath(*_relative_parts(resolved, run_dir)).as_posix(),
                        resolved.stat().st_size,
                    )
                )
        return sorted(files)

    def read_path(self, relative_artifacts_dir: str, name: str) -> Path:
        return self._file(relative_artifacts_dir, name)

    def read_text(self, relative_artifacts_dir: str, name: str) -> str:
        return self._file(relative_artifacts_dir, name).read_text("utf-8", "replace")

    def read_bytes(self, relative_artifacts_dir: str, name: str) -> bytes:
        return self._file(relative_artifacts_dir, name).read_bytes()

    def _write(self, relative_artifacts_dir: str, name: str, content: bytes) -> None:
        run_dir = self.run_artifacts_dir(relative_artifacts_dir)
        self._canonical_key(name, "artifact name")
        parent = self._contained(
            (run_dir / Path(name)).parent, "Artifact directory", require_exists=False
        )
        parent.mkdir(parents=True, exist_ok=True)
        target = self._contained(
            run_dir / Path(name), "Artifact path", require_exists=False
        )
        fd, temporary = tempfile.mkstemp(dir=parent, prefix=".artifact-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def write_text(self, relative_artifacts_dir: str, name: str, content: str) -> None:
        self._write(relative_artifacts_dir, name, content.encode("utf-8"))

    def write_bytes(
        self, relative_artifacts_dir: str, name: str, content: bytes
    ) -> None:
        self._write(relative_artifacts_dir, name, content)

    def bind_run(
        self,
        run_id: str,
        relative_artifacts_dir: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._canonical_key(run_id, "run ID")
        key = self._canonical_key(relative_artifacts_dir, "artifact run key")
        lock = self._contained(
            self.root / f"{self._MANIFEST}.lock",
            "Artifact binding lock",
            require_exists=False,
        )
        with _manifest_lock(lock):
            manifest = self._manifest_path(require_exists=False)
            try:
                bindings = json.loads(manifest.read_text())
            except FileNotFoundError:
                bindings = {}
            except (OSError, json.JSONDecodeError) as error:
                raise ArtifactStorageConfigurationError(
                    "Corrupt artifact run binding manifest"
                ) from error
            record = {"key": key.as_posix(), "metadata": metadata or {}}
            if run_id in bindings and bindings[run_id] != record:
                raise ArtifactStorageConfigurationError(
                    f"Conflicting artifact binding for run: {run_id}"
                )
            self.run_artifacts_dir(relative_artifacts_dir)
            bindings[run_id] = record
            fd, temporary = tempfile.mkstemp(dir=self.root, prefix=".bindings-")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as output:
                    json.dump(bindings, output, sort_keys=True, separators=(",", ":"))
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, manifest)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

    def run_storage_key(self, run_id: str) -> str:
        try:
            record = json.loads(self._manifest_path(require_exists=True).read_text())[
                run_id
            ]
            key = record["key"]
        except (FileNotFoundError, KeyError) as error:
            raise ArtifactStorageNotFoundError(run_id) from error
        except (OSError, TypeError, json.JSONDecodeError) as error:
            raise ArtifactStorageConfigurationError(
                "Corrupt artifact run binding manifest"
            ) from error
        self._run_dir(key, require_exists=True)
        return key

    def run_metadata(self, run_id: str) -> dict[str, Any]:
        key = self.run_storage_key(run_id)
        metadata = json.loads(self._manifest_path(require_exists=True).read_text())[
            run_id
        ]["metadata"]
        if not isinstance(metadata, dict) or metadata.get("id") != run_id:
            raise ArtifactStorageConfigurationError("Corrupt artifact run metadata")
        if metadata.get("relative_artifacts_dir") != key:
            raise ArtifactStorageConfigurationError(
                "Artifact run metadata key mismatch"
            )
        return metadata


def create_artifact_storage(
    backend: str, root: Path | None
) -> FilesystemArtifactStorage:
    if backend not in {"local", "shared-filesystem"}:
        raise ArtifactStorageConfigurationError(
            f"Unsupported artifact storage backend: {backend}"
        )
    if backend == "shared-filesystem" and root is None:
        raise ArtifactStorageConfigurationError(
            "artifact_storage_root is required for the shared-filesystem backend"
        )
    if root is None:
        raise ArtifactStorageConfigurationError("artifact storage root is required")
    return FilesystemArtifactStorage(root)


def get_artifact_storage() -> FilesystemArtifactStorage:
    from ._settings import get_settings

    settings = get_settings()
    if settings.artifact_storage_root is None:
        settings.artifacts_dir.mkdir(parents=True, exist_ok=True)
    root = settings.artifact_storage_root or settings.artifacts_dir
    return create_artifact_storage(settings.artifact_storage_backend, root)
