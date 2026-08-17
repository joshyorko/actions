import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

TOOLKIT_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = TOOLKIT_ROOT.parent
sys.path.insert(0, str(TOOLKIT_ROOT))
import toolkit  # noqa: E402


def test_manifest_defines_cross_platform_developer_tasks() -> None:
    manifest = yaml.safe_load((TOOLKIT_ROOT / "toolkit.yaml").read_text())

    assert set(manifest["devTasks"]) == {
        "Doctor",
        "Bootstrap",
        "Test",
        "ToolkitTest",
        "Lint",
        "Typecheck",
        "Docs",
        "CheckAll",
        "FrontendTest",
        "InstallCommunity",
    }
    assert manifest["ignoreFiles"] == ["../.gitignore"]
    assert manifest["environmentConfigs"] == [
        "setup_windows_amd64.yaml",
        "setup.yaml",
    ]


def test_windows_toolchain_uses_available_jq_distribution() -> None:
    windows_setup = yaml.safe_load(
        (TOOLKIT_ROOT / "setup_windows_amd64.yaml").read_text()
    )
    generic_setup = yaml.safe_load((TOOLKIT_ROOT / "setup.yaml").read_text())

    assert windows_setup["channels"] == generic_setup["channels"]
    assert windows_setup["dependencies"] == [
        "m2w64-jq=1.6" if dependency == "jq=1.7.1" else dependency
        for dependency in generic_setup["dependencies"]
    ]


def test_toolkit_workflow_cache_tracks_all_environment_configs() -> None:
    workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "developer_toolkit.yml"
    ).read_text()

    assert "'developer/setup_windows_amd64.yaml'" in workflow


def test_rcc_toolchain_includes_external_test_utilities() -> None:
    setup = yaml.safe_load((TOOLKIT_ROOT / "setup.yaml").read_text())

    assert "jq=1.7.1" in setup["dependencies"]


def test_ci_verifies_bootstrap_environment_isolation() -> None:
    workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "developer_toolkit.yml"
    ).read_text()

    bootstrap = workflow.index("- name: Bootstrap toolkit (Linux)")
    isolation = workflow.index("- name: Verify isolated package environments (Linux)")
    package_smoke = workflow.index("- name: Package task smoke (Linux)")
    assert bootstrap < isolation < package_smoke
    assert 'test -x "${package}/.venv/bin/python"' in workflow
    assert "rcc run -r developer/toolkit.yaml --dev -t ToolkitTest" in workflow[isolation:]


def test_ci_builds_and_launches_community_binary_on_linux() -> None:
    workflow = (
        REPOSITORY_ROOT / ".github" / "workflows" / "developer_toolkit.yml"
    ).read_text()

    assert "- name: Build and verify community binary (Linux)" in workflow
    assert "rcc run -r developer/toolkit.yaml --dev -t InstallCommunity" in workflow
    assert "BuildCommunity" not in workflow
    assert "build-community" not in workflow


def test_bootstrap_launchers_download_pinned_rcc_and_run_toolkit() -> None:
    shell = (REPOSITORY_ROOT / "devutils" / "bin" / "develop.sh").read_text()
    batch = (REPOSITORY_ROOT / "devutils" / "bin" / "develop.bat").read_text()

    for launcher in (shell, batch):
        assert "v18.18.1" in launcher
        assert "joshyorko/rcc/releases/download" in launcher
        assert "developer" in launcher
        assert "toolkit.yaml" in launcher
    assert "brew tap joshyorko/tools" in shell
    assert "brew install --cask joshyorko/tools/rcc" in shell
    assert "powershell.exe" in batch


def test_dispatcher_resolves_repository_root() -> None:
    assert toolkit.REPOSITORY_ROOT == REPOSITORY_ROOT
    assert toolkit.RCC_VERSION == "v18.18.1"
    assert toolkit.PACKAGES == (
        "actions",
        "actions-http-helper",
        "devutils",
        "work-items",
        "action_server",
    )
    assert toolkit.COMMANDS.keys() >= {
        "doctor",
        "bootstrap",
        "test",
        "toolkit-test",
        "lint",
        "typecheck",
        "docs",
        "check-all",
        "frontend-test",
        "install-community",
    }


