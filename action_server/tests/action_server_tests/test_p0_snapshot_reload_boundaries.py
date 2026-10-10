import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_snapshot_excludes_datadir_inside_package(tmp_path):
    from actions.server._action_package_handler import ActionPackageHandler

    root = tmp_path / "package"
    root.mkdir()
    (root / "my_actions.py").write_text("original source")
    data = root / "runtime-data"
    data.mkdir()
    (data / "catalog.sqlite").write_text("private catalog")
    (data / "artifacts").mkdir()
    (data / "artifacts" / "run.json").write_text("private run result")
    first, _ = ActionPackageHandler(str(root), data).prepare_runtime_source_snapshot()
    (data / "catalog.sqlite").write_text("new runtime catalog")
    second, _ = ActionPackageHandler(str(root), data).prepare_runtime_source_snapshot()
    included = sorted(
        str(p.relative_to(first)) for p in first.rglob("*") if p.is_file()
    )
    print("DATADIR_SNAPSHOT", included, "identity_stable=", first == second)
    assert not (first / "runtime-data").exists()
    assert first == second


def test_relative_external_pythonpath_preserves_resolution(tmp_path, monkeypatch):
    from actions.server import _rcc
    from actions.server._action_package_handler import ActionPackageHandler

    root = tmp_path / "package"
    root.mkdir()
    sibling = tmp_path / "shared"
    sibling.mkdir()
    (sibling / "shared.py").write_text('VALUE = "shared"')
    (root / "package.yaml").write_text(
        'name: package\nversion: 1\nspec-version: v2\npythonpath: [".", "../shared"]\n'
    )
    fake_rcc = SimpleNamespace(
        get_package_yaml_hash=lambda *args: "identity",
        create_env_and_get_vars=lambda *args: SimpleNamespace(
            success=True, result=SimpleNamespace(env={})
        ),
    )
    monkeypatch.setattr(_rcc, "get_rcc", lambda: fake_rcc)
    monkeypatch.delenv("ACTIONS_RUNTIME_RCC_PROVIDER", raising=False)
    monkeypatch.delenv("ACTIONS_REAL_RCC_ARTIFACT_TEST", raising=False)
    handler = ActionPackageHandler(str(root), tmp_path / "runtime-data")
    _, original = handler.bootstrap_environment()
    handler.prepare_runtime_source_snapshot()
    _, snapshotted = handler.bootstrap_environment()
    before = Path(original["PYTHONPATH"].split(os.pathsep)[1])
    after = Path(snapshotted["PYTHONPATH"].split(os.pathsep)[1])
    print("EXTERNAL_PYTHONPATH", before, before.exists(), after, after.exists())
    assert after == before
    assert after.exists()


