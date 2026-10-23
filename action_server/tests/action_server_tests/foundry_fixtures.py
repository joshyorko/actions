"""Task-owned common SQL fixtures for Foundry integration only."""

import os
from uuid import uuid4

import pytest


@pytest.fixture(params=["sqlite", "postgresql"])
def database_location(request, tmp_path):
    if request.param == "sqlite":
        yield tmp_path / "runtime.db"
        return
    base = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
    if not base:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("owned PostgreSQL deployment fixture required")
        pytest.skip("owned PostgreSQL deployment fixture not configured")
    import psycopg
    from action_server_tests.test_database_shared import _postgresql_schema_url

    schema = "foundry_deployment_" + uuid4().hex
    owner = psycopg.connect(base, autocommit=True)
    try:
        owner.execute(f'CREATE SCHEMA "{schema}"')
        yield _postgresql_schema_url(base, schema)
    finally:
        try:
            owner.execute(f'DROP SCHEMA "{schema}" CASCADE')
        finally:
            owner.close()
