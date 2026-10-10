import asyncio
import json
from pathlib import Path

import pytest
from actions.server._selftest import ActionServerClient, ActionServerProcess


@pytest.fixture(autouse=True)
def _bypass_proxy_for_loopback(monkeypatch, tmp_path):
    # These integration tests address a server bound to localhost. Environment
    # proxy settings in hosted runners must not intercept that local traffic.
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(name, raising=False)
    isolated_home = tmp_path / "test-home"
    isolated_home.mkdir()
    monkeypatch.setenv("HOME", str(isolated_home))
    monkeypatch.setenv("LOCALAPPDATA", str(isolated_home))

    # actions_http reads the user's profile settings, which can configure a
    # proxy that captures even localhost requests. Drop its cached profile so
    # it reads the isolated empty home for this test only.
    import actions_http

    actions_http._get_connection_manager.cache_clear()
    yield
    actions_http._get_connection_manager.cache_clear()


def _write_actions(package_dir: Path, action_results: dict[str, str]) -> None:
    package_dir.mkdir(exist_ok=True)
    source = ["from actions import action", ""]
    for function_name, result in action_results.items():
        source.extend(
            [
                "@action",
                f"def {function_name}() -> str:",
                f"    return {result!r}",
                "",
            ]
        )
    (package_dir / "package_actions.py").write_text("\n".join(source), encoding="utf-8")


def _action_states(datadir: Path) -> tuple[set[str], dict[tuple[str, str], bool]]:
    from actions.server._models import Action, ActionPackage, load_db

    with load_db(datadir / "shared.sqlite") as db:
        with db.connect():
            packages_by_id = {
                package.id: package.name for package in db.all(ActionPackage)
            }
            packages = set(packages_by_id.values())
            actions = {
                (packages_by_id[action.action_package_id], action.name): action.enabled
                for action in db.all(Action)
            }
    return packages, actions


def _start_sync(datadir: Path, cwd: Path, directories: tuple[Path, ...]):
    process = ActionServerProcess(datadir)
    process.start(
        db_file="shared.sqlite",
        actions_sync=True,
        cwd=cwd,
        min_processes=0,
        max_processes=2,
        reuse_processes=False,
        add_shutdown_api=True,
        env={"NO_PROXY": "*", "no_proxy": "*"},
        additional_args=[f"--dir={directory}" for directory in directories],
        timeout=30,
    )
    return process


def _start_existing_imports(datadir: Path, cwd: Path):
    process = ActionServerProcess(datadir)
    process.start(
        db_file="shared.sqlite",
        actions_sync=False,
        cwd=cwd,
        min_processes=0,
        max_processes=2,
        reuse_processes=False,
        add_shutdown_api=True,
        env={"NO_PROXY": "*", "no_proxy": "*"},
        timeout=30,
    )
    return process


async def _mcp_tool_names(process: ActionServerProcess) -> set[str]:
    async with process.mcp_client() as session:
        return {tool.name for tool in (await session.list_tools()).tools}


async def _call_mcp_tool(process: ActionServerProcess, tool_name: str) -> str:
    async with process.mcp_client() as session:
        result = await session.call_tool(tool_name, {})
        return result.content[0].text


def _stop_naturally(process: ActionServerProcess) -> int:
    from actions.server._common.wait_for import wait_for_condition

    try:
        if process.process.returncode is None:
            response = ActionServerClient(process).post_get_response(
                "api/shutdown/", {}
            )
            assert response.status_code == 200
            wait_for_condition(
                lambda: process.process.returncode is not None,
                msg="Action Server did not exit after HTTP shutdown",
                timeout=10,
                sleep=0.05,
            )
        return_code = process.process.returncode
        # The built-in shutdown endpoint interrupts the CLI's main thread;
        # the documented controlled KeyboardInterrupt path exits with 1.
        assert return_code == 1
        return return_code
    finally:
        process.stop()


