"""Explicit host-provisioned immutable provider versions; no public authority.

Connection factories are private host configuration. No caller path/DSN/SQL is
accepted. Each operation owns/closes its connection and transaction. These stores
are not Run publication, ingestion scheduling or search-readiness authority.
"""
# Closed wire/scalar checks intentionally reject subclasses and bool-as-int.
# ruff: noqa: E721
from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from actions.server.data_queries.knowledge_normalization import (
    MAX_CORPUS_BYTES,
    VERSION,
    NormalizedKnowledge,
    validate_corpus,
)
from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
from actions.server.data_queries.sealed_sources import (
    ReadBudget,
    SealedReadRejected,
    json_bytes,
)

_TABLES = (
    "CREATE TABLE IF NOT EXISTS actions_knowledge_versions (workspace_id TEXT NOT NULL, collection_id TEXT NOT NULL, revision_id TEXT NOT NULL, corpus_digest TEXT NOT NULL, definition_json TEXT NOT NULL, document_count INTEGER NOT NULL, PRIMARY KEY(workspace_id,collection_id,revision_id))",
    "CREATE TABLE IF NOT EXISTS actions_knowledge_documents (workspace_id TEXT NOT NULL, collection_id TEXT NOT NULL, revision_id TEXT NOT NULL, document_id TEXT NOT NULL, position INTEGER NOT NULL, document_json TEXT NOT NULL, PRIMARY KEY(workspace_id,collection_id,revision_id,document_id), UNIQUE(workspace_id,collection_id,revision_id,position))",
    "CREATE TABLE IF NOT EXISTS actions_knowledge_operations (workspace_id TEXT NOT NULL, collection_id TEXT NOT NULL, operation_id TEXT NOT NULL, revision_id TEXT NOT NULL, corpus_digest TEXT NOT NULL, PRIMARY KEY(workspace_id,collection_id,operation_id))",
)


