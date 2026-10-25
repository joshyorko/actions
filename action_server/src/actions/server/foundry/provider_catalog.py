"""Private durable catalogs under an owned Runtime datadir.

Caller holds the Runtime mutex and excludes concurrent same-user filesystem
mutation for writes. Startup only opens/validates; no secret reads or recovery.
"""
from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from actions.server.deployments.ids import WorkspaceId
from actions.server.deployments.logical_bindings import _Value
from actions.server.deployments.provider_registry import (
    ProviderDescriptor,
    SourceManifest,
    canonical,
    require_executable_source,
)
from actions.server.foundry.provider_config import ProviderHostConfig, SecretVersion
from actions.server.foundry.provider_registry import RetainedSourceEvidence
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor, SealReceipt

MAX_PRIVATE_BYTES = 1024 * 1024


def _uuid(value: str) -> str:
    if str(UUID(value)) != value:
        raise ValueError("canonical private identity required")
    return value


def _bytes(value: _Value) -> bytes:
    # Catalog has a separate aggregate budget; per-object public metadata remains bounded.
    from actions.server.deployments.canonical import canonicalize_json

    raw = canonicalize_json(value.model_dump_json().encode())
    if len(raw) > MAX_PRIVATE_BYTES:
        raise ValueError("private provider state exceeds bound")
    return raw


