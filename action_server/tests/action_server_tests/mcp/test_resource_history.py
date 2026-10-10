"""Historical concrete URIs must fail before a different owner is invoked."""

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from action_server_tests.mcp.test_alias_history import _action, _generate
from action_server_tests.mcp.test_alias_history import catalog as _catalog

catalog = _catalog


@pytest.mark.parametrize(
    "old_uri,new_uri,concrete",
    [
        ("example://cross/new", "example://cross/{item}", "example://cross/new"),
        (
            "example://cross-old/{item}",
            "example://cross-old/item",
            "example://cross-old/item",
        ),
        ("example://{tenant}/item", "example://acme/{resource}", "example://acme/item"),
    ],
)
def test_concrete_resource_cannot_change_historical_owner(
    catalog, old_uri, new_uri, concrete
):
    from actions.server._models import Action

    db, routes, request, invoked, insert = catalog
    old = insert("old", "read", options={"kind": "resource", "uri": old_uri})
    insert(
        "control",
        "direct",
        options={"kind": "resource", "uri": "example://control/item"},
    )
    insert(
        "control",
        "template",
        options={"kind": "resource", "uri": "example://control/{item}"},
    )
    routes.register_actions()
    # Deliberately do not read `concrete` first: advertised expansions are protected.
    assert (
        request("resources/read", {"uri": "example://control/item"})["contents"][0][
            "text"
        ]
        == "control/direct"
    )
    with db.transaction():
        db.update_by_id(Action, old.id, {"enabled": False})
        insert("new", "read", options={"kind": "resource", "uri": new_uri})
        routes.register_actions()
    before = list(invoked)
    result = request("resources/read", {"uri": concrete}, error=True)
    assert "conflicting historical owner" in result["error"]["message"]
    assert "does not reauthorize" in result["error"]["message"]
    assert invoked == before
    assert (
        request("resources/read", {"uri": "example://control/item"})["contents"][0][
            "text"
        ]
        == "control/direct"
    )


def test_same_owner_revision_uses_current_callback_and_noop_history(catalog):
    from actions.server._models import Action, McpResourceRouting

    db, routes, request, invoked, insert = catalog
    old = insert(
        "owner", "read", options={"kind": "resource", "uri": "example://same/{item}"}
    )
    routes.register_actions()
    history = db.all(McpResourceRouting)
    with db.transaction():
        db.execute("DELETE FROM action WHERE id=?", [old.id])
        insert(
            "owner",
            "read",
            action_id="new-uuid",
            options={"kind": "resource", "uri": "example://same/{item}"},
        )
        routes.register_actions()
    assert db.all(McpResourceRouting) == history
    assert (
        request("resources/read", {"uri": "example://same/one"})["contents"][0]["text"]
        == "new-uuid"
    )
    assert invoked == ["new-uuid"]
    revision = routes.mcp_server_setup_helper.catalog_revision
    with db.transaction():
        db.update_by_id(Action, "new-uuid", {"docs": "updated metadata"})
        routes.register_actions()
    assert routes.mcp_server_setup_helper.catalog_revision != revision
    assert db.all(McpResourceRouting) == history
    with db.transaction():
        db.update_by_id(
            Action,
            "new-uuid",
            {
                "options": json.dumps(
                    {"kind": "resource", "uri": "example://same/{resource}"}
                )
            },
        )
        routes.register_actions()
    assert len(db.all(McpResourceRouting)) == 2
    assert (
        request("resources/read", {"uri": "example://same/one"})["contents"][0]["text"]
        == "new-uuid"
    )
    history = db.all(McpResourceRouting)
    with db.transaction():
        db.update_by_id(Action, "new-uuid", {"enabled": False})
        routes.register_actions()
    before = list(invoked)
    error = request("resources/read", {"uri": "example://same/one"}, error=True)
    assert "No resource found" in error["error"]["message"]
    assert invoked == before
    assert db.all(McpResourceRouting) == history


def _read(helper, uri):
    return asyncio.run(
        helper._read_resource(SimpleNamespace(request=None), SimpleNamespace(uri=uri))
    )


def test_resource_history_survives_restart(tmp_path, monkeypatch):
    from mcp import MCPError

    from actions.server import _actions_run
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import ActionPackage, create_db, load_db

    monkeypatch.setattr(_actions_run, "generate_func_from_action", _generate)
    path = tmp_path / "catalog.db"
    with create_db(path) as db:
        with db.transaction():
            db.insert(ActionPackage("old", "old", ".", "hash", "{}"))
            db.insert(
                _action(
                    "old",
                    "read",
                    options={"kind": "resource", "uri": "example://{tenant}/item"},
                )
            )
        _ActionRoutes(None, []).prepare_actions()
    with load_db(path) as db:
        with db.transaction():
            db.execute("DELETE FROM action")
            db.insert(ActionPackage("new", "new", ".", "hash", "{}"))
            db.insert(
                _action(
                    "new",
                    "read",
                    options={"kind": "resource", "uri": "example://acme/{resource}"},
                )
            )
        helper = _ActionRoutes(None, []).prepare_actions()[1]
        with pytest.raises(MCPError, match="conflicting historical owner"):
            _read(helper, "example://acme/item")
        assert _read(helper, "example://acme/other").contents[0].text == "new/read"


