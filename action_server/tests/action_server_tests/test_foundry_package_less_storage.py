"""Forward UI-only storage keeps real Package anchors and migration atomicity."""

import os
from uuid import uuid4

import pytest

from actions.server._database import Database, DBError
from actions.server._models import get_all_model_classes
from actions.server.foundry.models import (
    FoundryDeploymentRevision,
    FoundryPackageRevision,
)
from actions.server.migrations import Migration, migrate_db
from actions.server.run_outputs.models import Workspace


@pytest.fixture(params=["sqlite", "postgresql"])
def schema17(request, tmp_path):
    from action_server_tests.test_database_shared import _postgresql_schema_url

    location = tmp_path / "schema17.db"
    owner = None
    schema = "foundry_ui_" + uuid4().hex
    if request.param == "postgresql":
        base = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
        if not base:
            if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
                pytest.fail("owned PostgreSQL fixture required")
            pytest.skip("owned PostgreSQL fixture not configured")
        import psycopg

        owner = psycopg.connect(base, autocommit=True)
        owner.execute(f'CREATE SCHEMA "{schema}"')
        location = _postgresql_schema_url(base, schema)
    db = Database(location)
    try:
        with db.connect():
            db.initialize(get_all_model_classes())
            with db.transaction():
                from action_server_tests.foundry_historical import (
                    create_historical_schema,
                )

                create_historical_schema(db, 17)
                db.insert(Migration(17, "add_foundry_records"))
                db.insert(Workspace("owned-workspace", "active", 7))
                db.insert(
                    FoundryPackageRevision(
                        "owned-package",
                        "owned-workspace",
                        "p",
                        "r",
                        "{}",
                        "digest",
                        "[]",
                        "{}",
                    )
                )
                db.insert(
                    FoundryDeploymentRevision(
                        "backend",
                        "owned-workspace",
                        "app",
                        "r",
                        "owned-package",
                        "{}",
                        "{}",
                    )
                )
        yield location
    finally:
        if owner is not None:
            try:
                owner.execute(f'DROP SCHEMA "{schema}" CASCADE')
            finally:
                owner.close()


def _nullable(db):
    with db.cursor() as cursor:
        if db.backend_name == "postgresql":
            db.execute_query(
                cursor,
                "SELECT is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='foundry_deployment_revision' AND column_name='foundry_package_revision_id'",
            )
            return cursor.fetchone()[0] == "YES"
        db.execute_query(cursor, "PRAGMA table_info(foundry_deployment_revision)")
        return not next(
            row for row in cursor.fetchall() if row[1] == "foundry_package_revision_id"
        )[3]


def test_forward_upgrade_preserves_backend_and_allows_no_fake_package(schema17):
    assert migrate_db(schema17, to_version=18)
    db = Database(schema17)
    with db.connect():
        db.initialize(get_all_model_classes())
        assert _nullable(db)
        assert (
            db.first(FoundryDeploymentRevision).foundry_package_revision_id
            == "owned-package"
        )
        with db.transaction():
            db.insert(
                FoundryDeploymentRevision(
                    "ui", "owned-workspace", "ui-app", "r", None, "{}", "{}"
                )
            )
        assert len(db.all(FoundryPackageRevision)) == 1
        with pytest.raises(DBError):
            with db.transaction():
                db.insert(
                    FoundryDeploymentRevision(
                        "invalid",
                        "owned-workspace",
                        "bad-app",
                        "r",
                        "missing-package",
                        "{}",
                        "{}",
                    )
                )
        assert len(db.all(FoundryDeploymentRevision)) == 2
        assert len(db.all(FoundryPackageRevision)) == 1
        assert max(row.id for row in db.all(Migration)) == 18


def test_interrupted_nullable_upgrade_restores_schema_rows_and_marker(
    schema17, monkeypatch
):
    from action_server_tests.foundry_historical import historical_rows

    from actions.server.migrations import migration_allow_package_less_canvas

    db = Database(schema17)
    with db.connect():
        db.initialize(get_all_model_classes())
        assert not _nullable(db)
        before = historical_rows(db, 17)
        insert = db.insert

        def interrupt(record):
            if isinstance(record, Migration) and record.id == 18:
                raise RuntimeError("owned failure after nullable DDL")
            return insert(record)

        monkeypatch.setattr(db, "insert", interrupt)
        with pytest.raises(RuntimeError, match="owned failure"):
            with db.transaction():
                migration_allow_package_less_canvas.migrate(db)
        assert not _nullable(db)
        assert historical_rows(db, 17) == before