def test_actual_reload_closure_compensates_nondurable_sqlite_commit(
    tmp_path, monkeypatch
):
    from fastapi import FastAPI

    from actions.server import _actions_import, _app, _models, _server
    from actions.server._actions_process_pool import ActionsProcessPool
    from actions.server._api_action_routes import _ActionRoutes
    from actions.server._database import Database
    from actions.server._models import (
        Action,
        ActionPackage,
        McpCatalogName,
        McpResourceRouting,
        get_model_db_rules,
    )
    from actions.server._settings import Settings

    db = Database(tmp_path / "catalog.db")
    db.initialize([ActionPackage, Action, McpCatalogName, McpResourceRouting])
    monkeypatch.setattr(_models, "get_db", lambda: db)
    app = FastAPI()
    monkeypatch.setattr(_app, "get_app", lambda: app)
    old_root = tmp_path / "last-good-source"
    new_root = tmp_path / "candidate-source"
    old_root.mkdir()
    new_root.mkdir()
    (old_root / "my_actions.py").write_text("last-good")
    (new_root / "my_actions.py").write_text("candidate")
    package = ActionPackage("package-id", "package", str(old_root), "old", "{}")
    action = Action(
        "action-id",
        package.id,
        "do_it",
        "last-good docs",
        "my_actions.py",
        1,
        '{"type":"object","properties":{}}',
        '{"type":"string"}',
    )
    candidate_package = ActionPackage(
        "candidate-package-id", "package", str(new_root), "new", "{}"
    )
    candidate_action = Action(
        "candidate-action-id",
        candidate_package.id,
        "candidate_do_it",
        "candidate docs",
        "my_actions.py",
        1,
        '{"type":"object","properties":{}}',
        '{"type":"string"}',
    )
    events = []

    def collect(**kwargs):
        assert not db.in_transaction()
        kwargs["_prepared"].append((candidate_package, [candidate_action]))

        def cleanup():
            import shutil

            events.append("cleanup")
            shutil.rmtree(new_root)

        kwargs["_candidate_cleanup"].append(cleanup)

    monkeypatch.setattr(_actions_import, "import_action_package", collect)
    settings = Settings(
        datadir=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        min_processes=0,
        max_processes=1,
    )
    pool = ActionsProcessPool(settings, {package.id: package}, [action])
    routes = _ActionRoutes("", [])

    class CommitFailure(RuntimeError):
        pass

    failure = CommitFailure("injected nondurable commit failure")

    class Connection:
        def __init__(self, connection):
            self.connection = connection

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def commit(self):
            events.append("failed-commit")
            raise failure

        def rollback(self):
            events.append("sqlite-rollback")
            self.connection.rollback()

    with db.connect():
        db.create_tables(get_model_db_rules())
        with db.transaction():
            db.insert(package)
            db.insert(action)
        routes.register_actions()
        old_catalog_names = db.all(McpCatalogName)
        old_routes = app.router.routes
        old_schema = app.openapi()
        old_catalog = routes.mcp_server_setup_helper._catalog
        old_pool_generation = pool.generation
        connection = db._tlocal.conn
        db._tlocal.conn = Connection(connection)

        def after_import():
            assert db.in_transaction()
            packages = {p.id: p for p in db.all(ActionPackage)}
            closures = _server._reload_action_generation(
                routes, pool, db.all(Action), packages, defer_publication=True
            )
            events.append("staged-pool")
            assert pool.generation == old_pool_generation + 1
            assert pool.actions[0].docs == "candidate docs"
            assert routes.mcp_server_setup_helper._catalog is old_catalog
            assert app.openapi_schema is old_schema
            assert any(
                binding.namespace == "tool" and binding.name == "candidate_do_it"
                for binding in db.all(McpCatalogName)
            )
            return closures

        try:
            with pytest.raises(CommitFailure) as caught:
                _actions_import.import_action_packages(
                    datadir=tmp_path,
                    action_package_dirs=["selected"],
                    disable_not_imported=True,
                    skip_lint=True,
                    whitelist="",
                    after_import=after_import,
                )
            assert caught.value is failure
            assert db.all(ActionPackage)[0].directory == str(old_root)
            assert db.all(Action)[0].docs == "last-good docs"
            assert db.all(McpCatalogName) == old_catalog_names
            assert not connection.in_transaction
            assert not db.in_transaction()
            assert routes.mcp_server_setup_helper._catalog == old_catalog
            assert (
                routes.mcp_server_setup_helper._catalog.tools[0].description
                == "last-good docs"
            )
            assert app.openapi_schema is old_schema
            assert app.router.routes == old_routes
            assert routes.actions[0].docs == "last-good docs"
            assert routes._process_pool_generation == old_pool_generation
            assert pool.generation == old_pool_generation
            assert pool.actions[0].docs == "last-good docs"
            assert pool.action_package_id_to_action_package[
                package.id
            ].directory == str(old_root)
            assert old_root.exists()
            assert not new_root.exists()
            assert events == [
                "staged-pool",
                "failed-commit",
                "sqlite-rollback",
                "cleanup",
            ]
            print(
                "ACTUAL_RELOAD_COMPENSATION",
                events,
                "restored_generation=",
                pool.generation,
            )
        finally:
            db._tlocal.conn = connection
            connection.rollback()