def test_run_isolates_package_poetry_from_rcc_and_host_environments() -> None:
    with patch.dict(
        "os.environ",
        {
            "VIRTUAL_ENV": "/host/venv",
            "POETRY_ACTIVE": "1",
            "CONDA_PREFIX": "/rcc/holotree",
            "CONDA_DEFAULT_ENV": "rcc",
            "CONDA_PROMPT_MODIFIER": "(rcc)",
            "CONDA_SHLVL": "1",
            "CONDA_EXE": "/rcc/micromamba",
            "_CE_CONDA": "1",
            "_CE_M": "1",
            "PYTHONHOME": "/host/python",
            "PYTHONPATH": "/host/pythonpath",
            "PYTHON_EXE": "/rcc/holotree/bin/python3",
            "ROBOT_ARTIFACTS": "/rcc/artifacts",
            "ROBOT_ROOT": "/rcc/robot",
        },
    ), patch(
        "toolkit.subprocess.run"
    ) as run:
        toolkit.run(["python", "--version"])

    assert "shell" not in run.call_args.kwargs
    environment = run.call_args.kwargs["env"]
    for name in (
        "VIRTUAL_ENV",
        "POETRY_ACTIVE",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "CONDA_PROMPT_MODIFIER",
        "CONDA_SHLVL",
        "CONDA_EXE",
        "_CE_CONDA",
        "_CE_M",
        "PYTHONHOME",
        "PYTHONPATH",
        "PYTHON_EXE",
        "ROBOT_ARTIFACTS",
        "ROBOT_ROOT",
    ):
        assert name not in environment
    assert environment["POETRY_VIRTUALENVS_CREATE"] == "true"
    assert environment["POETRY_VIRTUALENVS_IN_PROJECT"] == "true"
    assert environment["POETRY_VIRTUALENVS_OPTIONS_SYSTEM_SITE_PACKAGES"] == "false"