@pytest.mark.integration_test
def test_additive_import_serves_duplicate_action_names_across_restart(tmp_path):
    from actions.server._selftest import actions_server_run

    package_a = tmp_path / "package_a"
    package_b = tmp_path / "package_b"
    _write_actions(package_a, {"only_a": "A", "do_it": "A-do_it"})
    _write_actions(package_b, {"only_b": "B", "do_it": "B-do_it"})
    datadir = tmp_path / "runtime-data"

    # import is intentionally additive: both independent package identities
    # must survive in one DB before a sync-free server starts.
    for package in (package_a, package_b):
        actions_server_run(
            [
                "import",
                f"--dir={package}",
                "--db-file=shared.sqlite",
                f"--datadir={datadir}",
                "--skip-lint",
            ],
            returncode=0,
            cwd=tmp_path,
        )

    for _ in range(2):
        process = _start_existing_imports(datadir, tmp_path)
        try:
            client = ActionServerClient(process)
            openapi = json.loads(client.get_openapi_json())
            do_it_paths = [
                path for path in openapi["paths"] if path.endswith("/do-it/run")
            ]
            assert set(do_it_paths) == {
                "/api/actions/package-a/do-it/run",
                "/api/actions/package-b/do-it/run",
            }
            operation_ids = {
                openapi["paths"][path]["post"]["operationId"] for path in do_it_paths
            }
            assert len(operation_ids) == 2
            assert asyncio.run(_mcp_tool_names(process)) >= {
                "only_a",
                "only_b",
                "package_a__do_it",
                "package_b__do_it",
            }

            for package_slug, tool_name, result in (
                ("package-a", "package_a__do_it", "A-do_it"),
                ("package-b", "package_b__do_it", "B-do_it"),
            ):
                assert (
                    json.loads(
                        client.post_get_str(f"api/actions/{package_slug}/do-it/run", {})
                    )
                    == result
                )
                assert asyncio.run(_call_mcp_tool(process, tool_name)) == result
        finally:
            _stop_naturally(process)