class _Versions:
    def __init__(self, connect: Callable[[], Any], *, postgres: bool):
        self._connect, self._postgres = connect, postgres

    def _execute(self, connection, sql: str, parameters=()):
        return connection.execute(
            sql.replace("?", "%s") if self._postgres else sql, parameters
        )

    @contextmanager
    def _transaction(self, budget: ReadBudget | None, *, write: bool):
        if budget:
            budget.check()
        connection = self._connect()
        try:
            connection.execute("BEGIN")
            if self._postgres:
                # Read-only version queries never provision or mutate metadata.
                if not write:
                    connection.execute("SET TRANSACTION READ ONLY")
                if budget:
                    import time

                    remaining = max(1, int((budget.deadline - time.monotonic()) * 1000))
                    connection.execute(
                        "SELECT set_config('statement_timeout', %s, true)",
                        (str(remaining),),
                    )
                    connection.execute(
                        "SELECT set_config('lock_timeout', %s, true)", (str(remaining),)
                    )
            if budget:
                interrupt = (
                    connection.cancel if self._postgres else connection.interrupt
                )
                with budget.interruptible(interrupt):
                    yield connection
                    budget.check()
                    connection.execute("COMMIT")
            else:
                yield connection
                connection.execute("COMMIT")
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            connection.close()

    def provision(self) -> None:
        """Operator-only DDL. Never called implicitly by put/read or startup."""
        try:
            with self._transaction(None, write=True) as connection:
                for statement in _TABLES:
                    connection.execute(statement)
        except Exception:
            raise SealedReadRejected(
                "Knowledge provider provisioning unavailable"
            ) from None

    def put(
        self, corpus: NormalizedKnowledge, *, operation_id: str, budget: ReadBudget
    ) -> KnowledgeRevisionRef:
        budget.check()
        spec, documents = validate_corpus(corpus)
        if (
            type(operation_id) is not str
            or not 1 <= len(operation_id) <= 128
            or not operation_id.isascii()
            or not all(c.isalnum() or c in "_-" for c in operation_id)
        ):
            raise SealedReadRejected("invalid Knowledge operation identity")
        ref = spec.reference
        key = (str(ref.workspace_id.root), ref.collection_id, ref.revision_id)
        try:
            with self._transaction(budget, write=True) as connection:
                if self._postgres:
                    # Serialize provider-version writes, including same request ID
                    # targeting different revisions. No second scheduler/authority.
                    connection.execute(
                        "LOCK TABLE actions_knowledge_operations IN SHARE ROW EXCLUSIVE MODE"
                    )
                receipt = self._execute(
                    connection,
                    "SELECT revision_id,corpus_digest FROM actions_knowledge_operations WHERE workspace_id=? AND collection_id=? AND operation_id=?",
                    (*key[:2], operation_id),
                ).fetchone()
                existing = self._execute(
                    connection,
                    "SELECT corpus_digest FROM actions_knowledge_versions WHERE workspace_id=? AND collection_id=? AND revision_id=?",
                    key,
                ).fetchone()
                if receipt is not None and tuple(receipt) != (
                    ref.revision_id,
                    corpus.digest,
                ):
                    raise SealedReadRejected("Knowledge operation replay conflicts")
                if existing is not None:
                    if (
                        existing[0] != corpus.digest
                        or self._read(connection, ref, budget) != corpus
                    ):
                        raise SealedReadRejected(
                            "immutable Knowledge version conflicts"
                        )
                elif receipt is not None:
                    raise SealedReadRejected("Knowledge operation version missing")
                else:
                    self._execute(
                        connection,
                        "INSERT INTO actions_knowledge_versions VALUES (?,?,?,?,?,?)",
                        (
                            *key,
                            corpus.digest,
                            json_bytes(spec.model_dump(mode="json")).decode(),
                            len(documents),
                        ),
                    )
                    for index, doc in enumerate(documents):
                        budget.check()
                        self._execute(
                            connection,
                            "INSERT INTO actions_knowledge_documents VALUES (?,?,?,?,?,?)",
                            (*key, doc["id"], index, json_bytes(doc).decode()),
                        )
                if receipt is None:
                    self._execute(
                        connection,
                        "INSERT INTO actions_knowledge_operations VALUES (?,?,?,?,?)",
                        (*key[:2], operation_id, key[2], corpus.digest),
                    )
        except SealedReadRejected:
            raise
        except Exception:
            raise SealedReadRejected(
                "Knowledge provider version write unavailable"
            ) from None
        return ref

    def _read(
        self, connection, ref: KnowledgeRevisionRef, budget: ReadBudget
    ) -> NormalizedKnowledge:
        key = (str(ref.workspace_id.root), ref.collection_id, ref.revision_id)
        row = self._execute(
            connection,
            "SELECT corpus_digest,definition_json,document_count FROM actions_knowledge_versions WHERE workspace_id=? AND collection_id=? AND revision_id=? AND length(definition_json)<=32768",
            key,
        ).fetchone()
        if row is None or type(row[2]) is not int or not 0 <= row[2] <= 10000:
            raise SealedReadRejected("Knowledge retained version unavailable")
        bytes_expression = (
            "octet_length(convert_to(document_json,'UTF8'))"
            if self._postgres
            else "octet_length(encode(document_json))"
        )
        counts = self._execute(
            connection,
            "SELECT count(*),coalesce(sum("
            + bytes_expression
            + "),0) FROM actions_knowledge_documents WHERE workspace_id=? AND collection_id=? AND revision_id=?",
            key,
        ).fetchone()
        if counts is None or counts[0] != row[2] or counts[1] > MAX_CORPUS_BYTES:
            raise SealedReadRejected("Knowledge retained document bounds differ")
        rows = self._execute(
            connection,
            "SELECT document_id,position,document_json FROM actions_knowledge_documents WHERE workspace_id=? AND collection_id=? AND revision_id=? ORDER BY position",
            key,
        ).fetchall()
        docs = []
        for index, (doc_id, position, raw) in enumerate(rows):
            budget.check()
            doc = json.loads(raw)
            if (
                position != index
                or doc["id"] != doc_id
                or json_bytes(doc).decode() != raw
            ):
                raise SealedReadRejected("Knowledge retained document identity differs")
            docs.append(doc)
        raw = json_bytes(
            {"version": VERSION, "definition": json.loads(row[1]), "documents": docs}
        )
        corpus = NormalizedKnowledge(raw, row[0])
        spec, _ = validate_corpus(corpus)
        if spec.reference != ref:
            raise SealedReadRejected("Knowledge retained revision differs")
        return corpus

    def read(
        self, ref: KnowledgeRevisionRef, *, budget: ReadBudget
    ) -> NormalizedKnowledge:
        try:
            ref = KnowledgeRevisionRef.model_validate_json(
                ref.model_dump_json(warnings="error")
            )
            with self._transaction(budget, write=False) as connection:
                return self._read(connection, ref, budget)
        except SealedReadRejected:
            raise
        except Exception:
            raise SealedReadRejected(
                "Knowledge retained version read unavailable"
            ) from None


class DuckDBKnowledgeVersions(_Versions):
    def __init__(self, connect: Callable[[], Any]):
        super().__init__(connect, postgres=False)


class PostgreSQLKnowledgeVersions(_Versions):
    def __init__(self, connect: Callable[[], Any]):
        super().__init__(connect, postgres=True)
