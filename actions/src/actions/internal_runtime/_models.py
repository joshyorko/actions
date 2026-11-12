"""Immutable values for the internal delegated child client."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from enum import Enum

MAX_RESULT_REFERENCE_COUNT = 32
MAX_RESULT_REFERENCE_BYTES = 16 * 1024
_OPAQUE_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}\Z", re.ASCII)
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_MEDIA_TYPE = re.compile(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+\Z", re.ASCII)


class ChildRunState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    CANCEL_PENDING = "cancel_pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ChildRunHandle:
    """Opaque child Run reference; possession grants no read or cancel access."""

    id: str

    def __post_init__(self) -> None:
        if type(self.id) is not str:  # noqa: E721 -- reject string subclasses
            raise ValueError("canonical child handle required")
        try:
            parsed = uuid.UUID(self.id)
        except (ValueError, AttributeError):
            raise ValueError("canonical child handle required") from None
        if str(parsed) != self.id:
            raise ValueError("canonical child handle required")


@dataclass(frozen=True)
class ChildResultReference:
    """Opaque, metadata-only result reference supplied by an authorized host.

    The handle is a reference, not a bearer grant. Runtime must reauthorize any
    later read; raw result bytes are never carried in this value.
    """

    handle: str
    name: str
    media_type: str
    size_bytes: int
    digest: str | None = None

    def __post_init__(self) -> None:
        if (
            type(self.handle) is not str  # noqa: E721 -- reject string subclasses
            or _OPAQUE_REFERENCE.fullmatch(self.handle) is None
        ):
            raise ValueError("bounded opaque result reference required")
        if type(self.name) is not str or not self.name:  # noqa: E721 -- strict text
            raise ValueError("bounded result name required")
        try:
            name_bytes = self.name.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("bounded result name required") from None
        if len(name_bytes) > 256:
            raise ValueError("bounded result name required")
        if (
            type(self.media_type) is not str  # noqa: E721 -- reject string subclasses
            or len(self.media_type) > 128
            or _MEDIA_TYPE.fullmatch(self.media_type) is None
        ):
            raise ValueError("bounded result media type required")
        if (
            type(self.size_bytes) is not int  # noqa: E721 -- bool is not an integer
            or not 0 <= self.size_bytes <= 2**53 - 1
        ):
            raise ValueError("bounded result size required")
        if self.digest is not None and (
            type(self.digest) is not str  # noqa: E721 -- reject string subclasses
            or _DIGEST.fullmatch(self.digest) is None
        ):
            raise ValueError("canonical result digest required")


@dataclass(frozen=True)
class ChildRunStatus:
    """Bounded lifecycle plus authorized result references, never raw bytes."""

    handle: ChildRunHandle
    state: ChildRunState
    result_references: tuple[ChildResultReference, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.handle) is not ChildRunHandle
            or type(self.state) is not ChildRunState
        ):
            raise ValueError("typed child status required")
        if (
            type(self.result_references) is not tuple
            or len(self.result_references) > MAX_RESULT_REFERENCE_COUNT
        ):
            raise ValueError("bounded result reference tuple required")
        if any(type(ref) is not ChildResultReference for ref in self.result_references):
            raise ValueError("typed result references required")
        handles = {ref.handle for ref in self.result_references}
        if len(handles) != len(self.result_references):
            raise ValueError("duplicate result reference handle")
        metadata = [
            {
                "handle": ref.handle,
                "name": ref.name,
                "media_type": ref.media_type,
                "size_bytes": ref.size_bytes,
                "digest": ref.digest,
            }
            for ref in self.result_references
        ]
        metadata_bytes = json.dumps(
            metadata,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(metadata_bytes) > MAX_RESULT_REFERENCE_BYTES:
            raise ValueError("result reference metadata exceeds byte bound")
