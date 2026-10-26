"""Immutable definitions on common SQL; no runnable Knowledge provider is implied.

The existing provider registry verifies sealed source evidence. This authority
records a definition intent only; ingestion/publication and search remain absent.
"""
from __future__ import annotations

import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from actions.server._database import Database
from actions.server.data_queries.knowledge_values import (
    KnowledgePermission,
    KnowledgeRevisionRef,
    KnowledgeRevisionSpec,
    canonical,
)
from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.deployments.provider_registry import (
    ProviderDescriptor,
    SourceManifest,
)
from actions.server.deployments.provider_registry import canonical as provider_canonical
from actions.server.foundry.knowledge_models import KnowledgeCollectionRevision
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.foundry.provider_models import (
    FoundryProviderRevision,
    FoundrySourceRevision,
)
from actions.server.foundry.provider_registry import SqlProviderRegistry
from actions.server.foundry.provider_registry import _id as _provider_id
from actions.server.foundry.provider_registry import _ref_id
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.service import (
    _canonical,
    _lock_workspace,
    _now,
    _one,
    _transaction,
)
from actions.server.run_outputs.types import Actor

OPERATION = "knowledge.register-definition"


def _id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, "actions.knowledge-definition/v1:" + value))


def _request_id(actor: Actor, reference: KnowledgeRevisionRef, key: str) -> str:
    if not isinstance(key, str) or not 1 <= len(key) <= 128:
        raise ValueError("bounded Knowledge request identity required")
    return _id(
        _canonical(
            [str(reference.workspace_id.root), actor.principal_id, OPERATION, key], 4096
        )
    )


def _fingerprint(
    spec: KnowledgeRevisionSpec, provider: ProviderProfileRevisionRef
) -> str:
    payload = _canonical(
        {
            "specification": json.loads(canonical(spec)),
            "source_provider": provider.model_dump(mode="json"),
        },
        65536,
    )
    return "sha256:" + hashlib.sha256((OPERATION + "\n" + payload).encode()).hexdigest()


def _spec(value: KnowledgeRevisionSpec) -> KnowledgeRevisionSpec:
    try:
        if type(value) is not KnowledgeRevisionSpec:
            raise TypeError("typed definition required")
        raw = value.model_dump_json(warnings="error")
        if len(raw.encode()) > 32768:
            raise ValueError("metadata bound")
        return KnowledgeRevisionSpec.model_validate_json(raw)
    except (ValueError, TypeError):
        raise ValueError("invalid Knowledge definition") from None


