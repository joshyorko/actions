"""Restricted RFC 8785 canonical JSON for deployment value inputs."""

from __future__ import annotations

import json
import math
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

import rfc8785

_MAX_SAFE_INTEGER = 9_007_199_254_740_991


class CanonicalJSONError(ValueError):
    """Input is outside the actions-canonical-json/v1 domain."""


def _reject_constant(_value: str) -> None:
    raise CanonicalJSONError("non-finite JSON number")


def _parse_integer(token: str) -> int:
    value = int(token)
    if abs(value) > _MAX_SAFE_INTEGER:
        raise CanonicalJSONError("integer outside interoperable JSON range")
    return value


def _parse_float(token: str) -> float:
    try:
        exact = Decimal(token)
        value = float(exact)
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise CanonicalJSONError("invalid JSON number") from exc
    if not math.isfinite(value):
        raise CanonicalJSONError("non-finite JSON number")
    if exact != 0 and value == 0.0:
        raise CanonicalJSONError("nonzero JSON number underflows binary64")
    if exact == exact.to_integral_value() and abs(exact) > _MAX_SAFE_INTEGER:
        raise CanonicalJSONError("integer outside interoperable JSON range")
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalJSONError("duplicate JSON object key")
        result[key] = value
    return result


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise CanonicalJSONError("invalid Unicode scalar value")
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = _normalize(key)
            if normalized_key in normalized:
                raise CanonicalJSONError("object keys collide after NFC normalization")
            normalized[normalized_key] = _normalize(item)
        return normalized
    return value


def parse_canonical_json(raw: bytes) -> Any:
    """Parse strict UTF-8 JSON, applying the v1 restricted input domain."""
    if not isinstance(raw, bytes):
        raise TypeError("canonical JSON input must be bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
        parsed = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_int=_parse_integer,
            parse_float=_parse_float,
            parse_constant=_reject_constant,
        )
        return _normalize(parsed)
    except CanonicalJSONError:
        raise
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as exc:
        raise CanonicalJSONError("invalid canonical JSON input") from exc


def canonicalize_json(raw: bytes) -> bytes:
    """Return exact RFC 8785 bytes after validating the v1 input domain."""
    parsed = parse_canonical_json(raw)
    try:
        return rfc8785.dumps(parsed)
    except (rfc8785.CanonicalizationError, TypeError, ValueError) as exc:
        raise CanonicalJSONError(
            "JSON value cannot be represented canonically"
        ) from exc