@pytest.mark.integration_test
def test_start_sync_treats_repeated_dirs_as_one_desired_set(tmp_path):
    package_a = tmp_path / "package_a"
    package_b = tmp_path / "package_b"
    package_c = tmp_path / "package_c"
    _write_actions(package_a, {"from_package_a_v1": "A1", "do_it": "A-do_it"})
    _write_actions(package_b, {"from_package_b": "B", "do_it": "B-do_it"})
    datadir = tmp_path / "runtime-data"

    def assert_public_catalog(
        process, expected_routes: set[str], expected_mcp_tools: set[str]
    ) -> None:
        client = ActionServerClient(process)
        openapi = json.loads(client.get_openapi_json())
        paths = set(openapi["paths"])
        assert expected_routes <= paths
        tool_names = asyncio.run(_mcp_tool_names(process))
        assert expected_mcp_tools <= tool_names
        same_named_routes = [path for path in paths if path.endswith("/do-it/run")]
        expected_same_named_routes = {
            path for path in expected_routes if path.endswith("/do-it/run")
        }
        assert set(same_named_routes) == expected_same_named_routes
        operation_ids = {
            openapi["paths"][path]["post"]["operationId"] for path in same_named_routes
        }
        assert len(operation_ids) == len(same_named_routes)

    # The first directory order must retain both packages in shared metadata,
    # HTTP, and MCP catalogs, and both actions must actually execute.
    process = _start_sync(datadir, tmp_path, (package_a, package_b))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b"}
        assert actions == {
            ("package_a", "from_package_a_v1"): True,
            ("package_a", "do_it"): True,
            ("package_b", "from_package_b"): True,
            ("package_b", "do_it"): True,
        }
        expected_routes = {
            "/api/actions/package-a/from-package-a-v1/run",
            "/api/actions/package-a/do-it/run",
            "/api/actions/package-b/from-package-b/run",
            "/api/actions/package-b/do-it/run",
        }
        expected_mcp_tools = {
            "from_package_a_v1",
            "from_package_b",
            "package_a__do_it",
            "package_b__do_it",
        }
        assert_public_catalog(process, expected_routes, expected_mcp_tools)
        client = ActionServerClient(process)
        for path, result in (
            ("/api/actions/package-a/from-package-a-v1/run", "A1"),
            ("/api/actions/package-b/from-package-b/run", "B"),
            ("/api/actions/package-a/do-it/run", "A-do_it"),
            ("/api/actions/package-b/do-it/run", "B-do_it"),
        ):
            assert json.loads(client.post_get_str(path.lstrip("/"), {})) == result
        assert asyncio.run(_call_mcp_tool(process, "package_a__do_it")) == "A-do_it"
        assert asyncio.run(_call_mcp_tool(process, "package_b__do_it")) == "B-do_it"
    finally:
        _stop_naturally(process)

    # Restart with the reverse ordering, then repeat the same desired set.
    for directories in ((package_b, package_a), (package_a, package_b)):
        process = _start_sync(datadir, tmp_path, directories)
        try:
            packages, actions = _action_states(datadir)
            assert packages == {"package_a", "package_b"}
            assert actions == {
                ("package_a", "from_package_a_v1"): True,
                ("package_a", "do_it"): True,
                ("package_b", "from_package_b"): True,
                ("package_b", "do_it"): True,
            }
            assert_public_catalog(process, expected_routes, expected_mcp_tools)
            client = ActionServerClient(process)
            for package_slug, tool_name, expected_result in (
                ("package-a", "package_a__do_it", "A-do_it"),
                ("package-b", "package_b__do_it", "B-do_it"),
            ):
                path = f"api/actions/{package_slug}/do-it/run"
                assert json.loads(client.post_get_str(path, {})) == expected_result
                assert (
                    asyncio.run(_call_mcp_tool(process, tool_name)) == expected_result
                )
        finally:
            _stop_naturally(process)

    # A package-local change replaces its previous action without affecting B.
    _write_actions(package_a, {"from_package_a_v2": "A2", "do_it": "A-do_it-v2"})
    process = _start_sync(datadir, tmp_path, (package_a, package_b))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b"}
        assert actions == {
            ("package_a", "from_package_a_v1"): False,
            ("package_a", "from_package_a_v2"): True,
            ("package_a", "do_it"): True,
            ("package_b", "from_package_b"): True,
            ("package_b", "do_it"): True,
        }
        assert_public_catalog(
            process,
            {
                "/api/actions/package-a/from-package-a-v2/run",
                "/api/actions/package-a/do-it/run",
                "/api/actions/package-b/from-package-b/run",
                "/api/actions/package-b/do-it/run",
            },
            {
                "from_package_a_v2",
                "from_package_b",
                "package_a__do_it",
                "package_b__do_it",
            },
        )
    finally:
        _stop_naturally(process)

    # Omit B from the complete desired set: only B's action becomes disabled.
    process = _start_sync(datadir, tmp_path, (package_a,))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b"}
        assert actions == {
            ("package_a", "from_package_a_v1"): False,
            ("package_a", "from_package_a_v2"): True,
            ("package_a", "do_it"): True,
            ("package_b", "from_package_b"): False,
            ("package_b", "do_it"): False,
        }
        assert_public_catalog(
            process,
            {
                "/api/actions/package-a/from-package-a-v2/run",
                "/api/actions/package-a/do-it/run",
            },
            {"from_package_a_v2", "do_it"},
        )
    finally:
        _stop_naturally(process)

    # Add C while retaining A; B remains disabled because it is outside the
    # entire desired set for this start invocation.
    _write_actions(package_c, {"from_package_c": "C"})
    process = _start_sync(datadir, tmp_path, (package_c, package_a))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b", "package_c"}
        assert actions == {
            ("package_a", "from_package_a_v1"): False,
            ("package_a", "from_package_a_v2"): True,
            ("package_a", "do_it"): True,
            ("package_b", "from_package_b"): False,
            ("package_b", "do_it"): False,
            ("package_c", "from_package_c"): True,
        }
        assert_public_catalog(
            process,
            {
                "/api/actions/package-a/from-package-a-v2/run",
                "/api/actions/package-a/do-it/run",
                "/api/actions/package-c/from-package-c/run",
            },
            {"from_package_a_v2", "from_package_c", "do_it"},
        )
    finally:
        _stop_naturally(process)


