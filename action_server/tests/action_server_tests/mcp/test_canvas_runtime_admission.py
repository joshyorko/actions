"""Service-free admission controls; these are not native/browser execution proof."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from action_server_tests.mcp import test_mcp_apps_authoring as bridge


def test_public_mode_refuses_missing_owned_runner(monkeypatch):
    monkeypatch.setenv("ACTIONS_CANVAS_CORE_MODE", "published")
    monkeypatch.setattr(bridge, "CANVAS_OWNED_RUNNER", None, raising=False)
    with pytest.raises(AssertionError, match="owned runner"):
        bridge._canvas_core_mode()


def test_public_mode_has_no_candidate_build_or_override(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Public mode must not build a candidate wheel")

    monkeypatch.setattr(subprocess, "run", forbidden)
    core = bridge._prepare_canvas_core(
        tmp_path / "repository", tmp_path, {}, "published"
    )
    package = (tmp_path / "package.yaml").read_text()
    assert "actions-core=1.0.3" in package
    assert "post-install" not in package and "candidate-core" not in package
    assert not (tmp_path / "candidate-core").exists()
    assert core["mode"] == "published"
    assert "path" not in core and "sha256" not in core
    assert core["measured_members"] == list(bridge.PUBLISHED_CORE_MODULE_SHA256)
    assert core["whole_wheel_authenticated"] is False
    assert core["cold_registry_acquisition"] is False


def test_candidate_mode_keeps_local_wheel_contract(tmp_path, monkeypatch):
    commands = []

    def build(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out-dir") + 1])
        (output / "actions_core-1.0.3-py3-none-any.whl").write_bytes(b"candidate")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", build)
    core = bridge._prepare_canvas_core(
        tmp_path / "repository", tmp_path, {}, "candidate"
    )
    package = (tmp_path / "package.yaml").read_text()
    assert len(commands) == 1 and commands[0][1:3] == ["build", "--wheel"]
    assert "actions-core=1.0.2" in package and "post-install" in package
    assert core["mode"] == "candidate" and Path(core["path"]).is_file()
    assert core["sha256"]


@pytest.mark.parametrize("poison", [None, "member", "version", "ownership", "prefix"])
def test_public_probe_admits_exact_sample_and_rejects_boundary_poisons(
    tmp_path, poison
):
    import hashlib
    import sys
    from types import SimpleNamespace
    from unittest.mock import patch

    probe = bridge._canvas_worker_probe({"mode": "published"})
    # These checkout files equal the three accepted registry sample members.
    # Copy them into a synthetic distribution to exercise the emitted probe;
    # this control does not claim an installed public worker or registry acquisition.
    repository = Path(bridge.__file__).resolve().parents[4]
    modules = {}
    for name, digest in bridge.PUBLISHED_CORE_MODULE_SHA256.items():
        source = repository / "actions/src" / name.replace(".", "/")
        source = (
            source.with_suffix(".py")
            if name.endswith("_metadata")
            else source / "__init__.py"
        )
        payload = source.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == digest
        path = tmp_path / (name.replace(".", "_") + ".py")
        path.write_bytes(payload)
        modules[name] = SimpleNamespace(__file__=str(path))
    if poison == "member":
        Path(modules["actions.mcp"].__file__).write_bytes(b"poison")
    modules["actions"].mcp = modules["actions.mcp"]
    modules["actions.mcp"]._metadata = modules["actions.mcp._metadata"]
    files = [Path(m.__file__) for m in modules.values()]
    distribution = SimpleNamespace(
        version="0.0.0" if poison == "version" else "1.0.3",
        files=files[:-1] if poison == "ownership" else files,
        locate_file=lambda p: p,
    )
    prefix = tmp_path / "elsewhere" if poison == "prefix" else tmp_path
    namespace = {"mcp": SimpleNamespace(tool=lambda **kw: lambda f: f)}
    with patch.dict(sys.modules, modules), patch(
        "importlib.metadata.distribution", return_value=distribution
    ), patch.object(sys, "prefix", str(prefix)):
        exec(probe, namespace)
        if poison is None:
            result = namespace["canvas_fixture_worker_provenance"]()
            assert result["module_hashes"] == bridge.PUBLISHED_CORE_MODULE_SHA256
            assert result["version"] == "1.0.3"
        else:
            with pytest.raises(AssertionError):
                namespace["canvas_fixture_worker_provenance"]()


def test_owned_command_preserves_arguments_result_and_primary_output(
    tmp_path, monkeypatch
):
    command = ["node", "reviewed-cli.js", "test"]
    env = {"SELECTION": "exact"}
    observed = []

    def owner(actual, **kwargs):
        observed.append((actual, kwargs))
        return subprocess.CompletedProcess(
            actual, 7, "primary stdout", "primary stderr"
        )

    monkeypatch.setattr(bridge, "CANVAS_OWNED_RUNNER", owner)
    with pytest.raises(subprocess.CalledProcessError) as failure:
        bridge._canvas_command(
            command, cwd=tmp_path, env=env, timeout=180, mode="published"
        )
    assert observed == [(command, {"cwd": tmp_path, "env": env, "timeout": 180})]
    assert (
        failure.value.stdout == "primary stdout"
        and failure.value.stderr == "primary stderr"
    )
    monkeypatch.setattr(
        bridge,
        "CANVAS_OWNED_RUNNER",
        lambda *args, **kwargs: subprocess.CompletedProcess(["different"], 0, "", ""),
    )
    with pytest.raises(AssertionError, match="command identity"):
        bridge._canvas_command(
            command, cwd=tmp_path, env=env, timeout=180, mode="published"
        )


def test_unknown_mode_fails_before_side_effects(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIONS_CANVAS_CORE_MODE", "typo")
    with pytest.raises(AssertionError, match="Unknown"):
        bridge._canvas_core_mode()
    assert not list(tmp_path.iterdir())


def _browser_frontend(tmp_path):
    frontend = tmp_path / "frontend"
    cli = frontend / "node_modules/@playwright/test/cli.js"
    cli.parent.mkdir(parents=True)
    cli.touch()
    (cli.parent / "package.json").write_text('{"version":"1.62.1"}')
    (frontend / "package-lock.json").write_text(
        '{"packages":{"node_modules/@playwright/test":{"version":"1.62.1"}}}'
    )
    selected = tmp_path / "selected-shell"
    selected.write_bytes(b"owned-browser")
    selected.chmod(0o755)
    return frontend, selected


@pytest.mark.parametrize("launch_fails", [False, True])
def test_public_browser_preserves_pin_and_owns_temp(
    tmp_path, monkeypatch, launch_fails
):
    frontend, selected = _browser_frontend(tmp_path)
    poison = tmp_path / ("long-receipt-" * 12)
    poison.mkdir()
    monkeypatch.setenv("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", str(selected))
    for key in ("TMPDIR", "TMP", "TEMP"):
        monkeypatch.setenv(key, str(poison))
    monkeypatch.setattr(bridge.shutil, "which", lambda name: f"/system/{name}")
    roots = []
    commands = []

    def owned(command, *, cwd, env, timeout):
        commands.append(command)
        assert cwd == frontend
        assert env["CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] == str(selected)
        if command[-1] == "--version":
            return subprocess.CompletedProcess(command, 0, "Chromium sample", "")
        root = Path(env["TMPDIR"])
        roots.append(root)
        assert root.is_dir() and root != poison
        assert env["TMP"] == env["TEMP"] == str(root)
        if os.name != "nt":
            assert root.parent == Path("/tmp") and root.stat().st_mode & 0o777 == 0o700
            assert (
                len(os.fsencode(root / "org.chromium.Chromium.XXXXXX/SingletonSocket"))
                < 108
            )
        assert timeout == 180 and command[1] == str(
            frontend / "node_modules/@playwright/test/cli.js"
        )
        assert "npm" not in command and "--workers" in command
        if launch_fails:
            raise subprocess.CalledProcessError(
                1, command, "primary output", "primary error"
            )
        report = {
            "stats": {"expected": 1, "unexpected": 0, "skipped": 0, "flaky": 0},
            "suites": [
                {
                    "specs": [
                        {
                            "title": "official bridge renders a real Runtime Action result",
                            "tests": [{"results": [{"status": "passed"}]}],
                        }
                    ]
                }
            ],
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(report), "")

    monkeypatch.setattr(bridge, "CANVAS_OWNED_RUNNER", owned, raising=False)
    if launch_fails:
        with pytest.raises(subprocess.CalledProcessError):
            bridge._run_canvas_browser(
                frontend, "http://127.0.0.1:1234/mcp", "published"
            )
    else:
        receipt = bridge._run_canvas_browser(
            frontend, "http://127.0.0.1:1234/mcp", "published"
        )
        assert receipt["path"] == str(selected) and receipt["selection"] == "explicit"
        assert receipt["temporary_root_removed"] is True
    assert len(roots) == 1 and not roots[0].exists()
    assert poison.is_dir() and len(commands) == 2


def test_public_browser_requires_explicit_pin(tmp_path, monkeypatch):
    frontend, _ = _browser_frontend(tmp_path)
    monkeypatch.delenv("CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", raising=False)
    monkeypatch.setattr(bridge.shutil, "which", lambda name: f"/system/{name}")
    with pytest.raises(AssertionError, match="explicit"):
        bridge._run_canvas_browser(frontend, "http://127.0.0.1:1234/mcp", "published")


@pytest.mark.parametrize("poison", ["skipped", "failed", "wrong-name", "extra-case"])
def test_public_browser_rejects_poisoned_report(poison):
    spec = {
        "title": "official bridge renders a real Runtime Action result",
        "tests": [{"results": [{"status": "passed"}]}],
    }
    if poison in {"skipped", "failed"}:
        spec["tests"][0]["results"][0]["status"] = poison
    elif poison == "wrong-name":
        spec["title"] = "other case"
    report = {
        "stats": {"expected": 1, "unexpected": 0, "skipped": 0, "flaky": 0},
        "suites": [{"specs": [spec, spec] if poison == "extra-case" else [spec]}],
    }
    with pytest.raises(AssertionError):
        bridge._assert_canvas_playwright_report(report)


def test_sibling_cache_preserves_actual_snapshot_boundary(tmp_path):
    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._errors_action_server import ActionServerValidationError

    package = tmp_path / "package"
    package.mkdir()
    (package / "canvas_actions.py").write_text('VALUE = "authored"')
    cache = tmp_path / "sibling-cache"
    cache.mkdir()
    payload = cache / "payload"
    payload.mkdir()
    (cache / "directory-link").symlink_to(payload, target_is_directory=True)
    snapshot, _ = ActionPackageHandler(
        str(package), tmp_path / "runtime-data"
    ).prepare_runtime_source_snapshot()
    assert (snapshot / "canvas_actions.py").read_text() == 'VALUE = "authored"'
    assert sorted(p.name for p in snapshot.iterdir()) == ["canvas_actions.py"]
    (package / "uv-cache").symlink_to(cache, target_is_directory=True)
    with pytest.raises(ActionServerValidationError, match="directory symlinks"):
        ActionPackageHandler(
            str(package), tmp_path / "poison-runtime-data"
        ).prepare_runtime_source_snapshot()