class CatalogSeal(_Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    seal: SealReceipt


class SourceSealRecord(_Value):
    schema_version: Literal[
        "actions.local-source-seals/v1"
    ] = "actions.local-source-seals/v1"
    owner: Actor
    workspace: WorkspaceId
    source: SourceManifest
    seals: tuple[CatalogSeal, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def identities(self):
        require_executable_source(self.source)
        expected = {obj.name: (obj.digest, obj.size) for obj in self.source.objects}
        actual = {item.name: (item.seal.digest, item.seal.size) for item in self.seals}
        if len(actual) != len(self.seals) or expected != actual:
            raise ValueError("source seal identity mismatch")
        object.__setattr__(
            self, "seals", tuple(sorted(self.seals, key=lambda item: item.name))
        )
        return self


class CatalogEntry(_Value):
    descriptor: ProviderDescriptor
    source: SourceManifest
    seals: tuple[CatalogSeal, ...] = Field(min_length=1, max_length=16)
    config_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def identities(self):
        require_executable_source(self.source)
        if (
            self.descriptor.source_revision != self.source.revision_id
            or self.descriptor.kind != self.source.kind
        ):
            raise ValueError("catalog source identity mismatch")
        expected = {obj.name: (obj.digest, obj.size) for obj in self.source.objects}
        actual = {item.name: (item.seal.digest, item.seal.size) for item in self.seals}
        if len(actual) != len(self.seals) or expected != actual:
            raise ValueError("catalog source evidence mismatch")
        object.__setattr__(
            self, "seals", tuple(sorted(self.seals, key=lambda item: item.name))
        )
        return self


class ProviderCatalog(_Value):
    schema_version: Literal[
        "actions.local-provider-catalog/v1"
    ] = "actions.local-provider-catalog/v1"
    owner: Actor
    workspace: WorkspaceId
    generation: str
    parent_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    entries: tuple[CatalogEntry, ...] = Field(max_length=32)
    _generation = field_validator("generation")(_uuid)

    @model_validator(mode="after")
    def identities(self):
        keys = [entry.descriptor.reference.model_dump_json() for entry in self.entries]
        if len(set(keys)) != len(keys) or any(
            entry.descriptor.workspace_id != self.workspace for entry in self.entries
        ):
            raise ValueError("catalog provider scope mismatch")
        object.__setattr__(
            self,
            "entries",
            tuple(
                sorted(
                    self.entries,
                    key=lambda entry: entry.descriptor.reference.model_dump_json(),
                )
            ),
        )
        return self

    @property
    def catalog_digest(self) -> str:
        return (
            "sha256:"
            + hashlib.sha256(
                b"actions.local-provider-catalog/v1\n" + _bytes(self)
            ).hexdigest()
        )


class CatalogPointer(_Value):
    schema_version: Literal[
        "actions.local-provider-pointer/v1"
    ] = "actions.local-provider-pointer/v1"
    generation: str
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    _generation = field_validator("generation")(_uuid)


class CatalogIntent(_Value):
    schema_version: Literal[
        "actions.local-provider-intent/v1"
    ] = "actions.local-provider-intent/v1"
    operation_id: str
    owner: Actor
    workspace: WorkspaceId
    request_key: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected: CatalogPointer | None
    target: CatalogPointer
    _operation = field_validator("operation_id")(_uuid)


def _private(info: os.stat_result, *, directory: bool) -> None:
    if (
        info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o077
        or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
        or (not directory and info.st_nlink != 1)
    ):
        raise ValueError("private owned provider state required")


class PrivateProviderStore:
    """Fixed FD-anchored namespace; create=True is explicit offline operator only."""

    def __init__(
        self,
        datadir: Path,
        owner: Actor,
        workspace: WorkspaceId,
        *,
        create: bool = False,
    ):
        self.owner = Actor.model_validate(owner)
        self.workspace = WorkspaceId.model_validate(workspace)
        self._write = create
        self._fds: dict[str, int] = {}
        self._root = -1
        self._closed = False
        if (
            not datadir.is_absolute()
            or ".." in datadir.parts
            or any(p.is_symlink() for p in (datadir, *datadir.parents))
        ):
            raise ValueError("canonical owned datadir required")
        _private(datadir.stat(), directory=True)
        datafd = os.open(datadir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _private(os.fstat(datafd), directory=True)
            if create:
                try:
                    os.mkdir("provider-state", 0o700, dir_fd=datafd)
                    os.fsync(datafd)
                except FileExistsError:
                    pass
            self._root = os.open(
                "provider-state",
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=datafd,
            )
            _private(os.fstat(self._root), directory=True)
            for name in ("catalogs", "configs", "secrets", "intents", "sources"):
                if create:
                    try:
                        os.mkdir(name, 0o700, dir_fd=self._root)
                        os.fsync(self._root)
                    except FileExistsError:
                        pass
                fd = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=self._root,
                )
                self._fds[name] = fd
                _private(os.fstat(fd), directory=True)
        except BaseException:
            self.close()
            raise
        finally:
            os.close(datafd)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            for fd in self._fds.values():
                os.close(fd)
            if self._root >= 0:
                os.close(self._root)

    def _fd(self, group: str) -> int:
        if self._closed:
            raise ValueError("closed private provider store")
        return self._root if group == "" else self._fds[group]

    def _read(self, group: str, name: str, limit: int = MAX_PRIVATE_BYTES) -> bytes:
        fd = os.open(
            name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self._fd(group)
        )
        try:
            before = os.fstat(fd)
            _private(before, directory=False)
            if before.st_size > limit:
                raise ValueError("private provider state exceeds bound")
            data = bytearray()
            while len(data) <= limit:
                part = os.read(fd, min(65536, limit + 1 - len(data)))
                if not part:
                    break
                data.extend(part)
            after = os.fstat(fd)
            if (
                len(data) != before.st_size
                or len(data) > limit
                or (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                    before.st_ctime_ns,
                )
                != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                )
            ):
                raise ValueError("private provider state changed")
            return bytes(data)
        finally:
            os.close(fd)

    def _put(self, group: str, name: str, raw: bytes) -> None:
        if not self._write or len(raw) > MAX_PRIVATE_BYTES:
            raise ValueError("explicit bounded operator write required")
        directory = self._fd(group)
        try:
            existing = self._read(group, name)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if existing != raw:
                raise ValueError("immutable private provider state conflict")
            return
        temporary = ".stage-" + str(uuid4())
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        owned = os.fstat(fd)
        try:
            view = memoryview(raw)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise ValueError("private write made no progress")
                view = view[count:]
            os.fsync(fd)
            os.fchmod(fd, 0o400)
            os.fsync(fd)
            # The documented mutex/exclusive same-user writer precondition makes
            # this check + rename safe; there is no concurrent-adversary claim.
            try:
                existing = self._read(group, name)
            except FileNotFoundError:
                existing = None
            if existing is not None:
                if existing != raw:
                    raise ValueError("immutable private provider state conflict")
                return
            os.rename(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            os.close(fd)
            try:
                current = os.stat(temporary, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                    os.unlink(temporary, dir_fd=directory)
                    os.fsync(directory)

    def current(self) -> CatalogPointer | None:
        try:
            raw = self._read("", "CURRENT", 4096)
        except FileNotFoundError:
            return None
        value = CatalogPointer.model_validate_json(raw)
        if _bytes(value) != raw:
            raise ValueError("noncanonical provider pointer")
        return value

    def stage_source(self, record: SourceSealRecord) -> None:
        record = SourceSealRecord.model_validate(record)
        self._lineage(record.owner, record.workspace)
        self._put("sources", record.source.revision_id[7:] + ".json", _bytes(record))

    def source(self, revision: str) -> SourceSealRecord:
        from actions.server.deployments.ids import ProviderProfileRevisionId

        ProviderProfileRevisionId(revision)
        raw = self._read("sources", revision[7:] + ".json")
        record = SourceSealRecord.model_validate_json(raw)
        self._lineage(record.owner, record.workspace)
        if record.source.revision_id != revision or _bytes(record) != raw:
            raise ValueError("source seal record identity mismatch")
        return record

    def stage_config(self, config: ProviderHostConfig) -> str:
        config = ProviderHostConfig.model_validate(config)
        if config.provider.workspace_id != self.workspace:
            raise ValueError("private config Workspace mismatch")
        key = config.config_digest
        self._put(
            "configs", key.removeprefix("sha256:") + ".json", canonical(config).encode()
        )
        return key

    def config(self, digest_value: str) -> ProviderHostConfig:
        # Validate digest before deriving any filename.
        from actions.server.deployments.ids import ProviderProfileRevisionId

        ProviderProfileRevisionId(digest_value)
        raw = self._read(
            "configs", digest_value.removeprefix("sha256:") + ".json", 128 * 1024
        )
        config = ProviderHostConfig.model_validate_json(raw)
        if (
            config.config_digest != digest_value
            or canonical(config).encode() != raw
            or config.provider.workspace_id != self.workspace
        ):
            raise ValueError("private config identity mismatch")
        return config

    def stage_catalog(self, catalog: ProviderCatalog) -> CatalogPointer:
        catalog = ProviderCatalog.model_validate(catalog)
        self._lineage(catalog.owner, catalog.workspace)
        self._put("catalogs", catalog.generation + ".json", _bytes(catalog))
        return CatalogPointer(
            generation=catalog.generation, digest=catalog.catalog_digest
        )

    def _lineage(self, owner: Actor, workspace: WorkspaceId) -> None:
        if owner != self.owner or workspace != self.workspace:
            raise ValueError("private provider owner lineage mismatch")

    def catalog(self, pointer: CatalogPointer) -> ProviderCatalog:
        pointer = CatalogPointer.model_validate(pointer)
        raw = self._read("catalogs", pointer.generation + ".json")
        value = ProviderCatalog.model_validate_json(raw)
        self._lineage(value.owner, value.workspace)
        if (
            value.generation != pointer.generation
            or value.catalog_digest != pointer.digest
            or _bytes(value) != raw
        ):
            raise ValueError("private catalog identity mismatch")
        return value

    def reconstruct(
        self, pointer: CatalogPointer, blobs: FilesystemOutputProvider
    ) -> tuple[ProviderCatalog, RetainedSourceEvidence]:
        catalog = self.catalog(pointer)
        seals: dict[tuple[str, str], SealReceipt] = {}
        for entry in catalog.entries:
            config = self.config(entry.config_digest)
            if (
                config.provider != entry.descriptor.reference
                or config.source_revision != entry.source.revision_id
            ):
                raise ValueError("catalog config identity mismatch")
            for item in entry.seals:
                key = (str(catalog.workspace.root), item.seal.digest)
                if key in seals and seals[key] != item.seal:
                    raise ValueError("ambiguous source seal catalog")
                seals[key] = item.seal
        evidence = RetainedSourceEvidence(blobs, seals)
        for entry in catalog.entries:
            evidence.verify(self.workspace, entry.source)
        return catalog, evidence

    def stage_intent(self, intent: CatalogIntent) -> None:
        intent = CatalogIntent.model_validate(intent)
        self._lineage(intent.owner, intent.workspace)
        self._put("intents", intent.operation_id + ".json", _bytes(intent))

    def intent(self, operation_id: str) -> CatalogIntent:
        raw = self._read("intents", _uuid(operation_id) + ".json", 128 * 1024)
        value = CatalogIntent.model_validate_json(raw)
        self._lineage(value.owner, value.workspace)
        if value.operation_id != operation_id or _bytes(value) != raw:
            raise ValueError("private intent identity mismatch")
        return value

    def publish(self, intent: CatalogIntent) -> None:
        """Caller must verify committed SQL receipt and live authority first."""
        if not self._write:
            raise ValueError("explicit operator write required")
        stored = self.intent(intent.operation_id)
        if stored != intent:
            raise ValueError("private intent differs")
        current = self.current()
        if current == intent.target:
            self.catalog(current)
            return
        if current != intent.expected:
            raise ValueError("stale private catalog intent")
        catalog = self.catalog(intent.target)
        if catalog.parent_digest != (current.digest if current else None):
            raise ValueError("private catalog parent mismatch")
        name = "pending-" + str(uuid4())
        self._put("", name, _bytes(intent.target))
        os.replace(name, "CURRENT", src_dir_fd=self._root, dst_dir_fd=self._root)
        os.fsync(self._root)

    def import_secret(self, reference: SecretVersion, value: bytes) -> None:
        reference = SecretVersion.model_validate(reference)
        if not isinstance(value, bytes) or not 1 <= len(value) <= 65536:
            raise ValueError("bounded secret bytes required")
        self._put("secrets", reference.slot + "-" + reference.version, value)

    def resolve_secret(self, reference: SecretVersion) -> bytes:
        """Explicit host operation only; never invoked by reconstruct/startup."""
        reference = SecretVersion.model_validate(reference)
        return self._read("secrets", reference.slot + "-" + reference.version, 65536)
