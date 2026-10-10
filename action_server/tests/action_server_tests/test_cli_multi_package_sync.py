import asyncio
import json
from pathlib import Path

from actions.server._selftest import ActionServerClient, ActionServerProcess


def _write_action(package_dir: Path, function_name: str, result: str) -> None:
    package_dir.mkdir(exist_ok=True)
    (package_dir / "package_actions.py").write_text(
        "from actions import action\n\n"
        "@action\n"
        f"def {function_name}() -> str:\n"
        f"    return {result!r}\n",
        encoding="utf-8",
    )


def _action_states(datadir: Path) -> tuple[set[str], dict[str, bool]]:
    from actions.server._models import Action, ActionPackage, load_db

    with load_db(datadir / "shared.sqlite") as db:
        with db.connect():
            packages = {package.name for package in db.all(ActionPackage)}
            actions = {action.name: action.enabled for action in db.all(Action)}
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
        additional_args=[f"--dir={directory}" for directory in directories],
        timeout=30,
    )
    return process


def _visible_openapi_paths(client: ActionServerClient) -> set[str]:
    return set(json.loads(client.get_openapi_json())["paths"])


async def _mcp_tool_names(process: ActionServerProcess) -> set[str]:
    async with process.mcp_client() as session:
        return {tool.name for tool in (await session.list_tools()).tools}


def test_start_sync_treats_repeated_dirs_as_one_desired_set(tmp_path):
    package_a = tmp_path / "package_a"
    package_b = tmp_path / "package_b"
    package_c = tmp_path / "package_c"
    _write_action(package_a, "from_package_a_v1", "A1")
    _write_action(package_b, "from_package_b", "B")
    datadir = tmp_path / "runtime-data"

    def assert_public_catalog(process, expected_actions: set[str]) -> None:
        client = ActionServerClient(process)
        paths = _visible_openapi_paths(client)
        for action_name in expected_actions:
            action_slug = action_name.replace("_", "-")
            assert any(action_slug in path for path in paths)
        tool_names = asyncio.run(_mcp_tool_names(process))
        assert expected_actions <= tool_names

    # The first directory order must retain both packages in shared metadata,
    # HTTP, and MCP catalogs, and both actions must actually execute.
    process = _start_sync(datadir, tmp_path, (package_a, package_b))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b"}
        assert actions == {"from_package_a_v1": True, "from_package_b": True}
        assert_public_catalog(process, set(actions))
        client = ActionServerClient(process)
        for name, result in (("from-package-a-v1", "A1"), ("from-package-b", "B")):
            path = next(
                path
                for path in _visible_openapi_paths(client)
                if f"/{name}/run" in path
            )
            assert json.loads(client.post_get_str(path.lstrip("/"), {})) == result
    finally:
        process.stop()

    # Restart with the reverse ordering, then repeat the same desired set.
    for directories in ((package_b, package_a), (package_a, package_b)):
        process = _start_sync(datadir, tmp_path, directories)
        try:
            packages, actions = _action_states(datadir)
            assert packages == {"package_a", "package_b"}
            assert actions == {"from_package_a_v1": True, "from_package_b": True}
            assert_public_catalog(process, set(actions))
        finally:
            process.stop()

    # A package-local change replaces its previous action without affecting B.
    _write_action(package_a, "from_package_a_v2", "A2")
    process = _start_sync(datadir, tmp_path, (package_a, package_b))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b"}
        assert actions == {
            "from_package_a_v1": False,
            "from_package_a_v2": True,
            "from_package_b": True,
        }
        assert_public_catalog(process, {"from_package_a_v2", "from_package_b"})
    finally:
        process.stop()

    # Omit B from the complete desired set: only B's action becomes disabled.
    process = _start_sync(datadir, tmp_path, (package_a,))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b"}
        assert actions == {
            "from_package_a_v1": False,
            "from_package_a_v2": True,
            "from_package_b": False,
        }
        assert_public_catalog(process, {"from_package_a_v2"})
    finally:
        process.stop()

    # Add C while retaining A; B remains disabled because it is outside the
    # entire desired set for this start invocation.
    _write_action(package_c, "from_package_c", "C")
    process = _start_sync(datadir, tmp_path, (package_c, package_a))
    try:
        packages, actions = _action_states(datadir)
        assert packages == {"package_a", "package_b", "package_c"}
        assert actions == {
            "from_package_a_v1": False,
            "from_package_a_v2": True,
            "from_package_b": False,
            "from_package_c": True,
        }
        assert_public_catalog(process, {"from_package_a_v2", "from_package_c"})
    finally:
        process.stop()


def test_start_sync_rejects_bad_later_package_without_partial_database_update(
    tmp_path,
):
    from actions.server._selftest import actions_server_run

    package_a = tmp_path / "package_a"
    package_b = tmp_path / "package_b"
    _write_action(package_a, "from_package_a_v1", "A1")
    _write_action(package_b, "from_package_b", "B1")
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
        {"from_package_a_v1": True, "from_package_b": True},
    )

    _write_action(package_a, "from_package_a_v2", "A2")
    missing_package_b = tmp_path / "package_b_missing"
    actions_server_run(
        [
            "start",
            "--actions-sync=true",
            f"--dir={package_a}",
            f"--dir={missing_package_b}",
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
        {"from_package_a_v1": True, "from_package_b": True},
    )
