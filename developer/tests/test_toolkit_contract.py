import sys
from pathlib import Path
from unittest.mock import patch

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
        "BuildCommunity",
    }
    assert manifest["ignoreFiles"] == ["../.gitignore"]
    assert manifest["environmentConfigs"] == ["setup.yaml"]


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
    assert "rcc run -r developer/toolkit.yaml --dev -t BuildCommunity" in workflow


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
        "build-community",
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


def test_build_community_uses_public_invoke_contract() -> None:
    executable = "action-server.exe" if toolkit.sys.platform == "win32" else "action-server"
    with patch.object(toolkit, "poetry") as poetry, patch.object(toolkit, "run") as run:
        toolkit.build_community()

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
    run.assert_called_once_with(
        [
            str(REPOSITORY_ROOT / "action_server" / "dist" / "final" / executable),
            "new",
            "--help",
        ],
        REPOSITORY_ROOT / "action_server",
    )


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
