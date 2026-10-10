"""Stale tool names must never capture another package's capability."""

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _action(package, name, action_id=None, options=None):
    from actions.server._models import Action

    return Action(
        id=action_id or f"{package}/{name}",
        action_package_id=package,
        name=name,
        docs="Run this action",
        file="actions.py",
        lineno=1,
        input_schema=json.dumps({"type": "object", "properties": {}}),
        output_schema=json.dumps({"type": "string"}),
        options=json.dumps(options or {}),
    )


def _generate(action_package, action, display_name, **kwargs):
    async def execute(**kwargs):
        return action.id

    return execute, execute, {}


@pytest.fixture
def catalog(monkeypatch, request):
    from actions.server import _actions_run, _app
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import ActionPackage, create_db

    app = _app._CustomFastAPI()
    monkeypatch.setattr(_app, "get_app", lambda: app)
    invoked = []

    def generate(action_package, action, display_name, **kwargs):
        async def execute(**kwargs):
            invoked.append(action.id)
            return action.id

        return execute, execute, {}

    monkeypatch.setattr(_actions_run, "generate_func_from_action", generate)
    routes = _ActionRoutes(whitelist=None, endpoint_dependencies=[])
    api_key = getattr(request, "param", None)
    routes.setup_mcp_server(api_key)
    with create_db(":memory:") as db:

        def insert(package, name, action_id=None, options=None):
            with db.transaction():
                if package not in {item.id for item in db.all(ActionPackage)}:
                    db.insert(ActionPackage(package, package, ".", "hash", "{}"))
                action = _action(package, name, action_id, options)
                db.insert(action)
                return action

        with TestClient(app, base_url="http://localhost:8080") as client:

            def mcp_request(method, params=None, *, authorized=True, error=False):
                params = params or {}
                response = client.post(
                    "/mcp",
                    headers={
                        "Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2026-07-28",
                        "Mcp-Method": method,
                        **({"Mcp-Name": params["name"]} if "name" in params else {}),
                        **({"Mcp-Name": params["uri"]} if "uri" in params else {}),
                        **(
                            {"Authorization": f"Bearer {api_key}"}
                            if api_key and authorized
                            else {}
                        ),
                    },
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": method,
                        "params": {
                            **params,
                            "_meta": {
                                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                                "io.modelcontextprotocol/clientCapabilities": {},
                            },
                        },
                    },
                )
                if api_key and not authorized:
                    assert response.status_code in (401, 403)
                    return None
                assert response.status_code == (400 if error else 200), response.text
                return response.json().get("result", response.json())

            yield db, routes, mcp_request, invoked, insert


def _assert_retired(request, invoked, name):
    before = list(invoked)
    result = request("tools/call", {"name": name})
    assert result["isError"] is True
    assert "tools/list" in result["content"][0]["text"]
    assert invoked == before


def test_generated_alias_cannot_be_captured_by_later_literal_name(catalog):
    from actions.server._models import Action, McpCatalogName

    db, routes, request, invoked, insert = catalog
    insert("package1", "do_it")
    insert("package2", "do_it")
    routes.register_actions()
    stale_name = "package1__do_it"
    assert stale_name in {tool["name"] for tool in request("tools/list")["tools"]}
    assert (
        request("tools/call", {"name": stale_name})["content"][0]["text"]
        == "package1/do_it"
    )
    original = db.all(McpCatalogName)
    with pytest.raises(ValueError, match="reserved.*candidate"):
        with db.transaction():
            db.update_by_id(Action, "package2/do_it", {"enabled": False})
            insert("other", stale_name)
            routes.register_actions()
    assert db.all(McpCatalogName) == original
    assert (
        request("tools/call", {"name": stale_name})["content"][0]["text"]
        == "package1/do_it"
    )
    assert "other/package1__do_it" not in invoked
    # A deliberate source rename permits the corrected complete update.
    with db.transaction():
        db.update_by_id(Action, "package2/do_it", {"enabled": False})
        insert("other", "new_action")
        routes.register_actions()
    _assert_retired(request, invoked, stale_name)
    assert (
        request("tools/call", {"name": "new_action"})["content"][0]["text"]
        == "other/new_action"
    )


