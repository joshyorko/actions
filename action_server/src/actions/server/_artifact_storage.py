from pathlib import Path
from typing import Protocol


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
    def __init__(self, root: Path):
        self.root = root.expanduser().absolute()

    def _run_dir(self, relative_artifacts_dir: str) -> Path:
        run_dir = (self.root / relative_artifacts_dir).absolute()
        try:
            run_dir.relative_to(self.root)
        except ValueError as error:
            raise ArtifactStorageConfigurationError(
                f"Artifact run path escapes storage root: {relative_artifacts_dir}"
            ) from error
        return run_dir

    def create_run_artifacts_dir(self, relative_artifacts_dir: str) -> Path:
        run_dir = self._run_dir(relative_artifacts_dir)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def run_artifacts_dir(self, relative_artifacts_dir: str) -> Path:
        run_dir = self._run_dir(relative_artifacts_dir)
        if not run_dir.is_dir():
            raise ArtifactStorageNotFoundError(str(run_dir))
        return run_dir

    def _file(self, relative_artifacts_dir: str, name: str) -> Path:
        run_dir = self.run_artifacts_dir(relative_artifacts_dir)
        file_path = (run_dir / name).absolute()
        try:
            file_path.relative_to(run_dir)
        except ValueError as error:
            raise ArtifactStorageConfigurationError(
                f"Artifact path escapes run directory: {name}"
            ) from error
        if not file_path.is_file():
            raise ArtifactStorageNotFoundError(str(file_path))
        return file_path

    def list_files(self, relative_artifacts_dir: str) -> list[tuple[str, int]]:
        run_dir = self.run_artifacts_dir(relative_artifacts_dir)
        files = []
        for path in run_dir.rglob("*"):
            if path.is_file():
                files.append((path.relative_to(run_dir).as_posix(), path.stat().st_size))
        return files

    def read_text(self, relative_artifacts_dir: str, name: str) -> str:
        return self._file(relative_artifacts_dir, name).read_text("utf-8", "replace")

    def read_bytes(self, relative_artifacts_dir: str, name: str) -> bytes:
        return self._file(relative_artifacts_dir, name).read_bytes()

    def write_text(self, relative_artifacts_dir: str, name: str, content: str) -> None:
        path = self.run_artifacts_dir(relative_artifacts_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_bytes(self, relative_artifacts_dir: str, name: str, content: bytes) -> None:
        path = self.run_artifacts_dir(relative_artifacts_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def create_artifact_storage(backend: str, root: Path | None) -> FilesystemArtifactStorage:
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
    root = settings.artifact_storage_root or settings.artifacts_dir
    return create_artifact_storage(
        settings.artifact_storage_backend, root
    )
