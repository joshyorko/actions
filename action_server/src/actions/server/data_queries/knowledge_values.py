"""Immutable Knowledge definition intent, not executable collection authority."""
from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import WorkspaceId
from actions.server.run_outputs.types import canonical_uuid

_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
KnowledgePermission = Literal["knowledge.read", "knowledge.manage"]


class _Value(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )


def canonical(value: _Value) -> str:
    result = canonicalize_json(value.model_dump_json().encode("utf-8"))
    if len(result) > 32768:
        raise ValueError("bounded Knowledge metadata required")
    return result.decode("utf-8")


class KnowledgeCollectionRef(_Value):
    workspace_id: WorkspaceId
    collection_id: str

    @field_validator("collection_id")
    @classmethod
    def collection_uuid(cls, value: str) -> str:
        canonical_uuid(value)
        return value


class KnowledgeRevisionRef(KnowledgeCollectionRef):
    revision_id: str

    @field_validator("revision_id")
    @classmethod
    def digest(cls, value: str) -> str:
        if _DIGEST.fullmatch(value) is None:
            raise ValueError("canonical revision digest required")
        return value

    @property
    def collection(self) -> KnowledgeCollectionRef:
        return KnowledgeCollectionRef(
            workspace_id=self.workspace_id, collection_id=self.collection_id
        )


class KnowledgeDocumentField(_Value):
    name: str
    kind: Literal["string", "integer", "number", "boolean"]

    @field_validator("name")
    @classmethod
    def field_name(cls, value: str) -> str:
        if _NAME.fullmatch(value) is None:
            raise ValueError("canonical field name required")
        return value


class KnowledgeRevisionSpec(KnowledgeCollectionRef):
    schema_version: Literal[
        "actions.knowledge-definition/v1"
    ] = "actions.knowledge-definition/v1"
    source_revision: str
    source_format: Literal["utf8-documents/v1", "typed-csv/v1"] = "utf8-documents/v1"
    document_fields: tuple[KnowledgeDocumentField, ...] = Field(
        default=(), max_length=32
    )
    normalizer_contract: Literal[
        "actions.knowledge-normalizer/v1"
    ] = "actions.knowledge-normalizer/v1"
    max_source_files: int = Field(default=128, ge=1, le=128)
    max_source_bytes: int = Field(default=4 * 1024 * 1024, ge=1, le=4 * 1024 * 1024)
    max_documents: int = Field(default=10000, ge=1, le=10000)
    max_document_bytes: int = Field(default=16384, ge=1, le=16384)
    max_query_characters: int = Field(default=512, ge=1, le=512)
    max_offset: int = Field(default=100000, ge=0, le=100000)
    max_results: int = Field(default=100, ge=1, le=100)
    max_result_bytes: int = Field(default=1024 * 1024, ge=1, le=4 * 1024 * 1024)
    timeout_ms: int = Field(default=30000, ge=1, le=30000)

    @field_validator("source_revision")
    @classmethod
    def source_digest(cls, value: str) -> str:
        if _DIGEST.fullmatch(value) is None:
            raise ValueError("canonical source digest required")
        return value

    @model_validator(mode="after")
    def shape(self):
        names = [field.name for field in self.document_fields]
        if len(names) != len(set(names)):
            raise ValueError("unique document fields required")
        # CSV physical column order is semantic and remains in identity.
        if bool(self.document_fields) != (self.source_format == "typed-csv/v1"):
            raise ValueError("typed CSV requires fields; plain documents have none")
        if self.max_document_bytes > self.max_source_bytes:
            raise ValueError("document budget exceeds source budget")
        return self

    @property
    def reference(self) -> KnowledgeRevisionRef:
        revision = (
            "sha256:"
            + hashlib.sha256(
                ("actions.knowledge-revision/v1\n" + canonical(self)).encode()
            ).hexdigest()
        )
        return KnowledgeRevisionRef(
            workspace_id=self.workspace_id,
            collection_id=self.collection_id,
            revision_id=revision,
        )


def knowledge_grant_subject(
    reference: KnowledgeCollectionRef | KnowledgeRevisionRef,
) -> str:
    """Canonical scoped grant subject; no implicit Workspace/Data inheritance."""
    checked: KnowledgeCollectionRef | KnowledgeRevisionRef
    if type(reference) is KnowledgeRevisionRef:
        checked = KnowledgeRevisionRef.model_validate_json(reference.model_dump_json())
    elif type(reference) is KnowledgeCollectionRef:
        checked = KnowledgeCollectionRef.model_validate_json(
            reference.model_dump_json()
        )
    else:
        raise TypeError("exact Knowledge reference required")
    return (
        type(checked).__name__
        + ":sha256:"
        + hashlib.sha256(canonical(checked).encode()).hexdigest()
    )
