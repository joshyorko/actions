"""Fixed read-only exact-object scan over verified source/v2 bytes.

No caller SQL, path or connection string. Python budgets and native connection
limits are not a hostile native-process isolation boundary.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from actions.server.data_queries.parquet_gate import MAX_FOOTER, validate_footer
from actions.server.data_queries.sealed_sources import (
    DecodedRows,
    ReadBudget,
    SealedReadRejected,
    _string_json_size,
    add_row,
    checked_scalar,
    decode_csv,
    json_bytes,
)
from actions.server.deployments.logical_bindings import BindingOperation
from actions.server.deployments.provider_registry import (
    CsvSourceCodec,
    DecodedSourceObject,
    ParquetSourceCodec,
    ProviderDescriptor,
    SourceManifest,
    require_executable_source,
)
from actions.server.foundry.provider_catalog import SourceSealRecord
from actions.server.foundry.provider_config import DuckDBHost, ProviderHostConfig
from actions.server.foundry.provider_registry import SqlProviderRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor, SealReceipt


def _connect(*, parquet: Path | None = None):
    import duckdb

    connection = duckdb.connect(
        ":memory:",
        config={
            "threads": "1",
            "memory_limit": "64MB",
            "temp_directory": "",
            "autoload_known_extensions": "false",
            "autoinstall_known_extensions": "false",
            "preserve_insertion_order": "true",
        },
    )
    try:
        # DuckDB1.4.1 permits allowed_paths only after connection creation.
        # No native file/metadata query runs until this exact allowlist is locked.
        connection.execute("SET allowed_paths = ?", [[str(parquet)] if parquet else []])
        connection.execute("SET enable_external_access=false")
        connection.execute("SET lock_configuration=true")
        return connection
    except Exception:
        connection.close()
        raise SealedReadRejected("bounded DuckDB unavailable") from None


def decode_parquet(
    blobs: FilesystemOutputProvider,
    seal: SealReceipt,
    obj: DecodedSourceObject,
    budget: ReadBudget,
) -> DecodedRows:
    codec = obj.codec
    if not isinstance(codec, ParquetSourceCodec) or (seal.digest, seal.size) != (
        obj.digest,
        obj.size,
    ):
        raise SealedReadRejected("Parquet source identity or codec differs")
    budget.check()
    try:
        with tempfile.TemporaryDirectory(prefix="actions-sealed-parquet-") as directory:
            path = Path(directory) / "source.parquet"
            measured = hashlib.sha256()
            with blobs.open(
                seal.object_ref, seal.digest, seal.size
            ) as reader, path.open("xb") as target:
                while True:
                    budget.check()
                    chunk = reader.read(65536)
                    if not chunk:
                        break
                    measured.update(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            path.chmod(0o400)
            if (
                "sha256:" + measured.hexdigest() != obj.digest
                or path.stat().st_size != obj.size
                or obj.size < 12
            ):
                raise SealedReadRejected("Parquet copy identity differs")
            with path.open("rb") as raw:
                if raw.read(4) != b"PAR1":
                    raise SealedReadRejected("unsupported Parquet header")
                raw.seek(-8, os.SEEK_END)
                trailer = raw.read(8)
                size = int.from_bytes(trailer[:4], "little")
                if trailer[4:] != b"PAR1" or not 1 <= size <= min(
                    MAX_FOOTER, obj.size - 12
                ):
                    raise SealedReadRejected("invalid bounded Parquet footer")
                data_end = obj.size - 8 - size
                raw.seek(data_end)
                expected_rows = validate_footer(raw.read(size), data_end, codec, budget)
            # All external-path/shape/metadata/row/byte checks precede native calls.
            connection = _connect(parquet=path)
            try:
                rows: list[tuple] = []
                total = 0
                names = [f'"__actions_c{index}"' for index in range(len(codec.columns))]
                aliases = ",".join(names + ['"__actions_ordinal"'])
                with budget.interruptible(connection.interrupt):
                    projection = [
                        "substring(" + name + ",1,?)"
                        if column.kind == "string"
                        else name
                        for name, column in zip(names, codec.columns)
                    ]
                    bounds = [
                        codec.max_field_bytes + 1
                        for column in codec.columns
                        if column.kind == "string"
                    ]
                    cursor = connection.execute(
                        "SELECT "
                        + ",".join(projection + ['"__actions_ordinal"'])
                        + " FROM read_parquet(?,file_row_number=true) AS source("
                        + aliases
                        + ') ORDER BY "__actions_ordinal" LIMIT ?',
                        bounds + [str(path), codec.max_rows + 1],
                    )
                    while True:
                        budget.check()
                        row = cursor.fetchone()
                        if row is None:
                            break
                        if (
                            len(row) != len(codec.columns) + 1
                            or not isinstance(row[-1], int)
                            or isinstance(row[-1], bool)
                            or row[-1] != len(rows)
                        ):
                            raise SealedReadRejected("Parquet source order differs")
                        values = tuple(
                            checked_scalar(value, column, codec.max_field_bytes)
                            for value, column in zip(row[:-1], codec.columns)
                        )
                        total = add_row(rows, values, codec.columns, total, codec)
                if len(rows) != expected_rows:
                    raise SealedReadRejected("Parquet decoded row count differs")
                return DecodedRows(codec.columns, tuple(rows), total)
            finally:
                connection.close()
    except SealedReadRejected:
        raise
    except Exception:
        raise SealedReadRejected("sealed Parquet unavailable or invalid") from None


def scan_contract(
    descriptor: ProviderDescriptor, source: SourceManifest, name: str
) -> tuple[BindingOperation, DecodedSourceObject]:
    descriptor = ProviderDescriptor.model_validate(descriptor)
    source = require_executable_source(source)
    if (
        descriptor.source_revision != source.revision_id
        or descriptor.kind != source.kind
    ):
        raise SealedReadRejected("operation source identity differs")
    operations = [
        operation for operation in descriptor.operations if operation.name == name
    ]
    objects = [obj for obj in source.objects if name == obj.name + ".scan/v1"]
    if len(operations) != 1 or len(objects) != 1:
        raise SealedReadRejected("unsupported exact-object operation")
    operation, obj = operations[0], objects[0]
    if (
        not isinstance(obj, DecodedSourceObject)
        or operation.effect != "read"
        or operation.parameters
    ):
        raise SealedReadRejected("unsupported scan operation contract")
    columns = {column.name: column for column in obj.codec.columns}
    for result in operation.result:
        column = columns.get(result.name)
        if (
            column is None
            or result.kind != column.kind
            or result.required != (not column.nullable)
        ):
            raise SealedReadRejected("scan projection type/nullability differs")
    return operation, obj


@dataclass(frozen=True)
class SealedScanResult:
    payload: bytes
    row_count: int
    source_revision: str
    operation: str
    contract_digest: str


def _payload(rows, columns, operation: BindingOperation, budget: ReadBudget) -> bytes:
    indexes = {column.name: index for index, column in enumerate(columns)}
    parts: list[bytes] = []
    total = 2
    if total > operation.max_bytes:
        raise SealedReadRejected("scan output byte bound exceeded")
    for index, row in enumerate(rows):
        budget.check()
        if index >= operation.max_rows:
            raise SealedReadRejected("scan output row bound exceeded")
        value = {}
        for field in operation.result:
            actual = row[indexes[field.name]]
            if actual is None:
                if field.required:
                    raise SealedReadRejected("required scan output is missing")
            else:
                value[field.name] = actual
        estimated = (
            2
            + max(0, len(value) - 1)
            + sum(
                len(key)
                + 3
                + (
                    _string_json_size(item)
                    if isinstance(item, str)
                    else len(json_bytes(item))
                )
                for key, item in value.items()
            )
        )
        total += estimated + bool(parts)
        if total > operation.max_bytes:
            raise SealedReadRejected("scan output byte bound exceeded")
        raw = json_bytes(value)
        if len(raw) != estimated:
            raise SealedReadRejected("scan output byte accounting differs")
        parts.append(raw)
    return b"[" + b",".join(parts) + b"]"


class DuckDBSealedScan:
    """Trusted configured adapter, not a public endpoint or Run admission port."""

    def __init__(
        self,
        registry: SqlProviderRegistry,
        authorization: SqlFoundryAuthorization,
        blobs: FilesystemOutputProvider,
        config: ProviderHostConfig,
        source: SourceSealRecord,
    ):
        self.registry, self.authorization, self.blobs = registry, authorization, blobs
        self.config = ProviderHostConfig.model_validate(config)
        self.source = SourceSealRecord.model_validate(source)
        if (
            not isinstance(self.config.host, DuckDBHost)
            or self.config.provider.workspace_id != self.source.workspace
            or self.config.source_revision != self.source.source.revision_id
        ):
            raise SealedReadRejected("configured DuckDB source identity differs")

    def execute(
        self,
        actor: Actor,
        operation: str,
        parameters: dict[str, Any],
        cancelled: threading.Event,
    ) -> SealedScanResult:
        started = time.monotonic()
        if cancelled.is_set():
            raise SealedReadRejected("sealed read cancelled")
        actor = Actor.model_validate(actor)
        if not isinstance(parameters, dict) or parameters:
            raise SealedReadRejected("scan accepts no parameters")
        # Metadata inspection does not grant actual read access.
        self.authorization.require_reference(actor, self.config.provider, "data.read")
        descriptor = self.registry.describe(actor, self.config.provider)
        contract, obj = scan_contract(descriptor, self.source.source, operation)
        budget = ReadBudget(contract.timeout_ms, cancelled)
        budget.deadline = started + contract.timeout_ms / 1000
        budget.check()
        seal = next(item.seal for item in self.source.seals if item.name == obj.name)
        try:
            decoded = (
                decode_csv(self.blobs, seal, obj, budget)
                if isinstance(obj.codec, CsvSourceCodec)
                else decode_parquet(self.blobs, seal, obj, budget)
            )
            # Reject source/output overflow before DuckDB materialization; no partial result.
            expected = _payload(decoded.rows, decoded.columns, contract, budget)
            connection = _connect()
            try:
                kinds = {
                    "string": "VARCHAR",
                    "integer": "BIGINT",
                    "number": "DOUBLE",
                    "boolean": "BOOLEAN",
                }
                names = [
                    f'"__actions_c{index}"' for index in range(len(decoded.columns))
                ]
                declaration = ",".join(
                    name + " " + kinds[column.kind]
                    for name, column in zip(names, decoded.columns)
                )
                with budget.interruptible(connection.interrupt):
                    connection.execute("BEGIN TRANSACTION")
                    connection.execute(
                        'CREATE TEMP TABLE input_rows ("__actions_ordinal" BIGINT,'
                        + declaration
                        + ")"
                    )
                    placeholders = ",".join("?" for _ in range(len(names) + 1))
                    for offset in range(0, len(decoded.rows), 128):
                        budget.check()
                        batch = [
                            (index, *row)
                            for index, row in enumerate(
                                decoded.rows[offset : offset + 128], start=offset
                            )
                        ]
                        connection.executemany(
                            "INSERT INTO input_rows VALUES (" + placeholders + ")",
                            batch,
                        )
                    cursor = connection.execute(
                        "SELECT "
                        + ",".join(names)
                        + ' FROM input_rows ORDER BY "__actions_ordinal" LIMIT ?',
                        [contract.max_rows + 1],
                    )

                    def checked_rows():
                        while True:
                            budget.check()
                            row = cursor.fetchone()
                            if row is None:
                                return
                            if len(row) != len(decoded.columns):
                                raise SealedReadRejected(
                                    "scan result column count differs"
                                )
                            yield tuple(
                                checked_scalar(value, column, obj.codec.max_field_bytes)
                                for value, column in zip(row, decoded.columns)
                            )

                    payload = _payload(
                        checked_rows(), decoded.columns, contract, budget
                    )
                if payload != expected:
                    raise SealedReadRejected(
                        "scan materialization changed typed source values"
                    )
            finally:
                connection.close()
            # Recheck current permissions and availability before releasing any bytes.
            self.authorization.require_reference(
                actor, self.config.provider, "data.read"
            )
            if self.registry.describe(actor, self.config.provider) != descriptor:
                raise SealedReadRejected("scan provider changed")
            budget.check()
            return SealedScanResult(
                payload,
                len(decoded.rows),
                self.source.source.revision_id,
                contract.name,
                contract.contract_digest,
            )
        except SealedReadRejected:
            raise
        except Exception:
            raise SealedReadRejected("bounded sealed scan unavailable") from None