@pytest.mark.integration_test
def test_additive_reimport_removed_action_keeps_executable_last_good(
    tmp_path, monkeypatch
):
    import requests

    from actions.server._models import Action, ActionPackage, load_db
    from actions.server._selftest import ActionServerProcess, actions_server_run

    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "package"
    root.mkdir()
    source = root / "my_actions.py"
    source.write_text(
        'from actions import action\n@action\ndef kept() -> str:\n    return "kept-before"\n@action\ndef removed() -> str:\n    return "last-good-removed"\n'
    )
    data = tmp_path / "runtime-data"

    def import_package():
        actions_server_run(
            [
                "import",
                f"--dir={root}",
                f"--datadir={data}",
                "--db-file=catalog.sqlite",
                "--skip-lint",
            ],
            returncode=0,
            cwd=tmp_path,
            timeout=25,
        )

    import_package()
    with load_db(data / "catalog.sqlite") as db:
        with db.connect():
            old_directory = db.all(ActionPackage)[0].directory
    source.write_text(
        'from actions import action\n@action\ndef kept() -> str:\n    return "kept-after"\n'
    )
    rejected = actions_server_run(
        [
            "import",
            f"--dir={root}",
            f"--datadir={data}",
            "--db-file=catalog.sqlite",
            "--skip-lint",
        ],
        returncode=None,
        cwd=tmp_path,
        timeout=25,
    )
    assert rejected.returncode != 0
    with load_db(data / "catalog.sqlite") as db:
        with db.connect():
            assert [(a.name, a.enabled) for a in db.all(Action)] == [
                ("kept", True),
                ("removed", True),
            ]
            assert db.all(ActionPackage)[0].directory == old_directory
    session = requests.Session()
    session.trust_env = False
    process = ActionServerProcess(data)
    try:
        process.start(
            db_file="catalog.sqlite",
            actions_sync=False,
            cwd=tmp_path,
            min_processes=0,
            max_processes=1,
            reuse_processes=False,
            timeout=25,
            env={"NO_PROXY": "*", "no_proxy": "*"},
        )
        result = session.post(
            f"http://{process.host}:{process.port}/api/actions/package/removed/run",
            json={},
            timeout=20,
        )
        print(
            "ADDITIVE_REJECTED_LAST_GOOD",
            rejected.returncode,
            result.status_code,
            result.text,
        )
        assert result.status_code == 200
        assert result.json() == "last-good-removed"
    finally:
        process.stop()
    process = ActionServerProcess(data)
    try:
        process.start(
            db_file="catalog.sqlite",
            actions_sync=True,
            cwd=root,
            min_processes=0,
            max_processes=1,
            reuse_processes=False,
            timeout=25,
            env={"NO_PROXY": "*", "no_proxy": "*"},
            additional_args=[f"--dir={root}"],
        )
        with load_db(data / "catalog.sqlite") as db:
            with db.connect():
                assert dict((a.name, a.enabled) for a in db.all(Action)) == {
                    "kept": True,
                    "removed": False,
                }
                assert db.all(ActionPackage)[0].directory != old_directory
        result = session.post(
            f"http://{process.host}:{process.port}/api/actions/package/kept/run",
            json={},
            timeout=20,
        )
        assert result.status_code == 200
        assert result.json() == "kept-after"
        removed = session.post(
            f"http://{process.host}:{process.port}/api/actions/package/removed/run",
            json={},
            timeout=20,
        )
        print(
            "SYNC_CONTROL",
            result.status_code,
            result.text,
            "removed=",
            removed.status_code,
        )
        assert removed.status_code == 404
    finally:
        session.close()
        process.stop()


@pytest.mark.integration_test
def test_metadata_collection_cannot_mutate_admitted_snapshot(tmp_path):
    from actions.server._models import ActionPackage, load_db
    from actions.server._selftest import actions_server_run

    root = tmp_path / "package"
    root.mkdir()
    (root / "state.txt").write_text("original generation")
    source = root / "my_actions.py"
    source.write_text(
        'from actions import action\n@action\ndef do_it() -> str:\n    return "last-good"\n'
    )
    data = tmp_path / "runtime-data"
    args = [
        "import",
        f"--dir={root}",
        f"--datadir={data}",
        "--db-file=catalog.sqlite",
        "--skip-lint",
    ]
    actions_server_run(args, returncode=0, cwd=tmp_path, timeout=25)
    with load_db(data / "catalog.sqlite") as db:
        with db.connect():
            old_directory = db.all(ActionPackage)[0].directory
    source.write_text(
        'from pathlib import Path\nfrom actions import action\n(Path(__file__).parent / "state.txt").write_text("mutated during collection")\n@action\ndef do_it() -> str:\n    return "candidate"\n'
    )
    result = actions_server_run(args, returncode=None, cwd=tmp_path, timeout=25)
    assert result.returncode != 0
    with load_db(data / "catalog.sqlite") as db:
        with db.connect():
            assert db.all(ActionPackage)[0].directory == old_directory
    assert (Path(old_directory) / "state.txt").read_text() == "original generation"
    assert (root / "state.txt").read_text() == "original generation"
    snapshots = list((data / ".rcc-runtime-sources").iterdir())
    assert snapshots == [Path(old_directory)]
    print(
        "METADATA_MUTATION_REJECTED",
        result.returncode,
        "preserved_last_good=",
        old_directory,
    )


