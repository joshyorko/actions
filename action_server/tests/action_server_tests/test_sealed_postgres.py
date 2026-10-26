"""Owned TLS PostgreSQL, synthetic authority; no ordinary worker proof."""
import json
import os
import shutil
import subprocess
import threading
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_sealed_scan import CSV, codec, parquet_bytes, run
from action_server_tests.test_sealed_scan import setup as _scan_setup

from actions.server.data_queries.sealed_postgres import PostgreSQLSealedScan
from actions.server.data_queries.sealed_sources import SealedReadRejected
from actions.server.foundry.provider_config import PostgreSQLHost, SecretVersion

pytest_plugins = ["action_server_tests.foundry_fixtures"]
setup = _scan_setup


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture(scope="module")
def tls_postgres(tmp_path_factory):
    if shutil.which("docker") is None:
        message = "Docker CLI required for owned TLS PostgreSQL fixture"
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail(message)
        pytest.skip(message)

    import psycopg
    from psycopg import sql

    root = tmp_path_factory.mktemp("owned-pg-tls")

    def command(args, **kwargs):
        return subprocess.run(
            args, check=True, capture_output=True, text=True, **kwargs
        ).stdout.strip()

    command(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(root / "ca.key"),
            "-out",
            str(root / "ca.crt"),
            "-days",
            "1",
            "-subj",
            "/CN=owned-scan-test-ca",
        ]
    )
    command(
        [
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(root / "server.key"),
            "-out",
            str(root / "server.csr"),
            "-subj",
            "/CN=localhost",
        ]
    )
    (root / "extensions").write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\n")
    command(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            str(root / "server.csr"),
            "-CA",
            str(root / "ca.crt"),
            "-CAkey",
            str(root / "ca.key"),
            "-CAcreateserial",
            "-out",
            str(root / "server.crt"),
            "-days",
            "1",
            "-extfile",
            str(root / "extensions"),
        ]
    )
    password = uuid4().hex
    env = dict(os.environ, POSTGRES_PASSWORD=password)
    container = command(
        [
            "docker",
            "run",
            "--rm",
            "-d",
            "--label",
            "actions.owner=sealed-postgres-test",
            "--memory",
            "768m",
            "--tmpfs",
            "/var/lib/postgresql/data:rw,size=512m",
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_PASSWORD",
            "-v",
            str(root) + ":/owned-tls:ro",
            "--entrypoint",
            "bash",
            "postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81",
            "-c",
            "mkdir /tmp/tls; cp /owned-tls/server.key /owned-tls/server.crt /tmp/tls/; chown -R postgres:postgres /tmp/tls; chmod 600 /tmp/tls/server.key; exec docker-entrypoint.sh postgres -c ssl=on -c ssl_cert_file=/tmp/tls/server.crt -c ssl_key_file=/tmp/tls/server.key",
        ],
        env=env,
    )
    try:
        port = int(
            json.loads(command(["docker", "inspect", container]))[0]["NetworkSettings"][
                "Ports"
            ]["5432/tcp"][0]["HostPort"]
        )
        kwargs = dict(
            host="127.0.0.1",
            port=port,
            dbname="postgres",
            user="postgres",
            password=password,
            sslmode="verify-full",
            sslrootcert=str(root / "ca.crt"),
            connect_timeout=2,
            autocommit=True,
        )
        for _ in range(100):
            try:
                admin = psycopg.connect(**kwargs)
                break
            except psycopg.OperationalError:
                time.sleep(0.1)
        else:
            raise RuntimeError("owned TLS fixture did not start")
        reader_password = uuid4().hex
        with admin:
            admin.execute(
                sql.SQL(
                    "CREATE ROLE scan_reader LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
                ).format(sql.Literal(reader_password))
            )
            admin.execute("REVOKE ALL ON DATABASE postgres FROM PUBLIC")
            admin.execute("GRANT CONNECT ON DATABASE postgres TO scan_reader")
            admin.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            admin.execute("ALTER ROLE scan_reader SET temp_file_limit = 0")
            admin.execute(
                "ALTER ROLE scan_reader SET default_transaction_read_only = on"
            )
        yield SimpleNamespace(
            port=port,
            password=reader_password,
            ca=(root / "ca.crt").read_bytes(),
            admin=kwargs,
        )
    finally:
        command(["docker", "stop", container])


def adapt(g, tls, *, password=None, ca=None):
    pwref, caref = (
        SecretVersion(slot=str(uuid4()), version=str(uuid4())) for _ in range(2)
    )

    class Secrets:
        calls = []

        def resolve(self, reference):
            self.calls.append(reference)
            return (
                (tls.password.encode() if password is None else password)
                if reference == pwref
                else (tls.ca if ca is None else ca)
            )

    secrets = Secrets()
    host = PostgreSQLHost(
        host="127.0.0.1",
        port=tls.port,
        database="postgres",
        username="scan_reader",
        password=pwref,
        ca_bundle=caref,
    )
    original = g.adapter
    config = original.config.model_copy(update={"host": host})
    g.adapter = PostgreSQLSealedScan(
        original.registry,
        original.authorization,
        original.blobs,
        config,
        original.source,
        secrets,
    )
    return secrets


