import json
import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Protocol


class ArtifactStorageError(Exception):
    """Base class for artifact-storage failures."""


class ArtifactStorageConfigurationError(ArtifactStorageError, ValueError):
    """The configured artifact-storage backend or root is invalid."""


class ArtifactStorageNotFoundError(ArtifactStorageError, FileNotFoundError):
    """An artifact run or file does not exist."""


class ArtifactStorage(Protocol):
    root: Path

    def create_run_artifacts_dir(self, relative_artifacts_dir: str) -> Path: ...

    def run_artifacts_dir(self, relative_artifacts_dir: str) -> Path: ...

    def list_files(self, relative_artifacts_dir: str) -> list[tuple[str, int]]: ...

    def read_text(self, relative_artifacts_dir: str, name: str) -> str: ...

    def read_bytes(self, relative_artifacts_dir: str, name: str) -> bytes: ...


class FilesystemArtifactStorage:
    _MANIFEST = ".action-server-run-bindings.json"

    def __init__(self, root: Path):
        candidate = root.expanduser().absolute()
        if (
            not candidate.is_dir()
            or candidate.resolve() != candidate
            or not os.access(candidate, os.R_OK | os.W_OK | os.X_OK)
        ):
            raise ArtifactStorageConfigurationError(
                f"Artifact storage root must be an existing non-symlink directory: {root}"
            )
        self.root = candidate

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
        try:
            relative = path.absolute().relative_to(self.root)
        except ValueError as error:
            raise ArtifactStorageConfigurationError(
                f"{label} escapes storage root: {path}"
            ) from error
        current = self.root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise ArtifactStorageConfigurationError(
                    f"{label} contains a symlink: {path}"
                )
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(self.root)
        except ValueError as error:
            raise ArtifactStorageConfigurationError(
                f"{label} escapes storage root: {path}"
            ) from error
        if resolved == self.root:
            raise ArtifactStorageConfigurationError(
                f"{label} cannot be the storage root: {path}"
            )
        return resolved

    def _run_dir(self, relative_artifacts_dir: str, *, require_exists: bool) -> Path:
        key = self._canonical_key(relative_artifacts_dir, "artifact run key")
        return self._contained(
            self.root.joinpath(*key.parts), "Artifact run path", require_exists=require_exists
        )

    def _manifest_path(self, *, require_exists: bool) -> Path:
        return self._contained(self.root / self._MANIFEST, "Artifact binding manifest", require_exists=require_exists)

    def _file(self, relative_artifacts_dir: str, name: str) -> Path:
        run_dir = self.run_artifacts_dir(relative_artifacts_dir)
        self._canonical_key(name, "artifact name")
        path = self._contained(run_dir / Path(name), "Artifact path", require_exists=False)
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
                files.append((resolved.relative_to(run_dir).as_posix(), resolved.stat().st_size))
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
        parent = self._contained((run_dir / Path(name)).parent, "Artifact directory", require_exists=False)
        parent.mkdir(parents=True, exist_ok=True)
        target = self._contained(run_dir / Path(name), "Artifact path", require_exists=False)
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

    def write_bytes(self, relative_artifacts_dir: str, name: str, content: bytes) -> None:
        self._write(relative_artifacts_dir, name, content)

    def bind_run(self, run_id: str, relative_artifacts_dir: str, metadata: dict[str, Any] | None = None) -> None:
        self._canonical_key(run_id, "run ID")
        key = self._canonical_key(relative_artifacts_dir, "artifact run key")
        manifest = self._manifest_path(require_exists=False)
        import fcntl

        lock = self.root / f"{self._MANIFEST}.lock"
        with lock.open("a+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            try:
                try:
                    bindings = json.loads(manifest.read_text())
                except FileNotFoundError:
                    bindings = {}
                except (OSError, json.JSONDecodeError) as error:
                    raise ArtifactStorageConfigurationError("Corrupt artifact run binding manifest") from error
                record = {"key": key.as_posix(), "metadata": metadata or {}}
                if run_id in bindings and bindings[run_id] != record:
                    raise ArtifactStorageConfigurationError(f"Conflicting artifact binding for run: {run_id}")
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
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def run_storage_key(self, run_id: str) -> str:
        try:
            record = json.loads(self._manifest_path(require_exists=True).read_text())[run_id]
            key = record["key"]
        except (FileNotFoundError, KeyError) as error:
            raise ArtifactStorageNotFoundError(run_id) from error
        except (OSError, TypeError, json.JSONDecodeError) as error:
            raise ArtifactStorageConfigurationError("Corrupt artifact run binding manifest") from error
        self._run_dir(key, require_exists=True)
        return key

    def run_metadata(self, run_id: str) -> dict[str, Any]:
        key = self.run_storage_key(run_id)
        metadata = json.loads(self._manifest_path(require_exists=True).read_text())[run_id]["metadata"]
        if not isinstance(metadata, dict) or metadata.get("id") != run_id:
            raise ArtifactStorageConfigurationError("Corrupt artifact run metadata")
        if metadata.get("relative_artifacts_dir") != key:
            raise ArtifactStorageConfigurationError("Artifact run metadata key mismatch")
        return metadata


def create_artifact_storage(backend: str, root: Path | None) -> FilesystemArtifactStorage:
    if backend not in {"local", "shared-filesystem"}:
        raise ArtifactStorageConfigurationError(f"Unsupported artifact storage backend: {backend}")
    if backend == "shared-filesystem" and root is None:
        raise ArtifactStorageConfigurationError("artifact_storage_root is required for the shared-filesystem backend")
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
