"""Bounded source/v2 decoding. No caller filesystem path or engine SQL."""
from __future__ import annotations

import codecs
import json
import math
import re
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from actions.server.deployments.provider_registry import (
    CsvSourceCodec,
    DecodedSourceObject,
    SourceColumn,
)
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import SealReceipt

Scalar = str | int | float | bool | None
SAFE_INTEGER = 9007199254740991
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
_INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")


class SealedReadRejected(ValueError):
    """Safe bounded failure; never include source values or private locators."""


class ReadBudget:
    def __init__(self, timeout_ms: int, cancelled: threading.Event):
        if (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or not 1 <= timeout_ms <= 30000
        ):
            raise SealedReadRejected("invalid read deadline")
        self.deadline = time.monotonic() + timeout_ms / 1000
        self.cancelled = cancelled

    def check(self) -> None:
        if self.cancelled.is_set():
            raise SealedReadRejected("sealed read cancelled")
        if time.monotonic() >= self.deadline:
            raise SealedReadRejected("sealed read deadline exceeded")

    @contextmanager
    def interruptible(self, interrupt: Callable[[], Any]):
        stopped = threading.Event()

        def watch():
            while not stopped.wait(0.005):
                if self.cancelled.is_set() or time.monotonic() >= self.deadline:
                    try:
                        interrupt()
                    except Exception:
                        pass
                    return

        self.check()
        thread = threading.Thread(
            target=watch, name="sealed-read-deadline", daemon=True
        )
        thread.start()
        try:
            yield
            self.check()
        finally:
            stopped.set()
            thread.join(timeout=2)
            if thread.is_alive():
                raise SealedReadRejected("sealed read cancellation did not settle")


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _string_json_size(value: str) -> int:
    return 2 + sum(
        2
        if c in ('"', "\\", "\b", "\f", "\n", "\r", "\t")
        else 6
        if ord(c) < 32
        else len(c.encode("utf-8"))
        for c in value
    )


def checked_scalar(value: Any, column: SourceColumn, max_field_bytes: int) -> Scalar:
    if value is None:
        if not column.nullable:
            raise SealedReadRejected("required source value is missing")
        return None
    if column.kind == "string":
        if (
            not isinstance(value, str)
            or len(value.encode("utf-8")) > max_field_bytes
            or any(0xD800 <= ord(c) <= 0xDFFF for c in value)
        ):
            raise SealedReadRejected("source string type or bound differs")
    elif column.kind == "integer":
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or abs(value) > SAFE_INTEGER
        ):
            raise SealedReadRejected("source integer outside portable range")
    elif column.kind == "number":
        if (
            not isinstance(value, float)
            or not math.isfinite(value)
            or (value.is_integer() and abs(value) > SAFE_INTEGER)
        ):
            raise SealedReadRejected("source number outside portable range")
        if value == 0.0:
            return 0.0  # One deterministic numeric zero across CSV/Parquet engines.
    elif column.kind == "boolean":
        if not isinstance(value, bool):
            raise SealedReadRejected("source boolean type differs")
    return value


def _csv_scalar(value: str, column: SourceColumn, codec: CsvSourceCodec) -> Scalar:
    if value == codec.null_value:
        return checked_scalar(None, column, codec.max_field_bytes)
    if column.kind == "string":
        actual: Scalar = value
    elif column.kind == "boolean":
        if value not in ("true", "false"):
            raise SealedReadRejected("invalid strict source boolean")
        actual = value == "true"
    elif column.kind == "integer":
        if len(value) > 17 or not _INTEGER.fullmatch(value):
            raise SealedReadRejected("invalid strict source integer")
        actual = int(value)
    else:
        if len(value) > 128 or not _NUMBER.fullmatch(value):
            raise SealedReadRejected("invalid strict source number")
        actual = float(value)
        if actual == 0.0 and Decimal(value) != 0:
            raise SealedReadRejected("source number underflow")
    return checked_scalar(actual, column, codec.max_field_bytes)


@dataclass(frozen=True)
class DecodedRows:
    columns: tuple[SourceColumn, ...]
    rows: tuple[tuple[Scalar, ...], ...]
    decoded_bytes: int