@pytest.mark.parametrize("retirement", ["disabled", "whitelist", "deleted"])
def test_bare_alias_is_not_reassigned_after_collision_arrival_and_removal(
    catalog, retirement
):
    from actions.server._models import Action, McpCatalogName

    db, routes, request, invoked, insert = catalog
    insert("package1", "do_it")
    routes.register_actions()
    assert request("tools/list")["tools"][0]["name"] == "do_it"
    insert("package2", "do_it")
    routes.register_actions()
    _assert_retired(request, invoked, "do_it")
    original = db.all(McpCatalogName)
    try:
        with pytest.raises(ValueError, match="reserved.*candidate"):
            with db.transaction():
                if retirement == "whitelist":
                    routes.whitelist = "package2/do_it"
                elif retirement == "disabled":
                    db.update_by_id(Action, "package1/do_it", {"enabled": False})
                else:
                    db.execute("DELETE FROM action WHERE id=?", ["package1/do_it"])
                routes.register_actions()
    finally:
        routes.whitelist = None
    assert db.all(McpCatalogName) == original
    _assert_retired(request, invoked, "do_it")
    assert {tool["name"] for tool in request("tools/list")["tools"]} == {
        "package1__do_it",
        "package2__do_it",
    }


@pytest.mark.parametrize("catalog", ["secret"], indirect=True)
def test_retired_alias_does_not_bypass_bearer_authentication(catalog):
    db, routes, request, invoked, insert = catalog
    insert("package1", "do_it")
    routes.register_actions()
    routes.whitelist = "other/*"
    routes.register_actions()
    request("tools/call", {"name": "do_it"}, authorized=False)
    _assert_retired(request, invoked, "do_it")
    assert invoked == []


@pytest.mark.parametrize("namespace", ["resource", "resource-template", "prompt"])
def test_exact_public_key_reassignment_is_rejected_and_rename_recovers(
    catalog, namespace
):
    from actions.server._models import Action, McpCatalogName

    db, routes, request, invoked, insert = catalog
    prompt = namespace == "prompt"
    template = namespace == "resource-template"
    name = "shared_prompt" if prompt else "old_resource"
    uri = "example://stable/{item}" if template else "example://stable/direct"
    options = {"kind": "prompt"} if prompt else {"kind": "resource", "uri": uri}
    method = "prompts/get" if prompt else "resources/read"
    params = {"name": name} if prompt else {"uri": uri.replace("{item}", "one")}

    def text(result):
        if prompt:
            return result["messages"][0]["content"]["text"]
        return result["contents"][0]["text"]

    old = insert("old_package", name, options=options)
    routes.register_actions()
    assert text(request(method, params)) == old.id
    original = db.all(McpCatalogName)
    with pytest.raises(ValueError, match=f"{namespace} key.*reserved"):
        with db.transaction():
            db.update_by_id(Action, old.id, {"enabled": False})
            insert("new_package", name, options=options)
            routes.register_actions()
    assert db.all(McpCatalogName) == original
    assert text(request(method, params)) == old.id
    assert not any(item.startswith("new_package/") for item in invoked)
    corrected_name = "renamed_prompt" if prompt else name
    corrected_options = (
        {"kind": "prompt"}
        if prompt
        else {"kind": "resource", "uri": uri.replace("stable", "corrected")}
    )
    with db.transaction():
        db.update_by_id(Action, old.id, {"enabled": False})
        new = insert("new_package", corrected_name, options=corrected_options)
        routes.register_actions()
    corrected_params = (
        {"name": corrected_name}
        if prompt
        else {"uri": params["uri"].replace("stable", "corrected")}
    )
    assert text(request(method, corrected_params)) == new.id
    retired = request(method, params, error=True)
    assert "error" in retired
    assert ("prompts/list" if prompt else "resources/list") in str(retired)


def test_public_key_namespaces_are_separate(catalog):
    from actions.server._models import McpCatalogName

    db, routes, request, invoked, insert = catalog
    insert("tool_package", "same_name")
    insert("prompt_package", "same_name", options={"kind": "prompt"})
    routes.register_actions()
    assert {item.namespace for item in db.all(McpCatalogName)} == {"tool", "prompt"}
    assert (
        request("tools/call", {"name": "same_name"})["content"][0]["text"]
        == "tool_package/same_name"
    )
    assert (
        request("prompts/get", {"name": "same_name"})["messages"][0]["content"]["text"]
        == "prompt_package/same_name"
    )


