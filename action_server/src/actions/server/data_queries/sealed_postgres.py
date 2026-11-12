"""Explicit TLS PostgreSQL execution of the sealed parameterless scan subset."""
from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Protocol

from actions.server.data_queries.sealed_duckdb import (
    SealedScanResult,
    _payload,
    decode_parquet,
    scan_contract,
)
from actions.server.data_queries.sealed_sources import (
    ReadBudget,
    SealedReadRejected,
    checked_scalar,
    decode_csv,
)
from actions.server.deployments.provider_registry import CsvSourceCodec
from actions.server.foundry.provider_catalog import SourceSealRecord
from actions.server.foundry.provider_config import (
    PostgreSQLHost,
    ProviderHostConfig,
    SecretVersion,
)
from actions.server.foundry.provider_registry import SqlProviderRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor


class PrivateSecretResolver(Protocol):
    """Trusted exact-version lookup. Never invoked at startup/construction."""

    def resolve(self, reference: SecretVersion) -> bytes:
        ...


def _connect(host: PostgreSQLHost, password: str, ca: Path, private: Path):
    import psycopg

    # Refuse ambient libpq configuration rather than mutating process environment.
    # This also excludes PGSERVICE/PGSERVICEFILE and PGSSL* defaults.
    if any(name.startswith("PG") for name in os.environ):
        raise SealedReadRejected("ambient PostgreSQL configuration is unsupported")
    return psycopg.connect(
        host=host.host,
        port=host.port,
        dbname=host.database,
        user=host.username,
        password=password,
        sslmode="verify-full",
        sslrootcert=str(ca),
        sslcert=str(private / "absent-client.crt"),
        sslkey=str(private / "absent-client.key"),
        sslcrl=str(private / "absent.crl"),
        sslcrldir=str(private / "absent-crls"),
        passfile=str(private / "absent-passfile"),
        gssencmode="disable",
        connect_timeout=2,
        application_name="actions-sealed-scan",
        options="-c search_path=pg_catalog -c default_transaction_read_only=on -c client_encoding=UTF8",
        autocommit=True,
    )


