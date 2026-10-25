"""Closed generated Knowledge operations; validation grants no execution authority.

The primitive result_json field contains a separately validated fixed envelope.
It is not an implicit widening of BindingField or a corpus-publication receipt.
"""
from __future__ import annotations

import math
import re
from typing import Literal

from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef
from actions.server.data_queries.sealed_sources import (
    SAFE_INTEGER,
    SealedReadRejected,
    json_bytes,
)
from actions.server.deployments.logical_bindings import BindingField, BindingOperation
from actions.server.run_outputs.types import output_id_from_handle

_NAME = re.compile(r"[a-z][a-z0-9_-]{0,56}\.(ingest|search)/v1")
_SOURCE = re.compile(r"[a-z][a-z0-9_-]{0,63}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
_SEARCH_FIELDS = (
    BindingField(name="ingestion_handle", kind="string"),
    BindingField(name="limit", kind="integer"),
    BindingField(name="offset", kind="integer"),
    BindingField(name="query", kind="string"),
)
_RESULT_FIELDS = (BindingField(name="result_json", kind="string"),)


def knowledge_contract(operation: BindingOperation) -> Literal["ingest", "search"]:
    """Validate the exact contract independently of any result or host selection."""
    try:
        if type(operation) is not BindingOperation:
            raise ValueError()
        checked = BindingOperation.model_validate_json(
            operation.model_dump_json(warnings="error")
        )
        match = _NAME.fullmatch(checked.name)
        if match is None or checked.result != _RESULT_FIELDS:
            raise ValueError()
        kind: Literal["ingest", "search"] = (
            "ingest" if match.group(1) == "ingest" else "search"
        )
        if checked.effect != (
            "write" if kind == "ingest" else "read"
        ) or checked.parameters != (() if kind == "ingest" else _SEARCH_FIELDS):
            raise ValueError()
        return kind
    except (ValueError, TypeError, AttributeError, UnicodeError, OverflowError):
        raise SealedReadRejected(
            "closed generated Knowledge contract required"
        ) from None


def _bound(value, depth: int, remaining: list[int]) -> None:
    remaining[0] -= 1
    if depth > 8 or remaining[0] < 0:
        raise ValueError()
    kind = type(value)
    if kind is dict:
        if len(value) > 64:
            raise ValueError()
        for key, item in value.items():
            if type(key) is not str:  # noqa: E721 -- built-in JSON only
                raise ValueError()
            remaining[0] -= len(key.encode("utf-8"))
            _bound(item, depth + 1, remaining)
    elif kind is list:
        if len(value) > 10000:
            raise ValueError()
        for item in value:
            _bound(item, depth + 1, remaining)
    elif kind is str:
        if len(value) > remaining[0]:
            raise ValueError()
        remaining[0] -= len(value.encode("utf-8"))
    elif kind is int:
        if abs(value) > SAFE_INTEGER:
            raise ValueError()
    elif kind is float:
        if (
            not math.isfinite(value)
            or (value.is_integer() and abs(value) > SAFE_INTEGER)
            or (value == 0.0 and math.copysign(1.0, value) < 0)
        ):
            raise ValueError()
    elif value is not None and kind is not bool:
        raise ValueError()
    if remaining[0] < 0:
        raise ValueError()


def _digest(value):
    if type(value) is not str or _DIGEST.fullmatch(value) is None:  # noqa: E721 -- built-in JSON only
        raise ValueError()


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:  # noqa: E721 -- reject bool/coercion
        raise ValueError()


def _revision(value):
    if type(value) is not dict or set(value) != {  # noqa: E721 -- exact built-in JSON type required
        "workspace_id",
        "collection_id",
        "revision_id",
    }:  # noqa: E721 -- built-in JSON only
        raise ValueError()
    ref = KnowledgeRevisionRef.model_validate_json(json_bytes(value))
    if ref.model_dump(mode="json") != value:
        raise ValueError()


def _search(value):
    if (
        set(value)
        != {
            "version",
            "revision",
            "ingestionHandle",
            "corpusDigest",
            "query",
            "offset",
            "limit",
            "total",
            "hits",
        }
        or value["version"] != "actions.knowledge-search/v1"
    ):
        raise ValueError()
    output_id_from_handle(value["ingestionHandle"])
    if (
        type(value["query"]) is not str  # noqa: E721 -- exact built-in JSON type required
        or not 1 <= len(value["query"]) <= 512
        or not value["query"].strip()
        or "\x00" in value["query"]
    ):  # noqa: E721 -- built-in JSON only
        raise ValueError()
    _integer(value["offset"], 0, 100000)
    _integer(value["limit"], 1, 100)
    _integer(value["total"], 0, 10000)
    hits = value["hits"]
    if type(hits) is not list or len(hits) != min(  # noqa: E721 -- exact built-in JSON type required
        value["limit"], max(0, value["total"] - value["offset"])
    ):  # noqa: E721 -- built-in JSON only
        raise ValueError()
    seen = set()
    previous = None
    for hit in hits:
        if type(hit) is not dict or set(hit) != {  # noqa: E721 -- exact built-in JSON type required
            "id",
            "source",
            "ordinal",
            "text",
            "values",
        }:  # noqa: E721 -- built-in JSON only
            raise ValueError()
        _digest(hit["id"])
        if type(hit["source"]) is not str or _SOURCE.fullmatch(hit["source"]) is None:  # noqa: E721 -- built-in JSON only
            raise ValueError()
        _integer(hit["ordinal"], 0, SAFE_INTEGER)
        identity = hit["source"], hit["ordinal"]
        if hit["id"] in seen or (previous is not None and identity <= previous):
            raise ValueError()
        previous = identity
        seen.add(hit["id"])
        if (
            type(hit["text"]) is not str  # noqa: E721 -- exact built-in JSON type required
            or not hit["text"]
            or "\x00" in hit["text"]
            or type(hit["values"]) is not dict  # noqa: E721 -- exact built-in JSON type required
        ):  # noqa: E721 -- built-in JSON only
            raise ValueError()
    return len(hits)


def encode_result(operation: BindingOperation, envelope: dict) -> dict[str, str]:
    """Return lossless canonical JSON in the declared primitive result field.

    Byte limit measures the complete outer JSON, including escaped inner JSON.
    Staged ingestion counts as one metadata row; search counts returned hits.
    This validates a shape, not its provenance, grants or publication authority.
    """
    kind = knowledge_contract(operation)
    try:
        if type(envelope) is not dict:  # noqa: E721 -- reject behavioral containers
            raise ValueError()
        _bound(envelope, 0, [operation.max_bytes])
        if kind == "ingest":
            if (
                set(envelope)
                != {"version", "revision", "corpusHandle", "corpusDigest", "status"}
                or envelope["version"] != "actions.knowledge-ingestion-staged/v1"
                or envelope["status"] != "staged"
            ):
                raise ValueError()
            output_id_from_handle(envelope["corpusHandle"])
            rows = 1
        else:
            rows = _search(envelope)
        _revision(envelope["revision"])
        _digest(envelope["corpusDigest"])
        if rows > operation.max_rows:
            raise ValueError()
        result = {"result_json": json_bytes(envelope).decode("utf-8")}
        if len(json_bytes(result)) > operation.max_bytes:
            raise ValueError()
        return result
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        UnicodeError,
        RecursionError,
        OverflowError,
    ):
        raise SealedReadRejected(
            "Knowledge result envelope unavailable or exceeds declared bounds"
        ) from None