def test_long_public_key_uses_fixed_size_index_and_preserves_exact_key(catalog):
    from actions.server._models import McpCatalogName

    db, routes, request, invoked, insert = catalog
    long_uri = "example://stable/" + "".join(str(index) for index in range(2000))
    insert("package1", "long_resource", options={"kind": "resource", "uri": long_uri})
    routes.register_actions()
    binding = db.all(McpCatalogName)[0]
    assert len(binding.id) == 64
    assert binding.namespace == "resource"
    assert binding.name == long_uri
    assert request("resources/list")["resources"][0]["uri"] == long_uri


def test_catalog_key_digest_collision_is_rejected_before_inserting(
    catalog, monkeypatch
):
    import hashlib

    from actions.server._models import McpCatalogName

    db, routes, request, invoked, insert = catalog
    insert("package1", "tool_a")
    insert("package2", "tool_b")
    real_sha256 = hashlib.sha256
    fixed_digest = real_sha256(b"fixed")
    monkeypatch.setattr(hashlib, "sha256", lambda data: fixed_digest)
    with pytest.raises(ValueError, match="digest collision"):
        routes.register_actions()
    assert db.all(McpCatalogName) == []


def test_alias_ownership_survives_restart_and_action_uuid_change(tmp_path, monkeypatch):
    from actions.server import _actions_run
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import ActionPackage, create_db, load_db

    monkeypatch.setattr(_actions_run, "generate_func_from_action", _generate)
    path = tmp_path / "actions.db"
    with create_db(path) as db:
        with db.transaction():
            db.insert(ActionPackage("package1", "package1", ".", "hash", "{}"))
            db.insert(_action("package1", "do_it", "old-uuid"))
        _ActionRoutes(None, []).prepare_actions()
    with load_db(path) as db:
        with pytest.raises(ValueError, match="reserved.*candidate"):
            with db.transaction():
                db.execute("DELETE FROM action")
                db.insert(ActionPackage("package2", "package2", ".", "hash", "{}"))
                db.insert(_action("package2", "do_it"))
                _ActionRoutes(None, []).prepare_actions()
        with db.transaction():
            db.execute("DELETE FROM action")
            db.insert(_action("package1", "do_it", "new-uuid"))
        helper = _ActionRoutes(None, []).prepare_actions()[1]
        assert [tool.name for tool in helper._tools] == ["do_it"]


def test_equivalent_catalogs_ignore_unrelated_reservation_histories(monkeypatch):
    from actions.server import _actions_run
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._models import ActionPackage, McpCatalogName, create_db

    monkeypatch.setattr(_actions_run, "generate_func_from_action", _generate)
    revisions = []
    descriptors = []
    pairs = [("package1", "do_it"), ("package2", "do_it"), ("other", "package1__do_it")]
    for reverse in (False, True):
        with create_db(":memory:") as db:
            with db.transaction():
                if reverse:
                    db.insert(
                        McpCatalogName(
                            "unrelated-history", "tool", "retired", "old", "old"
                        )
                    )
                for package, name in reversed(pairs) if reverse else pairs:
                    db.insert(ActionPackage(package, package, ".", "hash", "{}"))
                    db.insert(_action(package, name))
            helper = _ActionRoutes(None, []).prepare_actions()[1]
            revisions.append(helper.catalog_revision)
            descriptors.append(
                [tool.model_dump(by_alias=True) for tool in helper._tools]
            )
    assert revisions[0] == revisions[1]
    assert descriptors[0] == descriptors[1]


def test_failed_batch_admission_rolls_back_name_reservations(tmp_path, monkeypatch):
    from actions.server import _actions_import, _actions_run
    from actions.server._models import ActionPackage, McpCatalogName, create_db, get_db

    monkeypatch.setattr(_actions_run, "generate_func_from_action", _generate)

    def collect(*, _prepared, **kwargs):
        _prepared.append(
            (
                ActionPackage("package1", "package1", ".", "hash", "{}"),
                [_action("package1", "do_it")],
            )
        )

    def fail_after_validation():
        assert get_db().all(McpCatalogName)
        raise RuntimeError("injected generation failure")

    monkeypatch.setattr(_actions_import, "import_action_package", collect)
    with create_db(":memory:") as db:
        with pytest.raises(RuntimeError, match="generation failure"):
            _actions_import.import_action_packages(
                datadir=tmp_path,
                action_package_dirs=[tmp_path / "package1"],
                disable_not_imported=True,
                skip_lint=True,
                whitelist="",
                after_import=fail_after_validation,
            )
        assert db.all(McpCatalogName) == []
        assert db.all(ActionPackage) == []


