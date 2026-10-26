"""Narrow bounded Parquet footer gate, before any native metadata/data call.

CompactProtocol/field IDs follow Apache parquet-format53b8bd8576827080d4382fa457003f45b41cda6e
and thrift f0eb8b84eb5654a949dda7c8ae444a11ca63e632. This is not a general
Parquet reader: unsupported containers/encodings/features fail closed.
"""
from __future__ import annotations

import struct
from typing import Any

from actions.server.data_queries.sealed_sources import ReadBudget, SealedReadRejected
from actions.server.deployments.provider_registry import ParquetSourceCodec

MAX_FOOTER = 1024 * 1024


class _Compact:
    def __init__(self, raw: bytes, budget: ReadBudget):
        if not 1 <= len(raw) <= MAX_FOOTER:
            raise SealedReadRejected("Parquet footer byte bound exceeded")
        self.raw, self.offset, self.nodes, self.budget = raw, 0, 0, budget

    def take(self, size: int) -> bytes:
        self.budget.check()
        if size < 0 or self.offset + size > len(self.raw):
            raise SealedReadRejected("truncated Parquet footer")
        result = self.raw[self.offset : self.offset + size]
        self.offset += size
        return result

    def varint(self) -> int:
        value = 0
        for index in range(10):
            byte = self.take(1)[0]
            if index == 9 and byte > 1:
                raise SealedReadRejected("oversized Parquet integer")
            value |= (byte & 127) << (7 * index)
            if not byte & 128:
                if index and byte == 0:
                    raise SealedReadRejected("nonminimal Parquet integer")
                return value
        raise SealedReadRejected("oversized Parquet integer")

    def integer(self) -> int:
        value = self.varint()
        return (value >> 1) ^ -(value & 1)

    def value(self, kind: int, depth: int, *, field: bool = False) -> Any:
        self.nodes += 1
        if depth > 32 or self.nodes > 100000:
            raise SealedReadRejected("Parquet metadata complexity bound exceeded")
        if kind in (1, 2):
            byte = kind if field else self.take(1)[0]
            if byte not in (1, 2):
                raise SealedReadRejected("invalid Parquet boolean")
            return byte == 1
        if kind == 3:
            return struct.unpack("b", self.take(1))[0]
        if kind in (4, 5, 6):
            value = self.integer()
            bits = {4: 16, 5: 32, 6: 64}[kind]
            if not -(1 << (bits - 1)) <= value < (1 << (bits - 1)):
                raise SealedReadRejected("Parquet integer type bound exceeded")
            return value
        if kind == 7:
            return struct.unpack("<d", self.take(8))[0]
        if kind == 8:
            size = self.varint()
            if size > 65536:
                raise SealedReadRejected("Parquet metadata field bound exceeded")
            return self.take(size)
        if kind == 9:
            header = self.take(1)[0]
            length, element = header >> 4, header & 15
            if length == 15:
                length = self.varint()
            if element not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 12):
                raise SealedReadRejected("unsupported Parquet list element encoding")
            if length > 32768:
                raise SealedReadRejected("Parquet metadata list bound exceeded")
            return [self.value(element, depth + 1) for _ in range(length)]
        if kind == 12:
            values: dict[int, Any] = {}
            previous = 0
            while True:
                header = self.take(1)[0]
                if header == 0:
                    return values
                delta, value_type = header >> 4, header & 15
                identity = previous + delta if delta else self.integer()
                if not 1 <= identity <= 32767 or identity in values:
                    raise SealedReadRejected("duplicate/invalid Parquet metadata field")
                previous = identity
                values[identity] = self.value(value_type, depth + 1, field=True)
        raise SealedReadRejected("unsupported Parquet metadata encoding")


