"""Explicit retained provider factory; metadata construction never reads secrets.

The ordinary Runtime must hold action_server.lock for this object's lifetime.
The offline CLI uses the same lock. Arbitrary same-user writes are not excluded.
"""
from __future__ import annotations

import dataclasses
import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from actions.server._database import Database, _make_table_name
from actions.server._local_authorization import _owner
from actions.server._local_provider_setup import verify_committed_catalog
from actions.server.data_queries.sealed_duckdb import DuckDBSealedScan
from actions.server.data_queries.sealed_postgres import PostgreSQLSealedScan
from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.foundry.provider_catalog import (
    PrivateProviderStore,
    SourceSealRecord,
)
from actions.server.foundry.provider_config import (
    DuckDBHost,
    PostgreSQLHost,
    SecretVersion,
)
from actions.server.foundry.provider_models import (
    FoundryProviderAvailability,
    FoundryProviderRevision,
    FoundrySourceRevision,
)
from actions.server.foundry.provider_registry import SqlProviderRegistry, _ref_id
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import Actor


def _rows(db, model, where, values, *, lock=False):
    selected = (
        db.select(
            model,
            "SELECT * FROM "
            + _make_table_name(model)
            + " WHERE "
            + where
            + " ORDER BY id FOR SHARE",
            list(values),
        )
        if lock and db.backend_name == "postgresql"
        else db.all(model, where=where, values=list(values))
    )
    rows = [dataclasses.asdict(row) for row in selected]
    return json.dumps(
        sorted(rows, key=lambda row: row["id"]), sort_keys=True, separators=(",", ":")
    )


@dataclass(frozen=True)
class SQLRecordPin:
    model: type
    where: str
    values: tuple[str, ...]
    rows: str

    @classmethod
    def capture(cls, db, model, where, values):
        return cls(model, where, tuple(values), _rows(db, model, where, values))

    def recheck(self, db):
        if _rows(db, self.model, self.where, self.values, lock=True) != self.rows:
            raise ValueError("retained provider SQL identity changed")


class _SelectedSecrets:
    def __init__(self, store, host):
        self.store, self.allowed = store, (host.password, host.ca_bundle)

    def resolve(self, reference: SecretVersion) -> bytes:
        if reference not in self.allowed:
            raise ValueError("private secret outside selected configuration")
        return self.store.resolve_secret(reference)