def test_run_puts_package_virtualenv_first_on_path(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()
    scripts = tmp_path / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")

    with patch.dict("os.environ", {"PATH": "/rcc/holotree/bin"}), patch(
        "toolkit.subprocess.run"
    ) as run:
        toolkit.run(["python", "--version"], cwd=tmp_path)

    assert run.call_args.kwargs["env"]["PATH"].split(toolkit.os.pathsep)[0] == str(
        scripts
    )


def test_install_community_builds_installs_and_verifies() -> None:
    executable = "action-server.exe" if toolkit.sys.platform == "win32" else "action-server"
    target = Path("/custom/bin") / executable
    with patch.object(toolkit, "poetry") as poetry, patch.object(toolkit, "run") as run, patch.object(
        toolkit, "resolve_install_target", return_value=target
    ) as resolve, patch.object(toolkit, "install_executable") as install:
        toolkit.install_community()

    assert [call.args for call in poetry.call_args_list] == [
        ("action_server", "run", "invoke", "build-frontend"),
        (
            "action_server",
            "run",
            "invoke",
            "build-executable",
            "--go-wrapper",
            "--version",
            "community-local",
        ),
    ]
    run.assert_any_call(
        [
            str(REPOSITORY_ROOT / "action_server" / "dist" / "final" / executable),
            "new",
            "--help",
        ],
        REPOSITORY_ROOT / "action_server",
    )
    resolve.assert_called_once_with()
    install.assert_called_once_with(
        REPOSITORY_ROOT / "action_server" / "dist" / "final" / executable, target
    )
    assert run.call_args_list[-2].args == ([str(target), "version"],)
    assert run.call_args_list[-1].args == ([str(target), "new", "--help"],)


def test_resolve_install_target_uses_existing_executable() -> None:
    with patch.object(
        toolkit.shutil,
        "which",
        return_value="/home/linuxbrew/.linuxbrew/bin/action-server",
    ):
        assert toolkit.resolve_install_target() == Path(
            "/home/linuxbrew/.linuxbrew/bin/action-server"
        )


def test_resolve_install_target_uses_posix_fallback_on_path() -> None:
    with patch.object(toolkit.shutil, "which", return_value=None), patch.object(
        toolkit.Path, "home", return_value=Path("/home/user")
    ), patch.dict("os.environ", {"PATH": "/home/user/.local/bin:/usr/bin"}):
        assert toolkit.resolve_install_target() == Path(
            "/home/user/.local/bin/action-server"
        )


def test_resolve_install_target_uses_windows_fallback_on_path() -> None:
    local_app_data = Path("/local/appdata")
    with patch.object(toolkit.shutil, "which", return_value=None), patch.object(
        toolkit.sys, "platform", "win32"
    ), patch.dict(
        "os.environ",
        {
            "LOCALAPPDATA": str(local_app_data),
            "PATH": str(local_app_data / "Programs" / "Actions" / "bin"),
        },
    ):
        assert toolkit.resolve_install_target() == Path(
            "/local/appdata/Programs/Actions/bin/action-server.exe"
        )


def test_resolve_install_target_rejects_fallback_directory_not_on_path() -> None:
    with patch.object(toolkit.shutil, "which", return_value=None), patch.object(
        toolkit.Path, "home", return_value=Path("/home/user")
    ), patch.dict("os.environ", {"PATH": "/usr/bin"}):
        error = pytest.raises(SystemExit, toolkit.resolve_install_target)

    assert "/home/user/.local/bin" in str(error.value)


def test_install_executable_atomically_replaces_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_bytes(b"new")
    target.write_bytes(b"old")
    target.chmod(0o755)

    toolkit.install_executable(source, target)

    assert target.read_bytes() == b"new"
    assert target.stat().st_mode & 0o111
    assert list(tmp_path.glob(f".{target.name}.*")) == []


def test_install_executable_preserves_old_target_on_replace_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_bytes(b"new")
    target.write_bytes(b"old")

    with patch.object(toolkit.os, "replace", side_effect=PermissionError("denied")):
        error = pytest.raises(SystemExit, toolkit.install_executable, source, target)

    assert target.read_bytes() == b"old"
    assert str(target) in str(error.value)
    assert list(tmp_path.glob(f".{target.name}.*")) == []


def test_typecheck_uses_only_package_configured_gates() -> None:
    with patch.object(toolkit, "poetry") as poetry:
        toolkit.typecheck()

    assert [call.args for call in poetry.call_args_list] == [
        ("actions", "run", "invoke", "typecheck"),
        ("actions-http-helper", "run", "invoke", "typecheck"),
        ("work-items", "run", "mypy"),
        ("action_server", "run", "invoke", "typecheck"),
    ]


def test_lint_uses_package_configured_gates() -> None:
    with patch.object(toolkit, "poetry") as poetry:
        toolkit.lint()

    assert [call.args for call in poetry.call_args_list] == [
        ("actions", "run", "invoke", "lint"),
        ("actions-http-helper", "run", "invoke", "lint"),
        ("devutils", "run", "ruff", "check", "src", "tests"),
        ("work-items", "run", "ruff", "check", "src", "tests"),
        ("action_server", "run", "invoke", "lint"),
    ]


def test_test_uses_package_configured_gates() -> None:
    with patch.object(toolkit, "toolkit_test"), patch.object(
        toolkit, "poetry"
    ) as poetry:
        toolkit.test()

    assert [call.args for call in poetry.call_args_list] == [
        ("actions", "run", "invoke", "test"),
        ("actions-http-helper", "run", "invoke", "test"),
        ("devutils", "run", "pytest", "tests"),
        (
            "work-items",
            "run",
            "pytest",
            "tests",
            "-m",
            "not persistent_backend_service",
        ),
        ("action_server", "run", "invoke", "test-not-integration"),
    ]