def _integer(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SealedReadRejected("invalid Parquet metadata count")
    return value


def _struct(value: Any) -> dict:
    if not isinstance(value, dict):
        raise SealedReadRejected("invalid Parquet metadata structure")
    return value


def _list(value: Any) -> list:
    if not isinstance(value, list):
        raise SealedReadRejected("invalid Parquet metadata list")
    return value


def validate_footer(
    raw: bytes, data_end: int, codec: ParquetSourceCodec, budget: ReadBudget
) -> int:
    parser = _Compact(raw, budget)
    meta = _struct(parser.value(12, 0))
    if (
        parser.offset != len(raw)
        or set(meta) - {1, 2, 3, 4, 5, 6, 7}
        or _integer(meta.get(1)) not in (1, 2)
        or meta.get(5)
    ):
        raise SealedReadRejected("unsupported Parquet file metadata")
    schema = _list(meta.get(2))
    if len(schema) != len(codec.columns) + 1:
        raise SealedReadRejected("Parquet must have exact flat columns")
    root = _struct(schema[0])
    if (
        set(root) - {3, 4, 5}
        or not isinstance(root.get(4), bytes)
        or _integer(root.get(5)) != len(codec.columns)
    ):
        raise SealedReadRejected("Parquet root is not flat")
    physical = {"string": 6, "integer": 2, "number": 5, "boolean": 0}
    for column, declaration in zip(codec.columns, schema[1:]):
        leaf = _struct(declaration)
        if (
            set(leaf) - {1, 3, 4, 5, 6, 9, 10}
            or _integer(leaf.get(1)) != physical[column.kind]
            or _integer(leaf.get(3)) not in (0, 1)
            or leaf.get(4) != column.name.encode()
            or _integer(leaf.get(5, 0)) != 0
        ):
            raise SealedReadRejected("Parquet column schema differs")
        converted, logical = leaf.get(6), leaf.get(10)
        if converted is not None:
            _integer(converted)
        if column.kind == "string":
            if (
                converted not in (None, 0)
                or logical not in (None, {1: {}})
                or (converted is None and logical is None)
            ):
                raise SealedReadRejected("Parquet string must be UTF-8")
        elif column.kind == "integer":
            valid_logical = logical is None or (
                isinstance(logical, dict)
                and set(logical) == {10}
                and isinstance(logical[10], dict)
                and set(logical[10]) == {1, 2}
                and _integer(logical[10][1]) == 64
                and logical[10][2] is True
            )
            if converted not in (None, 18) or not valid_logical:
                raise SealedReadRejected("Parquet integer annotation differs")
        elif converted is not None or logical is not None:
            raise SealedReadRejected("unsupported Parquet scalar annotation")
    groups = _list(meta.get(4))
    if len(groups) > codec.max_row_groups:
        raise SealedReadRejected("Parquet row group bound exceeded")
    total_rows = total_bytes = 0
    for group in groups:
        budget.check()
        group = _struct(group)
        if set(group) - {1, 2, 3, 4, 5, 6, 7}:
            raise SealedReadRejected("unsupported Parquet row group")
        rows = _integer(group.get(3))
        total_rows += rows
        if total_rows > codec.max_rows:
            raise SealedReadRejected("source row bound exceeded")
        columns = _list(group.get(1))
        if len(columns) != len(codec.columns):
            raise SealedReadRejected("Parquet row group columns differ")
        group_bytes = 0
        for column, chunk in zip(codec.columns, columns):
            chunk = _struct(chunk)
            # Reject external chunk paths, indexes and encryption before native calls.
            if set(chunk) - {2, 3}:
                raise SealedReadRejected("external/unsupported Parquet chunk metadata")
            metadata = _struct(chunk.get(3))
            if (
                set(metadata) - {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 16}
                or metadata.get(8)
                or _integer(metadata.get(4)) != 0
            ):
                raise SealedReadRejected(
                    "Parquet must be uncompressed without external metadata"
                )
            if (
                _integer(metadata.get(1)) != physical[column.kind]
                or metadata.get(3) != [column.name.encode()]
                or _integer(metadata.get(5)) != rows
            ):
                raise SealedReadRejected("Parquet column metadata differs")
            encodings = _list(metadata.get(2))
            if not encodings or any(
                isinstance(x, bool) or not isinstance(x, int) or x not in (0, 2, 3, 8)
                for x in encodings
            ):
                raise SealedReadRejected("unsupported Parquet page encoding")
            size = _integer(metadata.get(6))
            if size != _integer(metadata.get(7)):
                raise SealedReadRejected("Parquet uncompressed size differs")
            offsets = [_integer(metadata.get(9))]
            if 11 in metadata:
                offsets.append(_integer(metadata[11]))
            if (
                any(not 4 <= offset < data_end for offset in offsets)
                or min(offsets) + size > data_end
            ):
                raise SealedReadRejected("Parquet page extent outside retained data")
            group_bytes += size
            total_bytes += size
            if total_bytes > codec.max_decoded_bytes:
                raise SealedReadRejected("Parquet decoded byte bound exceeded")
        if group_bytes != _integer(group.get(2)):
            raise SealedReadRejected("Parquet row group byte identity differs")
    if total_rows != _integer(meta.get(3)):
        raise SealedReadRejected("Parquet total row identity differs")
    return total_rows
