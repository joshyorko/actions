"""Explicit common SQL provider metadata with retained sealed-source evidence.

No host/default provider, data operation, credential resolver or grants are created.
"""
from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from actions.server._database import Database
from actions.server.deployments.ids import ProviderProfileRevisionRef, WorkspaceId
from actions.server.deployments.logical_bindings import BindingOperation
from actions.server.deployments.provider_registry import (
    ProviderDescriptor,
    SourceManifest,
    canonical,
    digest,
)
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.foundry.provider_models import (
    FoundryProviderAvailability,
    FoundryProviderRevision,
    FoundrySourceRevision,
)
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor, SealReceipt


def _id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, "actions.provider-registry/v1:" + value))


def _ref_id(ref: ProviderProfileRevisionRef) -> str:
    return _id(ref.model_dump_json())


class RetainedSourceEvidence:
    """Trusted host-supplied seal catalog; no caller locator is accepted.

    Receipts must originate from the configured blob authority. Catalog lifetime
    and durable reconstruction are operator responsibilities, not SQL readiness.
    """

    def __init__(
        self,
        blobs: FilesystemOutputProvider,
        seals: Mapping[tuple[str, str], SealReceipt],
    ):
        self._blobs = blobs
        self._seals = dict(seals)

    def verify(self, workspace: WorkspaceId, source: SourceManifest) -> None:
        for entry in source.objects:
            receipt = self._seals.get((str(workspace.root), entry.digest))
            if (
                receipt is None
                or receipt.digest != entry.digest
                or receipt.size != entry.size
            ):
                raise ValueError("retained source evidence unavailable")
            # open validates the complete digest and sealed file identity.
            try:
                with self._blobs.open(receipt.object_ref, receipt.digest, receipt.size):
                    pass
            except (OSError, ValueError):
                raise ValueError("retained source evidence unavailable") from None


