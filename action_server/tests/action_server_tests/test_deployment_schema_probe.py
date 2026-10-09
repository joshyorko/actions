"""Executable probe for proposed #129 scoped DDL; this is not a migration."""

from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Iterable

import pytest


@dataclass(frozen=True)
class ForeignKey:
    child: str
    name: str
    child_columns: tuple[str, ...]
    parent: str
    parent_columns: tuple[str, ...]


FKS = (
    ForeignKey(
        "installation_default_workspace",
        "fk_default_workspace",
        ("workspace_id",),
        "workspace",
        ("workspace_id",),
    ),
    ForeignKey(
        "package",
        "fk_package_workspace",
        ("workspace_id",),
        "workspace",
        ("workspace_id",),
    ),
    ForeignKey(
        "package_revision",
        "fk_package_revision_package",
        ("workspace_id", "package_id"),
        "package",
        ("workspace_id", "package_id"),
    ),
    ForeignKey(
        "provider_profile",
        "fk_provider_profile_workspace",
        ("workspace_id",),
        "workspace",
        ("workspace_id",),
    ),
    ForeignKey(
        "provider_profile_revision",
        "fk_provider_revision_owner",
        ("workspace_id", "provider_profile_id"),
        "provider_profile",
        ("workspace_id", "provider_profile_id"),
    ),
    ForeignKey(
        "worker_profile",
        "fk_worker_profile_workspace",
        ("workspace_id",),
        "workspace",
        ("workspace_id",),
    ),
    ForeignKey(
        "worker_profile_revision",
        "fk_worker_revision_owner",
        ("workspace_id", "worker_profile_id"),
        "worker_profile",
        ("workspace_id", "worker_profile_id"),
    ),
    ForeignKey(
        "workspace_policy",
        "fk_workspace_policy_workspace",
        ("workspace_id",),
        "workspace",
        ("workspace_id",),
    ),
    ForeignKey(
        "workspace_policy_revision",
        "fk_policy_revision_owner",
        ("workspace_id", "policy_id"),
        "workspace_policy",
        ("workspace_id", "policy_id"),
    ),
    ForeignKey(
        "deployment",
        "fk_deployment_workspace",
        ("workspace_id",),
        "workspace",
        ("workspace_id",),
    ),
    ForeignKey(
        "deployment_revision",
        "fk_deployment_revision_owner",
        ("workspace_id", "deployment_id"),
        "deployment",
        ("workspace_id", "deployment_id"),
    ),
    ForeignKey(
        "deployment_revision",
        "fk_deployment_revision_parent",
        ("workspace_id", "deployment_id", "previous_revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision",
        "fk_deployment_revision_rollback",
        ("workspace_id", "deployment_id", "rollback_of_revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_package",
        "fk_revision_package_revision",
        ("workspace_id", "deployment_id", "revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_package",
        "fk_revision_package_source",
        ("workspace_id", "package_id", "package_revision_id"),
        "package_revision",
        ("workspace_id", "package_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_binding",
        "fk_binding_deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_binding",
        "fk_binding_revision_package",
        (
            "workspace_id",
            "deployment_id",
            "revision_id",
            "package_id",
            "package_revision_id",
        ),
        "deployment_revision_package",
        (
            "workspace_id",
            "deployment_id",
            "revision_id",
            "package_id",
            "package_revision_id",
        ),
    ),
    ForeignKey(
        "deployment_revision_binding",
        "fk_binding_provider_revision",
        ("workspace_id", "provider_profile_id", "provider_profile_revision_id"),
        "provider_profile_revision",
        ("workspace_id", "provider_profile_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_package_source_provider_ref",
        "fk_source_provider_deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_package_source_provider_ref",
        "fk_source_provider_profile_revision",
        ("workspace_id", "provider_profile_id", "provider_profile_revision_id"),
        "provider_profile_revision",
        ("workspace_id", "provider_profile_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_adapter_artifact_provider_ref",
        "fk_adapter_provider_deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_adapter_artifact_provider_ref",
        "fk_adapter_provider_profile_revision",
        ("workspace_id", "provider_profile_id", "provider_profile_revision_id"),
        "provider_profile_revision",
        ("workspace_id", "provider_profile_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_worker_profile_ref",
        "fk_worker_ref_deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_worker_profile_ref",
        "fk_worker_ref_profile_revision",
        ("workspace_id", "worker_profile_id", "worker_profile_revision_id"),
        "worker_profile_revision",
        ("workspace_id", "worker_profile_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_policy_ref",
        "fk_policy_ref_deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_policy_ref",
        "fk_policy_ref_policy_revision",
        ("workspace_id", "policy_id", "policy_revision_id"),
        "workspace_policy_revision",
        ("workspace_id", "policy_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_request",
        "fk_request_workspace",
        ("workspace_id",),
        "workspace",
        ("workspace_id",),
    ),
    ForeignKey(
        "deployment_revision_request",
        "fk_request_deployment",
        ("workspace_id", "deployment_id"),
        "deployment",
        ("workspace_id", "deployment_id"),
    ),
    ForeignKey(
        "deployment_revision_request",
        "fk_request_parent_revision",
        ("workspace_id", "deployment_id", "parent_revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
    ForeignKey(
        "deployment_revision_request",
        "fk_request_result_revision",
        ("workspace_id", "deployment_id", "result_revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
)

POINTER_FKS = (
    ForeignKey(
        "provider_profile",
        "fk_provider_profile_current_revision",
        ("workspace_id", "provider_profile_id", "current_revision_id"),
        "provider_profile_revision",
        ("workspace_id", "provider_profile_id", "revision_id"),
    ),
    ForeignKey(
        "worker_profile",
        "fk_worker_profile_current_revision",
        ("workspace_id", "worker_profile_id", "current_revision_id"),
        "worker_profile_revision",
        ("workspace_id", "worker_profile_id", "revision_id"),
    ),
    ForeignKey(
        "workspace_policy",
        "fk_workspace_policy_current_revision",
        ("workspace_id", "policy_id", "current_revision_id"),
        "workspace_policy_revision",
        ("workspace_id", "policy_id", "revision_id"),
    ),
    ForeignKey(
        "deployment",
        "fk_deployment_current_revision",
        ("workspace_id", "deployment_id", "current_revision_id"),
        "deployment_revision",
        ("workspace_id", "deployment_id", "revision_id"),
    ),
)

# Types and exact primary/unique tuples needed as referenced keys.
TABLES = {
    "workspace": (
        ("workspace_id",),
        (),
        {"workspace_id": "TEXT NOT NULL", "name": "TEXT NOT NULL"},
        (),
    ),
    "installation_default_workspace": (
        ("singleton_key",),
        (("workspace_id",),),
        {
            "singleton_key": "INTEGER NOT NULL CHECK(singleton_key=1)",
            "workspace_id": "TEXT NOT NULL",
        },
        (),
    ),
    "package": (
        ("workspace_id", "package_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "package_id": "TEXT NOT NULL",
            "name": "TEXT NOT NULL",
        },
        (),
    ),
    "package_revision": (
        ("workspace_id", "package_id", "revision_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "package_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "provider_profile": (
        ("workspace_id", "provider_profile_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "provider_profile_id": "TEXT NOT NULL",
            "current_revision_id": "TEXT",
        },
        (),
    ),
    "provider_profile_revision": (
        ("workspace_id", "provider_profile_id", "revision_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "provider_profile_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "worker_profile": (
        ("workspace_id", "worker_profile_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "worker_profile_id": "TEXT NOT NULL",
            "current_revision_id": "TEXT",
        },
        (),
    ),
    "worker_profile_revision": (
        ("workspace_id", "worker_profile_id", "revision_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "worker_profile_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "workspace_policy": (
        ("workspace_id", "policy_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "policy_id": "TEXT NOT NULL",
            "current_revision_id": "TEXT",
        },
        (),
    ),
    "workspace_policy_revision": (
        ("workspace_id", "policy_id", "revision_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "policy_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment": (
        ("workspace_id", "deployment_id"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "current_revision_id": "TEXT",
            "state": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment_revision": (
        ("workspace_id", "deployment_id", "revision_id"),
        (("workspace_id", "deployment_id", "sequence"),),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
            "sequence": "INTEGER NOT NULL CHECK(sequence>0)",
            "previous_revision_id": "TEXT",
            "rollback_of_revision_id": "TEXT",
            "change_kind": "TEXT NOT NULL",
        },
        (
            "CHECK((change_kind='publish' AND rollback_of_revision_id IS NULL AND ((sequence=1 AND previous_revision_id IS NULL) OR (sequence>1 AND previous_revision_id IS NOT NULL))) OR (change_kind='rollback' AND sequence>1 AND previous_revision_id IS NOT NULL AND rollback_of_revision_id IS NOT NULL))",
        ),
    ),
    "deployment_revision_package": (
        ("workspace_id", "deployment_id", "revision_id", "package_id"),
        (
            (
                "workspace_id",
                "deployment_id",
                "revision_id",
                "package_id",
                "package_revision_id",
            ),
        ),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
            "package_id": "TEXT NOT NULL",
            "package_revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment_revision_binding": (
        (
            "workspace_id",
            "deployment_id",
            "revision_id",
            "package_id",
            "package_revision_id",
            "binding_requirement_id",
        ),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
            "package_id": "TEXT NOT NULL",
            "package_revision_id": "TEXT NOT NULL",
            "binding_requirement_id": "TEXT NOT NULL",
            "provider_profile_id": "TEXT NOT NULL",
            "provider_profile_revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment_revision_package_source_provider_ref": (
        (
            "workspace_id",
            "deployment_id",
            "revision_id",
            "provider_profile_id",
            "provider_profile_revision_id",
        ),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
            "provider_profile_id": "TEXT NOT NULL",
            "provider_profile_revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment_revision_adapter_artifact_provider_ref": (
        (
            "workspace_id",
            "deployment_id",
            "revision_id",
            "purpose",
            "runtime_kind",
            "provider_profile_id",
            "provider_profile_revision_id",
        ),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
            "purpose": "TEXT NOT NULL CHECK(purpose IN ('runtime-artifact','environment-content'))",
            "runtime_kind": "TEXT NOT NULL",
            "provider_profile_id": "TEXT NOT NULL",
            "provider_profile_revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment_revision_worker_profile_ref": (
        (
            "workspace_id",
            "deployment_id",
            "revision_id",
            "worker_profile_id",
            "worker_profile_revision_id",
        ),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
            "worker_profile_id": "TEXT NOT NULL",
            "worker_profile_revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment_revision_policy_ref": (
        (
            "workspace_id",
            "deployment_id",
            "revision_id",
            "policy_id",
            "policy_revision_id",
        ),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "revision_id": "TEXT NOT NULL",
            "policy_id": "TEXT NOT NULL",
            "policy_revision_id": "TEXT NOT NULL",
        },
        (),
    ),
    "deployment_revision_request": (
        ("workspace_id", "idempotency_key"),
        (),
        {
            "workspace_id": "TEXT NOT NULL",
            "idempotency_key": "TEXT NOT NULL",
            "deployment_id": "TEXT NOT NULL",
            "operation_kind": "TEXT NOT NULL",
            "request_digest": "TEXT NOT NULL",
            "parent_revision_id": "TEXT",
            "result_revision_id": "TEXT NOT NULL",
        },
        (
            "CHECK((operation_kind='create' AND parent_revision_id IS NULL) OR (operation_kind<>'create' AND parent_revision_id IS NOT NULL))",
        ),
    ),
}

OWNER_TABLES = (
    "workspace",
    "package",
    "provider_profile",
    "worker_profile",
    "workspace_policy",
    "deployment",
)
REVISION_TABLES = (
    "package_revision",
    "provider_profile_revision",
    "worker_profile_revision",
    "workspace_policy_revision",
    "deployment_revision",
)
JOIN_TABLES = (
    "installation_default_workspace",
    "deployment_revision_package",
    "deployment_revision_binding",
    "deployment_revision_package_source_provider_ref",
    "deployment_revision_adapter_artifact_provider_ref",
    "deployment_revision_worker_profile_ref",
    "deployment_revision_policy_ref",
    "deployment_revision_request",
)


def _fk_sql(fk: ForeignKey) -> str:
    child = ", ".join(fk.child_columns)
    parent = ", ".join(fk.parent_columns)
    return (
        f"CONSTRAINT {fk.name} FOREIGN KEY ({child}) REFERENCES {fk.parent} ({parent})"
    )


def _create_table_sql(table: str, *, pointer_constraints: bool) -> str:
    primary, uniques, columns, checks = TABLES[table]
    defs = [f"{name} {declaration}" for name, declaration in columns.items()]
    defs.append(f"PRIMARY KEY ({', '.join(primary)})")
    defs.extend(f"UNIQUE ({', '.join(unique)})" for unique in uniques)
    defs.extend(checks)
    table_fks = [fk for fk in FKS + POINTER_FKS if fk.child == table]
    if not pointer_constraints:
        table_fks = [fk for fk in table_fks if fk not in POINTER_FKS]
    defs.extend(_fk_sql(fk) for fk in table_fks)
    return f"CREATE TABLE {table} ({', '.join(defs)})"


def _create_sqlite_fixture(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    for table in OWNER_TABLES:
        connection.execute(_create_table_sql(table, pointer_constraints=True))
    for table in REVISION_TABLES + JOIN_TABLES:
        connection.execute(_create_table_sql(table, pointer_constraints=True))


def _postgres_create_statements() -> tuple[list[str], list[str], list[str]]:
    owner_sql = [
        _create_table_sql(table, pointer_constraints=False) for table in OWNER_TABLES
    ]
    revision_sql = [
        _create_table_sql(table, pointer_constraints=False) for table in REVISION_TABLES
    ]
    join_sql = [
        _create_table_sql(table, pointer_constraints=False) for table in JOIN_TABLES
    ]
    pointer_sql = [f"ALTER TABLE {fk.child} ADD {_fk_sql(fk)}" for fk in POINTER_FKS]
    return owner_sql, revision_sql + join_sql, pointer_sql


def _sqlite_foreign_keys(
    connection: sqlite3.Connection,
) -> set[tuple[str, str, tuple[str, ...], tuple[str, ...]]]:
    found = set()
    for table in TABLES:
        rows = connection.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        grouped: dict[int, list[tuple[int, str, str, str]]] = {}
        for fk_id, seq, parent, child_column, parent_column, *_ in rows:
            grouped.setdefault(fk_id, []).append(
                (seq, parent, child_column, parent_column)
            )
        for values in grouped.values():
            values.sort()
            parent = values[0][1]
            found.add(
                (
                    table,
                    parent,
                    tuple(v[2] for v in values),
                    tuple(v[3] for v in values),
                )
            )
    return found


def _expected_foreign_keys() -> set[tuple[str, str, tuple[str, ...], tuple[str, ...]]]:
    return {
        (fk.child, fk.parent, fk.child_columns, fk.parent_columns)
        for fk in FKS + POINTER_FKS
    }


def _populate_sqlite(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN")
    connection.execute("INSERT INTO workspace VALUES ('w1','Workspace 1')")
    connection.execute("INSERT INTO workspace VALUES ('w2','Workspace 2')")
    connection.execute("INSERT INTO installation_default_workspace VALUES (1,'w1')")
    connection.execute("INSERT INTO package VALUES ('w1','p1','Package 1')")
    connection.execute("INSERT INTO package VALUES ('w1','p2','Package 2')")
    connection.execute("INSERT INTO package_revision VALUES ('w1','p1','pr1')")
    connection.execute("INSERT INTO package_revision VALUES ('w1','p2','pr2')")
    connection.execute("INSERT INTO provider_profile VALUES ('w1','pp1',NULL)")
    connection.execute(
        "INSERT INTO provider_profile_revision VALUES ('w1','pp1','ppr1')"
    )
    connection.execute(
        "UPDATE provider_profile SET current_revision_id='ppr1' WHERE workspace_id='w1' AND provider_profile_id='pp1'"
    )
    connection.execute("INSERT INTO worker_profile VALUES ('w1','wp1',NULL)")
    connection.execute("INSERT INTO worker_profile_revision VALUES ('w1','wp1','wpr1')")
    connection.execute(
        "UPDATE worker_profile SET current_revision_id='wpr1' WHERE workspace_id='w1' AND worker_profile_id='wp1'"
    )
    connection.execute("INSERT INTO workspace_policy VALUES ('w1','pol1',NULL)")
    connection.execute(
        "INSERT INTO workspace_policy_revision VALUES ('w1','pol1','polr1')"
    )
    connection.execute(
        "UPDATE workspace_policy SET current_revision_id='polr1' WHERE workspace_id='w1' AND policy_id='pol1'"
    )
    connection.execute("INSERT INTO deployment VALUES ('w1','d1',NULL,'active')")
    connection.execute("INSERT INTO deployment VALUES ('w1','d2',NULL,'active')")
    connection.execute(
        "INSERT INTO deployment_revision VALUES ('w1','d1','r1',1,NULL,NULL,'publish')"
    )
    connection.execute(
        "UPDATE deployment SET current_revision_id='r1' WHERE workspace_id='w1' AND deployment_id='d1'"
    )
    connection.execute(
        "INSERT INTO deployment_revision VALUES ('w1','d1','r2',2,'r1',NULL,'publish')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_package VALUES ('w1','d1','r1','p1','pr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_binding VALUES ('w1','d1','r1','p1','pr1','req1','pp1','ppr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_package_source_provider_ref VALUES ('w1','d1','r1','pp1','ppr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_adapter_artifact_provider_ref VALUES ('w1','d1','r1','environment-content','rcc','pp1','ppr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_worker_profile_ref VALUES ('w1','d1','r1','wp1','wpr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_policy_ref VALUES ('w1','d1','r1','pol1','polr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_request VALUES ('w1','create-1','d1','create','digest',NULL,'r1')"
    )
    # Database constraints do not enforce pointer presence at commit; the
    # repository must create the owner, first revision, and pointer atomically.
    connection.execute("INSERT INTO deployment VALUES ('w1','d3',NULL,'active')")
    connection.commit()
    assert (
        connection.execute(
            "SELECT current_revision_id FROM deployment WHERE deployment_id='d3'"
        ).fetchone()[0]
        is None
    )


def _assert_rejected(
    connection, sql: str, params: Iterable[object], integrity_error: type[Exception]
) -> None:
    connection.execute("SAVEPOINT expected_constraint_rejection")
    try:
        connection.execute(sql, tuple(params))
    except integrity_error as exc:
        assert "constraint" in str(exc).lower() or "foreign key" in str(exc).lower()
        connection.execute("ROLLBACK TO SAVEPOINT expected_constraint_rejection")
        connection.execute("RELEASE SAVEPOINT expected_constraint_rejection")
    else:
        connection.execute("RELEASE SAVEPOINT expected_constraint_rejection")
        raise AssertionError("invalid scoped reference unexpectedly accepted")


def _exercise_negative_rows(connection, integrity_error: type[Exception]) -> None:
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision VALUES ('w1','d2','cross-parent',2,'r1',NULL,'publish')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "UPDATE deployment SET current_revision_id='r1' WHERE workspace_id='w1' AND deployment_id='d2'",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_request VALUES ('w2','foreign-workspace','d1','publish','digest','r1','r1')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision VALUES ('w1','d2','cross-rollback',2,'r1','r1','rollback')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_request VALUES ('w1','missing-parent','d1','publish','digest',NULL,'r1')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_request VALUES ('w1','wrong-parent','d2','publish','digest','r1','r1')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_package VALUES ('w1','d1','r1','p1','foreign-pr')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_binding VALUES ('w1','d1','r1','p2','pr2','req2','pp1','ppr1')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_package_source_provider_ref VALUES ('w1','d1','r1','missing','missing-revision')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_worker_profile_ref VALUES ('w1','d1','r1','missing','missing-revision')",
        (),
        integrity_error,
    )
    _assert_rejected(
        connection,
        "INSERT INTO deployment_revision_policy_ref VALUES ('w1','d1','r1','missing','missing-revision')",
        (),
        integrity_error,
    )


def test_sqlite_proposed_deployment_schema_scopes_ancestry_and_pointer_order():
    connection = sqlite3.connect(":memory:")
    try:
        _create_sqlite_fixture(connection)
        assert _sqlite_foreign_keys(connection) == _expected_foreign_keys()
        _populate_sqlite(connection)
        _exercise_negative_rows(connection, sqlite3.IntegrityError)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        connection.close()


def _postgresql_foreign_keys(
    connection,
) -> set[tuple[str, str, tuple[str, ...], tuple[str, ...]]]:
    query = """
        SELECT child.relname, parent.relname,
               ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(attnum, ord)
                     JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.attnum
                     ORDER BY k.ord),
               ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(attnum, ord)
                     JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.attnum
                     ORDER BY k.ord)
          FROM pg_constraint c
          JOIN pg_class child ON child.oid=c.conrelid
          JOIN pg_class parent ON parent.oid=c.confrelid
         WHERE c.contype='f' AND c.connamespace=current_schema()::regnamespace
    """
    return {
        (row[0], row[1], tuple(row[2]), tuple(row[3]))
        for row in connection.execute(query).fetchall()
    }


@pytest.mark.integration_test
@pytest.mark.postgresql
def test_postgresql_proposed_deployment_schema_scoped_ddl_in_isolated_schema(
    record_testsuite_property,
):
    url = os.environ.get("ACTIONS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("ACTIONS_TEST_DATABASE_URL is not configured")
    psycopg = pytest.importorskip("psycopg")
    schema = f"deployment_probe_{uuid.uuid4().hex}"
    connection = psycopg.connect(url, autocommit=True)
    try:
        connection.execute(f'CREATE SCHEMA "{schema}"')
        connection.execute(f'SET search_path TO "{schema}"')
        owner_sql, later_sql, pointer_sql = _postgres_create_statements()
        with connection.transaction():
            for statement in owner_sql:
                connection.execute(statement)
            for statement in later_sql:
                connection.execute(statement)
            before = _postgresql_foreign_keys(connection)
            assert not any(fk in before for fk in _expected_pointer_foreign_keys())
            for statement in pointer_sql:
                connection.execute(statement)
            assert _postgresql_foreign_keys(connection) == _expected_foreign_keys()
            _populate_postgres(connection)
            _exercise_negative_rows(connection, psycopg.IntegrityError)
    finally:
        connection.execute("SET search_path TO public")
        connection.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        schema_remains = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %s)",
            (schema,),
        ).fetchone()[0]
        record_testsuite_property("postgres_schema", schema)
        record_testsuite_property("postgres_schema_removed", not schema_remains)
        assert not schema_remains
        connection.close()


def _expected_pointer_foreign_keys() -> (
    set[tuple[str, str, tuple[str, ...], tuple[str, ...]]]
):
    return {
        (fk.child, fk.parent, fk.child_columns, fk.parent_columns) for fk in POINTER_FKS
    }


def _populate_postgres(connection) -> None:
    # Same deterministic fixture as SQLite; PostgreSQL transaction already owns it.
    connection.execute(
        "INSERT INTO workspace VALUES ('w1','Workspace 1'),('w2','Workspace 2')"
    )
    connection.execute("INSERT INTO installation_default_workspace VALUES (1,'w1')")
    connection.execute(
        "INSERT INTO package VALUES ('w1','p1','Package 1'),('w1','p2','Package 2')"
    )
    connection.execute(
        "INSERT INTO package_revision VALUES ('w1','p1','pr1'),('w1','p2','pr2')"
    )
    connection.execute("INSERT INTO provider_profile VALUES ('w1','pp1',NULL)")
    connection.execute(
        "INSERT INTO provider_profile_revision VALUES ('w1','pp1','ppr1')"
    )
    connection.execute(
        "UPDATE provider_profile SET current_revision_id='ppr1' WHERE workspace_id='w1' AND provider_profile_id='pp1'"
    )
    connection.execute("INSERT INTO worker_profile VALUES ('w1','wp1',NULL)")
    connection.execute("INSERT INTO worker_profile_revision VALUES ('w1','wp1','wpr1')")
    connection.execute(
        "UPDATE worker_profile SET current_revision_id='wpr1' WHERE workspace_id='w1' AND worker_profile_id='wp1'"
    )
    connection.execute("INSERT INTO workspace_policy VALUES ('w1','pol1',NULL)")
    connection.execute(
        "INSERT INTO workspace_policy_revision VALUES ('w1','pol1','polr1')"
    )
    connection.execute(
        "UPDATE workspace_policy SET current_revision_id='polr1' WHERE workspace_id='w1' AND policy_id='pol1'"
    )
    connection.execute(
        "INSERT INTO deployment VALUES ('w1','d1',NULL,'active'),('w1','d2',NULL,'active')"
    )
    connection.execute(
        "INSERT INTO deployment_revision VALUES ('w1','d1','r1',1,NULL,NULL,'publish')"
    )
    connection.execute(
        "UPDATE deployment SET current_revision_id='r1' WHERE workspace_id='w1' AND deployment_id='d1'"
    )
    connection.execute(
        "INSERT INTO deployment_revision VALUES ('w1','d1','r2',2,'r1',NULL,'publish')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_package VALUES ('w1','d1','r1','p1','pr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_binding VALUES ('w1','d1','r1','p1','pr1','req1','pp1','ppr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_package_source_provider_ref VALUES ('w1','d1','r1','pp1','ppr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_adapter_artifact_provider_ref VALUES ('w1','d1','r1','environment-content','rcc','pp1','ppr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_worker_profile_ref VALUES ('w1','d1','r1','wp1','wpr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_policy_ref VALUES ('w1','d1','r1','pol1','polr1')"
    )
    connection.execute(
        "INSERT INTO deployment_revision_request VALUES ('w1','create-1','d1','create','digest',NULL,'r1')"
    )