def test_actual_tls_csv_and_parquet_match_duckdb(setup, tls_postgres, tmp_path):
    expected = run(setup()).payload
    for g in [setup(), setup(parquet_bytes(tmp_path), codec(True))]:
        secrets = adapt(g, tls_postgres)
        assert secrets.calls == []
        assert run(g).payload == expected
        assert len(secrets.calls) == 2


def test_multiple_batches_order(setup, tls_postgres):
    raw = b"record_id,count,amount,active,note\n" + b"".join(
        f"row{i},{i},1.5,true,\\N\n".encode() for i in range(300)
    )
    g = setup(raw, codec(max_rows=400), max_rows=400)
    expected = run(g).payload
    adapt(g, tls_postgres)
    assert run(g).payload == expected


@pytest.mark.parametrize("what", ["password", "ca"])
def test_bad_private_material_refused(setup, tls_postgres, what):
    g = setup()
    adapt(g, tls_postgres, **{what: b"rejected-synthetic-private-material"})
    with pytest.raises(
        SealedReadRejected, match="bounded sealed scan unavailable"
    ) as error:
        run(g)
    assert "synthetic" not in str(error.value)


def test_ambient_libpq_refused(setup, tls_postgres, monkeypatch):
    g = setup()
    adapt(g, tls_postgres)
    monkeypatch.setenv("PGSERVICE", "untrusted-service")
    with pytest.raises(SealedReadRejected, match="ambient PostgreSQL"):
        run(g)


def test_source_overflow_before_secrets_or_connect(setup, tls_postgres):
    g = setup(max_rows=1)
    secrets = adapt(g, tls_postgres)
    with pytest.raises(SealedReadRejected):
        run(g)
    assert secrets.calls == []


def test_actual_role_has_connect_only(tls_postgres):
    import psycopg

    kwargs = dict(
        tls_postgres.admin, user="scan_reader", password=tls_postgres.password
    )
    with psycopg.connect(**kwargs) as connection:
        assert connection.execute(
            "SELECT has_database_privilege(current_user,current_database(),'CONNECT'), has_database_privilege(current_user,current_database(),'TEMP'),has_schema_privilege(current_user,'public','CREATE')"
        ).fetchone() == (True, False, False)
        with pytest.raises(psycopg.Error):
            connection.execute("CREATE TEMP TABLE forbidden(x int)")


def test_nul_unicode_string_exact_across_engines(setup, tls_postgres):
    g = setup(CSV.replace(b"quoted, value", "nul\x00 snowman ☃".encode()))
    expected = run(g).payload
    adapt(g, tls_postgres)
    assert run(g).payload == expected


@pytest.mark.parametrize("cancel", [True, False])
def test_actual_native_cancel_and_total_timeout(
    setup, tls_postgres, monkeypatch, cancel
):
    from actions.server.data_queries import sealed_postgres as module

    g = setup(timeout_ms=2000 if cancel else 150)
    adapt(g, tls_postgres)
    original = module._connect
    event = threading.Event()
    entered = []

    class SlowConnection:
        def __init__(self, connection):
            self.connection = connection

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def execute(self, query, *args):
            if query.startswith('SELECT "c0"'):
                entered.append(True)
                timer = threading.Timer(0.03, event.set) if cancel else None
                if timer:
                    timer.start()
                try:
                    self.connection.execute("SELECT pg_catalog.pg_sleep(2)")
                finally:
                    if timer:
                        timer.join()
            return self.connection.execute(query, *args)

    monkeypatch.setattr(
        module, "_connect", lambda *args: SlowConnection(original(*args))
    )
    started = time.monotonic()
    with pytest.raises(SealedReadRejected):
        g.adapter.execute(g.actor, g.operation.name, {}, event)
    assert entered and time.monotonic() - started < 1.5


def test_revoke_during_engine_before_readback(setup, tls_postgres, monkeypatch):
    from actions.server.data_queries import sealed_postgres as module
    from actions.server.foundry.models import FoundryAccessGrant

    g = setup()
    adapt(g, tls_postgres)
    original = module._connect

    connected = []

    def revoke(*args):
        with g.db.transaction():
            g.db.update_by_id(FoundryAccessGrant, g.grant.id, {"operations_json": "[]"})
        connection = original(*args)
        connected.append(True)
        return connection

    monkeypatch.setattr(module, "_connect", revoke)
    with pytest.raises(SealedReadRejected):
        run(g)

    assert connected == [True]


def test_missing_pinned_ca_rejected_without_secret_resolution(setup, tls_postgres):
    g = setup()
    secrets = adapt(g, tls_postgres)
    adapter = g.adapter
    config = adapter.config.model_copy(
        update={"host": adapter.config.host.model_copy(update={"ca_bundle": None})}
    )
    with pytest.raises(SealedReadRejected, match="identity differs"):
        PostgreSQLSealedScan(
            adapter.registry,
            adapter.authorization,
            adapter.blobs,
            config,
            adapter.source,
            secrets,
        )
    assert secrets.calls == []


def test_server_spill_policy_must_be_explicit(setup, tls_postgres):
    import psycopg

    g = setup()
    adapt(g, tls_postgres)
    with psycopg.connect(**tls_postgres.admin) as admin:
        admin.execute("ALTER ROLE scan_reader SET temp_file_limit = -1")
    try:
        with pytest.raises(SealedReadRejected, match="spill policy"):
            run(g)
    finally:
        with psycopg.connect(**tls_postgres.admin) as admin:
            admin.execute("ALTER ROLE scan_reader SET temp_file_limit = 0")
