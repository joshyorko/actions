"""Private Runtime installation hook for bounded logical read context bytes.

The digest binds bytes supplied by the trusted host; it is not authentication.
Generated Python is trusted developer code, not isolated hostile code. Nothing
here discovers providers or confers authority to query them.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterator, Mapping, Union

Scalar = Union[str, int, float, bool]
_VERSION = "actions.logical-read-context/v1"
_VERSION_V2 = "actions.logical-context/v2"
_MAX_BYTES = 256 * 1024
_MAX_OPERATIONS = 32
_SAFE_INTEGER = 2**53 - 1
_REQUIREMENT = re.compile(r"[a-z][a-z0-9_-]{0,63}")
# The '.scan' suffix counts toward BindingOperation's 64-character name bound.
_OPERATION = re.compile(r"[a-z][a-z0-9_-]{0,58}\.scan/v1")
_INGEST = re.compile(r"[a-z][a-z0-9_-]{0,56}\.ingest/v1")
_SEARCH = re.compile(r"[a-z][a-z0-9_-]{0,56}\.search/v1")
_FIELD = re.compile(r"[a-z][a-z0-9_]{0,63}")
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


@dataclass(frozen=True)
class _Lookup:
    kind: str
    parameters: bytes
    result: bytes


_CURRENT: ContextVar[Mapping[tuple[str, str], _Lookup] | None] = ContextVar(
    "actions_logical_read_context", default=None
)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate context key")
        result[key] = value
    return result


def _integer(raw: str) -> int:
    if len(raw) > 17:
        raise ValueError("nonportable context integer")
    value = int(raw)
    if abs(value) > _SAFE_INTEGER:
        raise ValueError("nonportable context integer")
    return value


def _number(raw: str) -> float:
    if len(raw) > 128:
        raise ValueError("nonportable context number")
    value = float(raw)
    if not math.isfinite(value) or (value.is_integer() and abs(value) > _SAFE_INTEGER):
        raise ValueError("nonportable context number")
    return 0.0 if value == 0.0 else value


def _constant(raw: str):
    raise ValueError("nonfinite context number")


def _name(value: object, pattern: re.Pattern[str]) -> bool:
    return type(value) is str and pattern.fullmatch(value) is not None  # noqa: E721 -- reject behavior-overriding subclasses


def _validate(
    payload: bytes, expected_digest: str
) -> Mapping[tuple[str, str], _Lookup]:
    if (
        type(payload) is not bytes  # noqa: E721 -- immutable built-in bytes only
        or not 1 <= len(payload) <= _MAX_BYTES
        or not _name(expected_digest, _DIGEST)
        or "sha256:" + hashlib.sha256(payload).hexdigest() != expected_digest
    ):
        raise ValueError("logical context integrity rejected")
    value = json.loads(
        payload.decode("utf-8", errors="strict"),
        object_pairs_hook=_pairs,
        parse_int=_integer,
        parse_float=_number,
        parse_constant=_constant,
    )
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "lookups"}
        or value["version"] not in (_VERSION, _VERSION_V2)
        or not isinstance(value["lookups"], list)
        or len(value["lookups"]) > _MAX_OPERATIONS
        or _canonical(value) != payload
    ):
        raise ValueError("logical context schema rejected")
    if value["version"] == _VERSION_V2:
        return _validate_v2(value["lookups"])
    lookups: dict[tuple[str, str], _Lookup] = {}
    for lookup in value["lookups"]:
        if (
            not isinstance(lookup, dict)
            or set(lookup) != {"requirementId", "operation", "rows"}
            or not _name(lookup["requirementId"], _REQUIREMENT)
            or not _name(lookup["operation"], _OPERATION)
            or not isinstance(lookup["rows"], list)
            or len(lookup["rows"]) > 100000
        ):
            raise ValueError("logical lookup schema rejected")
        key = (lookup["requirementId"], lookup["operation"])
        if key in lookups:
            raise ValueError("ambiguous logical lookup")
        kinds: dict[str, type] = {}
        for row in lookup["rows"]:
            if not isinstance(row, dict) or len(row) > 32:
                raise ValueError("flat typed logical row required")
            for name, scalar in row.items():
                if (
                    not _name(name, _FIELD)
                    or type(scalar) not in (str, int, float, bool)
                    or (name in kinds and kinds[name] is not type(scalar))
                ):
                    raise ValueError("flat typed logical value required")
                # UTF-8 canonicalization already rejects surrogate strings;
                # numeric parsers enforce the Runtime's portable scalar bounds.
                kinds[name] = type(scalar)
            if len(kinds) > 32:
                raise ValueError("logical result column bound exceeded")
        lookups[key] = _Lookup("data", b"{}", _canonical(lookup["rows"]))
    return MappingProxyType(lookups)


def _search_parameters(value: object) -> bytes:
    if (
        not isinstance(value, dict)
        or set(value) != {"ingestion_handle", "query", "offset", "limit"}
        or type(value["ingestion_handle"]) is not str  # noqa: E721 -- reject bool/coercion and behavior-overriding subclasses
        or type(value["query"]) is not str  # noqa: E721 -- reject bool/coercion and behavior-overriding subclasses
        or type(value["offset"]) is not int  # noqa: E721 -- reject bool/coercion and behavior-overriding subclasses
        or type(value["limit"]) is not int  # noqa: E721 -- reject bool/coercion and behavior-overriding subclasses
        or not 0 <= value["offset"] <= _SAFE_INTEGER
        or not 1 <= value["limit"] <= _SAFE_INTEGER
    ):
        raise ValueError("prepared Knowledge parameters differ")
    return _canonical(value)


def _json_result(value: object, depth: int = 0) -> None:
    if depth > 8:
        raise ValueError("prepared result depth exceeded")
    if isinstance(value, dict):
        if len(value) > 64:
            raise ValueError("prepared result object exceeded")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("prepared result key rejected")
            _json_result(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 10000:
            raise ValueError("prepared result array exceeded")
        for item in value:
            _json_result(item, depth + 1)
    elif value is not None and type(value) not in (str, int, float, bool):
        raise ValueError("prepared result scalar rejected")
    # JSON parsing/canonical comparison already enforces portable finite numbers
    # and UTF-8. This function is only called with that parsed representation.


def _validate_v2(values: list) -> Mapping[tuple[str, str], _Lookup]:
    lookups: dict[tuple[str, str], _Lookup] = {}
    for value in values:
        if (
            not isinstance(value, dict)
            or set(value)
            != {"requirementId", "operation", "kind", "parameters", "result"}
            or not _name(value["requirementId"], _REQUIREMENT)
        ):
            raise ValueError("logical v2 lookup schema rejected")
        key = value["requirementId"], value["operation"]
        if not isinstance(key[1], str) or key in lookups:
            raise ValueError("ambiguous logical v2 lookup")
        if value["kind"] == "data":
            if value["parameters"] != {}:
                raise ValueError("prepared Data parameters rejected")
            legacy = _canonical(
                {
                    "version": _VERSION,
                    "lookups": [
                        {
                            "requirementId": key[0],
                            "operation": key[1],
                            "rows": value["result"],
                        }
                    ],
                }
            )
            checked = _validate(legacy, "sha256:" + hashlib.sha256(legacy).hexdigest())
            lookups[key] = checked[key]
        elif value["kind"] == "knowledge":
            if _name(key[1], _INGEST):
                if value["parameters"] != {}:
                    raise ValueError("prepared ingestion parameters rejected")
                parameters = b"{}"
            elif _name(key[1], _SEARCH):
                parameters = _search_parameters(value["parameters"])
            else:
                raise ValueError("prepared Knowledge operation rejected")
            if not isinstance(value["result"], dict):
                raise ValueError("prepared Knowledge result object required")
            _json_result(value["result"])
            lookups[key] = _Lookup("knowledge", parameters, _canonical(value["result"]))
        else:
            raise ValueError("prepared logical namespace rejected")
    return MappingProxyType(lookups)


def _knowledge_result(
    requirement_id: str, operation: str, parameters: dict, *, ingest: bool
) -> dict:
    """Private SDK selection hook; never prepare, authorize or execute a query."""
    if not _name(requirement_id, _REQUIREMENT) or not _name(
        operation, _INGEST if ingest else _SEARCH
    ):
        raise ValueError("prepared Knowledge result unavailable")
    try:
        expected = (
            b"{}" if ingest and parameters == {} else _search_parameters(parameters)
        )
        current = _CURRENT.get()
        lookup = (
            current.get((requirement_id, operation)) if current is not None else None
        )
        if (
            lookup is None
            or lookup.kind != "knowledge"
            or lookup.parameters != expected
        ):
            raise ValueError("prepared Knowledge result unavailable")
        return json.loads(lookup.result)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("prepared Knowledge result unavailable") from None


@contextmanager
def install_context(payload: bytes, *, expected_digest: str) -> Iterator[None]:
    """Install exact host context for this execution; always restore prior state.

    Callers must use ``with``. Neither constructing the manager nor importing
    this module reads context, environment, files, credentials or providers.
    """
    try:
        lookups = _validate(payload, expected_digest)
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise ValueError("logical context unavailable or invalid") from None
    token = _CURRENT.set(lookups)
    try:
        yield
    finally:
        _CURRENT.reset(token)


def scan(requirement_id: str, operation: str) -> list[dict[str, Scalar]]:
    """Return fresh rows from one declared eager scan in the current execution.

    Optional null fields are omitted. No parameters, lazy queries or writes are
    supported. An absent context or undeclared lookup raises ValueError.
    """
    if not _name(requirement_id, _REQUIREMENT) or not _name(operation, _OPERATION):
        raise ValueError("logical scan unavailable")
    current = _CURRENT.get()
    rows = current.get((requirement_id, operation)) if current is not None else None
    if rows is None or rows.kind != "data":
        raise ValueError("logical scan unavailable")
    return json.loads(rows.result)
