"""Public MCP resource reads retain concrete URI ownership across reloads."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest

from actions.server._selftest import ActionServerProcess

_TRANSITIONS = (
    {
        "name": "direct_to_template",
        "old_uri": "direct://host/value",
        "old_kind": "direct",
        "old_parameter": None,
        "candidate_uri": "direct://host/{item}",
        "candidate_kind": "template",
        "other_candidate_uri": "direct://host/other",
    },
    {
        "name": "template_to_direct",
        "old_uri": "template://host/value",
        "old_kind": "template",
        "old_parameter": "value",
        "candidate_uri": "template://host/value",
        "candidate_kind": "direct",
        "other_candidate_uri": None,
    },
    {
        "name": "template_to_template",
        "old_uri": "overlap://acme/value",
        "old_kind": "template",
        "old_parameter": "acme",
        "candidate_uri": "overlap://acme/{resource}",
        "candidate_kind": "template",
        "other_candidate_uri": "overlap://acme/other",
    },
)


def _route_source(
    routes: tuple[tuple[str, str, str, str | None], ...], *, managed: bool
) -> str:
    lines = ["from actions import mcp", ""]
    for name, uri, value, parameter in routes:
        signature = f"{parameter}: str" if parameter else ""
        result = f'f"{value}:{{{parameter}}}"' if parameter else repr(value)
        lines.extend(
            [
                f"@mcp.resource({uri!r})",
                f"def {name}({signature}) -> str:",
                f"    return {result}",
                "",
            ]
        )
    if managed:
        lines.extend(
            [
                "import hashlib, json, sys",
                "from importlib.metadata import version",
                "from pathlib import Path",
                "import actions",
                "",
                "@mcp.tool()",
                "def managed_worker_identity() -> str:",
                "    return json.dumps({",
                "        'python': str(Path(sys.executable).resolve()),",
                "        'core_origin': str(Path(actions.__file__).resolve()),",
                "        'core_sha256': hashlib.sha256(Path(actions.__file__).read_bytes()).hexdigest(),",
                "        'core_version': version('actions-core'),",
                "    }, sort_keys=True)",
                "",
            ]
        )
    return "\n".join(lines)


def _write_package(
    package: Path,
    routes: tuple[tuple[str, str, str, str | None], ...],
    *,
    managed: bool,
    malformed: bool = False,
) -> None:
    package.mkdir(exist_ok=True)
    if managed:
        (package / "package.yaml").write_text(
            "spec-version: v2\n"
            f"name: {package.name}\n"
            "description: Managed MCP resource-history acceptance fixture.\n"
            "version: 0.0.1\n"
            "dependencies:\n"
            "  conda-forge:\n"
            "    - python=3.12\n"
            "    - uv=0.9.26\n"
            "  pypi:\n"
            "    - actions-core=1.0.2\n",
            encoding="utf-8",
        )
    source = package / "catalog_actions.py"
    temporary = package / "next-source.tmp"
    content = (
        "from actions import mcp\n@mcp.resource('broken://source')\n" "def broken(:\n"
        if malformed
        else _route_source(routes, managed=managed)
    )
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(source)


def _mcp(
    client: httpx.Client, method: str, params: dict[str, object]
) -> dict[str, object]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": method,
    }
    if "name" in params:
        headers["Mcp-Name"] = str(params["name"])
    elif "uri" in params:
        headers["Mcp-Name"] = str(params["uri"])
    response = client.post(
        "/mcp",
        headers=headers,
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
    assert response.status_code in {200, 400}, response.text
    return response.json()


def _read(client: httpx.Client, uri: str) -> dict[str, object]:
    return _mcp(client, "resources/read", {"uri": uri})


def _resource_surface(client: httpx.Client) -> dict[str, object]:
    return {
        method: _mcp(client, method, {})
        for method in ("resources/list", "resources/templates/list")
    }


def _route_is_listed(client: httpx.Client, uri: str, *, template: bool) -> bool:
    surface = _resource_surface(client)
    key = "resourceTemplates" if template else "resources"
    item_key = "uriTemplate" if template else "uri"
    method = "resources/templates/list" if template else "resources/list"
    return any(item.get(item_key) == uri for item in surface[method]["result"][key])


def _read_text(client: httpx.Client, uri: str) -> str:
    result = _read(client, uri)
    assert "error" not in result, result
    return result["result"]["contents"][0]["text"]


def _old_owner_value(transition: dict[str, str | None], revision: str) -> str:
    value = f"owner-a:{revision}:{transition['name']}"
    if transition["old_parameter"]:
        value += f":{transition['old_parameter']}"
    return value


def _assert_mcp_error(client: httpx.Client, uri: str, expected: str) -> None:
    result = _read(client, uri)
    assert "error" in result, result
    assert expected in result["error"]["message"]


def _write_a_routes(
    *, revision: str, include_claims: bool
) -> tuple[tuple[str, str, str, str | None], ...]:
    routes = [
        (
            "control_direct",
            "control://same/value",
            "owner-a:control-direct",
            None,
        ),
        (
            "control_template",
            "control://same/{item}",
            "owner-a:control-template",
            "item",
        ),
    ]
    if include_claims:
        for index, transition in enumerate(_TRANSITIONS):
            uri = transition["old_uri"]
            kind = transition["old_kind"]
            parameter = "tenant" if index == 2 else "item"
            routes.append(
                (
                    f"owner_a_claim_{index}",
                    uri if kind == "direct" else _old_template(index),
                    f"owner-a:{revision}:{transition['name']}",
                    None if kind == "direct" else parameter,
                )
            )
    return tuple(routes)


def _old_template(index: int) -> str:
    return "template://host/{item}" if index == 1 else "overlap://{tenant}/value"


def _write_b_routes(*, phase: str) -> tuple[tuple[str, str, str, str | None], ...]:
    if phase == "candidate":
        routes = [
            (
                f"owner_b_claim_{index}",
                transition["candidate_uri"],
                f"owner-b:candidate:{transition['name']}",
                "item"
                if transition["candidate_kind"] == "template" and index == 0
                else "resource"
                if transition["candidate_kind"] == "template"
                else None,
            )
            for index, transition in enumerate(_TRANSITIONS)
        ]
    elif phase == "recovered":
        routes = []
    else:
        raise ValueError(f"Unknown package B phase: {phase}")
    routes.append(("owner_b_safe", "safe://owner-b/value", "owner-b:safe", None))
    if phase == "recovered":
        routes.append(
            (
                "owner_b_recovered",
                "recovered://owner-b/{item}",
                "owner-b:recovered",
                "item",
            )
        )
    return tuple(routes)


def _start(
    datadir: Path,
    cwd: Path,
    runtime_src: Path,
    package_a: Path,
    package_b: Path,
) -> ActionServerProcess:
    native_executable = os.environ.get(
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"
    )
    process = ActionServerProcess(datadir)
    process.start(
        db_file="catalog.sqlite",
        actions_sync=True,
        cwd=cwd,
        min_processes=0,
        max_processes=2,
        reuse_processes=False,
        add_shutdown_api=True,
        env={
            "NO_PROXY": "*",
            "no_proxy": "*",
            "PYTHONPATH": _runtime_pythonpath(runtime_src, native_executable),
        },
        additional_args=[
            "--address=127.0.0.1",
            "--auto-reload",
            f"--dir={package_a}",
            f"--dir={package_b}",
        ],
        timeout=90 if native_executable else 30,
    )
    if native_executable:
        import psutil

        assert Path(native_executable).is_file()
        actual = Path(psutil.Process(process.process.pid).exe()).resolve()
        assert actual == Path(native_executable).resolve()
    return process


def _runtime_pythonpath(runtime_src: Path, native_executable: str | None) -> str:
    if native_executable:
        return ""
    paths = [str(runtime_src.resolve())]
    for entry in os.environ.get("PYTHONPATH", "").split(os.pathsep):
        if entry:
            paths.append(str(Path(entry).resolve()))
    return os.pathsep.join(dict.fromkeys(paths))


def _stop(process: ActionServerProcess, client: httpx.Client) -> None:
    from actions.server._common.wait_for import wait_for_condition

    response = client.post("/api/shutdown/", json={})
    assert response.status_code == 200, response.text
    wait_for_condition(
        lambda: process.process.returncode is not None,
        msg="Action Server did not exit after controlled shutdown",
        timeout=10,
        sleep=0.05,
    )
    assert process.process.returncode == 1


@pytest.mark.integration_test
def test_cli_resource_owner_history_across_reload_and_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from actions.server._common.wait_for import wait_for_condition

    native_executable = os.environ.get(
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE"
    )
    selected_runtime = os.environ.get("ACTIONS_TEST_RESOURCE_HISTORY_RUNTIME_SOURCE")
    runtime_src = (
        Path(selected_runtime).resolve()
        if selected_runtime
        else (Path(__file__).resolve().parents[2] / "src")
    )
    assert (
        runtime_src.is_absolute()
        and (runtime_src / "actions/server/__init__.py").is_file()
    )
    print("RESOURCE_HISTORY_RUNTIME_SOURCE", runtime_src)
    monkeypatch.setenv("ACTIONS_HOME", str(tmp_path / "actions-home"))
    monkeypatch.setenv("ROBOTS_HOME", str(tmp_path / "robots-home"))
    runtime_tmp = tmp_path / "subprocess-tmp"
    runtime_tmp.mkdir()
    monkeypatch.setenv("TMPDIR", str(runtime_tmp))

    managed = native_executable is not None
    package_a, package_b = tmp_path / "package_a", tmp_path / "package_b"
    datadir = tmp_path / "runtime-data"
    _write_package(
        package_a, _write_a_routes(revision="v1", include_claims=True), managed=managed
    )
    _write_package(package_b, (), managed=managed)

    process = _start(datadir, tmp_path, runtime_src, package_a, package_b)
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{process.port}",
            timeout=30,
            trust_env=False,
        ) as client:
            for transition in _TRANSITIONS:
                assert _read_text(client, transition["old_uri"]) == _old_owner_value(
                    transition, "v1"
                )
            assert (
                _read_text(client, "control://same/value") == "owner-a:control-direct"
            )
            if managed:
                worker = json.loads(
                    client.post(
                        "/api/actions/package-a/managed-worker-identity/run", json={}
                    ).json()
                )
                holotree = (Path(os.environ["ACTIONS_HOME"]) / "holotree").resolve()
                assert Path(worker["python"]).is_relative_to(holotree)
                assert Path(worker["core_origin"]).is_relative_to(holotree)
                assert worker["core_version"] == "1.0.2"
                print(
                    "MANAGED_RESOURCE_HISTORY_WORKER",
                    json.dumps(worker, sort_keys=True),
                )

            # A changed callback under the same package owner remains valid.
            _write_package(
                package_a,
                _write_a_routes(revision="v2", include_claims=True),
                managed=managed,
            )
            wait_for_condition(
                lambda: all(
                    _read_text(client, transition["old_uri"])
                    == _old_owner_value(transition, "v2")
                    for transition in _TRANSITIONS
                ),
                msg="Same-owner resource revision was not admitted",
                timeout=30,
                sleep=0.05,
            )
            assert (
                _read_text(client, "control://same/value") == "owner-a:control-direct"
            )

            # B's changed route shapes are admitted, but reads of old concrete
            # URIs fail before the different package callback can run.
            _write_package(
                package_a,
                _write_a_routes(revision="v2", include_claims=False),
                managed=managed,
            )
            _write_package(
                package_b, _write_b_routes(phase="candidate"), managed=managed
            )
            for transition in _TRANSITIONS:
                template = transition["candidate_kind"] == "template"
                wait_for_condition(
                    lambda transition=transition, template=template: _route_is_listed(
                        client, transition["candidate_uri"], template=template
                    ),
                    msg=f"Candidate route was not published: {transition['name']}",
                    timeout=30,
                    sleep=0.05,
                )
                _assert_mcp_error(
                    client,
                    transition["old_uri"],
                    "conflicting historical owner",
                )
                if transition["other_candidate_uri"]:
                    assert _read_text(
                        client, transition["other_candidate_uri"]
                    ).startswith(f"owner-b:candidate:{transition['name']}")
            assert _read_text(client, "safe://owner-b/value") == "owner-b:safe"

            # Renaming removes the old concrete URI from the active catalog.
            _write_package(
                package_b, _write_b_routes(phase="recovered"), managed=managed
            )
            wait_for_condition(
                lambda: _route_is_listed(
                    client, "recovered://owner-b/{item}", template=True
                ),
                msg="Renamed resource was not published",
                timeout=30,
                sleep=0.05,
            )
            for transition in _TRANSITIONS:
                _assert_mcp_error(client, transition["old_uri"], "No resource found")
            assert (
                _read_text(client, "recovered://owner-b/ok") == "owner-b:recovered:ok"
            )

            # A malformed later package update must preserve the accepted catalog.
            last_good_surface = _resource_surface(client)
            log_offset = len(process.get_stderr())
            _write_package(package_b, (), managed=managed, malformed=True)
            wait_for_condition(
                lambda: "Unable to do auto-reload (actions could not be imported)."
                in process.get_stderr()[log_offset:],
                msg="Watcher did not reject malformed resource package",
                timeout=30,
                sleep=0.05,
            )
            assert process.process.returncode is None
            assert _resource_surface(client) == last_good_surface
            assert (
                _read_text(client, "recovered://owner-b/ok") == "owner-b:recovered:ok"
            )

            _write_package(
                package_b, _write_b_routes(phase="recovered"), managed=managed
            )
            wait_for_condition(
                lambda: _read_text(client, "recovered://owner-b/ok")
                == "owner-b:recovered:ok",
                msg="Corrected resource package did not recover",
                timeout=30,
                sleep=0.05,
            )
            _stop(process, client)
    finally:
        process.stop()

    # The same datadir must retain the old routing projection after restart.
    process = _start(datadir, tmp_path, runtime_src, package_a, package_b)
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{process.port}",
            timeout=30,
            trust_env=False,
        ) as client:
            for transition in _TRANSITIONS:
                _assert_mcp_error(client, transition["old_uri"], "No resource found")
            assert (
                _read_text(client, "control://same/value") == "owner-a:control-direct"
            )

            _write_package(
                package_b, _write_b_routes(phase="candidate"), managed=managed
            )
            for transition in _TRANSITIONS:
                template = transition["candidate_kind"] == "template"
                wait_for_condition(
                    lambda transition=transition, template=template: _route_is_listed(
                        client, transition["candidate_uri"], template=template
                    ),
                    msg=f"Post-restart candidate route missing: {transition['name']}",
                    timeout=30,
                    sleep=0.05,
                )
                _assert_mcp_error(
                    client,
                    transition["old_uri"],
                    "conflicting historical owner",
                )
            assert _read_text(client, "safe://owner-b/value") == "owner-b:safe"
            _stop(process, client)
    finally:
        process.stop()