@pytest.mark.parametrize(
    "bound", ["MAX_PROJECTIONS", "MAX_ROUTE_ROWS", "MAX_PAYLOAD_BYTES"]
)
def test_capacity_rejects_complete_update_but_allows_noop(catalog, monkeypatch, bound):
    from actions.server._models import Action, McpCatalogName, McpResourceRouting
    from actions.server.mcp import resource_routing

    db, routes, request, invoked, insert = catalog
    old = insert(
        "old", "read", options={"kind": "resource", "uri": "example://old/item"}
    )
    routes.register_actions()
    history = db.all(McpResourceRouting)
    names = db.all(McpCatalogName)
    maximum = (
        len(history[0].routing_json.encode("utf-8"))
        if bound == "MAX_PAYLOAD_BYTES"
        else 1
    )
    monkeypatch.setattr(resource_routing, bound, maximum)
    routes.register_actions()  # Duplicate projection remains allowed at capacity.
    old_catalog = routes.mcp_server_setup_helper._catalog
    with pytest.raises(ValueError, match="capacity"):
        with db.transaction():
            db.update_by_id(Action, old.id, {"enabled": False})
            insert(
                "new", "read", options={"kind": "resource", "uri": "example://new/item"}
            )
            routes.register_actions()
    assert routes.mcp_server_setup_helper._catalog is old_catalog
    assert db.all(McpResourceRouting) == history
    assert db.all(McpCatalogName) == names
    assert (
        request("resources/read", {"uri": "example://old/item"})["contents"][0]["text"]
        == "old/read"
    )


def test_failed_commit_rolls_back_projection_and_keeps_published_catalog(catalog):
    from actions.server._models import McpCatalogName, McpResourceRouting

    db, routes, request, invoked, insert = catalog
    insert("old", "read", options={"kind": "resource", "uri": "example://old/item"})
    routes.register_actions()
    history, names = db.all(McpResourceRouting), db.all(McpCatalogName)
    previous_catalog = routes.mcp_server_setup_helper._catalog
    failure = RuntimeError("injected nondurable commit failure")
    connection = db._tlocal.conn
    events = []

    class Connection:
        def __getattr__(self, name):
            return getattr(connection, name)

        def commit(self):
            events.append("failed-commit")
            raise failure

        def rollback(self):
            events.append("rollback")
            connection.rollback()

    db._tlocal.conn = Connection()
    try:
        with pytest.raises(RuntimeError) as caught:
            with db.transaction():
                insert(
                    "new",
                    "read",
                    options={"kind": "resource", "uri": "example://new/item"},
                )
                routes.prepare_actions()  # Staged helper is never published before commit.
                assert len(db.all(McpResourceRouting)) == len(history) + 1
        assert caught.value is failure
        assert events == ["failed-commit", "rollback"]
        assert db.all(McpResourceRouting) == history
        assert db.all(McpCatalogName) == names
        assert routes.mcp_server_setup_helper._catalog is previous_catalog
    finally:
        db._tlocal.conn = connection
    assert (
        request("resources/read", {"uri": "example://old/item"})["contents"][0]["text"]
        == "old/read"
    )


@pytest.mark.parametrize(
    "corruption", ["json", "version", "digest", "noncanonical", "regex"]
)
def test_malformed_history_fails_closed(catalog, corruption):
    from hashlib import sha256

    from actions.server._models import McpResourceRouting
    from actions.server.mcp.resource_routing import _DIGEST_DOMAIN

    db, routes, request, invoked, insert = catalog
    insert("owner", "read", options={"kind": "resource", "uri": "example://one/item"})
    routes.register_actions()
    row = db.all(McpResourceRouting)[0]
    payload = row.routing_json
    if corruption == "json":
        payload = "{"
    elif corruption == "version":
        payload = payload.replace(
            '"matcherPolicyVersion":1', '"matcherPolicyVersion":2'
        )
    elif corruption == "noncanonical":
        payload += " "
    elif corruption == "regex":
        payload = '{"matcherPolicyVersion":1,"resources":[],"templates":[["example://[/{item}","owner","read"]]}'
    with db.transaction():
        db.execute("DELETE FROM mcp_resource_routing")
        digest = (
            "wrong"
            if corruption == "digest"
            else sha256(_DIGEST_DOMAIN + payload.encode()).hexdigest()
        )
        db.insert(McpResourceRouting(digest, payload))
    old_catalog = routes.mcp_server_setup_helper._catalog
    with pytest.raises(ValueError, match="history"):
        routes.register_actions()
    assert routes.mcp_server_setup_helper._catalog is old_catalog