def test_same_root_datadir_excludes_custom_runtime_state(tmp_path, monkeypatch):
    from actions.server import _settings
    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._settings import Settings

    root = tmp_path / "package"
    root.mkdir()
    (root / "my_actions.py").write_text("original source")
    (root / "custom.sqlite").write_text("private database")
    (root / "custom.sqlite-wal").write_text("private wal")
    artifacts = root / "custom-artifacts"
    artifacts.mkdir()
    (artifacts / "result.json").write_text("private result")
    storage = root / "custom-storage"
    storage.mkdir()
    (storage / "payload.json").write_text("private payload")
    (root / ".api_key").write_text("fake test key")
    (root / "server_log.txt").write_text("private logs")
    settings = Settings(
        datadir=root,
        artifacts_dir=artifacts,
        artifact_storage_root=storage,
        db_file="custom.sqlite",
    )
    monkeypatch.setattr(_settings, "_global_settings", settings)
    first, _ = ActionPackageHandler(str(root), root).prepare_runtime_source_snapshot()
    (root / "custom.sqlite").write_text("runtime changed")
    (artifacts / "result.json").write_text("result changed")
    second, _ = ActionPackageHandler(str(root), root).prepare_runtime_source_snapshot()
    included = sorted(
        str(p.relative_to(first)) for p in first.rglob("*") if p.is_file()
    )
    assert included == ["my_actions.py"]
    assert first == second
    print("SAME_ROOT_RUNTIME_EXCLUSION", included, "stable=", first == second)


def test_absolute_internal_pythonpath_maps_snapshot_external_preserved(
    tmp_path, monkeypatch
):
    from actions.server import _rcc
    from actions.server._action_package_handler import ActionPackageHandler

    root = tmp_path / "package"
    root.mkdir()
    internal = root / "helpers"
    internal.mkdir()
    (internal / "inside.py").write_text('VALUE = "owned"')
    external = tmp_path / "external"
    external.mkdir()
    (external / "outside.py").write_text('VALUE = "outside"')
    (root / "package.yaml").write_text(
        "name: package\nversion: 1\nspec-version: v2\npythonpath: "
        + json.dumps([str(internal), str(external)])
        + "\n"
    )
    fake_rcc = SimpleNamespace(
        get_package_yaml_hash=lambda *args: "identity",
        create_env_and_get_vars=lambda *args: SimpleNamespace(
            success=True, result=SimpleNamespace(env={})
        ),
    )
    monkeypatch.setattr(_rcc, "get_rcc", lambda: fake_rcc)
    monkeypatch.delenv("ACTIONS_RUNTIME_RCC_PROVIDER", raising=False)
    monkeypatch.delenv("ACTIONS_REAL_RCC_ARTIFACT_TEST", raising=False)
    handler = ActionPackageHandler(str(root), tmp_path / "runtime-data")
    snapshot, _ = handler.prepare_runtime_source_snapshot()
    _, env = handler.bootstrap_environment()
    paths = env["PYTHONPATH"].split(os.pathsep)
    assert paths == [str(snapshot / "helpers"), str(external)]
    (internal / "inside.py").write_text('VALUE = "changed owned"')
    (external / "outside.py").write_text('VALUE = "changed external"')
    assert (Path(paths[0]) / "inside.py").read_text() == 'VALUE = "owned"'
    assert (Path(paths[1]) / "outside.py").read_text() == 'VALUE = "changed external"'
    print("ABSOLUTE_PYTHONPATH_BOUNDARY", paths)
