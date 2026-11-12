"""The opt-in test host must never adopt existing state or inherited profiles."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = (
    Path(__file__).resolve().parents[2] / "scripts/serve_managed_acceptance_fixture.py"
)
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux-only test host")


def call(tmp_path, *args, profile=False):
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
    }
    if profile:
        environment["ACTIONS_FOUNDRY_EXECUTION_PROFILE"] = str(tmp_path / "unowned")
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_no_opt_in_creates_no_state(tmp_path):
    state = tmp_path / "state"
    result = call(tmp_path, "--state", str(state))
    assert result.returncode != 0
    assert "explicit --allow-synthetic-owned-fixture" in result.stderr
    assert not state.exists()


def test_fresh_fixture_does_not_adopt_or_change_existing_files(tmp_path):
    state = tmp_path / "existing"
    state.mkdir()
    marker = state / "operator-data"
    marker.write_text("retain")
    result = call(tmp_path, "--state", str(state), "--allow-synthetic-owned-fixture")
    assert result.returncode != 0
    assert list(state.iterdir()) == [marker]
    assert marker.read_text() == "retain"


def test_external_execution_profile_is_refused_before_state_creation(tmp_path):
    state = tmp_path / "state"
    result = call(
        tmp_path, "--state", str(state), "--allow-synthetic-owned-fixture", profile=True
    )
    assert result.returncode != 0
    assert "external execution profiles must be absent" in result.stderr
    assert not state.exists()


def test_symlink_state_is_refused_before_adoption(tmp_path):
    target = tmp_path / "operator"
    target.mkdir()
    state = tmp_path / "state"
    state.symlink_to(target, target_is_directory=True)
    result = call(tmp_path, "--state", str(state), "--allow-synthetic-owned-fixture")
    assert result.returncode != 0
    assert "must not be symlinks" in result.stderr
    assert list(target.iterdir()) == []


def test_live_library_discovers_real_binding_without_admitting_work(tmp_path):
    import asyncio
    import json
    import sqlite3
    import time
    import urllib.error
    import urllib.request

    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    state = tmp_path / "owned"
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
    }
    with (tmp_path / "host.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                str(HELPER),
                "--state",
                str(state),
                "--allow-synthetic-owned-fixture",
            ],
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 20
            while not (state / "ready.json").exists():
                assert process.poll() is None, "owned fixture startup failed"
                assert time.monotonic() < deadline, "owned fixture readiness timeout"
                time.sleep(0.05)
            ready = json.loads((state / "ready.json").read_text())
            assert ready["schema_version"] == "actions.owned-vscode-fixture/v2"
            assert state.stat().st_mode & 0o077 == 0
            assert (state / "bearer").stat().st_mode & 0o077 == 0
            key = (state / "bearer").read_text()
            request = urllib.request.Request(
                ready["endpoint"] + "/api/managed-work-items/v1/schema",
                headers={"authorization": "Bearer " + key},
            )
            while True:
                try:
                    with urllib.request.urlopen(request, timeout=2) as response:
                        assert response.status == 200
                    break
                except urllib.error.URLError:
                    assert (
                        time.monotonic() < deadline
                    ), "owned fixture HTTP readiness timeout"
                    time.sleep(0.05)

            async def discover():
                async with httpx2.AsyncClient(
                    headers={"authorization": "Bearer " + key}, timeout=10
                ) as http:
                    async with streamable_http_client(
                        ready["endpoint"] + "/mcp", http_client=http
                    ) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.discover()
                            opened = await session.call_tool("canvas_open", {})
                            assert not opened.is_error
                            apps = opened.structured_content["applications"]
                            assert len(apps) == 1
                            assert apps[0]["applicationId"] == ready["application_id"]
                            selected = await session.call_tool(
                                "canvas_get", {"appId": ready["application_id"]}
                            )
                            assert not selected.is_error
                            descriptors = selected.structured_content[
                                "invocationDescriptors"
                            ]
                            assert len(descriptors) == 1
                            assert descriptors[0]["bindingId"] == "run"
                            assert descriptors[0]["snapshot"] == ready["snapshot"]
                            assert descriptors[0]["inputMode"] == "claim"
                            assert descriptors[0]["inputQueue"] == ready["queue"]

            asyncio.run(discover())
            with sqlite3.connect(
                "file:" + str(state / "server.db") + "?mode=ro", uri=True
            ) as db:
                assert db.execute("SELECT COUNT(*) FROM run").fetchone()[0] == 0
                assert (
                    db.execute("SELECT COUNT(*) FROM fenced_work_item").fetchone()[0]
                    == 0
                )
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_rcc_mode_refuses_missing_preparation_before_state_creation(tmp_path):
    state = tmp_path / "state"
    result = call(
        tmp_path,
        "--state",
        str(state),
        "--allow-synthetic-owned-fixture",
        "--runtime-kind",
        "rcc",
    )
    assert result.returncode != 0
    assert "genuine prepared receipt and pinned binary" in result.stderr
    assert not state.exists()


def test_direct_mode_refuses_rcc_arguments_without_relabeling(tmp_path):
    state = tmp_path / "state"
    result = call(
        tmp_path,
        "--state",
        str(state),
        "--allow-synthetic-owned-fixture",
        "--prepared-rcc-receipt",
        str(tmp_path / "unowned.json"),
    )
    assert result.returncode != 0
    assert "direct mode cannot accept RCC preparation" in result.stderr
    assert not state.exists()
