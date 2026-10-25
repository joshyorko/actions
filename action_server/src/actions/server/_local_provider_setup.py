"""Explicit offline saved-owner provider setup; never a model/admin HTTP route.

The local mutex covers cooperating Runtime writers; the operator also excludes
other same-user filesystem mutation. Shared PostgreSQL control planes are refused.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from dataclasses import asdict
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import Field, model_validator

from actions.server._common.app_mutex import obtain_app_mutex
from actions.server._database import Database
from actions.server._local_authorization import _operations, _owned, _owner
from actions.server._models import get_all_model_classes
from actions.server.deployments.ids import ProviderProfileRevisionRef, WorkspaceId
from actions.server.deployments.logical_bindings import _Value
from actions.server.deployments.provider_registry import (
    ProviderDescriptor,
    SourceManifest,
    canonical,
    digest,
    require_executable_source,
)
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.provider_catalog import (
    CatalogEntry,
    CatalogIntent,
    CatalogPointer,
    CatalogSeal,
    PrivateProviderStore,
    ProviderCatalog,
    SourceSealRecord,
)
from actions.server.foundry.provider_config import ProviderHostConfig, SecretVersion
from actions.server.foundry.provider_models import (
    FoundryProviderAvailability,
    FoundryProviderRevision,
)
from actions.server.foundry.provider_registry import (
    RetainedSourceEvidence,
    SqlProviderRegistry,
    _ref_id,
)
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor


class SourceImport(_Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    path: str = Field(min_length=1, max_length=4096)


class SecretImport(_Value):
    reference: SecretVersion
    path: str = Field(min_length=1, max_length=4096)


class LocalProviderRequest(_Value):
    schema_version: Literal[
        "actions.local-provider-setup/v1"
    ] = "actions.local-provider-setup/v1"
    operation: Literal[
        "inspect",
        "grant-owner",
        "revoke-owner",
        "import-source",
        "register-revision",
        "configure-host",
        "recover-intent",
        "set-enabled",
    ]
    request_id: str = Field(min_length=1, max_length=128)
    workspace_id: WorkspaceId
    provider: ProviderProfileRevisionRef | None = None
    permissions: tuple[
        Literal[
            "provider.register",
            "provider.inspect",
            "provider.manage",
            "deploy",
            "execute",
            "data.read",
            "data.manage",
        ],
        ...,
    ] = ()
    expected_grants_digest: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    source: SourceManifest | None = None
    files: tuple[SourceImport, ...] = Field(default=(), max_length=16)
    descriptor: ProviderDescriptor | None = None
    config: ProviderHostConfig | None = None
    secrets: tuple[SecretImport, ...] = Field(default=(), max_length=2)
    expected_catalog: CatalogPointer | None = None
    intent_id: str | None = None
    expected_generation: int | None = Field(default=None, ge=0)
    enabled: bool | None = None

    @model_validator(mode="after")
    def shape(self):
        allowed = {
            "inspect": {"provider"},
            "grant-owner": {"provider", "permissions", "expected_grants_digest"},
            "revoke-owner": {"provider", "permissions", "expected_grants_digest"},
            "import-source": {"source", "files"},
            "register-revision": {"descriptor"},
            "configure-host": {"config", "secrets", "expected_catalog"},
            "recover-intent": {"intent_id"},
            "set-enabled": {"provider", "expected_generation", "enabled"},
        }[self.operation]
        common = {"schema_version", "operation", "request_id", "workspace_id"}
        if any(
            name not in common | allowed and getattr(self, name) not in (None, ())
            for name in self.model_fields_set
        ):
            raise ValueError("fields outside selected provider operation")
        if len(set(self.permissions)) != len(self.permissions):
            raise ValueError("unique named permissions required")
        if self.operation in ("grant-owner", "revoke-owner"):
            if (
                not self.permissions
                or (
                    self.provider is None
                    and set(self.permissions) != {"provider.register"}
                )
                or (
                    self.provider is not None
                    and "provider.register" in self.permissions
                )
            ):
                raise ValueError(
                    "workspace register or exact-reference permissions required"
                )
        if self.operation == "import-source" and (
            self.source is None or not self.files
        ):
            raise ValueError("exact source and private imports required")
        if self.operation == "register-revision" and self.descriptor is None:
            raise ValueError("exact descriptor required")
        if self.operation == "configure-host" and self.config is None:
            raise ValueError("exact private configuration required")
        if self.operation == "recover-intent" and self.intent_id is None:
            raise ValueError("explicit intent identity required")
        if self.operation == "set-enabled" and (
            self.provider is None
            or self.enabled is None
            or self.expected_generation is None
        ):
            raise ValueError("exact provider availability CAS required")
        return self


def _key(actor: Actor, workspace: WorkspaceId, name: str) -> str:
    return str(
        uuid5(
            NAMESPACE_URL,
            "actions.local-provider-setup/v1:"
            + str(workspace.root)
            + ":"
            + actor.principal_id
            + ":"
            + name,
        )
    )


def _fingerprint(request: LocalProviderRequest) -> str:
    return digest("actions.local-provider-setup/v1", canonical(request))


def _metadata(db: Database, ref: ProviderProfileRevisionRef) -> ProviderDescriptor:
    rows = db.all(FoundryProviderRevision, where="id=?", values=[_ref_id(ref)])
    if (
        len(rows) != 1
        or rows[0].workspace_id != str(ref.workspace_id.root)
        or len(rows[0].descriptor_json) > 128 * 1024
    ):
        raise ValueError("exact retained provider unavailable")
    value = ProviderDescriptor.model_validate_json(rows[0].descriptor_json)
    if value.reference != ref or canonical(value) != rows[0].descriptor_json:
        raise ValueError("retained provider identity mismatch")
    return value


def _receipt(
    db: Database, actor: Actor, workspace: WorkspaceId, request: LocalProviderRequest
) -> FoundryRequest | None:
    identity = _key(actor, workspace, request.request_id)
    rows = db.all(FoundryRequest, where="id=?", values=[identity])
    if not rows:
        return None
    row = rows[0]
    expected = (
        str(workspace.root),
        actor.principal_id,
        "runtime.providers-local." + request.operation,
        request.request_id,
        _fingerprint(request),
    )
    if (
        row.workspace_id,
        row.principal_id,
        row.operation,
        row.idempotency_key,
        row.request_fingerprint,
    ) != expected:
        raise ValueError("local provider request replay conflict")
    audits = db.all(FoundryAudit, where="foundry_request_id=?", values=[identity])
    if len(audits) != 1 or (
        audits[0].id,
        audits[0].workspace_id,
        audits[0].principal_id,
        audits[0].operation,
        audits[0].deployment_id,
    ) != (
        str(uuid5(NAMESPACE_URL, identity)),
        str(workspace.root),
        actor.principal_id,
        row.operation,
        "",
    ):
        raise ValueError("local provider receipt provenance mismatch")
    return row


def _record(
    db: Database,
    actor: Actor,
    workspace: WorkspaceId,
    request: LocalProviderRequest,
    result: dict,
    revision: str = "",
) -> None:
    identity = _key(actor, workspace, request.request_id)
    operation = "runtime.providers-local." + request.operation
    db.insert(
        FoundryRequest(
            identity,
            str(workspace.root),
            actor.principal_id,
            operation,
            request.request_id,
            _fingerprint(request),
            json.dumps(result, sort_keys=True),
        )
    )
    db.insert(
        FoundryAudit(
            str(uuid5(NAMESPACE_URL, identity)),
            str(workspace.root),
            "",
            actor.principal_id,
            operation,
            identity,
            "",
            revision,
            str(int(time.time() * 1000)),
        )
    )


def _grant_state(
    db: Database,
    actor: Actor,
    workspace: WorkspaceId,
    ref: ProviderProfileRevisionRef | None,
):
    kind, subject = (
        ("reference", reference_grant_subject(ref))
        if ref is not None
        else ("workspace", str(workspace.root))
    )
    identity = _key(actor, workspace, "grant:" + kind + ":" + subject)
    rows = db.all(FoundryAccessGrant, where="id=?", values=[identity])
    row = rows[0] if rows else None
    if row and (
        row.workspace_id,
        row.principal_id,
        row.subject_kind,
        row.subject_id,
    ) != (str(workspace.root), actor.principal_id, kind, subject):
        raise ValueError("owned provider grant identity conflict")
    state = digest(
        "actions.local-provider-grants/v1",
        json.dumps(asdict(row) if row else None, sort_keys=True),
    )
    return identity, kind, subject, row, state


def _grant(
    db: Database,
    actor: Actor,
    workspace: WorkspaceId,
    request: LocalProviderRequest,
    dry_run: bool,
) -> dict:
    if request.provider is not None:
        _metadata(db, request.provider)
    identity, kind, subject, row, state = _grant_state(
        db, actor, workspace, request.provider
    )
    result = {
        "operation": request.operation,
        "provider": request.provider.model_dump(mode="json")
        if request.provider
        else None,
        "expected_grants_digest": state,
        "permissions": list(request.permissions),
    }
    if dry_run:
        return result
    prior = _receipt(db, actor, workspace, request)
    if prior is not None:
        return json.loads(prior.result_json)
    if request.expected_grants_digest != state:
        raise ValueError("provider grant CAS conflict; inspect dry-run first")
    current = _operations(row.operations_json) if row else set()
    if row is not None:
        history = db.select(
            FoundryRequest,
            "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? AND operation IN (?,?) LIMIT 129",
            [
                str(workspace.root),
                actor.principal_id,
                "runtime.providers-local.grant-owner",
                "runtime.providers-local.revoke-owner",
            ],
        )
        if len(history) > 128:
            raise ValueError("bounded provider grant provenance required")
        proven = False
        for receipt in history:
            if len(receipt.result_json) > 16384:
                continue
            value = json.loads(receipt.result_json)
            audits = db.all(
                FoundryAudit, where="foundry_request_id=?", values=[receipt.id]
            )
            if (
                value.get("ownedGrant") == asdict(row)
                and receipt.id == _key(actor, workspace, receipt.idempotency_key)
                and len(audits) == 1
                and (
                    audits[0].id,
                    audits[0].workspace_id,
                    audits[0].principal_id,
                    audits[0].operation,
                    audits[0].deployment_id,
                )
                == (
                    str(uuid5(NAMESPACE_URL, receipt.id)),
                    str(workspace.root),
                    actor.principal_id,
                    receipt.operation,
                    "",
                )
            ):
                proven = True
        if not proven:
            raise ValueError("command-owned grant provenance required")
    updated = (
        current | set(request.permissions)
        if request.operation == "grant-owner"
        else current - set(request.permissions)
    )
    owned = FoundryAccessGrant(
        identity,
        str(workspace.root),
        actor.principal_id,
        kind,
        subject,
        json.dumps(sorted(updated)),
    )
    if row is None:
        db.insert(owned)
    else:
        db.update_by_id(
            FoundryAccessGrant, identity, {"operations_json": owned.operations_json}
        )
    result["ownedGrant"] = asdict(owned)
    _record(
        db,
        actor,
        workspace,
        request,
        result,
        request.provider.revision_id.root if request.provider else "",
    )
    return result


def _evidence(
    record: SourceSealRecord, blobs: FilesystemOutputProvider
) -> RetainedSourceEvidence:
    value = RetainedSourceEvidence(
        blobs,
        {
            (str(record.workspace.root), item.seal.digest): item.seal
            for item in record.seals
        },
    )
    value.verify(record.workspace, record.source)
    return value


def _stream(path: Path, maximum: int):
    path = _owned(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if before.st_size > maximum:
            raise ValueError("private source exceeds declared bound")
        remaining = before.st_size
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                raise ValueError("private source truncated")
            remaining -= len(part)
            yield part
        after = os.fstat(fd)
        if os.read(fd, 1) or (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError("private source changed during import")
    finally:
        os.close(fd)


def _import_source(
    store: PrivateProviderStore | None,
    blobs: FilesystemOutputProvider,
    request: LocalProviderRequest,
    dry_run: bool,
) -> SourceSealRecord | None:
    assert request.source is not None
    source = require_executable_source(request.source)
    files = {item.name: item.path for item in request.files}
    if len(files) != len(request.files) or set(files) != {
        obj.name for obj in source.objects
    }:
        raise ValueError("exact private source imports required")
    try:
        old = store.source(source.revision_id) if store is not None else None
    except FileNotFoundError:
        old = None
    if old is not None:
        _evidence(old, blobs)
        return old
    seals = []
    for obj in source.objects:
        chunks = _stream(Path(files[obj.name]), obj.size)
        if dry_run:
            measured, size = hashlib.sha256(), 0
            for chunk in chunks:
                measured.update(chunk)
                size += len(chunk)
            actual_digest = "sha256:" + measured.hexdigest()
        else:
            receipt = blobs.stage(chunks).receipt
            actual_digest, size = receipt.digest, receipt.size
            seals.append(CatalogSeal(name=obj.name, seal=receipt))
        if (actual_digest, size) != (obj.digest, obj.size):
            raise ValueError("private source differs from pinned manifest")
    if dry_run:
        return None
    assert store is not None
    record = SourceSealRecord(
        owner=store.owner, workspace=store.workspace, source=source, seals=tuple(seals)
    )
    store.stage_source(record)
    return record


def _validate_intent_target(
    db: Database,
    store: PrivateProviderStore,
    intent: CatalogIntent,
    request: LocalProviderRequest,
) -> None:
    if (
        request.config is None
        or request.operation != "configure-host"
        or intent.expected != request.expected_catalog
        or intent.request_fingerprint != _fingerprint(request)
    ):
        raise ValueError("configuration intent request differs")
    private = store._read("intents", intent.operation_id + ".request.json", 128 * 1024)
    if private != canonical(request).encode():
        raise ValueError("private configuration request differs")
    config = request.config
    if store.config(config.config_digest) != config:
        raise ValueError("intent configuration differs")
    old = list(store.catalog(intent.expected).entries) if intent.expected else []
    expected = [entry for entry in old if entry.descriptor.reference != config.provider]
    source = store.source(config.source_revision)
    expected.append(
        CatalogEntry(
            descriptor=_metadata(db, config.provider),
            source=source.source,
            seals=source.seals,
            config_digest=config.config_digest,
        )
    )
    target = store.catalog(intent.target)
    if target.parent_digest != (
        intent.expected.digest if intent.expected else None
    ) or target.entries != tuple(
        sorted(expected, key=lambda entry: entry.descriptor.reference.model_dump_json())
    ):
        raise ValueError("configuration target differs from authorized request")


def _configured_intent(
    db: Database,
    store: PrivateProviderStore,
    blobs: FilesystemOutputProvider,
    actor: Actor,
    workspace: WorkspaceId,
    request: LocalProviderRequest,
    auth: SqlFoundryAuthorization,
    dry_run: bool,
) -> dict:
    assert request.config is not None
    config = request.config
    ref = config.provider
    auth.require_reference(actor, ref, "provider.manage")
    descriptor = _metadata(db, ref)
    if descriptor.source_revision != config.source_revision:
        raise ValueError("configuration source identity differs")
    record = store.source(config.source_revision)
    evidence = _evidence(record, blobs)
    operation_id = _key(actor, workspace, request.request_id)
    if dry_run:
        current = store.current()
        return {
            "operation": request.operation,
            "provider": ref.model_dump(mode="json"),
            "expected_catalog": current.model_dump(mode="json") if current else None,
            "readiness": "not-probed",
        }
    _receipt(db, actor, workspace, request)
    try:
        intent = store.intent(operation_id)
    except FileNotFoundError:
        intent = None
    if intent is None:
        current = store.current()
        if current != request.expected_catalog:
            raise ValueError("private catalog CAS conflict")
        if request.secrets:
            allowed = [
                getattr(config.host, name, None) for name in ("password", "ca_bundle")
            ]
            references = [item.reference for item in request.secrets]
            if len(set(item.model_dump_json() for item in references)) != len(
                references
            ) or any(item not in allowed for item in references):
                raise ValueError("secret import must match pinned host configuration")
            for secret in request.secrets:
                store.import_secret(
                    secret.reference, b"".join(_stream(Path(secret.path), 65536))
                )
        key = store.stage_config(config)
        entries = list(store.catalog(current).entries) if current else []
        entries = [entry for entry in entries if entry.descriptor.reference != ref]
        entries.append(
            CatalogEntry(
                descriptor=descriptor,
                source=record.source,
                seals=record.seals,
                config_digest=key,
            )
        )
        catalog = ProviderCatalog(
            owner=actor,
            workspace=workspace,
            generation=operation_id,
            parent_digest=current.digest if current else None,
            entries=tuple(entries),
        )
        target = store.stage_catalog(catalog)
        intent = CatalogIntent(
            operation_id=operation_id,
            owner=actor,
            workspace=workspace,
            request_key=request.request_id,
            request_fingerprint=_fingerprint(request),
            expected=current,
            target=target,
        )
        store._put(
            "intents",
            intent.operation_id + ".request.json",
            canonical(request).encode(),
        )
        store.stage_intent(intent)
    if intent.request_fingerprint != _fingerprint(request):
        raise ValueError("private intent replay conflict")
    _validate_intent_target(db, store, intent, request)
    store.reconstruct(intent.target, blobs)
    # Explicit trusted registry read; target descriptor and every seal rechecked.
    retained, _ = SqlProviderRegistry(db, auth, evidence)._read(ref)
    if retained != descriptor:
        raise ValueError("retained configuration target differs")
    result = {
        "operation": request.operation,
        "provider": ref.model_dump(mode="json"),
        "intent_id": intent.operation_id,
        "readiness": "configured-not-probed",
    }
    with db.transaction():
        auth.require_reference(actor, ref, "provider.manage")
        prior = _receipt(db, actor, workspace, request)
        if prior is None:
            _record(
                db,
                actor,
                workspace,
                request,
                dict(result, readiness="publication-authorized"),
                ref.revision_id.root,
            )
    # SQL commit precedes pointer publication. Replay cannot republish over a newer pointer.
    verify_committed_catalog(db, store, intent.target)
    auth.require_reference(actor, ref, "provider.manage")
    store.publish(intent)
    return result


def verify_committed_catalog(
    db: Database, store: PrivateProviderStore, pointer: CatalogPointer
) -> tuple[CatalogIntent, ProviderProfileRevisionRef]:
    """Read-only publication provenance, independent of current manage grants."""
    intent = store.intent(pointer.generation)
    if intent.operation_id != pointer.generation or intent.target != pointer:
        raise ValueError("catalog publication identity mismatch")
    actor, workspace = store.owner, store.workspace
    rows = db.all(FoundryRequest, where="id=?", values=[intent.operation_id])
    if len(rows) != 1:
        raise ValueError("committed configuration receipt required for recovery")
    row = rows[0]
    if (
        row.workspace_id,
        row.principal_id,
        row.operation,
        row.idempotency_key,
        row.request_fingerprint,
    ) != (
        str(workspace.root),
        actor.principal_id,
        "runtime.providers-local.configure-host",
        intent.request_key,
        intent.request_fingerprint,
    ):
        raise ValueError("configuration receipt lineage differs")
    private_request = LocalProviderRequest.model_validate_json(
        store._read("intents", intent.operation_id + ".request.json", 128 * 1024)
    )
    if (
        private_request.workspace_id != workspace
        or private_request.request_id != intent.request_key
        or row.id != _key(actor, workspace, intent.request_key)
    ):
        raise ValueError("configuration recovery request scope differs")
    _validate_intent_target(db, store, intent, private_request)
    if len(row.result_json) > 16384:
        raise ValueError("bounded configuration receipt required")
    result = json.loads(row.result_json)
    if private_request.config is None:
        raise ValueError("configuration receipt target differs")
    ref = private_request.config.provider
    if result != {
        "operation": "configure-host",
        "provider": ref.model_dump(mode="json"),
        "intent_id": intent.operation_id,
        "readiness": "publication-authorized",
    }:
        raise ValueError("configuration receipt target differs")
    audits = db.all(FoundryAudit, where="foundry_request_id=?", values=[row.id])
    if (
        len(audits) != 1
        or (
            audits[0].id,
            audits[0].workspace_id,
            audits[0].principal_id,
            audits[0].operation,
            audits[0].deployment_id,
            audits[0].from_revision_id,
            audits[0].to_revision_id,
        )
        != (
            str(uuid5(NAMESPACE_URL, row.id)),
            str(workspace.root),
            actor.principal_id,
            row.operation,
            "",
            "",
            ref.revision_id.root,
        )
        or result.get("intent_id") != intent.operation_id
    ):
        raise ValueError("configuration recovery audit mismatch")
    return intent, ref


def _recover(
    db: Database,
    store: PrivateProviderStore,
    blobs: FilesystemOutputProvider,
    actor: Actor,
    workspace: WorkspaceId,
    request: LocalProviderRequest,
    auth: SqlFoundryAuthorization,
    dry_run: bool,
) -> dict:
    assert request.intent_id is not None
    candidate = store.intent(request.intent_id)
    intent, ref = verify_committed_catalog(db, store, candidate.target)
    auth.require_reference(actor, ref, "provider.manage")
    catalog, evidence = store.reconstruct(intent.target, blobs)
    registry = SqlProviderRegistry(db, auth, evidence)
    for entry in catalog.entries:
        if registry._read(entry.descriptor.reference)[0] != entry.descriptor:
            raise ValueError("catalog retained target differs")
    if not dry_run:
        with db.transaction():
            auth.require_reference(actor, ref, "provider.manage")
            if _receipt(db, actor, workspace, request) is None:
                _record(
                    db,
                    actor,
                    workspace,
                    request,
                    {
                        "provider": ref.model_dump(mode="json"),
                        "intent_id": intent.operation_id,
                        "readiness": "publication-authorized",
                    },
                    ref.revision_id.root,
                )
        auth.require_reference(actor, ref, "provider.manage")
        store.publish(intent)
    return {
        "operation": "recover-intent",
        "provider": ref.model_dump(mode="json"),
        "readiness": "publication-authorized-dry-run"
        if dry_run
        else "configured-not-probed",
    }


def run_local_provider_setup(
    datadir: str, request_file: str, *, dry_run: bool = False
) -> dict:
    if os.name != "posix" or os.environ.get("ACTION_SERVER_DATABASE_URL"):
        raise ValueError("offline local SQLite only; shared/external database refused")
    root = _owned(Path(datadir), directory=True)
    db_path = _owned(root / "server.db")
    request_path = _owned(Path(request_file))
    request_bytes = b"".join(_stream(request_path, 128 * 1024))
    request = LocalProviderRequest.model_validate_json(request_bytes)
    # Existing lock must meet the same private regular-file boundary as state.
    lock = root / "action_server.lock"
    if lock.exists() or lock.is_symlink():
        info = lock.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
        ):
            raise ValueError("owned regular Runtime lock required")
    mutex = obtain_app_mutex(
        data_dir=root,
        lock_basename="action_server.lock",
        app_name="Action Server offline provider setup",
        timeout=0,
        kill_lock_holder=False,
    )
    if mutex is None:
        raise ValueError("Runtime is running or its lock is unavailable")
    try:
        _owned(db_path)
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(db_path) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                raise ValueError("unsettled SQLite sidecar; stop Runtime first")
        db = Database(db_path)
        with db.connect():
            db.initialize(get_all_model_classes())
            actor, workspace = _owner(db)
            if request.workspace_id != workspace:
                raise ValueError("request outside saved owner Workspace")
            for ref in (
                request.provider,
                request.descriptor.reference if request.descriptor else None,
                request.config.provider if request.config else None,
            ):
                if ref is not None and ref.workspace_id != workspace:
                    raise ValueError("provider outside saved owner Workspace")
            auth = SqlFoundryAuthorization(db)
            if request.operation in ("grant-owner", "revoke-owner"):
                with db.transaction():
                    return _grant(db, actor, workspace, request, dry_run)
            if request.operation == "inspect":
                if request.provider is not None:
                    auth.require_reference(actor, request.provider, "provider.inspect")
                    descriptor = _metadata(db, request.provider)
                    states = db.all(
                        FoundryProviderAvailability,
                        where="id=?",
                        values=[_ref_id(request.provider)],
                    )
                    if (
                        len(states) != 1
                        or states[0].foundry_provider_revision_id
                        != _ref_id(request.provider)
                        or states[0].generation < 0
                    ):
                        raise ValueError("provider availability unavailable")
                    availability = {
                        "generation": states[0].generation,
                        "enabled": states[0].enabled,
                    }
                else:
                    descriptor = None
                    availability = None
                _, _, _, _, state = _grant_state(db, actor, workspace, request.provider)
                return {
                    "operation": "inspect",
                    "provider": descriptor.model_dump(mode="json")
                    if descriptor
                    else None,
                    "expected_grants_digest": state,
                    "availability": availability,
                    "readiness": "not-probed",
                }
            if request.operation in ("import-source", "register-revision"):
                auth.require_workspace(actor, workspace, "provider.register")
            elif request.operation == "configure-host":
                assert request.config is not None
                auth.require_reference(
                    actor, request.config.provider, "provider.manage"
                )
            elif request.operation == "set-enabled":
                assert request.provider is not None
                assert request.expected_generation is not None
                auth.require_reference(actor, request.provider, "provider.manage")
                if request.enabled is False:
                    if dry_run:
                        return {
                            "operation": request.operation,
                            "readiness": "not-probed",
                        }
                    generation = SqlProviderRegistry(db, auth).set_enabled(
                        actor,
                        request.provider,
                        expected_generation=request.expected_generation,
                        enabled=False,
                        idempotency_key=_key(
                            actor, workspace, "registry:" + request.request_id
                        ),
                    )
                    return {"generation": generation, "enabled": False}
            blob_path = _owned(root / "blobs", directory=True)
            fd = os.open(blob_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                blobs = FilesystemOutputProvider(fd)
            finally:
                os.close(fd)
            with blobs:
                create = not dry_run and request.operation in (
                    "import-source",
                    "configure-host",
                )
                if (
                    dry_run
                    and request.operation == "import-source"
                    and not (root / "provider-state").exists()
                ):
                    assert request.source is not None
                    _import_source(None, blobs, request, True)
                    return {
                        "operation": request.operation,
                        "source_revision": request.source.revision_id,
                        "readiness": "not-probed",
                    }
                with PrivateProviderStore(
                    root, actor, workspace, create=create
                ) as store:
                    if request.operation == "import-source":
                        assert request.source is not None
                        if not dry_run:
                            _receipt(db, actor, workspace, request)
                        record = _import_source(store, blobs, request, dry_run)
                        result = {
                            "operation": request.operation,
                            "source_revision": request.source.revision_id,
                            "readiness": "not-probed",
                        }
                        if not dry_run:
                            assert record is not None
                            with db.transaction():
                                auth.require_workspace(
                                    actor, workspace, "provider.register"
                                )
                                if _receipt(db, actor, workspace, request) is None:
                                    _record(
                                        db,
                                        actor,
                                        workspace,
                                        request,
                                        result,
                                        record.source.revision_id,
                                    )
                        return result
                    if request.operation == "register-revision":
                        assert request.descriptor is not None
                        record = store.source(request.descriptor.source_revision)
                        evidence = _evidence(record, blobs)
                        if not dry_run:
                            ref = SqlProviderRegistry(db, auth, evidence).register(
                                actor,
                                request.descriptor,
                                record.source,
                                idempotency_key=_key(
                                    actor, workspace, "registry:" + request.request_id
                                ),
                            )
                        else:
                            if record.source.kind != request.descriptor.kind:
                                raise ValueError("provider/source kind mismatch")
                            ref = request.descriptor.reference
                        return {
                            "operation": request.operation,
                            "provider": ref.model_dump(mode="json"),
                            "readiness": "metadata-only",
                        }
                    if request.operation == "configure-host":
                        return _configured_intent(
                            db, store, blobs, actor, workspace, request, auth, dry_run
                        )
                    if request.operation == "recover-intent":
                        # Explicit recovery needs writable store, but never creates absent state.
                        if dry_run:
                            return _recover(
                                db, store, blobs, actor, workspace, request, auth, True
                            )
                        with PrivateProviderStore(
                            root, actor, workspace, create=True
                        ) as writable:
                            return _recover(
                                db,
                                writable,
                                blobs,
                                actor,
                                workspace,
                                request,
                                auth,
                                False,
                            )
                    if request.operation == "set-enabled":
                        assert request.expected_generation is not None
                        assert request.provider is not None
                        descriptor = _metadata(db, request.provider)
                        record = store.source(descriptor.source_revision)
                        evidence = _evidence(record, blobs)
                        if dry_run:
                            return {
                                "operation": request.operation,
                                "readiness": "not-probed",
                            }
                        generation = SqlProviderRegistry(
                            db, auth, evidence
                        ).set_enabled(
                            actor,
                            request.provider,
                            expected_generation=request.expected_generation,
                            enabled=True,
                            idempotency_key=_key(
                                actor, workspace, "registry:" + request.request_id
                            ),
                        )
                        return {"generation": generation, "enabled": True}
            raise ValueError("unsupported local provider operation")
    finally:
        mutex.release_mutex()