def _csv_records(
    reader, codec: CsvSourceCodec, budget: ReadBudget
) -> Iterator[tuple[str, ...]]:
    """Strict framing with bounds before field/row allocation, no global csv limit."""
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    field: list[str] = []
    fields: list[str] = []
    field_size = 0
    row_size = 0
    state = "start"
    pending_cr = False
    started = False
    records_seen = 0

    def append(c: str):
        nonlocal field_size, row_size
        size = len(c.encode("utf-8"))
        field_size += size
        row_size += size
        field_bound = (
            max(codec.max_field_bytes, 64)
            if records_seen == 0
            else codec.max_field_bytes
        )
        record_bound = (
            max(codec.max_decoded_bytes, 32 * 64)
            if records_seen == 0
            else codec.max_decoded_bytes
        )
        if field_size > field_bound or row_size > record_bound:
            raise SealedReadRejected("source field/record byte bound exceeded")
        field.append(c)

    def finish_field():
        nonlocal field_size
        if len(fields) >= len(codec.columns):
            raise SealedReadRejected("source column bound exceeded")
        fields.append("".join(field))
        field.clear()
        field_size = 0

    while True:
        budget.check()
        raw = reader.read(65536)
        text = decoder.decode(raw, final=not raw)
        for c in text:
            budget.check()
            if pending_cr:
                if c != "\n":
                    raise SealedReadRejected("bare CR outside quoted source field")
                pending_cr = False
                c = "\n"
            elif c == "\r" and state != "quoted":
                pending_cr = True
                continue
            if state == "quoted":
                if c == '"':
                    state = "after-quote"
                else:
                    append(c)
                continue
            if state == "after-quote" and c == '"':
                append(c)
                state = "quoted"
                continue
            if c in (",", "\n"):
                finish_field()
                state = "start"
                started = True
                if c == "\n":
                    if len(fields) != len(codec.columns):
                        raise SealedReadRejected("source column count differs")
                    records_seen += 1
                    yield tuple(fields)
                    fields.clear()
                    row_size = 0
                    started = False
                continue
            if state == "after-quote":
                raise SealedReadRejected("characters after closing source quote")
            started = True
            if c == '"':
                if state != "start":
                    raise SealedReadRejected("quote inside unquoted source field")
                state = "quoted"
            else:
                append(c)
                state = "unquoted"
        if not raw:
            break
    if pending_cr or state == "quoted":
        raise SealedReadRejected("unterminated source record")
    if started or fields or field:
        finish_field()
        if len(fields) != len(codec.columns):
            raise SealedReadRejected("source column count differs")
        yield tuple(fields)


def add_row(
    rows: list[tuple[Scalar, ...]],
    values: tuple[Scalar, ...],
    columns: tuple[SourceColumn, ...],
    total: int,
    codec,
) -> int:
    if len(rows) >= codec.max_rows:
        raise SealedReadRejected("source row bound exceeded")
    # Account for escaped strings and structure before encoding a complete row.
    size = 2 + max(0, len(values) - 1)
    for column, value in zip(columns, values):
        size += (
            len(column.name)
            + 3
            + (
                _string_json_size(value)
                if isinstance(value, str)
                else len(json_bytes(value))
            )
        )
    if total + size + 1 > codec.max_decoded_bytes:
        raise SealedReadRejected("source decoded byte bound exceeded")
    rows.append(values)
    return total + size + 1


def decode_csv(
    blobs: FilesystemOutputProvider,
    seal: SealReceipt,
    obj: DecodedSourceObject,
    budget: ReadBudget,
) -> DecodedRows:
    codec = obj.codec
    if not isinstance(codec, CsvSourceCodec) or (seal.digest, seal.size) != (
        obj.digest,
        obj.size,
    ):
        raise SealedReadRejected("CSV source identity or codec differs")
    budget.check()
    rows: list[tuple[Scalar, ...]] = []
    total = 0
    try:
        with blobs.open(seal.object_ref, seal.digest, seal.size) as reader:
            records = _csv_records(reader, codec, budget)
            header = next(records, None)
            if header != tuple(column.name for column in codec.columns):
                raise SealedReadRejected(
                    "source header differs from exact declared columns"
                )
            for record in records:
                values = tuple(
                    _csv_scalar(value, column, codec)
                    for value, column in zip(record, codec.columns)
                )
                total = add_row(rows, values, codec.columns, total, codec)
        budget.check()
        return DecodedRows(codec.columns, tuple(rows), total)
    except SealedReadRejected:
        raise
    except Exception:
        raise SealedReadRejected("sealed CSV unavailable or invalid") from None