def test_projection_digest_collision_is_rejected(catalog, monkeypatch):
    from actions.server._models import McpResourceRouting
    from actions.server.mcp import resource_routing

    class Digest:
        def hexdigest(self):
            return "0" * 64

    monkeypatch.setattr(resource_routing, "sha256", lambda data: Digest())
    db, routes, request, invoked, insert = catalog
    insert("owner", "one", options={"kind": "resource", "uri": "example://one/item"})
    routes.register_actions()
    history = db.all(McpResourceRouting)
    insert("owner", "two", options={"kind": "resource", "uri": "example://two/item"})
    with pytest.raises(ValueError, match="digest collision"):
        routes.register_actions()
    assert db.all(McpResourceRouting) == history


def test_overcapacity_history_is_rejected_before_loading_payloads(catalog, monkeypatch):
    from actions.server._models import McpResourceRouting
    from actions.server.mcp import resource_routing

    db, routes, request, invoked, insert = catalog
    insert("owner", "read", options={"kind": "resource", "uri": "example://one/item"})
    routes.register_actions()
    monkeypatch.setattr(resource_routing, "MAX_PROJECTIONS", 0)
    original_all = db.all

    def all_rows(model, **kwargs):
        assert model is not McpResourceRouting, "oversized payloads must not be loaded"
        return original_all(model, **kwargs)

    monkeypatch.setattr(db, "all", all_rows)
    with pytest.raises(ValueError, match="exceeds capacity"):
        routes.register_actions()


def test_capacity_counts_actual_utf8_bytes(catalog, monkeypatch):
    from actions.server._models import McpResourceRouting
    from actions.server.mcp import resource_routing

    db, routes, request, invoked, insert = catalog
    insert("owner", "read", options={"kind": "resource", "uri": "example://one/é"})
    routes.register_actions()
    payload = db.all(McpResourceRouting)[0].routing_json
    assert len(payload.encode("utf-8")) > len(payload)
    monkeypatch.setattr(resource_routing, "MAX_PAYLOAD_BYTES", len(payload))
    with pytest.raises(ValueError, match="exceeds capacity"):
        routes.register_actions()


def test_missing_routing_table_never_bypasses_history(catalog):
    from actions.server._database import DBError

    db, routes, request, invoked, insert = catalog
    insert("owner", "read", options={"kind": "resource", "uri": "example://one/item"})
    routes.register_actions()
    previous = routes.mcp_server_setup_helper._catalog
    with db.transaction():
        db.execute("DROP TABLE mcp_resource_routing")
    with pytest.raises(DBError, match="mcp_resource_routing"):
        routes.register_actions()
    assert routes.mcp_server_setup_helper._catalog is previous


def test_equivalent_resource_catalogs_ignore_history_and_import_order(monkeypatch):
    from actions.server import _actions_run
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import ActionPackage, create_db

    monkeypatch.setattr(_actions_run, "generate_func_from_action", _generate)
    revisions, descriptors = [], []
    for reverse in (False, True):
        with create_db(":memory:") as db:
            with db.transaction():
                db.insert(ActionPackage("owner", "owner", ".", "hash", "{}"))
                if reverse:
                    db.insert(
                        _action(
                            "owner",
                            "retired",
                            options={
                                "kind": "resource",
                                "uri": "example://unrelated/{item}",
                            },
                        )
                    )
            if reverse:
                _ActionRoutes(None, []).prepare_actions()
                with db.transaction():
                    db.execute("DELETE FROM action")
            with db.transaction():
                pairs = [
                    ("direct", "example://active/item"),
                    ("template", "example://active/{item}"),
                ]
                for name, uri in reversed(pairs) if reverse else pairs:
                    db.insert(
                        _action("owner", name, options={"kind": "resource", "uri": uri})
                    )
            helper = _ActionRoutes(None, []).prepare_actions()[1]
            revisions.append(helper.catalog_revision)
            descriptors.append((helper._resources, helper._resource_templates))
    assert revisions[0] == revisions[1]
    assert descriptors[0] == descriptors[1]


@pytest.mark.parametrize("catalog", ["secret"], indirect=True)
def test_routing_history_keeps_authentication_and_whitelist_enforcement(catalog):
    from actions.server._models import Action

    db, routes, request, invoked, insert = catalog
    old = insert(
        "old", "read", options={"kind": "resource", "uri": "example://{tenant}/item"}
    )
    routes.register_actions()
    with db.transaction():
        db.update_by_id(Action, old.id, {"enabled": False})
        insert(
            "new",
            "read",
            options={"kind": "resource", "uri": "example://acme/{resource}"},
        )
        routes.register_actions()
    before = list(invoked)
    request("resources/read", {"uri": "example://acme/item"}, authorized=False)
    request("resources/read", {"uri": "example://acme/item"}, error=True)
    assert invoked == before
    routes.whitelist = "old/read"
    routes.register_actions()
    error = request("resources/read", {"uri": "example://acme/other"}, error=True)
    assert "No resource found" in error["error"]["message"]
    assert invoked == before


