"""Private, explicitly provisioned Knowledge versions; no caller paths or DDL on load.

The ordinary Runtime or offline operator holds action_server.lock. As with the
private catalog, the operator must exclude arbitrary same-user filesystem writes.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from actions.server.data_queries.knowledge_values import KnowledgeRevisionRef, canonical
from actions.server.data_queries.knowledge_versions import (
    DuckDBKnowledgeVersions,
    PostgreSQLKnowledgeVersions,
)
from actions.server.deployments.ids import ProviderProfileRevisionRef
from actions.server.deployments.provider_registry import SourceManifest
from actions.server.foundry.knowledge_authority import KnowledgeRevisionAuthority, _id
from actions.server.foundry.knowledge_models import KnowledgeCollectionRevision
from actions.server.foundry.provider_catalog import _private
from actions.server.foundry.provider_config import (
    KnowledgeDuckDBHost,
    KnowledgePostgreSQLHost,
)
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.types import SealReceipt

KNOWLEDGE_HOSTS = (KnowledgeDuckDBHost, KnowledgePostgreSQLHost)


def require_definition(db, registry, actor, config, *, manage=False):
    """Canonical SQL and live grants only; no engine/blob/secret access."""
    host = config.host
    if not isinstance(host, KNOWLEDGE_HOSTS):
        raise ValueError("explicit Knowledge host required")
    authority = KnowledgeRevisionAuthority(db, registry)
    auth = authority.authorization
    auth.require_reference(actor, config.provider, "provider.inspect")
    auth.require_reference(actor, config.provider, "knowledge.read")
    auth.require_knowledge(actor, host.revision, "knowledge.read")
    if manage:
        auth.require_knowledge(actor, host.revision, "knowledge.manage")
    spec = authority._load(host.revision)
    rows = db.all(
        KnowledgeCollectionRevision,
        where="id=?",
        values=[_id(canonical(host.revision))],
    )
    if (
        len(rows) != 1
        or rows[0].source_provider_json != config.provider.model_dump_json()
        or spec.source_revision != config.source_revision
    ):
        raise ValueError("Knowledge host definition/source provider differs")
    return authority, rows[0]


@dataclass(frozen=True)
class KnowledgeHostSelection:
    revision: KnowledgeRevisionRef
    source_provider: ProviderProfileRevisionRef
    source: SourceManifest
    blobs: FilesystemOutputProvider
    seals: dict[str, SealReceipt]
    versions: DuckDBKnowledgeVersions | PostgreSQLKnowledgeVersions
    authority: KnowledgeRevisionAuthority


def _duckdb_path(datadir, config, *, provision):
    # The path is generated exclusively from canonical host-owned identities.
    root = datadir / "provider-state"
    for parent in (datadir, root):
        if parent.is_symlink():
            raise ValueError("owned Knowledge directory required")
        _private(parent.stat(), directory=True)
    directory = root / "knowledge-versions"
    if provision:
        directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink():
        raise ValueError("owned Knowledge directory required")
    _private(directory.stat(), directory=True)
    identity = f"{config.provider.workspace_id.root}:{config.provider.provider_profile_id.root}:{config.host.revision.collection_id}"
    path = directory / (hashlib.sha256(identity.encode()).hexdigest() + ".duckdb")
    for item in (path, Path(str(path) + ".wal")):
        if item.exists() or item.is_symlink():
            if item.is_symlink():
                raise ValueError("owned Knowledge file required")
            _private(item.stat(), directory=False)
    if not provision and not path.is_file():
        raise ValueError("Knowledge host requires explicit provisioning")
    return path


def _duckdb_connect(datadir, config, *, provision, manage):
    import duckdb

    path = _duckdb_path(datadir, config, provision=provision)
    connection = duckdb.connect(
        str(path),
        read_only=not (manage or provision),
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
        path.chmod(0o600)
        # WAL inherits private database mode; fixed statements alone reach this
        # connection. No SQL, path, extension or relation comes from a Package.
        connection.execute("SET enable_external_access=false")
        connection.execute("SET lock_configuration=true")
        return connection
    except BaseException:
        connection.close()
        raise


@contextmanager
def versions_store(datadir: Path, config, secrets, *, provision=False, manage=False):
    host = config.host
    if isinstance(host, KnowledgeDuckDBHost):
        # Constructing a selection performs no file creation or database probe.
        yield DuckDBKnowledgeVersions(
            lambda: _duckdb_connect(datadir, config, provision=provision, manage=manage)
        )
        return
    if not isinstance(host, KnowledgePostgreSQLHost):
        raise ValueError("explicit Knowledge host required")
    with tempfile.TemporaryDirectory(prefix="actions-knowledge-pg-") as directory:
        private = Path(directory)

        def connect():
            import psycopg

            if any(name.startswith("PG") for name in os.environ):
                raise ValueError("ambient PostgreSQL configuration is unsupported")
            password = secrets.resolve(host.password)
            ca_bytes = secrets.resolve(host.ca_bundle)
            if (
                not isinstance(password, bytes)
                or not 1 <= len(password) <= 4096
                or b"\x00" in password
                or not isinstance(ca_bytes, bytes)
                or not 1 <= len(ca_bytes) <= 262144
            ):
                raise ValueError("private connection material is invalid")
            ca = private / "ca.pem"
            ca.write_bytes(ca_bytes)
            ca.chmod(0o600)
            return psycopg.connect(
                host=host.host,
                port=host.port,
                dbname=host.database,
                user=host.username,
                password=password.decode("utf-8", errors="strict"),
                sslmode="verify-full",
                sslrootcert=str(ca),
                sslcert=str(private / "absent-client.crt"),
                sslkey=str(private / "absent-client.key"),
                sslcrl=str(private / "absent.crl"),
                sslcrldir=str(private / "absent-crls"),
                passfile=str(private / "absent-passfile"),
                gssencmode="disable",
                connect_timeout=2,
                application_name="actions-knowledge-versions",
                options="-c search_path=public -c client_encoding=UTF8 -c statement_timeout=2000 -c lock_timeout=2000 -c idle_in_transaction_session_timeout=2000"
                + (
                    ""
                    if manage or provision
                    else " -c default_transaction_read_only=on"
                ),
                autocommit=True,
            )

        yield PostgreSQLKnowledgeVersions(connect)
