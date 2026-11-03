"""The lineage migration adds identity metadata without adopting old Runs."""
import pytest
from action_server_tests.fixtures import database_v0

from actions.server._database import DBError, Database
from actions.server._models import create_db, get_all_model_classes, get_model_db_rules
from actions.server.migrations import CURRENT_VERSION, migrate_db
from actions.server.run_outputs.models import (
    RunChildLineage,
    run_child_identity_digest,
)


def test_migration_preserves_legacy_runs_without_synthetic_lineage(tmp_path):
    old_path = database_v0.__wrapped__(tmp_path)
    old_db = Database(old_path)
    with old_db.connect():
        with old_db.cursor() as cursor:
            old_db.execute_query(
                cursor, "SELECT id,status,inputs,result FROM run ORDER BY id"
            )
            old_runs = cursor.fetchall()

    assert migrate_db(old_path, CURRENT_VERSION)
    with old_db.connect():
        old_db.initialize(get_all_model_classes())
        with old_db.cursor() as cursor:
            old_db.execute_query(
                cursor, "SELECT id,status,inputs,result FROM run ORDER BY id"
            )
            assert cursor.fetchall() == old_runs
        assert old_db.all(RunChildLineage) == []
        migrated_schema = old_db.list_table_and_columns()
        migrated_indexes = old_db.list_indexes()

    with create_db(tmp_path / "fresh.db") as fresh_db:
        assert fresh_db.list_table_and_columns() == migrated_schema
        assert fresh_db.list_indexes() == migrated_indexes


def test_lineage_identity_and_child_are_unique(tmp_path):
    with create_db(tmp_path / "lineage.db") as db:
        lineage = RunChildLineage(
            id="lineage-1",
            workspace_id="workspace-1",
            parent_run_id="parent-1",
            child_run_id="child-1",
            binding_name="summarize",
            logical_key_digest="a" * 64,
            identity_digest=run_child_identity_digest(
                "parent-1", "summarize", "a" * 64
            ),
        )
        with db.transaction():
            db.insert(lineage)

        duplicate_identity = RunChildLineage(
            id="lineage-2",
            workspace_id="workspace-1",
            parent_run_id="parent-1",
            child_run_id="child-2",
            binding_name="summarize",
            logical_key_digest="a" * 64,
            identity_digest=run_child_identity_digest(
                "parent-1", "summarize", "a" * 64
            ),
        )
        with pytest.raises(DBError):
            with db.transaction():
                db.insert(duplicate_identity)

        duplicate_child = RunChildLineage(
            id="lineage-3",
            workspace_id="workspace-1",
            parent_run_id="parent-2",
            child_run_id="child-1",
            binding_name="other-binding",
            logical_key_digest="c" * 64,
            identity_digest=run_child_identity_digest(
                "parent-2", "other-binding", "c" * 64
            ),
        )
        with pytest.raises(DBError):
            with db.transaction():
                db.insert(duplicate_child)

        assert db.all(RunChildLineage) == [lineage]


def test_model_declares_only_stable_identity_indexes():
    rules = get_model_db_rules()
    assert "RunChildLineage.identity_digest" in rules.unique_indexes
    assert "RunChildLineage.child_run_id" in rules.unique_indexes
    assert "RunChildLineage.parent_run_id" in rules.indexes


def test_child_identity_excludes_attempt_identity_but_scopes_binding_and_key():
    identity = run_child_identity_digest("parent-1", "summarize", "a" * 64)
    assert run_child_identity_digest("parent-1", "summarize", "a" * 64) == identity
    assert run_child_identity_digest("parent-1", "other", "a" * 64) != identity
    assert run_child_identity_digest("parent-1", "summarize", "b" * 64) != identity
    assert run_child_identity_digest("parent-2", "summarize", "a" * 64) != identity
