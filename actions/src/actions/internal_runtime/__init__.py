# ruff: noqa: E721 - input primitives require exact types, excluding bool/subclasses
"""Internal asynchronous child Run operations explicitly delegated by Runtime.

The Runtime must install a trusted local transport for the current Action.
These calls do not use HTTP/MCP and do not themselves grant discovery,
execution, result-read, or cancellation authority. There is deliberately no
wait operation and no API for selecting a parent Run or worker.
"""
from __future__ import annotations

import json
import math
import re
from typing import Mapping

from ._context import current_transport
from ._models import ChildResultReference, ChildRunHandle, ChildRunState, ChildRunStatus

MAX_BINDING_NAME_BYTES = 128
MAX_INVOCATION_KEY_BYTES = 128
MAX_INPUT_BYTES = 256 * 1024
MAX_INPUT_DEPTH = 32
MAX_INPUT_NODES = 8192
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)
_SAFE_INTEGER = 2**53 - 1


class ChildRunUnavailable(RuntimeError):
    """No trusted Runtime transport is installed in this Action context."""


class ChildRunContractError(ValueError):
    """The Action supplied an invalid or unbounded child operation."""


def _validate_identifier(value: object, label: str, byte_limit: int) -> str:
    if (
        type(value) is not str  # noqa: E721 -- reject string subclasses
        or len(value.encode("utf-8", errors="surrogatepass")) > byte_limit
        or _IDENTIFIER.fullmatch(value) is None
    ):
        raise ChildRunContractError(f"invalid {label}")
    return value


def _canonical_inputs(inputs: Mapping[str, object]) -> str:
    if type(inputs) is not dict:  # noqa: E721 -- reject custom mappings
        raise ChildRunContractError("child inputs must be a plain JSON object")
    budget = {"nodes": 0, "encoded_bytes": 0}

    def normalize(value: object, depth: int):
        budget["nodes"] += 1
        if budget["nodes"] > MAX_INPUT_NODES or depth > MAX_INPUT_DEPTH:
            raise ChildRunContractError("child inputs exceed structural bounds")
        if value is None or type(value) is bool:
            budget["encoded_bytes"] += 8
            return value
        if type(value) is int:
            if abs(value) > _SAFE_INTEGER:
                raise ChildRunContractError("child input integer outside JSON range")
            budget["encoded_bytes"] += 24
            return value
        if type(value) is float:
            if not math.isfinite(value):
                raise ChildRunContractError("nonfinite child input number")
            budget["encoded_bytes"] += 32
            return 0.0 if value == 0 else value
        if type(value) is str:
            try:
                raw = value.encode("utf-8")
            except UnicodeEncodeError:
                raise ChildRunContractError(
                    "child input contains invalid text"
                ) from None
            budget["encoded_bytes"] += 6 * len(raw) + 2
            if budget["encoded_bytes"] > MAX_INPUT_BYTES:
                raise ChildRunContractError("child inputs exceed byte bound")
            return value
        if type(value) is list:
            return [normalize(item, depth + 1) for item in value]
        if type(value) is dict:
            if any(type(key) is not str for key in value):  # noqa: E721 -- JSON keys
                raise ChildRunContractError("child input keys must be strings")
            result = {}
            for key in sorted(value):
                try:
                    raw_key = key.encode("utf-8")
                except UnicodeEncodeError:
                    raise ChildRunContractError(
                        "child input key is invalid text"
                    ) from None
                budget["encoded_bytes"] += 6 * len(raw_key) + 3
                if budget["encoded_bytes"] > MAX_INPUT_BYTES:
                    raise ChildRunContractError("child inputs exceed byte bound")
                result[key] = normalize(value[key], depth + 1)
            return result
        raise ChildRunContractError("child inputs must contain only JSON values")

    normalized = normalize(inputs, 0)
    try:
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, RecursionError):
        raise ChildRunContractError("child inputs are not bounded JSON") from None
    if len(encoded.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ChildRunContractError("child inputs exceed byte bound")
    return encoded


def submit_child_run(
    binding: str, *, key: str, inputs: Mapping[str, object]
) -> ChildRunHandle:
    """Admit one delegated child asynchronously and return its opaque handle.

    ``binding`` names a host-declared delegation. ``key`` is supplied by the
    Action and must be stable for the same logical child call across parent
    retries. Runtime scopes it to the parent Run and binding and rejects
    conflicting payloads. It is an idempotency label, not an authorization
    token.
    """
    binding = _validate_identifier(
        binding, "delegation binding", MAX_BINDING_NAME_BYTES
    )
    key = _validate_identifier(key, "logical invocation key", MAX_INVOCATION_KEY_BYTES)
    canonical_inputs = _canonical_inputs(inputs)
    handle = current_transport().submit_child_run(binding, key, canonical_inputs)
    if type(handle) is not ChildRunHandle:  # noqa: E721 -- host contract is exact
        raise ChildRunUnavailable("Runtime returned an invalid child Run handle")
    return handle


def child_run_status(handle: ChildRunHandle) -> ChildRunStatus:
    """Read lifecycle and host-authorized result references, never raw output.

    References are opaque and do not grant later reads; Runtime must reauthorize
    each follow-up access.
    """
    if type(handle) is not ChildRunHandle:  # noqa: E721 -- reject caller lookalikes
        raise ChildRunContractError("typed child Run handle required")
    response = current_transport().child_run_status(handle)
    if type(response) is not ChildRunStatus or response.handle != handle:
        raise ChildRunUnavailable("Runtime returned an invalid child Run status")
    return response


def cancel_child_run(handle: ChildRunHandle) -> ChildRunStatus:
    """Request cancellation; ``cancel_pending`` is not terminal confirmation."""
    if type(handle) is not ChildRunHandle:  # noqa: E721 -- reject caller lookalikes
        raise ChildRunContractError("typed child Run handle required")
    response = current_transport().cancel_child_run(handle)
    if type(response) is not ChildRunStatus or response.handle != handle:
        raise ChildRunUnavailable("Runtime returned an invalid child Run status")
    return response


__all__ = [
    "ChildRunHandle",
    "ChildRunState",
    "ChildRunStatus",
    "ChildResultReference",
    "ChildRunContractError",
    "ChildRunUnavailable",
    "cancel_child_run",
    "child_run_status",
    "submit_child_run",
]