def test_existing_regex_literal_behavior_is_retained():
    from actions.server.mcp.resource_routing import ResourceRoutingProjection

    projection = ResourceRoutingProjection(
        (), (("example://host.test/{item}", "owner", "read"),)
    )
    assert projection.owner("example://hostXtest/one") == ("owner", "read")
    assert projection.owner("prefix-example://hostXtest/one") is None


def test_v13_migration_preserves_exact_keys_but_starts_empty_routing_history(tmp_path):
    from actions.server._models import (
        McpCatalogName,
        McpResourceRouting,
        create_db,
        load_db,
    )
    from actions.server.migrations import CURRENT_VERSION, migrate_db

    path = tmp_path / "old.db"
    with create_db(path) as db:
        columns, indexes = db.list_table_and_columns(), db.list_indexes()
        with db.transaction():
            db.insert(McpCatalogName("old-key", "tool", "old", "owner", "read"))
            db.execute("DROP TABLE mcp_resource_routing")
            # Restore the real pre-14 schema, including absence of migration 15.
            for table in (
                "run_output",
                "run_attempt",
                "run_pin",
                "run_access_grant",
                "run_admission",
                "workspace",
            ):
                db.execute("DROP TABLE " + table)
            db.execute("DELETE FROM migration")
            db.execute(
                "INSERT INTO migration(id,name) VALUES(13,'add_mcp_catalog_names')"
            )
    assert migrate_db(path, CURRENT_VERSION)
    with load_db(path) as db:
        assert db.list_table_and_columns() == columns
        assert db.list_indexes() == indexes
        assert db.all(McpResourceRouting) == []
        assert db.all(McpCatalogName)[0].name == "old"


_CHILD = """
import sys
from pathlib import Path
from actions.server import _actions_run
from actions.server._api_action_routes import _ActionRoutes
from actions.server._models import load_db
def generate(*args, **kwargs):
    async def execute(**kwargs):
        return "unused"
    return execute, execute, {}
_actions_run.generate_func_from_action = generate
with load_db(sys.argv[1]):
    Path(sys.argv[3]).write_text("ready")
    helper = _ActionRoutes(sys.argv[2], []).prepare_actions()[1]
    print(len(helper._catalog.resource_routing_history))
"""


@pytest.mark.parametrize("same_catalog", [True, False])
def test_concurrent_processes_retain_serialized_routing_history(
    tmp_path, monkeypatch, same_catalog
):
    from mcp import MCPError

    from actions.server import _actions_run
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import (
        ActionPackage,
        McpResourceRouting,
        create_db,
        load_db,
    )

    path = tmp_path / "catalog.db"
    with create_db(path) as db:
        with db.transaction():
            for package, uri in [
                ("one", "example://{tenant}/item"),
                ("two", "example://acme/{resource}"),
            ]:
                db.insert(ActionPackage(package, package, ".", "hash", "{}"))
                db.insert(
                    _action(package, "read", options={"kind": "resource", "uri": uri})
                )
    children = []
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(Path(__file__).resolve().parents[3] / "src"),
            environment.get("PYTHONPATH", ""),
        ]
    )
    try:
        with sqlite3.connect(path, timeout=10) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            for index in range(2):
                marker = tmp_path / str(index)
                children.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-c",
                            _CHILD,
                            str(path),
                            "one/read" if same_catalog or index == 0 else "two/read",
                            str(marker),
                        ],
                        env=environment,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                )
            deadline = time.monotonic() + 20
            while not all((tmp_path / str(index)).exists() for index in range(2)):
                assert time.monotonic() < deadline
                assert all(child.poll() is None for child in children)
                time.sleep(0.01)
            blocker.commit()
        counts = []
        for child in children:
            stdout, stderr = child.communicate(timeout=20)
            assert child.returncode == 0, stderr
            counts.append(int(stdout.strip()))
        assert sorted(counts) == ([1, 1] if same_catalog else [1, 2])
        monkeypatch.setattr(_actions_run, "generate_func_from_action", _generate)
        with load_db(path) as db:
            assert len(db.all(McpResourceRouting)) == (1 if same_catalog else 2)
            if not same_catalog:
                for package in ("one", "two"):
                    helper = _ActionRoutes(f"{package}/read", []).prepare_actions()[1]
                    with pytest.raises(MCPError, match="conflicting historical owner"):
                        _read(helper, "example://acme/item")
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=10)
