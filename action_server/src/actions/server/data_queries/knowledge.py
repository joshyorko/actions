"""Bounded, Workspace-scoped local knowledge collections.

The provider receives only operator-bound local files. Callers supply neither
paths nor SQL. Collection identity and source digest are provenance, not access
grants; every operation checks the injected authorization boundary.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from actions.server.run_outputs.types import Actor, canonical_uuid


class _Value(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class KnowledgeField(_Value):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: Literal["text", "integer", "number", "boolean"]


class KnowledgeSchema(_Value):
    version: Literal[1] = 1
    fields: tuple[KnowledgeField, ...] = Field(min_length=1, max_length=32)

    @field_validator("fields")
    @classmethod
    def unique_field_names(cls, fields: tuple[KnowledgeField, ...]):
        names = [field.name for field in fields]
        if len(names) != len(set(names)):
            raise ValueError("knowledge schema field names must be unique")
        return fields


class KnowledgeDocument(_Value):
    document_id: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=16384)
    values: dict[str, str | int | float | bool] = Field(default_factory=dict, max_length=32)
    metadata: dict[str, str] = Field(default_factory=dict, max_length=32)


class KnowledgeHit(_Value):
    document: KnowledgeDocument
    score: int = Field(ge=1)


class KnowledgeResult(_Value):
    data_schema: KnowledgeSchema
    workspace_id: str
    collection_id: str
    source_version: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provider: Literal["duckdb/v1", "postgresql/v1"]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    hits: tuple[KnowledgeHit, ...]


class KnowledgeDenied(PermissionError):
    """Collection is unknown, revoked, or inaccessible in this Workspace."""


class KnowledgeRejected(ValueError):
    """Input or source failed the bounded local ingestion contract."""


@dataclass(frozen=True)
class LocalCollection:
    workspace_id: str
    collection_id: str
    root: Path
    files: tuple[str, ...]
    schema: KnowledgeSchema
    source_version: str
    format: Literal["documents", "csv"]
    revoked: bool = False


class KnowledgeAuthorizer(Protocol):
    def can_read(self, actor: Actor, workspace_id: str, collection_id: str) -> bool:
        """Check current persisted read authority; references never grant it."""


    def can_manage(self, actor: Actor, workspace_id: str, collection_id: str) -> bool:
        """Check current persisted collection-management authority."""


class LocalKnowledgeIngestor(Protocol):
    def ingest(self, binding: LocalCollection) -> tuple[KnowledgeDocument, ...]: ...


class KnowledgeProvider(Protocol):
    kind: Literal["duckdb/v1", "postgresql/v1"]

    def publish(
        self, binding: LocalCollection, documents: tuple[KnowledgeDocument, ...]
    ) -> None: ...

    def documents(self, binding: LocalCollection) -> tuple[KnowledgeDocument, ...]: ...

    def revoke(self, binding: LocalCollection) -> None: ...


class LocalFilesKnowledgeProvider:
    """Read bounded operator-selected UTF-8 documents or CSV rows."""

    def __init__(self, *, max_files: int = 128, max_bytes: int = 4 * 1024 * 1024):
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.max_documents = 10000

    def ingest(self, binding: LocalCollection) -> tuple[KnowledgeDocument, ...]:
        if len(binding.files) > self.max_files or not binding.files:
            raise KnowledgeRejected("invalid collection file count")
        root = binding.root.resolve(strict=True)
        payloads: list[tuple[str, bytes]] = []
        total_bytes = 0
        for relative in binding.files:
            candidate = Path(relative)
            if (
                candidate.is_absolute()
                or ".." in candidate.parts
                or not candidate.parts
            ):
                raise KnowledgeRejected("source file escapes collection root")
            path = root.joinpath(candidate)
            if path.is_symlink():
                raise KnowledgeRejected("source symlinks are not accepted")
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise KnowledgeRejected("source file escapes collection root")
            data = resolved.read_bytes()
            total_bytes += len(data)
            if total_bytes > self.max_bytes:
                raise KnowledgeRejected("collection byte limit exceeded")
            payloads.append((candidate.as_posix(), data))
        digest = hashlib.sha256()
        for name, data in sorted(payloads):
            digest.update(name.encode("utf-8") + b"\0" + data + b"\0")
        if "sha256:" + digest.hexdigest() != binding.source_version:
            raise KnowledgeRejected("collection source version mismatch")
        try:
            if binding.format == "documents":
                docs = tuple(
                    KnowledgeDocument(
                        document_id=name,
                        text=data.decode("utf-8"),
                    )
                    for name, data in sorted(payloads)
                )
            else:
                docs = self._csv_documents(binding, payloads)
        except KnowledgeRejected:
            raise
        except (UnicodeDecodeError, csv.Error, ValueError):
            raise KnowledgeRejected("collection source is invalid") from None
        if len(docs) > self.max_documents:
            raise KnowledgeRejected("collection document limit exceeded")
        return docs

    @staticmethod
    def _csv_documents(
        binding: LocalCollection, payloads: list[tuple[str, bytes]]
    ) -> tuple[KnowledgeDocument, ...]:
        names = tuple(field.name for field in binding.schema.fields)
        documents = []
        for filename, data in sorted(payloads):
            reader = csv.DictReader(data.decode("utf-8-sig").splitlines())
            if tuple(reader.fieldnames or ()) != names:
                raise KnowledgeRejected("CSV header does not match typed schema")
            for line, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise KnowledgeRejected("CSV row does not match typed schema")
                values = {
                    field.name: _parse_scalar(row[field.name], field.kind)
                    for field in binding.schema.fields
                }
                text = " ".join(f"{name}: {values[name]}" for name in names)
                documents.append(
                    KnowledgeDocument(
                        document_id=f"{filename}#{line}",
                        text=text,
                        values=values,
                        metadata={"source_file": filename, "source_row": str(line)},
                    )
                )
        return tuple(documents)


def _parse_scalar(value: str, kind: str) -> str | int | float | bool:
    if kind == "text":
        return value
    if kind == "integer":
        if not re.fullmatch(r"-?(0|[1-9][0-9]*)", value):
            raise KnowledgeRejected("CSV value does not match typed schema")
        return int(value)
    if kind == "number":
        try:
            number = float(value)
        except ValueError:
            raise KnowledgeRejected("CSV value does not match typed schema") from None
        if not math.isfinite(number):
            raise KnowledgeRejected("CSV value does not match typed schema")
        return number
    if kind == "boolean":
        if value not in ("true", "false"):
            raise KnowledgeRejected("CSV value does not match typed schema")
        return value == "true"
    raise KnowledgeRejected("unsupported typed schema field")


def _schema_json(schema: KnowledgeSchema) -> str:
    return json.dumps(schema.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


class DuckDBKnowledgeProvider:
    """Local DuckDB-backed collection store; SQL is fixed and parameterized."""

    kind: Literal["duckdb/v1"] = "duckdb/v1"

    def __init__(self, database: Path, *, max_documents: int = 10000):
        self._database = database
        self._max_documents = max_documents

    def publish(
        self, binding: LocalCollection, documents: tuple[KnowledgeDocument, ...]
    ) -> None:
        self._validate_count(documents)
        connection = self._connect()
        try:
            self._create_tables(connection)
            connection.execute("BEGIN TRANSACTION")
            existing = connection.execute(
                "SELECT revoked FROM actions_knowledge_collections WHERE workspace_id = ? AND collection_id = ?",
                [binding.workspace_id, binding.collection_id],
            ).fetchone()
            if existing is not None and existing[0]:
                raise KnowledgeDenied("knowledge collection unavailable")
            connection.execute(
                "DELETE FROM actions_knowledge_documents WHERE workspace_id = ? AND collection_id = ?",
                [binding.workspace_id, binding.collection_id],
            )
            connection.execute(
                "DELETE FROM actions_knowledge_collections WHERE workspace_id = ? AND collection_id = ?",
                [binding.workspace_id, binding.collection_id],
            )
            connection.execute(
                "INSERT INTO actions_knowledge_collections VALUES (?, ?, ?, ?, false)",
                [binding.workspace_id, binding.collection_id, binding.source_version, _schema_json(binding.schema)],
            )
            connection.executemany(
                "INSERT INTO actions_knowledge_documents VALUES (?, ?, ?, ?, ?, ?, ?)",
                [self._row(binding, document) for document in documents],
            )
            connection.execute("COMMIT")
        except KnowledgeDenied:
            connection.execute("ROLLBACK")
            raise
        except KnowledgeRejected:
            connection.execute("ROLLBACK")
            raise
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except Exception:
                pass
            raise KnowledgeRejected("knowledge provider unavailable") from None
        finally:
            connection.close()

    def documents(self, binding: LocalCollection) -> tuple[KnowledgeDocument, ...]:
        connection = self._connect()
        try:
            self._create_tables(connection)
            collection = connection.execute(
                "SELECT source_version, schema_json, revoked FROM actions_knowledge_collections WHERE workspace_id = ? AND collection_id = ?",
                [binding.workspace_id, binding.collection_id],
            ).fetchone()
            self._check_collection(binding, collection)
            rows = connection.execute(
                "SELECT document_id, text, values_json, metadata_json FROM actions_knowledge_documents WHERE workspace_id = ? AND collection_id = ? AND source_version = ? ORDER BY document_id LIMIT ?",
                [binding.workspace_id, binding.collection_id, binding.source_version, self._max_documents + 1],
            ).fetchall()
            if len(rows) > self._max_documents:
                raise KnowledgeRejected("collection document limit exceeded")
            return tuple(self._document(row) for row in rows)
        except (KnowledgeDenied, KnowledgeRejected):
            raise
        except Exception:
            raise KnowledgeRejected("knowledge provider unavailable") from None
        finally:
            connection.close()

    def revoke(self, binding: LocalCollection) -> None:
        connection = self._connect()
        try:
            self._create_tables(connection)
            connection.execute("BEGIN TRANSACTION")
            collection = connection.execute(
                "SELECT source_version, schema_json, revoked FROM actions_knowledge_collections WHERE workspace_id = ? AND collection_id = ?",
                [binding.workspace_id, binding.collection_id],
            ).fetchone()
            self._check_collection(binding, collection)
            connection.execute(
                "UPDATE actions_knowledge_collections SET revoked = true WHERE workspace_id = ? AND collection_id = ?",
                [binding.workspace_id, binding.collection_id],
            )
            connection.execute("COMMIT")
        except KnowledgeDenied:
            connection.execute("ROLLBACK")
            raise
        except KnowledgeRejected:
            connection.execute("ROLLBACK")
            raise
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except Exception:
                pass
            raise KnowledgeRejected("knowledge provider unavailable") from None
        finally:
            connection.close()

    def _connect(self):
        try:
            import duckdb

            return duckdb.connect(
                str(self._database),
                config={"threads": 1, "memory_limit": "64MB", "enable_external_access": False},
            )
        except Exception:
            raise KnowledgeRejected("knowledge provider unavailable") from None

    @staticmethod
    def _create_tables(connection) -> None:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS actions_knowledge_collections (workspace_id VARCHAR, collection_id VARCHAR, source_version VARCHAR, schema_json VARCHAR, revoked BOOLEAN, PRIMARY KEY (workspace_id, collection_id))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS actions_knowledge_documents (workspace_id VARCHAR, collection_id VARCHAR, source_version VARCHAR, document_id VARCHAR, text VARCHAR, values_json VARCHAR, metadata_json VARCHAR, PRIMARY KEY (workspace_id, collection_id, document_id))"
        )

    def _validate_count(self, documents: tuple[KnowledgeDocument, ...]) -> None:
        if len(documents) > self._max_documents:
            raise KnowledgeRejected("collection document limit exceeded")

    @staticmethod
    def _row(binding: LocalCollection, document: KnowledgeDocument) -> list[str]:
        return [
            binding.workspace_id,
            binding.collection_id,
            binding.source_version,
            document.document_id,
            document.text,
            json.dumps(document.values, sort_keys=True, separators=(",", ":")),
            json.dumps(document.metadata, sort_keys=True, separators=(",", ":")),
        ]

    @staticmethod
    def _check_collection(binding: LocalCollection, row) -> None:
        if row is None:
            raise KnowledgeRejected("collection has not been ingested")
        if row[2]:
            raise KnowledgeDenied("knowledge collection unavailable")
        if row[0] != binding.source_version or row[1] != _schema_json(binding.schema):
            raise KnowledgeRejected("collection source version is not ingested")

    @staticmethod
    def _document(row) -> KnowledgeDocument:
        try:
            return KnowledgeDocument(
                document_id=row[0],
                text=row[1],
                values=json.loads(row[2]),
                metadata=json.loads(row[3]),
            )
        except Exception:
            raise KnowledgeRejected("stored knowledge document is invalid") from None


class PostgreSQLKnowledgeProvider:
    """PostgreSQL-backed service store with static parameterized statements."""

    kind: Literal["postgresql/v1"] = "postgresql/v1"

    def __init__(self, dsn: str, *, max_documents: int = 10000):
        self._dsn = dsn
        self._max_documents = max_documents

    def publish(
        self, binding: LocalCollection, documents: tuple[KnowledgeDocument, ...]
    ) -> None:
        self._validate_count(documents)
        connection = self._connect()
        try:
            self._create_tables(connection)
            with connection.transaction():
                connection.execute(
                    "DELETE FROM actions_knowledge_documents WHERE workspace_id = %s AND collection_id = %s",
                    (binding.workspace_id, binding.collection_id),
                )
                row = connection.execute(
                    "INSERT INTO actions_knowledge_collections (workspace_id, collection_id, source_version, schema_json, revoked) VALUES (%s, %s, %s, %s, false) ON CONFLICT (workspace_id, collection_id) DO UPDATE SET source_version = EXCLUDED.source_version, schema_json = EXCLUDED.schema_json WHERE actions_knowledge_collections.revoked = false RETURNING revoked",
                    (binding.workspace_id, binding.collection_id, binding.source_version, _schema_json(binding.schema)),
                ).fetchone()
                if row is None:
                    raise KnowledgeDenied("knowledge collection unavailable")
                with connection.cursor() as cursor:
                    cursor.executemany(
                        "INSERT INTO actions_knowledge_documents VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        [tuple(self._row(binding, document)) for document in documents],
                    )
        except (KnowledgeDenied, KnowledgeRejected):
            raise
        except Exception:
            raise KnowledgeRejected("knowledge provider unavailable") from None
        finally:
            connection.close()

    def documents(self, binding: LocalCollection) -> tuple[KnowledgeDocument, ...]:
        connection = self._connect()
        try:
            self._create_tables(connection)
            collection = connection.execute(
                "SELECT source_version, schema_json, revoked FROM actions_knowledge_collections WHERE workspace_id = %s AND collection_id = %s",
                (binding.workspace_id, binding.collection_id),
            ).fetchone()
            DuckDBKnowledgeProvider._check_collection(binding, collection)
            rows = connection.execute(
                "SELECT document_id, text, values_json, metadata_json FROM actions_knowledge_documents WHERE workspace_id = %s AND collection_id = %s AND source_version = %s ORDER BY document_id LIMIT %s",
                (binding.workspace_id, binding.collection_id, binding.source_version, self._max_documents + 1),
            ).fetchall()
            if len(rows) > self._max_documents:
                raise KnowledgeRejected("collection document limit exceeded")
            return tuple(DuckDBKnowledgeProvider._document(row) for row in rows)
        except (KnowledgeDenied, KnowledgeRejected):
            raise
        except Exception:
            raise KnowledgeRejected("knowledge provider unavailable") from None
        finally:
            connection.close()

    def revoke(self, binding: LocalCollection) -> None:
        connection = self._connect()
        try:
            self._create_tables(connection)
            with connection.transaction():
                collection = connection.execute(
                    "SELECT source_version, schema_json, revoked FROM actions_knowledge_collections WHERE workspace_id = %s AND collection_id = %s FOR UPDATE",
                    (binding.workspace_id, binding.collection_id),
                ).fetchone()
                DuckDBKnowledgeProvider._check_collection(binding, collection)
                connection.execute(
                    "UPDATE actions_knowledge_collections SET revoked = true WHERE workspace_id = %s AND collection_id = %s",
                    (binding.workspace_id, binding.collection_id),
                )
        except (KnowledgeDenied, KnowledgeRejected):
            raise
        except Exception:
            raise KnowledgeRejected("knowledge provider unavailable") from None
        finally:
            connection.close()

    def _connect(self):
        try:
            import psycopg

            return psycopg.connect(self._dsn, connect_timeout=2, autocommit=True)
        except Exception:
            raise KnowledgeRejected("knowledge provider unavailable") from None

    @staticmethod
    def _create_tables(connection) -> None:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS actions_knowledge_collections (workspace_id text NOT NULL, collection_id text NOT NULL, source_version text NOT NULL, schema_json text NOT NULL, revoked boolean NOT NULL, PRIMARY KEY (workspace_id, collection_id))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS actions_knowledge_documents (workspace_id text NOT NULL, collection_id text NOT NULL, source_version text NOT NULL, document_id text NOT NULL, text text NOT NULL, values_json text NOT NULL, metadata_json text NOT NULL, PRIMARY KEY (workspace_id, collection_id, document_id))"
        )

    def _validate_count(self, documents: tuple[KnowledgeDocument, ...]) -> None:
        if len(documents) > self._max_documents:
            raise KnowledgeRejected("collection document limit exceeded")

    @staticmethod
    def _row(binding: LocalCollection, document: KnowledgeDocument) -> list[str]:
        return DuckDBKnowledgeProvider._row(binding, document)


class KnowledgeCollectionService:
    """Deterministic lexical search over explicitly bound local collections."""

    def __init__(
        self,
        authorizer: KnowledgeAuthorizer,
        provider: KnowledgeProvider,
        bindings: tuple[LocalCollection, ...],
        ingestor: LocalKnowledgeIngestor | None = None,
    ):
        self._authorizer = authorizer
        self._provider = provider
        self._ingestor = ingestor or LocalFilesKnowledgeProvider()
        self._bindings = {}
        for binding in bindings:
            key = (binding.workspace_id, binding.collection_id)
            if key in self._bindings:
                raise ValueError("duplicate Workspace collection binding")
            canonical_uuid(binding.workspace_id)
            canonical_uuid(binding.collection_id)
            if re.fullmatch(r"sha256:[0-9a-f]{64}", binding.source_version) is None:
                raise ValueError("collection source version must be a SHA-256 digest")
            self._bindings[key] = binding

    def ingest(self, actor: Actor, workspace_id: str, collection_id: str) -> int:
        binding = self._authorized_binding(actor, workspace_id, collection_id)
        if binding.revoked:
            raise KnowledgeDenied("knowledge collection unavailable")
        documents = self._ingestor.ingest(binding)
        self._provider.publish(binding, documents)
        return len(documents)

    def revoke(self, actor: Actor, workspace_id: str, collection_id: str) -> None:
        binding = self._authorized_binding(actor, workspace_id, collection_id)
        if not self._authorizer.can_manage(actor, workspace_id, collection_id):
            raise KnowledgeDenied("knowledge collection unavailable")
        self._provider.revoke(binding)
        self._bindings[(workspace_id, collection_id)] = replace(binding, revoked=True)

    def search(
        self,
        actor: Actor,
        workspace_id: str,
        collection_id: str,
        query: str,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> KnowledgeResult:
        binding = self._authorized_binding(actor, workspace_id, collection_id)
        if not isinstance(query, str) or not 1 <= len(query) <= 512:
            raise KnowledgeRejected("query must contain 1 to 512 characters")
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
            or offset > 100000
            or isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            raise KnowledgeRejected("bounded integer page offset/limit required")
        if binding.revoked:
            raise KnowledgeDenied("knowledge collection unavailable")
        terms = tuple(dict.fromkeys(re.findall(r"[\w-]+", query.casefold())))
        if not terms:
            raise KnowledgeRejected("query contains no searchable terms")
        docs = self._provider.documents(binding)
        ranked = []
        for doc in docs:
            haystack = (doc.text + " " + " ".join(doc.metadata.values())).casefold()
            score = sum(haystack.count(term) for term in terms)
            if score:
                ranked.append(KnowledgeHit(document=doc, score=score))
        ranked.sort(key=lambda hit: (-hit.score, hit.document.document_id))
        return KnowledgeResult(
            data_schema=binding.schema,
            workspace_id=workspace_id,
            collection_id=collection_id,
            source_version=binding.source_version,
            provider=self._provider.kind,
            total=len(ranked),
            offset=offset,
            limit=limit,
            hits=tuple(ranked[offset : offset + limit]),
        )

    def _authorized_binding(
        self, actor: Actor, workspace_id: str, collection_id: str
    ) -> LocalCollection:
        canonical_uuid(workspace_id)
        canonical_uuid(collection_id)
        binding = self._bindings.get((workspace_id, collection_id))
        if binding is None or not self._authorizer.can_read(
            actor, workspace_id, collection_id
        ):
            raise KnowledgeDenied("knowledge collection unavailable")
        return binding


def local_source_version(root: Path, files: tuple[str, ...]) -> str:
    """Calculate the immutable content version used by a trusted binding."""
    resolved_root = root.resolve(strict=True)
    digest = hashlib.sha256()
    for relative in sorted(files):
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise KnowledgeRejected("source file escapes collection root")
        path = resolved_root / candidate
        if path.is_symlink():
            raise KnowledgeRejected("source symlinks are not accepted")
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
            raise KnowledgeRejected("source file escapes collection root")
        digest.update(candidate.as_posix().encode("utf-8") + b"\0")
        digest.update(resolved.read_bytes() + b"\0")
    return "sha256:" + digest.hexdigest()