def test_invalid_catalog_does_not_reserve_candidate_names(catalog):
    from actions.server._models import McpCatalogName

    db, routes, request, invoked, insert = catalog
    insert("package1", "valid")
    routes.register_actions()
    original = db.all(McpCatalogName)
    insert(
        "package2",
        "invalid",
        options={"_meta": {"ui": {"resourceUri": "missing://ui"}}},
    )
    with pytest.raises(ValueError):
        routes.register_actions()
    assert db.all(McpCatalogName) == original
    assert [tool["name"] for tool in request("tools/list")["tools"]] == ["valid"]


def test_v12_migration_creates_empty_history_matching_fresh_schema(tmp_path):
    from actions.server._models import create_db, load_db
    from actions.server.migrations import CURRENT_VERSION, migrate_db

    path = tmp_path / "old.db"
    with create_db(path) as db:
        expected_columns = db.list_table_and_columns()
        expected_indexes = db.list_indexes()
        with db.transaction():
            db.execute("DROP TABLE mcp_catalog_name")
            db.execute(
                "UPDATE migration SET id=12, name='reconcile_run_columns' WHERE id=13"
            )
    assert migrate_db(path, CURRENT_VERSION)
    with load_db(path) as db:
        assert db.list_table_and_columns() == expected_columns
        assert db.list_indexes() == expected_indexes
        with db.cursor() as cursor:
            db.execute_query(cursor, "SELECT * FROM mcp_catalog_name")
            assert cursor.fetchall() == []


_CHILD = """
import json, sys
from pathlib import Path
from actions.server import _actions_run
from actions.server._api_action_routes import _ActionRoutes
from actions.server._models import load_db

def generate(action_package, action, display_name, **kwargs):
    async def execute(**kwargs):
        return action.id
    return execute, execute, {}
_actions_run.generate_func_from_action = generate
with load_db(sys.argv[1]):
    Path(sys.argv[3]).write_text("ready")
    helper = _ActionRoutes(sys.argv[2], []).prepare_actions()[1]
    print(json.dumps({name: info.action.action_package_id for name, info in helper._tool_name_to_action_info.items()}))
"""


@pytest.mark.parametrize("same_catalog", [True, False])
def test_concurrent_processes_serialize_empty_history_allocation(
    tmp_path, same_catalog
):
    from actions.server._models import ActionPackage, McpCatalogName, create_db, load_db

    path = tmp_path / "actions.db"
    with create_db(path) as db:
        with db.transaction():
            for package in ("package1", "package2"):
                db.insert(ActionPackage(package, package, ".", "hash", "{}"))
                db.insert(_action(package, "do_it"))
    children = []
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [
            str(Path(__file__).resolve().parents[3] / "src"),
            environment.get("PYTHONPATH", ""),
        ]
    )
    try:
        # Both child processes reach catalog preparation while a real SQLite
        # writer holds the empty table. Neither may observe/allocate history
        # until the previous writer's reservation transaction finishes.
        with sqlite3.connect(path, timeout=10) as blocker:
            blocker.execute("BEGIN IMMEDIATE")
            for package in ("package1", "package2"):
                marker = tmp_path / package
                children.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-c",
                            _CHILD,
                            str(path),
                            ("" if same_catalog else f"{package}/do_it"),
                            str(marker),
                        ],
                        env=environment,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                )
            deadline = time.monotonic() + 20
            while not all(
                (tmp_path / package).exists() for package in ("package1", "package2")
            ):
                assert time.monotonic() < deadline
                assert all(child.poll() is None for child in children)
                time.sleep(0.01)
            blocker.commit()
        results = []
        for child in children:
            stdout, stderr = child.communicate(timeout=20)
            if child.returncode != 0:
                assert not same_catalog
                assert "reserved" in stderr and "candidate" in stderr
            else:
                results.append(json.loads(stdout))
        if same_catalog:
            assert len(results) == 2
            assert results[0] == results[1]
        else:
            assert len(results) == 1
        with load_db(path) as db:
            bindings = {item.name: item.package_name for item in db.all(McpCatalogName)}
        for result in results:
            assert all(bindings[name] == package for name, package in result.items())
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=10)
