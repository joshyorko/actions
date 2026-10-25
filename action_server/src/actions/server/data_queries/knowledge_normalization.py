"""Strict retained Knowledge codec; trusted host input, no path or query API.

One UTF8 source object is one document. Typed CSV rows become canonical JSON text
and typed values. All columns are required; literal \\N is rejected, empty string
is a string. No Unicode or newline rewriting is performed. No search readiness.
"""
# Closed wire/scalar checks intentionally reject subclasses and bool-as-int.
# ruff: noqa: E721
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

from actions.server.data_queries.knowledge_values import KnowledgeRevisionSpec
from actions.server.data_queries.sealed_sources import (
    ReadBudget,
    SealedReadRejected,
    _csv_records,
    _csv_scalar,
    json_bytes,
)
from actions.server.deployments.provider_registry import (
    CsvSourceCodec,
    SourceColumn,
    SourceManifest,
)
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import SealReceipt

MAX_CORPUS_BYTES = 8 * 1024 * 1024
VERSION = "actions.knowledge-corpus/v1"


def _digest(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class NormalizedKnowledge:
    """Returned immutable bytes are seal input, not a new blob authority."""

    raw: bytes
    digest: str


class _BoundedReader:
    def __init__(self, reader, size: int):
        self.reader, self.size, self.count = reader, size, 0
        self.digest = hashlib.sha256()

    def read(self, count: int) -> bytes:
        raw = self.reader.read(min(count, self.size - self.count + 1))
        if (
            not isinstance(raw, bytes)
            or self.count + len(raw) > self.size
            or b"\x00" in raw
        ):
            raise SealedReadRejected("Knowledge source bytes differ or contain NUL")
        self.count += len(raw)
        self.digest.update(raw)
        return raw

    def verify(self, digest: str):
        if self.count != self.size or "sha256:" + self.digest.hexdigest() != digest:
            raise SealedReadRejected("Knowledge source seal differs")


def normalize_knowledge(
    spec: KnowledgeRevisionSpec,
    source: SourceManifest,
    blobs: FilesystemOutputProvider,
    seals: Mapping[str, SealReceipt],
    budget: ReadBudget,
) -> NormalizedKnowledge:
    try:
        spec = KnowledgeRevisionSpec.model_validate_json(
            spec.model_dump_json(warnings="error")
        )
        source = SourceManifest.model_validate_json(
            source.model_dump_json(warnings="error")
        )
        if (
            source.kind != "knowledge"
            or source.schema_version != "actions.logical-source/v1"
            or source.revision_id != spec.source_revision
        ):
            raise ValueError()
        if (
            len(source.objects) > spec.max_source_files
            or sum(obj.size for obj in source.objects) > spec.max_source_bytes
        ):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise SealedReadRejected(
            "invalid retained Knowledge source or definition"
        ) from None
    budget.check()
    documents: list[dict] = []
    total = 0

    def append(name, ordinal, text, values):
        nonlocal total
        budget.check()
        if (
            len(documents) >= spec.max_documents
            or not text
            or len(text.encode("utf-8")) > spec.max_document_bytes
        ):
            raise SealedReadRejected("Knowledge document count or byte bound exceeded")
        document = {
            "id": _digest(json_bytes([name, ordinal])),
            "source": name,
            "ordinal": ordinal,
            "text": text,
            "values": values,
        }
        encoded = json_bytes(document)
        if total + len(encoded) + 1 > MAX_CORPUS_BYTES - 32768:
            raise SealedReadRejected("Knowledge corpus byte bound exceeded")
        total += len(encoded) + 1
        documents.append(document)

    for obj in source.objects:
        budget.check()
        seal = seals.get(obj.digest)
        if seal is None or (seal.digest, seal.size) != (obj.digest, obj.size):
            raise SealedReadRejected("retained Knowledge source seal unavailable")
        # Refuse oversized whole-document allocation before opening source.
        if (
            spec.source_format == "utf8-documents/v1"
            and obj.size > spec.max_document_bytes
        ):
            raise SealedReadRejected("Knowledge document byte bound exceeded")
        try:
            with blobs.open(seal.object_ref, seal.digest, seal.size) as stream:
                reader = _BoundedReader(stream, obj.size)
                if spec.source_format == "utf8-documents/v1":
                    parts = []
                    while True:
                        budget.check()
                        part = reader.read(4096)
                        if not part:
                            break
                        parts.append(part)
                    text = b"".join(parts).decode("utf-8", errors="strict")
                    if text.startswith("\ufeff"):
                        raise SealedReadRejected("Knowledge BOM is unsupported")
                    append(obj.name, 0, text, {})
                else:
                    codec = CsvSourceCodec(
                        columns=tuple(
                            SourceColumn(name=f.name, kind=f.kind)
                            for f in spec.document_fields
                        ),
                        max_rows=spec.max_documents,
                        max_decoded_bytes=spec.max_document_bytes,
                        max_field_bytes=spec.max_document_bytes,
                    )
                    records = iter(_csv_records(reader, codec, budget))
                    if next(records, None) != tuple(
                        f.name for f in spec.document_fields
                    ):
                        raise SealedReadRejected("Knowledge CSV header differs")
                    for ordinal, row in enumerate(records):
                        values = {
                            column.name: _csv_scalar(value, column, codec)
                            for column, value in zip(codec.columns, row)
                        }
                        text = json_bytes(values).decode("utf-8")
                        append(obj.name, ordinal, text, values)
                reader.verify(obj.digest)
        except (OSError, UnicodeError):
            raise SealedReadRejected(
                "Knowledge source bytes unavailable or invalid"
            ) from None
    raw = json_bytes(
        {
            "version": VERSION,
            "definition": spec.model_dump(mode="json"),
            "documents": documents,
        }
    )
    budget.check()
    if len(raw) > MAX_CORPUS_BYTES:
        raise SealedReadRejected("Knowledge corpus byte bound exceeded")
    return NormalizedKnowledge(raw, _digest(raw))


def validate_corpus(
    corpus: NormalizedKnowledge,
) -> tuple[KnowledgeRevisionSpec, list[dict]]:
    """Closed deterministic representation check; not issuance or authorization."""
    if (
        type(corpus) is not NormalizedKnowledge
        or type(corpus.raw) is not bytes
        or len(corpus.raw) > MAX_CORPUS_BYTES
        or _digest(corpus.raw) != corpus.digest
    ):
        raise SealedReadRejected("Knowledge corpus bytes or digest differ")
    try:
        value = json.loads(corpus.raw)
        if (
            type(value) is not dict
            or set(value) != {"version", "definition", "documents"}
            or value["version"] != VERSION
            or json_bytes(value) != corpus.raw
        ):
            raise ValueError()
        spec = KnowledgeRevisionSpec.model_validate_json(
            json_bytes(value["definition"])
        )
        documents = value["documents"]
        if type(documents) is not list or len(documents) > spec.max_documents:
            raise ValueError()
        seen = set()
        previous = None
        source_counts: dict[str, int] = {}
        for doc in documents:
            if type(doc) is not dict or set(doc) != {
                "id",
                "source",
                "ordinal",
                "text",
                "values",
            }:
                raise ValueError()
            if (
                type(doc["source"]) is not str
                or re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", doc["source"]) is None
                or type(doc["ordinal"]) is not int
                or doc["ordinal"] < 0
            ):
                raise ValueError()
            identity = (doc["source"], doc["ordinal"])
            if previous is not None and identity <= previous:
                raise ValueError()
            if doc["id"] != _digest(json_bytes(list(identity))) or doc["id"] in seen:
                raise ValueError()
            if doc["ordinal"] != source_counts.get(doc["source"], 0):
                raise ValueError()
            source_counts[doc["source"]] = doc["ordinal"] + 1
            if len(source_counts) > spec.max_source_files:
                raise ValueError()
            previous = identity
            seen.add(doc["id"])
            text = doc["text"]
            if (
                type(text) is not str
                or not text
                or "\x00" in text
                or len(text.encode()) > spec.max_document_bytes
            ):
                raise ValueError()
            values = doc["values"]
            if spec.source_format == "utf8-documents/v1":
                if values != {} or doc["ordinal"] != 0 or text.startswith("\ufeff"):
                    raise ValueError()
            else:
                if (
                    type(values) is not dict
                    or set(values) != {f.name for f in spec.document_fields}
                    or json_bytes(values).decode() != text
                ):
                    raise ValueError()
                from actions.server.data_queries.sealed_sources import checked_scalar

                for field in spec.document_fields:
                    checked = checked_scalar(
                        values[field.name],
                        SourceColumn(name=field.name, kind=field.kind),
                        spec.max_document_bytes,
                    )
                    if json_bytes(checked) != json_bytes(values[field.name]):
                        raise ValueError()
        return spec, documents
    except (
        ValueError,
        TypeError,
        KeyError,
        OverflowError,
        UnicodeError,
        RecursionError,
    ):
        raise SealedReadRejected("invalid canonical Knowledge corpus") from None