class SqlProviderRegistry:
    def __init__(
        self,
        db: Database,
        authorization: SqlFoundryAuthorization,
        evidence: RetainedSourceEvidence | None = None,
    ):
        self._db = db
        self._auth = authorization
        self._evidence = evidence

    def _verify(self, workspace: WorkspaceId, source: SourceManifest) -> None:
        if self._evidence is None:
            raise ValueError("retained source verifier is not configured")
        self._evidence.verify(workspace, source)

    def _request(
        self,
        actor: Actor,
        workspace: WorkspaceId,
        operation: str,
        key: str,
        payload: str,
    ) -> tuple[str, str, FoundryRequest | None]:
        if not isinstance(key, str) or not 1 <= len(key) <= 128:
            raise ValueError("bounded idempotency key required")
        identity = _id(
            json.dumps([str(workspace.root), actor.principal_id, operation, key])
        )
        fingerprint = digest(operation, payload)
        rows = self._db.all(FoundryRequest, where="id=?", values=[identity])
        old = rows[0] if rows else None
        if old is not None and (
            old.request_fingerprint != fingerprint
            or old.operation != operation
            or old.principal_id != actor.principal_id
            or old.workspace_id != str(workspace.root)
            or old.idempotency_key != key
        ):
            raise ValueError("provider request replay conflict")
        return identity, fingerprint, old

    def _record(
        self,
        actor: Actor,
        ref: ProviderProfileRevisionRef,
        operation: str,
        key: str,
        identity: str,
        fingerprint: str,
        result: str,
    ) -> None:
        self._db.insert(
            FoundryRequest(
                identity,
                str(ref.workspace_id.root),
                actor.principal_id,
                operation,
                key,
                fingerprint,
                result,
            )
        )
        self._db.insert(
            FoundryAudit(
                _id(identity + ":audit"),
                str(ref.workspace_id.root),
                "",
                actor.principal_id,
                operation,
                identity,
                "",
                ref.revision_id.root,
                str(int(time.time() * 1000)),
            )
        )

    def register(
        self,
        actor: Actor,
        descriptor: ProviderDescriptor,
        source: SourceManifest,
        *,
        idempotency_key: str,
    ) -> ProviderProfileRevisionRef:
        actor = Actor.model_validate(actor)
        descriptor = ProviderDescriptor.model_validate(descriptor)
        source = SourceManifest.model_validate(source)
        ref = descriptor.reference
        if (
            source.kind != descriptor.kind
            or source.revision_id != descriptor.source_revision
        ):
            raise ValueError("provider source identity mismatch")
        source_json, descriptor_json = canonical(source), canonical(descriptor)
        with self._db.connect(), self._db.transaction():
            self._auth.require_workspace(actor, ref.workspace_id, "provider.register")
            self._verify(ref.workspace_id, source)
            identity, fingerprint, old = self._request(
                actor,
                ref.workspace_id,
                "provider.register",
                idempotency_key,
                descriptor_json + source_json,
            )
            source_id = _id(str(ref.workspace_id.root) + source.revision_id)
            sources = self._db.all(
                FoundrySourceRevision, where="id=?", values=[source_id]
            )
            if sources:
                stored = sources[0]
                if (stored.workspace_id, stored.revision_id, stored.manifest_json) != (
                    str(ref.workspace_id.root),
                    source.revision_id,
                    source_json,
                ):
                    raise ValueError("retained source identity conflict")
            elif old is not None:
                raise ValueError("retained source missing on replay")
            else:
                self._db.insert(
                    FoundrySourceRevision(
                        source_id,
                        str(ref.workspace_id.root),
                        source.revision_id,
                        source_json,
                    )
                )
            rows = self._db.all(
                FoundryProviderRevision, where="id=?", values=[_ref_id(ref)]
            )
            if rows:
                if (
                    rows[0].workspace_id,
                    rows[0].descriptor_json,
                    rows[0].foundry_source_revision_id,
                ) != (str(ref.workspace_id.root), descriptor_json, source_id):
                    raise ValueError("provider revision identity conflict")
            elif old is not None:
                raise ValueError("provider revision missing on replay")
            else:
                self._db.insert(
                    FoundryProviderRevision(
                        _ref_id(ref),
                        str(ref.workspace_id.root),
                        descriptor_json,
                        source_id,
                    )
                )
                self._db.insert(
                    FoundryProviderAvailability(_ref_id(ref), _ref_id(ref), 0, True)
                )
            if old is None:
                self._record(
                    actor,
                    ref,
                    "provider.register",
                    idempotency_key,
                    identity,
                    fingerprint,
                    ref.model_dump_json(),
                )
            elif old.result_json != ref.model_dump_json():
                raise ValueError("provider registration receipt mismatch")
            return ref

    def _read(
        self, ref: ProviderProfileRevisionRef
    ) -> tuple[ProviderDescriptor, FoundryProviderAvailability]:
        rows = self._db.all(
            FoundryProviderRevision, where="id=?", values=[_ref_id(ref)]
        )
        if len(rows) != 1 or rows[0].workspace_id != str(ref.workspace_id.root):
            raise ValueError("provider revision unavailable")
        row = rows[0]
        if len(row.descriptor_json) > 128 * 1024:
            raise ValueError("provider descriptor exceeds bound")
        descriptor = ProviderDescriptor.model_validate_json(row.descriptor_json)
        if descriptor.reference != ref or canonical(descriptor) != row.descriptor_json:
            raise ValueError("provider descriptor identity mismatch")
        sources = self._db.all(
            FoundrySourceRevision, where="id=?", values=[row.foundry_source_revision_id]
        )
        if len(sources) != 1 or len(sources[0].manifest_json) > 128 * 1024:
            raise ValueError("provider source unavailable")
        stored = sources[0]
        source = SourceManifest.model_validate_json(stored.manifest_json)
        if (
            stored.workspace_id != str(ref.workspace_id.root)
            or stored.revision_id != source.revision_id
            or source.revision_id != descriptor.source_revision
            or source.kind != descriptor.kind
            or canonical(source) != stored.manifest_json
            or stored.id != _id(str(ref.workspace_id.root) + source.revision_id)
        ):
            raise ValueError("provider source identity mismatch")
        self._verify(ref.workspace_id, source)
        states = self._db.all(
            FoundryProviderAvailability, where="id=?", values=[_ref_id(ref)]
        )
        if (
            len(states) != 1
            or states[0].foundry_provider_revision_id != _ref_id(ref)
            or states[0].generation < 0
        ):
            raise ValueError("provider availability unavailable")
        return descriptor, states[0]

    def describe(
        self, actor: Actor, ref: ProviderProfileRevisionRef
    ) -> ProviderDescriptor:
        ref = ProviderProfileRevisionRef.model_validate(ref)
        with self._db.connect(), self._db.transaction():
            self._auth.require_reference(actor, ref, "provider.inspect")
            descriptor, state = self._read(ref)
            if not state.enabled:
                raise ValueError("provider revision disabled")
            return descriptor

    def operations(
        self,
        actor: Actor,
        provider: ProviderProfileRevisionRef,
        kind: Literal["data", "knowledge"],
    ) -> tuple[BindingOperation, ...]:
        descriptor = self.describe(actor, provider)
        if descriptor.kind != kind:
            raise ValueError("provider kind mismatch")
        return descriptor.operations

    def set_enabled(
        self,
        actor: Actor,
        ref: ProviderProfileRevisionRef,
        *,
        expected_generation: int,
        enabled: bool,
        idempotency_key: str,
    ) -> int:
        actor = Actor.model_validate(actor)
        ref = ProviderProfileRevisionRef.model_validate(ref)
        if (
            not isinstance(expected_generation, int)
            or isinstance(expected_generation, bool)
            or expected_generation < 0
            or not isinstance(enabled, bool)
        ):
            raise ValueError("invalid provider availability update")
        with self._db.connect(), self._db.transaction():
            self._auth.require_reference(actor, ref, "provider.manage")
            # Revocation must work even when retained blobs are unavailable.
            rows = self._db.all(
                FoundryProviderRevision, where="id=?", values=[_ref_id(ref)]
            )
            if (
                len(rows) != 1
                or rows[0].workspace_id != str(ref.workspace_id.root)
                or len(rows[0].descriptor_json) > 128 * 1024
                or ProviderDescriptor.model_validate_json(
                    rows[0].descriptor_json
                ).reference
                != ref
            ):
                raise ValueError("provider revision unavailable")
            parsed = ProviderDescriptor.model_validate_json(rows[0].descriptor_json)
            if canonical(parsed) != rows[0].descriptor_json:
                raise ValueError("provider descriptor is not canonical")
            if enabled:
                self._read(ref)
            payload = json.dumps(
                [ref.model_dump(mode="json"), expected_generation, enabled],
                sort_keys=True,
            )
            identity, fingerprint, old = self._request(
                actor,
                ref.workspace_id,
                "provider.availability",
                idempotency_key,
                payload,
            )
            result = json.dumps(
                {
                    "provider": ref.model_dump(mode="json"),
                    "generation": expected_generation + 1,
                },
                sort_keys=True,
            )
            if old is not None:
                # Historical receipt only; never replay the state mutation.
                if old.result_json != result:
                    raise ValueError("provider availability receipt mismatch")
                return expected_generation + 1
            with self._db.cursor() as cursor:
                self._db.execute_update_returning(
                    cursor,
                    "UPDATE foundry_provider_availability SET generation=generation+1,enabled=? WHERE id=? AND foundry_provider_revision_id=? AND generation=? RETURNING generation",
                    [enabled, _ref_id(ref), _ref_id(ref), expected_generation],
                )
                updated = cursor.fetchone()
            if not updated:
                raise ValueError("provider availability generation conflict")
            self._record(
                actor,
                ref,
                "provider.availability",
                idempotency_key,
                identity,
                fingerprint,
                result,
            )
            return expected_generation + 1