class PostgreSQLSealedScan:
    """No public routing, grants, DDL, mutable relation reads or source writes."""

    def __init__(
        self,
        registry: SqlProviderRegistry,
        authorization: SqlFoundryAuthorization,
        blobs: FilesystemOutputProvider,
        config: ProviderHostConfig,
        source: SourceSealRecord,
        secrets: PrivateSecretResolver,
    ):
        self.registry, self.authorization, self.blobs = registry, authorization, blobs
        self.config = ProviderHostConfig.model_validate(config)
        self.source = SourceSealRecord.model_validate(source)
        self.secrets = secrets
        if (
            not isinstance(self.config.host, PostgreSQLHost)
            or self.config.host.ca_bundle is None
            or self.config.provider.workspace_id != self.source.workspace
            or self.config.source_revision != self.source.source.revision_id
        ):
            raise SealedReadRejected("configured PostgreSQL source identity differs")

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
        if not isinstance(parameters, dict) or parameters:
            raise SealedReadRejected("scan accepts no parameters")
        actor = Actor.model_validate(actor)
        self.authorization.require_reference(actor, self.config.provider, "data.read")
        descriptor = self.registry.describe(actor, self.config.provider)
        contract, obj = scan_contract(descriptor, self.source.source, operation)
        budget = ReadBudget(contract.timeout_ms, cancelled)
        budget.deadline = started + contract.timeout_ms / 1000
        budget.check()
        try:
            seal = next(s.seal for s in self.source.seals if s.name == obj.name)
            decoded = (
                decode_csv(self.blobs, seal, obj, budget)
                if isinstance(obj.codec, CsvSourceCodec)
                else decode_parquet(self.blobs, seal, obj, budget)
            )
            expected = _payload(decoded.rows, decoded.columns, contract, budget)
            host = self.config.host
            assert isinstance(host, PostgreSQLHost) and host.ca_bundle is not None
            password_bytes = self.secrets.resolve(host.password)
            ca_bytes = self.secrets.resolve(host.ca_bundle)
            if (
                not isinstance(password_bytes, bytes)
                or not 1 <= len(password_bytes) <= 4096
                or b"\x00" in password_bytes
                or not isinstance(ca_bytes, bytes)
                or not 1 <= len(ca_bytes) <= 262144
            ):
                raise SealedReadRejected("private connection material is invalid")
            password = password_bytes.decode("utf-8", errors="strict")
            budget.check()
            with tempfile.TemporaryDirectory(prefix="actions-pg-scan-") as directory:
                private = Path(directory)
                ca = private / "ca.pem"
                ca.write_bytes(ca_bytes)
                ca.chmod(0o600)
                connection = _connect(host, password, ca, private)
                try:
                    budget.check()
                    with budget.interruptible(connection.cancel):
                        connection.execute("BEGIN READ ONLY")
                        connection.execute("SET LOCAL work_mem = '1MB'")
                        connection.execute(
                            "SET LOCAL max_parallel_workers_per_gather = 0"
                        )
                        connection.execute("SET LOCAL jit = off")
                        connection.execute(
                            "SET LOCAL idle_in_transaction_session_timeout = '2s'"
                        )
                        if (
                            connection.execute("SHOW temp_file_limit").fetchone()[0]
                            != "0"
                        ):
                            raise SealedReadRejected(
                                "PostgreSQL spill policy is unsupported"
                            )
                        types = {
                            "string": "bytea",
                            "integer": "bigint",
                            "number": "double precision",
                            "boolean": "boolean",
                        }
                        names = [f'"c{i}"' for i in range(len(decoded.columns))]
                        casts = ["%s::bigint"] + [
                            "%s::" + types[c.kind] for c in decoded.columns
                        ]
                        row_sql = "(" + ",".join(casts) + ")"
                        result = []
                        for offset in range(0, len(decoded.rows), 128):
                            budget.check()
                            remaining = max(
                                1, int((budget.deadline - time.monotonic()) * 1000)
                            )
                            connection.execute(
                                "SELECT pg_catalog.set_config('statement_timeout', %s, true)",
                                [str(remaining)],
                            )
                            connection.execute(
                                "SELECT pg_catalog.set_config('lock_timeout', %s, true)",
                                [str(remaining)],
                            )
                            batch = decoded.rows[offset : offset + 128]
                            query = (
                                "SELECT "
                                + ",".join(names)
                                + " FROM (VALUES "
                                + ",".join([row_sql] * len(batch))
                                + ') AS sealed("ordinal",'
                                + ",".join(names)
                                + ') ORDER BY "ordinal"'
                            )
                            values = [
                                value
                                for index, row in enumerate(batch, offset)
                                for value in (
                                    index,
                                    *(
                                        v.encode("utf-8") if isinstance(v, str) else v
                                        for v in row
                                    ),
                                )
                            ]
                            rows = connection.execute(query, values).fetchall()
                            if len(rows) != len(batch):
                                raise SealedReadRejected("scan row count differs")
                            for row in rows:
                                if len(row) != len(decoded.columns):
                                    raise SealedReadRejected(
                                        "scan column count differs"
                                    )
                                result.append(
                                    tuple(
                                        checked_scalar(
                                            value.decode("utf-8")
                                            if column.kind == "string"
                                            and isinstance(value, bytes)
                                            else value,
                                            column,
                                            obj.codec.max_field_bytes,
                                        )
                                        for value, column in zip(row, decoded.columns)
                                    )
                                )
                        payload = _payload(result, decoded.columns, contract, budget)
                        if payload != expected:
                            raise SealedReadRejected(
                                "scan materialization changed typed source values"
                            )
                finally:
                    # Closing an uncommitted session aborts it even after cancellation.
                    connection.close()
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