class ConfiguredProviderExecution:
    """An explicitly constructed factory, never an implicit/default provider."""

    def __init__(self, db: Database, datadir: Path, blobs: FilesystemOutputProvider):
        try:
            self._initialize(db, datadir, blobs)
        except Exception:
            raise ValueError("configured provider execution unavailable") from None

    def _initialize(self, db: Database, datadir: Path, blobs: FilesystemOutputProvider):
        self.db, self.datadir, self.blobs = db, datadir, blobs
        self.authorization = SqlFoundryAuthorization(db)
        with db.connect():
            self.owner, self.workspace = _owner(db)
            with PrivateProviderStore(datadir, self.owner, self.workspace) as store:
                self.pointer = store.current()
                if self.pointer is None:
                    raise ValueError("explicit committed provider catalog required")
                verify_committed_catalog(db, store, self.pointer)
                self.catalog, evidence = store.reconstruct(self.pointer, blobs)
                self.registry = SqlProviderRegistry(db, self.authorization, evidence)
                self.configs = {
                    entry.descriptor.reference: store.config(entry.config_digest)
                    for entry in self.catalog.entries
                }
                for entry in self.catalog.entries:
                    if (
                        self.registry._read(entry.descriptor.reference)[0]
                        != entry.descriptor
                    ):
                        raise ValueError("configured provider metadata differs")
                self.provenance = tuple(
                    SQLRecordPin.capture(db, model, where, (self.pointer.generation,))
                    for model, where in (
                        (FoundryRequest, "id=?"),
                        (FoundryAudit, "foundry_request_id=?"),
                    )
                )

    def entry(self, reference: ProviderProfileRevisionRef):
        matches = [
            entry
            for entry in self.catalog.entries
            if entry.descriptor.reference == reference
        ]
        if len(matches) != 1:
            raise ValueError("exact configured provider revision unavailable")
        return matches[0]

    def require_adapter_available(
        self, reference: ProviderProfileRevisionRef, operations: tuple[str, ...]
    ) -> None:
        """Selected local dependency imports only; no engine/secret/network probe.

        Called at execution readiness, never construction/startup. PostgreSQL
        Parquet scans also require the shared DuckDB decoder; CSV scans do not.
        """
        import importlib

        from actions.server.data_queries.sealed_duckdb import scan_contract
        from actions.server.deployments.provider_registry import ParquetSourceCodec

        try:
            entry = self.entry(reference)
            config = self.configs[reference]
            if (
                config.provider != reference
                or config.source_revision != entry.source.revision_id
            ):
                raise ValueError("selected configuration identity differs")
            if (
                not isinstance(operations, tuple)
                or not operations
                or len(operations) > 32
                or len(set(operations)) != len(operations)
            ):
                raise ValueError("bounded selected operations required")
            if isinstance(config.host, DuckDBHost):
                modules = {"duckdb"}
            elif isinstance(config.host, PostgreSQLHost):
                modules = {"psycopg"}
            else:
                raise ValueError("selected adapter unavailable")
            for name in operations:
                _, source_object = scan_contract(entry.descriptor, entry.source, name)
                if isinstance(source_object.codec, ParquetSourceCodec):
                    modules.add("duckdb")
            for name in sorted(modules):
                importlib.import_module(name)
        except Exception:
            raise ValueError(
                "selected logical adapter dependency unavailable"
            ) from None

    def check_current(self) -> None:
        """Filesystem/provenance validation; never call inside publication."""
        try:
            self._check_current()
        except Exception:
            raise ValueError(
                "private provider catalog changed or unavailable"
            ) from None

    def _check_current(self) -> None:
        with self.db.connect(), PrivateProviderStore(
            self.datadir, self.owner, self.workspace
        ) as store:
            if store.current() != self.pointer:
                raise ValueError("private provider catalog changed")
            verify_committed_catalog(self.db, store, self.pointer)
            catalog, _ = store.reconstruct(self.pointer, self.blobs)
            if catalog != self.catalog or any(
                store.config(entry.config_digest)
                != self.configs[entry.descriptor.reference]
                for entry in catalog.entries
            ):
                raise ValueError("private provider catalog identity changed")

    def pin_sql(
        self, actor: Actor, reference: ProviderProfileRevisionRef
    ) -> tuple[SQLRecordPin, ...]:
        entry = self.entry(reference)
        self.authorization.require_reference(actor, reference, "provider.inspect")
        self.authorization.require_reference(actor, reference, "data.read")
        descriptor, state = self.registry._read(reference)
        if descriptor != entry.descriptor or not state.enabled:
            raise ValueError("selected provider unavailable")
        provider_rows = self.db.all(
            FoundryProviderRevision, where="id=?", values=[_ref_id(reference)]
        )
        return self.provenance + (
            SQLRecordPin.capture(
                self.db, FoundryProviderRevision, "id=?", (_ref_id(reference),)
            ),
            SQLRecordPin.capture(
                self.db,
                FoundrySourceRevision,
                "id=?",
                (provider_rows[0].foundry_source_revision_id,),
            ),
            SQLRecordPin.capture(
                self.db, FoundryProviderAvailability, "id=?", (_ref_id(reference),)
            ),
        )

    def recheck_sql(
        self,
        actor: Actor,
        reference: ProviderProfileRevisionRef,
        pins: tuple[SQLRecordPin, ...],
    ) -> None:
        """No filesystem, engine, catalog reconstruction or secret lookup."""
        for pin in pins:
            pin.recheck(self.db)
        self.authorization.require_reference(actor, reference, "provider.inspect")
        self.authorization.require_reference(actor, reference, "data.read")

    @contextmanager
    def open_provider(
        self, actor: Actor, reference: ProviderProfileRevisionRef
    ) -> Iterator[DuckDBSealedScan | PostgreSQLSealedScan]:
        self.check_current()
        entry = self.entry(reference)
        with self.db.connect(), PrivateProviderStore(
            self.datadir, self.owner, self.workspace
        ) as store:
            pins = self.pin_sql(actor, reference)
            config = store.config(entry.config_digest)
            if config != self.configs[reference]:
                raise ValueError("selected private configuration changed")
            source = SourceSealRecord(
                owner=self.owner,
                workspace=self.workspace,
                source=entry.source,
                seals=entry.seals,
            )
            adapter: DuckDBSealedScan | PostgreSQLSealedScan
            if isinstance(config.host, DuckDBHost):
                adapter = DuckDBSealedScan(
                    self.registry, self.authorization, self.blobs, config, source
                )
            elif isinstance(config.host, PostgreSQLHost):
                adapter = PostgreSQLSealedScan(
                    self.registry,
                    self.authorization,
                    self.blobs,
                    config,
                    source,
                    _SelectedSecrets(store, config.host),
                )
            else:
                raise ValueError("configured provider adapter unsupported")
            yield adapter
            self.recheck_sql(actor, reference, pins)
            self.check_current()
