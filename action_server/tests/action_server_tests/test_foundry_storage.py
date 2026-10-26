"""Shared foundry storage is additive, transactional and restart-readable."""

import json
import os
import subprocess
import sys
from uuid import uuid4

import pytest

from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.migrations import Migration, migrate_db
from actions.server.run_outputs.models import Workspace


@pytest.fixture(params=["sqlite", "postgresql"])
def legacy(request, tmp_path):
    from action_server_tests.test_database_shared import _postgresql_schema_url

    location = tmp_path / "owned-foundry.db"
    owner = None
    schema = "foundry_storage_" + uuid4().hex
    if request.param == "postgresql":
        base = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
        if not base:
            if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
                pytest.fail("owned PostgreSQL control plane required")
            pytest.skip("owned PostgreSQL foundry fixture not configured")
        import psycopg

        owner = psycopg.connect(base, autocommit=True)
        owner.execute(f'CREATE SCHEMA "{schema}"')
        location = _postgresql_schema_url(base, schema)
    workspace = Workspace(str(uuid4()), "active", 7)
    try:
        db = Database(location)
        with db.connect():
            db.initialize(get_all_model_classes())
            with db.transaction():
                from action_server_tests.foundry_historical import (
                    create_historical_schema,
                )

                create_historical_schema(db, 16)
                db.insert(Migration(16, "add_invoice_reviews"))
                db.insert(workspace)
        yield location, workspace
    finally:
        if owner is not None:
            try:
                owner.execute(f'DROP SCHEMA "{schema}" CASCADE')
            finally:
                owner.close()


def test_upgrade_is_empty_and_shared_records_survive_a_fresh_interpreter(legacy):
    from actions.server.foundry.models import (
        MODEL_CLASSES,
        FoundryAccessGrant,
        FoundryAudit,
        FoundryDeploymentHead,
        FoundryRequest,
    )

    location, workspace = legacy
    assert migrate_db(location)
    db = Database(location)
    with db.connect():
        db.initialize(get_all_model_classes())
        assert db.first(Workspace) == workspace
        assert all(db.all(cls) == [] for cls in MODEL_CLASSES)
        before = {table: len(rows) for table, rows in db.list_whole_db().items()}
        principal = str(uuid4())
        deployment = str(uuid4())
        request = FoundryRequest(
            "owned-request",
            workspace.id,
            principal,
            "activate",
            "one",
            "sha256:" + "1" * 64,
            '{"revision":"owned-revision"}',
        )
        head = FoundryDeploymentHead(
            "owned-head", workspace.id, deployment, "owned-revision", 1
        )
        audit = FoundryAudit(
            str(uuid4()),
            workspace.id,
            deployment,
            principal,
            "activate",
            request.id,
            "",
            head.active_revision_id,
            "0",
        )
        with pytest.raises(RuntimeError, match="owned failure"):
            with db.transaction():
                db.insert(request)
                db.insert(head)
                db.insert(audit)
                raise RuntimeError("owned failure before commit")
        assert all(db.all(cls) == [] for cls in MODEL_CLASSES)
        with db.transaction():
            db.insert(request)
            db.insert(head)
            db.insert(audit)
        # Storage publication never manufactures a grant, Review, Work Item,
        # Run or Attempt. The service must later enforce real authorization.
        assert db.all(FoundryAccessGrant) == []
        after = {table: len(rows) for table, rows in db.list_whole_db().items()}
        for table in before:
            if table not in {
                "foundry_request",
                "foundry_deployment_head",
                "foundry_audit",
            }:
                assert after[table] == before[table]

    environment = os.environ.copy()
    environment["ACTIONS_OWNED_FOUNDRY_DB"] = str(location)
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import json, os
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.foundry.models import FoundryDeploymentHead, FoundryRequest, FoundryAudit
db = Database(os.environ['ACTIONS_OWNED_FOUNDRY_DB'])
with db.connect():
    db.initialize(get_all_model_classes())
    print(json.dumps([db.first(FoundryDeploymentHead).active_revision_id,
                      db.first(FoundryRequest).id, len(db.all(FoundryAudit))]))
""",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert json.loads(result.stdout) == ["owned-revision", "owned-request", 1]


def test_failed_schema_upgrade_rolls_back_all_new_tables_and_migration_row(
    legacy, monkeypatch
):
    from actions.server.migrations import migration_add_foundry_records

    location, workspace = legacy
    db = Database(location)
    with db.connect():
        db.initialize(get_all_model_classes())
        before = db.list_table_and_columns()
        execute = db.execute

        def fail_mid_migration(sql, values=None):
            if "CREATE TABLE IF NOT EXISTS foundry_deployment_head(" in sql:
                raise RuntimeError("owned interrupted schema upgrade")
            return execute(sql, values)

        monkeypatch.setattr(db, "execute", fail_mid_migration)
        with pytest.raises(RuntimeError, match="owned interrupted"):
            with db.transaction():
                migration_add_foundry_records.migrate(db)
        assert db.list_table_and_columns() == before
        assert max(row.id for row in db.all(Migration)) == 16
        assert db.first(Workspace) == workspace