@pytest.mark.integration_test
def test_start_sync_rejects_bad_later_package_without_partial_database_update(
    tmp_path,
):
    from actions.server._selftest import actions_server_run

    package_a = tmp_path / "package_a"
    package_b = tmp_path / "package_b"
    package_c = tmp_path / "package_c"
    _write_actions(package_a, {"from_package_a_v1": "A1"})
    _write_actions(package_b, {"from_package_b": "B1"})
    datadir = tmp_path / "runtime-data"

    for package in (package_a, package_b):
        actions_server_run(
            [
                "import",
                f"--dir={package}",
                "--db-file=shared.sqlite",
                f"--datadir={datadir}",
                "--skip-lint",
            ],
            returncode=0,
            cwd=tmp_path,
        )
    assert _action_states(datadir) == (
        {"package_a", "package_b"},
        {
            ("package_a", "from_package_a_v1"): True,
            ("package_b", "from_package_b"): True,
        },
    )

    _write_actions(package_a, {"from_package_a_v2": "A2"})
    package_c.mkdir()
    (package_c / "package_actions.py").write_text(
        "from actions import action\n"
        "@action\n"
        "def from_package_c() -> str:\n"
        "    return BROKEN_SYNTAX !!!\n",
        encoding="utf-8",
    )
    actions_server_run(
        [
            "start",
            "--actions-sync=true",
            f"--dir={package_a}",
            f"--dir={package_c}",
            "--db-file=shared.sqlite",
            f"--datadir={datadir}",
            "--skip-lint",
        ],
        returncode=1,
        cwd=tmp_path,
    )

    # Failed admission must retain the previously published database state:
    # neither A's newly collected action nor a disable of old A/B is committed.
    assert _action_states(datadir) == (
        {"package_a", "package_b"},
        {
            ("package_a", "from_package_a_v1"): True,
            ("package_b", "from_package_b"): True,
        },
    )

    # The source of B is still intact. After failed admission, restart from the
    # prior database without synchronization and execute B through the server.
    process = _start_existing_imports(datadir, tmp_path)
    try:
        response = ActionServerClient(process).post_get_str(
            "api/actions/package-b/from-package-b/run", {}
        )
        assert json.loads(response) == "B1"
    finally:
        _stop_naturally(process)


@pytest.mark.integration_test
def test_failed_sync_keeps_last_good_unmanaged_package_sources(tmp_path):
    from actions.server._selftest import actions_server_run

    package_a = tmp_path / "package_a"
    package_b = tmp_path / "package_b"
    _write_actions(package_a, {"from_package_a": "A1"})
    _write_actions(package_b, {"from_package_b": "B1"})
    datadir = tmp_path / "runtime-data"

    # Seed the persisted last-good generation through the actual additive CLI.
    for package in (package_a, package_b):
        actions_server_run(
            [
                "import",
                f"--dir={package}",
                "--db-file=shared.sqlite",
                f"--datadir={datadir}",
                "--skip-lint",
            ],
            returncode=0,
            cwd=tmp_path,
        )

    # A now contains a candidate version, while B's previously admitted action
    # is syntactically broken. Its @action marker ensures metadata collection
    # imports this module and rejects the whole start transaction.
    _write_actions(package_a, {"from_package_a": "A2"})
    (package_b / "package_actions.py").write_text(
        "from actions import action\n"
        "@action\n"
        "def from_package_b() -> str:\n"
        "    return BROKEN_SYNTAX !!!\n",
        encoding="utf-8",
    )
    actions_server_run(
        [
            "start",
            "--actions-sync=true",
            f"--dir={package_a}",
            f"--dir={package_b}",
            "--db-file=shared.sqlite",
            f"--datadir={datadir}",
            "--skip-lint",
        ],
        returncode=1,
        cwd=tmp_path,
    )

    # A sync-free restart must run the previously admitted source generation,
    # not just preserve its SQLite rows while reading the mutated files.
    process = _start_existing_imports(datadir, tmp_path)
    try:
        client = ActionServerClient(process)
        for package_slug, action_name, mcp_name, expected in (
            ("package-a", "from-package-a", "from_package_a", "A1"),
            ("package-b", "from-package-b", "from_package_b", "B1"),
        ):
            assert (
                json.loads(
                    client.post_get_str(
                        f"api/actions/{package_slug}/{action_name}/run", {}
                    )
                )
                == expected
            )
            assert asyncio.run(_call_mcp_tool(process, mcp_name)) == expected
    finally:
        _stop_naturally(process)

    # Once B is corrected, the complete desired set should admit both newer
    # source versions and serve those values on a fresh server process.
    _write_actions(package_b, {"from_package_b": "B2"})
    process = _start_sync(datadir, tmp_path, (package_a, package_b))
    try:
        client = ActionServerClient(process)
        for package_slug, action_name, mcp_name, expected in (
            ("package-a", "from-package-a", "from_package_a", "A2"),
            ("package-b", "from-package-b", "from_package_b", "B2"),
        ):
            assert (
                json.loads(
                    client.post_get_str(
                        f"api/actions/{package_slug}/{action_name}/run", {}
                    )
                )
                == expected
            )
            assert asyncio.run(_call_mcp_tool(process, mcp_name)) == expected
    finally:
        _stop_naturally(process)
