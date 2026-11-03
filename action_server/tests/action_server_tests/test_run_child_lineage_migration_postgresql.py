"""PostgreSQL schema parity for the additive 22-to-23 child-lineage migration."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from actions.server._database import Database
from actions.server.migrations import MIGRATION_ID_TO_NAME, Migration, migrate_db
from actions.server.run_outputs.models import RunChildLineage, Workspace


@pytest.mark.postgresql
def test_postgresql_schema_22_to_23_adds_empty_child_lineage_with_fresh_parity() -> None:
    base_url = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
    if not base_url:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("owned PostgreSQL deployment fixture required")
        pytest.skip("owned PostgreSQL deployment fixture not configured")

    import psycopg

    from action_server_tests.test_database_shared import (
        _drop_postgresql_schema,
        _postgresql_schema_url,
    )
    from actions.server._models import get_all_model_classes, get_model_db_rules

    migrated_schema = "child_lineage_migration_" + uuid4().hex
    fresh_schema = "child_lineage_fresh_" + uuid4().hex
    owner = psycopg.connect(base_url, autocommit=True)
    created: list[str] = []
    try:
        for schema in (migrated_schema, fresh_schema):
            owner.execute(f'CREATE SCHEMA "{schema}"')
            created.append(schema)

        migrated_url = _postgresql_schema_url(base_url, migrated_schema)
        fresh_url = _postgresql_schema_url(base_url, fresh_schema)
        classes = get_all_model_classes()
        rules = get_model_db_rules()
        assert RunChildLineage in classes

        old_db = Database(migrated_url)
        old_db.initialize(classes)
        with old_db.connect(), old_db.transaction():
            for model in classes:
                if model is RunChildLineage:
                    continue
                old_db.execute(old_db.create_table_sql(model, rules))
                for statement in (
                    old_db.create_unique_indexes_sql(model, rules)
                    + old_db.create_non_unique_indexes_sql(model, rules)
                ):
                    old_db.execute(statement)
            old_db.insert(Migration(22, MIGRATION_ID_TO_NAME[22]))
            workspace = Workspace(str(uuid4()), "active", 7)
            old_db.insert(workspace)

        with old_db.connect():
            assert old_db.first(Migration, "SELECT * FROM migration WHERE id=?", [22])
            assert "run_child_lineage" not in old_db.list_table_names()

        assert migrate_db(migrated_url, to_version=23)

        migrated = Database(migrated_url)
        migrated.initialize(classes)
        with migrated.connect():
            assert migrated.first(Migration, "SELECT * FROM migration WHERE id=?", [23])
            assert "run_child_lineage" in migrated.list_table_names()
            assert migrated.all(RunChildLineage) == []
            assert migrated.all(Workspace) == [workspace]
            migrated_columns = migrated.list_table_and_columns()
            migrated_indexes = migrated.list_indexes()

        fresh = Database(fresh_url)
        fresh.initialize(classes)
        fresh.create_tables(rules)
        with fresh.connect(), fresh.transaction():
            fresh.insert(Migration(23, MIGRATION_ID_TO_NAME[23]))
        with fresh.connect():
            assert fresh.all(RunChildLineage) == []
            assert fresh.list_table_and_columns() == migrated_columns
            assert fresh.list_indexes() == migrated_indexes
    finally:
        cleanup_errors = []
        try:
            for schema in reversed(created):
                try:
                    _drop_postgresql_schema(Database(base_url), schema)
                except Exception as exc:
                    cleanup_errors.append(exc)
        finally:
            owner.close()
        if cleanup_errors:
            raise RuntimeError("failed to remove a task-owned migration schema") from cleanup_errors[0]
