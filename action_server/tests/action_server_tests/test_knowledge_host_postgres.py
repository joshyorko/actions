"""Owned TLS PostgreSQL acceptance for ordinary Knowledge host selection."""
from threading import Event
from uuid import uuid4

import pytest
from action_server_tests.test_knowledge_host import configured, provision
from action_server_tests.test_local_knowledge_setup import (
    knowledge as knowledge_fixture,
)
from action_server_tests.test_local_knowledge_setup import local as local_fixture
from action_server_tests.test_local_knowledge_setup import provider as provider_fixture
from action_server_tests.test_local_provider_setup import loaded, private_write
from action_server_tests.test_sealed_postgres import (
    tls_postgres as tls_postgres_fixture,
)

from actions.server._local_provider_setup import SecretImport
from actions.server.data_queries.knowledge_normalization import normalize_knowledge
from actions.server.data_queries.sealed_sources import ReadBudget, SealedReadRejected
from actions.server.foundry.provider_config import (
    KnowledgePostgreSQLHost,
    SecretVersion,
)
from actions.server.foundry.provider_execution import ConfiguredProviderExecution

knowledge = knowledge_fixture
local = local_fixture
provider = provider_fixture
tls_postgres = tls_postgres_fixture


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def test_owned_tls_provision_roundtrip_and_readonly_selection(knowledge, tls_postgres):
    import psycopg
    from psycopg import sql

    g = knowledge
    password = uuid4().hex
    with psycopg.connect(**tls_postgres.admin) as admin:
        admin.execute(
            sql.SQL(
                "CREATE ROLE knowledge_writer LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
            ).format(sql.Literal(password))
        )
        admin.execute("GRANT CONNECT ON DATABASE postgres TO knowledge_writer")
        admin.execute("GRANT USAGE,CREATE ON SCHEMA public TO knowledge_writer")
        admin.execute("ALTER ROLE knowledge_writer SET temp_file_limit=0")
    secret = SecretVersion(slot=str(uuid4()), version=str(uuid4()))
    ca = SecretVersion(slot=str(uuid4()), version=str(uuid4()))
    secret_path = g.root / "synthetic-password"
    ca_path = g.root / "synthetic-ca"
    private_write(secret_path, password)
    private_write(ca_path, tls_postgres.ca.decode())
    host = KnowledgePostgreSQLHost(
        revision=g.spec.reference,
        host="localhost",
        port=tls_postgres.port,
        database="postgres",
        username="knowledge_writer",
        password=secret,
        ca_bundle=ca,
    )
    configured(
        g,
        host=host,
        secrets=(
            SecretImport(reference=secret, path=str(secret_path)),
            SecretImport(reference=ca, path=str(ca_path)),
        ),
    )

    def exercise(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        with execution.open_knowledge(
            g.actor, g.descriptor.reference, manage=True
        ) as selection:
            return normalize_knowledge(
                g.spec,
                selection.source,
                blobs,
                selection.seals,
                ReadBudget(2000, Event()),
            )

    corpus = loaded(g, exercise)
    with psycopg.connect(**tls_postgres.admin) as admin:
        assert (
            admin.execute(
                "SELECT to_regclass('public.actions_knowledge_versions')"
            ).fetchone()[0]
            is None
        )
    provision(g)

    def write(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        with execution.open_knowledge(
            g.actor, g.descriptor.reference, manage=True
        ) as selection:
            selection.versions.put(
                corpus, operation_id="tls_first", budget=ReadBudget(2000, Event())
            )

    loaded(g, write)

    def read(db, blobs):
        execution = ConfiguredProviderExecution(db, g.root, blobs)
        with execution.open_knowledge(g.actor, g.descriptor.reference) as selection:
            assert (
                selection.versions.read(
                    g.spec.reference, budget=ReadBudget(2000, Event())
                )
                == corpus
            )
            with pytest.raises(SealedReadRejected):
                selection.versions.put(
                    corpus, operation_id="tls_denied", budget=ReadBudget(2000, Event())
                )

    loaded(g, read)

    # Negative actual TLS checks use the same owned service and fixed SQL store;
    # no configuration or secret record is mutated to manufacture success.
    from actions.server.foundry.knowledge_host import versions_store
    from actions.server.foundry.provider_config import ProviderHostConfig

    class Secrets:
        def __init__(self, *, invalid_ca=False, invalid_password=False):
            self.invalid_ca, self.invalid_password = invalid_ca, invalid_password

        def resolve(self, reference):
            if reference == secret:
                return (
                    b"invalid-synthetic-password"
                    if self.invalid_password
                    else password.encode()
                )
            assert reference == ca
            return b"invalid-synthetic-ca" if self.invalid_ca else tls_postgres.ca

    for secrets in (Secrets(invalid_ca=True), Secrets(invalid_password=True)):
        with versions_store(g.root, g.config, secrets) as versions:
            with pytest.raises(SealedReadRejected):
                versions.read(g.spec.reference, budget=ReadBudget(2000, Event()))
    raw = g.config.model_dump(mode="json")
    raw["host"]["host"] = "127.0.0.2"
    # Closed DTO rejects both TLS downgrade and omission of the pinned CA.
    raw["host"]["sslmode"] = "require"
    with pytest.raises(ValueError):
        ProviderHostConfig.model_validate(raw)
    raw["host"]["sslmode"] = "verify-full"
    raw["host"].pop("ca_bundle")
    with pytest.raises(ValueError):
        ProviderHostConfig.model_validate(raw)