class KnowledgeRevisionAuthority:
    def __init__(self, db: Database, providers: SqlProviderRegistry):
        if not isinstance(providers, SqlProviderRegistry) or providers._db is not db:
            raise TypeError("canonical common SQL source registry required")
        self.db, self.providers = db, providers
        self.authorization = SqlFoundryAuthorization(db)

    def _source_metadata(
        self, spec: KnowledgeRevisionSpec, provider: ProviderProfileRevisionRef
    ) -> str:
        if provider.workspace_id != spec.workspace_id:
            raise ValueError("Knowledge source Workspace differs")
        provider_row = _one(self.db, FoundryProviderRevision, _ref_id(provider))
        if len(provider_row.descriptor_json.encode()) > 131072:
            raise ValueError("provider metadata exceeds bound")
        descriptor = ProviderDescriptor.model_validate_json(
            provider_row.descriptor_json
        )
        source_id = _provider_id(str(spec.workspace_id.root) + spec.source_revision)
        source_row = _one(self.db, FoundrySourceRevision, source_id)
        if len(source_row.manifest_json.encode()) > 131072:
            raise ValueError("source metadata exceeds bound")
        source = SourceManifest.model_validate_json(source_row.manifest_json)
        if (
            descriptor.reference != provider
            or descriptor.kind != "knowledge"
            or descriptor.source_revision != spec.source_revision
            or provider_row.workspace_id != str(spec.workspace_id.root)
            or provider_row.foundry_source_revision_id != source_id
            or provider_canonical(descriptor) != provider_row.descriptor_json
            or source_row.workspace_id != str(spec.workspace_id.root)
            or source_row.revision_id != spec.source_revision
            or source.revision_id != spec.source_revision
            or source.kind != "knowledge"
            or source.schema_version != "actions.logical-source/v1"
            or provider_canonical(source) != source_row.manifest_json
            or len(source.objects) > spec.max_source_files
            or sum(obj.size for obj in source.objects) > spec.max_source_bytes
        ):
            raise ValueError("retained Knowledge source identity or bounds differ")
        # Raw v1 sealed Knowledge sources are definition metadata only. This
        # does not select/implement a codec, normalize documents or prove readiness.
        return source_id

    def _receipt(
        self,
        request: FoundryRequest,
        spec: KnowledgeRevisionSpec,
        provider: ProviderProfileRevisionRef,
    ) -> None:
        ref = spec.reference
        if (
            request.id
            != _request_id(
                Actor(principal_id=request.principal_id), ref, request.idempotency_key
            )
            or request.workspace_id != str(ref.workspace_id.root)
            or request.operation != OPERATION
            or request.request_fingerprint != _fingerprint(spec, provider)
            or request.result_json != canonical(ref)
        ):
            raise ValueError("Knowledge registration receipt differs")
        audit = _one(self.db, FoundryAudit, _id(request.id + ":audit"))
        if (
            audit.workspace_id != request.workspace_id
            or audit.deployment_id != ""
            or audit.principal_id != request.principal_id
            or audit.operation != OPERATION
            or audit.foundry_request_id != request.id
            or audit.from_revision_id != ""
            or audit.to_revision_id != ref.revision_id
            or not isinstance(audit.created_ms, str)
            or not audit.created_ms.isascii()
            or not audit.created_ms.isdecimal()
            or not 1 <= len(audit.created_ms) <= 16
            or str(int(audit.created_ms)) != audit.created_ms
            or int(audit.created_ms) <= 0
        ):
            raise ValueError("Knowledge registration audit differs")

    def _load(self, reference: KnowledgeRevisionRef) -> KnowledgeRevisionSpec:
        row = _one(self.db, KnowledgeCollectionRevision, _id(canonical(reference)))
        if (
            len(row.specification_json.encode()) > 32768
            or len(row.source_provider_json.encode()) > 4096
        ):
            raise ValueError("Knowledge definition metadata exceeds bound")
        spec = KnowledgeRevisionSpec.model_validate_json(row.specification_json)
        provider = ProviderProfileRevisionRef.model_validate_json(
            row.source_provider_json
        )
        if (
            row.workspace_id != str(reference.workspace_id.root)
            or row.collection_id != reference.collection_id
            or row.revision_id != reference.revision_id
            or spec.reference != reference
            or canonical(spec) != row.specification_json
            or provider.model_dump_json() != row.source_provider_json
            or row.foundry_source_revision_id != self._source_metadata(spec, provider)
        ):
            raise ValueError("Knowledge definition identity differs")
        self._receipt(
            _one(self.db, FoundryRequest, row.foundry_request_id), spec, provider
        )
        return spec

    def register_definition(
        self,
        actor: Actor,
        specification: KnowledgeRevisionSpec,
        *,
        source_provider: ProviderProfileRevisionRef,
        idempotency_key: str,
    ) -> KnowledgeRevisionRef:
        actor = Actor.model_validate(actor)
        spec = _spec(specification)
        try:
            if type(source_provider) is not ProviderProfileRevisionRef:
                raise TypeError("typed source reference required")
            source_provider = ProviderProfileRevisionRef.model_validate_json(
                source_provider.model_dump_json(warnings="error")
            )
        except (ValueError, TypeError):
            raise ValueError("invalid Knowledge source reference") from None
        ref = spec.reference
        if source_provider.workspace_id != ref.workspace_id:
            raise ValueError("Knowledge source Workspace differs")
        request_id = _request_id(actor, ref, idempotency_key)
        with self.db.connect(), _transaction(self.db):
            _lock_workspace(self.db, str(ref.workspace_id.root))
            self.authorization.require_knowledge(actor, ref, "knowledge.read")
            self.authorization.require_knowledge(actor, ref, "knowledge.manage")
            self.authorization.require_reference(
                actor, source_provider, "knowledge.read"
            )
            # Existing source registry owns inspect authorization and sealed-byte
            # verification. Source absence/disable/tampering fails on replay too.
            self.providers.describe(actor, source_provider)
            source_id = self._source_metadata(spec, source_provider)
            requests = self.db.all(FoundryRequest, where="id=?", values=[request_id])
            rows = self.db.all(
                KnowledgeCollectionRevision, where="id=?", values=[_id(canonical(ref))]
            )
            if requests:
                self._receipt(requests[0], spec, source_provider)
                if self._load(ref) != spec:
                    raise ValueError("Knowledge registration replay differs")
                return ref
            if rows and self._load(ref) != spec:
                raise ValueError("immutable Knowledge definition conflict")
            self.db.insert(
                FoundryRequest(
                    request_id,
                    str(ref.workspace_id.root),
                    actor.principal_id,
                    OPERATION,
                    idempotency_key,
                    _fingerprint(spec, source_provider),
                    canonical(ref),
                )
            )
            self.db.insert(
                FoundryAudit(
                    _id(request_id + ":audit"),
                    str(ref.workspace_id.root),
                    "",
                    actor.principal_id,
                    OPERATION,
                    request_id,
                    "",
                    ref.revision_id,
                    str(_now(self.db)),
                )
            )
            if not rows:
                self.db.insert(
                    KnowledgeCollectionRevision(
                        _id(canonical(ref)),
                        str(ref.workspace_id.root),
                        ref.collection_id,
                        ref.revision_id,
                        canonical(spec),
                        source_id,
                        source_provider.model_dump_json(),
                        request_id,
                    )
                )
            return ref

    def require_revision(
        self,
        actor: Actor,
        reference: KnowledgeRevisionRef,
        permission: KnowledgePermission,
    ) -> KnowledgeRevisionSpec:
        actor = Actor.model_validate(actor)
        try:
            reference = KnowledgeRevisionRef.model_validate_json(
                reference.model_dump_json(warnings="error")
            )
        except (ValueError, TypeError, AttributeError):
            raise ValueError("invalid Knowledge revision reference") from None
        with self.db.connect(), _transaction(self.db):
            self.authorization.require_knowledge(actor, reference, permission)
            return self._load(reference)

    def require_search_ready(
        self, actor: Actor, reference: KnowledgeRevisionRef
    ) -> None:
        self.require_revision(actor, reference, "knowledge.read")
        raise ValueError(
            "Knowledge ingestion/publication and search are not configured"
        )
